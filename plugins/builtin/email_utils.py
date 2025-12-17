"""
# Email 工具插件 (Email Utils)

为 AI 提供完整的邮箱操作能力，包括获取账户信息、发送邮件、转发附件、查询邮件内容和总结邮件等功能。

## 主要功能

- **账户管理**: 查询当前配置的所有邮箱账户信息
- **邮件发送**: 使用指定或默认发件人账户发送邮件
- **附件转发**: 将邮件附件转发到任意聊天频道
- **邮件查询**: 获取指定邮件的详细内容（主题、正文、附件等）
- **邮件总结**: 使用 AI 模型总结最近的邮件内容

## 配置说明

- **默认总结模型组**: 用于总结邮件内容的默认模型组名称
- **最大总结邮件数**: 单次总结的最大邮件数量，默认 10 封

## Agent 可用工具 (Sandbox Methods)

### get_email_accounts
- 描述: 获取当前配置的所有邮箱账户信息
- 返回: 邮箱账户列表，包含账户地址、服务商、发信状态等信息
- 使用场景: 需要了解当前有哪些可用邮箱账户时调用

### send_email
- 描述: 发送邮件到指定收件人
- 参数:
  - `to_address` (str): 收件人邮箱地址
  - `subject` (str): 邮件主题
  - `content` (str): 邮件正文内容（纯文本格式）
  - `from_account` (str, 可选): 发件人邮箱地址，不指定则使用默认发件人
- 返回: 包含 success 状态、发送信息的字典
- 注意: 确保发件人账户已启用发信功能

### send_email_attachment
- 描述: 将邮件附件转发到指定的聊天频道
- 参数:
  - `account_username` (str): 邮箱账户地址（附件所属的邮箱）
  - `email_id` (str): 邮件 UID
  - `attachment_filename` (str): 附件文件名
  - `chat_key` (str): 目标聊天频道标识（如 onebot_v11-group_123456）
- 返回: 包含 success 状态、发送信息的字典
- 注意:
  - 附件会先从邮件存储位置复制到目标频道的上传目录
  - 确保目标适配器的挂载配置正确
  - 图片类型附件会自动识别并以图片形式发送

### summarize_recent_emails
- 描述: 使用 AI 模型总结最近 1 天内的邮件
- 参数:
  - `model_group` (str, 可选): 使用的模型组名称，不指定则使用插件配置的默认模型组
  - `count` (int, 可选): 要总结的邮件数量，不指定则使用插件配置的最大数量
  - `account_filter` (str, 可选): 只总结指定邮箱账户的邮件，不指定则总结所有账户
- 返回: AI 生成的邮件摘要文本
- 注意:
  - 总结内容包括每封邮件的发件人、主题、内容摘要和附件列表
  - 邮件正文会被截断到配置的最大长度以控制 token 消耗
  - 除非用户明确指定某个邮箱，否则默认总结所有邮箱的邮件

### get_email_content
- 描述: 获取指定邮件的完整详细内容
- 参数:
  - `account_username` (str): 邮箱账户地址
  - `email_id` (str): 邮件 UID
- 返回: 包含邮件详细信息的字典，包括：
  - `subject`: 邮件主题
  - `sender`: 发件人
  - `date`: 发送日期
  - `text_content`: 纯文本正文
  - `html_content`: HTML 正文
  - `attachments`: 附件列表（包含文件名和路径信息）
- 使用场景: 需要查看邮件的完整内容或准备转发附件时使用
"""

import asyncio
import email
import imaplib
import os
import re
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import magic
from pydantic import Field

from nekro_agent.adapters.email.base import EMAIL_PROVIDER_CONFIGS
from nekro_agent.adapters.email.config import EmailAccount
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformSendRequest,
    PlatformSendSegment,
    PlatformSendSegmentType,
)
from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger
from nekro_agent.core.config import config as core_config
from nekro_agent.core.os_env import OsEnv, USER_UPLOAD_DIR
from nekro_agent.services.agent.openai import gen_openai_chat_response
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin
from nekro_agent.services.plugin.schema import SandboxMethodType


# 创建插件实例
plugin = NekroPlugin(
    name="Email适配器工具插件",
    module_name="email_utils",
    description="邮箱工具插件，提供获取邮箱账户、发送邮件和总结邮件功能",
    version="1.0.0",
    author="liugu",
    url="https://github.com/nekro-agent/nekro-agent",
    #support_adapter=["email", "onebot_v11"],
    is_builtin=True,
)


