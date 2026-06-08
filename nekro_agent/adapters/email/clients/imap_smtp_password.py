import asyncio
import base64
import email
import imaplib
import re
import socket
import smtplib
import ssl
from contextlib import suppress
from email.message import Message
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from urllib.parse import urlparse

import aiofiles

from nekro_agent.adapters.email.base import EMAIL_PROVIDER_CONFIGS
from nekro_agent.adapters.email.config import EmailAccount

from .base import EmailRawContent


class ProxiedIMAP4SSL(imaplib.IMAP4_SSL):
    def __init__(self, host: str, port: int, proxy_url: str, timeout: int):
        self.proxy_url = proxy_url
        super().__init__(host=host, port=port, timeout=timeout)

    def _create_socket(self, timeout):
        sock = _connect_via_http_proxy(self.host, self.port, self.proxy_url, timeout)
        return self.ssl_context.wrap_socket(sock, server_hostname=self.host)


class ProxiedSMTP(smtplib.SMTP):
    def __init__(self, host: str, port: int, proxy_url: str, timeout: int):
        self.proxy_url = proxy_url
        super().__init__(host=host, port=port, timeout=timeout)

    def _get_socket(self, host, port, timeout):
        return _connect_via_http_proxy(host, port, self.proxy_url, timeout)


class ProxiedSMTPSSL(smtplib.SMTP_SSL):
    def __init__(self, host: str, port: int, proxy_url: str, timeout: int):
        self.proxy_url = proxy_url
        super().__init__(host=host, port=port, timeout=timeout)

    def _get_socket(self, host, port, timeout):
        sock = _connect_via_http_proxy(host, port, self.proxy_url, timeout)
        return self.context.wrap_socket(sock, server_hostname=host)


def _connect_via_http_proxy(host: str, port: int, proxy_url: str, timeout: int | float | None):
    parsed = urlparse(proxy_url)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError("IMAP/SMTP 代理目前仅支持 HTTP CONNECT 代理")
    if not parsed.hostname:
        raise RuntimeError("代理地址缺少主机名")
    proxy_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    raw_sock = socket.create_connection((parsed.hostname, proxy_port), timeout=timeout)
    if parsed.scheme == "https":
        raw_sock = ssl.create_default_context().wrap_socket(raw_sock, server_hostname=parsed.hostname)

    connect_target = f"{host}:{port}"
    headers = [
        f"CONNECT {connect_target} HTTP/1.1",
        f"Host: {connect_target}",
    ]
    if parsed.username or parsed.password:
        auth = f"{parsed.username or ''}:{parsed.password or ''}"
        headers.append("Proxy-Authorization: Basic " + base64.b64encode(auth.encode()).decode())
    raw_sock.sendall(("\r\n".join(headers) + "\r\n\r\n").encode())
    response = b""
    while b"\r\n\r\n" not in response:
        chunk = raw_sock.recv(4096)
        if not chunk:
            break
        response += chunk
    status_line = response.split(b"\r\n", 1)[0].decode(errors="ignore")
    if " 200 " not in status_line:
        raw_sock.close()
        raise RuntimeError(f"代理 CONNECT 失败: {status_line}")
    return raw_sock


