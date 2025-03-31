import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import chromadb
import chromadb.errors
import httpx
from mem0 import Memory
from pydantic import Field

from nekro_agent.api.core import logger
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.config import ModelConfigGroup
from nekro_agent.core.config import config as core_config
from nekro_agent.services.agent.creator import OpenAIChatMessage
from nekro_agent.services.agent.openai import gen_openai_chat_response
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

# 扩展元数据
plugin = NekroPlugin(
    name="[NA] 记忆模块",
    module_name="memory",
    description="长期记忆管理系统,支持记忆的增删改查及语义搜索",
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

#根据模型名获取模型组配置项
def get_model_group_info(model_name: str) -> ModelConfigGroup:
    try:
        return core_config.MODEL_GROUPS[model_name]
    except KeyError as e:
        raise ValueError(f"模型组 '{model_name}' 不存在，请确认配置正确") from e

@plugin.mount_config()
class MemoryConfig(ConfigBase):
    """基础配置"""

    MEMORY_MANAGE_MODEL: str = Field(
        default="default",
        title="记忆管理模型",
        description="用于将传入的记忆内容简化整理的llm,填入模型组名称即可",
    )
    TEXT_EMBEDDING_MODEL: str = Field(
        default="default",
        title="向量嵌入模型",
        description="用于将传入的记忆进行向量嵌入,填入模型组名称即可",
    )
    SESSION_ISOLATION: bool = Field(
        default=True,
        title="记忆会话隔离",
        description="开启后bot存储的记忆只对当前会话有效,在其他会话中无法获取",
    )
    AUTO_MEMORY_ENABLED: bool = Field(
        default=True,
        title="启用自动记忆检索",
        description="启用后,系统将在对话开始时自动检索与当前对话相关的用户的所有记忆",
    )
    AUTO_MEMORY_SEARCH_LIMIT: int = Field(
        default=5,
        title="自动记忆检索数量上限",
        description="自动检索时返回的记忆条数上限",
    )
    AUTO_MEMORY_CONTEXT_MESSAGE_COUNT: int = Field(
        default=5,
        title="上下文消息数",
        description="可获取到的上下文消息数量",
    )
    AUTO_MEMORY_USE_TOPIC_SEARCH: bool = Field(
        default=True,
        title="启用话题搜索",
        description="启用后,系统将使用LLM来找到最近聊天话题,并通过话题获取相关记忆,可能会延长响应时间",
    )
    TOPIC_CACHE_EXPIRE_SECONDS: int = Field(
        default=60,
        title="话题缓存时长",
        description="系统将临时保留话题,超时后再重新总结",
    )

memory_config: MemoryConfig = plugin.get_config(MemoryConfig)

# 初始化mem0客户端

_mem0_instance = None
_last_config_hash = None
_thread_pool = ThreadPoolExecutor(max_workers=5)  # 创建一个线程池用于执行同步操作

# 添加记忆注入缓存，避免短时间内重复执行
_memory_inject_cache = {}
_MEMORY_CACHE_EXPIRE_SECONDS = 60  # 缓存有效期，单位秒

def get_mem0_client():
    global _mem0_instance, _last_config_hash
    memory_config = plugin.get_config(MemoryConfig)
    # 计算当前配置的哈希值
    current_config = {
        "MEMORY_MANAGE_MODEL": memory_config.MEMORY_MANAGE_MODEL,
        "TEXT_EMBEDDING_MODEL": memory_config.TEXT_EMBEDDING_MODEL,
        "SESSION_ISOLATION": memory_config.SESSION_ISOLATION,
        "AUTO_MEMORY_ENABLED": memory_config.AUTO_MEMORY_ENABLED,
        "AUTO_MEMORY_SEARCH_LIMIT": memory_config.AUTO_MEMORY_SEARCH_LIMIT,
        "AUTO_MEMORY_CONTEXT_MESSAGE_COUNT": memory_config.AUTO_MEMORY_CONTEXT_MESSAGE_COUNT,
        "AUTO_MEMORY_USE_TOPIC_SEARCH": memory_config.AUTO_MEMORY_USE_TOPIC_SEARCH,
        "llm_model_name": get_model_group_info(memory_config.MEMORY_MANAGE_MODEL).CHAT_MODEL,
        "llm_api_key": get_model_group_info(memory_config.MEMORY_MANAGE_MODEL).API_KEY,
        "llm_base_url": get_model_group_info(memory_config.MEMORY_MANAGE_MODEL).BASE_URL,
        "embedder_model_name": get_model_group_info(memory_config.TEXT_EMBEDDING_MODEL).CHAT_MODEL,
        "embedder_api_key": get_model_group_info(memory_config.TEXT_EMBEDDING_MODEL).API_KEY,
        "embedder_base_url": get_model_group_info(memory_config.TEXT_EMBEDDING_MODEL).BASE_URL,
    }
    
    # 验证字段不能为空字符串
    errors = []
    
    if not current_config["llm_model_name"]:
        errors.append(f"模型组 '{memory_config.MEMORY_MANAGE_MODEL}' 的CHAT_MODEL不能为空")
    if not current_config["llm_api_key"]:
        errors.append(f"模型组 '{memory_config.MEMORY_MANAGE_MODEL}' 的API_KEY不能为空")
    if not current_config["llm_base_url"]:
        errors.append(f"模型组 '{memory_config.MEMORY_MANAGE_MODEL}' 的BASE_URL不能为空")
    if not current_config["embedder_model_name"]:
        errors.append(f"模型组 '{memory_config.TEXT_EMBEDDING_MODEL}' 的CHAT_MODEL不能为空")
    if not current_config["embedder_api_key"]:
        errors.append(f"模型组 '{memory_config.TEXT_EMBEDDING_MODEL}' 的API_KEY不能为空")
    if not current_config["embedder_base_url"]:
        errors.append(f"模型组 '{memory_config.TEXT_EMBEDDING_MODEL}' 的BASE_URL不能为空")
    
    if errors:
        error_message = "记忆模块配置错误：\n" + "\n".join([f"- {error}" for error in errors])
        logger.error(error_message)
        raise ValueError(error_message)
    
    
    current_hash = hash(frozenset(current_config.items()))
    
    # 如果配置变了或者实例不存在，重新初始化
    if _mem0_instance is None or current_hash != _last_config_hash:
        # 重新构建配置
        mem0_client_config = {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "path": str(plugin.get_plugin_path() / "vector_db"),
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "api_key": current_config["llm_api_key"],
                    "model": current_config["llm_model_name"],
                    "openai_base_url": current_config["llm_base_url"],
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "api_key": current_config["embedder_api_key"],
                    "model": current_config["embedder_model_name"],
                    "openai_base_url": current_config["embedder_base_url"],
                },
            },
            "version": "v1.1",
        }
        
        # 创建新实例
        _mem0_instance = Memory.from_config(mem0_client_config)
        _last_config_hash = current_hash
        logger.info("记忆管理器已重新初始化")
        
    return _mem0_instance

