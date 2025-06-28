import asyncio
import hashlib
import re
from typing import Dict, List, Optional, Type

from jinja2 import Environment, FileSystemLoader
from pydantic import Field

from nekro_agent.adapters.bilibili_live.templates.practice import (
    PracticePrompt_question_1,
    PracticePrompt_question_2,
    PracticePrompt_response_1,
    PracticePrompt_response_2,
)
from nekro_agent.adapters.interface.base import (
    AdapterMetadata,
    BaseAdapter,
    BaseAdapterConfig,
)
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
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)
from nekro_agent.services.agent.templates.base import PromptTemplate
from nekro_agent.tools.common_util import (
    copy_to_upload_dir,
    download_file,
)

from .core.client import BilibiliWebSocketClient, Danmaku


class BilibiliLiveConfig(BaseAdapterConfig):
    """Bilibili 适配器配置"""

    VTUBE_STUDIO_CONTROLLER_WS_URL: List[str] = Field(
        default=[],
        title="VTube Studio 控制端 WebSocket 地址",
        description="VTube Studio 控制端 WebSocket 地址，用于控制 VTube Studio",
    )


class BilibiliLiveAdapter(BaseAdapter[BilibiliLiveConfig]):
    """Bilibili 直播适配器"""

    def __init__(self, config_cls: Type[BilibiliLiveConfig] = BilibiliLiveConfig):
        super().__init__(config_cls)
        self.ws_clients: List[BilibiliWebSocketClient] = []
        self.ws_tasks: List[asyncio.Task] = []
        self.room_to_ws: Dict[str, BilibiliWebSocketClient] = {}

    @property
    def key(self) -> str:
        return "bilibili_live"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="Bilibili Live",
            description="Bilibili 直播适配器，实时接收直播间弹幕消息、礼物信息和用户互动事件",
            version="1.0.0",
            author="Zaxpris",
            homepage="https://github.com/nekro-agent/nekro-agent",
            tags=["bilibili", "live", "stream", "danmaku", "realtime"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        # Bilibili直播间的聊天Key规则: bilibili_live-{room_id}
        return [
            "LiveRoom chat: `bilibili_live-114514` (where room_id is the id of the Bilibili live room)",
        ]

    async def init(self) -> None:
        """初始化适配器"""
        if not self.config.VTUBE_STUDIO_CONTROLLER_WS_URL:
            logger.warning(
                "未设置VTUBE_STUDIO_CONTROLLER_WS_URL 取消加载 Bilibili 直播适配器",
            )
            return

        # 为每个WebSocket URL创建客户端连接
        for ws_url in self.config.VTUBE_STUDIO_CONTROLLER_WS_URL:
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

        self.ws_clients.clear()
        self.ws_tasks.clear()
        self.room_to_ws.clear()
        logger.info("Bilibili适配器资源清理完成")

    async def set_dialog_example(self) -> Optional[List[PromptTemplate]]:
        return [
            PracticePrompt_question_1(one_time_code=""),
            PracticePrompt_question_2(one_time_code=""),
            PracticePrompt_response_1(one_time_code="", enable_cot=False, enable_at=False),
            PracticePrompt_response_2(one_time_code="", enable_cot=False, enable_at=False),
        ]

    async def get_jinja_env(self) -> Optional[Environment]:
        """返回jinja模板"""
        return Environment(loader=FileSystemLoader("nekro_agent/adapters/bilibili_live/templates"), auto_reload=False)

    async def _handle_danmaku_message(self, client: BilibiliWebSocketClient, danmaku: Danmaku) -> None:
        """处理弹幕消息"""
        try:
            # 动态建立房间ID到WebSocket客户端的映射
            channel_id = str(danmaku.from_live_room)
            if channel_id and channel_id not in self.room_to_ws:
                self.room_to_ws[channel_id] = client
                logger.info(f"动态映射Bilibili直播间 {channel_id} 到WebSocket客户端")

            # 创建平台频道信息
            plt_channel = PlatformChannel(
                channel_id=channel_id,
                channel_name=f"Bilibili直播间{channel_id}",
                channel_type=ChatType.GROUP,
            )

            plt_user = PlatformUser(
                platform_name="Bilibili",
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
                        from_chat_key=f"bilibili_live-{channel_id}",
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
                is_tome=danmaku.is_trigger,  # 根据is_trigger字段决定是否触发AI
                timestamp=danmaku.time,
                is_self=False,
            )

            logger.info(f"Bilibili弹幕消息: [{channel_id}] {danmaku.username}: {danmaku.text}")

            # 推送消息到collect_message
            await collect_message(self, plt_channel, plt_user, plt_message)

        except Exception as e:
            logger.error(f"处理Bilibili弹幕消息失败: {e}")

    def _remove_at_mentions(self, text: str) -> str:
        """移除文本中的特定格式的 @ 提及 (例如 [@id:123;nickname:test@] 或 [@id:123@])"""
        processed_text = re.sub(r"\[@(?:id:[^;@]+(?:;nickname:[^@]+)?|[^@\]]+)@\]", "", text)
        # 将多个空格替换为单个空格，并去除首尾空格
        return re.sub(r"\s+", " ", processed_text).strip()

    def get_ws_client_by_room_id(self, room_id: str) -> Optional[BilibiliWebSocketClient]:
        """通过房间ID获取对应的WebSocket客户端实例

        Args:
            room_id: Bilibili直播间ID

        Returns:
            对应的WebSocket客户端实例，如果不存在则返回None
        """
        return self.room_to_ws.get(room_id)

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:  # noqa: ARG002
        """推送消息到Bilibili协议端（暂不实现）"""
        # TODO: 实现向Bilibili直播间发送消息的功能
        logger.warning("Bilibili适配器暂不支持发送消息")
        return PlatformSendResponse(success=False, error_message="暂不支持发送消息")

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        return PlatformUser(platform_name="Bilibili", user_id="BilibiliAnchor", user_name="BilibiliAnchor")

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
