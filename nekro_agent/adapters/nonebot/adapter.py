from pathlib import Path
from typing import List

from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.adapters.nonebot.matchers.message import register_matcher
from nekro_agent.core import config, logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType

from ..interface.base import BaseAdapter
from .core.bot import get_bot
from .tools.at_parser import SegAt, parse_at_from_text
from .tools.convertor import get_channel_type


class NoneBotAdapter(BaseAdapter):
    """NoneBot 适配器"""

    @property
    def key(self) -> str:
        return "onebot_v11"

    async def init(self) -> None:
        """初始化适配器"""
        from . import matchers

        register_matcher(self)

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到 NoneBot 协议端"""
        # 分离文件类型和其他类型的消息段
        file_segments = [seg for seg in request.segments if seg.type == PlatformSendSegmentType.FILE]
        other_segments = [seg for seg in request.segments if seg.type != PlatformSendSegmentType.FILE]

        # 先发送文件（如果有）
        if file_segments:
            await self._send_files(request.chat_key, file_segments)

        # 再发送其他类型消息（如果有）
        if other_segments:
            modified_request = PlatformSendRequest(chat_key=request.chat_key, segments=other_segments)
            await self._send_message(modified_request)

        return PlatformSendResponse(success=True)

    async def _send_message(self, request: PlatformSendRequest) -> None:
        """发送普通消息（文本、@、图片等）"""
        message = Message()

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
            await self._send_to_chat(request.chat_key, message)

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

    async def _send_to_chat(self, chat_key: str, message: Message) -> None:
        """发送消息到指定聊天"""
        bot: Bot = get_bot()

        # 获取聊天频道信息
        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        chat_type = db_chat_channel.chat_type

        # 从channel_id中提取真实的ID
        chat_id = int(db_chat_channel.channel_id.split("_")[1])

        if chat_type is ChatType.GROUP:
            await bot.send_group_msg(group_id=chat_id, message=message)
        elif chat_type is ChatType.PRIVATE:
            await bot.send_private_msg(user_id=chat_id, message=message)
        else:
            raise ValueError("Invalid chat type")

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        return PlatformUser(user_id=str(get_bot().self_id), user_name=get_bot().self_id)

    async def get_user_info(self, user_id: str) -> PlatformUser:
        """获取用户信息"""
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
