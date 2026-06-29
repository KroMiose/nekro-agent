import asyncio
import base64
import email
import imaplib
import re
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from email.header import decode_header
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import mktime_tz, parseaddr, parsedate_tz
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

import aiofiles
from fastapi import APIRouter

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformMessageExt,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.message_service import message_service

from .base import EMAIL_PROVIDER_CONFIGS
from .clients import EmailClient, GmailApiClient, ImapSmtpOAuth2Client, ImapSmtpPasswordClient, MicrosoftGraphMailClient
from .config import EmailAccount, EmailConfig
from .routers import router, set_email_adapter

logger = get_sub_logger("adapter.email")
def decode_mime_words(s):
    """解码MIME编码的字符串"""
    if not s:
        return ""

    try:
        # 解码MIME头部
        decoded_parts = decode_header(s)
        decoded_string = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                # 如果是字节串，使用指定的编码解码
                decoded_string += part.decode(encoding or "utf-8", errors="ignore")
            else:
                # 如果已经是字符串，直接添加
                decoded_string += part

    except Exception as e:
        logger.warning(f"解码MIME字符串时出错: {e}")
        return s if isinstance(s, str) else ""
    else:
        return decoded_string


class _HTMLTextExtractor(HTMLParser):
    """简单提取HTML中的可见文字，避免在聊天中展示冗长的原始HTML"""

    _BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}

    def __init__(self):
        super().__init__()
        self._texts: List[str] = []
        self._skip = False

    def handle_starttag(self, tag, _attrs):
        tag_lower = tag.lower()
        if tag_lower in {"script", "style"}:
            self._skip = True
        if tag_lower in self._BLOCK_TAGS:
            self._texts.append("\n")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in {"script", "style"}:
            self._skip = False
        if tag_lower in self._BLOCK_TAGS:
            self._texts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._texts.append(data)

    def get_text(self) -> str:
        text = " ".join(self._texts)
        # 规范空白并压缩空行，避免聊天里出现大段留白
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s*\n\s*", "\n", text)
        text = re.sub(r"\n{2,}", "\n\n", text)  # 至多保留一个空行
        return text.strip()


@dataclass
class ParsedEmail:
    """解析后的邮件数据"""

    subject: str
    sender_name: str
    sender_addr: str
    date_str: str
    html_content: str
    text_content: str
    attachments: List[str]
    raw_bytes: bytes


@dataclass
class EmailPullResult:
    success: bool
    account_username: str
    mailbox: str = ""
    search_unseen_only: bool = True
    mark_as_seen_after_fetch: bool = True
    max_per_poll: int = 0
    requested_limit: int | None = None
    effective_limit: int = 0
    found_count: int = 0
    processed_count: int = 0
    failed_count: int = 0
    marked_seen_count: int = 0
    mark_seen_failed_count: int = 0
    skipped_count: int = 0
    reconnect_attempted: bool = False
    reconnect_success: bool | None = None
    started_at: int = 0
    finished_at: int = 0
    duration_ms: int = 0
    errors: List[dict[str, Any]] = field(default_factory=list)
    debug_steps: List[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "account_username": self.account_username,
            "mailbox": self.mailbox,
            "search_unseen_only": self.search_unseen_only,
            "mark_as_seen_after_fetch": self.mark_as_seen_after_fetch,
            "max_per_poll": self.max_per_poll,
            "requested_limit": self.requested_limit,
            "effective_limit": self.effective_limit,
            "found_count": self.found_count,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "marked_seen_count": self.marked_seen_count,
            "mark_seen_failed_count": self.mark_seen_failed_count,
            "skipped_count": self.skipped_count,
            "reconnect_attempted": self.reconnect_attempted,
            "reconnect_success": self.reconnect_success,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "debug_steps": self.debug_steps,
        }


