from email.message import EmailMessage
from pathlib import Path

from aiosmtplib import send
from jinja2 import Environment, FileSystemLoader
from nonebot import logger

from nekro_agent.adapters.email.base import EMAIL_PROVIDER_CONFIGS
from nekro_agent.adapters.email.config import EmailAccount, EmailConfig
from nekro_agent.core.config import config
from nekro_agent.core.os_env import OsEnv

env = Environment(loader=FileSystemLoader("nekro_agent/services/mail"), auto_reload=False, enable_async=True)


def _load_email_adapter_config() -> EmailConfig:
    adapter_config_path = Path(OsEnv.DATA_DIR) / "configs" / "email" / "config.yaml"
    return EmailConfig.load_config(file_path=adapter_config_path, auto_register=False)


def _get_provider_config_for_account(account: EmailAccount) -> dict[str, str]:
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


def _get_runtime_mail_settings() -> dict:
    email_config = _load_email_adapter_config()

    enabled = bool(email_config.STATUS_MAIL_ENABLED or config.MAIL_ENABLED)
    sender_account = next(
        (
            account
            for account in email_config.RECEIVE_ACCOUNTS
            if account.USERNAME == email_config.STATUS_MAIL_SENDER_ACCOUNT and account.SEND_ENABLED
        ),
        None,
    )
    username = sender_account.USERNAME if sender_account else config.MAIL_USERNAME
    password = sender_account.PASSWORD if sender_account else config.MAIL_PASSWORD
    targets = (
        [item.EMAIL for item in email_config.STATUS_MAIL_TARGETS if item.EMAIL.strip()]
        if email_config.STATUS_MAIL_TARGETS
        else config.MAIL_TARGET
    )
    if sender_account:
        provider_config = _get_provider_config_for_account(sender_account)
        hostname = str(provider_config.get("smtp_host") or "")
        smtp_port = int(provider_config.get("smtp_port", 587))
        smtp_ssl_port = int(provider_config.get("smtp_ssl_port", smtp_port))
        use_tls = str(provider_config.get("smtp_use_ssl", False)).lower() == "true"
        port = smtp_ssl_port if use_tls else smtp_port
        starttls = not use_tls
    else:
        hostname = config.MAIL_HOSTNAME
        port = int(config.MAIL_PORT)
        use_tls = False
        starttls = bool(config.MAIL_STARTTLS)

    return {
        "enabled": enabled,
        "username": username,
        "password": password,
        "targets": targets,
        "hostname": hostname,
        "port": port,
        "use_tls": use_tls,
        "starttls": starttls,
    }

async def send_email(message: EmailMessage) -> None:
    """
    发送邮件

    Args:
        message: 邮件消息对象

    这是设置邮件内容的方法
    message.set_content("这是邮件的正文内容", subtype='plain')

    这是HTML格式的邮件内容
    message.add_alternative("<html><body><h1>这是HTML格式的邮件内容</h1></body></html>", subtype='html')

    添加附件
    with open('path/to/file', 'rb') as f:
        message.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename='file.txt')
    
    """
    settings = _get_runtime_mail_settings()
    try:
        await send(
            message,
            hostname=settings["hostname"],
            port=settings["port"],
            username=settings["username"],
            password=settings["password"],
            use_tls=settings["use_tls"],
            start_tls=settings["starttls"],
        )
        logger.info("邮件发送成功")
    except Exception as e:
        logger.error(f"邮件发送失败: {e!s}")


async def send_bot_status_email(adapter: str, bot_id: str, is_online: bool) -> None:
    """
    发送机器人状态邮件通知

    Args:
        adapter: 适配器名称
        bot_id: 机器人ID
        is_online: 是否在线
    """
    settings = _get_runtime_mail_settings()
    if not settings["enabled"]:
        return

    message = EmailMessage()
    message["From"] = settings["username"]
    message["To"] = ", ".join(settings["targets"]) if settings["targets"] else settings["username"]

    # 加载 Jinja2 模板
    template = env.get_template("connection.jinja2")

    # 渲染模板
    html_content = await template.render_async(is_online=is_online, adapter=adapter, bot_id=bot_id)

    # 设置 HTML 内容
    message.set_content(html_content, subtype="html")

    await send_email(message)
