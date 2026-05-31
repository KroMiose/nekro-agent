from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import Protocol

from email.mime.multipart import MIMEMultipart


@dataclass
class EmailSendRequest:
    from_address: str
    to_address: str
    subject: str
    text_content: str


@dataclass
class EmailRawContent:
    raw_email_base64: str
    raw_email_size: int
    html_content: str
    text_content: str


class EmailClient(Protocol):
    account_username: str

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def select_mailbox(self, preferred: str = "INBOX", override_folder: str | None = None) -> str: ...

    async def list_message_ids(self, unseen_only: bool) -> list[bytes]: ...

    async def fetch_raw_message(self, email_id: bytes) -> bytes | None: ...

    async def mark_seen(self, email_id: bytes) -> None: ...

    async def get_raw_email_content(self, email_id: str, folder: str | None = None) -> EmailRawContent: ...

    async def send_message(self, message: MIMEMultipart) -> None: ...

    async def download_attachment(self, part: Message, filename: str, target_path: Path) -> None: ...
