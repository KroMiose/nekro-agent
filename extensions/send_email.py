import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http import server
from pathlib import Path
from typing import Optional

import nekro_agent.tools.path_convertor
from nekro_agent.api import core
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import config
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.path_convertor import convert_to_host_path

__meta__ = ExtMetaData(
    name="send_email",
    description="NekroAgent 邮件扩展",
    version="0.1.0",
    author="wess09",
    url="https://github.com/KroMiose/nekro-agent",
)

@core.agent_collector.mount_method(core.MethodType.TOOL)
async def email_send(chat_key: str, email_receiver: str, emali_title: str, email_content: str, email_attachment: Path, _ctx: AgentCtx) -> Optional[str]:
    """邮件发送系统
    你可以使用这个方法发送邮件
    Args:
        chat_key (str): 聊天的唯一标识符
        email_receiver (str): 接收者的邮件地址
        emali_title (str): 邮件主题
        email_content (str): 邮件内容
        email_attachment (Path): 附件路径
    Example:
        chat_key("group_123456")
        email_receiver ("empexample@example.com")
        emali_title (str): 邮件主题
        email_content ("你好,这是附件")
        email_attachment("/Users/xxx/Desktop/xxx.jpg")
    """
    # Convert the attachment path to host path
    attachment = convert_to_host_path(email_attachment, chat_key)
    
    
    # 变量赋值
    smtp_server = config.MAIL_HOSTNAME
    smtp_prot = config.MAIL_PORT
    send_email = config.MAIL_USERNAME
    send_pwd = config.MAIL_PASSWORD

    # 创建SMTP会话
    server = smtplib.SMTP(smtp_server, smtp_prot)  # noqa: F811
    server.starttls()
    server.login(send_email, send_pwd)

    # 创建邮件内容
    mail = MIMEMultipart()
    mail["From"] = send_email
    mail["To"] = email_receiver
    mail["Subject"] = emali_title

    # 添加邮件正文
    mail.attach(MIMEText(email_content, "plain"))

    # 添加附件
    if attachment:
        文件名 = (attachment)  
        附件 = open(attachment, "rb")  # noqa: PTH123, SIM115

        mime_base = MIMEBase("application", "octet-stream")
        mime_base.set_payload(附件.read())
        encoders.encode_base64(mime_base)
        mime_base.add_header("Content-Disposition", f"attachment; filename={文件名}")

        mail.attach(mime_base)
        附件.close()  # 确保文件关闭

    # 发送邮件
    server.send_message(mail)
    server.quit()

    return "邮件发送成功"