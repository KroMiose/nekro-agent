"""
# 表情包 (Emotion)

提供收集、搜索、使用表情包的能力，使用向量数据库进行智能语义搜索。

## 主要功能

- **智能收藏**: 在聊天时发送图片，AI 会自动询问是否要收藏为表情包，并为其添加描述和标签。
- **语义搜索**: 可以用自然语言描述来搜索表情包，比如 "来张开心的猫猫图"。
- **后台管理**: 提供了一系列命令，方便用户管理自己的表情包收藏。

## 使用方法

- **与 AI 对话**: 在聊天中发送图片，AI 会引导您完成收藏。您也可以直接命令 AI "帮我收藏这张图"。
- **使用命令**: 通过 `emo_search` 等命令直接搜索和管理表情包。

## 命令列表

**注意：所有命令目前仅在 OneBot v11 适配器下可用。**

- `emo_search <关键词>`: 语义搜索表情包。
- `emo_stats`: 查看表情包统计信息。
- `emo_list [页码]`: 分页列出所有表情包。
- `emo_migrate`: 迁移旧的绝对路径到相对路径格式（适用于数据目录迁移后）。
- `emo_reindex -y`: 重建索引（高级功能，一般无需使用）。

## 配置说明

- **严格表情包模式**: 开启后，插件会尝试拒绝收藏截图、照片等非表情包内容的图片。
- **嵌入模型组**: 需要正确配置一个向量模型才能使用语义搜索功能。
"""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Annotated, Any, AsyncIterator, Dict, List, Optional, Tuple

import aiofiles
import httpx
from pydantic import BaseModel, Field
from qdrant_client import models as qdrant_models

from nekro_agent.api import i18n, schemas
from nekro_agent.api.core import ModelConfigGroup, get_qdrant_client, logger
from nekro_agent.api.core import config as core_config
from nekro_agent.api.plugin import (
    ConfigBase,
    ExtraField,
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.services.agent.creator import ContentSegment, OpenAIChatMessage
from nekro_agent.services.agent.openai import gen_openai_embeddings
from nekro_agent.services.command.base import CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse
from nekro_agent.services.message_service import message_service
from nekro_agent.tools.common_util import copy_to_upload_dir
from nekro_agent.tools.path_convertor import (
    convert_filename_to_sandbox_upload_path,
    convert_to_host_path,
)

plugin = NekroPlugin(
    name="表情包插件",
    module_name="emotion",
    description="提供收集、搜索、使用表情包能力，使用Qdrant向量数据库",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11", "discord"],
    i18n_name=i18n.i18n_text(
        zh_CN="表情包插件",
        en_US="Emotion Pack Plugin",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="提供收集、搜索、使用表情包能力，使用Qdrant向量数据库",
        en_US="Provides emotion pack collection, search and usage features using Qdrant vector database",
    ),
    sleep_brief="用于收藏、搜索和发送表情包，在需要图片表情语义检索或表情管理时激活。",
)


@plugin.mount_config()
class EmotionConfig(ConfigBase):
    """表情包配置"""

    MAX_RECENT_EMOTION_COUNT: int = Field(
        default=5,
        title="最近添加表情包显示数量",
        description="最近添加表情包最大显示数量",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="最近添加表情包显示数量",
                en_US="Recent Emotion Display Count",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="最近添加表情包最大显示数量",
                en_US="Maximum number of recently added emotions to display",
            ),
        ).model_dump(),
    )
    MAX_SEARCH_RESULTS: int = Field(
        default=3,
        title="搜索结果显示数量",
        description="搜索结果显示数量",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="搜索结果显示数量",
                en_US="Search Result Display Count",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="搜索结果显示数量",
                en_US="Number of search results to display",
            ),
        ).model_dump(),
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding",
        title="嵌入模型组",
        description="在此填入向量嵌入模型组名称",
        json_schema_extra=ExtraField(
            ref_model_groups=True,
            required=True,
            model_type="embedding",
            i18n_title=i18n.i18n_text(
                zh_CN="嵌入模型组",
                en_US="Embedding Model Group",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="在此填入向量嵌入模型组名称",
                en_US="Enter the vector embedding model group name here",
            ),
        ).model_dump(),
    )
    EMBEDDING_DIMENSION: int = Field(
        default=1024,
        title="嵌入维度",
        description="嵌入维度",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="嵌入维度",
                en_US="Embedding Dimension",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="嵌入维度",
                en_US="Dimension of embeddings",
            ),
        ).model_dump(),
    )
    STRICT_EMOTION_COLLECT: bool = Field(
        default=False,
        title="严格表情包模式",
        description="是否严格限制表情包收集并拒绝非表情包内容 (截图、非表情包内容等)",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="严格表情包模式",
                en_US="Strict Emotion Mode",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="是否严格限制表情包收集并拒绝非表情包内容 (截图、非表情包内容等)",
                en_US="Whether to strictly limit emotion collection and reject non-emotion content (screenshots, etc.)",
            ),
        ).model_dump(),
    )
    EMBEDDING_REQUEST_TIMEOUT: int = Field(
        default=5,
        title="向量化请求超时时间",
        description="生成嵌入向量时的 API 请求超时时间（秒）",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="向量化请求超时时间",
                en_US="Embedding Request Timeout",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="生成嵌入向量时的 API 请求超时时间（秒）",
                en_US="Timeout in seconds for embedding API requests",
            ),
        ).model_dump(),
    )
    IMAGE_DOWNLOAD_TIMEOUT: int = Field(
        default=30,
        title="图片下载超时时间",
        description="下载表情包图片时的超时时间（秒）",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="图片下载超时时间",
                en_US="Image Download Timeout",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="下载表情包图片时的超时时间（秒）",
                en_US="Timeout in seconds for downloading emotion images",
            ),
        ).model_dump(),
    )