# 将同步方法包装成异步方法
async def async_mem0_search(mem0, query: str, user_id: str):
    """异步执行mem0.search，避免阻塞事件循环"""
    return await asyncio.get_event_loop().run_in_executor(
        _thread_pool, 
        lambda: mem0.search(query=query, user_id=user_id),
    )

async def async_mem0_get_all(mem0, user_id: str):
    """异步执行mem0.get_all，避免阻塞事件循环"""
    return await asyncio.get_event_loop().run_in_executor(
        _thread_pool, 
        lambda: mem0.get_all(user_id=user_id),
    )

async def async_mem0_add(mem0, messages: str, user_id: str, metadata: Dict[str, Any]):
    """异步执行mem0.add，避免阻塞事件循环"""
    return await asyncio.get_event_loop().run_in_executor(
        _thread_pool, 
        lambda: mem0.add(messages=messages, user_id=user_id, metadata=metadata),
    )

async def async_mem0_update(mem0, memory_id: str, data: str):
    """异步执行mem0.update，避免阻塞事件循环"""
    return await asyncio.get_event_loop().run_in_executor(
        _thread_pool, 
        lambda: mem0.update(memory_id=memory_id, data=data),
    )

async def async_mem0_history(mem0, memory_id: str):
    """异步执行mem0.history，避免阻塞事件循环"""
    return await asyncio.get_event_loop().run_in_executor(
        _thread_pool, 
        lambda: mem0.history(memory_id=memory_id),
    )

