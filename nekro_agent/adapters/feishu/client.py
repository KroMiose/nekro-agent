import asyncio
import io
import json
import logging
import threading
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, Optional

import lark_oapi as lark
from lark_oapi.api.contact.v3 import GetUserRequest, GetUserResponse
from lark_oapi.api.im.v1 import (
    CreateFileRequest,
    CreateFileRequestBody,
    CreateFileResponse,
    CreateImageRequest,
    CreateImageRequestBody,
    CreateImageResponse,
    CreateMessageReactionRequest,
    CreateMessageReactionRequestBody,
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageResponse,
    DeleteMessageReactionRequest,
    Emoji,
    GetChatRequest,
    GetChatResponse,
    GetMessageResourceRequest,
)
from lark_oapi.core.enum import AccessTokenType, HttpMethod
from lark_oapi.core.model import BaseRequest

from nekro_agent.adapters.interface.schemas.platform import PlatformUser
from nekro_agent.core.logger import get_sub_logger

logger = get_sub_logger("adapter.feishu")
lark_logger = get_sub_logger("adapter.feishu.lark")


# ── 接管 lark-oapi 日志系统，转发到项目统一 logger ────────────────────────────


class _LarkLogHandler(logging.Handler):
    """将 lark-oapi SDK 的日志转发到项目的 loguru logger"""

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if "ping" in msg.lower():
            return
        if "pong" in msg.lower():
            return

        level_map = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "CRITICAL",
        }
        level = level_map.get(record.levelno, "INFO")
        lark_logger.opt(depth=6).log(level, "[Lark] {}", msg)


def _setup_lark_logging() -> None:
    """接管 lark_oapi 的日志输出，转发到项目 logger

    必须在 lark.ws.Client 构造之后调用，
    因为 ws.Client.__init__ 会 setLevel 覆盖级别。
    """
    lark_logger = logging.getLogger("Lark")
    lark_logger.handlers.clear()
    lark_logger.addHandler(_LarkLogHandler())
    lark_logger.setLevel(logging.DEBUG)

if TYPE_CHECKING:
    from .adapter import FeishuAdapter