# 获取配置和插件存储
emotion_config: EmotionConfig = plugin.get_config(EmotionConfig)
store = plugin.store
store_dir = plugin.get_plugin_path() / "emotions"

# 确保存储目录存在
store_dir.mkdir(parents=True, exist_ok=True)


@plugin.mount_init_method()
async def init_vector_db():
    """初始化表情包向量数据库"""
    # 先执行路径迁移（如果需要）
    try:
        await migrate_emotion_paths()
    except Exception as e:
        logger.error(f"迁移表情包路径失败: {e}")

    # 获取Qdrant客户端
    client = await get_qdrant_client()
    if client is None:
        logger.warning("无法获取Qdrant客户端，跳过向量数据库初始化")
        return

    collection_name = plugin.get_vector_collection_name()

    # 检查集合是否存在
    try:
        collections = await client.get_collections()
    except Exception as e:
        raise ValueError(f"获取Qdrant集合失败: {e}") from e

    collection_names = [collection.name for collection in collections.collections]

    if collection_name not in collection_names:
        logger.info(f"正在创建表情包向量数据库集合: {collection_name}")
        # 创建集合
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=emotion_config.EMBEDDING_DIMENSION,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        logger.success(f"表情包向量数据库集合 {collection_name} 创建成功")


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
    def create(
        cls,
        description: str,
        tags: List[str],
        source_path: str,
        file_path: str,
    ):
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
        max_count = emotion_config.MAX_RECENT_EMOTION_COUNT
        self.recent_emotion_ids = self.recent_emotion_ids[:max_count]

    def get_emotion(self, emotion_id: str) -> Optional[EmotionMetadata]:
        """获取表情包元数据"""
        return self.emotions.get(emotion_id)

    def get_recent_emotions(
        self,
        count: Optional[int] = None,
    ) -> List[Tuple[str, EmotionMetadata]]:
        """获取最近添加的表情包"""
        if count is None:
            count = emotion_config.MAX_RECENT_EMOTION_COUNT
        result = []
        for emotion_id in self.recent_emotion_ids[:count]:
            if emotion_id in self.emotions:
                result.append((emotion_id, self.emotions[emotion_id]))
        return result


# endregion: 表情包系统数据模型


# region: 表情包工具方法


def resolve_emotion_file_path(file_path: str) -> Path:
    """解析表情包文件路径，支持向后兼容

    如果传入的是绝对路径且文件不存在，会尝试从插件数据目录中查找同名文件。
    新数据统一使用相对路径（仅文件名）。

    Args:
        file_path (str): 文件路径（可能是绝对路径或相对路径）

    Returns:
        Path: 解析后的绝对路径
    """
    path_obj = Path(file_path)

    # 如果是绝对路径
    if path_obj.is_absolute():
        # 如果文件存在，直接返回
        if path_obj.exists():
            return path_obj

        # 文件不存在，尝试从插件数据目录中查找同名文件（兼容性修复）
        file_name = path_obj.name
        fallback_path = store_dir / file_name

        if fallback_path.exists():
            logger.info(f"检测到旧的绝对路径不存在，已适配到新路径: {file_name}")
            return fallback_path

        # 两者都不存在，返回原路径（让调用方处理错误）
        return path_obj

    # 相对路径，拼接到插件数据目录
    return store_dir / file_path


async def load_emotion_store() -> EmotionStore:
    """加载表情包存储"""
    data = await store.get(store_key="emotion_store")
    return EmotionStore.model_validate(json.loads(data)) if data else EmotionStore()


async def save_emotion_store(emotion_store: EmotionStore):
    """保存表情包存储"""
    await store.set(
        store_key="emotion_store",
        value=json.dumps(emotion_store.model_dump(), ensure_ascii=False),
    )


async def migrate_emotion_paths():
    """迁移旧的绝对路径到新的相对路径格式

    这个函数会检查所有表情包的路径，将绝对路径转换为相对路径。
    适用于数据迁移场景。
    """
    emotion_store = await load_emotion_store()
    migrated_count = 0
    skipped_count = 0

    for emotion_id, metadata in emotion_store.emotions.items():
        file_path = Path(metadata.file_path)

        # 如果是绝对路径，尝试转换为相对路径
        if file_path.is_absolute():
            # 提取文件名
            file_name = file_path.name
            new_path = store_dir / file_name

            # 检查文件是否在新目录中存在（按文件名查找）
            if new_path.exists():
                # 文件在新目录中存在，直接使用文件名作为相对路径
                metadata.file_path = file_name
                migrated_count += 1
                logger.info(f"迁移表情包路径: {emotion_id} -> {file_name}")
            else:
                # 文件不存在，跳过但记录（这些文件可能真的丢失了）
                skipped_count += 1
                logger.warning(
                    f"表情包文件不存在，跳过迁移: {emotion_id} -> {file_name}",
                )

    if migrated_count > 0:
        await save_emotion_store(emotion_store)
        logger.success(
            f"成功迁移 {migrated_count} 个表情包路径到新格式，跳过 {skipped_count} 个文件不存在的表情包",
        )
    else:
        if skipped_count > 0:
            logger.warning(
                f"没有需要迁移的表情包路径，但有 {skipped_count} 个文件不存在",
            )
        else:
            logger.info("没有需要迁移的表情包路径")

    return migrated_count


