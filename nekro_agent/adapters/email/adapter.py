import asyncio
import base64
import email
import imaplib
import os
import re
import smtplib
import time
from email import encoders
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, mktime_tz, parseaddr, parsedate_to_datetime, parsedate_tz
from html.parser import HTMLParser
from typing import Dict, List, Optional, Type

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
from nekro_agent.core import config as core_config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.services.message_service import message_service

from .base import EMAIL_PROVIDER_CONFIGS
from .config import EmailAccount, EmailConfig
from .routers import router, set_email_adapter

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
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                # 如果已经是字符串，直接添加
                decoded_string += part
                
        return decoded_string
    except Exception as e:
        logger.warning(f"解码MIME字符串时出错: {e}")
        return s if isinstance(s, str) else ""


class _HTMLTextExtractor(HTMLParser):
    """简单提取HTML中的可见文字，避免在聊天中展示冗长的原始HTML"""

    _BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}

    def __init__(self):
        super().__init__()
        self._texts: List[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
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


class EmailAdapter(BaseAdapter[EmailConfig]):
    """邮箱适配器"""
    
    def __init__(self, config_cls: Type[EmailConfig] = EmailConfig):
        """初始化邮箱适配器"""
        super().__init__(config_cls)
        
        # 初始化邮箱提供商
        self.providers: List = []
        
        # IMAP连接池
        self.imap_connections: dict = {}
        
        # 邮箱账户到聊天ID的映射
        self.account_chat_mapping: Dict[str, str] = {}
        
        # 轮询任务
        self._polling_task: Optional[asyncio.Task] = None
        self._polling_active = False

    def _html_to_text(self, html_content: str) -> str:
        """提取HTML中的文字，去除标签/脚本，便于聊天展示"""
        extractor = _HTMLTextExtractor()
        try:
            extractor.feed(html_content)
        except Exception as exc:  # 防御解析异常
            logger.debug(f"解析HTML为文本时出错: {exc}")
        return extractor.get_text()
        
    @property
    def key(self) -> str:
        """适配器唯一标识"""
        return "email"
    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "邮箱：email-邮箱账户名（例如：email-123456@qq.com）"
        ]
    
    @property
    def metadata(self) -> AdapterMetadata:
        """适配器元数据"""
        return AdapterMetadata(
            name="Email",
            description="邮箱适配器，支持通过IMAP/SMTP协议收发邮件",
            version="1.0.0",
            author="liugu",
            homepage="https://github.com/nekro-agent/nekro-agent",
            tags=["email", "imap", "smtp", "mail"],
        )
    
    async def init(self) -> None:
        """初始化适配器"""
        logger.info("邮箱适配器初始化...")
        # 确保附件保存目录存在
        try:
            os.makedirs(os.path.join(OsEnv.DATA_DIR, "uploads"), exist_ok=True)
            logger.info("附件保存目录已创建: ./data/uploads")
        except Exception as e:
            logger.error(f"创建附件保存目录失败: {e}")
        
        # 初始化IMAP连接等操作
        await self._init_imap_connections()
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
        # 关闭所有IMAP连接
        for conn in self.imap_connections.values():
            try:
                conn.close()
                conn.logout()
            except Exception as e:
                logger.warning(f"关闭IMAP连接时出错: {e}")
        self.imap_connections.clear()
        logger.info("邮箱适配器清理完成")
    
    def _start_polling(self) -> None:
        """启动轮询任务"""
        if not self._polling_task or self._polling_task.done():
            self._polling_active = True
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
                # 输出轮询状态信息
                logger.info(f"邮箱适配器第 {poll_count} 次轮询开始，轮询间隔: {self.config.POLL_INTERVAL} 秒，已连接账户数: {len(self.imap_connections)}")
                
                # 检查每个账户的新邮件
                accounts_to_check = list(self.imap_connections.items())
                for account_username, conn in accounts_to_check:
                    if self._polling_active:
                        try:
                            await self._check_new_emails(account_username, conn)
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
    
    async def _get_mailbox_folders(self, account_username: str, conn: imaplib.IMAP4_SSL) -> List[str]:
        """获取邮箱文件夹列表"""
        try:
            # 获取文件夹列表
            status, folders = conn.list()
            if status == 'OK':
                folder_names = []
                for folder in folders:
                    try:
                        # 文件夹信息格式类似于: b'(\\HasNoChildren) "/" "INBOX"'
                        # 或者: b'(\\HasChildren) "/" "[Gmail]"'
                        folder_info = folder.decode()
                        
                        # 使用正则表达式提取文件夹名称
                        # 匹配引号内的内容
                        match = re.search(r'"([^"]+)"$', folder_info)
                        if match:
                            folder_name = match.group(1)
                            folder_names.append(folder_name)
                        else:
                            # 如果没有引号，尝试按空格分割
                            parts = folder_info.split()
                            if parts:
                                folder_name = parts[-1]
                                # 移除可能的引号
                                folder_name = folder_name.strip('"\'')
                                folder_names.append(folder_name)
                    except Exception as e:
                        logger.warning(f"解析文件夹信息时出错: {e}")
                        continue
                        
                logger.debug(f"账户 {account_username} 的文件夹列表: {folder_names}")
                return folder_names
            else:
                logger.warning(f"获取账户 {account_username} 文件夹列表失败: {status}")
                return []
        except Exception as e:
            logger.error(f"获取账户 {account_username} 文件夹列表时发生错误: {e}")
            return []
    
    async def _check_new_emails(self, account_username: str, conn: imaplib.IMAP4_SSL) -> None:
        """检查指定账户的新邮件"""
        try:
            # 获取文件夹列表
            folders = await self._get_mailbox_folders(account_username, conn)
            
            # 确定要检查的文件夹
            # 默认使用INBOX文件夹
            target_folder = "INBOX"
            
            # 如果INBOX文件夹不可用，使用第一个可用的文件夹
            if folders and target_folder not in folders and folders:
                target_folder = folders[0]
                logger.info(f"账户 {account_username} 使用第一个可用文件夹: {target_folder}")
            
            # 选择邮箱文件夹
            conn.select(target_folder)
            
            # 根据配置决定是否只检查未读邮件
            if self.config.FETCH_UNSEEN_ONLY:
                # 搜索未读邮件
                status, messages = conn.search(None, 'UNSEEN')
            else:
                # 搜索所有邮件
                status, messages = conn.search(None, 'ALL')
            
            if status == 'OK':
                email_ids = messages[0].split()
                if email_ids:
                    logger.info(f"账户 {account_username} 在文件夹 {target_folder} 中发现 {len(email_ids)} 封新邮件")
                    # 处理新邮件，但不超过配置的最大数量
                    max_emails = min(len(email_ids), self.config.MAX_PER_POLL)
                    for i in range(max_emails):
                        email_id = email_ids[i]
                        try:
                            await self._process_email(account_username, email_id, conn)
                        except Exception as e:
                            logger.error(f"处理邮件 {email_id} 时发生错误: {e}")
                            
                    # 如果配置了标记已读，则标记这些邮件为已读
                    if self.config.MARK_AS_SEEN_AFTER_FETCH and self.config.FETCH_UNSEEN_ONLY:
                        for i in range(max_emails):
                            email_id = email_ids[i]
                            conn.store(email_id, '+FLAGS', '\\Seen')
                else:
                    logger.debug(f"账户 {account_username} 在文件夹 {target_folder} 中没有新邮件")
            else:
                logger.warning(f"账户 {account_username} 邮件搜索失败: {status}")
                
        except Exception as e:
            logger.error(f"检查账户 {account_username} 邮件时发生错误: {e}")
            # 尝试重新连接
            # 查找对应的账户配置
            for account in self.config.RECEIVE_ACCOUNTS:
                if account.USERNAME == account_username and account.ENABLED:
                    logger.info(f"尝试重新连接账户 {account_username}")
                    if await self._reconnect_imap(account):
                        logger.info(f"账户 {account_username} 重新连接成功")
                    else:
                        logger.error(f"账户 {account_username} 重新连接失败")
                    break
    
    async def _process_email(
        self,
        account_username: str,
        email_id: bytes,
        conn,
    ) -> None:
        """处理单封邮件"""
        try:
            # 获取邮件内容
            status, msg_data = conn.fetch(email_id, "(RFC822)")
            if status == "OK":
                # 解析邮件
                email_message = email.message_from_bytes(msg_data[0][1])
                
                # 解码邮件主题
                subject = decode_mime_words(email_message.get("Subject", ""))
                decoded_subject = subject if subject else "无主题"
                
                # 解析发件人信息
                from_header = email_message.get("From", "")
                sender_name, sender_addr = parseaddr(from_header)
                
                # 解码发件人昵称（处理MIME编码）
                if sender_name:
                    # 尝试解码MIME编码的发件人昵称
                    decoded_sender_name = decode_mime_words(sender_name)
                    sender_name = decoded_sender_name if decoded_sender_name else sender_name
                
                # 获取邮件日期
                date_str = email_message.get("Date", "")
                
                # 解析邮件正文
                html_content = ""
                text_content = ""
                html_text_content = ""
                attachments = []
                
                if email_message.is_multipart():
                    for part in email_message.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition", ""))
                        
                        # 处理附件
                        if part.get_content_disposition() == "attachment":
                            decoded_filename = decode_mime_words(part.get_filename() or "unnamed_attachment")
                            attachments.append(decoded_filename)
                            
                            # 异步下载附件，不阻塞主线程
                            asyncio.create_task(self._download_attachment(part, decoded_filename, account_username, decoded_subject, email_id.decode()))
                        # 处理内联附件（如嵌入的图片）
                        elif part.get_content_disposition() == "inline":
                            decoded_filename = decode_mime_words(part.get_filename() or "unnamed_inline")
                            attachments.append(decoded_filename)
                            
                            # 异步下载附件，不阻塞主线程
                            asyncio.create_task(self._download_attachment(part, decoded_filename, account_username, decoded_subject, email_id.decode()))
                        # 处理邮件正文
                        elif content_type == "text/html":
                            charset = part.get_content_charset()
                            try:
                                # 获取负载数据
                                payload = part.get_payload(decode=True)
                                if isinstance(payload, bytes):
                                    html_content = payload.decode(charset or "utf-8", errors="ignore")
                                else:
                                    html_content = str(payload)
                            except Exception as e:
                                logger.warning(f"解码HTML内容时出错: {e}")
                                try:
                                    payload = part.get_payload()
                                    if isinstance(payload, bytes):
                                        html_content = payload.decode("utf-8", errors="ignore")
                                    else:
                                        html_content = str(payload)
                                except Exception:
                                    html_content = "[无法解析HTML内容]"
                        elif content_type == "text/plain":
                            charset = part.get_content_charset()
                            try:
                                # 获取负载数据
                                payload = part.get_payload(decode=True)
                                if isinstance(payload, bytes):
                                    text_content = payload.decode(charset or "utf-8", errors="ignore")
                                else:
                                    text_content = str(payload)
                            except Exception as e:
                                logger.warning(f"解码文本内容时出错: {e}")
                                try:
                                    payload = part.get_payload()
                                    if isinstance(payload, bytes):
                                        text_content = payload.decode("utf-8", errors="ignore")
                                    else:
                                        text_content = str(payload)
                                except Exception:
                                    text_content = "[无法解析文本内容]"
                else:
                    # 非多部分邮件
                    content_type = email_message.get_content_type()
                    charset = email_message.get_content_charset()
                    try:
                        # 获取负载数据
                        payload = email_message.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            content = payload.decode(charset or "utf-8", errors="ignore")
                        else:
                            content = str(payload)
                    except Exception as e:
                        logger.warning(f"解码非多部分邮件内容时出错: {e}")
                        try:
                            payload = email_message.get_payload()
                            if isinstance(payload, bytes):
                                content = payload.decode("utf-8", errors="ignore")
                            else:
                                content = str(payload)
                        except Exception:
                            content = "[无法解析邮件内容]"
                        
                    if content_type == "text/html":
                        html_content = content
                    elif content_type == "text/plain":
                        text_content = content

                # 将HTML转换为纯文本，避免在聊天中出现冗长HTML
                if html_content and not text_content:
                    html_text_content = self._html_to_text(html_content)
                elif html_content and text_content:
                    # 同时存在时也准备一份转换文本，后续可替换正文
                    html_text_content = self._html_to_text(html_content)
                
                # 构建消息内容
                content = f"主题: {decoded_subject}\n发件人: {sender_name} <{sender_addr}>\n日期: {date_str}\n\n"
                
                # 添加正文内容
                if text_content:
                    # 优先使用纯文本内容
                    content += text_content
                elif html_content:
                    # 使用转换后的HTML纯文本，避免直接暴露HTML源码
                    content += html_text_content or self._html_to_text(html_content)
                else:
                    # 如果都没有内容，添加占位符
                    content += "[无邮件正文内容]"
                
                # 添加附件信息到邮件内容
                if attachments:
                    content += f"\n\n附件 ({len(attachments)} 个):\n"
                    for attachment in attachments:
                        content += f"- {attachment}\n"
                # 生成时间戳
                try:
                    date_tuple = parsedate_tz(date_str)
                    if date_tuple:
                        timestamp = mktime_tz(date_tuple)
                    else:
                        timestamp = int(time.time())
                except Exception:
                    timestamp = int(time.time())
                
                # 获取聊天ID
                chat_id = self.account_chat_mapping.get(account_username, f"email_{account_username}")
                
                # 创建平台消息对象
                platform_message = PlatformMessage(
                    message_id=email_id.decode(),
                    sender_id=sender_addr,  # 使用解码后的邮箱地址
                    sender_name=sender_name,  # 使用解码后的发件人昵称
                    content_text=content,
                    is_self=False,
                    timestamp=timestamp,
                    ext_data=PlatformMessageExt(
                        raw_data=msg_data[0][1]  # 原始邮件数据
                    )
                )
                
                # 创建平台频道对象
                platform_channel = PlatformChannel(
                    channel_id=chat_id,
                    channel_name=f"邮箱账户: {account_username}",
                    channel_type="private"
                )
                
                # 创建平台用户对象
                platform_user = PlatformUser(
                    platform_name="email",
                    user_id=sender_addr,  # 使用解码后的邮箱地址
                    user_name=sender_name,  # 使用解码后的发件人昵称
                    user_avatar=""
                )
                
                # 将消息发送到核心引擎
                await collect_message(self, platform_channel, platform_user, platform_message)
                logger.info(f"成功处理账户 {account_username} 的邮件: {decoded_subject}")

                # 如果在适配器配置中启用了新邮件通知，则在指定聊天频道触发 AI 处理
                try:
                    if self.config.EMAIL_NOTIFICATIONS_ENABLED and self.config.EMAIL_NOTIFICATIONS_CHAT_KEY:
                        notify_chat_key = self.config.EMAIL_NOTIFICATIONS_CHAT_KEY
                        # 构造一条系统提示消息，简要描述新邮件，用于作为 AI 的输入
                        attachment_info = ""
                        if attachments:
                            attachment_info = f"\n附件: 有 {len(attachments)} 个附件\n附件名称: {', '.join(attachments)}"
                        else:
                            attachment_info = "\n附件: 无附件"

                        notify_text = (
                            f"[邮箱新邮件通知]\n"
                            f"收件账户: {account_username}\n"
                            f"邮件UID: {email_id.decode()}\n"
                            f"发件人: {sender_name} <{sender_addr}>\n"
                            f"主题: {decoded_subject}\n"
                            f"日期: {date_str}"
                            f"{attachment_info}\n\n"
                            f"邮件内容已同步到聊天 {chat_id}，你可以使用 get_email_content 方法获取完整内容。"
                        )
                        await message_service.push_system_message(
                            chat_key=notify_chat_key,
                            agent_messages=notify_text,
                            trigger_agent=True,
                        )
                        logger.info(
                            f"已根据配置在频道 {notify_chat_key} 触发 AI 处理邮箱新邮件，账户={account_username}, 主题={decoded_subject}",
                        )
                except Exception as notify_exc:
                    logger.error(f"触发邮箱新邮件通知失败: {notify_exc}")
            else:
                logger.warning(f"获取邮件 {email_id.decode()} 失败: {status}")
        except Exception as e:
            logger.error(f"处理邮件 {email_id.decode()} 时发生错误: {e}")
    
    def _init_account_chat_mapping(self) -> None:
        """初始化邮箱账户到聊天ID的映射"""
        for account in self.config.RECEIVE_ACCOUNTS:
            if account.ENABLED:
                # 为每个启用的邮箱账户创建唯一的聊天ID
                chat_id = account.USERNAME
                self.account_chat_mapping[account.USERNAME] = chat_id
                logger.info(f"邮箱账户 {account.USERNAME} 映射到聊天 {chat_id}")
    
    async def _init_imap_connections(self) -> None:
        """初始化IMAP连接"""
        for account in self.config.RECEIVE_ACCOUNTS:
            if not account.ENABLED:
                continue
                
            try:
                # 获取邮箱提供商配置
                provider_config = EMAIL_PROVIDER_CONFIGS.get(account.EMAIL_ACCOUNT, {})
                if not provider_config:
                    logger.warning(f"未知的邮箱提供商: {account.EMAIL_ACCOUNT}")
                    continue
                    
                imap_host = provider_config.get("imap_host")
                imap_port = int(provider_config.get("imap_port", 993))
                
                # 创建IMAP连接
                conn = imaplib.IMAP4_SSL(imap_host, imap_port)
                
                # 登录
                conn.login(account.USERNAME, account.PASSWORD)
                
                # 执行特定的登录后处理
                self._post_login_imap(conn, account.USERNAME, imap_host)
                
                # 保存连接
                self.imap_connections[account.USERNAME] = conn
                logger.info(f"IMAP连接建立成功: {account.USERNAME}")
                
            except Exception as e:
                logger.error(f"IMAP连接建立失败 ({account.USERNAME}): {e}")
    
    async def _reconnect_imap(self, account: EmailAccount) -> bool:
        """重新连接IMAP"""
        try:
            # 获取邮箱提供商配置
            provider_config = EMAIL_PROVIDER_CONFIGS.get(account.EMAIL_ACCOUNT, {})
            if not provider_config:
                logger.warning(f"未知的邮箱提供商: {account.EMAIL_ACCOUNT}")
                return False
                
            imap_host = provider_config.get("imap_host")
            imap_port = int(provider_config.get("imap_port", 993))
            
            # 关闭旧连接（如果存在）
            if account.USERNAME in self.imap_connections:
                try:
                    old_conn = self.imap_connections[account.USERNAME]
                    old_conn.close()
                    old_conn.logout()
                except Exception:
                    pass
            
            # 创建新IMAP连接
            conn = imaplib.IMAP4_SSL(imap_host, imap_port)
            
            # 登录
            conn.login(account.USERNAME, account.PASSWORD)
            
            # 执行特定的登录后处理
            self._post_login_imap(conn, account.USERNAME, imap_host)
            
            # 保存连接
            self.imap_connections[account.USERNAME] = conn
            logger.info(f"IMAP连接重新建立成功: {account.USERNAME}")
            return True
            
        except Exception as e:
            logger.error(f"IMAP连接重新建立失败 ({account.USERNAME}): {e}")
            return False
    
    def _get_provider_config(self, email_account: str) -> dict:
        """获取邮箱提供商配置"""
        return EMAIL_PROVIDER_CONFIGS.get(email_account, {})
    
    def _get_smtp_config(self, email_account: str) -> tuple[str, int]:
        """获取SMTP配置"""
        provider_config = self._get_provider_config(email_account)
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
        try:
            # 注册 ID 命令
            imaplib.Commands["ID"] = ("AUTH", "SELECTED")
        except Exception:
            pass
        
        # 构建 ID 参数
        kv = " ".join([f'"{k}" "{v}"' for k, v in id_map.items()])
        payload = f'({kv})'
        
        # 发送 ID 命令
        try:
            conn._simple_command("ID", "NIL")
        except Exception:
            pass
        
        typ, data = conn._simple_command("ID", payload)
        logger.debug(f"IMAP ID 返回: typ={typ} data={data}")
    
    def _pre_connect_smtp(self, smtp_host: str, smtp_port: int, use_ssl: bool) -> tuple[str, int]:
        """SMTP连接前的预处理"""
        # 目前没有特殊的SMTP预处理需求
        return smtp_host, smtp_port
    
    def _apply_provider_smtp_preprocessing(self, email_account: str, smtp_host: str, smtp_port: int) -> tuple[str, int]:
        """应用提供商的SMTP预处理"""
        # 获取邮箱提供商配置
        provider_config = self._get_provider_config(email_account)
        
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
                if account.SEND_ENABLED and account.IS_DEFAULT_SENDER:
                    sender_account = account
                    break
            
            # 如果没有默认发件人，则使用第一个启用发信的账户
            if not sender_account:
                for account in self.config.RECEIVE_ACCOUNTS:
                    if account.SEND_ENABLED:
                        sender_account = account
                        break
            
            if not sender_account:
                return PlatformSendResponse(
                    success=False, 
                    error_message="没有配置可用的发信账户"
                )
            
            # 获取SMTP配置
            smtp_host, smtp_port = self._get_smtp_config(sender_account.EMAIL_ACCOUNT)
            smtp_ssl_port = int(self._get_provider_config(sender_account.EMAIL_ACCOUNT).get("smtp_ssl_port", smtp_port))
            use_ssl_preferred = bool(self._get_provider_config(sender_account.EMAIL_ACCOUNT).get("smtp_use_ssl", False))
            
            # 应用提供商的SMTP预处理
            smtp_host, smtp_port = self._apply_provider_smtp_preprocessing(
                sender_account.EMAIL_ACCOUNT, smtp_host, smtp_port
            )
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = sender_account.USERNAME
            msg['To'] = request.chat_key  # 这里应该是收件人地址
            msg['Subject'] = "NekroAgent 消息"  # 可以从请求中获取主题
            
            # 添加文本内容
            text_content = ""
            for segment in request.segments:
                if segment.type == "text":
                    text_content += segment.content + "\n"
            
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            
            async def _send_mail(use_ssl: bool, port: int) -> None:
                def _sync_send() -> None:
                    if use_ssl:
                        with smtplib.SMTP_SSL(smtp_host, port, timeout=60) as server:
                            server.login(sender_account.USERNAME, sender_account.PASSWORD)
                            server.send_message(msg)
                    else:
                        with smtplib.SMTP(smtp_host, port, timeout=60) as server:
                            server.starttls()
                            server.login(sender_account.USERNAME, sender_account.PASSWORD)
                            server.send_message(msg)

                return await asyncio.to_thread(_sync_send)

            try:
                await _send_mail(use_ssl_preferred, smtp_ssl_port if use_ssl_preferred else smtp_port)
            except Exception:
                if not use_ssl_preferred:
                    await _send_mail(True, smtp_ssl_port)
                else:
                    raise
            
            return PlatformSendResponse(success=True)
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))
    
    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        # 邮箱适配器的自身信息就是默认发件人
        default_sender: Optional[EmailAccount] = None
        for account in self.config.RECEIVE_ACCOUNTS:
            if account.IS_DEFAULT_SENDER:
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
                    user_avatar=""
                )
        
        return PlatformUser(
            platform_name="email",
            user_id=default_sender.USERNAME,
            user_name=default_sender.USERNAME,
            user_avatar=""
        )
    
    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户信息"""
        # 在邮箱适配器中，user_id就是邮箱地址
        return PlatformUser(
            platform_name="email",
            user_id=user_id,
            user_name=user_id,  # 可以从地址簿中查找真实姓名
            user_avatar=""
        )
    
    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""    
        return PlatformChannel(
            channel_id=channel_id,
            channel_name=f"邮箱账户: {email_address}",
            channel_type="private"  # 邮箱适配器默认是私聊
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
            "connected_accounts": len(self.imap_connections),
            "poll_interval": self.config.POLL_INTERVAL,
            "accounts": list(self.imap_connections.keys())
        }
    
    async def get_raw_email_content(self, account_username: str, email_id: str) -> dict:
        """获取邮件的原始内容
        
        Args:
            account_username: 邮箱账户用户名
            email_id: 邮件ID
            
        Returns:
            dict: 包含原始邮件内容的字典
        """
        # 检查适配器是否已初始化
        if not self.imap_connections:
            raise Exception("Adapter not initialized or no connections available")
        
        # 查找账户对应的IMAP连接
        if account_username not in self.imap_connections:
            raise Exception(f"Account {account_username} not found or not connected")
        
        conn = self.imap_connections[account_username]
        
        try:
            # 获取邮件内容
            # email_id是字符串，需要转换为bytes
            email_id_bytes = email_id.encode() if isinstance(email_id, str) else email_id
            status, msg_data = conn.fetch(email_id_bytes, '(RFC822)')
            
            if status == 'OK':
                # 获取原始邮件数据
                raw_email_data = msg_data[0][1] if msg_data and msg_data[0] else b""
                
                # 将原始邮件数据转换为base64编码的字符串，便于传输
                raw_email_base64 = base64.b64encode(raw_email_data).decode('utf-8') if raw_email_data else ""
                
                # 解析邮件内容，提取HTML部分（如果存在）
                html_content = ""
                text_content = ""
                if raw_email_data:
                    email_message = email.message_from_bytes(raw_email_data)
                    
                    # 提取邮件正文
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/html":
                                charset = part.get_content_charset()
                                html_content = part.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
                            elif part.get_content_type() == "text/plain":
                                charset = part.get_content_charset()
                                text_content = part.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
                    else:
                        charset = email_message.get_content_charset()
                        if email_message.get_content_type() == "text/html":
                            html_content = email_message.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
                        elif email_message.get_content_type() == "text/plain":
                            text_content = email_message.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
                
                return {
                    "account": account_username,
                    "email_id": email_id,
                    "raw_email_base64": raw_email_base64,
                    "raw_email_size": len(raw_email_data) if raw_email_data else 0,
                    "html_content": html_content,
                    "text_content": text_content
                }
            else:
                raise Exception(f"Failed to fetch email: {status}")
                
        except Exception as e:
            raise Exception(f"Failed to get raw email content: {str(e)}")

    async def _download_attachment(self, part, filename: str, account_username: str, email_subject: str, email_uid: str = None) -> None:
        """下载邮件附件"""
        try:
            # 使用固定的附件保存目录，便于沙盒访问
            base_path = os.path.join(OsEnv.DATA_DIR, "uploads", "email_attachment")
            # 保存到 DATA_DIR/uploads/email_attachment/{邮箱账户名}/{邮件UID}/ 目录下
            email_dir = (
                os.path.join(base_path, account_username, email_uid)
                if email_uid
                else os.path.join(
                    base_path,
                    account_username,
                    self._sanitize_filename(email_subject)[:50],
                )
            )

            # 异步创建目录
            await asyncio.to_thread(os.makedirs, email_dir, exist_ok=True)

            # 构造完整的文件路径
            file_path = os.path.join(email_dir, self._sanitize_filename(filename))

            # 异步获取附件数据（解码可能耗时）
            attachment_data = await asyncio.to_thread(part.get_payload, decode=True)

            # 异步写入文件
            if attachment_data:
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(attachment_data)
                logger.info(f"附件已下载: {file_path}")

                # 这是AI能够访问的唯一路径
                onebot_server_path = None
                if core_config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR:
                    try:
                        # 计算相对于DATA_DIR的路径
                        relative_path = os.path.relpath(file_path, OsEnv.DATA_DIR)
                        # 构造OneBot服务器可访问的路径
                        onebot_server_path = os.path.join(core_config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR, relative_path)
                    except Exception as e:
                        logger.warning(f"计算OneBot服务器路径失败: {e}")
                else:
                    logger.info("未配置SANDBOX_ONEBOT_SERVER_MOUNT_DIR，AI无法访问附件")
            else:
                logger.warning(f"附件数据为空: {filename}")
                
        except Exception as e:
            logger.error(f"下载附件 {filename} 时出错: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换文件名中的非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        # 移除控制字符
        filename = ''.join(ch for ch in filename if ord(ch) >= 32)
        # 限制文件名长度
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        return filename
