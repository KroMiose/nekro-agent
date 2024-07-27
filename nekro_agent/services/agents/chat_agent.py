import os
import time
from typing import List

from miose_toolkit_llm import (
    BaseScene,
    BaseStore,
    ModelResponse,
    Runner,
)
from miose_toolkit_llm.clients.chat_openai import (
    OpenAIChatClient,
    set_openai_base_url,
)
from miose_toolkit_llm.components import (
    TextComponent,
)
from miose_toolkit_llm.creators.openai import (
    AiMessage,
    OpenAIPromptCreator,
    SystemMessage,
    UserMessage,
)
from miose_toolkit_llm.exceptions import (
    ResolveError,
    SceneRuntimeError,
)
from miose_toolkit_llm.tools.tokenizers import TikTokenizer

from nekro_agent.core import logger
from nekro_agent.core.config import config
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.chat_message import ChatMessage
from nekro_agent.services.chat import chat_service
from nekro_agent.services.executor import limited_run_code

from .components.chat_history_cmp import ChatHistoryComponent
from .components.chat_ret_cmp import ChatResponseResolver, ChatResponseType

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class ChatScene(BaseScene):
    """基本对话场景类"""

    class Store(BaseStore):
        """场景数据源类"""

        chat_key: str = ""
        chat_preset: str = config.AI_CHAT_PRESET_SETTING


async def agent_run(chat_message: ChatMessage):
    """代理执行函数"""

    logger.info(f"正在构建对话场景: {chat_message.chat_key}")
    # 1. 构造一个应用场景
    scene = ChatScene()
    scene.store.set("chat_key", chat_message.chat_key)

    # 2. 构建聊天记录组件
    chat_history_component = ChatHistoryComponent(scene)
    sta_timestamp = int(time.time() - config.AI_CHAT_CONTEXT_EXPIRE_SECONDS)
    recent_chat_messages: List[DBChatMessage] = (
        DBChatMessage.sqa_query()
        .filter(
            DBChatMessage.chat_key == chat_message.chat_key,
            DBChatMessage.send_timestamp >= sta_timestamp,
        )
        .order_by(DBChatMessage.send_timestamp.desc())
        .limit(config.AI_CHAT_CONTEXT_MAX_LENGTH)
        .all()
    )
    for db_message in recent_chat_messages:
        chat_history_component.append_chat_message(db_message)

    # 3. 构造 OpenAI 提示词
    prompt_creator = OpenAIPromptCreator(
        SystemMessage(
            TextComponent(
                "Character Stetting For You: {chat_preset}",
                src_store=scene.store,
            ),
            ChatResponseResolver.example(),  # 生成一个解析结果示例
            sep="\n\n",  # 自定义构建 prompt 的分隔符 默认为 "\n"
        ),
        UserMessage(
            TextComponent(
                "当前会话: {chat_key}",
                src_store=scene.store,
            ),
            chat_history_component,
            "请参考上述信息，严格遵守回复要求回复，不要携带任何无关信息。",
        ),
        # 生成使用的参数
        temperature=0.3,
        presence_penalty=0.3,
        frequency_penalty=0.4,
    )

    # 4. 绑定 LLM 执行器
    scene.attach_runner(  # 为场景绑定 LLM 执行器
        Runner(
            client=OpenAIChatClient(
                model="gpt-4-1106-preview",
                api_key=config.OPENAI_API_KEY or OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL or OPENAI_BASE_URL,
            ),  # 指定聊天客户端
            tokenizer=TikTokenizer(model="gpt-4-1106-preview"),  # 指定分词器
            prompt_creator=prompt_creator,
        ),
    )

    # 5. 获取结果与解析
    try:
        mr: ModelResponse = await scene.run()
    except SceneRuntimeError as e:
        logger.error(f"Scene runtime error: {e}")
        raise

    try:
        resolved_response: ChatResponseResolver = ChatResponseResolver.resolve(
            model_response=mr,
        )  # 使用指定解析器解析结果
    except ResolveError as e:
        logger.error(f"Resolve error: {e}")
        raise

    ret_type: ChatResponseType = resolved_response.ret_type
    ret_content: str = resolved_response.ret_content

    # 6. 反馈与保存数据
    mr.save(
        prompt_file=".temp/chat_prompt-latest.txt",
        response_file=".temp/chat_response-latest.json",
    )

    await agent_exec_result(ret_type, ret_content, chat_message)


async def agent_exec_result(
    ret_type: ChatResponseType,
    ret_content: str,
    chat_message: ChatMessage,
):
    if ret_type is ChatResponseType.TEXT:
        await chat_service.send_message(chat_message.chat_key, ret_content)
        return

    if ret_type is ChatResponseType.SCRIPT:
        result: str = await limited_run_code(ret_content)
        await chat_service.send_message(chat_message.chat_key, result)
        return