@plugin.mount_config()
class EmailUtilsConfig(ConfigBase):
    """邮箱工具插件配置"""

    DEFAULT_SUMMARY_MODEL_GROUP: str = Field(
        default="default",
        title="默认总结模型组",
        description="用于总结邮件内容的默认模型组名称",
        json_schema_extra={
            "ref_model_groups": True,
            "required": True,
            "model_type": "chat",
        },
    )

    MAX_EMAILS_FOR_SUMMARY: int = Field(
        default=10,
        title="最大总结邮件数",
        description="单次总结的最大邮件数量"
    )


# 获取配置实例
config: EmailUtilsConfig = plugin.get_config(EmailUtilsConfig)

# 附件根目录（绝对路径，限制访问范围）
ATTACHMENT_BASE_DIR = Path(OsEnv.DATA_DIR) / "uploads" / "email_attachment"

# 统一限制每封邮件用于总结的正文长度，防止提示过长
_SUMMARY_CONTENT_LIMIT = 1000


def _trim_text(text: Optional[str], limit: int = _SUMMARY_CONTENT_LIMIT) -> str:
    """限制文本长度，超出部分截断并追加省略号"""
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _ensure_attachment_path(account_username: str, email_id: str, attachment_filename: str) -> Path:
    """构造并校验附件在宿主机的路径，防止路径穿越"""
    if not attachment_filename:
        raise ValueError("附件文件名不能为空")
    safe_filename = _sanitize_filename(attachment_filename)
    base_dir = ATTACHMENT_BASE_DIR.resolve()
    candidate = (ATTACHMENT_BASE_DIR / account_username / email_id / safe_filename).resolve()
    if candidate == base_dir or base_dir not in candidate.parents:
        raise ValueError("非法的附件访问路径")
    return candidate


@plugin.mount_sandbox_method(
    method_type=SandboxMethodType.TOOL,
    name="send_email_attachment",
    description="发送邮件附件到聊天频道"
)
async def send_email_attachment(_ctx: AgentCtx, account_username: str, email_id: str, attachment_filename: str, chat_key: str) -> Dict[str, Any]:
    """
    将邮件附件转发到指定的聊天频道。

    此方法会从邮件存储位置复制附件到目标频道的上传目录，然后通过适配器发送。
    系统会自动识别文件类型（图片/普通文件）并使用相应的方式发送。

    注意:
        - 附件必须已经下载到本地邮件存储目录
        - 目标聊天频道的适配器必须支持文件发送功能
        - 对于 Docker 环境，确保 NEKRO_DATA_DIR 和适配器挂载配置正确

    参数:
        account_username (str): 邮箱账户地址，例如 "user@qq.com"，用于定位附件所属的邮箱
        email_id (str): 邮件的唯一标识符 (UID)，用于定位附件所属的邮件
        attachment_filename (str): 附件的文件名，必须与实际保存的文件名完全匹配
        chat_key (str): 目标聊天频道标识，格式为 "adapter_key-channel_id"，例如 "onebot_v11-group_123456"

    返回:
        Dict[str, Any]: 包含以下字段的字典:
            - success (bool): 操作是否成功
            - message (str): 操作结果描述信息
            - filename (str): 附件的文件名
    """
    try:
        host_path = _ensure_attachment_path(account_username, email_id, attachment_filename)  
  
        if not host_path.exists():
            raise FileNotFoundError(f"附件文件不存在: {host_path}")

        # 使用原始文件名（已经经过 _sanitize_filename 清理）
        safe_filename = attachment_filename

        # 复制文件到目标聊天的上传目录
        upload_dir = Path(USER_UPLOAD_DIR).resolve() / chat_key
        upload_dir.mkdir(parents=True, exist_ok=True)
        target_path = upload_dir / safe_filename

        # 异步复制文件
        async with aiofiles.open(host_path, "rb") as src_file:
            content = await src_file.read()
        async with aiofiles.open(target_path, "wb") as target_file:
            await target_file.write(content)
        target_path.chmod(0o755)

        logger.info(f"[附件发送] 文件复制到宿主机: {target_path}")
        logger.info(f"[附件发送] 参数 chat_key: {chat_key}")
        logger.info(f"[附件发送] _ctx.chat_key: {_ctx.chat_key}")
        logger.info(f"[附件发送] target_path 是否存在: {target_path.exists()}")

        # 检测文件类型
        async with aiofiles.open(target_path, "rb") as f:
            file_data = await f.read()
            mime_type = magic.from_buffer(file_data, mime=True)
            is_image = mime_type.startswith("image/")

        # 构造发送请求
        # 需要传入相对于项目根目录的相对路径，因为 OneBot 适配器需要计算相对于 DATA_DIR 的路径
        # target_path 是绝对路径，需要转换为相对路径
        relative_path = target_path.relative_to(os.getcwd())

        segment_type = PlatformSendSegmentType.IMAGE if is_image else PlatformSendSegmentType.FILE
        request = PlatformSendRequest(
            chat_key=chat_key,
            segments=[
                PlatformSendSegment(
                    type=segment_type,
                    file_path=str(relative_path),  # 使用相对路径
                )
            ],
        )

        # 获取适配器并发送
        adapter = adapter_utils.get_adapter(_ctx.adapter_key)
        response = await adapter.forward_message(request)

        if not response.success:
            raise Exception(f"适配器发送失败: {response.error_message}")

        return {
            "success": True,
            "message": f"附件已发送: {attachment_filename}",
            "filename": attachment_filename
        }  
    except Exception as e:  
        logger.error(f"发送邮件附件失败: {e}")  
        return {  
            "success": False,  
            "message": f"发送邮件附件失败: {str(e)}",  
            "filename": attachment_filename  
        }