@plugin.mount_prompt_inject_method(name="memory_prompt_inject")
async def memory_prompt_inject(_ctx: AgentCtx) -> str:
    """记忆提示注入,在对话开始前检索相关记忆并注入到对话提示中"""
    global _memory_inject_cache
    
    # 检查缓存是否存在且未过期
    current_time = time.time()
    cache_key = _ctx.from_chat_key
    if cache_key in _memory_inject_cache:
        cache_data = _memory_inject_cache[cache_key]
        if current_time - cache_data["timestamp"] < _MEMORY_CACHE_EXPIRE_SECONDS:
            logger.info(f"使用缓存的记忆注入结果，剩余有效期：{int(_MEMORY_CACHE_EXPIRE_SECONDS - (current_time - cache_data['timestamp']))}秒")
            return cache_data["result"]
    
    # 没有缓存或缓存已过期，执行正常流程
    mem0 = get_mem0_client()
    if not memory_config.AUTO_MEMORY_ENABLED:
        return ""
    
    try:
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.models.db_chat_message import DBChatMessage
        
        # 获取会话信息
        db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=_ctx.from_chat_key)
        
        # 从会话键中提取用户ID和类型
        parts = _ctx.from_chat_key.split("_")
        if len(parts) != 2:
            return ""
        
        chat_type, chat_id = parts
        
        # 获取最近消息,用于识别用户和上下文
        record_sta_timestamp = int(time.time() - core_config.AI_CHAT_CONTEXT_EXPIRE_SECONDS)
        recent_messages: List[DBChatMessage] = await (
            DBChatMessage.filter(
                send_timestamp__gte=max(record_sta_timestamp, db_chat_channel.conversation_start_time.timestamp()),
                chat_key=_ctx.from_chat_key,
            )
            .order_by("-send_timestamp")
            .limit(memory_config.AUTO_MEMORY_CONTEXT_MESSAGE_COUNT)
        )
        recent_messages = [msg for msg in recent_messages if msg.sender_bind_qq != "0"] #去除系统发言

        if not recent_messages:
            return ""
        
        # 用于保存找到的用户记忆
        all_memories = []
        
        # 构建上下文内容,用于语义搜索
        context_content = "\n".join([db_message.parse_chat_history_prompt("") for db_message in recent_messages])
        # 识别参与对话的用户
        user_ids = set()
        
        # 只对私聊启用自动记忆检索
        if chat_type == "private":
            user_ids.add(chat_id)
        elif chat_type == "group":
            # 从最近消息中提取所有发言用户的QQ号
            for msg in recent_messages:
                if msg.sender_bind_qq and msg.sender_bind_qq != "0":
                    user_ids.add(msg.sender_bind_qq)

        # 没有找到有效用户ID,返回空
        if not user_ids:
            return ""
            
        # 对每个用户进行记忆检索
        for user_id in user_ids:
            try:
                # 如果启用会话隔离,添加会话前缀
                search_user_id = _ctx.from_chat_key + user_id if memory_config.SESSION_ISOLATION else user_id
                
                # 使用话题检索
                if memory_config.AUTO_MEMORY_USE_TOPIC_SEARCH and context_content:
        
                    # 使用话题搜索检索与当前对话上下文相关的记忆
                    # 调用LLM获取话题关键词
                    # 获取模型配置
                    memory_manage_model_group = get_model_group_info(memory_config.MEMORY_MANAGE_MODEL)
                    
                    # 准备消息
                    messages = [
                        OpenAIChatMessage.from_text("system", f"你是一个聊天主题分析专家,请分析给定的对话内容并总结用户{user_id}发言的关键词.只返回关键词,不要有任何解释或额外文本.例如'生日''爱好''喜欢的食物'等."),
                        OpenAIChatMessage.from_text("user", context_content),
                    ]
                    
                    # 调用LLM获取话题关键词
                    try:
                        llm_response = await gen_openai_chat_response(
                            model=memory_manage_model_group.CHAT_MODEL,
                            messages=[msg.to_dict() for msg in messages],
                            base_url=memory_manage_model_group.BASE_URL,
                            api_key=memory_manage_model_group.API_KEY,
                            stream_mode=False,
                        )
                        topic_keywords = llm_response.response_content.strip()
                        logger.info(f"话题分析结果: {topic_keywords}")
                        
                        # 使用生成的关键词进行搜索
                        result = await async_mem0_search(
                            mem0,
                            query=topic_keywords, 
                            user_id=search_user_id,
                        )
                        user_memories = result.get("results", [])
                    except Exception as e:
                        logger.error(f"话题分析失败: {e!s}")
                        # 出错时直接获取用户的所有记忆作为备选
                        result = await async_mem0_get_all(mem0, user_id=search_user_id)
                        user_memories = result.get("results", [])
                else:
                    # 搜索用户的所有记忆
                    result = await async_mem0_get_all(mem0, user_id=search_user_id)
                    user_memories = result.get("results", [])
                
                # 限制返回记忆数量
                user_memories = user_memories[:memory_config.AUTO_MEMORY_SEARCH_LIMIT]
                
                # 为每个记忆添加用户信息
                for memory in user_memories:
                    memory["user_qq"] = user_id
                    # 尝试获取用户昵称
                    for msg in recent_messages:
                        if msg.sender_bind_qq == user_id:
                            memory["user_nickname"] = msg.sender_nickname
                            break
                    else:
                        memory["user_nickname"] = user_id
                
                all_memories.extend(user_memories)
            except Exception as e:
                logger.error(f"检索用户 {user_id} 的记忆失败: {e!s}")
        
        if not all_memories:
            return ""
        # 按相关性排序（如果有分数的话）
        all_memories.sort(key=lambda x: float(x.get("score", 0) or 0), reverse=True)
        # 限制返回记忆数量
        all_memories = all_memories[:memory_config.AUTO_MEMORY_SEARCH_LIMIT]
        
        # 格式化记忆内容
        memory_text = "以下是当前会话的相关记忆,请你认真阅读,在没有需要的记忆内容时才使用search_memory:\n"
        for idx, mem in enumerate(all_memories, 1):
            metadata = mem.get("metadata", {})
            nickname = mem.get("user_nickname", mem.get("user_qq", "未知用户"))
            memory_id = encode_id(mem.get("id","未知ID"))
            score = round(float(mem.get("score", 0)), 3) if mem.get("score") else "暂无"
            memory_text += f"{idx}. [ 记忆归属: {nickname} | 元数据: {metadata} | ID: {memory_id} | 匹配度: {score} ] 内容: {mem['memory']}\n"
        logger.info(memory_text)
        
        # 将结果存入缓存
        _memory_inject_cache[cache_key] = {
            "timestamp": current_time,
            "result": memory_text,
        }
        
        # 清理过期缓存
        expired_keys = [k for k, v in _memory_inject_cache.items() if current_time - v["timestamp"] > _MEMORY_CACHE_EXPIRE_SECONDS]
        for k in expired_keys:
            del _memory_inject_cache[k]
        
        return memory_text  # noqa: TRY300
    except Exception as e:
        logger.error(f"自动记忆检索失败: {e!s}")
        raise RuntimeError(f"记忆提示注入失败: {e!s}") from e

