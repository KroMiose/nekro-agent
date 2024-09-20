import datetime

from miose_toolkit_db import Mapped, MappedColumn, MioModel
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func

from nekro_agent.core.config import config
from nekro_agent.core.database import orm
from nekro_agent.systems.message.convertor import (
    convert_raw_msg_data_json_to_msg_prompt,
)


@orm.reg_predefine_data_model(table_name="chat_message", primary_key="id")
class DBChatMessage(MioModel):
    """数据库聊天消息模型"""

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True, comment="ID")

    sender_id: Mapped[int] = MappedColumn(Integer, comment="发送者 ID", index=True)
    sender_bind_qq: Mapped[str] = MappedColumn(String(32), comment="发送者绑定 QQ", index=True)
    sender_real_nickname: Mapped[str] = MappedColumn(String(32), comment="发送者真实昵称", index=True)
    sender_nickname: Mapped[str] = MappedColumn(String(32), comment="发送者显示昵称", index=True)
    is_tome: Mapped[int] = MappedColumn(Integer, comment="是否与 Bot 相关")
    is_recalled: Mapped[bool] = MappedColumn(Boolean, comment="是否为撤回消息")

    chat_key: Mapped[str] = MappedColumn(String(32), comment="会话唯一标识", index=True)
    chat_type: Mapped[str] = MappedColumn(String(32), comment="会话类型: friend/group")

    content_text: Mapped[str] = MappedColumn(Text, comment="消息内容文本")
    content_data: Mapped[str] = MappedColumn(Text, comment="消息内容数据 JSON")

    raw_cq_code: Mapped[str] = MappedColumn(Text, comment="原始 CQ 码")
    ext_data: Mapped[str] = MappedColumn(Text, comment="扩展数据")

    send_timestamp: Mapped[int] = MappedColumn(Integer, comment="发送时间戳", index=True)
    create_time: Mapped[datetime.datetime] = MappedColumn(DateTime, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime.datetime] = MappedColumn(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
        index=True,
    )

    def parse_chat_history_prompt(self, one_time_code: str) -> str:
        """解析聊天历史记录生成提示词"""
        content = convert_raw_msg_data_json_to_msg_prompt(self.content_data, one_time_code)
        if len(content) > config.AI_CONTEXT_LENGTH_PER_MESSAGE:  # 截断消息内容
            content = (
                content[: config.AI_CONTEXT_LENGTH_PER_MESSAGE // 4 - 3]
                + "..."
                + content[-config.AI_CONTEXT_LENGTH_PER_MESSAGE // 4 + 3 :]
                + "(content too long, omitted)"
            )
        time_str = datetime.datetime.fromtimestamp(self.send_timestamp).strftime("%m-%d %H:%M:%S")
        return f'[{time_str} from_qq:{self.sender_bind_qq}] "{self.sender_nickname}" 说: {content or self.content_text}'
