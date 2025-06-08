import json
import re
from typing import Any, Dict, List

from pydantic import Field

from nekro_agent.api import core
from nekro_agent.api.core import logger
from nekro_agent.api.plugin import (
    ConfigBase,
    NekroPlugin,
    SandboxMethod,
    SandboxMethodType,
)
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.message_service import message_service
from nekro_agent.tools.common_util import calculate_text_similarity

plugin = NekroPlugin(
    name="Bilibili 直播工具插件",
    module_name="bilibili_live_utils",
    description="提供 Bilibili 直播适配器专用的消息发送和Live2d模型设置等功能",
    version="0.1.0",
    author="Zaxpris",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["bilibili_live"],
)


@plugin.mount_config()
class BasicConfig(ConfigBase):
    """基础配置"""

    STRICT_MESSAGE_FILTER: bool = Field(
        default=False,
        title="启用严格重复消息过滤",
        description="启用后，完全重复的消息将直接抛出异常，否则仅过滤并提示",
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.7,
        title="消息相似度警告阈值",
        description="当消息相似度超过该阈值时，将触发系统警告提示引导 AI 调整生成策略",
    )
    SIMILARITY_CHECK_LENGTH: int = Field(
        default=12,
        title="启用消息相似度检查阈值",
        description="当消息长度超过该阈值时，将进行相似度检查",
    )


config: BasicConfig = plugin.get_config(BasicConfig)

# 消息缓存
SEND_MSG_CACHE: Dict[str, List[str]] = {}


def extract_expressions(json_data: Dict) -> str:
    """
    Extracts and formats expression details (name, file, active status) from JSON data.

    This function is used internally to prepare a list of available expressions for the LLM.

    Args:
        json_data (Dict): A dictionary parsed from JSON containing expression data,
                          typically from an API response. It expects a structure like:
                          `{"data": {"expressions": [{"name": "str", "file": "str", "active": bool}, ...]}}`.

    Returns:
        str: A string with each expression's name, file, and active status, formatted for
             easy reading (e.g., "Happy happy.exp3.json Active\\nSad sad.exp3.json Inactive").
             Returns "No expression data found." if the 'expressions' array is missing or empty.
             Returns an error message if JSON processing fails.
    """
    try:

        # 提取expressions数组
        expressions = json_data.get("data", {}).get("expressions", [])

        if not expressions:
            return "No expression data found."

        result = []

        # 遍历表情数据并格式化
        for expression in expressions:
            name = expression.get("name", "Unknown")
            file = expression.get("file", "Unknown")
            active = "Active" if expression.get("active", False) else "Inactive"

            result.append(f"{name} {file} {active}")

        return "\n".join(result)

    except json.JSONDecodeError:
        return "JSON format error, please check the input data."
    except Exception as e:
        return f"Error processing data: {e!s}"


def extract_sound_effects(json_data: Dict) -> str:
    """
    Extracts and formats sound effects list from JSON data.

    This function is used internally to prepare a list of available sound effects for the LLM.

    Args:
        json_data (Dict): A dictionary parsed from JSON containing sound effects data,
                          typically from an API response. It expects a structure like:
                          `{"data": {"sounds": ["sound1.wav", "sound2.wav", ...]}}`.

    Returns:
        str: A string with each sound effect name, one per line.
             Returns "No sound effects found." if the 'sounds' array is missing or empty.
             Returns an error message if JSON processing fails.
    """
    try:
        # 提取sounds数组
        sounds = json_data.get("data", {}).get("sounds", [])

        if not sounds:
            return "No sound effects found."

        return "\n".join(sounds)

    except json.JSONDecodeError:
        return "JSON format error, please check the input data."
    except Exception as e:
        return f"Error processing data: {e!s}"


