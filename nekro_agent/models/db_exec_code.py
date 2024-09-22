import datetime

from miose_toolkit_db import Mapped, MappedColumn, MioModel
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func

from nekro_agent.core.database import orm


@orm.reg_predefine_data_model(table_name="exec_code", primary_key="id")
class DBExecCode(MioModel):
    """数据库聊天频道模型"""

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True, comment="ID")

    chat_key: Mapped[str] = MappedColumn(String(32), comment="会话唯一标识", index=True)
    trigger_user_id: Mapped[int] = MappedColumn(Integer, default=0, comment="触发用户ID", index=True)
    trigger_user_name: Mapped[str] = MappedColumn(String(128), default="System", comment="触发用户名")
    success: Mapped[bool] = MappedColumn(Boolean, default=False, comment="是否成功")
    code_text: Mapped[str] = MappedColumn(Text, comment="执行代码文本")
    outputs: Mapped[str] = MappedColumn(Text, comment="输出结果")

    create_time: Mapped[datetime.datetime] = MappedColumn(DateTime, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime.datetime] = MappedColumn(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
        index=True,
    )
