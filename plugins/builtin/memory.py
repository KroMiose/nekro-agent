from typing import Any, Dict, List, Optional

import chromadb
import chromadb.errors
import httpx
from pydantic import Field

from nekro_agent.api.core import logger
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.config import ModelConfigGroup, config
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

try:
    from mem0 import Memory
except ImportError as err:
    raise ImportError("mem0 未安装，请安装 mem0ai 包") from err

import uuid

# 扩展元数据
plugin = NekroPlugin(
    name="[NA] 记忆模块",
    module_name="memory",
    description="长期记忆管理系统，支持记忆的增删改查及语义搜索",
    version="0.1.0",
    author="Zaxpris",
    url="https://github.com/KroMiose/nekro-agent",
)


# 在现有import后添加以下代码
BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def encode_base62(number: int) -> str:
    """将大整数编码为Base62字符串"""
    if number == 0:
        return BASE62_ALPHABET[0]
    digits = []
    while number > 0:
        number, remainder = divmod(number, 62)
        digits.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(digits))

def decode_base62(encoded: str) -> int:
    """将Base62字符串解码回大整数"""
    number = 0
    for char in encoded:
        number = number * 62 + BASE62_ALPHABET.index(char)
    return number

def encode_id(original_id: str) -> str:
    """将UUID转换为短ID"""
    try:
        uuid_obj = uuid.UUID(original_id)
        return encode_base62(uuid_obj.int)
    except ValueError as err:
        raise ValueError("无效的UUID格式") from err

def decode_id(encoded_id: str) -> str:
    """将短ID转换回原始UUID"""
    try:
        number = decode_base62(encoded_id)
        return str(uuid.UUID(int=number))
    except (ValueError, AttributeError) as err:
        raise ValueError("无效的短ID格式") from err

@plugin.mount_config()
class BasicConfig(ConfigBase):
    """基础配置"""

    MEMORY_MANAGE_MODEL: str = Field(
        default="",
        title="记忆管理模型",
        description="用于将传入的记忆内容简化整理的llm,填入模型组名称即可",
    )
    VECTOR_MODEL: str = Field(
        default="",
        title="向量嵌入模型",
        description="用于将传入的记忆进行向量嵌入,填入模型组名称即可",
    )

memory_config: BasicConfig = plugin.get_config(BasicConfig)

memory_manage_model = memory_config.MEMORY_MANAGE_MODEL or "default"
vector_model = memory_config.VECTOR_MODEL or "default"

memory_manage: ModelConfigGroup = config.MODEL_GROUPS[memory_manage_model]
vector : ModelConfigGroup = config.MODEL_GROUPS[vector_model]
# 初始化内存客户端
mem0_client_config = {
    "vector_store": {
        "provider": "chroma",#这里填你的向量数据库名称
        "config": {
            "path": str(plugin.get_plugin_path() / "vector_db"),  # 指定本地路径
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "api_key": memory_manage.API_KEY,#这里填你的openai api key
            "model": memory_manage.CHAT_MODEL,#这里填llm模型
            "openai_base_url": memory_manage.BASE_URL,#这里可以填任何支持openai api格式的地址
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "api_key": vector.API_KEY,#这里填你的openai api key
            "model": vector.CHAT_MODEL,#这里只能用文本嵌入模型
            "openai_base_url": vector.BASE_URL,#这里可以填任何支持openai api格式的地址
        },
    },
    "version": "v1.1",
}

mem0 = Memory.from_config(mem0_client_config)

def format_memories(results: List[Dict]) -> str:
    """格式化记忆列表为字符串"""
    if not results:
        return "未找到任何记忆"
    
    formatted = []
    for idx, mem in enumerate(results, 1):
        metadata = mem.get("metadata", {})
        created_at = mem.get("created_at", "未知时间")
        score = mem.get("score", "暂无")
        formatted.append(
        f"{idx}. [ID: {encode_id(mem['id'])}]\n"  # 使用短ID
        f"内容: {mem['memory']}\n"
        f"元数据: {metadata}\n"
        f"创建时间: {created_at}\n"
        f"匹配度: {score}\n",
    )
    return "\n".join(formatted)

@plugin.mount_sandbox_method(SandboxMethodType.TOOL,name="")
async def notice(_ctx: AgentCtx):
    """
    这是有关记忆模块的提示
    ⚠️ 关键注意：
    - 绝对禁止将自己的ID作为user_id,除非记忆明确属于自身属性
    - user_id必须严格指向记忆的归属主体,metadata中的字段不可替代user_id的作用
    - 如果要存储的记忆中包含时间信息,禁止使用(昨天,前天,之后等)相对时间概念,应使用具体的时间(比如20xx年x月x日 x时x分)
    - 对于虚拟角色,需使用其英文小写全名,带有空格的部分请使用_替换,例如("hatsune_miku","louis","takanashi_hoshino")
    - 若记忆内容属于对话中的用户,则在存储记忆时user_id=该用户ID(如用户alice说"我的小名是喵喵",user_id="alice",记忆内容为"小名是喵喵")
    - 若记忆内容属于第三方,则在存储记忆时user_id=第三方ID(如用户alice说"我的朋友Bob喜欢游泳",user_id="bob",记忆内容为"喜欢游泳")

    """

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="添加记忆",
    description="指定用户id并添加长期记忆",
)
async def add_memory(
    _ctx: AgentCtx,
    memory: str,
    user_id: str,
    metadata: Dict[str, Any],
) -> str:
    """添加新记忆到用户档案
    
    Args:
        memory (str): 要添加的记忆内容文本
        **非常重要**
        user_id (str): 关联的用户ID,必须为有效非空字符串,标识应为用户qq,例如2708583339,而非chat_key.
        metadata (Dict[str, Any]): 元数据标签，例如分类标签
        
    Returns:
        返回记忆添加成功,并返回记忆ID
        
    Example:
        add_memory("喜欢周末打板球", "alice", {"category": "hobbies","sport_type": "cricket"})
        add_memory("喜欢吃披萨", "alice", {"category": "hobbies","food_type": "pizza"})
        add_memory("喜欢打csgo", "alice", {"category": "hobbies","game_type": "csgo"})
        add_memory("小名是喵喵", "alice", {"category": "name","nickname": "喵喵"})
    """
    try:
        result = mem0.add(messages=memory, user_id=user_id, metadata=metadata)
        logger.info(f"添加记忆结果: {result}")
        if result.get("results"):
            memory_id = result["results"][0]["id"]
            short_id = encode_id(memory_id)  # 添加编码
            return f"记忆添加成功，ID：{short_id}"
    except httpx.HTTPError as e:
        logger.error(f"网络请求失败: {e!s}")
        return "无法连接到记忆存储服务，请检查网络连接"
    except Exception as e:
        logger.error(f"添加记忆失败: {e!s}")
        return f"记忆添加失败: {e!s}"
    return "记忆添加失败：未返回有效ID"

