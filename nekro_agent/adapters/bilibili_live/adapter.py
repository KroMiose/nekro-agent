import asyncio
import hashlib
import re
from typing import List, Optional

from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformUser,
)
from nekro_agent.core import logger
from nekro_agent.core.config import config
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)
from nekro_agent.tools.common_util import (
    copy_to_upload_dir,
    download_file,
)

from .core.client import BilibiliWebSocketClient, Danmaku


class BilibiliLiveAdapter(BaseAdapter):
    """Bilibili 直播适配器"""

    def __init__(self):
        super().__init__()
        self.ws_clients: List[BilibiliWebSocketClient] = []
        self.ws_tasks: List[asyncio.Task] = []

    @property
    def key(self) -> str:
        return "bilibili-live"

    @property
    def chat_key_rules(self) -> List[str]:
        # Bilibili直播间的聊天Key规则: bilibili-live-{room_id}
        return [
            "LiveRoom chat: `bilibili-live-114514` (where room_id is the id of the Bilibili live room)",
        ]

    async def init(self) -> None:
        """初始化适配器"""
        if not config.VTUBE_STUDIO_CONTROLLER_WS_URL:
            logger.warning(
                "未设置VTUBE_STUDIO_CONTROLLER_WS_URL 取消加载 Bilibili 直播适配器",
            )
            return

        # 为每个WebSocket URL创建客户端连接
        for ws_url in config.VTUBE_STUDIO_CONTROLLER_WS_URL:
            try:
                client = BilibiliWebSocketClient(ws_url, self._handle_danmaku_message)
                self.ws_clients.append(client)
                
                # 创建异步任务来运行WebSocket客户端
                task = asyncio.create_task(client.start_with_auto_reconnect())
                self.ws_tasks.append(task)
                
                logger.info(f"已创建Bilibili WebSocket连接任务: {ws_url}")
                
            except Exception as e:
                logger.error(f"创建Bilibili WebSocket客户端失败 {ws_url}: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        # 取消所有WebSocket任务
        for task in self.ws_tasks:
            if not task.done():
                task.cancel()

        # 关闭所有WebSocket客户端
        for client in self.ws_clients:
            await client.close()

    async def _handle_danmaku_message(self, danmaku: Danmaku) -> None:
        """处理弹幕消息"""
        try:
            # 创建平台频道信息
            channel_id = str(danmaku.from_live_room)
            plt_channel = PlatformChannel(
                channel_id=channel_id,
                channel_name=f"Bilibili直播间{channel_id}",
                channel_type=ChatType.GROUP,
            )

            plt_user = PlatformUser(
                user_id=danmaku.uid,
                user_name=danmaku.username,
                user_avatar="",
            )

            # 构建消息内容
            content_data = []
            
            # 添加文本内容
            if danmaku.text:
                cleaned_text = self._remove_at_mentions(danmaku.text)
                if cleaned_text:
                    content_data.append(
                        ChatMessageSegment(
                            type=ChatMessageSegmentType.TEXT,
                            text=cleaned_text,
                        ),
                    )

            # 如果有图片URL，添加图片消息段
            if danmaku.url:
                for url in danmaku.url:
                    suffix = re.search(r"\.[^.]*$", url)
                    suffix = suffix.group(0) if suffix else ""
                    local_path, file_name = await download_file(
                        url,
                        use_suffix=suffix,
                        from_chat_key=f"bilibili-live-{channel_id}",
                    )
                    content_data.append(
                        ChatMessageSegmentImage(
                            type=ChatMessageSegmentType.IMAGE,
                            text="",
                            file_name=file_name,
                            local_path=local_path,
                            remote_url=url,
                        ),
                    )

            # 生成消息ID
            message_id = f"bilibili_{channel_id}_{danmaku.uid}_{int(danmaku.time)}"

            # 创建平台消息
            plt_message = PlatformMessage(
                message_id=message_id,
                sender_id=danmaku.uid,
                sender_name=danmaku.username,
                sender_nickname=danmaku.username,
                content_data=content_data,
                content_text=danmaku.text,
                is_tome=danmaku.is_trigget,  # 根据is_trigget字段决定是否触发AI
                timestamp=danmaku.time,                is_self=False,
            )

            logger.info(f"Bilibili弹幕消息: [{channel_id}] {danmaku.username}: {danmaku.text}")

            # 推送消息到collect_message
            await collect_message(self, plt_channel, plt_user, plt_message)

        except Exception as e:
            logger.error(f"处理Bilibili弹幕消息失败: {e}")

        self.ws_clients.clear()
        self.ws_tasks.clear()
        logger.info("Bilibili适配器资源清理完成")

    def _remove_at_mentions(self, text: str) -> str:
        """移除文本中的特定格式的 @ 提及 (例如 [@id:123;nickname:test@] 或 [@id:123@])"""
        processed_text = re.sub(r"\[@(?:id:[^;@]+(?:;nickname:[^@]+)?|[^@\]]+)@\]", "", text)
        # 将多个空格替换为单个空格，并去除首尾空格
        return re.sub(r"\s+", " ", processed_text).strip()

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:  # noqa: ARG002
        """推送消息到Bilibili协议端（暂不实现）"""
        # TODO: 实现向Bilibili直播间发送消息的功能
        logger.warning("Bilibili适配器暂不支持发送消息")
        return PlatformSendResponse(success=False, error_message="暂不支持发送消息")

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        return PlatformUser(user_id="BilibiliLiveBot", user_name="BilibiliLiveBot")

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:  # noqa: ARG002
        """获取用户(或者群聊用户)信息"""
        # TODO: 实现获取用户信息的功能
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        return PlatformChannel(
            channel_id=channel_id, 
            channel_name=f"Bilibili直播间{channel_id}", 
            channel_type=ChatType.GROUP,
        )

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:  # noqa: ARG002
        """设置消息反应（可选实现）"""
        return True
