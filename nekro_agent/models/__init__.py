from nekro_agent.core.database import orm

from .db_chat_channel import DBChatChannel
from .db_chat_message import DBChatMessage
from .db_exec_code import DBExecCode
from .db_user import DBUser


def database_init():
    orm.create_all()
