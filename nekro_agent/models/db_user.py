import datetime

from miose_toolkit_db import Mapped, MappedColumn, MioModel
from sqlalchemy import DateTime, Integer, String, func

from nekro_agent.core.database import orm


@orm.reg_predefine_data_model(table_name="user", primary_key="id")
class DBUser(MioModel):
    """数据库用户模型"""

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = MappedColumn(String(length=128), comment="用户名")
    password: Mapped[str] = MappedColumn(String(length=128), comment="密码")
    bind_qq: Mapped[str] = MappedColumn(String(length=32), unique=True, comment="绑定的QQ号")

    perm_level: Mapped[int] = MappedColumn(Integer, comment="权限等级")
    login_time: Mapped[datetime.datetime] = MappedColumn(DateTime, comment="上次登录时间")

    create_time: Mapped[datetime.datetime] = MappedColumn(DateTime, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime.datetime] = MappedColumn(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