class ImapSmtpPasswordClient:
    def __init__(self, account: EmailAccount, imap_timeout: int, proxy_url: str = ""):
        self.account = account
        self.account_username = account.USERNAME
        self.imap_timeout = imap_timeout
        self.proxy_url = proxy_url
        self.conn: imaplib.IMAP4_SSL | None = None

    async def connect(self) -> None:
        self.conn = await asyncio.to_thread(self._connect_sync)

    async def close(self) -> None:
        if not self.conn:
            return
        conn = self.conn
        self.conn = None
        await asyncio.to_thread(self._close_sync, conn)

    async def select_mailbox(self, preferred: str = "INBOX", override_folder: str | None = None) -> str:
        conn = self._require_conn()
        folders = await asyncio.to_thread(self._get_mailbox_folders_sync, conn)
        target = self._pick_mailbox(folders, preferred=preferred, override=override_folder)
        status, data = await asyncio.to_thread(conn.select, target)
        if status != "OK" and target.upper() == "INBOX":
            status, data = await asyncio.to_thread(conn.select, '"INBOX"')
        if status != "OK":
            raise RuntimeError(f"Failed to select mailbox {target} for account {self.account_username}: {data!r}")
        return target

    async def get_mailbox_folders_debug(self) -> list[str]:
        conn = self._require_conn()
        return await asyncio.to_thread(self._get_mailbox_folders_sync, conn)

    async def list_message_ids(self, unseen_only: bool) -> list[bytes]:
        conn = self._require_conn()
        criteria = "UNSEEN" if unseen_only else "ALL"
        status, messages = await asyncio.to_thread(conn.search, None, criteria)
        if status != "OK":
            raise RuntimeError(f"邮件搜索失败: {status}")
        return list(messages[0].split()) if messages else []

    async def fetch_raw_message(self, email_id: bytes) -> bytes | None:
        conn = self._require_conn()
        status, msg_data = await asyncio.to_thread(conn.fetch, email_id, "(RFC822)")
        if status != "OK":
            return None
        return msg_data[0][1] if msg_data and msg_data[0] else None

    async def mark_seen(self, email_id: bytes) -> None:
        conn = self._require_conn()
        await asyncio.to_thread(conn.store, email_id, "+FLAGS", "\\Seen")

    async def get_raw_email_content(self, email_id: str, folder: str | None = None) -> EmailRawContent:
        await self.select_mailbox(override_folder=folder)
        raw_email_data = await self.fetch_raw_message(email_id.encode() if isinstance(email_id, str) else email_id)
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

    async def send_message(self, message: MIMEMultipart) -> None:
        provider_config = self.get_provider_config()
        smtp_host = provider_config.get("smtp_host", "")
        smtp_port = int(provider_config.get("smtp_port", 587))
        smtp_ssl_port = int(provider_config.get("smtp_ssl_port", smtp_port))
        use_ssl_preferred = str(provider_config.get("smtp_use_ssl", False)).lower() == "true"
        if not smtp_host:
            raise RuntimeError(f"未找到 {self.account.EMAIL_ACCOUNT} 的SMTP配置")

        try:
            await self._send_mail(message, smtp_host, smtp_ssl_port if use_ssl_preferred else smtp_port, use_ssl_preferred)
        except Exception:
            if not use_ssl_preferred and smtp_ssl_port != smtp_port:
                await self._send_mail(message, smtp_host, smtp_ssl_port, True)
            else:
                raise

    async def download_attachment(self, part: Message, filename: str, target_path: Path) -> None:
        attachment_data = await asyncio.to_thread(part.get_payload, decode=True)
        if not attachment_data:
            raise RuntimeError(f"附件数据为空: {filename}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target_path, "wb") as f:
            await f.write(attachment_data)

    def get_provider_config(self) -> dict[str, str]:
        if self.account.EMAIL_ACCOUNT == "自定义":
            return {
                "imap_host": self.account.CUSTOM_IMAP_HOST,
                "imap_port": str(self.account.CUSTOM_IMAP_PORT),
                "smtp_host": self.account.CUSTOM_SMTP_HOST,
                "smtp_port": str(self.account.CUSTOM_SMTP_PORT),
                "smtp_ssl_port": str(self.account.CUSTOM_SMTP_SSL_PORT),
                "smtp_use_ssl": str(self.account.CUSTOM_SMTP_USE_SSL).lower(),
            }
        return EMAIL_PROVIDER_CONFIGS.get(self.account.EMAIL_ACCOUNT, {})

    def _require_conn(self) -> imaplib.IMAP4_SSL:
        if not self.conn:
            raise RuntimeError(f"账户 {self.account_username} 未连接或不存在")
        return self.conn

    def _connect_sync(self) -> imaplib.IMAP4_SSL:
        provider_config = self.get_provider_config()
        imap_host = provider_config.get("imap_host")
        if not imap_host:
            raise ValueError(f"邮箱提供商 {self.account.EMAIL_ACCOUNT} 缺少 imap_host 配置")
        imap_port = int(provider_config.get("imap_port", 993))
        if self.proxy_url:
            conn = ProxiedIMAP4SSL(imap_host, imap_port, self.proxy_url, self.imap_timeout)
        else:
            conn = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=self.imap_timeout)
        conn.login(self.account.USERNAME, self.account.PASSWORD)
        self._post_login_imap(conn, imap_host)
        return conn

    def _close_sync(self, conn: imaplib.IMAP4_SSL) -> None:
        with suppress(Exception):
            conn.close()
        with suppress(Exception):
            conn.logout()

    async def _send_mail(self, message: MIMEMultipart, smtp_host: str, port: int, use_ssl: bool) -> None:
        def _sync_send() -> None:
            if use_ssl:
                smtp_ssl_cls = ProxiedSMTPSSL if self.proxy_url else smtplib.SMTP_SSL
                if self.proxy_url:
                    server_context = smtp_ssl_cls(smtp_host, port, self.proxy_url, 60)
                else:
                    server_context = smtp_ssl_cls(smtp_host, port, timeout=60)
                with server_context as server:
                    server.login(self.account.USERNAME, self.account.PASSWORD)
                    server.send_message(message)
            else:
                smtp_cls = ProxiedSMTP if self.proxy_url else smtplib.SMTP
                if self.proxy_url:
                    server_context = smtp_cls(smtp_host, port, self.proxy_url, 60)
                else:
                    server_context = smtp_cls(smtp_host, port, timeout=60)
                with server_context as server:
                    server.starttls()
                    server.login(self.account.USERNAME, self.account.PASSWORD)
                    server.send_message(message)

        await asyncio.to_thread(_sync_send)

    def _post_login_imap(self, conn: imaplib.IMAP4, host: str) -> None:
        host_lower = str(host or "").lower()
        if any(domain in host_lower for domain in ["163.com", "126.com", "yeah.net"]):
            with suppress(Exception):
                self._send_imap_id(conn)

    def _send_imap_id(self, conn: imaplib.IMAP4) -> None:
        with suppress(Exception):
            imaplib.Commands["ID"] = ("AUTH", "SELECTED")
        payload = "(" + " ".join(
            [
                f'"{k}" "{v}"'
                for k, v in {
                    "name": "nekro-agent",
                    "version": "1.0.0",
                    "vendor": "nekro-agent",
                    "support-email": self.account.USERNAME,
                }.items()
            ],
        ) + ")"
        conn._simple_command("ID", payload)  # noqa: SLF001

    def _get_mailbox_folders_sync(self, conn: imaplib.IMAP4_SSL) -> list[str]:
        status, folders = conn.list()
        if status != "OK":
            return []
        folder_names: list[str] = []
        for folder in folders or []:
            line = folder.decode(errors="ignore") if isinstance(folder, bytes) else str(folder)
            name = self._parse_imap_list_line(line)
            if name:
                folder_names.append(name)
        if "INBOX" in folder_names:
            folder_names = ["INBOX"] + [f for f in folder_names if f != "INBOX"]
        return folder_names

    def _parse_imap_list_line(self, line: str) -> str | None:
        quoted = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        if len(quoted) >= 2:
            name = quoted[-1].replace(r'\"', '"')
            return name if name else None
        tokens = line.split()
        if not tokens:
            return None
        name = tokens[-1].strip('"')
        return name if name else None

    def _pick_mailbox(self, folders: list[str], preferred: str = "INBOX", override: str | None = None) -> str:
        if override:
            return override
        for folder in folders:
            if folder.upper() == preferred.upper():
                return folder
        if preferred.upper() == "INBOX":
            return "INBOX"
        if not folders:
            raise RuntimeError("no folders available")
        return folders[0]

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
