import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import aiofiles
import chromadb
import httpx
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from nekro_agent.api import core, schemas
from nekro_agent.core.logger import logger
from nekro_agent.matchers.command import command_guard, finish_with, on_command
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.services.agent.creator import ContentSegment, OpenAIChatMessage
from nekro_agent.services.agent.openai import gen_openai_chat_response
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.tools.path_convertor import convert_to_host_path

plugin = NekroPlugin(
    name="[NA] 表情包插件",
    module_name="emotion",
    description="提供收集、搜索、使用表情包能力",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class EmotionConfig(ConfigBase):
    """表情包配置"""

    MAX_RECENT_EMOTION_COUNT: int = Field(default=10, description="最近添加表情包最大显示数量")
    MAX_SEARCH_RESULTS: int = Field(default=3, description="表情包搜索结果最大数量")
    EMBEDDING_MODEL: str = Field(default="text-embedding-v3", description="使用的嵌入模型")
    EMBEDDING_API_KEY: Optional[str] = Field(default="", description="嵌入模型 API Key")
    EMBEDDING_API_BASE: Optional[str] = Field(default="https://one.api.miose.cn/v1", description="嵌入模型 API 地址")
    EMBEDDING_DIMENSION: int = Field(default=1024, description="嵌入维度")


# 获取配置和插件存储
config = plugin.get_config(EmotionConfig)
store = plugin.store
store_dir = plugin.get_plugin_path() / "emotions"
chroma_client = chromadb.PersistentClient(path=str(plugin.get_plugin_path() / "vector_db"))

# 确保存储目录存在
store_dir.mkdir(parents=True, exist_ok=True)

# 初始化 Chroma 向量集合
COLLECTION_NAME = "emotion_collection"
try:
    emotion_collection = chroma_client.get_collection(name=COLLECTION_NAME)
    logger.info(f"加载已有表情包向量集合: {COLLECTION_NAME}")
except ValueError:
    # 集合不存在时创建新集合
    emotion_collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# region: 表情包系统数据模型
class EmotionMetadata(BaseModel):
    """表情包元数据"""

    description: str
    tags: List[str]
    source_path: str
    file_path: str
    added_time: int
    last_updated: int

    @classmethod
    def create(cls, description: str, tags: List[str], source_path: str, file_path: str):
        current_time = int(time.time())
        return cls(
            description=description,
            tags=tags,
            source_path=source_path,
            file_path=file_path,
            added_time=current_time,
            last_updated=current_time,
        )

    def update(self, description: str, tags: List[str]):
        """更新元数据"""
        self.description = description
        self.tags = tags
        self.last_updated = int(time.time())


class EmotionStore(BaseModel):
    """表情包存储"""

    emotions: Dict[str, EmotionMetadata] = {}
    recent_emotion_ids: List[str] = []

    class Config:
        extra = "ignore"

    def add_emotion(self, emotion_id: str, metadata: EmotionMetadata):
        """添加表情包"""
        self.emotions[emotion_id] = metadata

        # 更新最近添加列表
        if emotion_id in self.recent_emotion_ids:
            self.recent_emotion_ids.remove(emotion_id)
        self.recent_emotion_ids.insert(0, emotion_id)

        # 保持最近列表长度
        max_count = config.MAX_RECENT_EMOTION_COUNT
        self.recent_emotion_ids = self.recent_emotion_ids[:max_count]

    def get_emotion(self, emotion_id: str) -> Optional[EmotionMetadata]:
        """获取表情包元数据"""
        return self.emotions.get(emotion_id)

    def get_recent_emotions(self, count: Optional[int] = None) -> List[Tuple[str, EmotionMetadata]]:
        """获取最近添加的表情包"""
        if count is None:
            count = config.MAX_RECENT_EMOTION_COUNT
        result = []
        for emotion_id in self.recent_emotion_ids[:count]:
            if emotion_id in self.emotions:
                result.append((emotion_id, self.emotions[emotion_id]))
        return result


# endregion: 表情包系统数据模型


# region: 表情包工具方法


async def load_emotion_store() -> EmotionStore:
    """加载表情包存储"""
    data = await store.get(store_key="emotion_store")
    return EmotionStore.model_validate_json(data) if data else EmotionStore()


async def save_emotion_store(emotion_store: EmotionStore):
    """保存表情包存储"""
    await store.set(store_key="emotion_store", value=emotion_store.model_dump_json())


async def generate_embedding(text: str) -> List[float]:
    """生成文本嵌入向量"""

    # 初始化客户端
    client = AsyncOpenAI(
        api_key=config.EMBEDDING_API_KEY,
        base_url=config.EMBEDDING_API_BASE,
    )

    # 调用embedding API
    response = await client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=text,
    )

    # 获取embedding向量
    embedding_vector = response.data[0].embedding
    vector_dimension = len(embedding_vector)
    logger.debug(f"生成嵌入向量: {text[:10]}... 向量维度: {vector_dimension}")

    # 验证维度是否一致
    if vector_dimension != config.EMBEDDING_DIMENSION:
        logger.error(f"嵌入向量维度不匹配！预期: {config.EMBEDDING_DIMENSION}, 实际: {vector_dimension}")
        raise ValueError(
            f"嵌入向量维度错误！预期为 {config.EMBEDDING_DIMENSION} 维，但实际获取到{vector_dimension}维。请更新配置中的EMBEDDING_DIMENSION值为{vector_dimension}。",
        )

    return embedding_vector


