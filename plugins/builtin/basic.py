"""
# 基础交互插件 (Basic)

提供智能体与聊天平台进行基础交互的核心功能，并内置了智能防刷屏机制。

## 主要功能

- **基础通信**: 负责 AI 发送文本、图片、文件的核心能力。
- **智能防刷屏**: 能够自动检测并过滤重复或高度相似的内容，避免 AI 发送无意义的重复消息，保持对话的清爽。
- **动态工具**: 能够根据当前所用的聊天适配器，动态提供一些特殊功能（例如在 QQ 中获取用户头像）。

## 配置说明

此插件包含一些关于消息过滤的配置，例如：
- **消息相似度过滤**: 是否启用防刷屏功能。
- **严格重复消息过滤**: 开启后，发送完全相同的消息会直接失败。
- **相似度警告阈值**: 用于判断消息是否相似的灵敏度。

## Agent 可用工具 (Sandbox Methods)

### 通用工具
- **send_msg_text**:
  - 描述: 发送文本消息到指定的聊天频道。
  - 注意: 插件会检查近期消息，如果发现重复或高度相似的内容，可能会阻止发送或发出警告。

- **send_msg_file**:
  - 描述: 发送文件或图片到指定的聊天频道。插件会自动识别文件类型（图片/普通文件）并发送。
  - 参数: `file_path` 可以是 URL 或容器内的共享路径。
  - 注意: 同样具有防重复发送机制，通过文件内容的 MD5 判断。

### OneBot v11 专属工具
- **get_user_avatar**:
  - 描述: 获取 QQ 用户的头像。
  - 参数: `user_qq` (用户 QQ 号)。
  - 返回: 头像文件的容器内共享路径。
  - **注意: 此工具仅在 `onebot_v11` 适配器下可用。**
"""

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

import aiofiles
import magic
from pydantic import Field

from nekro_agent.adapters.onebot_v11.tools import user
from nekro_agent.api import core, i18n
from nekro_agent.api.message import ChatMessage
from nekro_agent.api.plugin import (
    ConfigBase,
    ExtraField,
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.api.signal import MsgSignal
from nekro_agent.services.message_service import message_service
from nekro_agent.tools.common_util import (
    calculate_file_md5,
    calculate_text_similarity,
    download_file,
)
from nekro_agent.tools.path_convertor import (
    convert_filename_to_sandbox_upload_path,
    convert_to_host_path,
    is_url_path,
)

plugin = NekroPlugin(
    name="基础交互插件",
    module_name="basic",
    description="提供基础的聊天消息发送、图片/文件资源发送等基础功能",
    version="0.1.1",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="基础交互插件",
        en_US="Basic Interaction Plugin",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="提供基础的聊天消息发送、图片/文件资源发送等基础功能",
        en_US="Provides basic chat messaging, image/file sending and other fundamental features",
    ),
    # 开放给 telegram 使用（文本/文件发送可用，头像工具仅在 OneBot 下提供）
    support_adapter=["onebot_v11", "minecraft", "sse", "discord", "wechatpad", "telegram"],
)


# ========================================================================================
# |                              Nekro-Agent 交互基础工具集                                |
# ========================================================================================
#   插件编写注意:
#     1. 所有注解会被 AI 引用时参考，请务必准确填写
#     2. _ctx: AgentCtx 中存储有关当前聊天频道的上下文信息，不需要且不能加入到注释，以免误导 AI
#     3. _ctx 参数务必放在第一个，否则会因为参数位置匹配错误导致调用失败
#     4. 如果需要在注解中编写应用示例等信息，务必不要体现 _ctx 的存在，并且使用 `同步调用` 的方式
#        (即不需要 `await func()` )，因为其实际执行是通过 rpc 在 Nekro-Agent 主服务进行的
#     5. `inject_prompt` 方法会在每次聊天频道触发开始时调用一次，并将返回值注入到聊天频道提示词中
#     6. 插件的清理方法 `clean_up` 会在插件卸载时自动调用，请在此方法中实现清理或重置逻辑
# ========================================================================================


