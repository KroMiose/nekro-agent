import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from fastapi import APIRouter
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.adapters.onebot.v11.exception import NetworkError as OneBotNetworkError
from pydantic import Field

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.adapters.onebot_v11.matchers.message import register_matcher
from nekro_agent.core import config, logger
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.agent_message import AgentMessageSegment, AgentMessageSegmentType
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.schemas.i18n import i18n_text
from nekro_agent.services.command.schemas import CommandResponse

from ..interface.base import AdapterMetadata, BaseAdapter, BaseAdapterConfig
from .core.bot import get_bot
from .tools.at_parser import SegAt, parse_at_from_text
from .tools.cq_markup import neutralize_onebot_cq_at_all_markup
from .tools.convertor import get_channel_type


class OnebotV11Config(BaseAdapterConfig):
    """Onebot V11 适配器配置"""

    ENABLED: bool = Field(
        default=True,
        title="启用适配器",
        description="关闭后该适配器不会在启动时加载，修改后需要重启应用生效",
        json_schema_extra=ExtraField(
            is_need_restart=True,
            i18n_category=i18n_text(zh_CN="基础设置", en_US="Basic Settings"),
            i18n_title=i18n_text(zh_CN="启用适配器", en_US="Enable Adapter"),
            i18n_description=i18n_text(
                zh_CN="关闭后该适配器不会在启动时加载，修改后需要重启应用生效",
                en_US="When disabled, this adapter will not be loaded on startup. Restart the application after changes.",
            ),
        ).model_dump(),
    )

    BOT_QQ: str = Field(
        default="",
        title="机器人 QQ 号",
        description="当前 OneBot 机器人的 QQ 号",
        json_schema_extra=ExtraField(
            required=True,
            i18n_category=i18n_text(zh_CN="OneBot", en_US="OneBot"),
            i18n_title=i18n_text(zh_CN="机器人 QQ 号", en_US="Bot QQ Number"),
            i18n_description=i18n_text(
                zh_CN="当前 OneBot 机器人的 QQ 号",
                en_US="QQ number of the current OneBot bot.",
            ),
        ).model_dump(),
    )
    RESOLVE_CQ_CODE: bool = Field(
        default=False,
        title="是否解析 CQ 码",
        description="启用后，AI 发送的消息中的 CQ 码不再被视为纯文本，而是会被协议实现端解析为对应的富文本消息",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="OneBot", en_US="OneBot"),
            i18n_title=i18n_text(zh_CN="是否解析 CQ 码", en_US="Parse CQ Codes"),
            i18n_description=i18n_text(
                zh_CN="启用后，AI 发送的消息中的 CQ 码不再被视为纯文本，而是会被协议实现端解析为对应的富文本消息",
                en_US="When enabled, CQ codes in AI-generated messages will no longer be treated as plain text and will instead be parsed into rich messages by the protocol implementation.",
            ),
        ).model_dump(),
    )
    SESSION_GROUP_WELCOME_ENABLED: bool = Field(
        default=True,
        title="启用入群自动欢迎",
        description="启用后群成员增加通知会触发 AI 自动欢迎",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="OneBot", en_US="OneBot"),
            i18n_title=i18n_text(zh_CN="启用入群自动欢迎", en_US="Enable Group Welcome"),
            i18n_description=i18n_text(
                zh_CN="启用后群成员增加通知会触发 AI 自动欢迎",
                en_US="When enabled, group member increase notices trigger AI welcome replies.",
            ),
        ).model_dump(),
    )
    SESSION_GROUP_LEAVE_NOTICE_ENABLED: bool = Field(
        default=True,
        title="启用退群提醒",
        description="启用后群成员减少通知会触发 AI 退群提醒",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="OneBot", en_US="OneBot"),
            i18n_title=i18n_text(zh_CN="启用退群提醒", en_US="Enable Group Leave Notice"),
            i18n_description=i18n_text(
                zh_CN="启用后群成员减少通知会触发 AI 退群提醒",
                en_US="When enabled, group member decrease notices trigger AI leave notices.",
            ),
        ).model_dump(),
    )

    """NAPCAT 配置"""
    NAPCAT_ACCESS_URL: str = Field(
        default="http://127.0.0.1:6099/webui",
        title="NapCat WebUI 访问地址",
        description="NapCat 的 WebUI 地址，请确保对应端口已开放访问",
        json_schema_extra=ExtraField(
            placeholder="例: http://<服务器 IP>:<NapCat 端口>/webui",
            i18n_category=i18n_text(zh_CN="NapCat", en_US="NapCat"),
            i18n_title=i18n_text(zh_CN="NapCat WebUI 访问地址", en_US="NapCat WebUI URL"),
            i18n_description=i18n_text(
                zh_CN="NapCat 的 WebUI 地址，请确保对应端口已开放访问",
                en_US="WebUI URL of NapCat. Make sure the corresponding port is accessible.",
            ),
        ).model_dump(),
    )
    NAPCAT_CONTAINER_NAME: str = Field(
        default="nekro_napcat",
        title="NapCat 容器名称",
        description="NapCat 容器名称，用于容器相关集成功能",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="NapCat", en_US="NapCat"),
            i18n_title=i18n_text(zh_CN="NapCat 容器名称", en_US="NapCat Container Name"),
            i18n_description=i18n_text(
                zh_CN="NapCat 容器名称，用于容器相关集成功能",
                en_US="Container name of NapCat, used by container-related integration features.",
            ),
        ).model_dump(),
    )


