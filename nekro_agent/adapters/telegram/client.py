"""
Telegram 客户端实现
"""

from typing import TYPE_CHECKING, Optional, List, Any
from pathlib import Path
import re
import time

from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.extra import PlatformMessageExt
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformMessage,
)
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)

if TYPE_CHECKING:
    from .adapter import TelegramAdapter

# 延迟导入 pyrogram，以避免在未安装依赖时阻断整个应用
Client: Any = None
filters: Any = None
TelegramMessage: Any = None

def _ensure_pyrogram_loaded():
    global Client, filters, TelegramMessage
    if Client is not None:
        return True
    try:
        from pyrogram import Client as _Client, filters as _filters  # type: ignore
        from pyrogram.types import Message as _TelegramMessage  # type: ignore
        Client = _Client  # type: ignore
        filters = _filters  # type: ignore
        TelegramMessage = _TelegramMessage  # type: ignore
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "未安装 pyrogram/tgcrypto，Telegram 适配器将被跳过。请安装依赖: pip install pyrogram tgcrypto. 错误: %s",
            str(e),
        )
        return False


class TelegramClient:
    """
    一个用于管理与 Telegram 连接的客户端。
    """

    def __init__(self, adapter: "TelegramAdapter"):
        self._adapter = adapter
        self._config = adapter.config
        self._client = None
        self._bot_username = None

        # 如果配置了代理，设置代理参数
        self._proxy_dict = None
        if getattr(self._config, "PROXY_URL", ""):
            try:
                proxy_url = str(self._config.PROXY_URL or "").strip()
                m = re.match(r"^(?P<scheme>\w+?)://(?P<host>[^:]+):(?P<port>\d+)$", proxy_url)
                if m:
                    self._proxy_dict = {
                        "scheme": m.group("scheme"),
                        "hostname": m.group("host"),
                        "port": int(m.group("port")),
                    }
                    if getattr(self._config, "PROXY_USERNAME", "") and getattr(self._config, "PROXY_PASSWORD", ""):
                        self._proxy_dict["username"] = self._config.PROXY_USERNAME
                        self._proxy_dict["password"] = self._config.PROXY_PASSWORD
                else:
                    logger.warning("Telegram 代理地址格式不正确，应为 schema://host:port，例如 socks5://127.0.0.1:7890")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"解析 Telegram 代理配置失败: {e}")

    async def start(self):
        """启动 Telegram 客户端"""
        # 1) 校验依赖
        if not _ensure_pyrogram_loaded():
            return  # 已记录日志

        # 2) 校验配置
        if not getattr(self._config, "BOT_TOKEN", ""):
            logger.warning("Telegram 未启用，需要设置 BOT_TOKEN")
            return

        # API_ID / API_HASH 在 Pyrogram 的 Bot 模式通常是必须的
        api_id = getattr(self._config, "API_ID", "") or None
        api_hash = getattr(self._config, "API_HASH", "") or None
        if not api_id or not api_hash:
            logger.error("Telegram 启动失败: 需要在 data/configs/telegram/config.yaml 中配置 API_ID 和 API_HASH")
            return
        try:
            api_id = int(api_id)  # 允许字符串数字
        except Exception:  # noqa: BLE001
            logger.error("Telegram API_ID 必须是数字，当前值: %s", str(self._config.API_ID))
            return

        try:
            # 创建客户端实例
            self._client = Client(
                name=self._config.SESSION_FILE,
                bot_token=self._config.BOT_TOKEN,
                api_id=api_id,
                api_hash=api_hash,
                proxy=self._proxy_dict if self._proxy_dict else None
            )

            # 设置事件处理
            self._setup_events()

            # 启动客户端
            await self._client.start()
            try:
                me = await self._client.get_me()
                self._bot_username = getattr(me, "username", None)
            except Exception:
                self._bot_username = None
            logger.success("Telegram Bot 已成功启动")

        except Exception as e:
            logger.error(f"启动 Telegram Bot 失败: {str(e)}")
            self._client = None

    async def stop(self):
        """停止 Telegram 客户端"""
        if self._client:
            await self._client.stop()
            logger.info("Telegram Bot 已停止")

    def _setup_events(self):
        """设置事件处理器"""
        if not self._client or not _ensure_pyrogram_loaded():
            return

        @self._client.on_message(filters.text | filters.document | filters.photo)
        async def handle_message(client: Any, message: Any):
            # 忽略来自 bot 自身的消息（如果配置了API_ID和API_HASH）
            if message.from_user and message.from_user.is_self:
                return

            # 检查是否允许该用户或群组
            if not self._check_permission(message):
                logger.debug(f"拒绝处理来自未授权用户/群组的消息: {message.from_user.id if message.from_user else 'unknown'}")
                return

            # 构建聊天键
            chat_id = str(message.chat.id)
            chat_key = self._adapter.build_chat_key(chat_id)
            segments: List[ChatMessageSegment] = []
            content_text = message.text or message.caption or ""

            # 处理图片
            if message.photo:
                # 获取最大尺寸的图片
                largest_photo = max(message.photo, key=lambda p: p.file_size)
                file_id = largest_photo.file_id

                # 获取文件路径
                file_path = await self._get_file_path(file_id)
                if file_path:
                    segment = await ChatMessageSegmentImage.create_form_local_path(
                        local_path=file_path,
                        from_chat_key=chat_key,
                        file_name=f"{file_id}.jpg",
                        use_suffix=".jpg",
                    )
                    segments.append(segment)

            # 处理文档/文件
            elif message.document:
                file_id = message.document.file_id
                file_name = message.document.file_name or f"{file_id}"

                # 获取文件路径
                file_path = await self._get_file_path(file_id)
                if file_path:
                    segment = await ChatMessageSegmentFile.create_form_local_path(
                        local_path=file_path,
                        from_chat_key=chat_key,
                        file_name=file_name,
                    )
                    segments.append(segment)

            # 处理文本内容
            if content_text:
                segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=content_text))

            if not segments:
                logger.debug("空消息，已忽略")
                return

            # 检查是否被@
            is_tome = False
            if message.text and self._bot_username and f"@{self._bot_username}" in message.text:
                is_tome = True

            # 创建平台消息对象
            platform_message = PlatformMessage(
                message_id=str(message.id),
                sender_id=str(message.from_user.id) if message.from_user else "unknown",
                sender_name=message.from_user.first_name if message.from_user else "unknown",
                sender_nickname=message.from_user.username if message.from_user and message.from_user.username else "",
                sender_avatar="",  # Telegram API 不直接提供头像URL，需要单独获取
                content_data=segments,
                content_text=content_text,
                is_tome=is_tome,
                timestamp=int(time.time()),
                is_self=False,
                ext_data=PlatformMessageExt()
            )

            # 构建平台用户与频道信息
            from nekro_agent.adapters.interface.schemas.platform import PlatformUser, PlatformChannel

            platform_user = PlatformUser(
                platform_name=self._adapter.key,
                user_id=str(message.from_user.id) if message.from_user else "unknown",
                user_name=message.from_user.first_name if message.from_user else "unknown",
                user_avatar="",
            )
            channel_type = ChatType.PRIVATE if getattr(message.chat, "type", "private") == "private" else ChatType.GROUP
            platform_channel = PlatformChannel(
                channel_id=chat_id,
                channel_name=getattr(message.chat, "title", "") or getattr(message.chat, "username", "") or chat_id,
                channel_type=channel_type,
                channel_avatar="",
            )

            # 收集消息
            await collect_message(self._adapter, platform_channel, platform_user, platform_message)

    async def _get_file_path(self, file_id: str) -> Optional[str]:
        """获取文件的本地路径，保存到 data/uploads/telegram 目录"""
        if not self._client or not _ensure_pyrogram_loaded():
            return None

        try:
            from nekro_agent.core.os_env import USER_UPLOAD_DIR

            save_dir = Path(USER_UPLOAD_DIR) / "telegram"
            save_dir.mkdir(parents=True, exist_ok=True)
            # 使用 pyrogram 的下载方法
            file_path = await self._client.download_media(file_id, file_name=str(save_dir / f"{file_id}"))
            return str(file_path) if file_path else None
        except Exception as e:  # noqa: BLE001
            logger.error(f"获取文件失败: {str(e)}")
            return None

    def _check_permission(self, message: Any) -> bool:
        """检查用户或群组是否有权限使用机器人"""
        # 如果没有设置允许列表，则允许所有
        if not self._config.ALLOWED_USERS and not self._config.ALLOWED_CHATS:
            return True

        # 检查用户权限
        if message.from_user and str(message.from_user.id) in self._config.ALLOWED_USERS:
            return True

        # 检查群组权限
        if message.chat.id != message.from_user.id:  # 不是私聊
            if str(message.chat.id) in self._config.ALLOWED_CHATS:
                return True

        return False

    async def send_message(self, chat_id: str, text: str = "", files: Optional[List[str]] = None) -> bool:
        """发送消息到指定聊天"""
        if not self._client:
            return False

        try:
            # 处理消息长度限制
            if len(text) > self._config.MAX_MESSAGE_LENGTH:
                # 分段发送消息
                messages = self._split_message(text)
                for msg in messages:
                    await self._client.send_message(chat_id=chat_id, text=msg)
            else:
                await self._client.send_message(chat_id=chat_id, text=text)

            # 发送文件
            if files:
                for file_path in files:
                    # 根据文件类型选择发送方式
                    if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        await self._client.send_photo(chat_id=chat_id, photo=file_path)
                    else:
                        await self._client.send_document(chat_id=chat_id, document=file_path)

            return True
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return False

    def _split_message(self, text: str) -> List[str]:
        """将长消息分割成符合 Telegram 长度限制的消息"""
        messages = []
        current_message = ""
        words = text.split(' ')
        
        for word in words:
            if len(current_message) + len(word) + 1 > self._config.MAX_MESSAGE_LENGTH:
                messages.append(current_message)
                current_message = word
            else:
                if current_message:
                    current_message += " " + word
                else:
                    current_message = word
        
        if current_message:
            messages.append(current_message)
        
        return messages