async def generate_embedding(text: str, max_retries: int = 3) -> List[float]:
    """生成文本嵌入向量（带重试机制）

    Args:
        text: 要生成嵌入向量的文本
        max_retries: 最大重试次数，默认3次

    Returns:
        List[float]: 嵌入向量

    Raises:
        ValueError: 向量维度不匹配
        Exception: 重试次数耗尽后仍然失败
    """
    model_group: ModelConfigGroup = core_config.get_model_group_info(
        emotion_config.EMBEDDING_MODEL,
    )

    last_exception = None

    def _validate_dimension(vector: List[float]) -> None:
        """验证向量维度"""
        vector_dimension = len(vector)
        if vector_dimension != emotion_config.EMBEDDING_DIMENSION:
            error_msg = (
                f"嵌入向量维度错误！预期为 {emotion_config.EMBEDDING_DIMENSION} 维，"
                f"但实际获取到 {vector_dimension} 维。"
                f"请更新配置中的 EMBEDDING_DIMENSION 值为 {vector_dimension} 。"
            )
            logger.error(
                f"嵌入向量维度不匹配！预期: {emotion_config.EMBEDDING_DIMENSION}, 实际: {vector_dimension}",
            )
            raise ValueError(error_msg)

    for attempt in range(max_retries):
        try:
            embedding_vector = await gen_openai_embeddings(
                model=model_group.CHAT_MODEL,
                input=text,
                dimensions=emotion_config.EMBEDDING_DIMENSION,
                api_key=model_group.API_KEY,
                base_url=model_group.BASE_URL,
                timeout=emotion_config.EMBEDDING_REQUEST_TIMEOUT,
            )

            logger.debug(
                f"生成嵌入向量: {text[:10]}... 向量维度: {len(embedding_vector)}",
            )

            # 验证维度是否一致
            _validate_dimension(embedding_vector)

        except ValueError:
            # 维度错误不需要重试，直接抛出
            raise
        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.TimeoutException) as e:
            # 超时异常，提供更详细的错误信息
            last_exception = e
            timeout_seconds = emotion_config.EMBEDDING_REQUEST_TIMEOUT
            error_msg = f"请求超时（超时时间: {timeout_seconds}秒）"
            if attempt < max_retries - 1:
                # 指数退避：1秒、2秒、4秒
                wait_time = 2**attempt
                logger.warning(
                    f"生成嵌入向量超时 (尝试 {attempt + 1}/{max_retries}): {error_msg}，{wait_time}秒后重试...",
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"生成嵌入向量超时，已达最大重试次数 ({max_retries}): {error_msg}",
                )
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                # 指数退避：1秒、2秒、4秒
                wait_time = 2**attempt
                logger.warning(
                    f"生成嵌入向量失败 (尝试 {attempt + 1}/{max_retries}): {e}，{wait_time}秒后重试...",
                )
                await asyncio.sleep(wait_time)
            else:
                logger.exception(
                    f"生成嵌入向量失败，已达最大重试次数 ({max_retries}): {e}",
                )
        else:
            # 成功生成并验证通过，返回结果
            return embedding_vector

    # 所有重试都失败
    timeout_seconds = emotion_config.EMBEDDING_REQUEST_TIMEOUT
    if isinstance(
        last_exception,
        (httpx.ReadTimeout, httpx.WriteTimeout, httpx.TimeoutException),
    ):
        error_msg = (
            f"生成嵌入向量失败，已重试 {max_retries} 次。"
            f"请求超时（超时时间: {timeout_seconds}秒）。"
            f"请检查网络连接或增加配置中的 EMBEDDING_REQUEST_TIMEOUT 值。"
        )
    else:
        error_msg = f"生成嵌入向量失败，已重试 {max_retries} 次: {last_exception}"
    raise Exception(error_msg) from last_exception


async def download_image(url: str, save_path: Path) -> bool:
    """下载图片到指定路径

    Args:
        url: 图片 URL
        save_path: 保存路径

    Returns:
        是否下载成功
    """
    try:
        timeout = httpx.Timeout(emotion_config.IMAGE_DOWNLOAD_TIMEOUT)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(save_path, "wb") as f:
                await f.write(response.content)
            logger.info(f"成功下载图片: {url} -> {save_path}")
            return True
    except httpx.TimeoutException:
        logger.error(f"下载图片超时 ({emotion_config.IMAGE_DOWNLOAD_TIMEOUT}秒): {url}")
        return False
    except Exception as e:
        logger.error(f"下载图片失败: {url}, 错误: {e}")
        return False