@plugin.mount_config()
class BasicConfig(ConfigBase):
    """基础配置"""

    SIMILARITY_MESSAGE_FILTER: bool = Field(
        default=True,
        title="启用消息相似度过滤",
        description="启用后将按以下策略自动过滤重复消息并提示 AI 调整生成策略",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用消息相似度过滤",
                en_US="Enable Message Similarity Filtering",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="启用后将按以下策略自动过滤重复消息并提示 AI 调整生成策略",
                en_US="When enabled, duplicate messages will be automatically filtered and AI will be prompted to adjust generation strategy",
            ),
        ).model_dump(),
    )
    STRICT_MESSAGE_FILTER: bool = Field(
        default=False,
        title="启用严格重复消息过滤",
        description="启用后，完全重复的消息将直接抛出异常，否则仅过滤并提示",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用严格重复消息过滤",
                en_US="Enable Strict Duplicate Message Filtering",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="启用后，完全重复的消息将直接抛出异常，否则仅过滤并提示",
                en_US="When enabled, identical messages will throw exceptions, otherwise only filtered with warnings",
            ),
        ).model_dump(),
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.7,
        title="消息相似度警告阈值",
        description="当消息相似度超过该阈值时，将触发系统警告提示引导 AI 调整生成策略",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="消息相似度警告阈值",
                en_US="Message Similarity Warning Threshold",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="当消息相似度超过该阈值时，将触发系统警告提示引导 AI 调整生成策略",
                en_US="System warning will be triggered when message similarity exceeds this threshold",
            ),
        ).model_dump(),
    )
    SIMILARITY_CHECK_LENGTH: int = Field(
        default=12,
        title="启用消息相似度检查阈值",
        description="当消息长度超过该阈值时，将进行相似度检查",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用消息相似度检查阈值",
                en_US="Message Similarity Check Length Threshold",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="当消息长度超过该阈值时，将进行相似度检查",
                en_US="Similarity check will be performed when message length exceeds this threshold",
            ),
        ).model_dump(),
    )
    ALLOW_AT_ALL: bool = Field(
        default=False,
        title="允许 @全体成员",
        description="启用后，消息中可以触发 @全体成员 功能；禁用时将被替换为纯文本形式的 @全体成员",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="允许 @全体成员",
                en_US="Allow @all Members",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="启用后，消息中可以触发 @全体成员 功能；禁用时将被替换为纯文本形式的 @全体成员",
                en_US="When enabled, messages can trigger @all function; when disabled, it will be replaced with plain text",
            ),
        ).model_dump(),
    )
    ENABLE_VIEW_STR_CONTENT: bool = Field(
        default=True,
        title="启用字符串内容查看工具",
        description="启用后，AI 可以使用 view_str_content 工具查看数据内容（如 Excel、CSV 等）",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用字符串内容查看工具",
                en_US="Enable String Content Viewer Tool",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="启用后，AI 可以使用 view_str_content 工具查看数据内容（如 Excel、CSV 等）",
                en_US="When enabled, AI can use view_str_content tool to view data content (e.g., Excel, CSV)",
            ),
        ).model_dump(),
    )


# 获取配置
config: BasicConfig = plugin.get_config(BasicConfig)


@plugin.mount_on_user_message()
async def on_user_message(_ctx: AgentCtx, message: ChatMessage):
    """用户任意消息回调"""


@plugin.mount_prompt_inject_method(name="basic_prompt_inject")
async def basic_prompt_inject(_ctx: AgentCtx):
    """示例提示注入"""
    features: Dict[str, bool] = {
        "Reference_Message": False,
    }
    base_prompt = "Current Adapter Support Feature:\n"
    if _ctx.adapter_key in ["onebot_v11"]:
        features["Reference_Message"] = True
    tips: str = "When you reference a message, user can click it to jump to the referenced message."
    return base_prompt + "\n".join([f"{k}: {v}" for k, v in features.items()]) + "\n" + tips