@plugin.mount_sandbox_method(
    method_type=SandboxMethodType.TOOL,
    name="get_email_accounts",
    description="获取当前所有邮箱账户信息"
)
async def get_email_accounts(_ctx: AgentCtx) -> List[Dict[str, Any]]:
    """
    获取当前系统配置的所有邮箱账户信息。

    此方法返回所有已启用的邮箱账户列表，包括账户的基本信息和状态。
    可用于查看当前有哪些可用的邮箱账户，以及哪些账户可以用于发送邮件。

    注意:
        - 只返回已启用的邮箱账户（ENABLED=True）
        - 未启用的账户不会出现在返回列表中

    返回:
        List[Dict[str, Any]]: 邮箱账户列表，每个账户包含以下字段:
            - email_address (str): 邮箱地址
            - provider (str): 邮箱服务商名称（如 "QQ邮箱"、"163邮箱"）
            - send_enabled (bool): 是否启用发信功能
            - is_default_sender (bool): 是否为默认发件人
    """
    try:
        # 获取邮箱适配器
        email_adapter = adapter_utils.get_adapter("email")
        if not email_adapter:
            raise Exception("邮箱适配器未启用或未找到")
        
        # 获取配置
        config = email_adapter.config
        
        # 返回账户信息
        accounts = []
        for account in config.RECEIVE_ACCOUNTS:
            if account.ENABLED:
                accounts.append({
                    "email_address": account.USERNAME,
                    "provider": account.EMAIL_ACCOUNT,
                    "send_enabled": account.SEND_ENABLED,
                    "is_default_sender": account.IS_DEFAULT_SENDER
                })
        
        return accounts
    except Exception as e:
        logger.error(f"获取邮箱账户信息失败: {e}")
        raise