async def save_image(
    source_path: str,
    file_name: str,
    _ctx: schemas.AgentCtx,
) -> Tuple[bool, str]:
    """保存图片到表情包存储目录

    Args:
        source_path (str): 源图片路径或URL
        file_name (str): 目标文件名
        _ctx (schemas.AgentCtx): 上下文

    Returns:
        Tuple[bool, str]: (是否成功, 相对路径文件名)
    """
    target_path = store_dir / file_name

    # 如果是URL，则下载图片
    if source_path.startswith(("http://", "https://")):
        logger.info(f"从URL下载图片: {source_path} 到 {target_path}")
        success = await download_image(source_path, target_path)
        return success, file_name  # 返回相对路径（文件名）

    # 如果是本地路径，则复制图片
    try:
        source_path_obj = convert_to_host_path(Path(source_path), _ctx.chat_key)
        logger.info(f"从本地路径复制图片: {source_path_obj} 到 {target_path}")

        if not source_path_obj.exists():
            logger.error(f"图片不存在: {source_path}")
            return False, file_name  # 返回相对路径（文件名）

        async with aiofiles.open(source_path_obj, "rb") as src_file:
            content = await src_file.read()

        async with aiofiles.open(target_path, "wb") as target_file:
            await target_file.write(content)

    except Exception as e:
        logger.error(f"保存图片失败: {source_path}, 错误: {e}")
        return False, file_name  # 返回相对路径（文件名）
    else:
        return True, file_name  # 返回相对路径（文件名）


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
        existing_path = resolve_emotion_file_path(metadata.file_path)
        if existing_path.exists():
            existing_hash = calculate_file_hash(existing_path)
            if existing_hash == target_hash:
                logger.info(f"发现重复表情包：{emotion_id}，哈希值：{target_hash}")
                return emotion_id

    return None


# endregion: 表情包工具方法


