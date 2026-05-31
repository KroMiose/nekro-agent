import base64
import email
from email.message import Message
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from nekro_agent.adapters.email.config import EmailAccount

from .base import EmailRawContent
from .oauth import OAuthTokenManager, _httpx_client_kwargs


class _ApiClientBase:
    def __init__(self, account: EmailAccount, oauth_proxy: str = ""):
        self.account = account
        self.account_username = account.USERNAME
        self.oauth_proxy = oauth_proxy
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
    _GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    async def list_message_ids(self, unseen_only: bool) -> list[bytes]:
        params: dict[str, Any] = {
            "$select": "id",
            "$orderby": "receivedDateTime desc",
            "$top": "50",
        }
        if unseen_only:
            params["$filter"] = "isRead eq false"

        payload = await self._graph_request_json(
            "GET",
            "/me/mailFolders/inbox/messages",
            params=params,
        )
        messages = payload.get("value", [])
        if not isinstance(messages, list):
            return []
        ids: list[bytes] = []
        for item in messages:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]).encode("utf-8"))
        return ids

    async def fetch_raw_message(self, email_id: bytes) -> bytes | None:
        message_id = self._decode_message_id(email_id)
        response = await self._graph_request("GET", f"/me/messages/{quote(message_id, safe='')}/$value")
        return response.content or None

    async def mark_seen(self, email_id: bytes) -> None:
        message_id = self._decode_message_id(email_id)
        await self._graph_request(
            "PATCH",
            f"/me/messages/{quote(message_id, safe='')}",
            json={"isRead": True},
        )

    async def get_raw_email_content(self, email_id: str, folder: str | None = None) -> EmailRawContent:
        raw_email_data = await self.fetch_raw_message(email_id.encode("utf-8"))
        raw_email_base64 = base64.b64encode(raw_email_data).decode("utf-8") if raw_email_data else ""
        html_content = ""
        text_content = ""
        if raw_email_data:
            email_message = email.message_from_bytes(raw_email_data)
            html_content, text_content = self._extract_body(email_message)
        return EmailRawContent(
            raw_email_base64=raw_email_base64,
            raw_email_size=len(raw_email_data) if raw_email_data else 0,
            html_content=html_content,
            text_content=text_content,
        )

    async def _graph_request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        access_token = await self.token_manager.get_access_token()
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {access_token}"
        url = f"{self._GRAPH_BASE_URL}{path}"
        async with httpx.AsyncClient(**_httpx_client_kwargs(self.oauth_proxy)) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response

    async def _graph_request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._graph_request(method, path, **kwargs)
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _decode_message_id(self, email_id: bytes) -> str:
        return email_id.decode("utf-8") if isinstance(email_id, bytes) else str(email_id)

    def _extract_body(self, email_message: Message) -> tuple[str, str]:
        html_content = ""
        text_content = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                ctype = part.get_content_type()
                if part.get_content_disposition() in ("attachment", "inline"):
                    continue
                if ctype in ("text/html", "text/plain"):
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        payload = part.get_payload(decode=True)
                        content = payload.decode(charset, errors="ignore") if isinstance(payload, bytes) else str(payload)
                    except Exception:
                        content = ""
                    if ctype == "text/html":
                        html_content = content
                    else:
                        text_content = content
        else:
            ctype = email_message.get_content_type()
            charset = email_message.get_content_charset() or "utf-8"
            try:
                payload = email_message.get_payload(decode=True)
                content = payload.decode(charset, errors="ignore") if isinstance(payload, bytes) else str(payload)
            except Exception:
                content = ""
            if ctype == "text/html":
                html_content = content
            elif ctype == "text/plain":
                text_content = content
        return html_content, text_content