@plugin.mount_sandbox_method(
    method_type=SandboxMethodType.TOOL,
    name="send_email",
    description="发送邮件"
)
async def send_email(_ctx: AgentCtx, to_address: str, subject: str, content: str, from_account: Optional[str] = None) -> Dict[str, Any]:
    """
    使用指定或默认的发件人账户发送邮件。

    此方法通过 SMTP 协议发送邮件，支持自动选择发件人账户。如果不指定发件人，
    系统会按以下顺序查找：默认发件人 > 第一个启用发信的账户。

    注意:
        - 发件人账户必须启用发信功能（SEND_ENABLED=True）
        - 邮件内容为纯文本格式，不支持 HTML
        - 系统会自动尝试使用 SSL 或 TLS 连接
        - 确保发件人账户的密码/授权码正确配置

    参数:
        to_address (str): 收件人邮箱地址，必须是有效的邮箱格式
        subject (str): 邮件主题，不能为空
        content (str): 邮件正文内容，纯文本格式
        from_account (str, 可选): 发件人邮箱地址，不指定则使用默认发件人

    返回:
        Dict[str, Any]: 包含以下字段的字典:
            - success (bool): 发送是否成功
            - message (str): 操作结果描述
            - from (str): 实际使用的发件人地址
            - to (str): 收件人地址
            - subject (str): 邮件主题
    """
    try:
        # 获取邮箱适配器
        email_adapter = adapter_utils.get_adapter("email")
        if not email_adapter:
            raise Exception("邮箱适配器未启用或未找到")
        
        # 获取配置
        email_config = email_adapter.config
        
        # 查找发件人账户
        sender_account: Optional[EmailAccount] = None
        if from_account:
            for account in email_config.RECEIVE_ACCOUNTS:
                if account.USERNAME == from_account and account.SEND_ENABLED:
                    sender_account = account
                    break
        else:
            # 查找默认发件人
            for account in email_config.RECEIVE_ACCOUNTS:
                if account.SEND_ENABLED and account.IS_DEFAULT_SENDER:
                    sender_account = account
                    break
            # 如果没有默认发件人，则使用第一个启用发信的账户
            if not sender_account:
                for account in email_config.RECEIVE_ACCOUNTS:
                    if account.SEND_ENABLED:
                        sender_account = account
                        break
        
        if not sender_account:
            raise Exception("没有找到可用的发件人账户")
        
        # 获取SMTP配置
        provider_config = EMAIL_PROVIDER_CONFIGS.get(sender_account.EMAIL_ACCOUNT, {})
        smtp_host = provider_config.get("smtp_host", "")
        smtp_port = int(provider_config.get("smtp_port", 587))
        smtp_ssl_port = int(provider_config.get("smtp_ssl_port", smtp_port))
        # 将字符串 "true"/"false" 转换为布尔值
        use_ssl_str = provider_config.get("smtp_use_ssl", "false").lower()
        use_ssl_preferred = use_ssl_str == "true"
        
        if not smtp_host:
            raise Exception(f"未找到 {sender_account.EMAIL_ACCOUNT} 的SMTP配置")
        
        # 创建邮件
        msg = MIMEMultipart()
        msg["From"] = sender_account.USERNAME
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "plain", "utf-8"))
        
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
        except Exception as e:
            # 只在连接/认证错误时重试，避免邮件重复发送
            error_msg = str(e).lower()
            error_str = str(e)

            # QQ 邮箱等可能在邮件发送成功后返回特殊响应码（如 -1）
            # 这种情况下邮件实际已发送，不应重试
            if "(-1," in error_str:
                logger.warning(f"邮件可能已发送成功，但收到特殊响应码: {e}")
                # 不抛出异常，视为发送成功
            elif not use_ssl_preferred and ("connect" in error_msg or "ssl" in error_msg or "tls" in error_msg or "certificate" in error_msg):
                # 只在连接相关错误时尝试 SSL
                logger.info(f"非 SSL 连接失败，尝试使用 SSL 连接: {e}")
                await _send_mail(True, smtp_ssl_port)
            else:
                # 其他错误直接抛出
                raise
        
        return {
            "success": True,
            "message": "邮件发送成功",
            "from": sender_account.USERNAME,
            "to": to_address,
            "subject": subject
        }
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return {
            "success": False,
            "message": f"邮件发送失败: {str(e)}",
            "from": from_account or "unknown",
            "to": to_address,
            "subject": subject
        }