# region: 表情包命令
@plugin.mount_command(
    name="emo_search",
    description="语义搜索表情包",
    aliases=["emo-search"],
    usage="emo_search <关键词>",
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_search_cmd(
    context: CommandExecutionContext,
    keyword: Annotated[str, Arg("搜索关键词", positional=True, greedy=True)] = "",
) -> CommandResponse:
    if not keyword:
        return CmdCtl.failed("请输入要搜索的关键词")

    # 生成查询向量
    try:
        query_embedding = await generate_embedding(keyword)
    except Exception as e:
        logger.exception(f"生成查询向量失败: {e}")
        return CmdCtl.failed(f"生成查询向量失败: {e!s}")

    # 获取Qdrant客户端
    client = await get_qdrant_client()

    # 进行向量搜索
    try:
        search_results = await client.search(
            collection_name=plugin.get_vector_collection_name(),
            query_vector=query_embedding,
            limit=emotion_config.MAX_SEARCH_RESULTS,
            with_payload=True,
        )
    except Exception as e:
        logger.error(f"向量搜索失败: {e}")
        return CmdCtl.failed(f"搜索失败: {e!s}")

    if not search_results:
        return CmdCtl.failed(f"没有找到和「{keyword}」相关的表情包")

    # 加载表情包存储
    emotion_store = await load_emotion_store()

    # 构建文本结果
    result_lines = [f"和「{keyword}」相关的表情包："]
    found_count = 0

    for i, result in enumerate(search_results, 1):
        emotion_id = result.payload.get("emotion_id") if result.payload else None
        if not emotion_id:
            emotion_id = format(result.id, "x")

        metadata = emotion_store.get_emotion(emotion_id)
        if not metadata:
            continue

        file_path = resolve_emotion_file_path(metadata.file_path)
        if not file_path.exists():
            logger.warning(f"表情包文件不存在: {emotion_id}, {file_path}")
            continue

        tags_str = "、".join(metadata.tags) if metadata.tags else "暂无标签"
        result_lines.append(f"\n{i}. ID: {emotion_id}\n   描述: {metadata.description}\n   标签: {tags_str}")
        found_count += 1

    if not found_count:
        return CmdCtl.failed(f"没有找到和「{keyword}」相关的可用表情包")

    return CmdCtl.success("\n".join(result_lines))


@plugin.mount_command(
    name="emo_stats",
    description="查看表情包统计信息",
    aliases=["emo-stats"],
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_stats_cmd(context: CommandExecutionContext) -> CommandResponse:
    try:
        emotion_store = await load_emotion_store()
        client = await get_qdrant_client()
        collection_info = await client.get_collection(
            plugin.get_vector_collection_name(),
        )

        total_count = len(emotion_store.emotions)
        vector_count = collection_info.vectors_count if collection_info else 0
        all_tags: set[str] = set()
        for metadata in emotion_store.emotions.values():
            all_tags.update(metadata.tags)

        sorted_tags = sorted(all_tags)[:32]
        tags_str = "、".join(sorted_tags) if sorted_tags else "暂无标签"

        return CmdCtl.success(
            f"当前表情包统计信息：\n总数量：{total_count} 个\n向量数量：{vector_count} 个\n标签集合（top 32）：{tags_str}"
        )
    except Exception as e:
        logger.error(f"统计表情包失败: {e}")
        return CmdCtl.failed(f"统计失败: {e!s}")


@plugin.mount_command(
    name="emo_list",
    description="分页列出所有表情包",
    aliases=["emo-list", "emo_ls", "emo-ls"],
    usage="emo_list [页码]",
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_list_cmd(
    context: CommandExecutionContext,
    page: Annotated[int, Arg("页码", positional=True)] = 1,
) -> CommandResponse:
    emotion_store = await load_emotion_store()

    page = max(1, page)
    page_size = 10
    total_count = len(emotion_store.emotions)
    total_pages = (total_count + page_size - 1) // page_size

    if page > total_pages:
        return CmdCtl.failed(f"当前只有 {total_pages} 页，请输入有效的页码")

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_count)

    lines = [f"第 {page}/{total_pages} 页的表情包列表：\n"]

    sorted_emotions = sorted(
        emotion_store.emotions.items(),
        key=lambda x: x[1].added_time,
        reverse=True,
    )[start_idx:end_idx]

    for emotion_id, metadata in sorted_emotions:
        tags_str = "、".join(metadata.tags[:3]) + ("..." if len(metadata.tags) > 3 else "")
        lines.append(f"ID: {emotion_id}\n描述: {metadata.description[:30]}...\n标签: {tags_str}\n")

    lines.append("使用 emo_list <页码> 查看其他页面")

    return CmdCtl.success("\n".join(lines))


@plugin.mount_command(
    name="emo_migrate",
    description="迁移表情包路径到新格式",
    aliases=["emo-migrate"],
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_migrate_cmd(context: CommandExecutionContext) -> CommandResponse:
    migrated_count = await migrate_emotion_paths()
    return CmdCtl.success(f"路径迁移完成！成功迁移 {migrated_count} 个表情包路径")


@plugin.mount_command(
    name="emo_reindex",
    description="重建表情包索引",
    aliases=["emo-reindex"],
    usage="emo_reindex -y",
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_reindex_cmd(
    context: CommandExecutionContext,
    args_str: Annotated[str, Arg("参数", positional=True, greedy=True)] = "",
) -> AsyncIterator[CommandResponse]:
    if "-y" not in args_str:
        yield CmdCtl.failed("请输入 -y 确认重建表情包索引")
        return

    emotion_store = await load_emotion_store()
    total_emotions = len(emotion_store.emotions)

    if total_emotions == 0:
        yield CmdCtl.success("当前没有任何表情包需要重建索引")
        return

    yield CmdCtl.message(f"开始重建 {total_emotions} 个表情包的索引，这可能需要一些时间...")

    client = await get_qdrant_client()
    if client is None:
        yield CmdCtl.failed("无法连接到向量数据库，重建索引失败")
        return

    collection_name = plugin.get_vector_collection_name()

    try:
        collections = await client.get_collections()
        collection_names = [collection.name for collection in collections.collections]

        if collection_name in collection_names:
            await client.delete_collection(collection_name=collection_name)
            logger.info(f"已删除现有集合: {collection_name}")

        await client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=emotion_config.EMBEDDING_DIMENSION,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        logger.info(f"已创建新集合: {collection_name}")

    except Exception as e:
        logger.error(f"重置向量集合失败: {e}")
        yield CmdCtl.failed(f"重置向量集合失败: {e!s}")
        return

    success_count = 0
    error_count = 0
    missing_file_count = 0
    batch_size = 50
    current_batch: list[qdrant_models.PointStruct] = []
    last_progress_time = time.time()
    progress_interval = 60

    for emotion_id, metadata in emotion_store.emotions.items():
        try:
            file_path = resolve_emotion_file_path(metadata.file_path)
            if not file_path.exists():
                logger.warning(f"表情包文件不存在: {emotion_id}, {file_path}")
                missing_file_count += 1
                continue

            embedding_text = f"{metadata.description} {' '.join(metadata.tags)}"
            embedding = await generate_embedding(embedding_text)

            current_batch.append(
                qdrant_models.PointStruct(
                    id=int(emotion_id, 16),
                    vector=embedding,
                    payload={
                        "description": metadata.description,
                        "tags": metadata.tags,
                        "emotion_id": emotion_id,
                    },
                ),
            )

            if (
                len(current_batch) >= batch_size
                or emotion_id == list(emotion_store.emotions.keys())[-1]
            ):
                await client.upsert(
                    collection_name=collection_name,
                    points=current_batch,
                )
                current_batch = []

            success_count += 1

            current_time = time.time()
            if current_time - last_progress_time >= progress_interval:
                yield CmdCtl.message(f"已成功处理 {success_count}/{total_emotions} 个表情包...")
                last_progress_time = current_time

            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"处理表情包失败: {emotion_id}, 错误: {e}")
            error_count += 1

    result = f"表情包索引重建完成！\n总计: {total_emotions} 个\n成功: {success_count} 个\n失败: {error_count} 个\n文件缺失: {missing_file_count} 个"

    if error_count > 0:
        result += "\n有一些表情包处理失败了，请查看日志获取详细信息"

    yield CmdCtl.success(result)


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
        tags_str = ", ".join(metadata.tags[:3]) + (
            "..." if len(metadata.tags) > 3 else ""
        )
        prompt_parts.append(
            f"{idx}. ID: {emotion_id} - {metadata.description[:30]}... [Tags: {tags_str}]",
        )

    addition_prompt = "Attention: Emotion Plugin is a isolated self-managed plugin, you should not record the emotion ID manually by using other plugins. Just use the `collect_emotion` tool to collect the emotion and use `search_emotion` to search the emotion if you need."

    return "\n".join(prompt_parts) + "\n" + addition_prompt


# endregion: 表情包提示注入

# region: 表情包沙盒方法


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="收集表情包",
    description="收集表情包并进行特征打标，保存到向量数据库",
)
async def collect_emotion(
    _ctx: schemas.AgentCtx,
    source_path: str,
    description: str,
    tags: List[str],
    vision_and_emotion_confirmed: bool,
) -> str:
    """Collect Emotion (表情包)

    Collect an expression image/GIF to the emotion database.
    **IMPORTANT:** Only collect actual expression images or reaction GIFs, **DO NOT COLLECT ANY screenshots, photos, or other images!** You can only collect the images you are sure about (visible in vision content). Do not collect anything send by yourself!

    Args:
        source_path (str): The path or URL of the expression image
        description (str): A detailed description of the emotion/expression (used for searching. You Must fill it in carefully)
        tags (List[str]): Tags for the emotion (e.g. ["happy", "excited", "anime"])
        vision_and_emotion_confirmed (bool): Whether the image content is confirmed by vision (default: False, You Can Only Collect Images That Are Visible in Vision Content and NEVER Guess the content!)

    Returns:
        str: The emotion ID

    Example:
        ```python
        # Collect from URL
        emotion_id = collect_emotion("https://example.com/happy_cat.gif", "一只开心的猫跳来跳去", ["开心", "猫", "可爱", "Q版"], vision_and_emotion_confirmed=True)

        # Collect from local path
        emotion_id = collect_emotion("/app/uploads/surprised_anime_girl.png", "蓝色头发的动漫女孩一脸惊讶", ["动漫", "惊讶", "反应"], vision_and_emotion_confirmed=True) # Do not send the emotion ID in your message directly!

        # DO NOT COLLECT ANY screenshots, photos, or other images!
        emotion_id = collect_emotion("/app/uploads/user_screenshot.png", "用户截图", ["截图", "用户", "游戏"], vision_and_emotion_confirmed=False)  # Rejected.
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

    if not vision_and_emotion_confirmed:
        await message_service.push_system_message(
            _ctx.chat_key,
            "Image content is not confirmed by vision or it is a screenshot! You CANT COLLECT ANY screenshots, photos, or other images! Rejected.",
        )
        return ""

    # 确保表情包目录存在
    store_dir.mkdir(parents=True, exist_ok=True)

    # 文件名处理
    if source_path.startswith(("http://", "https://")):
        # 从URL中提取文件名
        path_obj = Path(source_path.split("?")[0])
        file_name = path_obj.name
        # 确保文件名有扩展名
        if not any(
            file_name.lower().endswith(ext)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        ):
            file_name = f"{hashlib.md5(source_path.encode()).hexdigest()[:8]}.png"
    else:
        # 本地文件，直接使用原文件名
        file_name = convert_to_host_path(Path(source_path), _ctx.chat_key).name

    # 添加随机字符串避免文件名冲突
    path_obj = Path(file_name)
    file_name = f"{path_obj.stem}_{hashlib.md5(description.encode()).hexdigest()[:6]}{path_obj.suffix}"

    # 保存图片（返回相对路径文件名）
    success, relative_file_path = await save_image(source_path, file_name, _ctx)
    if not success:
        raise ValueError(f"Error: Failed to save image from {source_path}")

    # 检查是否有重复图片
    absolute_file_path = resolve_emotion_file_path(relative_file_path)
    duplicate_id = await find_duplicate_emotion(absolute_file_path)

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

            # 生成嵌入向量
            embedding = await generate_embedding(f"{description} {' '.join(tags)}")

            # 获取Qdrant客户端
            client = await get_qdrant_client()

            # 更新Qdrant向量数据库中的向量
            try:
                # 先删除旧点
                await client.delete(
                    collection_name=plugin.get_vector_collection_name(),
                    points_selector=qdrant_models.PointIdsList(
                        points=[int(duplicate_id, 16)],
                    ),
                )
                logger.info(f"已删除Qdrant中的旧点: {duplicate_id}")
            except Exception as e:
                logger.warning(f"删除Qdrant中的旧点失败，可能不存在: {e}")

            # 添加新点
            await client.upsert(
                collection_name=plugin.get_vector_collection_name(),
                points=[
                    qdrant_models.PointStruct(
                        id=int(duplicate_id, 16),  # 将十六进制字符串转换为整数
                        vector=embedding,
                        payload={
                            "description": description,
                            "tags": tags,
                            "emotion_id": duplicate_id,  # 保存原始ID以便后续检索
                        },
                    ),
                ],
            )
            logger.info(f"已添加新向量到Qdrant: {duplicate_id}")

            await save_emotion_store(emotion_store)
            return duplicate_id

    # 生成唯一ID
    emotion_id = generate_emotion_id(relative_file_path, description)

    # 创建元数据（使用相对路径）
    metadata = EmotionMetadata.create(
        description=description,
        tags=tags,
        source_path=source_path,
        file_path=relative_file_path,  # 保存相对路径
    )

    # 添加到存储
    emotion_store.add_emotion(emotion_id, metadata)
    await save_emotion_store(emotion_store)

    # 添加到向量数据库
    try:
        # 生成嵌入向量
        embedding = await generate_embedding(f"{description} {' '.join(tags)}")

        # 获取Qdrant客户端
        client = await get_qdrant_client()

        # 添加到Qdrant向量数据库
        await client.upsert(
            collection_name=plugin.get_vector_collection_name(),
            points=[
                qdrant_models.PointStruct(
                    id=int(emotion_id, 16),  # 将十六进制字符串转换为整数
                    vector=embedding,
                    payload={
                        "description": description,
                        "tags": tags,
                        "emotion_id": emotion_id,  # 保存原始ID以便后续检索
                    },
                ),
            ],
        )
        logger.info(f"已添加表情包描述新向量到Qdrant: {emotion_id}")
    except Exception as e:
        raise ValueError(f"添加到向量数据库失败: {e}") from e
    await message_service.push_system_message(
        _ctx.chat_key,
        f"Successfully collected emotion: {emotion_id} - {description} {' '.join(tags)} ({source_path=})",
    )

    return emotion_id


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="更新表情包",
    description="更新表情包的描述和标签",
)
async def update_emotion(
    _ctx: schemas.AgentCtx,
    emotion_id: str,
    description: str,
    tags: List[str],
) -> str:
    """Update Emotion (更新表情包)

    Update the metadata of an existing emotion.

    Args:
        emotion_id (str): The ID of the emotion to update
        description (str): New description for the emotion
        tags (List[str]): New tags for the emotion

    Returns:
        str: The emotion ID of the updated emotion

    Example:
        ```python
        # Update emotion metadata
        updated_id = update_emotion("a1b2c3d4", description="一只超可爱的猫猫", tags=["可爱", "猫咪", "萌"])
        ```
    """
    # 参数验证
    if not emotion_id:
        raise ValueError("Error: Emotion ID cannot be empty!")

    if not isinstance(tags, list):
        raise TypeError("Error: Tags must be a list!")

    # 加载表情包存储
    emotion_store = await load_emotion_store()

    # 检查表情包是否存在
    metadata = emotion_store.get_emotion(emotion_id)
    if not metadata:
        raise ValueError(f"Error: Emotion with ID '{emotion_id}' not found")

    # 更新描述和标签
    metadata.description = description
    metadata.tags = tags
    metadata.last_updated = int(time.time())

    # 保存更新后的表情包存储
    emotion_store.add_emotion(emotion_id, metadata)
    await save_emotion_store(emotion_store)

    # 更新向量数据库
    # 生成嵌入向量
    embedding_text = f"{description} {' '.join(tags)}"
    embedding = await generate_embedding(embedding_text)

    # 获取Qdrant客户端
    client = await get_qdrant_client()

    # 更新Qdrant向量数据库中的向量
    try:
        # 先删除旧点
        await client.delete(
            collection_name=plugin.get_vector_collection_name(),
            points_selector=qdrant_models.PointIdsList(
                points=[int(emotion_id, 16)],
            ),
        )
        logger.info(f"已删除Qdrant中的旧点: {emotion_id}")
    except Exception as e:
        logger.warning(f"删除Qdrant中的旧点失败，可能不存在: {e}")

    # 添加新点
    await client.upsert(
        collection_name=plugin.get_vector_collection_name(),
        points=[
            qdrant_models.PointStruct(
                id=int(emotion_id, 16),  # 将十六进制字符串转换为整数
                vector=embedding,
                payload={
                    "description": description,
                    "tags": tags,
                    "emotion_id": emotion_id,  # 保存原始ID以便后续检索
                },
            ),
        ],
    )
    logger.info(f"已添加新向量到Qdrant: {emotion_id}")

    await message_service.push_system_message(
        _ctx.chat_key,
        f"Successfully updated emotion metadata: {emotion_id}",
    )

    return emotion_id


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="删除表情包",
    description="删除表情包，并从向量数据库中移除",
)
async def remove_emotion(_ctx: schemas.AgentCtx, emotion_id: str) -> str:
    """Remove Emotion (删除表情包)

    Remove an emotion from the database by its ID.

    Args:
        emotion_id (str): The ID of the emotion to be deleted

    Returns:
        str: A message indicating the success or failure of the operation

    Example:
        ```python
        # Remove an emotion
        result = remove_emotion("a1b2c3d4")
        ```
    """
    # 参数验证
    if not emotion_id:
        raise ValueError("Error: Emotion ID cannot be empty!")

    # 加载表情包存储
    emotion_store = await load_emotion_store()

    # 检查表情包是否存在
    metadata = emotion_store.get_emotion(emotion_id)
    if not metadata:
        raise ValueError(f"Error: Emotion with ID '{emotion_id}' not found")

    # 获取文件路径
    file_path = resolve_emotion_file_path(metadata.file_path)

    # 从表情包存储中删除
    if emotion_id in emotion_store.emotions:
        del emotion_store.emotions[emotion_id]

    # 从最近表情包列表中删除
    if emotion_id in emotion_store.recent_emotion_ids:
        emotion_store.recent_emotion_ids.remove(emotion_id)

    # 保存更新后的表情包存储
    await save_emotion_store(emotion_store)

    # 从向量数据库中删除
    try:
        # 获取Qdrant客户端
        client = await get_qdrant_client()

        # 从Qdrant删除点
        await client.delete(
            collection_name=plugin.get_vector_collection_name(),
            points_selector=qdrant_models.PointIdsList(
                points=[int(emotion_id, 16)],
            ),
        )
        logger.info(f"已从Qdrant中删除表情包: {emotion_id}")
    except Exception as e:
        logger.warning(f"从Qdrant删除表情包失败，可能不存在: {e}")

    # 尝试删除文件
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"已删除表情包文件: {file_path}")
    except Exception as e:
        logger.warning(f"删除表情包文件失败: {e}")

    await message_service.push_system_message(
        _ctx.chat_key,
        f"Successfully removed emotion: {emotion_id}",
    )

    return f"表情包 {emotion_id} 已成功删除"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="获取表情包路径",
    description="获取表情包文件路径",
)
async def get_emotion_path(_ctx: schemas.AgentCtx, emotion_id: str) -> str:
    """Get Emotion Path

    Get the path of an emotion by its ID.

    Args:
        emotion_id (str): The emotion ID (**NOT PATH**)

    Returns:
        str: The path of the emotion file

    Example:
        ```python
        # Get emotion path and use it in another function
        emotion_file_path = get_emotion_path("a1b2c3d4")
        # Send it or do something ... But DO NOT do any addition record for this emotion file!
        ```
    """
    # 加载表情包存储
    emotion_store = await load_emotion_store()

    # 获取表情包元数据
    metadata = emotion_store.get_emotion(emotion_id)
    if not metadata:
        raise ValueError(f"Error: Emotion with ID '{emotion_id}' not found")

    # 获取文件路径
    file_path = resolve_emotion_file_path(metadata.file_path)
    if not file_path.exists():
        raise ValueError(f"Error: Emotion file not found: {file_path}")

    # 读取文件内容
    try:
        emo_file_path, _ = await copy_to_upload_dir(
            str(file_path),  # 使用解析后的绝对路径
            file_path.name,
            from_chat_key=_ctx.chat_key,
        )

    except Exception as e:
        raise ValueError(f"Error reading emotion file: {e}") from e
    else:
        return str(convert_filename_to_sandbox_upload_path(Path(emo_file_path)))


@plugin.mount_sandbox_method(
    SandboxMethodType.MULTIMODAL_AGENT,
    name="搜索表情包",
    description="根据文本描述搜索表情包",
)
async def search_emotion(
    _ctx: schemas.AgentCtx,
    query: str,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """Search Emotion

    Search for emotions using a text query and display the results.

    Args:
        query (str): The search query
        max_results (int, optional): Maximum number of results to observe (recommended: 3-5)

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
    search_limit = emotion_config.MAX_SEARCH_RESULTS
    if max_results is not None:
        search_limit = max_results

    # 生成查询向量
    query_embedding = await generate_embedding(query)

    # 获取Qdrant客户端
    client = await get_qdrant_client()

    # 进行向量搜索
    try:
        search_results = await client.search(
            collection_name=plugin.get_vector_collection_name(),
            query_vector=query_embedding,
            limit=search_limit,
            with_payload=True,  # 确保返回payload以获取原始emotion_id
        )
    except Exception as e:
        logger.error(f"向量搜索失败: {e}")
        msg = OpenAIChatMessage.from_text(
            "user",
            f"Failed to search emotions: {e}. Please try again later or check your query.",
        )
        return msg.to_dict()

    # 检查是否有结果
    if not search_results:
        msg = OpenAIChatMessage.from_text(
            "user",
            f"No emotions found for query: '{query}'. Try another search term or collect more emotions.",
        )
        return msg.to_dict()

    # 加载表情包存储
    emotion_store = await load_emotion_store()

    # 构建多模态消息
    msg = OpenAIChatMessage.from_text(
        "user",
        f"Here are the emotions You have collected for '{query}':",
    )

    for i, result in enumerate(search_results):
        # 从payload中获取原始emotion_id
        emotion_id = result.payload.get("emotion_id") if result.payload else None
        if not emotion_id:
            # 向后兼容：如果没有emotion_id，尝试使用十六进制字符串
            emotion_id = format(result.id, "x")

        metadata = emotion_store.get_emotion(emotion_id)
        if not metadata:
            continue

        file_path = resolve_emotion_file_path(metadata.file_path)
        if not file_path.exists():
            continue

        # 准备标签字符串
        tags_str = ", ".join(metadata.tags) if metadata.tags else "No tags"

        # 添加表情包详细信息
        msg.batch_add(
            [
                ContentSegment.text_content(
                    f"\nEmotion {i + 1} (ID: {emotion_id}):\nDescription: {metadata.description}\nTags: {tags_str}",
                ),
                ContentSegment.image_content_from_path(str(file_path)),
            ],
        )
    msg.add(
        ContentSegment.text_content(
            "If the emotion doesn't match the description, please use `update_emotion` IMMEDIATELY to correct it. If you find any non-expression images (like screenshots, photos, or irrelevant content), please use `remove_emotion` IMMEDIATELY to delete them. Expression images should only be reaction GIFs or meme images. ALWAYS KEEP YOUR COLLECTIONS CLEAN AND ACCURATE. After that, continue to Your task.",
        ),
    )

    return msg.to_dict()


# endregion: 表情包沙盒方法


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