SEND_MSG_CACHE: Dict[str, List[str]] = {}
SEND_FILE_CACHE: Dict[str, List[str]] = {}  # 文件 MD5 缓存，格式: {chat_key: [md5_1, md5_2, md5_3]}


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送聊天消息文本",
    description="发送聊天消息文本，附带缓存消息重复检查",
)
async def send_msg_text(_ctx: AgentCtx, chat_key: str, message_text: str, ref_msg_id: Optional[str] = None):
    """发送聊天消息文本

    Attention:
        1. Do not expose any unnecessary technical id or key in the message content.
        2. You can always send messages that are confident in the content, not content that you don't even know what it will be.

    Args:
        chat_key (str): 聊天频道标识
        message_text (str): 消息内容
        ref_msg_id (Optional[str]): 引用消息 ID (部分适配器可用，参考 `Reference_Message`)

    Example:
        # Send some valid message
        send_msg_text(_ck, f"Hello, 1 + 1 = {1+1}")  # You can predict the result of the calculation

        # Bad Example:
        try:
            ... # Do something
        except Exception as e:
            send_msg_text(_ck, f"Error: {e}")  # You can't send error message directly, because you can't be sure about the content.

        # Good Example:
        ... # Just do something **WITHOUT ANY TRY-EXCEPT BLOCK**! You have the opportunity to debug and fix it only if you let the error happen directly instead of covering it up.
        result = ... # Always use the right result, not the error message.
        send_msg_text(_ck, f"Result: {result}")  # You can send the result of the calculation directly.
    """
    global SEND_MSG_CACHE

    if _ctx.adapter_key not in plugin.support_adapter:
        raise Exception(f"Error: This method is not available in this adapter. Current adapter: {_ctx.adapter_key}")

    if not message_text.strip():
        raise Exception("Error: The message content cannot be empty.")

    if not config.ALLOW_AT_ALL:
        message_text = message_text.replace("[@all@]", "@全体成员")

    # 拒绝包含 [image:xxx...] 的图片消息
    if re.match(r"^.*\[image:.*\]$", message_text) and len(message_text) > 100:
        raise Exception(
            "Error: You can't send image message directly, please use the send_msg_file method to send image/file resources.",
        )

    # 初始化消息缓存
    if chat_key not in SEND_MSG_CACHE:
        SEND_MSG_CACHE[chat_key] = []

    recent_messages = SEND_MSG_CACHE[chat_key][-5:] if SEND_MSG_CACHE[chat_key] else []

    # 检查完全匹配
    if config.SIMILARITY_MESSAGE_FILTER:
        if message_text in recent_messages:
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
            similarity = calculate_text_similarity(message_text, recent_msg, min_length=config.SIMILARITY_CHECK_LENGTH)
            if similarity > config.SIMILARITY_THRESHOLD:
                # 发送系统消息提示避免类似内容
                core.logger.warning(f"[{chat_key}] 检测到相似度过高的消息: {similarity:.2f}")
                await message_service.push_system_message(
                    chat_key=chat_key,
                    agent_messages="System Alert: You have sent a message that is too similar to a recently sent message! You should KEEP YOUR RESPONSE USEFUL and not redundant and cumbersome!",
                    trigger_agent=False,
                )
                break

    try:
        await _ctx.ms.send_text(chat_key, message_text, _ctx, ref_msg_id=ref_msg_id)
    except Exception as e:
        core.logger.exception(f"发送消息失败: {e}")
        raise Exception(
            "Error sending text message to chat: Make sure the chat key is valid, you have permission to speak and message is not too long.",
        ) from e

    # 更新消息缓存
    SEND_MSG_CACHE[chat_key].append(message_text)
    SEND_MSG_CACHE[chat_key] = SEND_MSG_CACHE[chat_key][-10:]  # 保持最近10条消息


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="发送聊天消息图片/文件资源",
    description="发送聊天消息图片/文件资源，附带缓存文件重复检查",
)
async def send_msg_file(_ctx: AgentCtx, chat_key: str, file_path: str, ref_msg_id: Optional[str] = None):
    """发送聊天消息图片/文件资源

    Args:
        chat_key (str): 聊天频道标识
        file_path (str): 图片/文件路径或 URL 容器内路径
        ref_msg_id (Optional[str]): 引用消息 ID (部分适配器可用，参考 `Reference_Message`)
    """
    global SEND_FILE_CACHE
    file_container_path = file_path  # 防止误导llm
    if not isinstance(file_container_path, str):
        raise TypeError("Error: The file argument must be a string with the correct file shared path or URL.")

    if is_url_path(file_container_path):
        file_host_path, _ = await download_file(file_container_path, from_chat_key=chat_key)
        file_container_path = str(convert_filename_to_sandbox_upload_path(Path(file_host_path)))
    else:
        file_host_path = str(
            convert_to_host_path(Path(file_container_path), _ctx.chat_key, container_key=_ctx.container_key),
        )
        if not Path(file_host_path).exists():
            raise FileNotFoundError(
                f"The file `{file_container_path}` does not exist! Attention: The file you generated in previous conversation may not be persistence in sandbox environment, please check it.",
            )
    # 初始化文件缓存
    if chat_key not in SEND_FILE_CACHE:
        SEND_FILE_CACHE[chat_key] = []

    # 计算文件 MD5
    file_md5 = await calculate_file_md5(file_host_path)

    # 过滤重复文件
    if config.SIMILARITY_MESSAGE_FILTER and file_md5 in SEND_FILE_CACHE[chat_key]:
        SEND_FILE_CACHE[chat_key].remove(file_md5)
        if config.STRICT_MESSAGE_FILTER:
            raise Exception(
                "Error: Identical file has been sent recently. Please check if this file is really needed to be sent again. Please generate more interesting replies. SPAM IS NOT ALLOWED!",
            )
        await message_service.push_system_message(
            chat_key=chat_key,
            agent_messages="System Alert: Identical file has been sent recently. Auto Skip this file. Please check if this file is really needed to be sent again. Please generate more interesting replies. SPAM IS NOT ALLOWED!",
            trigger_agent=False,
        )
        return

    try:
        # 使用magic库检测文件MIME类型
        async with aiofiles.open(file_host_path, "rb") as f:
            file_data = await f.read()
            mime_type = magic.from_buffer(file_data, mime=True)
            is_image = mime_type.startswith("image/")

        if is_image:
            await _ctx.ms.send_image(chat_key, file_container_path, _ctx, ref_msg_id=ref_msg_id)
        else:
            await _ctx.ms.send_file(chat_key, file_container_path, _ctx, ref_msg_id=ref_msg_id)

        # 更新文件缓存
        SEND_FILE_CACHE[chat_key].append(file_md5)
        SEND_FILE_CACHE[chat_key] = SEND_FILE_CACHE[chat_key][-3:]  # 只保留最近 3 个文件的 MD5
    except Exception as e:
        raise Exception(
            f"Error sending file to chat: {e}, make sure the file path is valid(in shared directory or uploads directory).",
        ) from e


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="获取用户头像",
    description="获取用户头像",
)
async def get_user_avatar(_ctx: AgentCtx, user_qq: str) -> str:
    """获取用户头像

    Args:
        user_qq (str): 用户 QQ 号 (即 onebot 适配器的用户 id)

    Returns:
        str: 头像文件路径
    """
    try:
        return await user.get_avatar(user_qq, _ctx)
    except Exception as e:
        raise Exception(f"Error getting user avatar: {e}") from e


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="查看字符串内容",
    description="查看字符串内容，支持分页浏览大数据",
)
async def view_str_content(
    _ctx: AgentCtx,
    data_str: str,
    start_line: int = 1,
    end_line: int = 100,
    max_len: int = 4096,
    show_line_num: bool = False,
) -> str:
    """查看字符串内容，用于在运行时"看到"数据内容以进行分析和决策

    适用场景：
    - 查看读取的文件内容（Excel、CSV、文本文件等）
    - 浏览处理后的数据结果
    - 检查长字符串的具体内容

    Args:
        data_str (str): 要查看的数据字符串
        start_line (int): 起始行号，从 1 开始 (Default: 1)
        end_line (int): 结束行号，包含该行 (Default: 100)
        max_len (int): 返回内容的最大字符数 (Default: 4096)
        show_line_num (bool): 是否在每行前显示行号 (Default: False)

    Returns:
        str: 数据内容，包含元信息（总行数、是否截断等）

    Example:
        # 查看 Excel 文件内容
        import pandas as pd
        df = pd.read_excel("/shared/data.xlsx")
        view_str_content(df.to_string())  # 查看前100行

        # 分页浏览大数据
        view_str_content(df.to_string(), start_line=101, end_line=200)  # 查看第101-200行

        # 查看 CSV 文件
        df = pd.read_csv("/shared/data.csv")
        view_str_content(df.head(50).to_string())  # 推荐：先用 pandas 筛选再查看

        # 查看文本文件内容并显示行号
        with open("/shared/readme.txt", "r") as f:
            content = f.read()
        view_str_content(content, start_line=1, end_line=50, show_line_num=True)
    """
    if not data_str:
        return "⚠️ 数据为空，没有内容可查看。"

    # 按行分割数据
    lines = data_str.splitlines()
    total_lines = len(lines)

    # 参数边界校验
    start_line = max(1, start_line)
    end_line = min(total_lines, end_line)

    if start_line > total_lines:
        return f"⚠️ 起始行号 {start_line} 超出数据范围，数据共 {total_lines} 行。"

    if start_line > end_line:
        return f"⚠️ 起始行号 ({start_line}) 不能大于结束行号 ({end_line})。"

    # 提取指定行范围（转换为 0-indexed）
    selected_lines = lines[start_line - 1 : end_line]

    # 构建内容（根据参数决定是否显示行号）
    if show_line_num:
        line_width = len(str(end_line))  # 行号宽度，用于对齐
        formatted_lines = [f"{i:>{line_width}}| {line}" for i, line in enumerate(selected_lines, start=start_line)]
    else:
        formatted_lines = selected_lines
    content = "\n".join(formatted_lines)

    # 检查是否需要截断
    is_truncated = False
    if len(content) > max_len:
        content = content[:max_len]
        # 确保在换行符处截断，避免截断半行
        last_newline = content.rfind("\n")
        if last_newline > max_len // 2:
            content = content[:last_newline]
        is_truncated = True

    # 构建元信息头部
    meta_parts = [f"📊 数据概览: 共 {total_lines} 行"]

    if start_line > 1 or end_line < total_lines:
        meta_parts.append(f"当前显示: 第 {start_line}-{min(end_line, total_lines)} 行")

    if is_truncated:
        meta_parts.append("⚠️ 内容已截断，请缩小行范围或减少 max_len 查看完整内容")

    # 提供分页建议
    if end_line < total_lines:
        next_start = end_line + 1
        next_end = min(end_line + 100, total_lines)
        meta_parts.append(f"💡 查看下一页: view_str_content(your_str, start_line={next_start}, end_line={next_end})")

    meta_header = " | ".join(meta_parts)

    return f"{meta_header}\n{'─' * 60}\n{content}"


@plugin.mount_collect_methods()
async def collect_available_methods(_ctx: AgentCtx) -> List[Callable]:
    """根据适配器收集可用方法"""
    methods: List[Callable] = []

    # 基础能力：大多数适配器支持文本与文件发送
    if _ctx.adapter_key == "minecraft":
        methods = [send_msg_text]
    elif _ctx.adapter_key == "sse":
        methods = [send_msg_text, send_msg_file]
    elif _ctx.adapter_key == "onebot_v11":
        # 仅 OneBot 提供头像工具
        methods = [send_msg_text, send_msg_file, get_user_avatar]
    else:
        # 其他（包含 telegram、discord、wechatpad 等）
        methods = [send_msg_text, send_msg_file]

    # 根据配置添加字符串内容查看工具
    if config.ENABLE_VIEW_STR_CONTENT:
        methods.append(view_str_content)

    return methods


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
    global SEND_MSG_CACHE, SEND_FILE_CACHE
    SEND_MSG_CACHE = {}
    SEND_FILE_CACHE = {}
