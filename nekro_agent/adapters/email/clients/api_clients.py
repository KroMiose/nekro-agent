from email.message import Message
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from nekro_agent.adapters.email.config import EmailAccount

from .base import EmailRawContent
from .oauth import OAuthTokenManager


class _ApiClientBase:
    def __init__(self, account: EmailAccount, oauth_proxy: str = ""):
        self.account = account
        self.account_username = account.USERNAME
        self.token_manager = OAuthTokenManager(account, oauth_proxy)

    async def connect(self) -> None:
        await self.token_manager.get_access_token()

    async def close(self) -> None:
        return None

    async def select_mailbox(self, preferred: str = "INBOX", override_folder: str | None = None) -> str:
        return override_folder or preferred

    async def list_message_ids(self, unseen_only: bool) -> list[bytes]:
        raise NotImplementedError("官方 API 邮件拉取尚未实现")

    async def fetch_raw_message(self, email_id: bytes) -> bytes | None:
        raise NotImplementedError("官方 API 邮件读取尚未实现")

    async def mark_seen(self, email_id: bytes) -> None:
        raise NotImplementedError("官方 API 标记已读尚未实现")

    async def get_raw_email_content(self, email_id: str, folder: str | None = None) -> EmailRawContent:
        raise NotImplementedError("官方 API 原始邮件读取尚未实现")

    async def send_message(self, message: MIMEMultipart) -> None:
        raise NotImplementedError("官方 API 发信尚未实现")

    async def download_attachment(self, part: Message, filename: str, target_path: Path) -> None:
        raise NotImplementedError("官方 API 附件下载尚未实现")


class GmailApiClient(_ApiClientBase):
    pass


class MicrosoftGraphMailClient(_ApiClientBase):
    pass
