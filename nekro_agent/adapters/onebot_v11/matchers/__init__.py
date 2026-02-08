from nekro_agent.core.logger import get_sub_logger


from . import command, message, notice

logger = get_sub_logger("adapter.onebot_v11")
logger.success("Matchers loaded successfully")
