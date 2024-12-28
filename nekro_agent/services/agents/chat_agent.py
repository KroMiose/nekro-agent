import asyncio
import os
import time
from typing import List, Optional, Set, Union

import weave

from nekro_agent.core import logger
from nekro_agent.core.config import ModelConfigGroup, config
from nekro_agent.core.os_env import PROMPT_LOG_DIR
from nekro_agent.libs.miose_llm import (
    BaseScene,
    BaseStore,
    ModelResponse,
    Runner,
)
from nekro_agent.libs.miose_llm.clients.chat_openai import (
    OpenAIChatClient,
)
from nekro_agent.libs.miose_llm.components import (
    TextComponent,
)
from nekro_agent.libs.miose_llm.creators.openai import (
    AiMessage,
    ImageMessageSegment,
    OpenAIPromptCreator,
    SystemMessage,
    UserMessage,
)
from nekro_agent.libs.miose_llm.exceptions import (
    ResolveError,
    SceneRuntimeError,
)
from nekro_agent.libs.miose_llm.tools.tokenizers import TikTokenizer
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.chat_message import ChatMessage, ChatMessageSegmentImage
from nekro_agent.services.chat import chat_service
from nekro_agent.services.sandbox.executor import CODE_RUN_ERROR_FLAG, limited_run_code
from nekro_agent.systems.message.push_bot_msg import push_system_message
from nekro_agent.tools.common_util import (
    compress_image,
    convert_file_name_to_access_path,
    get_downloaded_prompt_file_path,
)

from .components.chat_history_cmp import ChatHistoryComponent
from .components.chat_ret_cmp import (
    ChatResponseResolver,
    ChatResponseType,
    check_negative_response,
)

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class ChatScene(BaseScene):
    """基本对话场景类"""

    class Store(BaseStore):
        """场景数据源类"""

        chat_key: str = ""
        chat_preset: str = config.AI_CHAT_PRESET_SETTING
        one_time_code: str = ""


