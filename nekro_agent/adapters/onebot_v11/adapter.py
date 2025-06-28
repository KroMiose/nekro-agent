from pathlib import Path
from typing import List, Optional, Type

from fastapi import APIRouter
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
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
from nekro_agent.schemas.chat_message import ChatType

from ..interface.base import AdapterMetadata, BaseAdapter, BaseAdapterConfig
from .core.bot import get_bot
from .tools.at_parser import SegAt, parse_at_from_text
from .tools.convertor import get_channel_type


class OnebotV11Config(BaseAdapterConfig):
    """Onebot V11 适配器配置"""

    BOT_QQ: str = Field(
        default="",
        title="机器人 QQ 号",
        json_schema_extra=ExtraField(required=True).model_dump(),
    )
    RESOLVE_CQ_CODE: bool = Field(
        default=False,
        title="是否解析 CQ 码",
        description="启用后，AI 发送的消息中的 CQ 码不再被视为纯文本，而是会被协议实现端解析为对应的富文本消息",
    )

    """NAPCAT 配置"""
    NAPCAT_ACCESS_URL: str = Field(
        default="http://127.0.0.1:6099/webui",
        title="NapCat WebUI 访问地址",
        description="NapCat 的 WebUI 地址，请确保对应端口已开放访问",
        json_schema_extra=ExtraField(placeholder="例: http://<服务器 IP>:<NapCat 端口>/webui").model_dump(),
    )
    NAPCAT_CONTAINER_NAME: str = Field(default="nekro_napcat", title="NapCat 容器名称")


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
            author="NekroAgent",
            homepage="https://github.com/nekro-agent/nekro-agent",
            tags=["qq", "onebot", "v11", "chat", "messaging"],
        )

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
                    # NoneBot 特有功能：解析文本中的 @ 信息
                    seg_data = await parse_at_from_text(segment.content, db_chat_channel)

                    for seg in seg_data:
                        if isinstance(seg, str):
                            if seg.strip():
                                message.append(MessageSegment.text(seg))
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
            return await self._send_to_chat(request.chat_key, message)
        return None

    async def _send_files(self, chat_key: str, file_segments: List) -> None:
        """发送文件（文件上传模式）"""
        bot: Bot = get_bot()
        files: List[Path] = []

        # 收集所有文件路径
        for segment in file_segments:
            if segment.file_path:
                file_path = Path(segment.file_path)
                if file_path.exists():
                    files.append(file_path)
                else:
                    logger.warning(f"File not found: {segment.file_path}")

        if not files:
            logger.warning("No valid files to send")
            return

        # 获取聊天频道信息
        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        chat_type = db_chat_channel.chat_type

        # 从channel_id中提取真实的ID
        chat_id = int(db_chat_channel.channel_id.split("_")[1])

        # 如果配置了 OneBot 服务器挂载目录，需要转换路径
        def get_onebot_path(file_path: Path) -> Path:
            if config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR:
                return Path(config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR) / file_path.relative_to(Path(OsEnv.DATA_DIR))
            return file_path

        if chat_type is ChatType.GROUP:
            for file in files:
                logger.info(f"Sending file: {file}")
                onebot_path = get_onebot_path(file)
                await bot.upload_group_file(
                    group_id=chat_id,
                    file=str(onebot_path),
                    name=file.name,
                )
        elif chat_type is ChatType.PRIVATE:
            for file in files:
                onebot_path = get_onebot_path(file)
                await bot.upload_private_file(
                    user_id=chat_id,
                    file=str(onebot_path),
                    name=file.name,
                )
        else:
            raise ValueError("Invalid chat type")

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
