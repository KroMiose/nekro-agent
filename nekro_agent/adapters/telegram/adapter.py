"""
Telegram 适配器实现
"""

import asyncio
import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from telegram import Bot
from telegram.ext import Application, MessageHandler, filters

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    ChatType,
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import logger

from .config import TelegramConfig
from .http_client import TelegramHTTPClient
from .message_processor import MessageProcessor

if TYPE_CHECKING:
    from fastapi import APIRouter


class TelegramAdapter(BaseAdapter[TelegramConfig]):
    """基于 python-telegram-bot 的 Telegram 适配器"""

    def __init__(self, config_cls: type[TelegramConfig] = TelegramConfig):
        super().__init__(config_cls)
        self.application: Optional[Application] = None
        self.message_processor: Optional[MessageProcessor] = None
        self.http_client: Optional[TelegramHTTPClient] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._polling_retries = 0
        self._max_polling_retries = 5
        self._polling_retry_delay = 5  # 秒

    @property
    def key(self) -> str:
        return "telegram"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="Telegram",
            description="基于 python-telegram-bot 的 Telegram 适配器",
            version="2.0.0",
            author="nekro-agent",
            tags=["telegram", "chat", "bot"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "群聊: `telegram-group_-123456789` (负数为超级群组)",
            "私聊: `telegram-private_123456789` (正数为私聊用户)",
        ]

    def build_chat_key(self, chat_id_or_chat) -> str:
        """重写基类方法，生成包含类型前缀的聊天标识
        
        Args:
            chat_id_or_chat: 可以是 chat.id (int) 或 Chat 对象
        
        Returns:
            str: 完整的聊天标识，格式为 telegram-{type}_{id}
        """
        # 如果传入的是 Chat 对象
        if hasattr(chat_id_or_chat, 'type') and hasattr(chat_id_or_chat, 'id'):
            chat_type = "private" if chat_id_or_chat.type == "private" else "group"
            return f"{self.key}-{chat_type}_{chat_id_or_chat.id}"

    def parse_chat_key(self, chat_key: str) -> Tuple[str, str]:
        """解析聊天标识（Telegram 特殊处理负数群组ID）

        Args:
            chat_key: 聊天标识，格式如 telegram-group_-1002768666191

        Returns:
            Tuple[str, str]: (adapter_key, channel_id)

        Raises:
            ValueError: 当聊天标识格式无效时
        """
        # 使用限制分割次数的方式处理，只在第一个 '-' 处分割
        # 这样可以正确处理负数群组ID，如: telegram-group_-1002768666191
        parts = chat_key.split("-", 1)

        if len(parts) != 2:
            raise ValueError(f"无效的聊天标识: {chat_key}")

        adapter_key = parts[0]
        channel_id = parts[1]

        return adapter_key, channel_id

    async def init(self) -> None:
        """初始化适配器"""
        if not self.config.BOT_TOKEN:
            logger.warning("BOT_TOKEN 未配置，跳过 Telegram 适配器初始化")
            return

        try:
            # 使用配置中的代理地址（默认na代理配置）
            proxy_url = self.config.PROXY_URL.strip() if self.config.PROXY_URL else None
            if proxy_url:
                logger.info(f"Telegram 适配器使用代理: {proxy_url}")
            
            # 初始化 Application
            self.application = (
                Application.builder().token(self.config.BOT_TOKEN).build()
            )

            # 初始化消息处理器
            self.message_processor = MessageProcessor(self)

            # 添加消息处理器
            self.application.add_handler(
                MessageHandler(filters.ALL, self.message_processor.process_update),
            )

            # 初始化 HTTP 客户端（传入代理配置）
            self.http_client = TelegramHTTPClient(self.config.BOT_TOKEN, proxy_url)

            # 启动应用
            await self.application.initialize()
            await self.application.start()

            # 在后台启动轮询
            self._polling_retries = 0  # 重置重试计数
            self._polling_task = asyncio.create_task(self._start_polling_with_retry())

            logger.info("Telegram 适配器初始化成功")

        except Exception as e:
            logger.error(f"Telegram 适配器初始化失败: {e}")
            await self.cleanup()

    async def _start_polling(self) -> None:
        """启动轮询"""
        try:
            if self.application and self.application.updater:
                await self.application.updater.start_polling()
                logger.info("Telegram 轮询已启动")
                # 成功启动后重置重试计数
                self._polling_retries = 0
        except Exception as e:
            logger.error(f"Telegram 轮询启动失败: {e}")
            raise

    async def _start_polling_with_retry(self) -> None:
        """启动带重试机制的轮询"""
        while self._polling_retries < self._max_polling_retries:
            try:
                await self._start_polling()
                return  # 成功启动，退出循环
            except Exception as e:
                self._polling_retries += 1
                if self._polling_retries < self._max_polling_retries:
                    logger.warning(
                        f"Telegram 轮询启动失败，第 {self._polling_retries} 次重试，"
                        f"{self._polling_retry_delay} 秒后重试: {e}"
                    )
                    await asyncio.sleep(self._polling_retry_delay)
                else:
                    logger.error(
                        f"Telegram 轮询启动失败，已达到最大重试次数 {self._max_polling_retries}，"
                        f"请检查网络连接或 Bot Token 配置"
                    )
                    break

    async def cleanup(self) -> None:
        """清理适配器"""
        try:
            # 停止轮询任务
            if self._polling_task and not self._polling_task.done():
                self._polling_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._polling_task

            # 停止应用
            if self.application:
                if self.application.updater:
                    await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

            # 关闭 HTTP 客户端
            if (
                self.http_client
                and hasattr(self.http_client, "client")
                and self.http_client.client
            ):
                await self.http_client.client.aclose()

            logger.info("Telegram 适配器已清理")
        except Exception as e:
            logger.error(f"Telegram 适配器清理失败: {e}")

    async def forward_message(
        self,
        request: PlatformSendRequest,
    ) -> PlatformSendResponse:
        """转发消息到 Telegram 平台"""
        if not self.http_client:
            return PlatformSendResponse(
                success=False,
                error_message="Telegram HTTP 客户端未初始化",
            )

        try:
            # 解析聊天键获取频道ID
            _, channel_id = self.parse_chat_key(request.chat_key)
            # 提取实际的 chat_id
            chat_id = channel_id.split("_", 1)[1] if "_" in channel_id else channel_id

            message_ids = []

            async with self.http_client:
                # 处理消息段
                for segment in request.segments:
                    if segment.type == PlatformSendSegmentType.TEXT:
                        if segment.content and segment.content.strip():
                            msg_id = await self.http_client.send_message(
                                chat_id=chat_id,
                                text=segment.content,
                                reply_to_message_id=request.ref_msg_id,
                            )
                            if msg_id:
                                message_ids.append(msg_id)

                    elif segment.type == PlatformSendSegmentType.AT:
                        # Telegram @ 功能通过在文本中包含 @username 或用户ID来实现
                        # 这里将 AT 段转换为文本形式
                        if segment.at_info:
                            at_text = f"@{segment.at_info.nickname or segment.at_info.platform_user_id}"
                            msg_id = await self.http_client.send_message(
                                chat_id=chat_id,
                                text=at_text,
                                reply_to_message_id=request.ref_msg_id,
                            )
                            if msg_id:
                                message_ids.append(msg_id)

                    elif segment.type == PlatformSendSegmentType.IMAGE:
                        if segment.file_path and Path(segment.file_path).exists():
                            with Path(segment.file_path).open("rb") as f:
                                photo_data = f.read()
                            msg_id = await self.http_client.send_photo(
                                chat_id=chat_id,
                                photo_data=photo_data,
                                reply_to_message_id=request.ref_msg_id,
                            )
                            if msg_id:
                                message_ids.append(msg_id)

                    elif (
                        segment.type == PlatformSendSegmentType.FILE
                        and segment.file_path
                        and Path(segment.file_path).exists()
                    ):
                        with Path(segment.file_path).open("rb") as f:
                            file_data = f.read()
                        filename = Path(segment.file_path).name
                        msg_id = await self.http_client.send_document(
                            chat_id=chat_id,
                            document_data=file_data,
                            filename=filename,
                            reply_to_message_id=request.ref_msg_id,
                        )
                        if msg_id:
                            message_ids.append(msg_id)

            if message_ids:
                return PlatformSendResponse(
                    success=True,
                    message_id=message_ids[0]
                    if len(message_ids) == 1
                    else ",".join(message_ids),
                )
            return PlatformSendResponse(
                success=True,
                message_id="empty",
            )

        except Exception as e:
            error_msg = f"Telegram 消息发送失败: {e!s}"
            logger.error(error_msg)
            return PlatformSendResponse(success=False, error_message=error_msg)

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        if not self.http_client:
            raise RuntimeError("HTTP 客户端未初始化")

        async with self.http_client:
            bot_info = await self.http_client.get_me()

        return PlatformUser(
            platform_name=self.key,
            user_id=str(bot_info.get("id", "")),
            user_name=bot_info.get("username", ""),
            user_avatar="",
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户信息
        
        注意：这个方法主要用于其他地方需要获取用户信息时调用
        在消息处理过程中，应直接使用 message.from_user 中的信息
        """
        if not self.http_client:
            raise RuntimeError("HTTP 客户端未初始化")

        try:
            chat_id = channel_id.split("_", 1)[1] if "_" in channel_id else channel_id

            async with self.http_client:
                # 对于群聊，尝试获取群成员信息
                if "group" in channel_id:
                    member_info = await self.http_client.get_chat_member(chat_id, user_id)
                    user_info = member_info.get("user", {})
                else:
                    # 对于私聊，无法获取详细信息，只能返回基本信息
                    user_info = {"id": user_id}

            # 构建完整的用户名称
            first_name = user_info.get("first_name", "")
            last_name = user_info.get("last_name", "")
            username = user_info.get("username", "")
            
            # 优先使用完整名称，然后是用户名
            if first_name and last_name:
                display_name = f"{first_name} {last_name}"
            elif first_name:
                display_name = first_name
            elif username:
                display_name = username
            else:
                display_name = user_id

            return PlatformUser(
                platform_name=self.key,
                user_id=str(user_info.get("id", user_id)),
                user_name=display_name,
                user_avatar="",
            )
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            # 返回默认用户信息
            return PlatformUser(
                platform_name=self.key,
                user_id=user_id,
                user_name=user_id,
                user_avatar="",
            )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        if not self.http_client:
            raise RuntimeError("HTTP 客户端未初始化")

        try:
            chat_id = channel_id.split("_", 1)[1] if "_" in channel_id else channel_id

            async with self.http_client:
                chat_info = await self.http_client.get_chat(chat_id)

            chat_type = (
                ChatType.PRIVATE
                if chat_info.get("type") == "private"
                else ChatType.GROUP
            )

            return PlatformChannel(
                platform_name=self.key,
                channel_id=channel_id,
                channel_name=chat_info.get("title")
                or chat_info.get("first_name")
                or chat_id,
                channel_type=chat_type,
            )
        except Exception as e:
            logger.error(f"获取频道信息失败: {e}")
            # 返回默认频道信息
            chat_type = ChatType.PRIVATE if "private" in channel_id else ChatType.GROUP
            return PlatformChannel(
                platform_name=self.key,
                channel_id=channel_id,
                channel_name=channel_id,
                channel_type=chat_type,
            )

    def get_adapter_router(self) -> "APIRouter":
        """获取适配器路由"""
        from .routers import router

        return router
