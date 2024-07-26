from nekro_agent.core.logger import logger

from .command import command_matcher, push_message_matcher
from .execute import execute_matcher
from .message import message_matcher

logger.success("Matchers loaded successfully")