@plugin.mount_sandbox_method(
    method_type=SandboxMethodType.AGENT,
    name="summarize_recent_emails",
    description="调用指定模型组总结最近1天内的特定数量条邮件"
)
async def summarize_recent_emails(_ctx: AgentCtx, model_group: Optional[str] = None, count: Optional[int] = None, account_filter: Optional[str] = None) -> str:
    """
    使用 AI 模型总结最近 1 天内收到的邮件内容。

    此方法会搜索最近 1 天内的邮件，按时间倒序排列后选取指定数量的邮件，
    然后使用指定的模型组生成简洁的摘要。摘要包括每封邮件的发件人、主题、
    内容概要和附件列表（如有）。

    注意:
        - 邮件正文会被截断到 1000 字符以控制 token 消耗
        - 只会总结已启用账户的邮件
        - 除非用户明确指定某个邮箱，否则默认总结所有邮箱的邮件
        - 确保指定的模型组已在系统中配置

    参数:
        model_group (str, 可选): 使用的模型组名称，不指定则使用插件配置的默认模型组
        count (int, 可选): 要总结的邮件数量，不指定则使用插件配置的最大数量（默认 10）
        account_filter (str, 可选): 只总结指定邮箱账户的邮件，不指定则总结所有启用账户的邮件

    返回:
        str: AI 生成的邮件摘要文本，每封邮件包含：
            - 序号和邮箱账户
            - 发件人
            - 主题
            - 内容摘要
            - 邮件 UID（用于后续操作）
            - 附件列表（如有）
    """
    try:
        # 使用插件配置中的默认值
        if model_group is None:
            model_group = config.DEFAULT_SUMMARY_MODEL_GROUP
        if count is None:
            count = config.MAX_EMAILS_FOR_SUMMARY
            
        # 获取邮箱适配器
        email_adapter = adapter_utils.get_adapter("email")
        if not email_adapter:
            raise Exception("邮箱适配器未启用或未找到")
        
        # 获取配置
        email_config = email_adapter.config
        
        # 筛选账户
        accounts_to_check = []
        for account in email_config.RECEIVE_ACCOUNTS:
            if account.ENABLED:
                if account_filter is None or account.USERNAME == account_filter:
                    accounts_to_check.append(account)
        
        if not accounts_to_check:
            raise Exception("没有找到符合条件的邮箱账户")
        
        # 收集最近1天的邮件
        recent_emails = []
        one_day_ago = datetime.now() - timedelta(days=1)
        timestamp_one_day_ago = one_day_ago.timestamp()
        
        # 遍历每个账户的IMAP连接
        for account in accounts_to_check:
            account_username = account.USERNAME
            if account_username in email_adapter.imap_connections:
                conn = email_adapter.imap_connections[account_username]
                try:
                    status, folders = conn.list()
                    target_folder = "INBOX"
                    if status == 'OK' and folders:
                        folder_names = []
                        for folder in folders:
                            info = folder.decode()
                            m = re.search(r'"([^"]+)"$', info)
                            if m:
                                folder_names.append(m.group(1))
                            else:
                                parts = info.split()
                                if parts:
                                    folder_names.append(parts[-1].strip('"\''))
                        if folder_names and target_folder not in folder_names:
                            target_folder = folder_names[0]
                    conn.select(target_folder)

                    search_criteria = f'SINCE {one_day_ago.strftime("%d-%b-%Y")}'
                    status, messages = conn.search(None, search_criteria)

                    if status == 'OK':
                        email_ids = messages[0].split()
                        email_ids = email_ids[-count:] if len(email_ids) > count else email_ids

                        tasks = []
                        for email_id in email_ids:
                            task = asyncio.create_task(_fetch_email_content(_ctx, conn, account_username, email_id, timestamp_one_day_ago))
                            tasks.append(task)

                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        for result in results:
                            if isinstance(result, Exception):
                                logger.warning(f"获取邮件内容时出错: {result}")
                            elif result is not None:
                                recent_emails.append(result)

                except Exception as e:
                    logger.error(f"搜索账户 {account_username} 的邮件时出错: {e}")
        
        # 按时间排序并限制数量
        recent_emails.sort(key=lambda x: x['date'], reverse=True)
        recent_emails = recent_emails[:count]
        
        if not recent_emails:
            return "没有找到最近1天内的邮件"
        
        # 构造总结提示词（仅总结内容、邮箱账户、邮件UID；附件路径由单条查询方法提供）
        summary_prompt = "请总结以下邮件内容，为每封邮件提供简短摘要，并标明邮箱账户与对应的邮件UID（无需包含附件保存位置，若有附件仅列文件名），不要使用markdown格式:\n\n"
        for i, email_info in enumerate(recent_emails, 1):
            summary_prompt += f"{i}. 来自邮箱账户 {email_info['account']} 的邮件\n"
            summary_prompt += f"   发件人: {email_info['sender']}\n"
            summary_prompt += f"   主题: {email_info['subject']}\n"
            summary_prompt += f"   内容: {email_info['content']}\n"
            if email_info.get('uid'):
                summary_prompt += f"   邮件UID: {email_info['uid']}\n"
            if email_info['attachments']:
                att_names = []
                for att in email_info['attachments']:
                    name = att.get('filename') if isinstance(att, dict) else att
                    if name:
                        att_names.append(name)
                if att_names:
                    summary_prompt += f"   附件: {', '.join(att_names)}\n"
            summary_prompt += "\n"
        
        try:
            model_group_config = core_config.MODEL_GROUPS[model_group]
        except KeyError:
            raise Exception(f"模型组 '{model_group}' 未找到，请检查配置")
        
        # 调用模型生成摘要
        try:
            response = await gen_openai_chat_response(
                model=model_group_config.CHAT_MODEL,
                messages=[{"role": "user", "content": summary_prompt}],
                base_url=model_group_config.BASE_URL,
                api_key=model_group_config.API_KEY,
                stream_mode=False,
            )
            return response.response_content
        except Exception as e:
            logger.error(f"调用模型生成摘要失败: {e}")
            raise Exception(f"调用模型生成摘要失败: {str(e)}")
        
    except Exception as e:
        logger.error(f"总结邮件失败: {e}")
        return f"邮件总结失败: {str(e)}"


