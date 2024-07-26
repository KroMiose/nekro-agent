from nekro_agent.core.database import orm

from .db_chat_message import DBChatMessage
from .db_user import DBUser

# from .game.db_character import DBCharacter
# from .game.db_item import DBItem
# from .game.db_story import DBStory
# from .game.db_zone import DBZone


def database_init():
    orm.create_all()