@weave.op(name="agent_run")
async def agent_run(
    chat_message: ChatMessage,
    addition_prompt_message: Optional[List[Union[UserMessage, AiMessage]]] = None,
    retry_depth: int = 0,
):
    """代理执行函数"""

    sta_timestamp = time.time()
    one_time_code = os.urandom(4).hex()  # 防止提示词注入，生成一次性随机码

    if not addition_prompt_message:
        addition_prompt_message = []

    logger.info(f"正在构建对话场景: {chat_message.chat_key}")
    if config.DEBUG_IN_CHAT:
        await chat_service.send_message(chat_message.chat_key, "[Debug] 思考中🤔...")

    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_message.chat_key)
    # logger.info(f"加载对话场景配置: {db_chat_channel.get_channel_data().render_prompt()}")

    # 1. 构造一个应用场景
    scene = ChatScene()
    scene.store.set("chat_key", chat_message.chat_key)
    scene.store.set("one_time_code", one_time_code)

    # 2. 构建聊天记录组件
    chat_history_component = (
        ChatHistoryComponent(scene)
        .bind(
            param_key="one_time_code",
            store_key="one_time_code",
            src_store=scene.store,
        )
        .bind(
            param_key="chat_key",
            store_key="chat_key",
            src_store=scene.store,
        )
    )
    record_sta_timestamp = int(time.time() - config.AI_CHAT_CONTEXT_EXPIRE_SECONDS)
    recent_chat_messages: List[DBChatMessage] = await (
        DBChatMessage.filter(
            send_timestamp__gte=record_sta_timestamp,
            chat_key=chat_message.chat_key,
        )
        .order_by("-send_timestamp")
        .limit(config.AI_CHAT_CONTEXT_MAX_LENGTH)
    )
    # 反转列表顺序并确保不超过最大长度
    recent_chat_messages = recent_chat_messages[::-1][-config.AI_CHAT_CONTEXT_MAX_LENGTH :]

    # 提取并构造图片片段
    image_segments: List[ChatMessageSegmentImage] = []
    for db_message in recent_chat_messages:
        for seg in db_message.parse_content_data():
            if isinstance(seg, ChatMessageSegmentImage):
                image_segments.append(seg)

    img_seg_prompts: List[Union[str, ImageMessageSegment]] = []
    img_seg_set: Set[str] = set()
    if image_segments and config.AI_ENABLE_VISION:
        img_seg_prompts.append("Here are some images in the chat history:")
        for seg in image_segments[::-1]:
            if len(img_seg_set) >= config.AI_VISION_IMAGE_LIMIT:
                break
            if seg.local_path:
                if seg.file_name in img_seg_set:
                    continue
                access_path = convert_file_name_to_access_path(seg.file_name, chat_message.chat_key)
                img_seg_set.add(seg.file_name)
                # 检查图片大小
                if access_path.stat().st_size > config.AI_VISION_IMAGE_SIZE_LIMIT_KB * 1024:
                    # 压缩图片
                    try:
                        compressed_path = compress_image(access_path, config.AI_VISION_IMAGE_SIZE_LIMIT_KB)
                    except Exception as e:
                        logger.error(f"压缩图片时发生错误: {e} | 图片路径: {access_path} 跳过处理...")
                        continue
                    img_seg_prompts.append(f"<{one_time_code} | Image:{get_downloaded_prompt_file_path(seg.file_name)}>")
                    img_seg_prompts.append(ImageMessageSegment.from_path(str(compressed_path)))
                    logger.info(f"压缩图片: {access_path.name} -> {compressed_path.stat().st_size / 1024}KB")
                else:
                    img_seg_prompts.append(f"<{one_time_code} | Image:{get_downloaded_prompt_file_path(seg.file_name)}>")
                    img_seg_prompts.append(ImageMessageSegment.from_path(str(access_path)))
            elif seg.remote_url:
                if seg.remote_url in img_seg_set:
                    continue
                img_seg_set.add(seg.remote_url)
                img_seg_prompts.append(f"<{one_time_code} | Image:{seg.remote_url}>")
                img_seg_prompts.append(ImageMessageSegment.from_url(seg.remote_url))

    for db_message in recent_chat_messages:
        chat_history_component.append_chat_message(db_message)
    logger.info(f"加载最近 {len(recent_chat_messages)} 条对话记录")

    # 3. 构造 OpenAI 提示词
    prompt_creator = OpenAIPromptCreator(
        SystemMessage(
            TextComponent(
                "Base Character Stetting For You: {chat_preset}",
                src_store=scene.store,
            ),
            ChatResponseResolver.example(one_time_code),  # 生成一个解析结果示例
            sep="\n\n",  # 自定义构建 prompt 的分隔符 默认为 "\n"
        ),
        UserMessage(ChatResponseResolver.practice_question_1()),
        AiMessage(ChatResponseResolver.practice_response_1()),
        UserMessage(ChatResponseResolver.practice_question_2()),
        AiMessage(ChatResponseResolver.practice_response_2()),
        UserMessage(
            "Good, this is an effective response to a positive action. Next is a real user conversation scene\n\n",
            *img_seg_prompts,
            TextComponent(
                (
                    f"{(await db_chat_channel.get_channel_data()).render_prompts()}\n"  # 聊天频道配置
                    "Current Chat Key: {chat_key}"  # 当前聊天会话键名
                ),
                src_store=scene.store,
            ),
            chat_history_component,
        ),
        *addition_prompt_message,
        # # 文本生成使用的参数
        # temperature=0.3,
        # presence_penalty=0.3,
        # frequency_penalty=0.4,
    )

    # 4. 绑定 LLM 执行器
    model_group: ModelConfigGroup = ModelConfigGroup.model_validate(config.MODEL_GROUPS[config.USE_MODEL_GROUP])
    scene.attach_runner(  # 为场景绑定 LLM 执行器
        Runner(
            client=OpenAIChatClient(
                model=model_group.CHAT_MODEL,
                api_key=model_group.API_KEY or OPENAI_API_KEY,
                base_url=model_group.BASE_URL or OPENAI_BASE_URL,
                proxy=model_group.CHAT_PROXY,
            ),  # 指定聊天客户端
            tokenizer=TikTokenizer(model=model_group.CHAT_MODEL),  # 指定分词器
            prompt_creator=prompt_creator,
        ),
    )

    # 5. 获取结果与解析
    for _ in range(config.AI_CHAT_LLM_API_MAX_RETRIES):
        try:
            logger.debug("发送生成请求...")
            scene_run_sta_timestamp = time.time()
            mr: ModelResponse = await scene.run()
            logger.debug(f"LLM 运行耗时: {time.time() - scene_run_sta_timestamp:.3f}s")
            break
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            await asyncio.sleep(1)
    else:
        await chat_service.send_agent_message(chat_message.chat_key, "哎呀，请求模型发生了未知错误，等会儿再试试吧 ~")
        raise SceneRuntimeError("LLM API error: 达到最大重试次数，停止重试。") from None

    if (not retry_depth) and check_negative_response(mr.response_text):
        logger.warning(f"检测到消极回复: {mr.response_text}，拒绝结果并重试")
        if config.DEBUG_IN_CHAT:
            await chat_service.send_message(chat_message.chat_key, "[Debug] 检测到消极回复，拒绝结果并重试...")
        addition_prompt_message.append(AiMessage(mr.response_text))
        addition_prompt_message.append(
            UserMessage(
                "[System Automatic Detection] A suspected negative or invalid response is detected in your reply (such as asking for a meaningless wait or claiming to do something but not do anything). Your answers must be consistent with your words and deeds, no pretending behavior, and no meaningless promises. If you think this is an error, please ** keep the previously agreed reply format ** and try again.",
            ),
        )
        await agent_run(chat_message, addition_prompt_message, retry_depth + 1)
        return

    try:
        resolved_response: ChatResponseResolver = ChatResponseResolver.resolve(
            model_response=mr,
        )  # 使用指定解析器解析结果
        logger.debug("解析完成结果完成")
    except Exception as e:
        logger.error(f"解析结果出错: {e}")
        raise ResolveError(f"解析结果出错: {e}") from e

    # 7. 执行响应结果
    logger.debug(f"开始执行 {len(resolved_response.ret_list)} 条响应结果")
    for ret_data in resolved_response.ret_list:
        # 最终过滤一次待执行的代码
        if ret_data.content.lower().startswith("```python"):
            ret_data.content = ret_data.content[10:]
        if ret_data.content.lower().endswith("```"):
            ret_data.content = ret_data.content[:-3]
        await agent_exec_result(ret_data.type, ret_data.content, chat_message, addition_prompt_message, retry_depth)

    # 8. 反馈与保存数据
    if config.SAVE_PROMPTS_LOG:
        current_strftime = time.strftime("%Y%m%d%H%M%S")
        logger.debug(f"保存对话记录: {current_strftime}")
        mr.save(
            prompt_file=f".temp/prompts/chat_prompt-{current_strftime}.txt",
            response_file=f".temp/prompts/chat_response-{current_strftime}.json",
        )
        logger.debug("另存最新对话记录")
        mr.save(
            prompt_file=".temp/chat_prompt-latest.txt",
            response_file=".temp/chat_response-latest.json",
        )

    logger.info(f"本轮响应耗时: {time.time() - sta_timestamp:.2f}s | To {chat_message.sender_nickname}")