class FeishuClient:
    """飞书客户端，负责 WebSocket 连接和 API 封装

    核心架构：
    - 主线程运行 asyncio 事件循环
    - daemon 线程运行 lark.ws.Client 的 WebSocket 长连接
    - 通过 asyncio.run_coroutine_threadsafe 从 daemon 线程桥接到主线程
    - 通过 run_in_executor 从主线程调用同步 API
    """

    def __init__(self, app_id: str, app_secret: str, adapter: "FeishuAdapter"):
        self._app_id = app_id
        self._app_secret = app_secret
        self._adapter = adapter
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._bot_info: Optional[PlatformUser] = None

        # 创建 lark-oapi 同步客户端
        self._lark_client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()

    @property
    def bot_info(self) -> Optional[PlatformUser]:
        return self._bot_info

    async def start(self) -> None:
        """启动客户端"""
        self._loop = asyncio.get_running_loop()

        # 获取机器人自身信息
        try:
            bot_info_dict = await self._run_sync(self._get_bot_info_sync)
            self._bot_info = PlatformUser(
                platform_name="feishu",
                user_id=bot_info_dict.get("open_id", ""),
                user_name=bot_info_dict.get("name", "FeishuBot"),
                user_avatar=bot_info_dict.get("avatar", {}).get("avatar_72", ""),
            )
            logger.success(f"飞书机器人信息获取成功: {self._bot_info.user_name} ({self._bot_info.user_id})")
        except Exception:
            logger.exception("获取飞书机器人信息失败，部分功能可能受限")

        # 构建事件处理器
        event_handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._on_message_receive)
            .build()
        )

        # 构建 WebSocket 客户端
        ws_client = lark.ws.Client(
            self._app_id,
            self._app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.WARNING,
        )

        _setup_lark_logging()

        # 在 daemon 线程中启动 WebSocket 连接
        ws_thread = threading.Thread(target=ws_client.start, daemon=True, name="feishu-ws")
        ws_thread.start()
        logger.info("飞书 WebSocket 客户端已在后台线程启动")

    async def stop(self) -> None:
        """停止客户端（daemon 线程随主进程自动终止）"""
        logger.info("飞书客户端停止")

    def _on_message_receive(self, data: lark.im.v1.P2ImMessageReceiveV1) -> None:
        """WebSocket 消息回调（在 SDK 线程中被同步调用）

        通过 asyncio.run_coroutine_threadsafe 桥接到主线程的 asyncio 事件循环。
        """
        if self._loop is None:
            logger.warning("事件循环未就绪，忽略消息")
            return

        try:
            event = data.event
            if not event:
                return

            # 将 event 数据转换为字典
            event_data = self._extract_event_data(event)

            # 导入消息处理器（延迟导入避免循环引用）
            from .message_processor import handle_message

            # 桥接到主线程事件循环
            future = asyncio.run_coroutine_threadsafe(
                handle_message(self, self._adapter, event_data),
                self._loop,
            )
            # 阻塞等待结果，设置超时防止死锁
            future.result(timeout=30)
        except TimeoutError:
            logger.warning("消息处理超时")
        except Exception:
            logger.exception("处理飞书消息回调失败")

    def _extract_event_data(self, event: Any) -> Dict[str, Any]:
        """从 lark-oapi 事件对象中提取数据字典"""
        result: Dict[str, Any] = {}

        # 提取 sender 信息
        sender = event.sender
        if sender:
            sender_id = sender.sender_id
            result["sender"] = {
                "sender_id": {
                    "open_id": sender_id.open_id if sender_id else "",
                    "user_id": sender_id.user_id if sender_id else "",
                    "union_id": sender_id.union_id if sender_id else "",
                },
                "sender_type": sender.sender_type or "",
                "tenant_key": sender.tenant_key or "",
            }

        # 提取 message 信息
        msg = event.message
        if msg:
            # 处理 mentions
            mentions_list = []
            if msg.mentions:
                for mention in msg.mentions:
                    mentions_list.append({
                        "key": mention.key or "",
                        "id": {
                            "open_id": mention.id.open_id if mention.id else "",
                            "user_id": mention.id.user_id if mention.id else "",
                            "union_id": mention.id.union_id if mention.id else "",
                        },
                        "name": mention.name or "",
                        "tenant_key": mention.tenant_key or "",
                    })

            result["message"] = {
                "message_id": msg.message_id or "",
                "root_id": msg.root_id or "",
                "parent_id": msg.parent_id or "",
                "create_time": msg.create_time or "",
                "chat_id": msg.chat_id or "",
                "chat_type": msg.chat_type or "",
                "message_type": msg.message_type or "",
                "content": msg.content or "{}",
                "mentions": mentions_list,
            }

        return result

    async def _run_sync(self, func: Any, *args: Any) -> Any:
        """在线程池中运行同步函数"""
        if self._loop is None:
            raise RuntimeError("事件循环未初始化")
        return await self._loop.run_in_executor(None, partial(func, *args))

    # ========================================================================================
    # |                              飞书 API 封装                                             |
    # ========================================================================================

    def _get_bot_info_sync(self) -> Dict[str, Any]:
        """获取机器人自身信息（同步）

        通过 GET /open-apis/bot/v3/info/ 获取机器人信息，
        该接口是飞书获取机器人自身信息的标准方式。
        """
        request = (
            BaseRequest.builder()
            .http_method(HttpMethod.GET)
            .uri("/open-apis/bot/v3/info/")
            .token_types({AccessTokenType.TENANT})
            .build()
        )
        response = self._lark_client.request(request)

        if response.code != 0:
            raise RuntimeError(f"获取机器人信息失败: {response.code} - {response.msg}")

        # 从原始响应解析 bot 信息
        raw_data = json.loads(response.raw.content.decode("utf-8")) if response.raw else {}
        bot = raw_data.get("bot", {})
        return {
            "open_id": bot.get("open_id", ""),
            "name": bot.get("app_name", ""),
            "avatar": {
                "avatar_72": bot.get("avatar_url", ""),
                "avatar_240": bot.get("avatar_url", ""),
                "avatar_640": bot.get("avatar_url", ""),
                "avatar_origin": bot.get("avatar_url", ""),
            },
        }

    async def get_user_info(self, open_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        return await self._run_sync(self._get_user_info_sync, open_id)

    def _get_user_info_sync(self, open_id: str) -> Dict[str, Any]:
        """获取用户信息（同步）"""
        request = GetUserRequest.builder().user_id(open_id).user_id_type("open_id").build()
        response: GetUserResponse = self._lark_client.contact.v3.user.get(request)

        if not response.success():
            raise RuntimeError(f"获取用户信息失败: {response.code} - {response.msg}")

        user = response.data.user
        return {
            "open_id": user.open_id or "",
            "name": user.name or "",
            "avatar": {
                "avatar_72": user.avatar.avatar_72 if user.avatar else "",
                "avatar_240": user.avatar.avatar_240 if user.avatar else "",
                "avatar_640": user.avatar.avatar_640 if user.avatar else "",
                "avatar_origin": user.avatar.avatar_origin if user.avatar else "",
            },
        }

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """获取群聊信息"""
        return await self._run_sync(self._get_chat_info_sync, chat_id)

    def _get_chat_info_sync(self, chat_id: str) -> Dict[str, Any]:
        """获取群聊信息（同步）"""
        request = GetChatRequest.builder().chat_id(chat_id).build()
        response: GetChatResponse = self._lark_client.im.v1.chat.get(request)

        if not response.success():
            raise RuntimeError(f"获取群聊信息失败: {response.code} - {response.msg}")

        chat = response.data
        return {
            "chat_id": chat_id,
            "name": chat.name or "",
            "avatar": chat.avatar or "",
            "description": chat.description or "",
        }

    async def send_text_message(self, receive_id: str, receive_id_type: str, text: str) -> str:
        """发送文本消息，返回 message_id"""
        return await self._run_sync(self._send_text_message_sync, receive_id, receive_id_type, text)

    def _send_text_message_sync(self, receive_id: str, receive_id_type: str, text: str) -> str:
        """发送文本消息（同步）"""
        content = json.dumps({"text": text})
        request = (
            CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .msg_type("text")
                .content(content)
                .build()
            )
            .build()
        )
        response: CreateMessageResponse = self._lark_client.im.v1.message.create(request)

        if not response.success():
            raise RuntimeError(f"发送文本消息失败: {response.code} - {response.msg}")

        return response.data.message_id or ""

    async def upload_image(self, image_bytes: bytes) -> str:
        """上传图片，返回 image_key"""
        return await self._run_sync(self._upload_image_sync, image_bytes)

    def _upload_image_sync(self, image_bytes: bytes) -> str:
        """上传图片（同步）"""
        request = (
            CreateImageRequest.builder()
            .request_body(
                CreateImageRequestBody.builder()
                .image_type("message")
                .image(io.BytesIO(image_bytes))
                .build()
            )
            .build()
        )
        response: CreateImageResponse = self._lark_client.im.v1.image.create(request)

        if not response.success():
            raise RuntimeError(f"上传图片失败: {response.code} - {response.msg}")

        return response.data.image_key or ""

    async def send_image_message(self, receive_id: str, receive_id_type: str, image_key: str) -> str:
        """发送图片消息，返回 message_id"""
        return await self._run_sync(self._send_image_message_sync, receive_id, receive_id_type, image_key)

    def _send_image_message_sync(self, receive_id: str, receive_id_type: str, image_key: str) -> str:
        """发送图片消息（同步）"""
        content = json.dumps({"image_key": image_key})
        request = (
            CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .msg_type("image")
                .content(content)
                .build()
            )
            .build()
        )
        response: CreateMessageResponse = self._lark_client.im.v1.message.create(request)

        if not response.success():
            raise RuntimeError(f"发送图片消息失败: {response.code} - {response.msg}")

        return response.data.message_id or ""

    async def upload_file(self, file_bytes: bytes, file_name: str, file_type: str = "stream") -> str:
        """上传文件，返回 file_key"""
        return await self._run_sync(self._upload_file_sync, file_bytes, file_name, file_type)

    def _upload_file_sync(self, file_bytes: bytes, file_name: str, file_type: str = "stream") -> str:
        """上传文件（同步）"""
        request = (
            CreateFileRequest.builder()
            .request_body(
                CreateFileRequestBody.builder()
                .file_type(file_type)
                .file_name(file_name)
                .file(io.BytesIO(file_bytes))
                .build()
            )
            .build()
        )
        response: CreateFileResponse = self._lark_client.im.v1.file.create(request)

        if not response.success():
            raise RuntimeError(f"上传文件失败: {response.code} - {response.msg}")

        return response.data.file_key or ""

    async def send_file_message(self, receive_id: str, receive_id_type: str, file_key: str) -> str:
        """发送文件消息，返回 message_id"""
        return await self._run_sync(self._send_file_message_sync, receive_id, receive_id_type, file_key)

    def _send_file_message_sync(self, receive_id: str, receive_id_type: str, file_key: str) -> str:
        """发送文件消息（同步）"""
        content = json.dumps({"file_key": file_key})
        request = (
            CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .msg_type("file")
                .content(content)
                .build()
            )
            .build()
        )
        response: CreateMessageResponse = self._lark_client.im.v1.message.create(request)

        if not response.success():
            raise RuntimeError(f"发送文件消息失败: {response.code} - {response.msg}")

        return response.data.message_id or ""

    async def download_image(self, message_id: str, image_key: str) -> bytes:
        """下载图片内容"""
        return await self._run_sync(self._download_resource_sync, message_id, image_key, "image")

    async def download_file(self, message_id: str, file_key: str) -> bytes:
        """下载文件内容"""
        return await self._run_sync(self._download_resource_sync, message_id, file_key, "file")

    def _download_resource_sync(self, message_id: str, file_key: str, resource_type: str) -> bytes:
        """下载消息资源（同步）"""
        request = (
            GetMessageResourceRequest.builder()
            .message_id(message_id)
            .file_key(file_key)
            .type(resource_type)
            .build()
        )
        response = self._lark_client.im.v1.message_resource.get(request)

        if not response.success():
            raise RuntimeError(f"下载资源失败: {response.code} - {response.msg}")

        return response.file.read()

    async def add_message_reaction(self, message_id: str, emoji_type: str) -> Optional[str]:
        """添加消息表情回应，返回 reaction_id"""
        return await self._run_sync(self._add_message_reaction_sync, message_id, emoji_type)

    def _add_message_reaction_sync(self, message_id: str, emoji_type: str) -> Optional[str]:
        """添加消息表情回应（同步）"""
        request = (
            CreateMessageReactionRequest.builder()
            .message_id(message_id)
            .request_body(
                CreateMessageReactionRequestBody.builder()
                .reaction_type(Emoji.builder().emoji_type(emoji_type).build())
                .build()
            )
            .build()
        )
        response = self._lark_client.im.v1.message_reaction.create(request)

        if not response.success():
            logger.warning(f"添加表情回应失败: {response.code} - {response.msg}")
            return None

        return response.data.reaction_id if response.data else None

    async def remove_message_reaction(self, message_id: str, reaction_id: str) -> bool:
        """移除消息表情回应"""
        return await self._run_sync(self._remove_message_reaction_sync, message_id, reaction_id)

    def _remove_message_reaction_sync(self, message_id: str, reaction_id: str) -> bool:
        """移除消息表情回应（同步）"""
        request = (
            DeleteMessageReactionRequest.builder()
            .message_id(message_id)
            .reaction_id(reaction_id)
            .build()
        )
        response = self._lark_client.im.v1.message_reaction.delete(request)

        if not response.success():
            logger.warning(f"移除表情回应失败: {response.code} - {response.msg}")
            return False

        return True