async def download_image(url: str, save_path: Path) -> bool:
    """下载图片到指定路径"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()

            async with aiofiles.open(save_path, "wb") as f:
                await f.write(response.content)
            return True
    except Exception as e:
        logger.error(f"下载图片失败: {url}, 错误: {e}")
        return False


async def save_image(source_path: str, file_name: str, _ctx: schemas.AgentCtx) -> Tuple[bool, Path]:
    """保存图片到表情包存储目录"""
    target_path = store_dir / file_name

    # 如果是URL，则下载图片
    if source_path.startswith(("http://", "https://")):
        logger.info(f"从URL下载图片: {source_path} 到 {target_path}")
        success = await download_image(source_path, target_path)
        return success, target_path

    # 如果是本地路径，则复制图片
    try:
        source_path_obj = convert_to_host_path(Path(source_path), _ctx.from_chat_key)
        logger.info(f"从本地路径复制图片: {source_path_obj} 到 {target_path}")

        if not source_path_obj.exists():
            logger.error(f"图片不存在: {source_path}")
            return False, target_path

        async with aiofiles.open(source_path_obj, "rb") as src_file:
            content = await src_file.read()

        async with aiofiles.open(target_path, "wb") as target_file:
            await target_file.write(content)

    except Exception as e:
        logger.error(f"保存图片失败: {source_path}, 错误: {e}")
        return False, target_path
    else:
        return True, target_path


def generate_emotion_id(file_path: str, description: str) -> str:
    """生成表情包唯一ID"""
    # 使用文件路径和描述来生成唯一ID
    content = f"{file_path}:{description}:{time.time()}"
    hash_obj = hashlib.md5(content.encode())
    # 取前8位作为ID
    return hash_obj.hexdigest()[:8]


def calculate_file_hash(file_path: Path) -> str:
    """计算文件哈希值，用于检测重复图片"""
    if not file_path.exists():
        return ""

    with file_path.open("rb") as f:
        return hashlib.md5(f.read()).hexdigest()


async def find_duplicate_emotion(file_path: Path) -> Optional[str]:
    """查找重复的表情包，返回已存在表情包的ID"""
    if not file_path.exists():
        return None

    # 计算目标文件的哈希值
    target_hash = calculate_file_hash(file_path)
    if not target_hash:
        return None

    # 加载所有表情包数据
    emotion_store = await load_emotion_store()

    # 遍历查找匹配哈希值的表情包
    for emotion_id, metadata in emotion_store.emotions.items():
        existing_path = Path(metadata.file_path)
        if existing_path.exists():
            existing_hash = calculate_file_hash(existing_path)
            if existing_hash == target_hash:
                logger.info(f"发现重复表情包：{emotion_id}，哈希值：{target_hash}")
                return emotion_id

    return None


# endregion: 表情包工具方法


# region: 表情包命令
@on_command("emo_search", aliases={"emo-search"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if not cmd_content:
        await finish_with(matcher, message="喵~ 请输入要搜索的关键词哦！")
        return

    try:
        # 调用搜索方法
        result = await search_emotion(schemas.AgentCtx(from_chat_key=chat_key), cmd_content)
        # 从返回的字典中提取消息内容
        message = result.get("content", "没有找到相关表情包呢...")
    except Exception as e:
        logger.error(f"搜索表情包失败: {e}")
        message = f"喵呜... 搜索失败了: {e!s}"

    await finish_with(matcher, message=message)


@on_command("emo_stats", aliases={"emo-stats"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    try:
        # 加载表情包存储
        emotion_store = await load_emotion_store()

        # 统计信息
        total_count = len(emotion_store.emotions)
        all_tags = set()
        for metadata in emotion_store.emotions.values():
            all_tags.update(metadata.tags)

        # 限制标签显示数量
        sorted_tags = sorted(all_tags)[:32]
        tags_str = "、".join(sorted_tags) if sorted_tags else "暂无标签"

        message = f"喵~ 这是当前的表情包统计信息：\n总数量：{total_count} 个\n标签集合（top 32）：{tags_str}"
    except Exception as e:
        logger.error(f"统计表情包失败: {e}")
        message = f"喵呜... 统计失败了: {e!s}"

    await finish_with(matcher, message=message)


@on_command("emo_ls", aliases={"emo-ls"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    try:
        # 加载表情包存储
        emotion_store = await load_emotion_store()

        # 获取页码，默认为1
        try:
            page = max(1, int(cmd_content)) if cmd_content else 1
        except ValueError:
            page = 1

        # 计算分页
        page_size = 10
        total_count = len(emotion_store.emotions)
        total_pages = (total_count + page_size - 1) // page_size

        # 确保页码有效
        if page > total_pages:
            await finish_with(matcher, message=f"喵... 当前只有 {total_pages} 页呢，请输入有效的页码～")
            return

        # 获取当前页的表情包
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_count)

        # 构建消息
        message = f"喵~ 这是第 {page}/{total_pages} 页的表情包列表：\n\n"

        # 获取排序后的表情包列表
        sorted_emotions = sorted(
            emotion_store.emotions.items(),
            key=lambda x: x[1].added_time,
            reverse=True,
        )[start_idx:end_idx]

        for emotion_id, metadata in sorted_emotions:
            tags_str = "、".join(metadata.tags[:3]) + ("..." if len(metadata.tags) > 3 else "")
            message += f"ID: {emotion_id}\n描述: {metadata.description[:30]}...\n标签: {tags_str}\n\n"

        message += "使用 emo-list <页码> 查看其他页面～"
    except Exception as e:
        logger.error(f"查看表情包列表失败: {e}")
        message = f"喵呜... 获取列表失败了: {e!s}"

    await finish_with(matcher, message=message)


# endregion: 表情包命令

# region: 表情包提示注入


@plugin.mount_prompt_inject_method("emotion_prompt_inject")
async def emotion_prompt_inject(_ctx: schemas.AgentCtx) -> str:
    """表情包提示注入"""
    emotion_store = await load_emotion_store()
    recent_emotions = emotion_store.get_recent_emotions()

    if not recent_emotions:
        return "Recent Emotions: No emotions added yet. You can use `collect_emotion` to add some. (You should not send 'ID' in your message directly.)"

    prompt_parts = ["Recent Emotions:"]
    for idx, (emotion_id, metadata) in enumerate(recent_emotions, 1):
        tags_str = ", ".join(metadata.tags[:3]) + ("..." if len(metadata.tags) > 3 else "")
        prompt_parts.append(f"{idx}. ID: {emotion_id} - {metadata.description[:30]}... [Tags: {tags_str}]")

    return "\n".join(prompt_parts)


# endregion: 表情包提示注入


# region: 表情包沙盒方法


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "收集表情包")
async def collect_emotion(_ctx: schemas.AgentCtx, source_path: str, description: str, tags: Optional[List[str]] = None) -> str:
    """Collect Emotion (表情包)

    Collect an expression image/GIF and add it to the emotion database.
    **IMPORTANT:** Only collect actual expression images or reaction GIFs, NOT screenshots, photos, or other images! You can only collect the images you are sure about (visible in vision content). Do not collect anything send by yourself!

    Args:
        source_path (str): The path or URL of the expression image
        description (str): A detailed description of the emotion/expression (used for searching. You Must fill it in carefully)
        tags (List[str], optional): Tags for the emotion (e.g. ["happy", "excited", "anime"])

    Returns:
        str: The emotion ID

    Example:
        ```python
        # Collect from URL
        emotion_id = collect_emotion("https://example.com/happy_cat.gif", "一只开心的猫跳来跳去", ["开心", "猫", "可爱", "Q版"])

        # Collect from local path
        emotion_id = collect_emotion("/app/uploads/surprised_anime_girl.png", "蓝色头发的动漫女孩一脸惊讶", ["动漫", "惊讶", "反应"]) # Do not send the emotion ID in your message directly!
        ```
    """
    # 参数验证
    if not source_path:
        raise ValueError("Error: Source path cannot be empty!")

    if not description:
        raise ValueError("Error: Description cannot be empty!")

    # 确保tags是列表
    if tags is None:
        tags = []

    # 确保表情包目录存在
    store_dir.mkdir(parents=True, exist_ok=True)

    # 文件名处理
    if source_path.startswith(("http://", "https://")):
        # 从URL中提取文件名
        path_obj = Path(source_path.split("?")[0])
        file_name = path_obj.name
        # 确保文件名有扩展名
        if not any(file_name.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
            file_name = f"{hashlib.md5(source_path.encode()).hexdigest()[:8]}.png"
    else:
        # 本地文件，直接使用原文件名
        file_name = convert_to_host_path(Path(source_path), _ctx.from_chat_key).name

    # 添加随机字符串避免文件名冲突
    path_obj = Path(file_name)
    file_name = f"{path_obj.stem}_{hashlib.md5(description.encode()).hexdigest()[:6]}{path_obj.suffix}"

    # 保存图片
    success, file_path = await save_image(source_path, file_name, _ctx)
    if not success:
        raise ValueError(f"Error: Failed to save image from {source_path}")

    # 检查是否有重复图片
    duplicate_id = await find_duplicate_emotion(file_path)

    # 加载表情包存储
    emotion_store = await load_emotion_store()

    if duplicate_id:
        # 更新已存在的表情包信息
        logger.info(f"表情包已存在，更新信息: {duplicate_id}")
        metadata = emotion_store.get_emotion(duplicate_id)
        if metadata:
            # 更新元数据
            metadata.update(description, tags)
            emotion_store.add_emotion(duplicate_id, metadata)

            # 更新向量数据库
            try:
                # 生成嵌入向量
                embedding = await generate_embedding(f"{description} {' '.join(tags)}")

                # 先删除旧向量，再添加新向量
                try:
                    # 先尝试删除旧向量
                    emotion_collection.delete(ids=[duplicate_id])
                    logger.info(f"已删除旧向量: {duplicate_id}")
                except Exception as e:
                    logger.warning(f"删除旧向量失败，可能不存在: {e}")

                # 添加新向量
                emotion_collection.add(
                    ids=[duplicate_id],
                    embeddings=[embedding],
                    metadatas=[{"description": description, "tags": ",".join(tags)}],
                )
                logger.info(f"已添加新向量: {duplicate_id}")
            except Exception as e:
                raise ValueError(f"更新向量数据库失败: {e}") from e

            await save_emotion_store(emotion_store)
            return duplicate_id

    # 生成唯一ID
    emotion_id = generate_emotion_id(str(file_path), description)

    # 创建元数据
    metadata = EmotionMetadata.create(
        description=description,
        tags=tags,
        source_path=source_path,
        file_path=str(file_path),
    )

    # 添加到存储
    emotion_store.add_emotion(emotion_id, metadata)
    await save_emotion_store(emotion_store)

    # 添加到向量数据库
    try:
        # 生成嵌入向量
        embedding = await generate_embedding(f"{description} {' '.join(tags)}")

        # 添加到向量数据库
        emotion_collection.add(
            ids=[emotion_id],
            embeddings=[embedding],
            metadatas=[{"description": description, "tags": ",".join(tags)}],
        )
        logger.info(f"已添加表情包描述新向量: {emotion_id}")
    except Exception as e:
        raise ValueError(f"添加到向量数据库失败: {e}") from e
    await message_service.push_system_message(
        _ctx.from_chat_key,
        f"Successfully collected emotion: {emotion_id} - {description} {' '.join(tags)} ({source_path=})",
    )

    return emotion_id


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "获取表情包数据")
async def get_emotion_bytes(_ctx: schemas.AgentCtx, emotion_id: str) -> bytes:
    """Get Emotion Bytes

    Get the raw bytes data of an emotion by its ID.

    Args:
        emotion_id (str): The emotion ID

    Returns:
        bytes: The raw bytes data of the emotion

    Example:
        ```python
        # Get emotion bytes and use it in another function
        emotion_bytes = get_emotion_bytes("a1b2c3d4")
        # Save as a file or use the bytes data...
        ```
    """
    # 加载表情包存储
    emotion_store = await load_emotion_store()

    # 获取表情包元数据
    metadata = emotion_store.get_emotion(emotion_id)
    if not metadata:
        raise ValueError(f"Error: Emotion with ID '{emotion_id}' not found")

    # 获取文件路径
    file_path = Path(metadata.file_path)
    if not file_path.exists():
        raise ValueError(f"Error: Emotion file not found: {file_path}")

    # 读取文件内容
    try:
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()
    except Exception as e:
        raise ValueError(f"Error reading emotion file: {e}") from e


@plugin.mount_sandbox_method(SandboxMethodType.MULTIMODAL_AGENT, "搜索表情包")
async def search_emotion(_ctx: schemas.AgentCtx, query: str, max_results: Optional[int] = None) -> Dict[str, Any]:
    """Search Emotion

    Search for emotions using a text query and display the results.

    Args:
        query (str): The search query
        max_results (int, optional): Maximum number of results to return (default is 3)

    Returns:
        Dict: OpenAI chat message format containing the search results

    Example:
        ```python
        # Search for happy cat emotions
        search_results = search_emotion("开心猫")
        ```
    """
    if not query:
        raise ValueError("Error: Search query cannot be empty!")

    # 设置最大结果数
    search_limit = config.MAX_SEARCH_RESULTS
    if max_results is not None:
        search_limit = max_results

    # 生成查询向量
    query_embedding = await generate_embedding(query)

    # 进行向量搜索
    results = emotion_collection.query(
        query_embeddings=[query_embedding],
        n_results=search_limit,
    )

    # 检查是否有结果
    if not results or not results["ids"] or not results["ids"][0]:
        msg = OpenAIChatMessage.from_text(
            "assistant",
            f"No emotions found for query: '{query}'. Try another search term or collect more emotions.",
        )
        return msg.to_dict()

    # 加载表情包存储
    emotion_store = await load_emotion_store()

    # 构建多模态消息
    msg = OpenAIChatMessage.from_text("user", f"Here are the emotions You have collected for '{query}':")

    for i, emotion_id in enumerate(results["ids"][0]):
        metadata = emotion_store.get_emotion(emotion_id)
        if not metadata:
            continue

        file_path = Path(metadata.file_path)
        if not file_path.exists():
            continue

        # 准备标签字符串
        tags_str = ", ".join(metadata.tags) if metadata.tags else "No tags"

        # 添加表情包详细信息
        msg.batch_add(
            [
                ContentSegment.text_content(
                    f"\nEmotion {i+1} (ID: {emotion_id}):\nDescription: {metadata.description}\nTags: {tags_str}",
                ),
                ContentSegment.image_content_from_path(str(file_path)),
            ],
        )
    msg.add(
        ContentSegment.text_content(
            "If they don't look don't match the description, please use `collect_emotion` immediately to correct it.",
        ),
    )

    return msg.to_dict()


# endregion: 表情包沙盒方法


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
