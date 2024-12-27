from typing import Dict, List

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.libs.miose_llm.clients.chat_openai import (
    gen_openai_chat_response,
    set_openai_base_url,
)


async def get_chat_response(messages: List[Dict[str, str]], model_group: str = "") -> str:
    model_group = model_group or config.USE_MODEL_GROUP
    if model_group not in config.MODEL_GROUPS:
        logger.error(f"指定的模型组 {model_group} 不存在，请检查配置文件")
        raise ValueError(f"指定的模型组 {model_group} 不存在，请检查配置文件")

    for _i in range(3):
        try:
            set_openai_base_url(config.MODEL_GROUPS[model_group]["BASE_URL"])
            ret, tokens = await gen_openai_chat_response(
                messages=messages,
                model=config.MODEL_GROUPS[model_group]["CHAT_MODEL"],
                api_key=config.MODEL_GROUPS[model_group]["API_KEY"],
            )
        except Exception as e:
            logger.error(f"Error while generating chat response: {e}")
        else:
            return ret

    raise Exception("Failed to generate chat response after 3 attempts")