class EmailAdapter(BaseAdapter[EmailConfig]):
    """邮箱适配器"""

    _POLLING_STATUS_LOG_INTERVAL_SECONDS = 3600

    def __init__(self, config_cls: Type[EmailConfig] = EmailConfig):
        """初始化邮箱适配器"""
        super().__init__(config_cls)

        # 初始化邮箱提供商
        self.providers: List = []

        # 邮件客户端池
        self.email_clients: Dict[str, EmailClient] = {}

        # IMAP连接池（兼容旧插件直接访问）
        self.imap_connections: dict = {}

        # 账户连接锁（确保每个账户的线程安全访问）
        self.imap_locks: Dict[str, asyncio.Lock] = {}

        # 邮箱账户到聊天ID的映射
        self.account_chat_mapping: Dict[str, str] = {}

        # 轮询任务
        self._polling_task: Optional[asyncio.Task] = None
        self._polling_active = False
        self._last_polling_status_log_at: float | None = None

    def get_default_channel_status(self, channel_type: ChatType) -> str:
        if channel_type in {ChatType.GROUP, ChatType.PRIVATE}:
            return "disabled"
        return super().get_default_channel_status(channel_type)

    def _html_to_text(self, html_content: str) -> str:
        """提取HTML中的文字，去除标签/脚本，便于聊天展示"""
        extractor = _HTMLTextExtractor()
        try:
            extractor.feed(html_content)
        except Exception as exc:  # 防御解析异常
            logger.debug(f"解析HTML为文本时出错: {exc}")
        return extractor.get_text()

    def _parse_email(self, raw_email: bytes) -> ParsedEmail:
        """解析邮件内容

        Args:
            raw_email: 原始邮件字节数据

        Returns:
            ParsedEmail: 解析后的邮件数据
        """
        email_message = email.message_from_bytes(raw_email)

        subject = decode_mime_words(email_message.get("Subject", "")) or "无主题"
        from_header = email_message.get("From", "")
        sender_name, sender_addr = parseaddr(from_header)
        sender_name = decode_mime_words(sender_name) or sender_name
        date_str = email_message.get("Date", "")

        html_content = ""
        text_content = ""
        attachments: List[str] = []

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                cdisp = part.get_content_disposition()

                # 处理附件（attachment 和 inline）
                if cdisp in {"attachment", "inline"}:
                    decoded_filename = decode_mime_words(part.get_filename() or "unnamed_attachment")
                    attachments.append(decoded_filename)
                    # 附件下载由调用者处理（保持纯函数）
                    continue

                charset = part.get_content_charset()
                try:
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        text = payload.decode(charset or "utf-8", errors="ignore")
                    else:
                        text = str(payload)
                except Exception:
                    try:
                        payload = part.get_payload()
                        text = payload.decode("utf-8", errors="ignore") if isinstance(payload, bytes) else str(payload)
                    except Exception:
                        text = ""

                if content_type == "text/html":
                    html_content = text
                elif content_type == "text/plain":
                    text_content = text
        else:
            content_type = email_message.get_content_type()
            charset = email_message.get_content_charset()
            try:
                payload = email_message.get_payload(decode=True)
                if isinstance(payload, bytes):
                    text = payload.decode(charset or "utf-8", errors="ignore")
                else:
                    text = str(payload)
            except Exception:
                try:
                    payload = email_message.get_payload()
                    text = payload.decode("utf-8", errors="ignore") if isinstance(payload, bytes) else str(payload)
                except Exception:
                    text = ""

            if content_type == "text/html":
                html_content = text
            elif content_type == "text/plain":
                text_content = text

        return ParsedEmail(
            subject=subject,
            sender_name=sender_name,
            sender_addr=sender_addr,
            date_str=date_str,
            html_content=html_content,
            text_content=text_content,
            attachments=attachments,
            raw_bytes=raw_email,
        )

    def _connect_imap(self, account: EmailAccount) -> imaplib.IMAP4_SSL:
        """连接到IMAP服务器

        Args:
            account: 邮箱账户配置

        Returns:
            imaplib.IMAP4_SSL: IMAP连接对象
        """
        if account.EMAIL_ACCOUNT == "自定义":
            imap_host = account.CUSTOM_IMAP_HOST
            if not imap_host:
                raise ValueError("自定义邮箱提供商必须填写 IMAP 主机地址")
            imap_port = account.CUSTOM_IMAP_PORT
        else:
            provider_config = EMAIL_PROVIDER_CONFIGS.get(account.EMAIL_ACCOUNT, {})
            if not provider_config:
                raise ValueError(f"未知的邮箱提供商: {account.EMAIL_ACCOUNT}")
            imap_host = provider_config.get("imap_host")
            if not imap_host:
                raise ValueError(f"邮箱提供商 {account.EMAIL_ACCOUNT} 缺少 imap_host 配置")
            imap_port = int(provider_config.get("imap_port", 993))

        # 使用配置的超时时间
        conn = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=self.config.IMAP_TIMEOUT)
        conn.login(account.USERNAME, account.PASSWORD)
        # 执行登录后的特殊处理（如163邮箱的ID命令）
        self._post_login_imap(conn, account.USERNAME, imap_host)
        logger.info(f"IMAP连接建立成功: {account.USERNAME}@{imap_host}")
        return conn

    async def _notify_new_email(
        self,
        account_username: str,
        chat_id: str,
        email_id: bytes,
        parsed: ParsedEmail,
    ) -> None:
        """发送新邮件通知

        Args:
            account_username: 邮箱账户用户名
            chat_id: 聊天ID
            email_id: 邮件ID
            parsed: 解析后的邮件数据
        """
        if not (self.config.EMAIL_NOTIFICATIONS_ENABLED and self.config.EMAIL_NOTIFICATIONS_CHAT_KEY):
            return

        notify_chat_key = self.config.EMAIL_NOTIFICATIONS_CHAT_KEY
        attachment_info = (
            f"\n附件: 有 {len(parsed.attachments)} 个附件\n附件名称: {', '.join(parsed.attachments)}"
            if parsed.attachments
            else "\n附件: 无附件"
        )

        notify_text = (
            f"[邮箱新邮件通知]\n"
            f"收件账户: {account_username}\n"
            f"邮件UID: {self._email_id_text(email_id)}\n"
            f"发件人: {parsed.sender_name} <{parsed.sender_addr}>\n"
            f"主题: {parsed.subject}\n"
            f"日期: {parsed.date_str}"
            f"{attachment_info}\n\n"
            f"邮件内容已同步到聊天 {chat_id}，你可以使用 get_email_content 方法获取完整内容。"
        )
        await message_service.push_system_message(
            chat_key=notify_chat_key,
            agent_messages=notify_text,
            trigger_agent=True,
        )

    @property
    def key(self) -> str:
        """适配器唯一标识"""
        return "email"

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "邮箱：email-邮箱账户名（例如：email-123456@qq.com）",
        ]

    def detect_command(self, _text: str) -> Optional[Tuple[str, str]]:
        """邮箱场景禁用命令系统，避免正文误触发命令解析。"""
        return None

    @property
    def metadata(self) -> AdapterMetadata:
        """适配器元数据"""
        return AdapterMetadata(
            name="Email",
            description="邮箱适配器，支持多账户 IMAP/SMTP 收发、Gmail/Outlook 官方登录、邮件同步、附件流转和手动收件诊断",
            version="2.0.0",
            author="NekroAI",
            homepage="https://github.com/nekro-agent/nekro-agent",
            tags=["email", "imap", "smtp", "oauth", "mail"],
        )

    async def init(self) -> None:
        """初始化适配器"""
        logger.info("邮箱适配器初始化...")

        # 检查是否有启用的邮箱账户
        enabled_accounts = [
            acc for acc in self.config.RECEIVE_ACCOUNTS
            if getattr(acc, "ENABLED", False) and getattr(acc, "RECEIVE_ENABLED", False)
        ]
        if not enabled_accounts:
            logger.info("没有启用的邮箱账户，跳过邮箱适配器初始化")
            return

        # 确保附件保存目录存在
        try:
            Path(OsEnv.DATA_DIR, "uploads").mkdir(parents=True, exist_ok=True)
            logger.info("附件保存目录已创建: ./data/uploads")
        except Exception as e:
            logger.error(f"创建附件保存目录失败: {e}")

        # 初始化邮件客户端连接等操作
        await self._init_email_clients()
        # 初始化邮箱账户到聊天ID的映射
        self._init_account_chat_mapping()
        # 启动轮询任务
        self._start_polling()
        logger.info("邮箱适配器初始化完成")

    async def cleanup(self) -> None:
        """清理适配器"""
        logger.info("邮箱适配器清理中...")
        # 停止轮询任务
        self._stop_polling()
        # 关闭所有邮件客户端连接
        for client in self.email_clients.values():
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"关闭邮件客户端连接时出错: {e}")
        self.email_clients.clear()
        self.imap_connections.clear()
        logger.info("邮箱适配器清理完成")

    def _start_polling(self) -> None:
        """启动轮询任务"""
        # 如果没有邮件客户端连接，不启动轮询任务
        if not self.email_clients:
            logger.info("没有邮件客户端连接，跳过轮询任务启动")
            return

        if not self._polling_task or self._polling_task.done():
            self._polling_active = True
            self._last_polling_status_log_at = None
            self._polling_task = asyncio.create_task(self._polling_loop())
            logger.info("邮箱适配器轮询任务已启动")

    def _stop_polling(self) -> None:
        """停止轮询任务"""
        self._polling_active = False
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            logger.info("邮箱适配器轮询任务已停止")

    async def _polling_loop(self) -> None:
        """轮询循环"""
        poll_count = 0
        while self._polling_active:
            try:
                poll_count += 1
                now = time.monotonic()
                if (
                    self._last_polling_status_log_at is None
                    or now - self._last_polling_status_log_at >= self._POLLING_STATUS_LOG_INTERVAL_SECONDS
                ):
                    logger.info(
                        f"邮箱适配器第 {poll_count} 次轮询开始，轮询间隔: {self.config.POLL_INTERVAL} 秒，已连接账户数: {len(self.email_clients)}",
                    )
                    self._last_polling_status_log_at = now

                # 检查每个账户的新邮件
                accounts_to_check = list(self.email_clients.items())
                for account_username, client in accounts_to_check:
                    if self._polling_active:
                        try:
                            await self._check_new_emails(account_username, client)
                        except Exception as e:
                            logger.error(f"检查账户 {account_username} 的新邮件时发生错误: {e}")

                # 等待下次轮询
                await asyncio.sleep(self.config.POLL_INTERVAL)

            except asyncio.CancelledError:
                logger.info("邮箱适配器轮询任务被取消")
                break
            except Exception as e:
                logger.error(f"邮箱适配器轮询过程中发生错误: {e}")
                # 发生错误时仍然继续轮询
                await asyncio.sleep(self.config.POLL_INTERVAL)

    @asynccontextmanager
    async def _account_lock(self, account_username: str):
        """账户锁上下文管理器

        Args:
            account_username: 邮箱账户用户名

        Yields:
            None

        Raises:
            RuntimeError: 如果账户锁不存在
        """
        lock = self.imap_locks.get(account_username)
        if lock is None:
            raise RuntimeError(f"Lock for account {account_username} not found")
        async with lock:
            yield

    def _pick_mailbox(
        self,
        folders: List[str],
        preferred: str = "INBOX",
        override: str | None = None,
    ) -> str:
        """选择邮箱文件夹（纯函数，不涉及I/O）

        Args:
            folders: 可用的文件夹列表
            preferred: 首选文件夹名称
            override: 强制使用的文件夹名称

        Returns:
            str: 选择的文件夹名称

        Raises:
            RuntimeError: 如果没有可用文件夹
        """
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

    async def _select_mailbox(
        self,
        account_username: str,
        conn: imaplib.IMAP4_SSL,
        preferred: str = "INBOX",
        override_folder: str | None = None,
    ) -> str:
        """选择邮箱文件夹

        Args:
            account_username: 邮箱账户用户名
            conn: IMAP连接对象
            preferred: 首选文件夹名称，默认为 "INBOX"
            override_folder: 强制使用的文件夹名称，如果指定则忽略 preferred

        Returns:
            str: 实际选择的文件夹名称

        Raises:
            Exception: 如果文件夹选择失败
        """
        folders = await asyncio.to_thread(self.get_mailbox_folders, conn)
        target = self._pick_mailbox(folders, preferred=preferred, override=override_folder)

        status, _ = await asyncio.to_thread(conn.select, target)
        if status != "OK":
            raise Exception(f"Failed to select mailbox {target} for account {account_username}")
        return target

    def _parse_imap_list_line(self, line: str) -> str | None:
        """解析 IMAP LIST 命令返回的单行数据

        Args:
            line: IMAP LIST 返回的一行数据

        Returns:
            Optional[str]: 解析出的文件夹名称，解析失败返回 None
        """
        quoted = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        if len(quoted) >= 2:
            name = quoted[-1].replace(r'\"', '"')
            return name if name else None
        tokens = line.split()
        if not tokens:
            return None
        name = tokens[-1].strip('"')
        return name if name else None

    def _extract_body(self, email_message: Message) -> tuple[str, str]:
        """提取邮件正文内容（HTML 和纯文本）

        Args:
            email_message: 邮件消息对象

        Returns:
            tuple[str, str]: (html_content, text_content)
        """
        html_content = ""
        text_content = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                ctype = part.get_content_type()
                # 跳过附件
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

    def _inline_cid_images(self, html_content: str, email_message: Message) -> str:
        """将 HTML 正文中的 cid 图片替换为 data URL，便于 Web 端直接预览。"""
        if not html_content:
            return html_content

        resolved_html = html_content
        for part in email_message.walk():
            content_id = str(part.get("Content-ID") or "").strip().strip("<>")
            if not content_id:
                continue

            content_type = part.get_content_type()
            if not content_type.startswith("image/"):
                continue

            try:
                payload = part.get_payload(decode=True)
            except Exception:
                payload = None

            if not payload:
                continue

            encoded = base64.b64encode(payload).decode("utf-8")
            data_url = f"data:{content_type};base64,{encoded}"
            resolved_html = resolved_html.replace(f"cid:{content_id}", data_url)

        return resolved_html

    def get_mailbox_folders(self, conn: imaplib.IMAP4_SSL) -> List[str]:
        """获取邮箱文件夹列表（同步版本，供asyncio.to_thread调用）

        优先返回INBOX，其次返回其他文件夹
        """
        status, folders = conn.list()
        if status != "OK":
            return []

        folder_names: List[str] = []

        # 解析 IMAP LIST 返回的文件夹名
        for folder in folders or []:
            # IMAP 库通常返回 bytes，需要先解码
            line = folder.decode(errors="ignore") if isinstance(folder, bytes) else str(folder)
            name = self._parse_imap_list_line(line)
            if name:
                folder_names.append(name)

        # 优先返回 INBOX，将其移动到列表开头（如果存在）
        inbox = "INBOX"
        if inbox in folder_names:
            folder_names = [inbox] + [f for f in folder_names if f != inbox]

        return folder_names

    async def select_default_mailbox(self, account_username: str, preferred: str = "INBOX"):
        """选择默认邮箱文件夹（带锁保护的辅助方法）

        Args:
            account_username: 邮箱账户用户名
            preferred: 首选文件夹名称，默认为 "INBOX"

        Returns:
            imaplib.IMAP4_SSL: 已选择文件夹的IMAP连接对象

        Raises:
            RuntimeError: 如果账户不存在或没有可用文件夹
        """
        if account_username not in self.imap_connections:
            raise RuntimeError(f"账户 {account_username} 未连接或不存在")

        conn = self.imap_connections[account_username]
        await self._select_mailbox(account_username, conn, preferred=preferred)
        return conn

    async def imap_search(self, conn: imaplib.IMAP4_SSL, criteria: str) -> tuple[str, list]:
        """异步执行 IMAP SEARCH 命令

        Args:
            conn: IMAP连接对象
            criteria: 搜索条件

        Returns:
            tuple[str, list]: (status, data) 元组，status 为状态字符串，data 为搜索结果列表
        """
        return await asyncio.to_thread(conn.search, None, criteria)

    async def imap_fetch(self, conn: imaplib.IMAP4_SSL, msg_id, query: str = "(RFC822)") -> tuple[str, list]:
        """异步执行 IMAP FETCH 命令

        Args:
            conn: IMAP连接对象
            msg_id: 邮件ID
            query: 查询字符串，默认为 '(RFC822)'

        Returns:
            tuple[str, list]: (status, data) 元组，status 为状态字符串，data 为数据列表
        """
        return await asyncio.to_thread(conn.fetch, msg_id, query)

    def _email_id_text(self, email_id: bytes) -> str:
        return email_id.decode(errors="ignore") if isinstance(email_id, bytes) else str(email_id)

    async def manual_pull_account(
        self,
        account: EmailAccount,
        *,
        unseen_only: bool = True,
        limit: int | None = None,
    ) -> dict:
        if not account.ENABLED or not account.RECEIVE_ENABLED:
            raise RuntimeError("账户未启用收信")

        reconnect_attempted = False
        reconnect_success: bool | None = None
        client = self.email_clients.get(account.USERNAME)
        if client is None:
            reconnect_attempted = True
            reconnect_success = await self._reconnect_email_client(account)
            client = self.email_clients.get(account.USERNAME)

        if client is None:
            now = int(time.time())
            result = EmailPullResult(
                success=False,
                account_username=account.USERNAME,
                search_unseen_only=unseen_only,
                mark_as_seen_after_fetch=self.config.MARK_AS_SEEN_AFTER_FETCH,
                max_per_poll=self.config.MAX_PER_POLL,
                requested_limit=limit,
                effective_limit=0,
                reconnect_attempted=reconnect_attempted,
                reconnect_success=reconnect_success,
                started_at=now,
                finished_at=now,
                errors=[{"stage": "connect", "message": "账户未连接，且重连失败"}],
                debug_steps=[
                    {
                        "stage": "connect",
                        "client_available": False,
                        "reconnect_attempted": reconnect_attempted,
                        "reconnect_success": reconnect_success,
                    },
                ],
            )
            self._log_manual_pull_result(account, result)
            return self._build_pull_response(account, result)

        result = await self._pull_account_emails(
            account.USERNAME,
            client,
            unseen_only=unseen_only,
            limit=limit,
            reconnect_on_error=True,
        )
        if reconnect_attempted and not result.reconnect_attempted:
            result.reconnect_attempted = True
            result.reconnect_success = reconnect_success
        result.debug_steps.insert(
            0,
            {
                "stage": "connect",
                "client_available": True,
                "reconnect_attempted": reconnect_attempted,
                "reconnect_success": reconnect_success,
                "client": client.__class__.__name__,
            },
        )
        self._log_manual_pull_result(account, result)
        return self._build_pull_response(account, result)

    def _log_manual_pull_result(self, account: EmailAccount, result: EmailPullResult) -> None:
        logger.info(
            f"手动拉取邮箱账户: username={account.USERNAME}, provider={account.EMAIL_ACCOUNT}, "
            f"auth_type={account.AUTH_TYPE}, transport_type={account.TRANSPORT_TYPE}, mailbox={result.mailbox}, "
            f"unseen_only={result.search_unseen_only}, found={result.found_count}, processed={result.processed_count}, "
            f"failed={result.failed_count}, marked_seen={result.marked_seen_count}, skipped={result.skipped_count}, "
            f"duration_ms={result.duration_ms}, success={result.success}",
        )
        for step in result.debug_steps:
            logger.info(f"手动拉取邮箱账户 {account.USERNAME} debug: {step}")
        for error in result.errors:
            logger.error(f"手动拉取邮箱账户 {account.USERNAME} error: {error}")

    def _build_pull_response(self, account: EmailAccount, result: EmailPullResult) -> dict:
        payload = result.to_dict()
        payload.update(
            {
                "provider": account.EMAIL_ACCOUNT,
                "auth_type": account.AUTH_TYPE,
                "transport_type": account.TRANSPORT_TYPE,
            },
        )
        return payload

    async def _pull_account_emails(
        self,
        account_username: str,
        client: EmailClient,
        *,
        unseen_only: bool | None = None,
        limit: int | None = None,
        reconnect_on_error: bool = True,
    ) -> EmailPullResult:
        effective_unseen_only = self.config.FETCH_UNSEEN_ONLY if unseen_only is None else unseen_only
        configured_limit = max(1, self.config.MAX_PER_POLL)
        effective_limit = configured_limit if limit is None else min(max(1, limit), configured_limit)
        started_monotonic = time.monotonic()
        result = EmailPullResult(
            success=False,
            account_username=account_username,
            search_unseen_only=effective_unseen_only,
            mark_as_seen_after_fetch=self.config.MARK_AS_SEEN_AFTER_FETCH,
            max_per_poll=self.config.MAX_PER_POLL,
            requested_limit=limit,
            effective_limit=effective_limit,
            started_at=int(time.time()),
        )
        reconnect_needed = False

        try:
            async with self._account_lock(account_username):
                if hasattr(client, "get_mailbox_folders_debug"):
                    try:
                        folders = await client.get_mailbox_folders_debug()
                        result.debug_steps.append({"stage": "list_mailboxes", "folders": folders})
                    except Exception as e:
                        result.debug_steps.append({"stage": "list_mailboxes", "error": str(e)})
                try:
                    result.debug_steps.append({"stage": "select_mailbox", "preferred": "INBOX"})
                    target_folder = await client.select_mailbox()
                    result.mailbox = target_folder
                    result.debug_steps.append({"stage": "select_mailbox", "selected": target_folder})
                    logger.debug(f"账户 {account_username} 使用文件夹: {target_folder}")
                except Exception as e:
                    reconnect_needed = True
                    result.errors.append({"stage": "select_mailbox", "message": str(e)})
                    result.debug_steps.append({"stage": "select_mailbox", "error": str(e)})
                    raise

                try:
                    list_step = {"stage": "list_message_ids", "unseen_only": effective_unseen_only, "mailbox": result.mailbox}
                    if client.__class__.__name__ == "MicrosoftGraphMailClient":
                        list_step["url"] = "https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages"
                        list_step["params"] = {"$select": "id", "$top": 50}
                        if effective_unseen_only:
                            list_step["params"]["$filter"] = "isRead eq false"
                        else:
                            list_step["params"]["$orderby"] = "receivedDateTime desc"
                    else:
                        list_step["criteria"] = "UNSEEN" if effective_unseen_only else "ALL"
                    result.debug_steps.append(list_step)
                    email_ids = await client.list_message_ids(effective_unseen_only)
                    result.found_count = len(email_ids)
                    result.debug_steps.append(
                        {
                            "stage": "list_message_ids",
                            "found_count": result.found_count,
                            "sample_ids": [self._email_id_text(email_id) for email_id in email_ids[:5]],
                        },
                    )
                except Exception as e:
                    reconnect_needed = True
                    result.errors.append({"stage": "list_message_ids", "message": str(e)})
                    result.debug_steps.append({"stage": "list_message_ids", "error": str(e)})
                    raise

                result.effective_limit = min(result.found_count, effective_limit)
                result.skipped_count = max(0, result.found_count - result.effective_limit)
                if email_ids:
                    logger.info(f"账户 {account_username} 在文件夹 {target_folder} 中发现 {len(email_ids)} 封新邮件")
                else:
                    logger.debug(f"账户 {account_username} 在文件夹 {target_folder} 中没有新邮件")

                for email_id in email_ids[: result.effective_limit]:
                    email_id_text = self._email_id_text(email_id)
                    try:
                        if await self._process_email(account_username, email_id, client, raise_on_error=True):
                            result.processed_count += 1
                        else:
                            result.failed_count += 1
                            result.errors.append(
                                {"stage": "process", "email_id": email_id_text, "message": "邮件处理失败"},
                            )
                    except Exception as e:
                        result.failed_count += 1
                        result.errors.append({"stage": "process", "email_id": email_id_text, "message": str(e)})

                if self.config.MARK_AS_SEEN_AFTER_FETCH and effective_unseen_only:
                    for email_id in email_ids[: result.effective_limit]:
                        email_id_text = self._email_id_text(email_id)
                        try:
                            await client.mark_seen(email_id)
                            result.marked_seen_count += 1
                        except Exception as e:
                            result.mark_seen_failed_count += 1
                            result.errors.append({"stage": "mark_seen", "email_id": email_id_text, "message": str(e)})
        except Exception as e:
            if not result.errors:
                result.errors.append({"stage": "pull", "message": str(e)})
            if reconnect_on_error and reconnect_needed:
                result.reconnect_attempted = True
                for account in self.config.RECEIVE_ACCOUNTS:
                    if account_username == account.USERNAME and account.ENABLED and account.RECEIVE_ENABLED:
                        logger.info(f"尝试重新连接账户 {account_username}")
                        result.reconnect_success = await self._reconnect_email_client(account)
                        if result.reconnect_success:
                            logger.info(f"账户 {account_username} 重新连接成功")
                        else:
                            logger.error(f"账户 {account_username} 重新连接失败")
                        break
        finally:
            result.finished_at = int(time.time())
            result.duration_ms = int((time.monotonic() - started_monotonic) * 1000)
            result.success = not result.errors

        return result

    async def _check_new_emails(self, account_username: str, client: EmailClient) -> None:
        """检查指定账户的新邮件"""
        result = await self._pull_account_emails(
            account_username,
            client,
            unseen_only=self.config.FETCH_UNSEEN_ONLY,
            limit=self.config.MAX_PER_POLL,
            reconnect_on_error=True,
        )
        if result.found_count:
            logger.info(
                f"账户 {account_username} 邮件拉取完成: 文件夹={result.mailbox}, 发现={result.found_count}, "
                f"处理={result.processed_count}, 失败={result.failed_count}, 跳过={result.skipped_count}",
            )
        for error in result.errors:
            logger.error(f"账户 {account_username} 邮件拉取错误: {error}")

    async def _process_email(
        self,
        account_username: str,
        email_id: bytes,
        client: EmailClient,
        *,
        raise_on_error: bool = False,
    ) -> bool:
        """处理单封邮件"""
        try:
            raw_email = await client.fetch_raw_message(email_id)
            if raw_email is None:
                message = f"获取邮件 {self._email_id_text(email_id)} 失败"
                logger.warning(message)
                if raise_on_error:
                    raise RuntimeError(message)
                return False
            # 只解析一次邮件，避免重复解析
            email_message = email.message_from_bytes(raw_email)
            parsed = self._parse_email(raw_email)

            # 处理附件下载（基于解析结果）
            if parsed.attachments and email_message.is_multipart():
                for part in email_message.walk():
                    cdisp = part.get_content_disposition()
                    if cdisp in {"attachment", "inline"}:
                        decoded_filename = decode_mime_words(part.get_filename() or "unnamed_attachment")
                        asyncio.create_task(
                            self._download_attachment(
                                part,
                                decoded_filename,
                                account_username,
                                parsed.subject,
                                self._email_id_text(email_id),
                            ),
                        )

            # HTML → 文本规范化
            html_text_content = ""
            if parsed.html_content:
                html_text_content = self._html_to_text(parsed.html_content)

            # 构建消息内容
            content = (
                f"主题: {parsed.subject}\n"
                f"发件人: {parsed.sender_name} <{parsed.sender_addr}>\n"
                f"日期: {parsed.date_str}\n\n"
            )

            if parsed.text_content:
                content += parsed.text_content
            elif parsed.html_content:
                content += html_text_content or self._html_to_text(parsed.html_content)
            else:
                content += "[无邮件正文内容]"

            # 添加附件信息
            if parsed.attachments:
                content += f"\n\n附件 ({len(parsed.attachments)} 个):\n"
                for attachment in parsed.attachments:
                    content += f"- {attachment}\n"

            # 生成时间戳
            try:
                date_tuple = parsedate_tz(parsed.date_str)
                timestamp = mktime_tz(date_tuple) if date_tuple else int(time.time())
            except Exception:
                timestamp = int(time.time())

            # 获取聊天ID
            chat_id = self.account_chat_mapping.get(account_username, f"email_{account_username}")

            # 创建平台消息对象
            platform_message = PlatformMessage(
                message_id=self._email_id_text(email_id),
                sender_id=parsed.sender_addr,
                sender_name=parsed.sender_name,
                content_text=content,
                is_self=False,
                timestamp=timestamp,
                ext_data=PlatformMessageExt(),
            )

            # 创建平台频道对象
            platform_channel = PlatformChannel(
                channel_id=chat_id,
                channel_name=f"邮箱账户: {account_username}",
                channel_type=ChatType.PRIVATE,
            )

            # 创建平台用户对象
            platform_user = PlatformUser(
                platform_name="email",
                user_id=parsed.sender_addr,
                user_name=parsed.sender_name,
                user_avatar="",
            )

            # 将消息发送到核心引擎
            await collect_message(self, platform_channel, platform_user, platform_message)
            logger.info(f"成功处理账户 {account_username} 的邮件: {parsed.subject}")

            # 写入本地缓存
            try:
                import json

                from nekro_agent.models.db_email import DBEmail

                # 提取 In-Reply-To 和 References 头
                in_reply_to = email_message.get("In-Reply-To", "") or ""
                references_header = email_message.get("References", "") or ""
                message_id_header = email_message.get("Message-ID", "") or ""

                # 收件人列表
                to_header = email_message.get("To", "") or ""
                recipients_json = json.dumps([addr.strip() for addr in to_header.split(",") if addr.strip()])

                # 正文截断到前 5000 字符
                body_text = parsed.text_content or html_text_content or ""
                body_text = body_text[:5000]

                # 附件名称列表
                attachment_names_json = json.dumps(parsed.attachments) if parsed.attachments else "[]"

                # 解析邮件日期
                email_date = None
                try:
                    from email.utils import parsedate_to_datetime

                    if parsed.date_str:
                        email_date = parsedate_to_datetime(parsed.date_str)
                except Exception:
                    pass

                await DBEmail.update_or_create(
                    defaults={
                        "message_id": message_id_header[:512],
                        "subject": parsed.subject[:1024],
                        "sender": f"{parsed.sender_name} <{parsed.sender_addr}>"[:512],
                        "recipients": recipients_json,
                        "date": email_date,
                        "body_text": body_text,
                        "has_attachments": len(parsed.attachments) > 0,
                        "attachment_names": attachment_names_json,
                        "in_reply_to": in_reply_to[:512],
                        "references": references_header,
                    },
                    account_username=account_username,
                    email_uid=self._email_id_text(email_id),
                )
            except Exception as cache_exc:
                logger.warning(f"写入邮件缓存失败: {cache_exc}")

            # 发送新邮件通知
            try:
                await self._notify_new_email(account_username, chat_id, email_id, parsed)
                if self.config.EMAIL_NOTIFICATIONS_ENABLED and self.config.EMAIL_NOTIFICATIONS_CHAT_KEY:
                    logger.info(
                        f"已根据配置在频道 {self.config.EMAIL_NOTIFICATIONS_CHAT_KEY} 触发 AI 处理邮箱新邮件，账户={account_username}, 主题={parsed.subject}",
                    )
            except Exception as notify_exc:
                logger.error(f"触发邮箱新邮件通知失败: {notify_exc}")

            return True
        except Exception as e:
            logger.error(f"处理邮件 {self._email_id_text(email_id)} 时发生错误: {e}")
            if raise_on_error:
                raise
            return False

    def _init_account_chat_mapping(self) -> None:
        """初始化邮箱账户到聊天ID的映射"""
        for account in self.config.RECEIVE_ACCOUNTS:
            if account.ENABLED and account.RECEIVE_ENABLED:
                # 为每个启用的邮箱账户创建唯一的聊天ID
                chat_id = account.USERNAME
                self.account_chat_mapping[account.USERNAME] = chat_id
                logger.info(f"邮箱账户 {account.USERNAME} 映射到聊天 {chat_id}")

    def _create_email_client(self, account: EmailAccount) -> EmailClient:
        proxy_url = self.config.OAUTH_PROXY if account.USE_PROXY else ""
        if account.AUTH_TYPE == "oauth2" and account.TRANSPORT_TYPE == "imap_smtp":
            return ImapSmtpOAuth2Client(account, self.config.IMAP_TIMEOUT, proxy_url, self.config.dump_config)
        if account.TRANSPORT_TYPE == "gmail_api":
            return GmailApiClient(account, proxy_url)
        if account.TRANSPORT_TYPE == "microsoft_graph":
            return MicrosoftGraphMailClient(account, proxy_url)
        return ImapSmtpPasswordClient(account, self.config.IMAP_TIMEOUT, proxy_url)

    async def _init_email_clients(self) -> None:
        """初始化邮件客户端连接"""
        for account in self.config.RECEIVE_ACCOUNTS:
            if not account.ENABLED or not account.RECEIVE_ENABLED:
                continue

            try:
                client = self._create_email_client(account)
                await client.connect()
                self.email_clients[account.USERNAME] = client
                conn = getattr(client, "conn", None)
                if conn is not None:
                    self.imap_connections[account.USERNAME] = conn
                self.imap_locks[account.USERNAME] = asyncio.Lock()
                logger.info(f"邮件客户端连接建立成功: {account.USERNAME}")

            except Exception as e:
                logger.error(f"邮件客户端连接建立失败 ({account.USERNAME}): {e}")

    async def _reconnect_email_client(self, account: EmailAccount) -> bool:
        """重新连接邮件客户端"""
        try:
            await self._remove_email_client(account.USERNAME)
            if not account.ENABLED or not account.RECEIVE_ENABLED:
                return True

            client = self._create_email_client(account)
            await client.connect()
            self.email_clients[account.USERNAME] = client
            conn = getattr(client, "conn", None)
            if conn is not None:
                self.imap_connections[account.USERNAME] = conn
            if account.USERNAME not in self.imap_locks:
                self.imap_locks[account.USERNAME] = asyncio.Lock()
            self.account_chat_mapping[account.USERNAME] = account.USERNAME
        except Exception as e:
            logger.error(f"邮件客户端重新连接失败 ({account.USERNAME}): {e}")
            return False
        else:
            logger.info(f"邮件客户端重新连接成功: {account.USERNAME}")
            self._start_polling()
            return True

    async def _remove_email_client(self, account_username: str) -> None:
        client = self.email_clients.pop(account_username, None)
        if client:
            await client.close()
        self.imap_connections.pop(account_username, None)
        self.imap_locks.pop(account_username, None)
        self.account_chat_mapping.pop(account_username, None)

    async def _reconnect_imap(self, account: EmailAccount) -> bool:
        return await self._reconnect_email_client(account)

    def _get_provider_config(self, email_account: str) -> dict:
        """获取邮箱提供商配置"""
        return EMAIL_PROVIDER_CONFIGS.get(email_account, {})

    def get_provider_config_for_account(self, account: EmailAccount) -> dict:
        """获取邮箱提供商配置（支持自定义提供商）

        当提供商为"自定义"时，从 account 的 CUSTOM_* 字段构建配置 dict；
        否则走预设映射。供 adapter 内部和 email_utils 插件复用。
        """
        if account.EMAIL_ACCOUNT == "自定义":
            return {
                "imap_host": account.CUSTOM_IMAP_HOST,
                "imap_port": str(account.CUSTOM_IMAP_PORT),
                "smtp_host": account.CUSTOM_SMTP_HOST,
                "smtp_port": str(account.CUSTOM_SMTP_PORT),
                "smtp_ssl_port": str(account.CUSTOM_SMTP_SSL_PORT),
                "smtp_use_ssl": str(account.CUSTOM_SMTP_USE_SSL).lower(),
            }
        return EMAIL_PROVIDER_CONFIGS.get(account.EMAIL_ACCOUNT, {})

    def _get_smtp_config(self, email_account: str) -> tuple[str, int]:
        """获取SMTP配置"""
        provider_config = self._get_provider_config(email_account)
        smtp_host = provider_config.get("smtp_host", "")
        smtp_port = int(provider_config.get("smtp_port", 587))
        return smtp_host, smtp_port

    def _get_smtp_config_for_account(self, account: EmailAccount) -> tuple[str, int]:
        """获取SMTP配置（支持自定义提供商）"""
        provider_config = self.get_provider_config_for_account(account)
        smtp_host = provider_config.get("smtp_host", "")
        smtp_port = int(provider_config.get("smtp_port", 587))
        return smtp_host, smtp_port

    def _post_login_imap(self, conn: imaplib.IMAP4, username: str, host: str) -> None:
        """IMAP登录后的处理"""
        # 检查是否是163邮箱，如果是则发送ID命令
        host_lower = str(host or "").lower()
        if any(domain in host_lower for domain in ["163.com", "126.com", "yeah.net"]):
            try:
                self._send_imap_id(conn, self._build_id_map(username))
                logger.debug(f"163邮箱 IMAP ID 发送成功: {username}")
            except Exception as e:
                logger.debug(f"163邮箱 IMAP ID 发送失败: {e!s}")

    def _build_id_map(self, account: str) -> dict:
        """构建 ID 参数"""
        return {
            "name": "nekro-agent",
            "version": "1.0.0",
            "vendor": "nekro-agent",
            "support-email": account,
        }

    def _send_imap_id(self, conn: imaplib.IMAP4, id_map: dict) -> None:
        """发送 IMAP ID 命令"""
        with suppress(Exception):
            # 注册 ID 命令
            imaplib.Commands["ID"] = ("AUTH", "SELECTED")

        # 构建 ID 参数
        kv = " ".join([f"{k!r} {v!r}" for k, v in id_map.items()])
        payload = f"({kv})"

        # 发送 ID 命令
        with suppress(Exception):
            conn._simple_command("ID", "NIL")  # noqa: SLF001

        typ, data = conn._simple_command("ID", payload)  # noqa: SLF001
        logger.debug(f"IMAP ID 返回: typ={typ} data={data}")

    def _pre_connect_smtp(self, smtp_host: str, smtp_port: int, _use_ssl: bool) -> tuple[str, int]:
        """SMTP连接前的预处理"""
        # 目前没有特殊的SMTP预处理需求
        return smtp_host, smtp_port

    def _apply_provider_smtp_preprocessing(self, _email_account: str, smtp_host: str, smtp_port: int) -> tuple[str, int]:
        """应用提供商的SMTP预处理"""
        # 检查是否需要特殊的SMTP预处理
        use_ssl = True  # 默认使用SSL
        return self._pre_connect_smtp(smtp_host, smtp_port, use_ssl)

    def get_chat_id_for_account(self, account_username: str) -> str:
        """获取邮箱账户对应的聊天ID"""
        return self.account_chat_mapping.get(account_username, f"email_{account_username}")

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """发送邮件

        Args:
            request: 包含要发送的邮件内容和目标地址

        Returns:
            PlatformSendResponse: 发送结果
        """
        try:
            # 查找启用发信的默认账户
            sender_account: Optional[EmailAccount] = None
            for account in self.config.RECEIVE_ACCOUNTS:
                if getattr(account, "SEND_ENABLED", False) and getattr(account, "IS_DEFAULT_SENDER", False):
                    sender_account = account
                    break

            # 如果没有默认发件人，则使用第一个启用发信的账户
            if not sender_account:
                for account in self.config.RECEIVE_ACCOUNTS:
                    if getattr(account, "SEND_ENABLED", False):
                        sender_account = account
                        break

            if not sender_account:
                return PlatformSendResponse(
                    success=False,
                    error_message="没有配置可用的发信账户",
                )

            client = self.email_clients.get(sender_account.USERNAME) or self._create_email_client(sender_account)

            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = sender_account.USERNAME
            # 注意：在邮箱适配器中，chat_key 必须是有效的邮箱地址，而非会话标识符
            # 这与其他适配器（如 onebot_v11）的 chat_key 语义不同，使用时需特别注意
            msg["To"] = request.chat_key  # chat_key 在邮箱适配器中表示收件人邮箱地址
            msg["Subject"] = "NekroAgent 消息"  # 可以从请求中获取主题

            # 添加文本内容
            text_content = ""
            for segment in request.segments:
                if segment.type == "text":
                    text_content += segment.content + "\n"

            msg.attach(MIMEText(text_content, "plain", "utf-8"))

            await client.send_message(msg)

            return PlatformSendResponse(success=True)

        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        # 邮箱适配器的自身信息就是默认发件人
        default_sender: Optional[EmailAccount] = None
        for account in self.config.RECEIVE_ACCOUNTS:
            if getattr(account, "IS_DEFAULT_SENDER", False):
                default_sender = account
                break

        if not default_sender:
            # 如果没有默认发件人，使用第一个账户
            if self.config.RECEIVE_ACCOUNTS:
                default_sender = self.config.RECEIVE_ACCOUNTS[0]
            else:
                # 如果没有任何账户，创建一个虚拟账户
                return PlatformUser(
                    platform_name="email",
                    user_id="email_bot",
                    user_name="Email Bot",
                    user_avatar="",
                )

        return PlatformUser(
            platform_name="email",
            user_id=getattr(default_sender, "USERNAME", "email_bot"),
            user_name=getattr(default_sender, "USERNAME", "Email Bot"),
            user_avatar="",
        )

    async def get_user_info(self, user_id: str, _channel_id: str) -> PlatformUser:
        """获取用户信息"""
        # 在邮箱适配器中，user_id就是邮箱地址
        return PlatformUser(
            platform_name="email",
            user_id=user_id,
            user_name=user_id,  # 可以从地址簿中查找真实姓名
            user_avatar="",
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        return PlatformChannel(
            channel_id=channel_id,
            channel_name=f"邮箱账户: {channel_id}",
            channel_type=ChatType.PRIVATE,  # 邮箱适配器默认是私聊
        )

    def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        # 设置适配器实例，以便路由器可以访问适配器状态
        set_email_adapter(self)
        return router

    def get_polling_status(self) -> dict:
        """获取轮询状态信息"""
        return {
            "polling_active": self._polling_active,
            "connected_accounts": len(self.email_clients),
            "poll_interval": self.config.POLL_INTERVAL,
            "accounts": list(self.email_clients.keys()),
        }

    async def get_raw_email_content(self, account_username: str, email_id: str, folder: str | None = None) -> dict:
        """获取邮件的原始内容

        Args:
            account_username: 邮箱账户用户名
            email_id: 邮件ID
            folder: 可选的邮箱文件夹名称，不指定则自动选择

        Returns:
            dict: 包含原始邮件内容的字典
        """
        if not self.email_clients:
            raise Exception("Adapter not initialized or no connections available")

        client = self.email_clients.get(account_username)
        if not client:
            raise Exception(f"Account {account_username} not found or not connected")

        async with self._account_lock(account_username):
            try:
                raw_content = await client.get_raw_email_content(email_id, folder)
                return {
                    "account": account_username,
                    "email_id": email_id,
                    "raw_email_base64": raw_content.raw_email_base64,
                    "raw_email_size": raw_content.raw_email_size,
                    "html_content": raw_content.html_content,
                    "text_content": raw_content.text_content,
                }
            except Exception as e:
                error_msg = f"Failed to get raw email content: {e!s}"
                raise Exception(error_msg) from e

    async def _download_attachment(
        self,
        part,
        filename: str,
        account_username: str,
        email_subject: str,
        email_uid: str | None = None,
    ) -> None:
        """下载邮件附件"""
        try:
            # 使用固定的附件保存目录，便于沙盒访问
            base_path = Path(OsEnv.DATA_DIR) / "uploads" / "email_attachment"
            # 保存到 DATA_DIR/uploads/email_attachment/{邮箱账户名}/{邮件UID}/ 目录下
            email_dir = (
                base_path / account_username / email_uid
                if email_uid
                else base_path / account_username / self._sanitize_filename(email_subject)[:50]
            )

            # 异步创建目录
            await asyncio.to_thread(email_dir.mkdir, parents=True, exist_ok=True)

            # 构造完整的文件路径
            file_path = email_dir / self._sanitize_filename(filename)

            # 异步获取附件数据（解码可能耗时）
            attachment_data = await asyncio.to_thread(part.get_payload, decode=True)

            # 异步写入文件
            if attachment_data:
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(attachment_data)
                logger.info(f"附件已下载: {file_path}")
            else:
                logger.warning(f"附件数据为空: {filename}")

        except Exception as e:
            logger.error(f"下载附件 {filename} 时出错: {e}")

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换文件名中的非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, "_")
        # 移除控制字符
        filename = "".join(ch for ch in filename if ord(ch) >= 32)
        # 限制文件名长度
        if len(filename) > 255:
            path = Path(filename)
            name = path.stem
            ext = path.suffix
            filename = name[: 255 - len(ext)] + ext
        return filename