def _sanitize_filename(filename: str) -> str:
    illegal_chars = '<>:"/\\|?*'
    for ch in illegal_chars:
        filename = filename.replace(ch, '_')
    filename = ''.join(ch for ch in filename if ord(ch) >= 32)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename

async def _fetch_email_content(_ctx: AgentCtx, conn, account_username, email_id, timestamp_one_day_ago):
    """异步获取单封邮件内容"""
    try:
        # 获取邮件
        status, msg_data = conn.fetch(email_id, '(RFC822)')
        if status == 'OK':
            # 解析邮件
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # 获取邮件时间
            date_str = email_message.get('Date')
            if date_str:
                try:
                    email_date = email.utils.parsedate_to_datetime(date_str)
                    if email_date.timestamp() >= timestamp_one_day_ago:
                        # 提取邮件基本信息
                        subject = email_message.get('Subject', '')
                        sender = email_message.get('From', '')
                        
                        # 解码主题
                        if subject:
                            decoded_parts = email.header.decode_header(subject)
                            subject = ''.join([
                                part.decode(encoding or 'utf-8') if isinstance(part, bytes) else str(part)
                                for part, encoding in decoded_parts
                            ])
                        
                        # 提取邮件正文
                        content = ""
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        charset = part.get_content_charset() or 'utf-8'
                                        content = payload.decode(charset, errors='ignore')
                                        break
                        else:
                            payload = email_message.get_payload(decode=True)
                            if payload:
                                charset = email_message.get_content_charset() or 'utf-8'
                                content = payload.decode(charset, errors='ignore')
                        
                        attachments = []
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_disposition() == "attachment":
                                    filename = part.get_filename()
                                    if filename:
                                        decoded_parts = email.header.decode_header(filename)
                                        filename = ''.join([
                                            part.decode(encoding or 'utf-8') if isinstance(part, bytes) else str(part)
                                            for part, encoding in decoded_parts
                                        ])
                                        host_path = _ensure_attachment_path(account_username, email_id.decode(), filename)
                                        onebot_server_path = None
                                        if core_config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR:
                                            try:
                                                rel = os.path.relpath(str(host_path), OsEnv.DATA_DIR)
                                                onebot_server_path = os.path.join(core_config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR, rel)
                                            except Exception:
                                                onebot_server_path = None

                                        attachments.append({
                                            "filename": filename,
                                            "host_path": str(host_path),
                                            "onebot_server_path": onebot_server_path
                                        })
                        
                        return {
                            "account": account_username,
                            "subject": subject,
                            "sender": sender,
                            "date": email_date.isoformat(),
                            "content": _trim_text(content, _SUMMARY_CONTENT_LIMIT),
                            "attachments": attachments,
                            "uid": email_id.decode()
                        }
                except Exception as e:
                    logger.warning(f"解析邮件日期时出错: {e}")
    except Exception as e:
        logger.warning(f"获取邮件 {email_id.decode()} 时出错: {e}")
    
    return None