@plugin.mount_sandbox_method(SandboxMethodType.TOOL,name="memory_notice")
async def _memory_notice(_ctx: AgentCtx):
    """
    Do Not Call This Function!
    这是有关记忆模块的提示
    ⚠️ 关键注意：
    - 在使用以下Function时,尽量放在代码最后进行处理,特别是send_msg_text或是send_msg_file
    - user_id必须严格指向记忆的归属主体,metadata中的字段不可替代user_id的作用
    - 如果要存储的记忆中包含时间信息,禁止使用(昨天,前天,之后等)相对时间概念,应使用具体的时间(比如20xx年x月x日 x时x分)
    - 对于虚拟角色,需使用其英文小写全名,例如("hatsune_miku","takanashi_hoshino")
    - 若记忆内容属于对话中的用户,则在存储记忆时user_id=该用户ID(如QQ号为123456的用户说"我的小名是喵喵",则user_id="123456",记忆内容为"小名是喵喵")
    - 若记忆内容属于第三方,则在存储记忆时user_id=第三方ID(如QQ号为123456的用户说"@114514喜欢游泳",则user_id="114514",记忆内容为"喜欢游泳")
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
        user_id (str): 关联的用户ID,标识应为用户qq,例如2708583339,而非chat_key.传入空字符串则代表查询有关自身记忆
        metadata (Dict[str, Any]): 元数据标签,{"category": "hobbies"}
        
    Returns:
        str: 记忆ID
        
    Example:
        add_memory("喜欢周末打板球", "114514", {"category": "hobbies","sport_type": "cricket"})
        add_memory("喜欢吃披萨", "123456", {"category": "hobbies","food_type": "pizza"})
        add_memory("喜欢打csgo", "114514", {"category": "hobbies","game_type": "csgo"})
        add_memory("小名是喵喵", "123456", {"category": "name","nickname": "喵喵"})
    """
    mem0 = get_mem0_client()
    if user_id == "":
        user_id = core_config.BOT_QQ

    if memory_config.SESSION_ISOLATION :
        user_id = _ctx.from_chat_key + user_id

    user_id = user_id.replace(" ", "_")

    try:
        result = await async_mem0_add(mem0, messages=memory, user_id=user_id, metadata=metadata)
        logger.info(f"添加记忆结果: {result}")
        if result.get("results"):
            memory_id = result["results"][0]["id"]
            short_id = encode_id(memory_id)  # 添加编码
            return f"记忆添加成功,ID：{short_id}"
        return ""  # noqa: TRY300
    except httpx.HTTPError as e:
        logger.error(f"网络请求失败: {e!s}")
        raise RuntimeError(f"网络请求失败: {e!s}") from e
    except Exception as e:
        logger.error(f"添加记忆失败: {e!s}")
        raise RuntimeError(f"记忆添加失败: {e!s}") from e