@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="搜索记忆",
    description="通过模糊描述对有关记忆进行搜索",
)
async def search_memory(_ctx: AgentCtx, query: str, user_id: str) -> str:
    """搜索记忆
    Args:
        query (str): 要搜索的记忆内容文本,可以是问句,例如"喜欢吃什么","生日是多久"
        user_id (str): 要查询的用户唯一标识,必须为有效非空字符串,标识应为用户qq,例如2708583339,而非chat_key.
    Examples:
        search_memory("2025年3月1日吃了什么","2708583339")
    """
    try:
        result = mem0.search(query=query, user_id=user_id)
        logger.info(f"搜索记忆结果: {result}")
        return "以下是你对该用户的记忆:\n" + format_memories(result.get("results", []))
    except httpx.HTTPError as e:
        logger.error(f"网络请求失败: {e!s}")
        return "无法连接到记忆存储服务，请稍后再试"
    except Exception as e:
        logger.error(f"搜索记忆失败: {e!s}")
        return f"搜索记忆失败: {e!s}"

@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="获取记忆",
    description="获取有关该用户的所有记忆",
)
async def get_all_memories( _ctx: AgentCtx,user_id: str) -> str:
    """获取用户所有记忆
    Args:
        user_id (str): 要查询的用户唯一标识,必须为有效非空字符串,标识应为用户qq,例如2708583339,而非chat_key.
    Returns:
        str: 格式化后的记忆列表字符串,包含记忆内容和元数据
        
    Example:
        get_all_memories("2708583339")
    """
    try:
        if not user_id.strip():
            return "用户ID不能为空"
        
        result = mem0.get_all(user_id=user_id)
        logger.info(f"获取所有记忆结果: {result}")
        return "以下是你脑海中的记忆:\n" + format_memories(result.get("results", []))
    except httpx.HTTPError as e:
        logger.error(f"网络请求失败: {e!s}")
        return "无法连接到记忆存储服务，请稍后再试"
    except Exception as e:
        logger.error(f"获取记忆失败: {e!s}")
        return f"获取记忆失败: {e!s}"

@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    name="更新记忆",
    description="根据记忆id更新记忆",
)
async def update_memory(_ctx: AgentCtx,memory_id: str, new_content: str) -> str:
    """更新现有记忆内容
    
    Args:
        memory_id (str): 要更新的记忆ID
        new_content (str): 新的记忆内容文本,至少10个字符
    Returns:
        str: 操作结果状态信息
        
    Example:
        update_memory("bf4d4092...", "喜欢周末打网球")
    """
    try:
        original_id = decode_id(memory_id)  # 解码短ID
    except ValueError as e:
        return f"无效的记忆ID: {e!s}"
    
    try:        
        result = mem0.update(memory_id=original_id, data=new_content)
        logger.info(f"更新记忆结果: {result}")
        return result.get("message", "记忆更新成功")
    except httpx.HTTPError:
        return "更新失败：无法连接记忆存储服务"
    except Exception as e:
        logger.error(f"更新失败: {e!s}")
        return f"记忆更新失败: {e!s}"

@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="查询记忆修改记录",
    description="查询指定记忆的修改记录",
)
async def get_memory_history( _ctx: AgentCtx, memory_id: str) -> str:
    """获取记忆修改历史记录,可以查询到记忆修改历史
    
    Args:
        memory_id (str): 要查询的记忆ID
    
    Returns:
        str: 格式化后的历史记录字符串,包含记忆修改历史
        
    Example:
        get_memory_history("bf4d4092...")
    """
    try:
        original_id = decode_id(memory_id)  # 解码短ID
    except ValueError as e:
        return f"无效的记忆ID: {e!s}"
    
    try:
        records = mem0.history(memory_id=original_id)
        logger.info(f"获取历史记录结果: {records}")
        if not records:
            return "该记忆暂无历史记录"
            
        formatted = []
        for idx, r in enumerate(records, 1):
            formatted.append(
                f"{idx}. [事件更改类型: {r['event']}]\n"
                f"旧内容: {r['old_memory'] or '无'}\n"
                f"新内容: {r['new_memory'] or '无'}\n"
                f"时间: {r['created_at']}\n",
            )
        return "\n".join(formatted)
    except Exception as e:
        logger.error(f"获取历史失败: {e!s}")
        return "获取历史记录失败"
    
@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""