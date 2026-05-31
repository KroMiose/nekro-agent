import asyncio
import imaplib
import smtplib
from collections.abc import Callable
from email.mime.multipart import MIMEMultipart

from nekro_agent.adapters.email.config import EmailAccount

from .imap_smtp_password import ImapSmtpPasswordClient, ProxiedIMAP4SSL, ProxiedSMTP, ProxiedSMTPSSL
from .oauth import OAuthTokenManager


class ImapSmtpOAuth2Client(ImapSmtpPasswordClient):
    def __init__(
        self,
        account: EmailAccount,
        imap_timeout: int,
        oauth_proxy: str = "",
        on_token_update: Callable[[], None] | None = None,
    ):
        super().__init__(account, imap_timeout, oauth_proxy)
        self.token_manager = OAuthTokenManager(account, oauth_proxy, on_token_update)

    async def connect(self) -> None:
        access_token = await self.token_manager.get_access_token()
        self.conn = await asyncio.to_thread(self._connect_sync_with_token, access_token)

    async def send_message(self, message: MIMEMultipart) -> None:
        access_token = await self.token_manager.get_access_token()
        provider_config = self.get_provider_config()
        smtp_host = provider_config.get("smtp_host", "")
        smtp_port = int(provider_config.get("smtp_port", 587))
        smtp_ssl_port = int(provider_config.get("smtp_ssl_port", smtp_port))
        use_ssl_preferred = str(provider_config.get("smtp_use_ssl", False)).lower() == "true"
        if not smtp_host:
            raise RuntimeError(f"未找到 {self.account.EMAIL_ACCOUNT} 的SMTP配置")

        try:
            await self._send_mail_oauth2(
                message,
                smtp_host,
                smtp_ssl_port if use_ssl_preferred else smtp_port,
                use_ssl_preferred,
                access_token,
            )
        except Exception:
            if not use_ssl_preferred:
                await self._send_mail_oauth2(message, smtp_host, smtp_ssl_port, True, access_token)
            else:
                raise

    def _connect_sync_with_token(self, access_token: str) -> imaplib.IMAP4_SSL:
        provider_config = self.get_provider_config()
        imap_host = provider_config.get("imap_host")
        if not imap_host:
            raise ValueError(f"邮箱提供商 {self.account.EMAIL_ACCOUNT} 缺少 imap_host 配置")
        imap_port = int(provider_config.get("imap_port", 993))
        if self.proxy_url:
            conn = ProxiedIMAP4SSL(imap_host, imap_port, self.proxy_url, self.imap_timeout)
        else:
            conn = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=self.imap_timeout)
        auth_string = self._build_xoauth2_string(access_token)
        conn.authenticate("XOAUTH2", lambda _: auth_string.encode())
        self._post_login_imap(conn, imap_host)
        return conn

    async def _send_mail_oauth2(
        self,
        message: MIMEMultipart,
        smtp_host: str,
        port: int,
        use_ssl: bool,
        access_token: str,
    ) -> None:
        auth_string = self._build_xoauth2_string(access_token)

        def auth_object(_challenge: bytes | None = None) -> str:
            return auth_string

        def _sync_send() -> None:
            if use_ssl:
                smtp_ssl_cls = ProxiedSMTPSSL if self.proxy_url else smtplib.SMTP_SSL
                if self.proxy_url:
                    server_context = smtp_ssl_cls(smtp_host, port, self.proxy_url, 60)
                else:
                    server_context = smtp_ssl_cls(smtp_host, port, timeout=60)
                with server_context as server:
                    server.auth("XOAUTH2", auth_object)
                    server.send_message(message)
            else:
                smtp_cls = ProxiedSMTP if self.proxy_url else smtplib.SMTP
                if self.proxy_url:
                    server_context = smtp_cls(smtp_host, port, self.proxy_url, 60)
                else:
                    server_context = smtp_cls(smtp_host, port, timeout=60)
                with server_context as server:
                    server.starttls()
                    server.auth("XOAUTH2", auth_object)
                    server.send_message(message)

        await asyncio.to_thread(_sync_send)

    def _build_xoauth2_string(self, access_token: str) -> str:
        return f"user={self.account.USERNAME}\x01auth=Bearer {access_token}\x01\x01"