@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="搜索记忆",
    description="通过模糊描述对有关记忆进行搜索",
)
async def search_memory(_ctx: AgentCtx, query: str, user_id: str) -> str:
    """搜索记忆
    在使用该方法前先关注提示词中出现的 "当前会话相关记忆" 字样,如果已有需要的相关记忆,则不需要再使用search_memory进行搜索
    Args:
        query (str): 要搜索的记忆内容文本,可以是问句,例如"喜欢吃什么","生日是多久"
        user_id (str): 要查询的用户唯一标识,标识应为用户qq,例如123456,而非chat_key.传入空字符串则代表查询有关自身记忆
    Examples:
        search_memory("2025年3月1日吃了什么","123456")
    """
    mem0 = get_mem0_client()
    if user_id == "":
        user_id = core_config.BOT_QQ
    
    if memory_config.SESSION_ISOLATION :
        user_id = _ctx.from_chat_key + user_id

    user_id = user_id.replace(" ", "_")

    try:
        result = await async_mem0_search(mem0, query=query, user_id=user_id)
        logger.info(f"搜索记忆结果: {result}")
        return "以下是你对该用户的记忆:\n" + format_memories(result.get("results", []))
    except httpx.HTTPError as e:
        logger.error(f"网络请求失败: {e!s}")
        raise RuntimeError(f"网络请求失败: {e!s}") from e
    except Exception as e:
        logger.error(f"搜索记忆失败: {e!s}")
        raise RuntimeError(f"搜索记忆失败: {e!s}") from e

@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="获取记忆",
    description="获取有关该用户的所有记忆",
)
async def get_all_memories( _ctx: AgentCtx,user_id: str) -> str:
    """获取用户所有记忆
    Args:
        user_id (str): 要查询的用户唯一标识,标识应为用户qq,例如123456,而非chat_key.传入空字符串则代表查询有关自身记忆
    Returns:
        str: 格式化后的记忆列表字符串,包含记忆内容和元数据
        
    Example:
        get_all_memories("123456")
    """
    mem0 = get_mem0_client()
    if user_id == "":
        user_id = core_config.BOT_QQ

    if memory_config.SESSION_ISOLATION :
        user_id = _ctx.from_chat_key + user_id

    user_id = user_id.replace(" ", "_")
    
    try:        
        result = await async_mem0_get_all(mem0, user_id=user_id)
        logger.info(f"获取所有记忆结果: {result}")
        return "以下是你脑海中的记忆:\n" + format_memories(result.get("results", []))
    except httpx.HTTPError as e:
        logger.error(f"网络请求失败: {e!s}")
        raise RuntimeError(f"网络请求失败: {e!s}") from e
    except Exception as e:
        logger.error(f"获取记忆失败: {e!s}")
        raise RuntimeError(f"获取记忆失败: {e!s}") from e

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
    mem0 = get_mem0_client()
    try:
        original_id = decode_id(memory_id)  # 解码短ID
    except ValueError as e:
        logger.error(f"无效的记忆ID: {e!s}")
        raise ValueError(f"无效的记忆ID格式: {e!s}") from e
    
    try:        
        result = await async_mem0_update(mem0, memory_id=original_id, data=new_content)
        logger.info(f"更新记忆结果: {result}")
        return result.get("message", "记忆更新成功")
    except httpx.HTTPError as e:
        logger.error(f"更新失败: {e!s}")
        raise RuntimeError(f"网络请求失败: {e!s}") from e
    except Exception as e:
        logger.error(f"更新失败: {e!s}")
        raise RuntimeError(f"记忆更新失败: {e!s}") from e

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
    mem0 = get_mem0_client()
    try:
        original_id = decode_id(memory_id)  # 解码短ID
    except ValueError as e:
        logger.error(f"无效的记忆ID: {e!s}")
        raise ValueError(f"无效的记忆ID格式: {e!s}") from e
    
    try:
        records = await async_mem0_history(mem0, memory_id=original_id)
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
        raise RuntimeError(f"获取记忆历史记录失败: {e!s}") from e
    
@plugin.mount_cleanup_method()
async def clean_up():
    global _mem0_instance, _last_config_hash, _thread_pool, _memory_inject_cache
    _mem0_instance = None
    _last_config_hash = None
    _thread_pool.shutdown()
    _memory_inject_cache = {}
    """清理插件"""