@plugin.mount_prompt_inject_method(name="basic_prompt_inject")
async def basic_prompt_inject(_ctx: AgentCtx):
    """
    Injects dynamic information about available Live2D expressions and sound effects into the agent's prompt.

    This method fetches the current list of available expressions and sound effects from the Bilibili Live
    websocket client and formats it into a prompt string. This helps the LLM understand
    which expressions and sound effects it can use with the respective tools.
    """
    chat_key = _ctx.chat_key
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    avilable_expressions = ""
    available_sound_effects = ""
    
    if ws_client:
        # 获取表情数据
        msg = {
            "type": "emotion",
            "data": {},
        }
        avilable_expressions = await ws_client.send_animate_command(msg)
        avilable_expressions = extract_expressions(avilable_expressions)
        
        # 获取音效数据
        sound_msg = {
            "type": "sound_play",
            "data": {},
        }
        available_sound_effects = await ws_client.send_animate_command(sound_msg)
        available_sound_effects = extract_sound_effects(available_sound_effects)
        
    basic_prompt = f"""
    Important Instructions for Live2D Model Control:

    1.  **Task Queuing:** Actions like `send_text_message`, `set_expression`, and `set_model_face_params`
        do NOT execute immediately. Instead, they add tasks to an animation queue.
    2.  **Execution Trigger:** The `send_execute` command is REQUIRED to execute all tasks
        currently in the queue.
    3.  **Sequential Execution:** Animation queues (defined by a series of tasks followed by `send_execute`)
        are processed one after another. A new queue will only start after the previous one has fully completed.
    4.  **Achieving Delays & Complex Sequences:** You can create sophisticated animation sequences by:
        - Using the `delay` parameter within individual task functions (e.g., `set_expression`, `set_model_face_params`).
        - Strategically placing `send_execute` calls to define segments of an animation. Delays *between*
          `send_execute` calls are effectively the sum of durations and delays of the tasks within the preceding queue.

    Available Expressions (Format: Name File Status):
    {avilable_expressions}

    To use an expression, call `set_expression(_ck, "expression_file_name.exp3.json", duration, delay)`.
    Example: `set_expression(_ck, "Happy.exp3.json", 2.0, 0)` sets the "Happy" expression for 2 seconds with no initial delay.

    Note: The "expressions" listed above might include more than just facial expressions.
    They can control other model parts like props (e.g., pillows) or hair.
    Refer to the list for all available controllable expression assets.

    Available Sound Effects (for creating show effects):
    {available_sound_effects}

    To play a sound effect, call `play_sound(_ck, "sound_file_name.wav", volume, speed, delay)`.
    Sound effects can enhance the atmosphere and create better program effects during the live stream.
    However you can't use them frequently, otherwise it will affect the live stream.
    """
    return basic_prompt  # noqa: RET504


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送文本消息",
    description="发送聊天消息文本，附带缓存消息重复检查",
)
async def send_text_message(_ctx: AgentCtx, chat_key: str, message_text: List[str], speeds: List[float]):
    """
    Sends a list of text messages with specified speaking speeds for a Live2D model.

    This function adds 'say' tasks to an animation queue. The messages will be spoken
    sequentially by the Live2D model when the queue is executed via `send_execute`.
    It includes checks to prevent sending empty, duplicate, or overly similar messages.

    Attention:
        - Do not expose any unnecessary technical IDs or keys in the message content.
        - THIS FUNCTION ADDS TASKS TO THE QUEUE. CALL `send_execute` TO TRIGGER EXECUTION.
        - **IMPORTANT: Only ONE call to `send_text_message` is allowed before each `send_execute` call.
          Subsequent calls to `send_text_message` will overwrite the previous queued messages.**
        - Only segment text when you need to change speaking speed, not for punctuation marks.
        - Keep complete sentences together unless speed changes are necessary.

    Args:
        _ctx (AgentCtx): The agent context (automatically passed).
        chat_key (str): The session identifier for the chat, e.g., "bilibili_live-ROOM_ID".
        message_text (List[str]): A list of strings, where each string is a segment of the message to be spoken.
                                  Cannot be empty, and individual messages cannot be blank.
                                  Only split text when you need different speaking speeds for different parts.
        speeds (List[float]): A list of floats corresponding to `message_text`. Each float specifies
                              the speaking speed for the respective message segment in characters per second.
                              Ensure `len(message_text) == len(speeds)`.
                              Recommended speeds:
                                  - 5.0: Slow
                                  - 10.0: Medium (Normal conversational pace is typically 8.0-10.0)
                                  - 15.0: Fast
    Raises:
        Exception: If `message_text` is empty, if `len(message_text)` != `len(speeds)`,
                   if any message string is empty/whitespace, or if an image tag is detected.
                   Also raises an exception for strictly filtered duplicate messages.
    """
    global SEND_MSG_CACHE

    # 检查消息列表是否为空或者长度不匹配
    if not message_text:
        raise Exception("Error: The message list cannot be empty.")

    if len(message_text) != len(speeds):
        raise Exception("Error: The length of message_text and speeds must be equal.")

    # 检查每条消息内容
    for text in message_text:
        if not text.strip():
            raise Exception("Error: The message content cannot be empty.")

        # 拒绝包含 [image:xxx...] 的图片消息
        if re.match(r"^.*\[image:.*\]$", text) and len(text) > 100:
            raise Exception(
                "Error: You can't send image message directly, please use the send_msg_file method to send image/file resources.",
            )

    # 初始化消息缓存
    if chat_key not in SEND_MSG_CACHE:
        SEND_MSG_CACHE[chat_key] = []

    recent_messages = SEND_MSG_CACHE[chat_key][-5:] if SEND_MSG_CACHE[chat_key] else []

    # 合并所有消息文本用于检查
    combined_message = " ".join(message_text)

    # 检查完全匹配
    if combined_message in recent_messages:
        # 清空缓存允许再次发送
        SEND_MSG_CACHE[chat_key] = []
        if config.STRICT_MESSAGE_FILTER:
            raise Exception(
                "Error: Identical message has been sent recently. Carefully read the recent chat history whether it has sent duplicate messages. Please generate more interesting replies. If you COMPLETELY DETERMINED that it is necessary, resend it. SPAM IS NOT ALLOWED!",
            )
        await message_service.push_system_message(
            chat_key=chat_key,
            agent_messages="System Alert: Identical message has been sent recently. Auto Skip this message. Carefully read the recent chat history whether it has sent duplicate messages. If you COMPLETELY DETERMINED that it is necessary, resend it. SPAM IS NOT ALLOWED!",
            trigger_agent=False,
        )
        return

    # 检查相似度（仅对超过限定字符的消息进行检查）
    for recent_msg in recent_messages:
        similarity = calculate_text_similarity(combined_message, recent_msg, min_length=config.SIMILARITY_CHECK_LENGTH)
        if similarity > config.SIMILARITY_THRESHOLD:
            # 发送系统消息提示避免类似内容
            logger.warning(f"[{chat_key}] 检测到相似度过高的消息: {similarity:.2f}")
            await message_service.push_system_message(
                chat_key=chat_key,
                agent_messages="System Alert: You have sent a message that is too similar to a recently sent message! You should KEEP YOUR RESPONSE USEFUL and not redundant and cumbersome!",
                trigger_agent=False,
            )
            break

    # TODO: 在这里实现实际的消息发送逻辑
    # 此处预留给用户自行实现发送功能
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "say",
            "data": {
                "text": message_text,
                "speed": speeds,
                "delay": 0.0,
            },
        }
        await ws_client.send_animate_command(msg)
    # 更新消息缓存
    SEND_MSG_CACHE[chat_key].append(combined_message)
    SEND_MSG_CACHE[chat_key] = SEND_MSG_CACHE[chat_key][-10:]  # 保持最近10条消息


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="设置Live2d表情",
    description="设置Live2d表情",
)
async def set_expression(_ctx: AgentCtx, chat_key: str, expression: str, duration: float, delay: float):
    """
    Sets a specific Live2D model expression.

    This function adds an 'emotion' task to the animation queue. The expression will be
    applied to the Live2D model when the queue is executed via `send_execute`.

    Attention:
        - THIS FUNCTION ADDS A TASK TO THE QUEUE. CALL `send_execute` TO TRIGGER EXECUTION.

    Args:
        _ctx (AgentCtx): The agent context (automatically passed).
        chat_key (str): The session identifier, e.g., "bilibili_live-ROOM_ID".
        expression (str): The filename of the expression to set (e.g., "happy.exp3.json").
                          Refer to the list of available expressions provided in the prompt.
        duration (float): The duration in seconds for which the expression should be active.
                          - If `duration < 0`, the expression will persist indefinitely.
                          - To turn off a persistent expression, you can set a new expression
                            or set the same expression with `duration = 0`.
        delay (float): The delay in seconds before this expression task starts after the
                       `send_execute` command (or the previous task in the queue) begins.
    """
    # TODO: 在这里实现实际的Live2d模型设置逻辑
    # 此处预留给用户自行实现设置功能
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "emotion",
            "data": {
                "name": expression,
                "duration": duration,
                "delay": delay,
            },
        }
        await ws_client.send_animate_command(msg)


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="设置模型面部参数",
    description="设置模型面部参数",
)
async def set_model_face_params(
    _ctx: AgentCtx, chat_key: str, parameter: str, target: float, duration: float, delay: float, easing: str,
):
    """
    Sets or animates a specific Live2D model facial parameter.

    This function adds an 'animation' task to the animation queue to control individual
    facial parameters like mouth openness, eye blinking, or head angles. The parameter
    will be animated when the queue is executed via `send_execute`.

    Attention:
        - THIS FUNCTION ADDS A TASK TO THE QUEUE. CALL `send_execute` TO TRIGGER EXECUTION.

    Args:
        _ctx (AgentCtx): The agent context (automatically passed).
        chat_key (str): The session identifier, e.g., "bilibili_live-ROOM_ID".
        parameter (str): The name of the facial parameter to animate. See "Available Facial Parameters" below.
        target (float): The target value for the parameter. The valid range depends on the parameter.
        duration (float): The time in seconds over which the parameter animates from its current
                          value to the `target` value.
        delay (float): The delay in seconds before this animation task starts after the
                       `send_execute` command (or the previous task in the queue) begins.
        easing (str): The easing function to use for the animation. See "Available Easing Functions" below.

    Available Easing Functions:
        'linear', 'in_sine', 'out_sine', 'in_out_sine', 'in_back', 'out_back',
        'in_out_back', 'in_elastic', 'out_elastic', 'in_out_elastic'

    Available Facial Parameters (and their typical ranges):
        - 'MouthSmile': 0.0 (corners down) to 1.0 (corners up)
        - 'MouthOpen': 0.0 (closed) to 1.0 (fully open)
        - 'EyeOpenLeft': 0.0 (fully open) to 1.0 (fully closed)
        - 'EyeOpenRight': 0.0 (fully open) to 1.0 (fully closed)
        - 'Brows': 0.0 (furrowed) to 1.0 (raised)
        - 'FaceAngleY': -30.0 (looking down) to 30.0 (looking up)
        - 'FaceAngleX': -30.0 (facing model's right) to 30.0 (facing model's left)
        - 'FaceAngleZ': -90.0 (tilted model's right) to 90.0 (tilted model's left)

    You can combine multiple `set_model_face_params` calls (and other tasks)
    before a `send_execute` to create complex facial animations.

    Example (Wink then smile):
        # Stage 1: Wink left eye (0.3s duration), then smile (0.3s duration, starting after wink finishes)
        set_model_face_params(_ck, "EyeOpenLeft", 1.0, 0.3, 0.0, "in_sine")  # Wink starts immediately
        set_model_face_params(_ck, "MouthSmile", 1.0, 0.3, 0.3, "in_sine") # Smile starts after 0.3s
        send_execute(_ck, 1) # Execute this sequence once
    """
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "animation",
            "data": {
                "parameter": parameter,
                "target": target,
                "duration": duration,
                "delay": delay,
                "easing": easing,
            },
        }
        await ws_client.send_animate_command(msg)


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送执行指令",
    description="发送执行指令",
)
async def send_execute(_ctx: AgentCtx, chat_key: str, loop: int):
    """
    Executes all queued Live2D animation tasks.

    This function triggers the execution of all 'say', 'emotion', and 'animation' tasks
    that have been added to the animation queue since the last `send_execute` call
    (or since the beginning if no `send_execute` has been called yet).

    Attention:
        - THIS FUNCTION EXECUTES ALL TASKS CURRENTLY IN THE QUEUE.

    Args:
        _ctx (AgentCtx): The agent context (automatically passed).
        chat_key (str): The session identifier, e.g., "bilibili_live-ROOM_ID".
        loop (int): The number of times to repeat the entire sequence of tasks
                    currently in the queue. For example, `loop=1` will execute
                    the current queue, then execute it again.
                    A value of `0` means execute once.

    Behavior:
        - The system waits for the previous `send_execute` queue to complete fully
          before starting the next queue. This allows for creating distinct animation segments.
        - If `loop` is greater than 0, the entire set of tasks defined before this
          `send_execute` will be repeated `loop` times.
    """
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "execute",
            "data": {
                "loop": loop,
            },
        }
        await ws_client.send_animate_command(msg)

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="播放音效",
    description="播放音效",
)
async def play_sound(_ctx: AgentCtx, chat_key: str, sound_name: str, volume: float,speed: float, delay: float):
    """
    Plays a sound effect.
    Attention:
        - THIS FUNCTION ADDS A TASK TO THE QUEUE. CALL `send_execute` TO TRIGGER EXECUTION.
    Args:
        chat_key (str): The session identifier, e.g., "bilibili_live-ROOM_ID".
        sound_name (str): The path of the sound to play.
        volume (float): The volume of the sound (0.0-1.0).
        speed (float): The speed of the sound (0.0-1.0).
        delay (float): The delay in seconds before this sound task starts after the `send_execute` command (or the previous task in the queue) begins.
    """
    room_id = chat_key.replace("bilibili_live-", "")
    ws_client = _ctx.adapter.get_ws_client_by_room_id(room_id)  # type: ignore
    if ws_client:
        msg = {
            "type": "sound_play",
            "data": {
                "path": sound_name,
                "volume": volume,
                "speed": speed,
                "delay": delay,
            },
        }
        await ws_client.send_animate_command(msg)


@plugin.mount_cleanup_method()
async def clean_up():
    """
    Cleans up plugin resources, specifically clearing the message cache.

    This function is typically called when the plugin is unloaded or the application
    is shutting down. It resets the `SEND_MSG_CACHE` to an empty dictionary.
    """
    global SEND_MSG_CACHE
    SEND_MSG_CACHE = {}
