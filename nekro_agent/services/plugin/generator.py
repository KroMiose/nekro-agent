"""扩展生成器

负责生成扩展代码和模板。
"""

from typing import Any, AsyncGenerator, Dict, Optional

from nekro_agent.core.config import config
from nekro_agent.tools.llm import get_chat_response, get_chat_response_stream


def generate_extension_template(name: str, description: str) -> str:
    """生成扩展模板

    Args:
        name (str): 扩展名称
        description (str): 扩展描述

    Returns:
        str: 扩展模板代码
    """
    return f'''from typing import Optional
from pydantic import BaseModel

from nekro_agent.api import core, message
from nekro_agent.api.schemas import AgentCtx

__meta__ = core.ExtMetaData(
    name="{name}",
    version="0.1.0",
    author="喵喵小助手",
    description="{description}",
)

@core.agent_collector.mount_method(core.MethodType.TOOL)
async def example_add_method(a: int, b: int, _ctx: AgentCtx) -> int:
    """示例方法

    Args:
        a (int): 参数 a
        b (int): 参数 b

    Returns:
        int: 处理结果
    """
    # 在这里实现你的功能
    return a + b

def clean_up():
    """清理扩展资源"""
    # 如有必要，在此实现清理资源的逻辑
'''


GENERATE_SYSTEM_PROMPT = r'''你是一个专业的 Python 开发者，负责生成 Nekro Agent 的扩展代码。
请根据用户的需求，生成符合以下规范的代码修改建议：

1. 代码规范：
   - 使用 Python 3.8+ 语法
   - 使用类型注解（包括函数参数、返回值和变量）
   - 使用 Pydantic 进行数据验证和模型定义
   - 遵循 PEP8 代码风格（适当的空行、缩进和命名规范）
   - 添加详细的文档字符串（包括函数描述、参数说明、返回值说明和使用示例）
   - 正确处理异常情况（使用 try-except 并记录日志）
   - 返回合适的响应消息（使用 Pydantic 模型或明确的返回类型）

2. 扩展结构：
   - 必须包含 __meta__ 定义，用于描述扩展的基本信息
   - 使用 @core.agent_collector.mount_method 装饰器注册方法，指定正确的方法类型
   - 可选实现 clean_up 函数用于清理资源（如关闭连接、清理缓存等）
   - 相关功能应该组织在同一个扩展中
   - 复杂功能应该拆分为多个子函数，保持代码清晰

3. 方法类型说明：
   a) TOOL 类型 (工具方法)：
      - 用于执行具体的功能操作，如发送消息、处理数据等
      - 返回结果会通过 RPC 返回给沙盒，允许 AI 获取结果继续处理
      - 由于扩展代码和沙盒在两个不同的执行环境运行，不应该通过直接任何文件路径进行交互（例如直接返回文件路径）
      - 参数和返回值必须是可通过 pickle 序列化的基本数据类型（str、int、float、bool、list、dict、byte等）
      - 不要使用复杂对象或自定义类作为参数或返回值
      - 适用场景：用于增强沙盒数据处理能力的扩展

   b) AGENT 类型 (代理方法)：
      - 用于实现 Agent 的核心行为，如对话、决策等
      - 返回 str 类型的执行结果
      - 会阻断程序运行，把方法执行结果添加到上下文并再触发一次新的回复流
      - 适用场景：搜索、查询、计算等需要再次唤醒 AI 基于提供的信息继续回复的场景

   c) BEHAVIOR 类型 (行为方法)：
      - 用于执行特定的行为，如状态更新
      - 返回 str 类型的执行结果
      - 执行结果会被加入上下文供 AI 参考，但不会再触发一次回复流
      - 适用场景：处理结果单一的行为

4. 文档规范：
   - 模块级文档：描述扩展的整体功能和用途
   - 类文档：描述类的功能、属性和使用方法
   - 函数文档：
     * 简短的功能描述
     * 详细的参数说明（类型和用途）
     * 返回值说明
     * 可能抛出的异常
     * 使用示例（不包含 _ctx 参数）
   - 重要逻辑处添加行内注释

5. 错误处理：
   - 所有外部调用都应该包含在 try-except 中
   - 捕获具体的异常类型，避免使用裸异常
   - 异常信息应该包含上下文信息
   - 使用 logger 记录错误详情
   - 返回友好的错误消息给用户

6. 性能考虑：
   - 避免重复计算
   - 合理使用缓存
   - 避免阻塞操作

7. 可用的 API：
   a) 核心 API (nekro_agent.api.core):
      - ExtMetaData: 扩展元数据类
      - MethodType: 方法类型(TOOL/AGENT/BEHAVIOR)
      - agent_collector: 方法收集器
      - logger: 日志记录器
      - config: 配置访问器
      - get_bot(): 获取机器人实例

   b) 消息 API (nekro_agent.api.message):
      - send_text(chat_key: str, message: str, record: bool = True, ctx: AgentCtx)
      - send_image(chat_key: str, image_path: str, record: bool = True, ctx: AgentCtx)
      - send_file(chat_key: str, file_path: str, record: bool = True, ctx: AgentCtx)
      - download_from_url(url: str, ctx: AgentCtx) -> str

   c) 定时器 API (nekro_agent.api.timer):
      - set_timer(chat_key: str, trigger_time: int, event_desc: str) -> bool
      - set_temp_timer(chat_key: str, trigger_time: int, event_desc: str) -> bool
      - clear_timers(chat_key: str, temporary: Optional[bool] = None) -> bool
        * 定时器类型：
          - 普通定时器：用于常规定时提醒，如用户请求的提醒事项
          - 临时定时器：用于 AI 自我唤醒，观察用户反馈，每个会话只保留最后一个临时定时器
        * 清除定时器：
          - temporary=None：清除所有定时器
          - temporary=True：只清除临时定时器
          - temporary=False：只清除非临时定时器
        * 注意事项：
          - 定时器的本质功能是允许 AI 自行唤醒自己的回复流程
          - 非必要不应反复自我唤醒
          - 临时定时器应该及时清理，避免资源浪费

   d) 上下文 API (nekro_agent.api.context):
      - parse_chat_key(chat_key: str) -> Tuple[str, str]
      - get_chat_type(chat_key: str) -> str
      - get_chat_id(chat_key: str) -> str

   e) 用户 API (nekro_agent.api.user):
      - get_avatar(user_qq: str, ctx: AgentCtx) -> str

8. 注意事项：
   - 所有注册方法必须是异步的(async def), 网络请求使用 httpx 库
   - _ctx 参数必须放在参数最后且不在方法文档中提及
   - 注册方法的代码文档中不要出现 await 关键字
   - 认真考虑注册方法文档对 LLM 的参考价值
   - 必须生成完整代码，不要省略内容
   - 必须包含所有必要的导入语句
   - 必须正确处理所有可能的异常
   - 不使用 Optional 类型的扩展方法参数，不要为任何参数设定默认值，要求 AI 必须提供参数
   - 修改代码时对于原代码中重复的内容可以使用 "\# ... existing code ..." 占位

示例扩展结构：

```python
"""天气查询扩展

提供天气查询相关功能，包括实时天气、天气预报等。
使用 wttr.in API 获取天气数据。
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field

from nekro_agent.api import core, message
from nekro_agent.api.schemas import AgentCtx

# 扩展元数据
__meta__ = core.ExtMetaData(
    name="weather",  # Do not modify when generating code for user
    version="1.0.0",
    author="喵喵小助手", # Do not modify when generating code for user
    description="天气查询扩展",
)

@core.agent_collector.mount_method(core.MethodType.AGENT)
async def query_weather(city: str, _ctx: AgentCtx) -> str:
    """查询指定城市的实时天气
    
    Args:
        city (str): 城市名称，如 "北京"、"上海"
    
    Returns:
        str: 天气信息字符串，包含温度、湿度等信息
        
    Example:
        query_weather("北京")
    """
    # 在这里实现你的功能

def clean_up():
    """清理扩展资源"""
    # 如有必要，在此实现清理资源的逻辑

请根据以上规范和示例生成内容。
'''.strip()