class OnebotV11Adapter(BaseAdapter[OnebotV11Config]):
    """OneBot V11 适配器"""

    def __init__(self, config_cls: Type[OnebotV11Config] = OnebotV11Config):
        """初始化OnebotV11适配器"""
        super().__init__(config_cls)

    @property
    def key(self) -> str:
        return "onebot_v11"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="OneBot V11",
            description="OneBot V11 协议适配器，支持与兼容 OneBot V11 标准的 QQ 机器人实现进行通信",
            version="1.0.0",
            author="NekroAI",
            homepage="https://github.com/nekro-agent/nekro-agent",
            tags=["qq", "onebot", "v11", "chat", "messaging"],
        )

    @property
    def supports_webui_send(self) -> bool:
        return True

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "群聊: `onebot_v11-group_123456` (123456为群号)",
            "私聊: `onebot_v11-private_123456` (123456为用户QQ号)",
        ]

    def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        from .routers import router

        return router

    async def init(self) -> None:
        """初始化适配器"""
        from . import matchers

        register_matcher(self)

    async def cleanup(self) -> None:
        """清理适配器"""
        return

    async def render_runtime_prompt(self) -> str:
        """渲染 OneBot V11 适配器运行时提示词"""
        return (
            "<adapter_runtime_context name=\"OneBot V11\" adapter_key=\"onebot_v11\">\n"
            "Do not use raw CQ codes in `message_text`; use `[@id:123@]` for mentions and "
            "`send_msg_file` for images/files.\n"
            "</adapter_runtime_context>"
        )

    async def _try_send_enhanced_command_message(self, chat_key: str, message: str) -> bool:
        """OneBot V11: 以合并转发消息形式发送长文本"""
        try:
            await self._send_forward_message(chat_key, message)
        except Exception as e:
            logger.warning(f"[ForwardMsg] 合并转发发送失败: {e}")
            return False
        else:
            return True

    async def _try_send_enhanced_command_response(
        self,
        chat_key: str,
        response: CommandResponse,
        messages: list[AgentMessageSegment],
    ) -> bool:
        """OneBot V11: 以合并转发消息形式发送图文命令输出。"""
        if not response.output_segments:
            return False

        if any(msg.type == AgentMessageSegmentType.FILE for msg in messages):
            return False

        try:
            await self._send_forward_segments(chat_key, messages)
        except Exception as e:
            logger.warning(f"[ForwardMsg] 富媒体命令输出发送失败: {e}")
            return False
        else:
            return True

    async def _send_forward_message(self, chat_key: str, text: str) -> None:
        """以合并转发消息形式发送长文本，智能拆分段落"""
        bot: Bot = get_bot()
        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        chat_type = db_chat_channel.chat_type
        chat_id = int(db_chat_channel.channel_id.split("_")[1])

        # 智能拆分：优先按 ====== 分隔符，其次按双换行，最后按固定行数
        sections: List[str] = []
        if re.search(r"={3,}", text):
            # 按 ===== 标题行拆分
            sections = re.split(r"\n(?=={3,})", text)
        elif "\n\n" in text:
            # 按双换行拆分（如插件列表）
            sections = text.split("\n\n")
        else:
            # 按固定行数拆分（每 20 行一段）
            lines = text.split("\n")
            for i in range(0, len(lines), 20):
                sections.append("\n".join(lines[i : i + 20]))

        nodes: List[Dict[str, Any]] = []
        for section in sections:
            content = section.strip()
            if not content:
                continue
            nodes.append(
                {
                    "type": "node",
                    "data": {
                        "name": "NekroAgent",
                        "uin": bot.self_id,
                        "content": [{"type": "text", "data": {"text": content}}],
                    },
                }
            )

        if not nodes:
            raise ValueError("无法拆分消息内容")

        if chat_type is ChatType.GROUP:
            await bot.call_api("send_group_forward_msg", group_id=chat_id, messages=nodes)
        elif chat_type is ChatType.PRIVATE:
            await bot.call_api("send_private_forward_msg", user_id=chat_id, messages=nodes)
        else:
            raise ValueError(f"不支持的聊天类型: {chat_type}")

    async def _send_forward_segments(self, chat_key: str, messages: list[AgentMessageSegment]) -> None:
        """以合并转发消息形式发送图文消息段。"""
        bot: Bot = get_bot()
        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        chat_type = db_chat_channel.chat_type
        chat_id = int(db_chat_channel.channel_id.split("_")[1])

        nodes: list[dict[str, Any]] = []
        current_message = Message()

        def flush_current() -> None:
            if current_message:
                nodes.append(
                    {
                        "type": "node",
                        "data": {
                            "name": "NekroAgent",
                            "uin": bot.self_id,
                            "content": current_message.copy(),
                        },
                    }
                )
                current_message.clear()

        for item in messages:
            if item.type == AgentMessageSegmentType.TEXT:
                text = item.content.strip()
                if not text:
                    continue
                if current_message:
                    flush_current()
                current_message.append(MessageSegment.text(text))
                continue

            if item.type == AgentMessageSegmentType.IMAGE:
                image_path = Path(item.content)
                if not image_path.exists():
                    logger.warning(f"[ForwardMsg] 图片不存在，跳过: {image_path}")
                    continue
                current_message.append(MessageSegment.image(file=image_path.read_bytes()))
                flush_current()

        flush_current()

        if not nodes:
            raise ValueError("无法构建合并转发节点")

        if chat_type is ChatType.GROUP:
            await bot.call_api("send_group_forward_msg", group_id=chat_id, messages=nodes)
        elif chat_type is ChatType.PRIVATE:
            await bot.call_api("send_private_forward_msg", user_id=chat_id, messages=nodes)
        else:
            raise ValueError(f"不支持的聊天类型: {chat_type}")

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到 OneBot V11 协议端"""

        message_id: Optional[str] = None

        # 分离文件类型和其他类型的消息段
        file_segments = [seg for seg in request.segments if seg.type == PlatformSendSegmentType.FILE]
        other_segments = [seg for seg in request.segments if seg.type != PlatformSendSegmentType.FILE]

        # 先发送文件（如果有）
        if file_segments:
            await self._send_files(request.chat_key, file_segments)

        # 再发送其他类型消息（如果有）
        if other_segments:
            modified_request = PlatformSendRequest(
                chat_key=request.chat_key,
                segments=other_segments,
                ref_msg_id=request.ref_msg_id,
            )
            message_id = await self._send_message(modified_request)

        return PlatformSendResponse(success=True, message_id=message_id)

    async def _send_message(self, request: PlatformSendRequest) -> Optional[str]:
        """发送普通消息（文本、@、图片等）"""
        message = Message()

        if request.ref_msg_id:
            message.append(MessageSegment.reply(id_=int(request.ref_msg_id)))

        # 获取聊天频道信息用于 @ 解析
        db_chat_channel = await DBChatChannel.get_channel(chat_key=request.chat_key)

        for segment in request.segments:
            if segment.type == PlatformSendSegmentType.TEXT:
                if segment.content.strip():
                    content = neutralize_onebot_cq_at_all_markup(segment.content)
                    # NoneBot 特有功能：解析文本中的 @ 信息
                    seg_data = await parse_at_from_text(content, db_chat_channel)

                    for seg in seg_data:
                        if isinstance(seg, str):
                            if seg.strip():
                                self._append_text_message_segment(message, seg)
                        elif isinstance(seg, SegAt):  # SegAt 对象
                            message.append(MessageSegment.at(user_id=seg.platform_user_id))

            elif segment.type == PlatformSendSegmentType.AT:
                if segment.at_info:
                    message.append(MessageSegment.at(user_id=segment.at_info.platform_user_id))
            elif segment.type == PlatformSendSegmentType.IMAGE:
                # 图片以富文本形式发送
                if segment.file_path:
                    file_path = Path(segment.file_path)
                    if file_path.exists():
                        message.append(MessageSegment.image(file=file_path.read_bytes()))
                    else:
                        message.append(MessageSegment.text(f"Image file not found: {segment.file_path}"))
            else:
                logger.warning(f"Unsupported segment type in normal mode: {segment.type}")

        if message:
            return await self._send_to_chat_with_retry(request.chat_key, message)
        return None

    def _append_text_message_segment(self, message: Message, text: str) -> None:
        """按配置决定普通文本中的 CQ 码是否解析为 OneBot 消息段。"""

        if not self.config.RESOLVE_CQ_CODE:
            message.append(MessageSegment.text(text))
            return

        for segment in Message(text):
            message.append(segment)

    async def _send_files(self, chat_key: str, file_segments: List) -> None:
        """发送文件（物化到 uploads 目录后通过 OneBot 文件上传 API 发送）"""
        bot: Bot = get_bot()
        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        chat_id = int(db_chat_channel.channel_id.split("_")[1])

        from nekro_agent.tools.common_util import copy_to_upload_dir

        def _get_onebot_path(local_path: Path) -> Path:
            """若配置了协议端挂载目录，将本地路径转换为协议端可访问路径"""
            if config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR:
                return Path(config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR) / local_path.relative_to(Path(OsEnv.DATA_DIR))
            return local_path

        for segment in file_segments:
            if not segment.file_path:
                continue

            src_path = Path(segment.file_path)
            if not src_path.exists():
                logger.warning(f"File not found: {segment.file_path}")
                continue

            copied_path, copied_name = await copy_to_upload_dir(
                file_path=str(src_path),
                file_name=src_path.name,
                from_chat_key=chat_key,
            )
            logger.info(f"文件已物化至: {copied_path}")

            onebot_path = _get_onebot_path(Path(copied_path))
            if db_chat_channel.chat_type == ChatType.GROUP:
                await bot.upload_group_file(
                    group_id=chat_id,
                    file=str(onebot_path),
                    name=copied_name,
                )
            elif db_chat_channel.chat_type == ChatType.PRIVATE:
                await bot.upload_private_file(
                    user_id=chat_id,
                    file=str(onebot_path),
                    name=copied_name,
                )
            else:
                logger.warning(f"不支持的聊天类型，文件发送跳过: {db_chat_channel.chat_type}")

    async def _send_to_chat(self, chat_key: str, message: Message) -> str:
        """发送消息到指定聊天"""
        bot: Bot = get_bot()

        # 获取聊天频道信息
        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        chat_type = db_chat_channel.chat_type

        # 从channel_id中提取真实的ID
        chat_id = int(db_chat_channel.channel_id.split("_")[1])

        if chat_type is ChatType.GROUP:
            ret = await bot.send_group_msg(group_id=chat_id, message=message, auto_escape=self.config.RESOLVE_CQ_CODE)
        elif chat_type is ChatType.PRIVATE:
            ret = await bot.send_private_msg(user_id=chat_id, message=message, auto_escape=self.config.RESOLVE_CQ_CODE)
        else:
            raise ValueError("Invalid chat type")

        logger.debug(f"发送消息成功: {ret}")
        return str(ret.get("message_id", "")) or ""

    async def _send_to_chat_with_retry(self, chat_key: str, message: Message) -> str:
        """带指数退避重试的发送包装器，用于应对 NapCat WebSocket 1006 异常关闭。

        触发场景：NTQQ 进程掉线 / NapCat ↔ NTQQ 短暂断连 / 网络抖动
        重试策略：3 / 6 / 12 秒，最多 3 次（总耗时 ≤ 21 秒）
        异常吞咽：仅吞咽 OneBotNetworkError（WebSocket 关闭、连接超时等）
        其余异常（ActionFailed / ValueError 等业务错误）立即抛出，避免掩盖真实问题。
        """
        _MAX_RETRIES = 3
        _BASE_BACKOFF_SECONDS = 3

        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return await self._send_to_chat(chat_key, message)
            except OneBotNetworkError as e:
                last_error = e
                if attempt >= _MAX_RETRIES:
                    logger.error(
                        f"[OneBot] 发送消息失败，已重试 {_MAX_RETRIES} 次仍失败: {e!s}"
                    )
                    raise
                wait_seconds = _BASE_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    f"[OneBot] 网络异常（attempt {attempt + 1}/{_MAX_RETRIES}），"
                    f"等待 {wait_seconds}s 后重试: {e!s}"
                )
                await asyncio.sleep(wait_seconds)

        # 理论上不会执行到这里（循环要么 return 要么 raise），加防御性兜底
        if last_error is not None:
            raise last_error
        raise RuntimeError("_send_to_chat_with_retry: unexpected retry loop exit")

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        bot: Bot = get_bot()
        if bot:
            logger.info(f"Self_id:{bot.self_id} user_name:{bot.self_id}")
            return PlatformUser(platform_name="QQ", user_id=str(bot.self_id), user_name=bot.self_id)
        raise ValueError("No bot found")

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户(或者群聊用户)信息"""
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        chat_type = get_channel_type(channel_id)
        if chat_type == ChatType.GROUP:
            try:
                channel_name = (await get_bot().get_group_info(group_id=int(channel_id.replace("group_", ""))))["group_name"]
            except Exception as e:
                logger.error(f"获取群组名称失败: {e!s}")
                channel_name = channel_id
        elif chat_type == ChatType.PRIVATE:
            channel_name = (await get_bot().get_stranger_info(user_id=int(channel_id.replace("private_", ""))))["nickname"]
        else:
            channel_name = channel_id

        return PlatformChannel(channel_id=channel_id, channel_name=channel_name, channel_type=chat_type)

    async def send_poke(self, chat_key: str, target_user_id: str) -> bool:
        """发送戳一戳

        Args:
            chat_key: 聊天频道 key
            target_user_id: 被戳用户的 platform_userid (QQ号)

        Returns:
            bool: 是否成功
        """
        try:
            bot: Bot = get_bot()
            db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
            chat_type = db_chat_channel.chat_type
            uid = int(target_user_id)

            if chat_type is ChatType.GROUP:
                gid = int(db_chat_channel.channel_id.split("_")[1])
                await bot.call_api("group_poke", group_id=gid, user_id=uid)
            elif chat_type is ChatType.PRIVATE:
                await bot.call_api("friend_poke", user_id=uid)
            else:
                logger.warning(f"不支持的聊天类型: {chat_type}")
                return False
        except Exception as e:
            logger.error(f"发送戳一戳失败: {e}")
            return False
        else:
            return True

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:
        """设置消息反应（NoneBot 实现）

        Args:
            message_id (str): 消息ID
            status (bool): True为设置反应，False为取消反应

        Returns:
            bool: 是否成功设置
        """
        try:
            bot: Bot = get_bot()
            await bot.call_api(
                "set_msg_emoji_like",
                message_id=int(message_id),
                emoji_id="212",
                set="true" if status else "false",
            )
        except Exception as e:
            logger.error(f"设置消息emoji失败: {e} | 如果协议端不支持该功能，请关闭配置 `SESSION_PROCESSING_WITH_EMOJI`")
            return False
        else:
            return True