@plugin.mount_sandbox_method(
    method_type=SandboxMethodType.TOOL,
    name="get_email_content",
    description="获取指定邮箱和邮件ID的邮件内容"
)
async def get_email_content(_ctx: AgentCtx, account_username: str, email_id: str) -> Dict[str, Any]:
    """
    获取指定邮件的完整详细内容。

    此方法返回邮件的所有详细信息，包括主题、发件人、发送时间、正文内容
    （纯文本和 HTML 格式）以及附件列表。适用于需要查看邮件完整内容或
    准备转发附件的场景。

    注意:
        - 邮箱账户必须已启用且已成功连接到 IMAP 服务器
        - 邮件 ID (UID) 必须存在且可访问
        - HTML 内容可能包含大量文本，注意 token 消耗
        - 附件信息包含文件名和路径，可用于 send_email_attachment 方法

    参数:
        account_username (str): 邮箱账户地址，例如 "user@qq.com"
        email_id (str): 邮件的唯一标识符 (UID)

    返回:
        Dict[str, Any]: 包含以下字段的字典:
            - success (bool): 操作是否成功
            - account (str): 邮箱账户地址
            - email_id (str): 邮件 UID
            - subject (str): 邮件主题
            - sender (str): 发件人信息（格式为 "名称 <邮箱地址>"）
            - date (str): 发送日期时间
            - text_content (str): 纯文本格式的邮件正文
            - html_content (str): HTML 格式的邮件正文
            - has_attachments (bool): 是否包含附件
            - attachment_count (int): 附件数量
            - attachment_names (List[str]): 附件文件名列表
            - attachments (List[Dict]): 详细附件信息列表，每个附件包含:
                - filename (str): 附件文件名
                - onebot_server_path (str): OneBot 服务器可访问的路径（如适用）
    """
    try:
        # 获取邮箱适配器
        email_adapter = adapter_utils.get_adapter("email")
        if not email_adapter:
            raise Exception("邮箱适配器未启用或未找到")
        
        # 检查账户是否存在且已连接
        if account_username not in email_adapter.imap_connections:
            raise Exception(f"账户 {account_username} 未连接或不存在")
        
        conn = email_adapter.imap_connections[account_username]

        status, folders = conn.list()
        target_folder = "INBOX"
        if status == 'OK' and folders:
            folder_names = []
            for folder in folders:
                info = folder.decode()
                m = re.search(r'"([^"]+)"$', info)
                if m:
                    folder_names.append(m.group(1))
                else:
                    parts = info.split()
                    if parts:
                        folder_names.append(parts[-1].strip('"\''))
            if folder_names and target_folder not in folder_names:
                target_folder = folder_names[0]
        conn.select(target_folder)

        status, msg_data = conn.fetch(email_id.encode(), '(RFC822)')
        if status != 'OK':
            raise Exception(f"获取邮件 {email_id} 失败")
        
        # 解析邮件
        raw_email = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email)
        
        # 提取邮件基本信息
        subject = email_message.get('Subject', '')
        sender = email_message.get('From', '')
        date_str = email_message.get('Date', '')
        
        # 解码主题
        if subject:
            decoded_parts = email.header.decode_header(subject)
            subject = ''.join([
                part.decode(encoding or 'utf-8') if isinstance(part, bytes) else str(part)
                for part, encoding in decoded_parts
            ])
        
        # 解码发件人
        if sender:
            decoded_parts = email.header.decode_header(sender)
            sender = ''.join([
                part.decode(encoding or 'utf-8') if isinstance(part, bytes) else str(part)
                for part, encoding in decoded_parts
            ])
        
        # 提取邮件正文
        html_content = ""
        text_content = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # 处理邮件正文
                if content_type == "text/html" and "attachment" not in content_disposition:
                    charset = part.get_content_charset()
                    try:
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
                elif content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset()
                    try:
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
        
        # 提取附件信息（包含保存位置）
        attachments = []
        attachment_names = []
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_disposition() == "attachment":
                    filename = part.get_filename()
                    if filename:
                        decoded_parts = email.header.decode_header(filename)
                        filename = ''.join([
                            part.decode(encoding or 'utf-8') if isinstance(part, bytes) else str(part)
                            for part, encoding in decoded_parts
                        ])
                        attachment_names.append(filename)
                        host_path = _ensure_attachment_path(account_username, email_id, filename)
                        onebot_server_path = None
                        if core_config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR:
                            try:
                                rel = os.path.relpath(str(host_path), OsEnv.DATA_DIR)
                                onebot_server_path = os.path.join(core_config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR, rel)
                            except Exception:
                                onebot_server_path = None
                        attachments.append({
                            "filename": filename,
                            "onebot_server_path": onebot_server_path
                        })

        return {
            "success": True,
            "account": account_username,
            "email_id": email_id,
            "subject": subject,
            "sender": sender,
            "date": date_str,
            "text_content": text_content,
            "html_content": html_content,
            "has_attachments": len(attachments) > 0,
            "attachment_count": len(attachments),
            "attachment_names": attachment_names,
            "attachments": attachments
        }
    except Exception as e:
        logger.error(f"获取邮件内容失败: {e}")
        return {
            "success": False,
            "message": f"获取邮件内容失败: {str(e)}"
        }