GENERATE_USER_PROMPT = """
{'当前代码：' + current_code if current_code else '暂无'}

以下是用户需求：
<requirement>
{prompt}
</requirement>

请根据以上需求生成内容
""".strip()


async def generate_extension_code(file_path: str, prompt: str, current_code: Optional[str] = None) -> str:  # noqa: ARG001
    """生成扩展代码

    Args:
        file_path (str): 文件路径
        prompt (str): 提示词
        current_code (Optional[str], optional): 当前代码. Defaults to None.

    Returns:
        str: 生成的代码
    """
    # 构建提示词
    user_prompt = GENERATE_USER_PROMPT.format(prompt=prompt, current_code=current_code)

    # 调用 LLM 生成代码
    response = await get_chat_response(
        messages=[{"role": "system", "content": GENERATE_SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
        model_group=config.PLUGIN_GENERATE_MODEL_GROUP,
    )

    return _clean_code_format(response)


async def generate_extension_code_stream(
    file_path: str,  # noqa: ARG001
    prompt: str,
    current_code: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """流式生成扩展代码

    Args:
        file_path (str): 文件路径
        prompt (str): 提示词
        current_code (Optional[str], optional): 当前代码. Defaults to None.

    Yields:
        str: 生成的代码片段
    """
    # 构建提示词
    user_prompt = f"""请生成以下扩展功能的代码：

{prompt}

{'当前代码：' + current_code if current_code else '这是一个新文件，请从头开始生成代码。'}
"""

    # 调用 LLM 流式生成代码
    async for chunk in get_chat_response_stream(
        messages=[{"role": "system", "content": GENERATE_SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
        model_group=config.PLUGIN_GENERATE_MODEL_GROUP,
    ):
        yield chunk


APPLY_SYSTEM_PROMPT = r"""You are a specialized model responsible for applying code modifications. Your task is to accurately and completely apply modification suggestions from a generation model to existing code.

Requirements:
1. Understand that these modification suggestions come from another generation model
2. Strictly follow the modification requirements while working with the original code
3. Maintain the code's overall structure and style
4. Ensure the output code is complete and executable, without any placeholder content
5. Follow the modification requirements with 100% fidelity
6. When encountering "... existing code ..." or similar placeholders in modification suggestions:
   - You MUST locate the corresponding content in the original code
   - Replace placeholders with the actual content from the original code
   - Ensure the final output code is complete and executable
7. NEVER use any form of placeholders or omission symbols in your output
8. Output the complete code even for unchanged sections

Return the complete modified code file directly, without any explanations."""

APPLY_USER_PROMPT = """Here is the existing code:
<code>
{current_code}
</code>

Modification requirements (potentially from another LLM's suggestions):
<suggestion>
{prompt}
</suggestion>

Please strictly follow these requirements and return the complete, modified, usable code.

Important Notes:
1. Your output has no length restrictions
2. The modified code MUST be complete, without any placeholders or omitted content
3. NEVER use expressions like "... same as before ..." or any other placeholders
4. When encountering "... existing code ..." placeholders:
   - You MUST locate and replace them with the complete content from the original code
   - Ensure proper context alignment before and after the replaced content
5. ALL code sections MUST be included in the output, even if unchanged
6. The output MUST be complete, executable, and functionally intact Python code
"""


async def apply_extension_code(file_path: str, prompt: str, current_code: str) -> str:  # noqa: ARG001
    """应用生成的代码

    Args:
        file_path (str): 文件路径
        prompt (str): 提示词
        current_code (str): 当前代码

    Returns:
        str: 处理后的代码
    """
    messages = [
        {
            "role": "system",
            "content": APPLY_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": "Please confirm that you understand your responsibilities as an application model: You need to output complete, executable code based on the original code and modification suggestions. Even when the suggestions contain placeholders or omitted content, you must locate and fully replace them with the corresponding original code. You cannot use any form of placeholders or omissions. Do you agree to these requirements?",
        },
        {
            "role": "assistant",
            "content": "Yes, I fully understand my responsibilities:\n1. I am an application model responsible for accurately applying modification suggestions to the original code\n2. I will ensure the output code is complete and executable, without any placeholders\n3. When encountering placeholders in suggestions, I will locate and fully replace them with content from the original code\n4. I will maintain the code's structure and style while ensuring functional completeness\n5. I will include all code sections in the output, even if they remain unchanged\nI am now ready to perform the code modification task.",
        },
        {
            "role": "user",
            "content": APPLY_USER_PROMPT.format(current_code=current_code, prompt=prompt),
        },
    ]

    response = await get_chat_response(messages, model_group=config.PLUGIN_APPLY_MODEL_GROUP)

    return _clean_code_format(response)


def _clean_code_format(code: str) -> str:
    """清理代码格式，移除 Markdown 代码块标记

    Args:
        code (str): 原始代码文本

    Returns:
        str: 清理后的代码
    """
    code = code.strip()
    # 移除开头的 ```python 或 ``` 标记
    if code.lower().startswith("```python"):
        code = code[10:]
    # 移除结尾的 ``` 标记
    if code.endswith("\n```"):
        code = code[:-3]

    return code.strip() + "\n"