async def agent_exec_result(
    ret_type: ChatResponseType,
    ret_content: str,
    chat_message: ChatMessage,
    addition_prompt_message: List[Union[UserMessage, AiMessage]],
    retry_depth: int = 0,
):
    if ret_type is ChatResponseType.TEXT:
        logger.info(f"解析文本回复: {ret_content} | To {chat_message.sender_nickname}")
        await chat_service.send_agent_message(chat_message.chat_key, ret_content, record=True)
        return

    if ret_type is ChatResponseType.SCRIPT:
        if ret_content.endswith("\n```"):
            ret_content = ret_content[:-3]
        logger.info(f"解析程式回复: 等待执行资源 | To {chat_message.sender_nickname}")
        if config.DEBUG_IN_CHAT:
            await chat_service.send_message(chat_message.chat_key, "[Debug] 执行程式中🖥️...")
        result: str = await limited_run_code(ret_content, from_chat_key=chat_message.chat_key)
        if result.endswith(CODE_RUN_ERROR_FLAG):  # 运行出错标记，将错误信息返回给 AI
            err_msg = result[: -len(CODE_RUN_ERROR_FLAG)]
            addition_prompt_message.append(AiMessage(f"{ret_content}"))
            if retry_depth < config.AI_SCRIPT_MAX_RETRY_TIMES - 1:
                addition_prompt_message.append(
                    UserMessage(
                        f"Code run error: {err_msg or 'No error message'}\nPlease maintain agreed reply format and try again.",
                    ),
                )
            else:
                addition_prompt_message.append(
                    UserMessage(
                        f"Code run error: {err_msg or 'No error message'}\nThe number of retries has reached the limit, you should give up retries and explain the problem you are experiencing.",
                    ),
                )
            logger.info(f"程式运行出错: ...{err_msg[-100:]} | 重试次数: {retry_depth} | To {chat_message.sender_nickname}")
            if retry_depth < config.AI_SCRIPT_MAX_RETRY_TIMES:
                if config.DEBUG_IN_CHAT:
                    await chat_service.send_message(
                        chat_message.chat_key,
                        f"[Debug] 程式运行出错: {err_msg or 'No error message'}\n正在调试中...({retry_depth + 1}/{config.AI_SCRIPT_MAX_RETRY_TIMES})",
                    )
                await agent_run(chat_message, addition_prompt_message, retry_depth + 1)
            else:
                await chat_service.send_message(chat_message.chat_key, "程式运行出错，达到最大重试次数，停止重试。")
        else:
            output_msg = result[:100] if result else "No output"
            logger.info(f"程式执行成功: {output_msg}... | To {chat_message.sender_nickname}")
            await push_system_message(
                chat_message.chat_key,
                f'"""python(history run)\n{ret_content}\n"""The requested program was executed successfully, and the output is: {output_msg}...',
            )
            return
        return
