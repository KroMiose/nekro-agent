"""命令系统核心数据模型

定义命令执行上下文、请求、响应及参数描述符。
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

from nekro_agent.schemas.i18n import SupportedLang

# Arg 默认值哨兵
_UNSET = object()


class CommandExecutionContext(BaseModel):
    """命令执行上下文 - 平台无关"""

    user_id: str
    chat_key: str
    username: str
    adapter_key: str
    is_super_user: bool = False
    is_advanced_user: bool = False
    lang: SupportedLang = SupportedLang.ZH_CN  # 命令响应语言


class CommandRequest(BaseModel):
    """命令请求"""

    context: CommandExecutionContext
    command_name: str  # 不含前缀，可含命名空间 (如 "weather" 或 "tools:weather")
    raw_args: str = ""  # 原始参数字符串（由解析器处理）


class CommandResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    INVALID_ARGS = "invalid_args"
    DISABLED = "disabled"
    PROCESSING = "processing"  # 中间状态 (CmdCtl.message)
    WAITING = "waiting"  # 等待用户交互 (CmdCtl.wait)


class CommandOutputSegmentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


class CommandOutputSegment(BaseModel):
    """命令输出段

    `message` 继续作为命令输出摘要使用，`output_segments` 负责承载真正的富媒体内容。
    对于 `image/file` 段：
    - `file_path` 给后端发送链路使用
    - `web_url` 给 WebUI / SSE 直接渲染使用
    """

    type: CommandOutputSegmentType
    text: str = ""
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    web_url: Optional[str] = None


class CommandResponse(BaseModel):
    """命令响应"""

    status: CommandResponseStatus
    message: str
    data: Optional[dict[str, Any]] = None  # 结构化数据 (给 Agent 读取)
    output_segments: Optional[list[CommandOutputSegment]] = None  # 富媒体输出段

    # wait 相关
    callback_cmd: Optional[str] = None  # wait 状态下接收后续输入的命令
    wait_options: Optional[list[str]] = None  # wait 状态下可选项
    wait_timeout: Optional[float] = None  # wait 超时秒数
    on_timeout_message: Optional[str] = None  # wait 超时提示
    context_data: Optional[dict[str, Any]] = None  # 透传给 callback_cmd 的上下文


class Arg:
    """命令参数描述符 - 借鉴 FastAPI 的 Query/Body 设计

    支持两种写法（效果等价）:

    写法一 (推荐，简洁): 直接作为默认值
        location: str = Arg("城市名", default="北京", positional=True)

    写法二 (显式类型): 配合 Annotated
        location: Annotated[str, Arg("城市名", positional=True)] = "北京"

    核心能力:
    - 自动生成 JSON Schema (供 Agent Tool-Use)
    - 支持位置参数和 K-V 参数双模式解析
    - 支持类型校验和范围约束
    """

    def __init__(
        self,
        description: str = "",
        *,
        default: Any = _UNSET,
        positional: bool = False,
        greedy: bool = False,
        choices: Optional[list[str]] = None,
        range: Optional[tuple[Any, Any]] = None,
        prompt_hint: Optional[str] = None,
    ):
        self.description = description
        self.default = default
        self.positional = positional
        self.greedy = greedy
        self.choices = choices
        self.range = range
        self.prompt_hint = prompt_hint

    @property
    def has_default(self) -> bool:
        return self.default is not _UNSET
