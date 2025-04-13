from email.message import EmailMessage

from aiosmtplib import send
from jinja2 import Environment, FileSystemLoader
from nonebot import logger

from nekro_agent.core.config import config

env = Environment(loader=FileSystemLoader("nekro_agent/services/mail"), auto_reload=False,enable_async=True)

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
    try:
        await send(
            message,
            hostname=config.MAIL_HOSTNAME,
            port=config.MAIL_PORT,
            username=config.MAIL_USERNAME,
            password=config.MAIL_PASSWORD,
            start_tls=config.MAIL_STARTTLS,
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
    if not config.MAIL_ENABLED:
        return

    message = EmailMessage()
    message["From"] = config.MAIL_USERNAME
    message["To"] = ", ".join(config.MAIL_TARGET) if config.MAIL_TARGET else config.MAIL_USERNAME

    # 加载 Jinja2 模板
    template = env.get_template("connection.jinja2")

    # 渲染模板
    html_content = await template.render_async(is_online=is_online, adapter=adapter, bot_id=bot_id)

    # 设置 HTML 内容
    message.set_content(html_content, subtype="html")

    await send_email(message)