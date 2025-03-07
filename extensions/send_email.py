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
async def send_email(chat_key: str, to_mail: str, title: str, txt: str, fujian: Path[str], _ctx: AgentCtx) -> Optional[str]:
    """邮件发送系统
    你可以使用这个方法发送邮件
    Args:
        chat_key (str): 聊天的唯一标识符
        to_mail (str): 接收者的邮件地址
        title (str): 邮件主题
        txt (str): 邮件内容
        fujian (List[str]): 附件路径列表
    Example:
        send_email("group_123456", "empexample@example.com", "你好", "这是一封邮件", [Path("/Users/xxx/Desktop/xxx.jpg")])
        send_email("group_123456", "{user_qq}@qq.com", "你好", "这是一封邮件", [Path("/Users/xxx/Desktop/xxx.jpg"), Path("/Users/xxx/Desktop/yyy.pdf")])
    """
    # 变量赋值
    smtp服务器 = config.MAIL_HOSTNAME
    smtp端口 = config.MAIL_PORT
    发件人邮箱 = config.MAIL_USERNAME
    发件人密码 = config.MAIL_PASSWORD

    # 创建异步 SMTP 会话
    smtp客户端 = aiosmtplib.SMTP(hostname=smtp服务器, port=smtp端口)
    await smtp客户端.connect()
    await smtp客户端.login(发件人邮箱, 发件人密码)

    # 创建邮件内容
    邮件 = MIMEMultipart()
    邮件["From"] = 发件人邮箱
    邮件["To"] = to_mail
    邮件["Subject"] = title

    # 添加邮件正文
    邮件.attach(MIMEText(txt, "plain"))

    # 添加附件（支持多附件）
    if fujian:
        for 附件 in fujian: # type: ignore
            # 将每个附件转换为主机路径（转换函数接收 Path 类型）
            转换后的附件路径 = convert_to_host_path(Path(附件), chat_key)
            文件名 = Path(附件).name
            # 直接读取附件文件内容
            with open(str(转换后的附件路径), "rb") as 文件:  # noqa: PTH123
                文件内容 = 文件.read()
            mime部分 = MIMEBase("application", "octet-stream")
            mime部分.set_payload(文件内容)
            encoders.encode_base64(mime部分)
            mime部分.add_header("Content-Disposition", f"attachment; filename={文件名}")
            邮件.attach(mime部分)

    # 发送邮件
    await smtp客户端.send_message(邮件)
    await smtp客户端.quit()

    return "邮件发送成功"
