from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from .config import WeChatILinkMultiConfig
from .schemas import (
    BindPollResult,
    BindStartResult,
    ContextToken,
    OpenILinkCredentials,
    OpenILinkMedia,
    OpenILinkMessage,
    OpenILinkRecipient,
    RenewResult,
    SendMessageResult,
    SyncState,
)

MediaDownloadResult: TypeAlias = bytes | Path
MessageCallback: TypeAlias = Callable[[OpenILinkMessage], Awaitable[None]]
SyncStateCallback: TypeAlias = Callable[[SyncState], Awaitable[None]]
ErrorCallback: TypeAlias = Callable[[Exception], Awaitable[None]]


@dataclass(slots=True)
class OpenILinkMonitorCallbacks:
    """OpenILink 监控连接回调集合。"""

    on_message: MessageCallback
    on_sync_state: SyncStateCallback | None = None
    on_error: ErrorCallback | None = None


class OpenILinkMultiClient(ABC):
    """OpenILink 多实例协议客户端边界。"""

    def __init__(self, config: WeChatILinkMultiConfig):
        self.config = config

    @abstractmethod
    async def start_bind(self) -> BindStartResult:
        """启动一次账号绑定流程。"""

    @abstractmethod
    async def poll_bind(self, session_id: str) -> BindPollResult:
        """轮询绑定会话状态。"""

    @abstractmethod
    async def start_monitor(
        self,
        credentials: OpenILinkCredentials,
        sync_state: SyncState,
        callbacks: OpenILinkMonitorCallbacks,
    ) -> None:
        """基于指定账号凭据启动一条消息监控连接。"""

    @abstractmethod
    async def stop_monitor(self) -> None:
        """停止当前客户端实例持有的监控连接。"""

    @abstractmethod
    async def send_text(
        self,
        recipient: OpenILinkRecipient,
        text: str,
        context_token: ContextToken,
    ) -> SendMessageResult:
        """发送文本消息。"""

    @abstractmethod
    async def send_file(
        self,
        recipient: OpenILinkRecipient,
        file_path: Path,
        context_token: ContextToken,
    ) -> SendMessageResult:
        """发送本地文件。"""

    @abstractmethod
    async def download_media(self, media: OpenILinkMedia) -> MediaDownloadResult:
        """下载媒体，返回内存字节或本地缓存路径。"""

    @abstractmethod
    async def renew_session(
        self,
        credentials: OpenILinkCredentials,
        sync_state: SyncState,
    ) -> RenewResult:
        """续期账号会话并返回新的同步状态。"""


class UnsupportedOpenILinkMultiClient(OpenILinkMultiClient):
    """尚未绑定具体传输实现时使用的显式占位客户端。"""

    async def start_bind(self) -> BindStartResult:
        raise NotImplementedError("OpenILink multi-instance transport is not configured")

    async def poll_bind(self, session_id: str) -> BindPollResult:
        raise NotImplementedError("OpenILink multi-instance transport is not configured")

    async def start_monitor(
        self,
        credentials: OpenILinkCredentials,
        sync_state: SyncState,
        callbacks: OpenILinkMonitorCallbacks,
    ) -> None:
        raise NotImplementedError("OpenILink multi-instance transport is not configured")

    async def stop_monitor(self) -> None:
        raise NotImplementedError("OpenILink multi-instance transport is not configured")

    async def send_text(
        self,
        recipient: OpenILinkRecipient,
        text: str,
        context_token: ContextToken,
    ) -> SendMessageResult:
        raise NotImplementedError("OpenILink multi-instance transport is not configured")

    async def send_file(
        self,
        recipient: OpenILinkRecipient,
        file_path: Path,
        context_token: ContextToken,
    ) -> SendMessageResult:
        raise NotImplementedError("OpenILink multi-instance transport is not configured")

    async def download_media(self, media: OpenILinkMedia) -> MediaDownloadResult:
        raise NotImplementedError("OpenILink multi-instance transport is not configured")

    async def renew_session(
        self,
        credentials: OpenILinkCredentials,
        sync_state: SyncState,
    ) -> RenewResult:
        raise NotImplementedError("OpenILink multi-instance transport is not configured")
