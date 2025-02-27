from email.message import EmailMessage

from aiosmtplib import send
from nonebot import logger

from nekro_agent.core.config import config


async def send_bot_status_email(adapter: str, bot_id: str, is_online: bool) -> None:
    """
    发送机器人状态邮件通知

    Args:
        adapter: 适配器名称
        bot_id: 机器人ID
        is_online: 是否在线
    """
    if not config.MAIL_ENABLED:
        return

    message = EmailMessage()
    message["From"] = config.MAIL_USERNAME
    message["To"] = ", ".join(config.MAIL_TARGET) if config.MAIL_TARGET else config.MAIL_USERNAME
    message["Subject"] = "Bot状态提醒！"

    if is_online:
        content = f"您的Bot上线啦!\n适配器：{adapter}\nBot：{bot_id}"
    else:
        content = f"您的Bot下线了，可能出现了问题，快去看看吧！\n适配器：{adapter}\nBot：{bot_id}"

    message.set_content(content)

    try:
        await send(
            message,
            hostname=config.MAIL_HOSTNAME,
            port=config.MAIL_PORT,
            username=config.MAIL_USERNAME,
            password=config.MAIL_PASSWORD,
            start_tls=config.MAIL_STARTTLS,
        )
        logger.info("Bot状态邮件发送成功")
    except Exception as e:
        logger.error(f"Bot状态邮件发送失败: {e!s}")