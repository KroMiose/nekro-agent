import asyncio
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

import aiosmtplib

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
async def send_email(to_mail: str, title: str, txt: str, files: List[str], _ctx: AgentCtx) -> Optional[str]:
    """邮件发送系统
    你可以使用这个方法发送邮件
    Args:
        to_mail (str): 接收者的邮件地址
        title (str): 邮件主题
        txt (str): 邮件内容
        files (List[str]): 附件路径列表
    Example:
        send_email("empexample@example.com", "你好", "这是一封邮件", ["/app/shared/xxxx.jpg"])
        send_email("{user_qq}@qq.com", "你好", "这是一封邮件", ["/app/shared/xxxx.doc", "/app/shared/xxx.txt"])
    """
    # 变量
    chat_key = _ctx.from_chat_key
    smtp_server = config.MAIL_HOSTNAME
    smtp_port = config.MAIL_PORT
    email_uer = config.MAIL_USERNAME
    pwd = config.MAIL_PASSWORD

    # 创建异步 SMTP 会话
    smtp = aiosmtplib.SMTP(hostname=smtp_server, port=smtp_port)
    await smtp.connect()
    await smtp.login(email_uer, pwd)

    # 创建邮件内容
    email = MIMEMultipart()
    email["From"] = email_uer
    email["To"] = to_mail
    email["Subject"] = title

    # 添加邮件正文
    email.attach(MIMEText(txt, "plain"))

    # 添加附件（支持多附件）
    files_PATH = [Path(file) for file in files]
    if files_PATH:
        for files_DATA in files_PATH: # type: ignore
            # 将每个附件转换为主机路径（转换函数接收 Path 类型）
            host_path = convert_to_host_path(Path(files_DATA), chat_key)
            files_NAME = Path(files_DATA).name
            # 直接读取附件文件内容
            with open(str(host_path), "rb") as files_EMAIL:  # noqa: PTH123
                files_content = files_EMAIL.read()
            mime = MIMEBase("application", "octet-stream")
            mime.set_payload(files_content)
            encoders.encode_base64(mime)
            mime.add_header("Content-Disposition", f"attachment; filename={files_NAME}")
            email.attach(mime)

    # 发送邮件
    await smtp.send_message(email)
    await smtp.quit()

    return "邮件发送成功"
