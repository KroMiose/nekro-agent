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
- `emo_list [页码]`: 分页列出所有表情包，并默认预览图片。
- `emo_migrate`: 迁移旧的绝对路径到相对路径格式（适用于数据目录迁移后）。
- `emo_reindex -y`: 重建索引（高级功能，一般无需使用）。

## 配置说明

- **严格表情包模式**: 开启后，插件会尝试拒绝收藏截图、照片等非表情包内容的图片。
- **嵌入模型组**: 需要正确配置一个向量模型才能使用语义搜索功能。
"""

import asyncio
import hashlib
import json
import shutil
import time
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, AsyncIterator, Dict, List, Literal, Optional, Tuple

import aiofiles
import httpx
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
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
from nekro_agent.services.agent.openai import gen_openai_chat_response, gen_openai_embeddings
from nekro_agent.services.command.base import CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import (
    Arg,
    CommandExecutionContext,
    CommandOutputSegment,
    CommandOutputSegmentType,
    CommandResponse,
)
from nekro_agent.services.message_service import message_service
from nekro_agent.tools.common_util import copy_to_upload_dir
from nekro_agent.tools.path_convertor import (
    convert_filename_to_sandbox_upload_path,
    convert_to_host_path,
)

from .constants import DEFAULT_CATEGORY_DESCRIPTIONS
from .gallery import CategoryGalleryManager, is_supported_image_file, safe_category_name
from .image_host import ImageHostService

plugin = NekroPlugin(
    name="表情包插件",
    module_name="emotion",
    description="提供收集、搜索、使用表情包能力，使用Qdrant向量数据库",
    version="1.0.0",
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
    VISION_MODEL: str = Field(
        default="default",
        title="图库自动分类视觉模型组",
        description="用于 WebUI 自动化分类，为未分类或缺少描述的表情生成描述、标签和分类",
        json_schema_extra=ExtraField(
            ref_model_groups=True,
            required=False,
            model_type="chat",
            i18n_title=i18n.i18n_text(
                zh_CN="图库自动分类视觉模型组",
                en_US="Gallery Auto Classification Vision Model Group",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="用于 WebUI 自动化分类，为未分类或缺少描述的表情生成描述、标签和分类",
                en_US="Used by WebUI auto classification to generate descriptions, tags and categories for gallery emotions",
            ),
        ).model_dump(),
    )
    AUTO_CLASSIFY_BATCH_LIMIT: int = Field(
        default=5,
        title="自动化分类单次处理数量",
        description="WebUI 每次自动化分类最多处理的图片数量，避免一次调用过多视觉模型请求",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="自动化分类单次处理数量",
                en_US="Auto Classification Batch Limit",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="WebUI 每次自动化分类最多处理的图片数量，避免一次调用过多视觉模型请求",
                en_US="Maximum images processed per WebUI auto classification run to avoid too many vision model requests",
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
    ALLOW_AI_COLLECT_EMOTION: bool = Field(
        default=True,
        title="允许 AI 自行收藏表情",
        description="关闭后 AI 无法通过 collect_emotion 收集新表情，只能搜索、浏览和使用已有图库表情",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="允许 AI 自行收藏表情",
                en_US="Allow AI Emotion Collection",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="关闭后 AI 无法通过 collect_emotion 收集新表情，只能搜索、浏览和使用已有图库表情",
                en_US="When disabled, AI cannot collect new emotions via collect_emotion and can only use existing gallery emotions",
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
    ENABLE_LOOSE_MATCH: bool = Field(
        default=True,
        title="宽松匹配模式",
        description="搜索结果不足或低于阈值时，允许使用描述、标签、分类的关键词命中作为补充结果",
    )
    ENABLE_FALLBACK_TAG_MATCH: bool = Field(
        default=True,
        title="备用标记匹配",
        description="向量搜索无结果时，使用标签和分类标记进行备用匹配",
    )
    ENABLE_DUPLICATE_EMOTION_DETECTION: bool = Field(
        default=True,
        title="重复表情检测",
        description="收集表情包时通过文件哈希检测重复表情，命中后更新已有元数据而不是新增记录",
    )
    SIMILARITY_THRESHOLD: float = Field(
        default=0.45,
        title="向量相似度阈值",
        description="向量搜索结果低于该相似度时不作为直接命中，仅由宽松匹配或备用标记匹配补充",
    )
    HIGH_CONFIDENCE_THRESHOLD: float = Field(
        default=0.78,
        title="高置信度表情阈值",
        description="搜索结果达到该相似度时标记为高置信度，优先提示 Agent 使用",
    )
    LOOSE_MATCH_MIN_SCORE: float = Field(
        default=0.34,
        title="宽松匹配最低分",
        description="宽松文本匹配结果的最低分数，分数越低结果越宽泛",
    )
    ENABLE_CATEGORY_GALLERY: bool = Field(
        default=True,
        title="启用分类管理",
        description="启用 WebUI 分类、类别描述和表情分类元数据管理；图片仍统一保存在 emotions 根目录，不会按分类创建文件夹",
    )
    DEFAULT_CATEGORY_DESCRIPTIONS: Dict[str, str] = Field(
        default_factory=lambda: DEFAULT_CATEGORY_DESCRIPTIONS.copy(),
        title="图库类别描述",
        description="用于初始化或同步 WebUI 分类列表的类别描述；不会创建分类文件夹，图片分类由元数据记录",
        json_schema_extra=ExtraField(
            textarea=True,
            rows=25,
            i18n_title=i18n.i18n_text(
                zh_CN="图库类别描述",
                en_US="Gallery Category Descriptions",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="用于初始化或同步 WebUI 分类列表的类别描述；不会创建分类文件夹，图片分类由元数据记录",
                en_US="Category descriptions for initializing or syncing WebUI category list; will not create folders",
            ),
        ).model_dump(),
    )
    IMAGE_HOST_PROVIDER: Literal["disabled", "stardots", "cloudflare_r2"] = Field(
        default="disabled",
        title="图床提供商",
        description="分类图库同步使用的图床提供商：不使用、stardots 或 cloudflare_r2",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="图床提供商",
                en_US="Image Host Provider",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="分类图库同步使用的图床提供商：不使用、stardots 或 cloudflare_r2",
                en_US="Image host provider for syncing gallery: disabled, stardots, or cloudflare_r2",
            ),
        ).model_dump(),
    )
    STARDOTS_KEY: str = Field(default="", title="StarDots Key", description="StarDots 图床 Key")
    STARDOTS_SECRET: str = Field(default="", title="StarDots Secret", description="StarDots 图床 Secret")
    STARDOTS_SPACE: str = Field(default="", title="StarDots Space", description="StarDots 图床空间名")
    R2_ACCOUNT_ID: str = Field(default="", title="Cloudflare R2 Account ID", description="Cloudflare R2 账号 ID")
    R2_ACCESS_KEY_ID: str = Field(default="", title="Cloudflare R2 Access Key ID", description="Cloudflare R2 Access Key ID")
    R2_SECRET_ACCESS_KEY: str = Field(default="", title="Cloudflare R2 Secret Access Key", description="Cloudflare R2 Secret Access Key")
    R2_BUCKET_NAME: str = Field(default="", title="Cloudflare R2 Bucket", description="Cloudflare R2 存储桶名称")
    R2_PUBLIC_URL: str = Field(default="", title="Cloudflare R2 Public URL", description="可选，自定义 CDN/公开访问域名")
    WEB_MANAGER_ENABLE_UPLOAD: bool = Field(
        default=True,
        title="Web 管理允许上传",
        description="是否允许通过插件 Web 管理页面上传表情包到统一图库",
    )
    WEBUI_ACCESS_KEY: str = Field(
        default="",
        title="WebUI 访问密钥",
        description="设置后访问 WebUI 和 API 必须携带密钥；为空则不启用密钥保护",
    )



# 获取配置和插件存储
emotion_config: EmotionConfig = plugin.get_config(EmotionConfig)
store = plugin.store
store_dir = plugin.get_plugin_path() / "emotions"
gallery_dir = store_dir
gallery_data_path = plugin.get_plugin_path() / "emotions_data.json"
default_gallery_dir = Path(__file__).resolve().parent / "emotions"

store_dir.mkdir(parents=True, exist_ok=True)

gallery_manager = CategoryGalleryManager(
    gallery_dir=gallery_dir,
    gallery_data_path=gallery_data_path,
    default_gallery_dir=default_gallery_dir,
    config=emotion_config,
    calculate_file_hash=lambda file_path: calculate_file_hash(file_path),
    download_image=lambda url, save_path: download_image(url, save_path),
)
image_host_service = ImageHostService(emotion_config, gallery_dir)
plugin_web_base = f"/plugins/{plugin.key}"


@plugin.mount_init_method()
async def init_vector_db():
    """初始化表情包向量数据库"""
    init_category_gallery()
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
    category: Optional[str] = None

    @classmethod
    def create(
        cls,
        description: str,
        tags: List[str],
        source_path: str,
        file_path: str,
        category: Optional[str] = None,
    ):
        current_time = int(time.time())
        return cls(
            description=description,
            tags=tags,
            source_path=source_path,
            file_path=file_path,
            added_time=current_time,
            last_updated=current_time,
            category=category,
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


# region: 分类图库兼容包装


def _safe_category_name(category: str) -> str:
    return safe_category_name(category)


def _is_supported_image_file(path: Path) -> bool:
    return is_supported_image_file(path)


def load_category_descriptions() -> Dict[str, str]:
    return gallery_manager.load_descriptions()


def save_category_descriptions(descriptions: Dict[str, str]) -> None:
    gallery_manager.save_descriptions(descriptions)


def sync_category_descriptions_with_filesystem() -> Dict[str, str]:
    return gallery_manager.sync_descriptions_with_filesystem()


def sync_default_category_descriptions_to_filesystem() -> Dict[str, Any]:
    return gallery_manager.sync_default_descriptions_to_filesystem()


def init_category_gallery() -> None:
    gallery_manager.init_gallery()


async def get_category_image_paths(category: str) -> List[Path]:
    emotion_store = await load_emotion_store()
    safe_category = _safe_category_name(category)
    image_paths: List[Path] = []
    managed_files = set()
    for metadata in emotion_store.emotions.values():
        file_path = resolve_emotion_file_path(metadata.file_path)
        if not file_path.exists() or not _is_supported_image_file(file_path):
            continue
        managed_files.add(file_path.name)
        if get_emotion_storage_category(metadata.category) == safe_category:
            image_paths.append(file_path)
    if safe_category == "未分类" and store_dir.exists():
        for image_path in store_dir.iterdir():
            if _is_supported_image_file(image_path) and image_path.name not in managed_files:
                image_paths.append(image_path)
    return sorted(image_paths)


def get_category_stats_from_store(emotion_store: EmotionStore, descriptions: Dict[str, str]) -> Dict[str, int]:
    stats = {category: 0 for category in descriptions}
    metadata_files = set()
    for metadata in emotion_store.emotions.values():
        file_path = resolve_emotion_file_path(metadata.file_path)
        if not file_path.exists() or not _is_supported_image_file(file_path):
            continue
        category = get_emotion_storage_category(metadata.category)
        stats[category] = stats.get(category, 0) + 1
        metadata_files.add(file_path.name)
    if store_dir.exists():
        unmanaged_count = 0
        for image_path in store_dir.iterdir():
            if image_path.name == ".upload_tracker.json":
                continue
            if _is_supported_image_file(image_path) and image_path.name not in metadata_files:
                unmanaged_count += 1
        stats["未分类"] = stats.get("未分类", 0) + unmanaged_count
    return stats


def get_category_image_items_from_store(emotion_store: EmotionStore, category: str) -> List[Dict[str, Any]]:
    safe_category = _safe_category_name(category)
    metadata_by_filename: Dict[str, Tuple[str, EmotionMetadata]] = {}
    for emotion_id, metadata in emotion_store.emotions.items():
        file_path = resolve_emotion_file_path(metadata.file_path)
        if not file_path.exists() or not _is_supported_image_file(file_path):
            continue
        image_category = get_emotion_storage_category(metadata.category)
        if image_category != safe_category:
            continue
        metadata_by_filename[file_path.name] = (emotion_id, metadata)

    items: List[Dict[str, Any]] = []
    for filename, (emotion_id, metadata) in metadata_by_filename.items():
        file_path = resolve_emotion_file_path(metadata.file_path)
        items.append(
            {
                "filename": filename,
                "emotion_id": emotion_id,
                "category": get_emotion_storage_category(metadata.category),
                "description": metadata.description,
                "tags": metadata.tags,
                "managed": True,
                "url": f"{plugin_web_base}/emotions/{filename}",
                "size": file_path.stat().st_size,
            },
        )

    if safe_category == "未分类" and store_dir.exists():
        managed_filenames = set(metadata_by_filename.keys())
        all_metadata_filenames = {
            resolve_emotion_file_path(metadata.file_path).name
            for metadata in emotion_store.emotions.values()
            if resolve_emotion_file_path(metadata.file_path).exists()
        }
        for image_path in sorted(store_dir.iterdir()):
            if not _is_supported_image_file(image_path):
                continue
            if image_path.name in managed_filenames or image_path.name in all_metadata_filenames:
                continue
            items.append(
                {
                    "filename": image_path.name,
                    "emotion_id": "",
                    "category": "未分类",
                    "description": "",
                    "tags": [],
                    "managed": False,
                    "url": f"{plugin_web_base}/emotions/{image_path.name}",
                    "size": image_path.stat().st_size,
                },
            )

    items.sort(key=lambda item: item["filename"])
    return items


async def get_category_stats() -> Dict[str, int]:
    emotion_store = await load_emotion_store()
    descriptions = sync_category_descriptions_with_filesystem()
    return get_category_stats_from_store(emotion_store, descriptions)


def find_duplicate_gallery_image(category: str, file_path: Path) -> Optional[Path]:
    return gallery_manager.find_duplicate_image(category, file_path)


def copy_or_move_gallery_images(source_category: str, target_category: str, filenames: List[str], move: bool) -> Dict[str, Any]:
    return gallery_manager.copy_or_move_images(source_category, target_category, filenames, move)


async def save_upload_file_to_gallery(upload_file: UploadFile, category: str) -> Path:
    return await gallery_manager.save_upload_file(upload_file, category)


async def add_image_to_category_gallery(source_path: str, category: str, _ctx: schemas.AgentCtx) -> Path:
    return await gallery_manager.add_image(source_path, category, _ctx)


# endregion: 分类图库兼容包装

# region: 图床同步兼容包装


def get_image_host_overview() -> Dict[str, Any]:
    return image_host_service.get_overview()


async def run_image_sync_task(task: str) -> Dict[str, Any]:
    return await image_host_service.run_task(task)


def summarize_sync_result(result: Dict[str, Any]) -> str:
    return image_host_service.summarize_result(result)


# endregion: 图床同步兼容包装


# region: 表情包工具方法


def resolve_emotion_file_path(file_path: str) -> Path:
    """解析表情包文件路径

    新数据统一使用 emotions 根目录下的文件名作为相对路径，分类由元数据记录。

    Args:
        file_path (str): 文件路径（可能是绝对路径或相对路径）

    Returns:
        Path: 解析后的绝对路径
    """
    path_obj = Path(file_path)

    if path_obj.is_absolute():
        if path_obj.exists():
            return path_obj
        return store_dir / path_obj.name

    direct_path = store_dir / file_path
    if direct_path.exists():
        return direct_path

    file_name = PurePosixPath(file_path.replace("\\", "/")).name
    fallback_path = store_dir / file_name
    if fallback_path.exists():
        return fallback_path

    return direct_path


def get_emotion_storage_category(category: Optional[str]) -> str:
    normalized_category = _safe_category_name(category) if category else ""
    return normalized_category or "未分类"


def get_emotion_file_name(file_path: str) -> str:
    return PurePosixPath(str(file_path).replace("\\", "/")).name


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


async def upsert_emotion_vector(emotion_id: str, metadata: EmotionMetadata) -> None:
    embedding_text = f"{metadata.description} {' '.join(metadata.tags)}"
    embedding = await generate_embedding(embedding_text)
    client = await get_qdrant_client()
    if client is None:
        raise ValueError("无法获取 Qdrant 客户端")

    try:
        await client.delete(
            collection_name=plugin.get_vector_collection_name(),
            points_selector=qdrant_models.PointIdsList(points=[int(emotion_id, 16)]),
        )
    except Exception as e:
        logger.warning(f"删除Qdrant中的旧点失败，可能不存在: {e}")

    await client.upsert(
        collection_name=plugin.get_vector_collection_name(),
        points=[
            qdrant_models.PointStruct(
                id=int(emotion_id, 16),
                vector=embedding,
                payload={
                    "description": metadata.description,
                    "tags": metadata.tags,
                    "emotion_id": emotion_id,
                    "category": metadata.category,
                    "file_path": metadata.file_path,
                },
            ),
        ],
    )


def parse_vision_emotion_result(content: str) -> Dict[str, Any]:
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"description": content.strip(), "tags": [], "category": None}
    description = str(data.get("description") or content.strip()).strip()
    tags_value = data.get("tags", [])
    if isinstance(tags_value, str):
        tags = [tag.strip() for tag in tags_value.replace("，", ",").split(",") if tag.strip()]
    elif isinstance(tags_value, list):
        tags = [str(tag).strip() for tag in tags_value if str(tag).strip()]
    else:
        tags = []
    category = _safe_category_name(str(data.get("category", ""))) if data.get("category") else None
    return {"description": description, "tags": tags, "category": category}


async def analyze_emotion_image_with_vision(image_path: Path) -> Dict[str, Any]:
    if not emotion_config.VISION_MODEL:
        raise ValueError("未配置图库自动分类视觉模型组")
    vision_model_group: ModelConfigGroup = core_config.get_model_group_info(emotion_config.VISION_MODEL)
    if vision_model_group.MODEL_TYPE != "chat":
        raise ValueError("图库自动分类视觉模型组必须是 chat 类型")
    if not vision_model_group.ENABLE_VISION:
        raise ValueError("当前视觉模型组未启用视觉功能")
    categories = sync_category_descriptions_with_filesystem()
    category_lines = "\n".join([f"- {name}: {description}" for name, description in categories.items()])
    prompt = (
        "你是表情包图库整理助手。请识别这张图片是否适合作为表情包，并生成可搜索的中文描述、标签和最匹配分类。"
        "必须只返回 JSON，不要包含 Markdown。JSON 格式："
        "{\"description\":\"简洁但具体的中文表情描述\",\"tags\":[\"标签1\",\"标签2\"],\"category\":\"分类名或空字符串\"}。"
        "分类必须从下面列表中选择，实在没有合适分类才返回空字符串：\n"
        f"{category_lines}"
    )
    vision_msg = OpenAIChatMessage.from_text("user", prompt)
    vision_msg.batch_add([
        ContentSegment.text_content(f"Image: {image_path.name}"),
        ContentSegment.image_content_from_path(image_path),
    ])
    response = await gen_openai_chat_response(
        model=vision_model_group.CHAT_MODEL,
        messages=[vision_msg.to_dict()],
        base_url=vision_model_group.BASE_URL,
        api_key=vision_model_group.API_KEY,
    )
    parsed = parse_vision_emotion_result(response.response_content or "")
    if not parsed["description"]:
        parsed["description"] = image_path.stem
    if not parsed["category"]:
        parsed["category"] = infer_emotion_category(parsed["description"], parsed["tags"])
    if parsed["category"] and parsed["category"] not in categories:
        parsed["category"] = infer_emotion_category(parsed["description"], parsed["tags"])
    if parsed["category"] and parsed["category"] not in parsed["tags"]:
        parsed["tags"] = [*parsed["tags"], parsed["category"]]
    return parsed


async def auto_classify_gallery_emotions() -> Dict[str, Any]:
    emotion_store = await load_emotion_store()
    metadata_by_filename = {get_emotion_file_name(metadata.file_path): (emotion_id, metadata) for emotion_id, metadata in emotion_store.emotions.items()}
    candidates: List[Tuple[str, Optional[str], Optional[EmotionMetadata], Path]] = []
    for image_path in sorted(store_dir.iterdir() if store_dir.exists() else []):
        if not _is_supported_image_file(image_path):
            continue
        emotion_id = None
        metadata = None
        if image_path.name in metadata_by_filename:
            emotion_id, metadata = metadata_by_filename[image_path.name]
        needs_description = not metadata or not metadata.description.strip() or metadata.description.strip() == image_path.stem
        needs_category = not metadata or not metadata.category
        if needs_description or needs_category:
            candidates.append((image_path.name, emotion_id, metadata, image_path))
    limit = max(1, int(emotion_config.AUTO_CLASSIFY_BATCH_LIMIT))
    processed = []
    skipped = []
    failed = []
    for filename, emotion_id, metadata, image_path in candidates[:limit]:
        try:
            analysis = await analyze_emotion_image_with_vision(image_path)
            if not emotion_id:
                emotion_id = generate_emotion_id(image_path.name, analysis["description"])
                metadata = EmotionMetadata.create(
                    description=analysis["description"],
                    tags=analysis["tags"],
                    source_path=str(image_path),
                    file_path=image_path.name,
                    category=analysis["category"],
                )
            else:
                assert metadata is not None
                metadata.description = analysis["description"]
                metadata.tags = analysis["tags"]
                metadata.category = analysis["category"]
                metadata.last_updated = int(time.time())
            emotion_store.add_emotion(emotion_id, metadata)
            await upsert_emotion_vector(emotion_id, metadata)
            processed.append(filename)
        except Exception as e:
            failed.append(f"{filename}: {e}")
            logger.warning(f"自动化分类失败: {filename}, {e}")
    if processed:
        await save_emotion_store(emotion_store)
    skipped = [filename for filename, _, _, _ in candidates[limit:]]
    return {
        "status": "ok",
        "processed_count": len(processed),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
        "message": f"自动化分类完成，本次处理 {len(processed)} 个，失败 {len(failed)} 个，剩余 {len(skipped)} 个",
    }


async def update_emotion_metadata_realtime(
    emotion_id: str,
    description: str,
    tags: List[str],
    category: Optional[str] = None,
) -> EmotionMetadata:
    if not emotion_id:
        raise ValueError("Emotion ID cannot be empty")
    if not description.strip():
        raise ValueError("Description cannot be empty")
    if not isinstance(tags, list):
        raise TypeError("Tags must be a list")

    emotion_store = await load_emotion_store()
    metadata = emotion_store.get_emotion(emotion_id)
    if not metadata:
        raise ValueError(f"Emotion with ID '{emotion_id}' not found")

    normalized_category = _safe_category_name(category) if category else metadata.category
    cleaned_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    if normalized_category and normalized_category not in cleaned_tags:
        cleaned_tags = [*cleaned_tags, normalized_category]

    metadata.description = description.strip()
    metadata.tags = cleaned_tags
    metadata.category = normalized_category
    metadata.last_updated = int(time.time())
    emotion_store.add_emotion(emotion_id, metadata)
    await save_emotion_store(emotion_store)
    await upsert_emotion_vector(emotion_id, metadata)
    return metadata


async def upsert_emotion_metadata_by_filename(
    filename: str,
    description: str,
    tags: List[str],
    category: Optional[str] = None,
) -> Tuple[str, EmotionMetadata, bool]:
    safe_filename = Path(str(filename)).name
    image_path = store_dir / safe_filename
    if not safe_filename or not image_path.exists() or not _is_supported_image_file(image_path):
        raise ValueError("图片不存在或格式不受支持")
    if not description.strip():
        raise ValueError("Description cannot be empty")
    if not isinstance(tags, list):
        raise TypeError("Tags must be a list")

    emotion_store = await load_emotion_store()
    for emotion_id, metadata in emotion_store.emotions.items():
        file_path = resolve_emotion_file_path(metadata.file_path)
        if file_path.exists() and file_path.name == safe_filename:
            updated = await update_emotion_metadata_realtime(emotion_id, description, tags, category)
            return emotion_id, updated, False

    normalized_category = _safe_category_name(category) if category else None
    cleaned_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    if normalized_category and normalized_category not in cleaned_tags:
        cleaned_tags = [*cleaned_tags, normalized_category]

    emotion_id = generate_emotion_id(image_path.name, description.strip())
    metadata = EmotionMetadata.create(
        description=description.strip(),
        tags=cleaned_tags,
        source_path=str(image_path),
        file_path=image_path.name,
        category=normalized_category,
    )
    emotion_store.add_emotion(emotion_id, metadata)
    await save_emotion_store(emotion_store)
    await upsert_emotion_vector(emotion_id, metadata)
    return emotion_id, metadata, True


async def migrate_emotion_paths() -> Dict[str, Any]:
    """规范表情路径到 emotions 根目录文件名格式"""
    emotion_store = await load_emotion_store()
    migrated_count = 0
    copied_count = 0
    conflict_count = 0
    skipped_count = 0
    reindexed_count = 0
    errors: List[str] = []

    def _unique_target_path(target_path: Path) -> Path:
        if not target_path.exists():
            return target_path
        stem = target_path.stem
        suffix = target_path.suffix
        for index in range(1, 1000):
            candidate = target_path.with_name(f"{stem}_{index}{suffix}")
            if not candidate.exists():
                return candidate
        return target_path.with_name(f"{stem}_{int(time.time())}{suffix}")

    for emotion_id, metadata in emotion_store.emotions.items():
        resolved_path = resolve_emotion_file_path(metadata.file_path)
        if not resolved_path.exists():
            skipped_count += 1
            logger.warning(
                f"表情包文件不存在，跳过规范化: {emotion_id} -> {metadata.file_path}",
            )
            continue

        target_path = store_dir / resolved_path.name

        if target_path.exists() and target_path.resolve() != resolved_path.resolve():
            target_path = _unique_target_path(target_path)
            conflict_count += 1

        try:
            if target_path.resolve() != resolved_path.resolve():
                store_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(resolved_path), str(target_path))
                copied_count += 1
        except Exception as e:
            skipped_count += 1
            errors.append(f"{emotion_id}: {e}")
            logger.error(f"规范化表情包文件失败: {emotion_id}, {e}")
            continue

        relative_path = target_path.name
        if metadata.file_path != relative_path:
            metadata.file_path = relative_path
            migrated_count += 1
            logger.info(f"规范化表情包路径: {emotion_id} -> {relative_path}")

    if migrated_count > 0:
        await save_emotion_store(emotion_store)
        for emotion_id, metadata in emotion_store.emotions.items():
            if not resolve_emotion_file_path(metadata.file_path).exists():
                continue
            try:
                await upsert_emotion_vector(emotion_id, metadata)
                reindexed_count += 1
            except Exception as e:
                errors.append(f"索引更新 {emotion_id}: {e}")
                logger.error(f"规范化后更新向量索引失败: {emotion_id}, {e}")
        logger.success(
            f"成功规范化 {migrated_count} 个表情包路径到 emotions 根目录文件名格式，复制 {copied_count} 个，冲突改名 {conflict_count} 个，跳过 {skipped_count} 个",
        )
    else:
        if skipped_count > 0:
            logger.warning(
                f"没有需要规范化的表情包路径，但有 {skipped_count} 个文件不存在或处理失败",
            )
        else:
            logger.info("没有需要规范化的表情包路径")

    return {
        "migrated_count": migrated_count,
        "copied_count": copied_count,
        "conflict_count": conflict_count,
        "skipped_count": skipped_count,
        "reindexed_count": reindexed_count,
        "errors": errors[:20],
    }


async def delete_emotion_vectors(emotion_ids: List[str]) -> None:
    if not emotion_ids:
        return
    try:
        client = await get_qdrant_client()
        if client is not None:
            await client.delete(
                collection_name=plugin.get_vector_collection_name(),
                points_selector=qdrant_models.PointIdsList(points=[int(emotion_id, 16) for emotion_id in emotion_ids]),
            )
    except Exception as e:
        logger.warning(f"删除Qdrant中的表情点失败: {e}")


async def deduplicate_gallery_images() -> Dict[str, Any]:
    emotion_store = await load_emotion_store()
    metadata_by_filename = {get_emotion_file_name(metadata.file_path): emotion_id for emotion_id, metadata in emotion_store.emotions.items()}
    seen_hashes: Dict[str, str] = {}
    duplicate_groups: Dict[str, List[str]] = {}
    deleted = []
    deleted_ids = []
    missing = []
    if not store_dir.exists():
        return {"status": "ok", "deleted": [], "deleted_count": 0, "duplicate_groups": {}, "message": "图库目录不存在"}
    for image_path in sorted(store_dir.iterdir()):
        if not _is_supported_image_file(image_path):
            continue
        try:
            file_hash = hashlib.md5(image_path.read_bytes()).hexdigest()
        except Exception as e:
            missing.append(f"{image_path.name}: {e}")
            continue
        if file_hash not in seen_hashes:
            seen_hashes[file_hash] = image_path.name
            continue
        kept_filename = seen_hashes[file_hash]
        duplicate_groups.setdefault(kept_filename, []).append(image_path.name)
        emotion_id = metadata_by_filename.get(image_path.name)
        if emotion_id:
            emotion_store.emotions.pop(emotion_id, None)
            deleted_ids.append(emotion_id)
        image_path.unlink(missing_ok=True)
        deleted.append(image_path.name)
    if deleted:
        emotion_store.recent_emotion_ids = [emotion_id for emotion_id in emotion_store.recent_emotion_ids if emotion_id not in deleted_ids]
        await save_emotion_store(emotion_store)
        await delete_emotion_vectors(deleted_ids)
    return {
        "status": "ok",
        "deleted": deleted,
        "deleted_count": len(deleted),
        "duplicate_groups": duplicate_groups,
        "missing": missing,
        "missing_count": len(missing),
        "message": f"去重完成，删除 {len(deleted)} 个重复图片" if deleted else "未发现重复图片",
    }


async def validate_unified_gallery() -> Dict[str, Any]:
    emotion_store = await load_emotion_store()
    category_stats = await get_category_stats()
    indexed_by_category: Dict[str, int] = {}
    missing_files: List[str] = []
    path_references: List[str] = []
    unmanaged_files: List[str] = []
    metadata_paths = set()

    for emotion_id, metadata in emotion_store.emotions.items():
        file_path = resolve_emotion_file_path(metadata.file_path)
        category = get_emotion_storage_category(metadata.category)
        indexed_by_category[category] = indexed_by_category.get(category, 0) + 1
        if file_path.exists():
            try:
                metadata_paths.add(str(file_path.resolve()))
            except Exception:
                metadata_paths.add(str(file_path))
        else:
            missing_files.append(emotion_id)
        metadata_path = str(metadata.file_path).replace("\\", "/")
        if Path(metadata_path).is_absolute() or "/" in metadata_path:
            path_references.append(emotion_id)

    if store_dir.exists():
        for image_path in store_dir.iterdir():
            if image_path.is_file() and is_supported_image_file(image_path):
                try:
                    resolved_image_path = str(image_path.resolve())
                except Exception:
                    resolved_image_path = str(image_path)
                if resolved_image_path not in metadata_paths:
                    unmanaged_files.append(image_path.name)

    return {
        "status": "ok" if not missing_files and not path_references else "warning",
        "gallery_dir": str(store_dir),
        "total_metadata": len(emotion_store.emotions),
        "category_stats": category_stats,
        "indexed_by_category": indexed_by_category,
        "missing_files": missing_files[:50],
        "path_references": sorted(set(path_references))[:50],
        "unmanaged_files": unmanaged_files[:100],
        "unmanaged_count": len(unmanaged_files),
    }


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
    category: Optional[str] = None,
) -> Tuple[bool, str]:
    """保存图片到表情包存储目录

    Args:
        source_path (str): 源图片路径或URL
        file_name (str): 目标文件名
        _ctx (schemas.AgentCtx): 上下文
        category (Optional[str]): 表情分类，未指定时归入未分类

    Returns:
        Tuple[bool, str]: (是否成功, 相对路径)
    """
    target_path = store_dir / Path(file_name).name
    relative_path = target_path.name

    if source_path.startswith(("http://", "https://")):
        logger.info(f"从URL下载图片: {source_path} 到 {target_path}")
        success = await download_image(source_path, target_path)
        return success, relative_path

    try:
        source_path_obj = convert_to_host_path(Path(source_path), _ctx.chat_key)
        logger.info(f"从本地路径复制图片: {source_path_obj} 到 {target_path}")

        if not source_path_obj.exists():
            logger.error(f"图片不存在: {source_path}")
            return False, relative_path

        async with aiofiles.open(source_path_obj, "rb") as src_file:
            content = await src_file.read()

        async with aiofiles.open(target_path, "wb") as target_file:
            await target_file.write(content)

    except Exception as e:
        logger.error(f"保存图片失败: {source_path}, 错误: {e}")
        return False, relative_path
    else:
        return True, relative_path


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
    if not emotion_config.ENABLE_DUPLICATE_EMOTION_DETECTION:
        return None
    if not file_path.exists():
        return None

    target_hash = calculate_file_hash(file_path)
    if not target_hash:
        return None

    emotion_store = await load_emotion_store()
    for emotion_id, metadata in emotion_store.emotions.items():
        existing_path = resolve_emotion_file_path(metadata.file_path)
        if not existing_path.exists():
            continue
        existing_hash = calculate_file_hash(existing_path)
        if existing_hash == target_hash:
            logger.info(f"发现重复表情包：{emotion_id}，哈希值：{target_hash}")
            return emotion_id

    return None


def normalize_match_tokens(text: str) -> List[str]:
    lowered = text.lower().replace("_", " ").replace("-", " ")
    separators = [",", "，", ";", "；", "|", "/", "\\", "\n", "\t"]
    for separator in separators:
        lowered = lowered.replace(separator, " ")
    return [token.strip() for token in lowered.split() if token.strip()]


def calculate_loose_match_score(query: str, metadata: EmotionMetadata) -> float:
    query_tokens = normalize_match_tokens(query)
    if not query_tokens:
        return 0.0

    searchable_parts = [metadata.description, *metadata.tags]
    if metadata.category:
        searchable_parts.append(metadata.category)
    searchable_text = " ".join(searchable_parts).lower().replace("_", " ").replace("-", " ")
    searchable_tokens = set(normalize_match_tokens(searchable_text))
    matched = 0
    partial = 0
    for token in query_tokens:
        if token in searchable_tokens or token in searchable_text:
            matched += 1
        elif emotion_config.ENABLE_LOOSE_MATCH and any(token in candidate or candidate in token for candidate in searchable_tokens):
            partial += 1

    tag_bonus = 0.0
    if emotion_config.ENABLE_FALLBACK_TAG_MATCH:
        tag_text = " ".join([*metadata.tags, metadata.category or ""]).lower().replace("_", " ").replace("-", " ")
        if any(token in tag_text for token in query_tokens):
            tag_bonus = 0.15

    return min(1.0, (matched + partial * 0.5) / len(query_tokens) + tag_bonus)


def fallback_emotion_matches(
    query: str,
    emotion_store: EmotionStore,
    exclude_ids: Optional[set[str]] = None,
    limit: Optional[int] = None,
) -> List[Tuple[str, EmotionMetadata, float]]:
    if not emotion_config.ENABLE_LOOSE_MATCH and not emotion_config.ENABLE_FALLBACK_TAG_MATCH:
        return []

    exclude_ids = exclude_ids or set()
    limit = limit or emotion_config.MAX_SEARCH_RESULTS
    matches: List[Tuple[str, EmotionMetadata, float]] = []
    for emotion_id, metadata in emotion_store.emotions.items():
        if emotion_id in exclude_ids:
            continue
        score = calculate_loose_match_score(query, metadata)
        if score >= emotion_config.LOOSE_MATCH_MIN_SCORE:
            matches.append((emotion_id, metadata, score))

    matches.sort(key=lambda item: item[2], reverse=True)
    return matches[:limit]


def is_high_confidence_score(score: float) -> bool:
    return score >= emotion_config.HIGH_CONFIDENCE_THRESHOLD


def infer_emotion_category(description: str, tags: List[str]) -> Optional[str]:
    available_categories = sync_category_descriptions_with_filesystem()
    text = f"{description} {' '.join(tags or [])}".lower()
    category_keywords = {
        "happy": ["开心", "笑", "高兴", "庆祝"],
        "angry": ["生气", "怒", "骂", "不爽"],
        "confused": ["困惑", "问号", "不懂", "懵"],
        "sad": ["伤心", "哭", "难过", "遗憾"],
        "surprised": ["惊讶", "震惊", "意外"],
    }
    best_category: Optional[str] = None
    best_score = 0
    for category, keywords in category_keywords.items():
        if category not in available_categories:
            continue
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_category = category
            best_score = score
    return best_category


async def get_category_prompt_lines() -> List[str]:
    if not emotion_config.ENABLE_CATEGORY_GALLERY:
        return []
    categories = sync_category_descriptions_with_filesystem()
    if not categories:
        return []
    stats = await get_category_stats()
    return [
        f"- {category}: {description} ({stats.get(category, 0)} images)"
        for category, description in categories.items()
    ]


def get_emotion_directory_prompt_lines(emotion_store: EmotionStore) -> List[str]:
    category_counts: Dict[str, int] = {}
    orphan_count = 0
    missing_count = 0
    for metadata in emotion_store.emotions.values():
        if not resolve_emotion_file_path(metadata.file_path).exists():
            missing_count += 1
            continue
        if metadata.category:
            category_counts[metadata.category] = category_counts.get(metadata.category, 0) + 1
        else:
            orphan_count += 1

    lines: List[str] = []
    if category_counts:
        lines.append("Collected Emotion Directory:")
        for category, count in sorted(category_counts.items()):
            lines.append(f"- {category}: {count} collected emotions")
    if orphan_count:
        if not lines:
            lines.append("Collected Emotion Directory:")
        lines.append(f"- uncategorized: {orphan_count} collected emotions")
    if missing_count:
        if not lines:
            lines.append("Collected Emotion Directory:")
        lines.append(f"- missing files ignored: {missing_count}")
    return lines


# endregion: 表情包工具方法


# region: 表情包命令
@plugin.mount_command(
    name="emo_search",
    description="语义搜索表情包",
    aliases=[],
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

    # 加载表情包存储
    emotion_store = await load_emotion_store()

    vector_matches: List[Tuple[str, EmotionMetadata, float]] = []
    matched_ids: set[str] = set()
    found_count = 0

    for result in search_results:
        score = float(getattr(result, "score", 0.0) or 0.0)
        emotion_id = result.payload.get("emotion_id") if result.payload else None
        if not emotion_id:
            emotion_id = format(result.id, "x")
        metadata = emotion_store.get_emotion(emotion_id)
        if not metadata:
            continue
        if score < emotion_config.SIMILARITY_THRESHOLD:
            continue
        vector_matches.append((emotion_id, metadata, score))
        matched_ids.add(emotion_id)

    fallback_matches = fallback_emotion_matches(
        keyword,
        emotion_store,
        exclude_ids=matched_ids,
        limit=max(0, emotion_config.MAX_SEARCH_RESULTS - len(vector_matches)),
    )
    combined_matches = [*vector_matches, *fallback_matches]

    if not combined_matches:
        return CmdCtl.failed(f"没有找到和「{keyword}」相关的表情包")

    output_segments: list[CommandOutputSegment] = []

    for i, (emotion_id, metadata, score) in enumerate(combined_matches, 1):
        file_path = resolve_emotion_file_path(metadata.file_path)
        if not file_path.exists():
            logger.warning(f"表情包文件不存在: {emotion_id}, {file_path}")
            continue

        tags_str = "、".join(metadata.tags) if metadata.tags else "暂无标签"
        source_text = "向量匹配" if emotion_id in matched_ids else "备用标记匹配"
        confidence_text = "高置信度" if is_high_confidence_score(score) else "普通置信度"
        output_segments.append(
            CommandOutputSegment(
                type=CommandOutputSegmentType.TEXT,
                text=(
                    f"{i}. ID: {emotion_id}\n"
                    f"描述: {metadata.description}\n"
                    f"标签: {tags_str}\n"
                    f"匹配: {source_text} / {confidence_text} / {score:.2f}"
                ),
            )
        )
        output_segments.append(
            CommandOutputSegment(
                type=CommandOutputSegmentType.IMAGE,
                file_path=str(file_path),
            )
        )
        found_count += 1

    if not found_count:
        return CmdCtl.failed(f"没有找到和「{keyword}」相关的可用表情包")

    return CmdCtl.success([
        CommandOutputSegment(
            type=CommandOutputSegmentType.TEXT,
            text=f"和「{keyword}」相关的表情包，共 {found_count} 个",
        ),
        *output_segments,
    ])


@plugin.mount_command(
    name="emo_stats",
    description="查看表情包统计信息",
    aliases=[],
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


def _parse_emo_list_page(args_str: str) -> int:
    """解析 emo_list 的页码。

    兼容旧版 `-i/--image` 预览参数，但现在默认就会带图片。
    """
    page = 1

    for token in args_str.split():
        if token in {"-i", "--image", "--images", "--preview"}:
            continue
        if token.lstrip("-").isdigit():
            page = max(1, int(token))
            continue
        raise ValueError(f"不支持的参数: {token}")

    return page


@plugin.mount_command(
    name="emo_list",
    description="分页列出所有表情包",
    aliases=["emo_ls"],
    usage="emo_list [页码]",
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_list_cmd(
    context: CommandExecutionContext,
    args_str: Annotated[str, Arg("参数", positional=True, greedy=True)] = "",
) -> CommandResponse:
    emotion_store = await load_emotion_store()

    try:
        page = _parse_emo_list_page(args_str)
    except ValueError as e:
        return CmdCtl.failed(str(e))

    page_size = 10
    total_count = len(emotion_store.emotions)
    if total_count == 0:
        return CmdCtl.success("当前还没有收藏任何表情包")

    total_pages = (total_count + page_size - 1) // page_size

    if page > total_pages:
        return CmdCtl.failed(f"当前只有 {total_pages} 页，请输入有效的页码")

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_count)

    sorted_emotions = sorted(
        emotion_store.emotions.items(),
        key=lambda x: x[1].added_time,
        reverse=True,
    )[start_idx:end_idx]

    output_segments: list[CommandOutputSegment] = []
    preview_count = 0

    for emotion_id, metadata in sorted_emotions:
        file_path = resolve_emotion_file_path(metadata.file_path)
        if not file_path.exists():
            logger.warning(f"表情包文件不存在: {emotion_id}, {file_path}")
            continue

        tags_str = "、".join(metadata.tags[:3]) + ("..." if len(metadata.tags) > 3 else "")
        output_segments.append(
            CommandOutputSegment(
                type=CommandOutputSegmentType.TEXT,
                text=f"ID: {emotion_id}\n描述: {metadata.description[:30]}...\n标签: {tags_str}",
            )
        )
        output_segments.append(
            CommandOutputSegment(
                type=CommandOutputSegmentType.IMAGE,
                file_path=str(file_path),
            )
        )
        preview_count += 1

    if preview_count == 0:
        return CmdCtl.failed(f"第 {page}/{total_pages} 页没有可预览的表情包图片")

    return CmdCtl.success([
        CommandOutputSegment(
            type=CommandOutputSegmentType.TEXT,
            text=f"第 {page}/{total_pages} 页表情包预览，共 {preview_count} 个，使用 emo_list <页码> 查看其他页面",
        ),
        *output_segments,
    ])


@plugin.mount_command(
    name="emo_gallery",
    description="查看分类图库统计",
    aliases=["emo_categories"],
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_gallery_cmd(context: CommandExecutionContext) -> CommandResponse:
    descriptions = sync_category_descriptions_with_filesystem()
    stats = await get_category_stats()
    if not descriptions:
        return CmdCtl.success("当前还没有任何分类图库")

    lines = [
        f"- {name}: {description}（{stats.get(name, 0)} 个）"
        for name, description in descriptions.items()
    ]
    return CmdCtl.success("当前分类图库：\n" + "\n".join(lines))


@plugin.mount_command(
    name="emo_category_update",
    description="新增或更新分类描述",
    aliases=[],
    usage="emo_category_update <分类> <描述>",
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_category_update_cmd(
    context: CommandExecutionContext,
    args_str: Annotated[str, Arg("参数", positional=True, greedy=True)] = "",
) -> CommandResponse:
    parts = args_str.split(maxsplit=1)
    if len(parts) != 2:
        return CmdCtl.failed("用法：emo_category_update <分类> <描述>")

    category_name = _safe_category_name(parts[0])
    description = parts[1].strip()
    if not category_name or not description:
        return CmdCtl.failed("分类和描述不能为空")

    descriptions = sync_category_descriptions_with_filesystem()
    descriptions[category_name] = description
    save_category_descriptions(descriptions)
    return CmdCtl.success(f"已更新分类「{category_name}」：{description}")


@plugin.mount_command(
    name="emo_category_clear",
    description="清空指定分类图库中的图片但保留分类描述",
    aliases=[],
    usage="emo_category_clear <分类> -y",
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_category_clear_cmd(
    context: CommandExecutionContext,
    args_str: Annotated[str, Arg("参数", positional=True, greedy=True)] = "",
) -> CommandResponse:
    tokens = args_str.split()
    if len(tokens) < 2 or "-y" not in tokens:
        return CmdCtl.failed("用法：emo_category_clear <分类> -y")

    category_name = _safe_category_name(tokens[0])
    emotion_store = await load_emotion_store()
    image_paths = await get_category_image_paths(category_name)
    if not image_paths:
        return CmdCtl.success(f"分类「{category_name}」没有可清空的图片")

    deleted_count = 0
    deleted_ids = []
    managed_files = {get_emotion_file_name(metadata.file_path) for metadata in emotion_store.emotions.values()}
    for image_path in image_paths:
        try:
            image_path.unlink(missing_ok=True)
            deleted_count += 1
        except Exception as e:
            logger.warning(f"删除分类图库图片失败: {image_path}, {e}")
    for emotion_id, metadata in list(emotion_store.emotions.items()):
        file_path = resolve_emotion_file_path(metadata.file_path)
        if get_emotion_storage_category(metadata.category) == category_name or (
            category_name == "未分类" and file_path.name not in managed_files
        ):
            emotion_store.emotions.pop(emotion_id, None)
            deleted_ids.append(emotion_id)
    if deleted_ids:
        emotion_store.recent_emotion_ids = [emotion_id for emotion_id in emotion_store.recent_emotion_ids if emotion_id not in deleted_ids]
        await save_emotion_store(emotion_store)
        try:
            client = await get_qdrant_client()
            if client is not None:
                await client.delete(
                    collection_name=plugin.get_vector_collection_name(),
                    points_selector=qdrant_models.PointIdsList(points=[int(emotion_id, 16) for emotion_id in deleted_ids]),
                )
        except Exception as e:
            logger.warning(f"清空分类时删除Qdrant中的表情点失败: {e}")

    return CmdCtl.success(f"已清空分类「{category_name}」，删除 {deleted_count} 个图片")


@plugin.mount_command(
    name="emo_sync",
    description="同步分类图库到图床或从图床同步回来",
    aliases=["emo_img_sync"],
    usage="emo_sync <status|upload|download|sync_all|overwrite_to_remote|overwrite_from_remote>",
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_sync_cmd(
    context: CommandExecutionContext,
    task: Annotated[str, Arg("同步任务", positional=True)] = "status",
) -> CommandResponse:
    try:
        result = await run_image_sync_task(task)
        return CmdCtl.success(summarize_sync_result(result))
    except Exception as e:
        logger.error(f"图床同步失败: {e}")
        return CmdCtl.failed(f"图床同步失败: {e}")


@plugin.mount_command(
    name="emo_migrate",
    description="迁移表情包路径到新格式",
    aliases=[],
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_migrate_cmd(context: CommandExecutionContext) -> CommandResponse:
    result = await migrate_emotion_paths()
    return CmdCtl.success(
        "统一图库迁移完成！\n"
        f"路径更新：{result['migrated_count']} 个\n"
        f"文件移动：{result['moved_count']} 个\n"
        f"文件复制：{result['copied_count']} 个\n"
        f"冲突改名：{result['conflict_count']} 个\n"
        f"跳过：{result['skipped_count']} 个\n"
        f"索引更新：{result['reindexed_count']} 个"
    )


@plugin.mount_command(
    name="emo_gallery_check",
    description="验证统一图库状态",
    aliases=["emo_check"],
    permission=CommandPermission.SUPER_USER,
    category="表情包",
)
async def emo_gallery_check_cmd(context: CommandExecutionContext) -> CommandResponse:
    result = await validate_unified_gallery()
    lines = [
        "统一图库验证结果：",
        f"状态：{result['status']}",
        f"图库目录：{result['gallery_dir']}",
        f"元数据数量：{result['total_metadata']} 个",
        f"图库图片数量：{sum(result['category_stats'].values())} 个",
        f"未入库图库图片：{result['unmanaged_count']} 个",
        f"缺失文件：{len(result['missing_files'])} 个",
        f"路径引用：{len(result['path_references'])} 个",
    ]
    if result["indexed_by_category"]:
        indexed_lines = [f"{category}:{count}" for category, count in sorted(result["indexed_by_category"].items())]
        lines.append("入库分类统计：" + "、".join(indexed_lines[:24]))
    if result["missing_files"]:
        lines.append("缺失文件 ID：" + "、".join(result["missing_files"][:10]))
    if result["path_references"]:
        lines.append("路径引用 ID：" + "、".join(result["path_references"][:10]))
    if result["unmanaged_files"]:
        lines.append("未入库图库示例：" + "、".join(result["unmanaged_files"][:10]))
    return CmdCtl.success("\n".join(lines))


@plugin.mount_command(
    name="emo_reindex",
    description="重建表情包索引",
    aliases=[],
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
                        "category": metadata.category,
                        "file_path": metadata.file_path,
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

    prompt_parts: List[str] = []
    if recent_emotions:
        prompt_parts.append("Recent Emotions:")
        for idx, (emotion_id, metadata) in enumerate(recent_emotions, 1):
            tags_str = ", ".join(metadata.tags[:3]) + (
                "..." if len(metadata.tags) > 3 else ""
            )
            category_str = f" [Category: {metadata.category}]" if metadata.category else ""
            prompt_parts.append(
                f"{idx}. ID: {emotion_id} - {metadata.description[:30]}... [Tags: {tags_str}]{category_str}",
            )
    else:
        prompt_parts.append("Recent Emotions: No emotions added yet. You can use `collect_emotion` to add some. (You should not send 'ID' in your message directly.)")

    directory_prompt_lines = get_emotion_directory_prompt_lines(emotion_store)
    if directory_prompt_lines:
        prompt_parts.extend(directory_prompt_lines)

    category_prompt_lines = await get_category_prompt_lines()
    if category_prompt_lines:
        prompt_parts.append("Available Meme Categories:")
        prompt_parts.extend(category_prompt_lines)

    addition_prompt = (
        "Attention: Emotion Plugin is a isolated self-managed plugin, you should not record the emotion ID manually by using other plugins. "
        "When you need to send an existing emotion, do NOT call vision just to inspect the image first. "
        "Prefer `search_emotion` or `browse_meme_category` to get text metadata candidates, then use `get_emotion_path` for the selected emotion ID. "
        "The candidate lists returned by emotion search tools are internal tool results only: do NOT quote, summarize, or expose the raw candidate list, category description, emotion ID, filename, tags, score, or matching details to the user unless the user explicitly asks for search details. "
        "If the goal is to send an emotion, silently choose the best candidate, call `get_emotion_path`, and send the emotion directly. "
        + (
            "When collecting an emotion, you MUST choose the best matching `category` from Available Meme Categories according to the image description, emotion and usage scenario, then pass it to `collect_emotion`; leave `category` empty only when no category is suitable. "
            if emotion_config.ALLOW_AI_COLLECT_EMOTION
            else "AI emotion collection is disabled by configuration; DO NOT call `collect_emotion`, and only use emotions already in the gallery. "
        )
        + "Search results may include vector matches and fallback tag/loose matches; prefer high confidence results when several emotions are returned. "
        "You can use `list_meme_categories` and category-aware collect/search tools when scene categories are helpful."
    )

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
    category: Optional[str] = None,
) -> str:
    """Collect Emotion (表情包)

    Collect an expression image/GIF to the emotion database.
    **IMPORTANT:** Only collect actual expression images or reaction GIFs, **DO NOT COLLECT ANY screenshots, photos, or other images!** You can only collect the images you are sure about (visible in vision content). Do not collect anything send by yourself!

    Args:
        source_path (str): The path or URL of the expression image
        description (str): A detailed description of the emotion/expression (used for searching. You Must fill it in carefully)
        tags (List[str]): Tags for the emotion (e.g. ["happy", "excited", "anime"])
        vision_and_emotion_confirmed (bool): Whether the image content is confirmed by vision (default: False, You Can Only Collect Images That Are Visible in Vision Content and NEVER Guess the content!)
        category (str, optional): Scene/category name from the category gallery, such as happy, sad, angry

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
    if not emotion_config.ALLOW_AI_COLLECT_EMOTION:
        await message_service.push_system_message(
            _ctx.chat_key,
            "AI emotion collection is disabled by configuration. Use existing gallery emotions only.",
        )
        return ""

    if not source_path:
        raise ValueError("Error: Source path cannot be empty!")

    if not description:
        raise ValueError("Error: Description cannot be empty!")

    # 确保tags是列表
    if tags is None:
        tags = []

    normalized_category = _safe_category_name(category) if category else infer_emotion_category(description, tags)
    if normalized_category and normalized_category not in tags:
        tags = [*tags, normalized_category]

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

    # 保存图片（返回 emotions 根目录相对文件名）
    success, relative_path = await save_image(source_path, file_name, _ctx, category)
    if not success:
        raise ValueError(f"Error: Failed to save image from {source_path}")

    # 检查是否有重复图片
    absolute_file_path = resolve_emotion_file_path(relative_path)
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
            metadata.category = normalized_category
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
    emotion_id = generate_emotion_id(relative_path, description)

    # 创建元数据（使用相对路径）
    metadata = EmotionMetadata.create(
        description=description,
        tags=tags,
        source_path=source_path,
        file_path=relative_path,  # 保存相对路径
        category=normalized_category,
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
    category: Optional[str] = None,
) -> str:
    """Update Emotion (更新表情包)

    Update the metadata of an existing emotion.

    Args:
        emotion_id (str): The ID of the emotion to update
        description (str): New description for the emotion
        tags (List[str]): New tags for the emotion
        category (str, optional): New category for the emotion

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
    metadata = await update_emotion_metadata_realtime(
        emotion_id=emotion_id,
        description=description,
        tags=tags,
        category=category,
    )
    logger.info(f"已实时更新表情包元数据和向量索引: {emotion_id}")

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
    SandboxMethodType.TOOL,
    name="同步统一图库图床",
    description="执行统一图库与图床的同步任务，支持 status/upload/download/sync_all/overwrite_to_remote/overwrite_from_remote",
)
async def sync_meme_image_host(_ctx: schemas.AgentCtx, task: str = "status") -> str:
    """Sync meme gallery with the configured image host.

    Run a unified gallery sync task against the configured image host provider.
    Supported tasks are: `status`, `upload`, `download`, `sync_all`,
    `overwrite_to_remote`, and `overwrite_from_remote`.

    Args:
        task (str): Sync task name. Defaults to `status`.

    Returns:
        str: Human-readable summary of the sync result

    Example:
        ```python
        # Check sync status
        result = sync_meme_image_host("status")

        # Upload local gallery changes to remote image host
        result = sync_meme_image_host("upload")
        ```
    """
    result = await run_image_sync_task(task)
    return summarize_sync_result(result)


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="查看表情包分类",
    description="查看按场景组织的表情包图库分类、描述与数量",
)
async def list_meme_categories(_ctx: schemas.AgentCtx) -> str:
    """List meme categories (查看表情包分类).

    Return the current gallery categories, their descriptions, and image counts
    as a JSON string for downstream planning and selection.

    Returns:
        str: JSON string containing category names, descriptions, and counts

    Example:
        ```python
        categories_json = list_meme_categories()
        ```
    """
    descriptions = sync_category_descriptions_with_filesystem()
    stats = await get_category_stats()
    return json.dumps(
        {
            "categories": [
                {
                    "name": category,
                    "description": description,
                    "count": stats.get(category, 0),
                }
                for category, description in descriptions.items()
            ],
        },
        ensure_ascii=False,
    )


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="更新表情包分类描述",
    description="新增或更新一个表情包场景分类的说明",
)
async def update_meme_category(
    _ctx: schemas.AgentCtx,
    category: str,
    description: str,
) -> str:
    """Create or update a meme category description (更新表情包分类描述).

    Args:
        category (str): Category name to create or update
        description (str): Category description text

    Returns:
        str: Updated category name

    Example:
        ```python
        category_name = update_meme_category("happy", "适合开心、庆祝、轻松等场景")
        ```
    """
    safe_category = _safe_category_name(category)
    if not safe_category:
        raise ValueError("Error: Category cannot be empty!")
    if not description.strip():
        raise ValueError("Error: Description cannot be empty!")

    descriptions = sync_category_descriptions_with_filesystem()
    descriptions[safe_category] = description.strip()
    save_category_descriptions(descriptions)
    return safe_category


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="添加图片到统一图库",
    description="把图片加入统一图库并记录分类元数据；如需语义检索请使用收集表情包",
)
async def add_meme_to_category(
    _ctx: schemas.AgentCtx,
    source_path: str,
    category: str,
) -> str:
    """Add an image to the unified gallery without vector indexing.

    Args:
        source_path (str): Source image path or image URL
        category (str): Target gallery category name

    Returns:
        str: Saved gallery image path

    Example:
        ```python
        saved_path = add_meme_to_category("/app/uploads/happy_cat.png", "happy")
        ```
    """
    if not emotion_config.ENABLE_CATEGORY_GALLERY:
        raise ValueError("Error: Category gallery is disabled")
    target_path = await add_image_to_category_gallery(source_path, category, _ctx)
    return str(target_path)


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="浏览分类表情包",
    description="按分类浏览表情包元数据候选列表，不返回图片内容",
)
async def browse_meme_category(
    _ctx: schemas.AgentCtx,
    category: str,
    max_results: Optional[int] = None,
) -> str:
    """Browse category meme images (浏览分类表情包).

    Args:
        category (str): Category name to browse
        max_results (int, optional): Maximum number of images to observe

    Returns:
        str: Formatted candidate list with emotion IDs and metadata

    Example:
        ```python
        category_view = browse_meme_category("happy", max_results=3)
        ```
    """
    safe_category = _safe_category_name(category)
    emotion_store = await load_emotion_store()
    items = get_category_image_items_from_store(emotion_store, safe_category)
    if not items:
        return f"分类 `{safe_category}` 下没有可用表情。"
    limit = max_results or emotion_config.MAX_SEARCH_RESULTS
    descriptions = sync_category_descriptions_with_filesystem()
    lines = [
        "内部工具结果：仅用于选择候选表情，禁止原样转发或复述给用户；如果你的目标是发送表情，请直接选中候选并调用 `get_emotion_path`。",
        f"分类: {safe_category}",
        f"分类描述: {descriptions.get(safe_category, '无描述')}",
        "以下是可直接发送的表情候选，请根据描述/标签选择；不需要先调用视觉查看图片。",
    ]
    for idx, item in enumerate(items[:limit], 1):
        tags_str = ", ".join(item.get("tags") or []) or "无标签"
        description = item.get("description") or "无描述"
        emotion_id = item.get("emotion_id") or "未建档"
        managed_text = "已建档" if item.get("managed") else "仅图库图片"
        lines.append(
            f"{idx}. ID: {emotion_id} | 文件: {item['filename']} | 状态: {managed_text} | 描述: {description} | 标签: {tags_str}",
        )
    lines.append("选中后，如需发送，请对已建档候选调用 `get_emotion_path` 获取文件路径。")
    return "\n".join(lines)


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="搜索表情包",
    description="根据文本描述搜索表情包，返回文字元数据候选而不是图片",
)
async def search_emotion(
    _ctx: schemas.AgentCtx,
    query: str,
    max_results: Optional[int] = None,
) -> str:
    """Search Emotion

    Search for emotions using a text query and display the results.

    Args:
        query (str): The search query text
        max_results (int, optional): Maximum number of results to observe (recommended: 3-5)

    Returns:
        str: Formatted candidate list with emotion IDs and metadata

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
        return f"搜索表情包失败: {e}"

    # 加载表情包存储
    emotion_store = await load_emotion_store()

    vector_matches: List[Tuple[str, EmotionMetadata, float]] = []
    matched_ids: set[str] = set()

    for result in search_results:
        score = float(getattr(result, "score", 0.0) or 0.0)
        emotion_id = result.payload.get("emotion_id") if result.payload else None
        if not emotion_id:
            emotion_id = format(result.id, "x")
        metadata = emotion_store.get_emotion(emotion_id)
        if not metadata:
            continue
        if score < emotion_config.SIMILARITY_THRESHOLD:
            continue
        vector_matches.append((emotion_id, metadata, score))
        matched_ids.add(emotion_id)

    fallback_matches = fallback_emotion_matches(
        query,
        emotion_store,
        exclude_ids=matched_ids,
        limit=max(0, search_limit - len(vector_matches)),
    )
    combined_matches = [*vector_matches, *fallback_matches]

    if not combined_matches:
        return f"没有找到与 `{query}` 相关的表情。可以换个关键词，或先补充更多表情。"

    found_count = 0
    lines = [
        "内部工具结果：仅用于选择候选表情，禁止原样转发或复述给用户；如果你的目标是发送表情，请直接选中候选并调用 `get_emotion_path`。",
        f"查询: {query}",
        "以下是按语义和标签匹配得到的表情候选；发送已有表情时不需要先调用视觉查看图片。",
    ]
    for i, (emotion_id, metadata, score) in enumerate(combined_matches, 1):
        file_path = resolve_emotion_file_path(metadata.file_path)
        if not file_path.exists():
            continue

        tags_str = ", ".join(metadata.tags) if metadata.tags else "No tags"
        category_str = f"\nCategory: {metadata.category}" if metadata.category else ""
        source_text = "vector" if emotion_id in matched_ids else "fallback tag/loose"
        confidence_text = "high confidence" if is_high_confidence_score(score) else "normal confidence"
        category_text = metadata.category or "未分类"
        lines.append(
            f"{i}. ID: {emotion_id} | 分类: {category_text} | 描述: {metadata.description} | 标签: {tags_str} | 匹配: {source_text}, {confidence_text}, score {score:.2f}",
        )
        found_count += 1

    if not found_count:
        return f"查询 `{query}` 命中了记录，但没有找到可用的表情文件。"
    lines.append("选中后请直接调用 `get_emotion_path` 获取该表情文件路径并发送。")
    lines.append("如果发现描述不准，请立即调用 `update_emotion` 修正；如果发现是截图、照片等非表情内容，请立即调用 `remove_emotion` 删除。")
    return "\n".join(lines)


# region: Web 管理路由


def is_webui_access_key_enabled() -> bool:
    return bool(emotion_config.WEBUI_ACCESS_KEY.strip())


def verify_webui_access_key(access_key: Optional[str]) -> bool:
    expected_key = emotion_config.WEBUI_ACCESS_KEY.strip()
    if not expected_key:
        return True
    return access_key == expected_key


def require_webui_access_key(access_key: Optional[str]) -> None:
    if not verify_webui_access_key(access_key):
        raise HTTPException(status_code=403, detail="WebUI 访问密钥无效或缺失")


def get_webui_access_key_from_request(request: Request) -> Optional[str]:
    return request.query_params.get("access_key") or request.cookies.get("emotion_webui_access_key")


async def webui_auth_dependency(
    request: Request,
    access_key: Optional[str] = Query(None),
    x_emotion_webui_key: Optional[str] = Header(None),
) -> None:
    require_webui_access_key(access_key or x_emotion_webui_key or get_webui_access_key_from_request(request))


@plugin.mount_router()
def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, summary="表情包管理页面")
    async def emotion_manager_page(request: Request):
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>表情包管理</title>
  <style>
    :root {
      --bg: #08111f;
      --panel: rgba(15, 23, 42, .78);
      --panel-strong: rgba(15, 23, 42, .92);
      --border: rgba(148, 163, 184, .22);
      --text: #e5edf8;
      --muted: #91a4bd;
      --primary: #7c3aed;
      --primary-2: #06b6d4;
      --success: #22c55e;
      --danger: #ef4444;
      --warning: #f59e0b;
      --shadow-sm: 0 4px 12px rgba(0, 0, 0, .2);
      --shadow: 0 12px 30px rgba(0, 0, 0, .3);
      --shadow-lg: 0 24px 60px rgba(0, 0, 0, .4);
      --radius-sm: 10px;
      --radius: 16px;
      --radius-lg: 24px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background: var(--bg);
      background-image: 
        radial-gradient(circle at 12% 10%, rgba(124, 58, 237, .15), transparent 30%),
        radial-gradient(circle at 88% 6%, rgba(6, 182, 212, .15), transparent 28%),
        radial-gradient(circle at 50% 92%, rgba(34, 197, 94, .1), transparent 28%),
        linear-gradient(135deg, #060914 0%, #0b1220 48%, #111827 100%);
      background-attachment: fixed;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: linear-gradient(rgba(255,255,255,.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.02) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, rgba(0,0,0,.8), transparent 85%);
    }
    body.locked main { display: none; }
    header {
      position: sticky;
      top: 0;
      z-index: 20;
      padding: 20px 32px;
      border-bottom: 1px solid rgba(148, 163, 184, .1);
      background: rgba(8, 17, 31, .6);
      backdrop-filter: blur(24px);
      box-shadow: 0 4px 30px rgba(0, 0, 0, .4);
    }
    header h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: .05em;
      background: linear-gradient(120deg, #fff, #a5f3fc 45%, #c4b5fd);
      -webkit-background-clip: text;
      color: transparent;
      text-shadow: 0 0 30px rgba(6, 182, 212, .4);
    }
    header div { margin-top: 6px; color: var(--muted); font-size: 13px; font-weight: 500; }
    main { position: relative; padding: 32px; max-width: 1560px; margin: 0 auto; }
    .grid { display: flex; gap: 28px; align-items: flex-start; }
    .category-panel {
      position: sticky;
      top: 104px;
      width: 320px;
      flex: 0 0 320px;
      max-height: calc(100vh - 132px);
      display: flex;
      flex-direction: column;
      transition: width 0.28s cubic-bezier(0.4, 0, 0.2, 1), flex-basis 0.28s cubic-bezier(0.4, 0, 0.2, 1), padding 0.28s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.2s ease, background 0.2s ease;
      will-change: width, flex-basis;
    }
    .category-panel.card { overflow: visible; }
    .category-panel.collapsed {
      width: 44px;
      flex-basis: 44px;
      padding: 8px;
      border-color: rgba(148, 163, 184, .16);
    }
    .category-panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 28px;
      margin-bottom: 18px;
    }
    .category-panel-header h3 {
      margin: 0;
      white-space: nowrap;
      transition: opacity 0.18s ease, width 0.18s ease;
    }
    .category-panel.collapsed .category-panel-header {
      justify-content: center;
      margin-bottom: 0;
    }
    .category-panel.collapsed .category-panel-header h3 {
      opacity: 0;
      width: 0;
      overflow: hidden;
      pointer-events: none;
    }
    .category-panel-body {
      display: flex;
      flex: 1;
      min-height: 0;
      flex-direction: column;
      opacity: 1;
      transform: translateX(0);
      transition: opacity 0.18s ease, transform 0.18s ease;
    }
    .category-panel.collapsed .category-panel-body {
      opacity: 0;
      transform: translateX(-10px);
      pointer-events: none;
    }
    .category-panel.collapsed .category-panel-body {
      width: 0;
      height: 0;
      margin: 0;
      padding: 0;
      overflow: hidden;
    }
    .toggle-sidebar-btn {
      width: 28px;
      height: 28px;
      min-width: 0;
      padding: 0;
      border-radius: 6px;
      background: transparent;
      color: #94a3b8;
      border: 1px solid transparent;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .toggle-sidebar-btn:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.15);
    }
    .category-panel.collapsed .toggle-sidebar-btn { transform: rotate(180deg); }
    .content-panel { flex: 1; min-width: 0; }
    .card {
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(255, 255, 255, .05);
      border-radius: var(--radius-lg);
      background: linear-gradient(145deg, rgba(15, 23, 42, .6), rgba(30, 41, 59, .4));
      box-shadow: var(--shadow);
      padding: 24px;
      backdrop-filter: blur(12px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .card::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: linear-gradient(135deg, rgba(255,255,255,.05), transparent 35%);
    }
    .card:hover {
      box-shadow: 0 20px 40px rgba(0,0,0,.4), 0 0 0 1px rgba(255,255,255,.08) inset;
      transform: translateY(-2px);
    }
    .card > * { position: relative; }
    .card h3 { margin: 0 0 18px; font-size: 18px; font-weight: 700; color: var(--text); }
    .category-tools { display: grid; gap: 12px; margin-bottom: 16px; }
    .category-summary { color: var(--muted); font-size: 13px; font-weight: 500; }
    .category-list { overflow-y: auto; padding-right: 8px; min-height: 0; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: rgba(15, 23, 42, .2); border-radius: 999px; }
    ::-webkit-scrollbar-thumb { background: rgba(148, 163, 184, .3); border-radius: 999px; border: 2px solid transparent; background-clip: padding-box; }
    ::-webkit-scrollbar-thumb:hover { background-color: rgba(14, 165, 233, .5); }
    .category-empty { color: var(--muted); padding: 24px 12px; border: 2px dashed rgba(255, 255, 255, .1); border-radius: var(--radius); text-align: center; font-weight: 500; }
    .pager { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 16px 0; color: var(--muted); font-size: 13px; font-weight: 500; }
    .pager button { min-width: 82px; min-height: 36px; padding: 6px 12px; font-size: 13px; }
    .pager select, .pager input { min-height: 36px; padding: 6px 12px; font-size: 13px; }
    .pager .jump-group { display: flex; align-items: center; gap: 6px; }
    .pager .jump-group input { width: 60px; text-align: center; }
    .pager-info { flex: 1; text-align: center; }
    .category {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      padding: 14px 16px;
      margin-bottom: 8px;
      border: 1px solid rgba(148, 163, 184, .15);
      border-radius: var(--radius-sm);
      background: rgba(15, 23, 42, .4);
      color: #e2e8f0;
      text-align: left;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .category:hover { transform: translateY(-2px); border-color: rgba(125, 211, 252, .5); background: rgba(14, 165, 233, .1); box-shadow: 0 4px 12px rgba(14, 165, 233, .1); }
    .category.active { 
      border-color: rgba(167, 139, 250, .8); 
      background: linear-gradient(135deg, rgba(124, 58, 237, .2), rgba(6, 182, 212, .1)); 
      color: #c4b5fd; 
      font-weight: 700; 
      box-shadow: 0 0 0 1px rgba(167,139,250,.2), 0 8px 20px rgba(124,58,237,.2); 
    }
    .category.drop-target { border-color: var(--success); background: rgba(16, 185, 129, .15); color: #a7f3d0; }
    .toolbar {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 24px;
      align-items: stretch;
    }
    .toolbar.card { padding: 20px; align-items: stretch; }
    .toolbar-group {
      display: flex;
      gap: 12px;
      align-items: stretch;
      padding: 6px;
      border-radius: var(--radius-sm);
      background: rgba(0, 0, 0, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.05);
      flex-wrap: wrap;
    }
    .toolbar input, .toolbar select { min-height: 42px; }
    .toolbar textarea { min-height: 42px; }
    input, select, textarea, button {
      border: 1px solid rgba(148, 163, 184, .2);
      border-radius: var(--radius-sm);
      padding: 10px 14px;
      color: var(--text);
      background: rgba(15, 23, 42, .6);
      outline: none;
      font-family: inherit;
      font-size: 14px;
      transition: all 0.2s ease;
    }
    textarea { resize: vertical; line-height: 1.5; }
    input:focus, select:focus, textarea:focus { border-color: rgba(34, 211, 238, .6); box-shadow: 0 0 0 3px rgba(6, 182, 212, .15); background: rgba(15, 23, 42, .9); }
    input::placeholder, textarea::placeholder { color: rgba(148, 163, 184, .5); }
    select { color-scheme: dark; }
    button {
      min-height: 42px;
      min-width: 100px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 10px 20px;
      border-color: transparent;
      border-radius: var(--radius-sm);
      background: linear-gradient(135deg, var(--primary), var(--primary-2));
      color: #ffffff;
      cursor: pointer;
      font-weight: 600;
      box-shadow: 0 4px 14px rgba(14, 165, 233, .2);
    }
    button:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(59, 130, 246, .3); }
    button:active { transform: translateY(0); }
    button.secondary { background: rgba(30, 41, 59, .6); color: #cbd5e1; border-color: rgba(148, 163, 184, .2); box-shadow: none; }
    button.secondary:hover { background: rgba(51, 65, 85, .8); border-color: rgba(148, 163, 184, .4); color: #fff; }
    button.danger { background: linear-gradient(135deg, #ef4444, #f97316); color: white; border-color: transparent; box-shadow: 0 4px 14px rgba(239, 68, 68, .2); }
    button.danger:hover { box-shadow: 0 8px 24px rgba(239, 68, 68, .3); }
    .images { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
    .image-card {
      overflow: hidden;
      display: flex;
      flex-direction: column;
      border: 1px solid rgba(148, 163, 184, .15);
      border-radius: var(--radius);
      background: rgba(15, 23, 42, .5);
      cursor: grab;
      box-shadow: var(--shadow-sm);
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .image-card:hover { transform: translateY(-4px); border-color: rgba(125, 211, 252, .5); box-shadow: 0 12px 30px rgba(6, 182, 212, .15); background: rgba(30, 41, 59, .6); }
    .image-card.dragging { opacity: .5; border-color: var(--primary); transform: scale(0.95); }
    .image-card img { width: 100%; height: 188px; object-fit: contain; background: rgba(2, 6, 23, .4); display: block; border-bottom: 1px solid rgba(255, 255, 255, .05); }
    .image-card .meta { display: flex; flex-direction: column; gap: 10px; padding: 12px; font-size: 13px; word-break: break-all; color: #94a3b8; }
    .image-card .meta label { display: flex; align-items: center; gap: 6px; cursor: pointer; color: #e2e8f0; font-weight: 600; }
    .image-card .meta button { min-height: 34px; padding: 6px 12px; font-size: 12px; }
    .image-card .meta textarea,
    .image-card .meta input,
    .image-card .meta select { width: 100%; margin-top: 6px; }
    .image-card .meta textarea { min-height: 84px; resize: vertical; }
    .image-card .card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
    .image-card .card-title { flex: 1; min-width: 0; }
    .image-card .file-name { display: block; color: #e2e8f0; font-weight: 600; word-break: break-all; }
    .image-card .status-badge {
      flex-shrink: 0;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid rgba(56, 189, 248, .35);
      background: rgba(14, 165, 233, .12);
      color: #7dd3fc;
      font-size: 12px;
      line-height: 1.2;
    }
    .image-card .status-badge.unmanaged {
      border-color: rgba(251, 191, 36, .3);
      background: rgba(234, 179, 8, .12);
      color: #fcd34d;
    }
    .image-card .image-actions,
    .image-card .meta-actions { display: flex; gap: 8px; }
    .image-card .meta-actions button { flex: 1; }
    .image-card .meta-summary {
      display: grid;
      gap: 8px;
      padding: 10px;
      border-radius: var(--radius-sm);
      background: rgba(2, 6, 23, .28);
      border: 1px solid rgba(148, 163, 184, .1);
    }
    .image-card .summary-item strong {
      display: block;
      margin-bottom: 4px;
      color: #cbd5e1;
      font-size: 12px;
      font-weight: 600;
    }
    .image-card .summary-item span {
      display: block;
      color: #94a3b8;
      font-size: 12px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .image-card .meta-editor {
      display: none;
      padding-top: 2px;
      border-top: 1px solid rgba(148, 163, 184, .12);
    }
    .image-card .meta-editor.open { display: block; }
    .image-card .field-label {
      display: block;
      margin-top: 10px;
      margin-bottom: 2px;
      color: #cbd5e1;
      font-size: 12px;
      font-weight: 600;
    }
    .image-select { width: 16px; height: 16px; margin: 0; accent-color: var(--primary-2); cursor: pointer; }
    .info-bar { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .info-item {
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(148, 163, 184, .15);
      border-radius: var(--radius);
      padding: 20px;
      background: linear-gradient(145deg, rgba(15, 23, 42, .6), rgba(30, 41, 59, .4));
      box-shadow: var(--shadow-sm);
      backdrop-filter: blur(12px);
      transition: all 0.3s ease;
    }
    .info-item:hover { box-shadow: 0 12px 30px rgba(6, 182, 212, .15); border-color: rgba(125, 211, 252, .4); transform: translateY(-2px); }
    .info-item::after { content: ""; position: absolute; right: -20px; top: -20px; width: 80px; height: 80px; border-radius: 999px; background: rgba(14, 165, 233, 0.15); filter: blur(20px); }
    .info-item strong { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 8px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
    .access-panel {
      max-width: 440px;
      margin: 10vh auto;
      border: 1px solid rgba(255, 255, 255, .1);
      background: linear-gradient(145deg, rgba(15, 23, 42, .8), rgba(30, 41, 59, .6));
      padding: 32px;
      border-radius: var(--radius-lg);
      box-shadow: 0 24px 60px rgba(0, 0, 0, .6);
      backdrop-filter: blur(24px);
    }
    .access-panel h3 { margin-top: 0; font-size: 24px; color: #f8fafc; font-weight: 800; text-shadow: 0 0 20px rgba(14, 165, 233, .4); }
    .access-panel p { color: #94a3b8; line-height: 1.6; font-size: 14px; margin-bottom: 24px; }
    .access-panel input { width: 100%; margin-bottom: 20px; min-height: 46px; background: rgba(2, 6, 23, .4); }
    .access-panel button { width: 100%; margin-bottom: 12px; }
    .access-panel button.secondary { width: 100%; margin: 0; }
    .hidden { display: none; }
    .result-panel {
      position: fixed;
      bottom: 24px;
      left: 24px;
      width: 400px;
      max-width: calc(100vw - 48px);
      z-index: 9999;
      border: 1px solid rgba(14, 165, 233, .3);
      border-radius: var(--radius);
      background: linear-gradient(135deg, rgba(15, 23, 42, .8), rgba(30, 41, 59, .6));
      box-shadow: 0 12px 40px rgba(0, 0, 0, .4);
      backdrop-filter: blur(12px);
      overflow: hidden;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .result-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid rgba(14, 165, 233, .2);
      background: rgba(14, 165, 233, .05);
      cursor: pointer;
      user-select: none;
    }
    .result-title { font-weight: 700; color: #bae6fd; letter-spacing: 0.05em; font-size: 14px; }
    .result-actions { display: flex; gap: 8px; align-items: center; }
    .result-actions button { min-height: 28px; min-width: 60px; padding: 4px 10px; border-radius: var(--radius-sm); font-size: 12px; }
    .result-panel.compact pre { display: none; }
    .result-panel.compact .result-head { border-bottom: none; }
    .result-panel.empty { opacity: 0; pointer-events: none; transform: translateY(20px); }
    .result-panel.empty .result-head { background: transparent; border-bottom-color: rgba(148, 163, 184, .1); }
    .result-panel.empty .result-title { color: #94a3b8; }
    .result-panel.success { border-color: rgba(16, 185, 129, .4); box-shadow: 0 8px 32px rgba(16, 185, 129, .15); }
    .result-panel.success .result-head { background: rgba(16, 185, 129, .1); color: #a7f3d0; border-bottom-color: rgba(16, 185, 129, .2); }
    .result-panel.success .result-title { color: #a7f3d0; }
    .result-panel.error { border-color: rgba(239, 68, 68, .4); box-shadow: 0 8px 32px rgba(239, 68, 68, .15); }
    .result-panel.error .result-head { background: rgba(239, 68, 68, .1); color: #fca5a5; border-bottom-color: rgba(239, 68, 68, .2); }
    .result-panel.error .result-title { color: #fca5a5; }
    .result-panel.running { border-color: rgba(139, 92, 246, .4); box-shadow: 0 8px 32px rgba(139, 92, 246, .15); }
    .result-panel.running .result-head { background: rgba(139, 92, 246, .1); color: #ddd6fe; border-bottom-color: rgba(139, 92, 246, .2); }
    .result-panel.running .result-title { color: #ddd6fe; }
    .result-time { color: rgba(255, 255, 255, .4); font-size: 12px; white-space: nowrap; margin-top: 4px; }
    .result-panel pre { margin: 0; border: 0; border-radius: 0; background: rgba(2, 6, 23, .4); box-shadow: none; max-height: 240px; color: #e2e8f0; }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid rgba(255, 255, 255, .05);
      background: rgba(2, 6, 23, .6);
      color: #e2e8f0;
      border-radius: var(--radius);
      padding: 16px;
      max-height: 280px;
      overflow: auto;
      font-size: 13px;
      line-height: 1.6;
      font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
    }
    main > h3 { margin: 22px 0 10px; }
    @media (max-width: 900px) {
      main { padding: 14px; }
      header { padding: 16px; }
      header h2 { font-size: 20px; letter-spacing: .04em; }
      header div { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .grid { display: block; }
      .category-panel {
        position: relative;
        top: auto;
        width: auto;
        max-height: 42vh;
        flex: none;
      }
      .category-panel.collapsed {
        width: auto;
        flex-basis: auto;
        padding: 14px;
      }
      .category-panel-header h3,
      .category-panel.collapsed .category-panel-header h3,
      .category-panel-body,
      .category-panel.collapsed .category-panel-body {
        opacity: 1;
        width: auto;
        height: auto;
        margin: 0;
        padding: 0;
        overflow: visible;
        transform: none;
        pointer-events: auto;
      }
      .toggle-sidebar-btn { display: none; }
      .toolbar { flex-direction: column; align-items: stretch; }
      .toolbar.card { padding: 14px; }
      .toolbar textarea { min-width: 0 !important; }
      input, select, textarea, button { width: 100%; }
      .images { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
      .image-card img { height: 132px; }
      .info-bar { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
      .pager { flex-wrap: wrap; justify-content: center; }
      .pager-info { order: -1; flex-basis: 100%; }
      .result-panel { bottom: 10px; left: 10px; width: calc(100vw - 20px); max-width: none; border-radius: 16px; }
      .result-head { align-items: flex-start; flex-direction: column; }
      .result-actions { width: 100%; justify-content: space-between; }
      .result-actions button { width: auto; min-width: 72px; }
    }
    @media (max-width: 520px) {
      main { padding: 10px; }
      .card { padding: 14px; border-radius: 18px; }
      .info-bar { grid-template-columns: 1fr; }
      .images { grid-template-columns: 1fr; }
      button { min-width: 0; }
    }
  </style>
</head>
<body>
  <section id="resultPanel" class="result-panel empty compact">
    <div class="result-head" onclick="toggleResultCompact()">
      <div>
        <div class="result-title">操作结果</div>
        <div id="resultTime" class="result-time">等待操作...</div>
      </div>
      <div class="result-actions">
        <button type="button" class="secondary" onclick="event.stopPropagation(); clearResult()">清空</button>
      </div>
    </div>
    <pre id="result">等待操作...</pre>
  </section>
  <header><h2>表情包统一图库管理</h2><div>路径：__PLUGIN_WEB_BASE__/</div></header>
  <div id="accessPanel" class="access-panel hidden">
    <h3>WebUI 访问验证</h3>
    <p>请输入访问密钥后继续。密钥会保存在当前浏览器本地，仅用于本插件 WebUI 请求。</p>
    <input id="accessKeyInput" type="password" placeholder="访问密钥">
    <button type="button" onclick="saveAccessKey()">进入管理页</button>
    <button type="button" class="secondary" onclick="clearAccessKey()">清除本地密钥</button>
    <pre id="accessMessage"></pre>
  </div>
  <main>
    <div id="hostOverview" class="info-bar"></div>
    <div class="toolbar card">
      <div class="toolbar-group" style="flex: 1; min-width: 320px;">
        <input id="categoryName" placeholder="分类名" style="flex: 1;">
        <textarea id="categoryDesc" placeholder="分类描述" rows="1" style="flex: 2; min-width: 200px;"></textarea>
        <button onclick="saveCategory()">保存</button>
      </div>
      <div class="toolbar-group">
        <button id="syncDefaultButton" class="secondary" onclick="syncDefaultCategories()">同步描述</button>
        <button id="autoClassifyButton" class="secondary" onclick="runAutoClassify()">自动分类</button>
        <button id="deduplicateButton" class="danger" onclick="runDeduplicate()">图库去重</button>
      </div>
      <div class="toolbar-group">
        <select id="syncTask">
          <option value="status">同步状态</option>
          <option value="upload">上传到图床</option>
          <option value="download">从图床下载</option>
          <option value="sync_all">双向同步</option>
          <option value="overwrite_to_remote">本地覆盖云端</option>
          <option value="overwrite_from_remote">云端覆盖本地</option>
        </select>
        <button id="runSyncButton" class="secondary" onclick="runSync()">执行任务</button>
      </div>
    </div>
    <div id="mainGrid" class="grid">
      <section id="categoryPanel" class="card category-panel">
        <div class="category-panel-header">
          <h3>图库分类</h3>
          <button type="button" class="toggle-sidebar-btn" onclick="toggleSidebar(event)" title="展开/收起分类">◀</button>
        </div>
        <div class="category-panel-body">
          <div class="category-tools">
            <input id="categoryFilter" placeholder="搜索分类" oninput="renderCategories()">
            <div id="categorySummary" class="category-summary"></div>
          </div>
          <div id="categories" class="category-list"></div>
        </div>
      </section>
      <section class="card content-panel">
        <h3 id="currentTitle">请选择分类</h3>
        <div class="toolbar">
          <div class="toolbar-group" style="flex: 1; min-width: 280px;">
            <input id="uploadFile" type="file" accept="image/*" style="flex: 1; min-width: 140px;">
            <button type="button" onclick="uploadImage()">上传图片</button>
          </div>
          <div class="toolbar-group">
            <button type="button" class="secondary" onclick="toggleSelectAllImages()">全选/反选</button>
            <select id="targetCategory" style="width: 140px;"></select>
            <button type="button" class="secondary" onclick="moveSelectedImages()">移动</button>
            <button type="button" class="secondary" onclick="copySelectedImages()">复制</button>
          </div>
          <div class="toolbar-group">
            <button type="button" class="danger" onclick="deleteSelectedImages()">删除选中</button>
            <button type="button" class="danger" onclick="clearCategory()">清空当前分类</button>
          </div>
        </div>
        <div id="imagePagerTop" class="pager"></div>
        <div id="images" class="images"></div>
        <div id="imagePagerBottom" class="pager"></div>
      </section>
    </div>
  </main>
<script>
let currentCategory = '';
let originalCategoryName = '';
let categoryItems = [];
let imageItems = [];
let imagePage = 1;
let imagePageSize = 36;
let sidebarCollapsed = false;
const accessKeyRequired = __ACCESS_KEY_REQUIRED__;
const accessKeyFromUrl = new URLSearchParams(window.location.search).get('access_key') || '';
if (accessKeyFromUrl) localStorage.setItem('emotion_webui_access_key', accessKeyFromUrl);
let webuiAccessKey = accessKeyFromUrl || localStorage.getItem('emotion_webui_access_key') || '';

function toggleSidebar(e) {
  if (e) e.stopPropagation();
  sidebarCollapsed = !sidebarCollapsed;
  const panel = document.getElementById('categoryPanel');
  const btn = panel.querySelector('.toggle-sidebar-btn');
  if (sidebarCollapsed) {
    panel.classList.add('collapsed');
  } else {
    panel.classList.remove('collapsed');
  }
}

const api = path => `__PLUGIN_WEB_BASE__${path}`;
function appendAccessKey(url) {
  if (!webuiAccessKey) return url;
  const joiner = url.includes('?') ? '&' : '?';
  return `${url}${joiner}access_key=${encodeURIComponent(webuiAccessKey)}`;
}
function authorizedImageUrl(url) { return appendAccessKey(url); }
function showAccessPanel(message = '') {
  document.body.classList.add('locked');
  document.getElementById('accessPanel').classList.remove('hidden');
  document.getElementById('accessMessage').textContent = message;
}
function hideAccessPanel() {
  document.body.classList.remove('locked');
  document.getElementById('accessPanel').classList.add('hidden');
}
async function saveAccessKey() {
  webuiAccessKey = document.getElementById('accessKeyInput').value.trim();
  localStorage.setItem('emotion_webui_access_key', webuiAccessKey);
  try {
    await requestJson(api('/api/auth/check'));
    hideAccessPanel();
    await boot();
  } catch (e) {
    showAccessPanel(e.detail || '密钥验证失败');
  }
}
function clearAccessKey() {
  webuiAccessKey = '';
  localStorage.removeItem('emotion_webui_access_key');
  showAccessPanel('已清除本地密钥');
}
function formatList(value) {
  if (!Array.isArray(value) || !value.length) return '无';
  return value.join('、');
}
function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
function metadataDomId(filename) {
  return encodeURIComponent(filename);
}
function getImageItem(filename) {
  return imageItems.find(item => item.filename === filename);
}
function formatResult(data) {
  if (typeof data === 'string') return data;
  if (!data || typeof data !== 'object') return String(data);
  if (data.detail) return `操作失败：${data.detail}`;
  if (data.message && Object.keys(data).length <= 2) return data.message;

  const lines = [];
  const statusText = data.status === 'ok' ? '成功' : (data.status || data.result || '已完成');
  lines.push(`操作状态：${statusText}`);
  if (data.name) lines.push(`分类名称：${data.name}`);
  if (data.category) lines.push(`当前分类：${data.category}`);
  if (data.source_category) lines.push(`来源分类：${data.source_category}`);
  if (data.target_category) lines.push(`目标分类：${data.target_category}`);
  if (data.filename) lines.push(`图片文件：${data.filename}`);
  if (data.file_path) lines.push(`保存路径：${data.file_path}`);
  if (data.description) lines.push(`描述：${data.description}`);
  if (data.message) lines.push(`说明：${data.message}`);

  const countLabels = {
    count: '数量',
    category_count: '分类数量',
    image_count: '图片数量',
    local_image_count: '本地图片数量',
    remote_image_count: '云端图片数量',
    processed_count: '处理数量',
    deleted_count: '删除数量',
    missing_count: '缺失数量',
    invalid_count: '无效数量',
    conflict_count: '冲突数量',
    unmanaged_count: '新建元数据数量',
    reindexed_count: '重建索引数量',
    deleted_count: '删除数量',
    processed_count: '处理数量',
    uploaded_count: '上传数量',
    downloaded_count: '下载数量',
    skipped_count: '跳过数量',
    failed_count: '失败数量',
  };
  Object.entries(countLabels).forEach(([key, label]) => {
    if (data[key] !== undefined) lines.push(`${label}：${data[key]}`);
  });

  const listLabels = {
    created_categories: '新增分类',
    added_descriptions: '新增分类描述',
    updated_descriptions: '更新分类描述',
    normalized_categories: '已规范化分类名',
    uploaded: '已上传',
    downloaded: '已下载',
    deleted: '已删除',
    moved: '已移动',
    copied: '已复制',
    missing: '缺失文件',
    invalid: '无效项目',
    conflicts: '冲突文件',
    unmanaged: '已补元数据图片',
    processed: '已处理',
    deleted: '已删除',
    skipped: '已跳过',
    failed: '失败项目',
  };
  Object.entries(listLabels).forEach(([key, label]) => {
    if (Array.isArray(data[key])) lines.push(`${label}：${formatList(data[key])}`);
  });

  const usedKeys = new Set(['status', 'result', 'name', 'category', 'source_category', 'target_category', 'filename', 'file_path', 'description', 'message', ...Object.keys(countLabels), ...Object.keys(listLabels)]);
  const extra = Object.entries(data).filter(([key, value]) => !usedKeys.has(key) && value !== undefined && value !== null && typeof value !== 'object');
  extra.forEach(([key, value]) => lines.push(`${key}：${value}`));
  return lines.join('\\n');
}
function getResultKind(data) {
  if (!data || typeof data !== 'object') return 'success';
  if (data.detail || data.status === 'error' || data.result === 'error') return 'error';
  if (data.status === 'running' || data.result === 'running') return 'running';
  return 'success';
}
function showResult(data) {
  const result = document.getElementById('result');
  const panel = document.getElementById('resultPanel');
  const time = document.getElementById('resultTime');
  const kind = getResultKind(data);
  result.textContent = formatResult(data);
  time.textContent = new Date().toLocaleString();
  panel.classList.remove('empty', 'success', 'error', 'running');
  panel.classList.add(kind);
  if (kind !== 'running') {
    panel.classList.remove('compact');
  }
}
function clearResult() {
  document.getElementById('result').textContent = '等待操作...';
  document.getElementById('resultTime').textContent = '等待操作...';
  const panel = document.getElementById('resultPanel');
  panel.classList.remove('success', 'error', 'running');
  panel.classList.add('empty', 'compact');
}
function toggleResultCompact() {
  document.getElementById('resultPanel').classList.toggle('compact');
}
function setButtonLoading(button, loadingText) {
  if (!button) return;
  button.disabled = true;
  button.dataset.originalText = button.dataset.originalText || button.textContent;
  button.textContent = loadingText;
}
function restoreButton(button, fallbackText) {
  if (!button) return;
  button.disabled = false;
  button.textContent = button.dataset.originalText || fallbackText;
}
async function requestJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (webuiAccessKey) headers.set('X-Emotion-Webui-Key', webuiAccessKey);
  const res = await fetch(appendAccessKey(url), {...options, headers});
  const data = await res.json();
  if (res.status === 403 && accessKeyRequired) showAccessPanel(data.detail || '需要访问密钥');
  if (!res.ok) throw data;
  return data;
}
async function loadHostOverview() {
  const box = document.getElementById('hostOverview');
  try {
    const data = await requestJson(api('/api/image-host/overview'));
    box.innerHTML = `
      <div class="info-item"><strong>图床服务商</strong>${data.provider_name || data.provider || '未知'}</div>
      <div class="info-item"><strong>云端图片数量</strong>${data.remote_image_count ?? 0}</div>
      <div class="info-item"><strong>云端占用空间</strong>${data.remote_total_size_human || '0 B'}</div>
      <div class="info-item"><strong>本地图片数量</strong>${data.local_image_count ?? 0}</div>
      <div class="info-item"><strong>本地占用空间</strong>${data.local_total_size_human || '0 B'}</div>
      <div class="info-item"><strong>待上传</strong>${data.to_upload_count ?? 0}</div>
      <div class="info-item"><strong>待下载</strong>${data.to_download_count ?? 0}</div>
      <div class="info-item"><strong>同步状态</strong>${data.is_synced ? '已同步' : '未同步'}</div>
      <div class="info-item"><strong>状态说明</strong>${data.status_message || '所有修改立即生效，无需重启'}</div>`;
  } catch (e) {
    box.innerHTML = `<div class="info-item"><strong>图床状态</strong>${e.detail || JSON.stringify(e)}</div><div class="info-item"><strong>本地图片数量</strong>请检查接口日志</div><div class="info-item"><strong>实时状态</strong>所有修改立即生效，无需重启</div>`;
  }
}
function clampPage(page, total, pageSize) {
  return Math.max(1, Math.min(page, Math.max(1, Math.ceil(total / pageSize))));
}
function renderPager(topId, bottomId, page, pageSize, total, changeFn, sizeFn) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const start = total ? (page - 1) * pageSize + 1 : 0;
  const end = Math.min(page * pageSize, total);
  const html = `
    <button type="button" class="secondary" onclick="${changeFn}(${page - 1})" ${page <= 1 ? 'disabled' : ''}>上一页</button>
    <span class="pager-info">${start}-${end} / ${total}，第 ${page} / ${pageCount} 页</span>
    <div class="jump-group">
      <input type="number" min="1" max="${pageCount}" placeholder="页码" onkeydown="if(event.key==='Enter') ${changeFn}(this.value)">
      <button type="button" class="secondary" style="min-width: 48px;" onclick="${changeFn}(this.previousElementSibling.value)">跳转</button>
    </div>
    <select onchange="${sizeFn}(this.value)">
      ${[12, 24, 36, 60, 96].map(size => `<option value="${size}" ${size === pageSize ? 'selected' : ''}>每页 ${size}</option>`).join('')}
    </select>
    <button type="button" class="secondary" onclick="${changeFn}(${page + 1})" ${page >= pageCount ? 'disabled' : ''}>下一页</button>`;
  [topId, bottomId].forEach(id => {
    const node = document.getElementById(id);
    if (node) node.innerHTML = total > pageSize ? html : total ? `<span class="pager-info">共 ${total} 项</span>` : '';
  });
}
function slicePage(items, page, pageSize) {
  return items.slice((page - 1) * pageSize, page * pageSize);
}
function setImagePage(page) {
  imagePage = clampPage(page, imageItems.length, imagePageSize);
  renderImages();
}
function setImagePageSize(value) {
  imagePageSize = Number(value) || 36;
  imagePage = 1;
  renderImages();
}
function renderCategories() {
  const box = document.getElementById('categories');
  const summary = document.getElementById('categorySummary');
  const keyword = (document.getElementById('categoryFilter')?.value || '').trim().toLowerCase();
  const filtered = categoryItems.filter(item => item.name.toLowerCase().includes(keyword) || (item.description || '').toLowerCase().includes(keyword));
  box.innerHTML = '';
  summary.textContent = `共 ${categoryItems.length} 个分类，当前显示 ${filtered.length} 个`;
  if (!filtered.length) {
    box.innerHTML = '<div class="category-empty">没有匹配的分类</div>';
    return;
  }
  filtered.forEach(item => {
    const btn = document.createElement('button'); btn.className = `category ${item.name === currentCategory ? 'active' : ''}`;
    btn.textContent = `${item.name} (${item.count})`;
    btn.title = item.description || item.name;
    btn.onclick = () => selectCategory(item.name, item.description);
    btn.ondragover = event => { event.preventDefault(); btn.classList.add('drop-target'); };
    btn.ondragleave = () => btn.classList.remove('drop-target');
    btn.ondrop = async event => {
      event.preventDefault(); btn.classList.remove('drop-target');
      await handleCategoryDrop(item.name, event);
    };
    box.appendChild(btn);
  });
}
async function loadCategories() {
  const data = await requestJson(api('/api/categories'));
  categoryItems = data.categories;
  renderCategories();
  const targetSelect = document.getElementById('targetCategory'); targetSelect.innerHTML = '<option value="">选择目标分类</option>';
  data.categories.forEach(item => {
    if (item.name !== currentCategory) {
      const option = document.createElement('option'); option.value = item.name; option.textContent = item.name;
      targetSelect.appendChild(option);
    }
  });
}
async function selectCategory(name, desc='') {
  currentCategory = name;
  originalCategoryName = name;
  document.getElementById('categoryName').value = name;
  document.getElementById('categoryDesc').value = desc;
  document.getElementById('currentTitle').textContent = `分类：${name}`;
  await loadCategories(); await loadImages();
}
async function loadImages() {
  if (!currentCategory) return;
  const data = await requestJson(api(`/api/categories/${encodeURIComponent(currentCategory)}/images`));
  imageItems = data.images;
  imagePage = 1;
  renderImages();
}
function renderImages() {
  const box = document.getElementById('images'); box.innerHTML = '';
  imagePage = clampPage(imagePage, imageItems.length, imagePageSize);
  renderPager('imagePagerTop', 'imagePagerBottom', imagePage, imagePageSize, imageItems.length, 'setImagePage', 'setImagePageSize');
  if (!imageItems.length) {
    box.innerHTML = '<div class="category-empty">当前分类暂无图片</div>';
    return;
  }
  slicePage(imageItems, imagePage, imagePageSize).forEach(item => {
    const card = document.createElement('div'); card.className = 'image-card'; card.draggable = true;
    card.dataset.filename = item.filename;
    card.ondragstart = event => {
      card.classList.add('dragging');
      const filenames = getSelectedImages().includes(item.filename) ? getSelectedImages() : [item.filename];
      event.dataTransfer.setData('application/json', JSON.stringify({sourceCategory: currentCategory, filenames}));
      event.dataTransfer.effectAllowed = 'copyMove';
    };
    card.ondragend = () => card.classList.remove('dragging');
    const tags = Array.isArray(item.tags) ? item.tags.join(', ') : '';
    const categoryValue = item.category || '未分类';
    const domId = metadataDomId(item.filename);
    const encodedFilename = encodeURIComponent(item.filename);
    const editorButtonText = item.managed ? '编辑表情元数据' : '添加表情元数据';
    card.innerHTML = `
      <img src="${authorizedImageUrl(item.url)}" loading="lazy">
      <div class="meta">
        <div class="card-top">
          <label class="card-title">
            <input type="checkbox" class="image-select" value="${escapeHtml(item.filename)}">
            <span class="file-name">${escapeHtml(item.filename)}</span>
          </label>
          <span class="status-badge ${item.managed ? '' : 'unmanaged'}">${item.managed ? '已建元数据' : '未建元数据'}</span>
        </div>
        <div class="meta-summary">
          <div class="summary-item">
            <strong>分类</strong>
            <span>${escapeHtml(categoryValue)}</span>
          </div>
          <div class="summary-item">
            <strong>描述</strong>
            <span>${escapeHtml(item.description || '暂无描述')}</span>
          </div>
          <div class="summary-item">
            <strong>标签</strong>
            <span>${escapeHtml(tags || '暂无标签')}</span>
          </div>
        </div>
        <div class="image-actions">
          <button type="button" class="secondary" onclick="toggleEmotionEditor(decodeURIComponent('${encodedFilename}'))">${editorButtonText}</button>
          <button type="button" class="danger" onclick="deleteImage(decodeURIComponent('${encodedFilename}'))">删除</button>
        </div>
        <div id="editor_${domId}" class="meta-editor">
          <label class="field-label" for="desc_${domId}">表情描述</label>
          <textarea id="desc_${domId}" placeholder="请输入表情描述">${escapeHtml(item.description || '')}</textarea>
          <label class="field-label" for="tags_${domId}">标签</label>
          <input id="tags_${domId}" value="${escapeHtml(tags)}" placeholder="标签，逗号分隔">
          <label class="field-label" for="cat_${domId}">分类</label>
          <select id="cat_${domId}">
            ${categoryItems.map(cat => `<option value="${escapeHtml(cat.name)}" ${cat.name === categoryValue ? 'selected' : ''}>${escapeHtml(cat.name)}</option>`).join('')}
          </select>
          <div class="meta-actions">
            <button type="button" onclick="saveImageMetadata(decodeURIComponent('${encodedFilename}'))">保存元数据</button>
            <button type="button" class="secondary" onclick="toggleEmotionEditor(decodeURIComponent('${encodedFilename}'), false)">收起</button>
          </div>
        </div>
      </div>`;
    box.appendChild(card);
  });
}
function toggleEmotionEditor(filename, forceOpen = null) {
  const domId = metadataDomId(filename);
  const editor = document.getElementById(`editor_${domId}`);
  if (!editor) return;
  const shouldOpen = forceOpen === null ? !editor.classList.contains('open') : !!forceOpen;
  editor.classList.toggle('open', shouldOpen);
}
async function saveImageMetadata(filename) {
  const item = getImageItem(filename);
  if (!item) return showResult('未找到当前图片数据');
  const domId = metadataDomId(filename);
  const description = document.getElementById(`desc_${domId}`).value.trim();
  const tags = document.getElementById(`tags_${domId}`).value;
  const category = document.getElementById(`cat_${domId}`).value;
  const requestPath = item.emotion_id
    ? api(`/api/emotions/${encodeURIComponent(item.emotion_id)}`)
    : api(`/api/emotions/by_file/${encodeURIComponent(filename)}`);
  const data = await requestJson(requestPath, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({description, tags, category})
  });
  showResult(data);
  toggleEmotionEditor(filename, false);
  await refreshCurrentView();
}
async function saveCategory() {
  const name = document.getElementById('categoryName').value.trim(); const description = document.getElementById('categoryDesc').value.trim();
  const data = await requestJson(api('/api/categories'), { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({original_name: originalCategoryName, name, description}) });
  showResult(data); currentCategory = name; originalCategoryName = name; await loadCategories(); await loadImages(); await loadHostOverview();
}
async function syncDefaultCategories() {
  const button = document.getElementById('syncDefaultButton');
  setButtonLoading(button, '同步中...');
  showResult('正在同步图库类别描述，会按配置项的键作为分类名、值作为分类描述。');
  try {
    const data = await requestJson(api('/api/categories/sync_defaults'), { method: 'POST' });
    showResult(data);
    await loadCategories();
    await loadHostOverview();
  } catch (e) {
    showResult(e);
  } finally {
    restoreButton(button, '同步图库类别描述');
  }
}
async function uploadImage() {
  if (!currentCategory) return showResult('请先选择分类');
  const file = document.getElementById('uploadFile').files[0]; if (!file) return showResult('请选择图片');
  const form = new FormData(); form.append('file', file);
  const data = await requestJson(api(`/api/categories/${encodeURIComponent(currentCategory)}/images`), { method: 'POST', body: form });
  showResult(data); await loadCategories(); await loadImages(); await loadHostOverview();
}
async function refreshCurrentView() {
  await loadCategories(); await loadImages(); await loadHostOverview();
}
async function deleteImage(filename) {
  if (!confirm(`删除 ${filename}？`)) return;
  const data = await requestJson(api(`/api/categories/${encodeURIComponent(currentCategory)}/images/${encodeURIComponent(filename)}`), { method: 'DELETE' });
  showResult(data); await refreshCurrentView();
}
function getSelectedImages() {
  return Array.from(document.querySelectorAll('.image-select:checked')).map(item => item.value);
}
function getTargetCategory() {
  return document.getElementById('targetCategory').value;
}
async function batchTransferImages(action, targetCategory, filenames = null, sourceCategory = currentCategory) {
  const selected = filenames || getSelectedImages();
  if (!sourceCategory) return showResult('请先选择来源分类');
  if (!targetCategory) return showResult('请选择目标分类');
  if (!selected.length) return showResult('请先选择图片');
  if (sourceCategory === targetCategory) return showResult('来源分类和目标分类不能相同');
  const label = action === 'batch_move' ? '移动' : '复制';
  if (!confirm(`${label} ${selected.length} 张图片到 ${targetCategory}？`)) return;
  const data = await requestJson(api(`/api/categories/${encodeURIComponent(sourceCategory)}/images/${action}`), {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({target_category: targetCategory, filenames: selected})
  });
  showResult(data); await refreshCurrentView();
}
async function moveSelectedImages() {
  await batchTransferImages('batch_move', getTargetCategory());
}
async function copySelectedImages() {
  await batchTransferImages('batch_copy', getTargetCategory());
}
async function handleCategoryDrop(targetCategory, event) {
  const raw = event.dataTransfer.getData('application/json');
  if (!raw) return;
  const data = JSON.parse(raw);
  await batchTransferImages(event.ctrlKey ? 'batch_copy' : 'batch_move', targetCategory, data.filenames, data.sourceCategory);
}
function toggleSelectAllImages() {
  const boxes = Array.from(document.querySelectorAll('.image-select'));
  const shouldSelect = boxes.some(item => !item.checked);
  boxes.forEach(item => { item.checked = shouldSelect; });
}
async function deleteSelectedImages() {
  const filenames = getSelectedImages();
  if (!currentCategory) return showResult('请先选择分类');
  if (!filenames.length) return showResult('请先选择要删除的图片');
  if (!confirm(`删除选中的 ${filenames.length} 张图片？`)) return;
  const data = await requestJson(api(`/api/categories/${encodeURIComponent(currentCategory)}/images/batch_delete`), {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filenames})
  });
  showResult(data); await refreshCurrentView();
}
async function clearCategory() {
  if (!currentCategory || !confirm(`清空分类 ${currentCategory}？`)) return;
  const data = await requestJson(api(`/api/categories/${encodeURIComponent(currentCategory)}/clear`), { method: 'POST' });
  showResult(data); await refreshCurrentView();
}
async function runDeduplicate() {
  const button = document.getElementById('deduplicateButton');
  if (!confirm('将按文件内容 MD5 扫描图库，删除重复图片并同步清理元数据和向量索引。继续？')) return;
  setButtonLoading(button, '去重中...');
  showResult('图库去重执行中：正在扫描重复图片，并同步清理元数据和向量索引。');
  try {
    const data = await requestJson(api('/api/emotions/deduplicate'), { method: 'POST' });
    showResult(data);
    await refreshCurrentView();
  } catch (e) {
    showResult(e);
  } finally {
    restoreButton(button, '图库去重');
  }
}
async function runAutoClassify() {
  const button = document.getElementById('autoClassifyButton');
  if (!confirm('将调用视觉模型为未分类或缺少描述的表情补全元数据，并写入向量数据库。继续？')) return;
  setButtonLoading(button, '分类中...');
  showResult('自动化分类执行中：正在调用视觉模型识别图片、补全描述和分类，并写入向量数据库。');
  try {
    const data = await requestJson(api('/api/emotions/auto_classify'), { method: 'POST' });
    showResult(data);
    await refreshCurrentView();
  } catch (e) {
    showResult(e);
  } finally {
    restoreButton(button, '自动化分类');
  }
}
async function runSync() {
  const task = document.getElementById('syncTask').value;
  const button = document.getElementById('runSyncButton');
  const taskLabel = document.getElementById('syncTask').selectedOptions[0]?.textContent || task;
  setButtonLoading(button, '执行中...');
  showResult(`图床任务「${taskLabel}」执行中，请稍候。任务完成后会自动刷新图床状态和图库分类。`);
  try {
    const data = await requestJson(api(`/api/image-host/${task}`), { method: 'POST' });
    showResult(data);
    await refreshCurrentView();
  } catch (e) {
    showResult(e);
  } finally {
    restoreButton(button, '执行图床任务');
  }
}
async function boot() {
  if (accessKeyRequired) {
    try {
      await requestJson(api('/api/auth/check'));
      hideAccessPanel();
    } catch (e) {
      showAccessPanel(e.detail || '请输入访问密钥');
      return;
    }
  }
  await Promise.all([loadCategories(), loadHostOverview()]);
  if (!currentCategory && categoryItems.length) await selectCategory(categoryItems[0].name, categoryItems[0].description);
}
boot().catch(showResult);
</script>
</body>
</html>
        """
        html_content = html_content.replace(
            "__ACCESS_KEY_REQUIRED__",
            "true" if is_webui_access_key_enabled() else "false",
        ).replace(
            "__PLUGIN_WEB_BASE__",
            plugin_web_base,
        )
        response = HTMLResponse(content=html_content)
        access_key = get_webui_access_key_from_request(request)
        if verify_webui_access_key(access_key) and access_key:
            response.set_cookie(
                key="emotion_webui_access_key",
                value=access_key,
                httponly=True,
                samesite="strict",
            )
        return response

    @router.get("/api/auth/check", summary="校验 WebUI 访问密钥")
    async def api_auth_check(access_key: Optional[str] = Query(None), x_emotion_webui_key: Optional[str] = Header(None)):
        require_webui_access_key(access_key or x_emotion_webui_key)
        return {"status": "ok", "enabled": is_webui_access_key_enabled()}

    @router.get("/api/categories", summary="获取分类列表", dependencies=[Depends(webui_auth_dependency)])
    async def api_categories():
        descriptions = sync_category_descriptions_with_filesystem()
        emotion_store = await load_emotion_store()
        stats = get_category_stats_from_store(emotion_store, descriptions)
        categories = [
            {"name": name, "description": description, "count": stats.get(name, 0)}
            for name, description in descriptions.items()
        ]
        if "未分类" not in descriptions and stats.get("未分类", 0) > 0:
            categories.append({"name": "未分类", "description": "尚未设置分类元数据的图片", "count": stats.get("未分类", 0)})
        return {"categories": categories}

    @router.post("/api/categories/sync_defaults", summary="同步图库类别描述", dependencies=[Depends(webui_auth_dependency)])
    async def api_sync_default_categories():
        return sync_default_category_descriptions_to_filesystem()

    @router.post("/api/categories", summary="保存分类描述", dependencies=[Depends(webui_auth_dependency)])
    async def api_save_category(payload: Dict[str, str]):
        original_name = _safe_category_name(payload.get("original_name", ""))
        name = _safe_category_name(payload.get("name", ""))
        description = payload.get("description", "").strip()
        if not name or not description:
            raise HTTPException(status_code=400, detail="分类和描述不能为空")
        descriptions = sync_category_descriptions_with_filesystem()
        if original_name and original_name != name:
            if name in descriptions:
                raise HTTPException(status_code=400, detail="目标分类已存在")
            descriptions.pop(original_name, None)
        descriptions[name] = description
        save_category_descriptions(descriptions)
        return {"status": "ok", "name": name, "description": description, "realtime": True}

    @router.get("/api/emotions", summary="获取表情元数据列表", dependencies=[Depends(webui_auth_dependency)])
    async def api_emotions(category: Optional[str] = None):
        emotion_store = await load_emotion_store()
        safe_category = _safe_category_name(category) if category else None
        items = []
        for emotion_id, metadata in emotion_store.emotions.items():
            if safe_category and metadata.category != safe_category:
                continue
            file_path = resolve_emotion_file_path(metadata.file_path)
            items.append(
                {
                    "id": emotion_id,
                    "description": metadata.description,
                    "tags": metadata.tags,
                    "category": metadata.category,
                    "file_path": metadata.file_path,
                    "exists": file_path.exists(),
                    "url": f"{plugin_web_base}/emotions/{emotion_id}" if file_path.exists() else "",
                    "last_updated": metadata.last_updated,
                },
            )
        items.sort(key=lambda item: item["last_updated"], reverse=True)
        return {"emotions": items}

    @router.post("/api/emotions/deduplicate", summary="手动执行图库去重", dependencies=[Depends(webui_auth_dependency)])
    async def api_deduplicate_emotions():
        return await deduplicate_gallery_images()

    @router.post("/api/emotions/auto_classify", summary="自动化补全表情描述与分类", dependencies=[Depends(webui_auth_dependency)])
    async def api_auto_classify_emotions():
        try:
            return await auto_classify_gallery_emotions()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.post("/api/emotions/{emotion_id}", summary="实时更新表情描述和标签", dependencies=[Depends(webui_auth_dependency)])
    async def api_update_emotion(emotion_id: str, payload: Dict[str, Any]):
        description = str(payload.get("description", "")).strip()
        tags_value = payload.get("tags", [])
        if isinstance(tags_value, str):
            tags = [tag.strip() for tag in tags_value.split(",") if tag.strip()]
        elif isinstance(tags_value, list):
            tags = [str(tag).strip() for tag in tags_value if str(tag).strip()]
        else:
            raise HTTPException(status_code=400, detail="tags 必须是列表或逗号分隔字符串")
        category = payload.get("category")
        try:
            metadata = await update_emotion_metadata_realtime(emotion_id, description, tags, str(category) if category else None)
            return {"status": "ok", "id": emotion_id, "metadata": metadata.model_dump(), "realtime": True}
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.post("/api/emotions/by_file/{filename}", summary="按图片文件创建或更新表情元数据", dependencies=[Depends(webui_auth_dependency)])
    async def api_upsert_emotion_by_file(filename: str, payload: Dict[str, Any]):
        description = str(payload.get("description", "")).strip()
        tags_value = payload.get("tags", [])
        if isinstance(tags_value, str):
            tags = [tag.strip() for tag in tags_value.split(",") if tag.strip()]
        elif isinstance(tags_value, list):
            tags = [str(tag).strip() for tag in tags_value if str(tag).strip()]
        else:
            raise HTTPException(status_code=400, detail="tags 必须是列表或逗号分隔字符串")
        category = payload.get("category")
        try:
            emotion_id, metadata, created = await upsert_emotion_metadata_by_filename(
                filename=filename,
                description=description,
                tags=tags,
                category=str(category) if category else None,
            )
            return {
                "status": "ok",
                "id": emotion_id,
                "filename": Path(filename).name,
                "metadata": metadata.model_dump(),
                "message": "已创建表情元数据" if created else "已更新表情元数据",
                "created": created,
                "realtime": True,
            }
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.get("/emotions/{image_key}", summary="访问表情包图片", dependencies=[Depends(webui_auth_dependency)])
    async def api_serve_emotion(image_key: str):
        emotion_store = await load_emotion_store()
        metadata = emotion_store.get_emotion(image_key)
        if metadata:
            file_path = resolve_emotion_file_path(metadata.file_path)
        else:
            safe_filename = Path(image_key).name
            file_path = store_dir / safe_filename
        if not file_path.exists() or not _is_supported_image_file(file_path):
            raise HTTPException(status_code=404, detail="表情包图片不存在")
        return Response(content=file_path.read_bytes(), media_type="image/*")

    @router.get("/api/categories/{category}/images", summary="获取分类图片", dependencies=[Depends(webui_auth_dependency)])
    async def api_category_images(category: str):
        safe_category = _safe_category_name(category)
        emotion_store = await load_emotion_store()
        return {
            "category": safe_category,
            "images": get_category_image_items_from_store(emotion_store, safe_category),
        }

    @router.post("/api/categories/{category}/images", summary="上传分类图片", dependencies=[Depends(webui_auth_dependency)])
    async def api_upload_image(category: str, file: UploadFile = File(...)):
        if not emotion_config.WEB_MANAGER_ENABLE_UPLOAD:
            raise HTTPException(status_code=403, detail="Web 上传已禁用")
        try:
            target_path = await save_upload_file_to_gallery(file, category)
            return {"status": "ok", "filename": target_path.name, "path": str(target_path)}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.post("/api/categories/{category}/images/batch_copy", summary="批量复制分类图片", dependencies=[Depends(webui_auth_dependency)])
    async def api_batch_copy_images(category: str, payload: Dict[str, Any]):
        target_category = _safe_category_name(str(payload.get("target_category", "")))
        filenames = payload.get("filenames", [])
        if not isinstance(filenames, list) or not filenames:
            raise HTTPException(status_code=400, detail="filenames 不能为空")
        if not target_category:
            raise HTTPException(status_code=400, detail="target_category 不能为空")
        try:
            return copy_or_move_gallery_images(category, target_category, filenames, move=False)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.post("/api/categories/{category}/images/batch_move", summary="批量移动分类图片", dependencies=[Depends(webui_auth_dependency)])
    async def api_batch_move_images(category: str, payload: Dict[str, Any]):
        target_category = _safe_category_name(str(payload.get("target_category", "")))
        filenames = payload.get("filenames", [])
        if not isinstance(filenames, list) or not filenames:
            raise HTTPException(status_code=400, detail="filenames 不能为空")
        if not target_category:
            raise HTTPException(status_code=400, detail="target_category 不能为空")
        if _safe_category_name(category) == target_category:
            raise HTTPException(status_code=400, detail="来源分类和目标分类不能相同")

        emotion_store = await load_emotion_store()
        moved = []
        missing = []
        unmanaged = []
        invalid = []
        filename_set = {Path(str(filename)).name for filename in filenames if Path(str(filename)).name}
        for raw_filename in filenames:
            safe_filename = Path(str(raw_filename)).name
            if not safe_filename:
                invalid.append(str(raw_filename))
                continue
            matched = False
            for emotion_id, metadata in emotion_store.emotions.items():
                file_path = resolve_emotion_file_path(metadata.file_path)
                if file_path.exists() and file_path.name == safe_filename:
                    metadata.category = target_category
                    if target_category not in metadata.tags:
                        metadata.tags = [*metadata.tags, target_category]
                    metadata.last_updated = int(time.time())
                    emotion_store.add_emotion(emotion_id, metadata)
                    moved.append(safe_filename)
                    matched = True
                    break
            if not matched:
                image_path = store_dir / safe_filename
                if image_path.exists() and _is_supported_image_file(image_path):
                    emotion_id = generate_emotion_id(image_path.name, image_path.stem)
                    metadata = EmotionMetadata.create(
                        description=image_path.stem,
                        tags=[target_category],
                        source_path=str(image_path),
                        file_path=image_path.name,
                        category=target_category,
                    )
                    emotion_store.add_emotion(emotion_id, metadata)
                    moved.append(safe_filename)
                    unmanaged.append(safe_filename)
                else:
                    missing.append(safe_filename)
        if moved:
            await save_emotion_store(emotion_store)
            for emotion_id, metadata in emotion_store.emotions.items():
                if get_emotion_file_name(metadata.file_path) in filename_set:
                    try:
                        await upsert_emotion_vector(emotion_id, metadata)
                    except Exception as e:
                        logger.warning(f"更新移动后表情向量失败: {emotion_id}, {e}")
        return {
            "status": "ok",
            "source_category": _safe_category_name(category),
            "target_category": target_category,
            "moved": moved,
            "unmanaged": unmanaged,
            "missing": missing,
            "invalid": invalid,
            "processed_count": len(moved),
            "unmanaged_count": len(unmanaged),
            "missing_count": len(missing),
            "invalid_count": len(invalid),
            "message": "未建立元数据的图片已创建元数据并归类" if unmanaged else "分类元数据已更新",
        }

    @router.post("/api/categories/{category}/images/batch_delete", summary="批量删除分类图片", dependencies=[Depends(webui_auth_dependency)])
    async def api_batch_delete_images(category: str, payload: Dict[str, List[str]]):
        safe_category = _safe_category_name(category)
        filenames = payload.get("filenames", [])
        if not isinstance(filenames, list) or not filenames:
            raise HTTPException(status_code=400, detail="filenames 不能为空")

        emotion_store = await load_emotion_store()
        deleted = []
        missing = []
        invalid = []
        deleted_ids = []
        for filename in filenames:
            safe_filename = Path(str(filename)).name
            if not safe_filename:
                invalid.append(str(filename))
                continue
            target_path = store_dir / safe_filename
            if not target_path.exists() or not _is_supported_image_file(target_path):
                missing.append(safe_filename)
                continue
            for emotion_id, metadata in list(emotion_store.emotions.items()):
                if get_emotion_file_name(metadata.file_path) == safe_filename:
                    emotion_store.emotions.pop(emotion_id, None)
                    deleted_ids.append(emotion_id)
                    break
            target_path.unlink()
            deleted.append(safe_filename)

        if deleted_ids:
            emotion_store.recent_emotion_ids = [emotion_id for emotion_id in emotion_store.recent_emotion_ids if emotion_id not in deleted_ids]
            await save_emotion_store(emotion_store)
            try:
                client = await get_qdrant_client()
                if client is not None:
                    await client.delete(
                        collection_name=plugin.get_vector_collection_name(),
                        points_selector=qdrant_models.PointIdsList(points=[int(emotion_id, 16) for emotion_id in deleted_ids]),
                    )
            except Exception as e:
                logger.warning(f"批量删除Qdrant中的表情点失败: {e}")

        return {
            "status": "ok",
            "category": safe_category,
            "deleted": deleted,
            "missing": missing,
            "invalid": invalid,
            "deleted_count": len(deleted),
            "missing_count": len(missing),
            "invalid_count": len(invalid),
        }

    @router.delete("/api/categories/{category}/images/{filename}", summary="删除分类图片", dependencies=[Depends(webui_auth_dependency)])
    async def api_delete_image(category: str, filename: str):
        safe_filename = Path(filename).name
        target_path = store_dir / safe_filename
        if not target_path.exists() or not _is_supported_image_file(target_path):
            raise HTTPException(status_code=404, detail="图片不存在")
        emotion_store = await load_emotion_store()
        deleted_id = ""
        for emotion_id, metadata in list(emotion_store.emotions.items()):
            if get_emotion_file_name(metadata.file_path) == safe_filename:
                emotion_store.emotions.pop(emotion_id, None)
                deleted_id = emotion_id
                break
        if deleted_id:
            emotion_store.recent_emotion_ids = [emotion_id for emotion_id in emotion_store.recent_emotion_ids if emotion_id != deleted_id]
            await save_emotion_store(emotion_store)
            try:
                client = await get_qdrant_client()
                if client is not None:
                    await client.delete(
                        collection_name=plugin.get_vector_collection_name(),
                        points_selector=qdrant_models.PointIdsList(points=[int(deleted_id, 16)]),
                    )
            except Exception as e:
                logger.warning(f"删除Qdrant中的表情点失败: {e}")
        target_path.unlink()
        return {"status": "ok", "filename": safe_filename}

    @router.post("/api/categories/{category}/clear", summary="清空分类图片", dependencies=[Depends(webui_auth_dependency)])
    async def api_clear_category(category: str):
        safe_category = _safe_category_name(category)
        emotion_store = await load_emotion_store()
        deleted = []
        deleted_ids = []
        if safe_category == "未分类":
            managed_files = {get_emotion_file_name(metadata.file_path) for metadata in emotion_store.emotions.values()}
            for image_path in list(store_dir.iterdir()):
                if _is_supported_image_file(image_path) and image_path.name not in managed_files:
                    image_path.unlink(missing_ok=True)
                    deleted.append(image_path.name)
        for emotion_id, metadata in list(emotion_store.emotions.items()):
            if get_emotion_storage_category(metadata.category) != safe_category:
                continue
            file_path = resolve_emotion_file_path(metadata.file_path)
            if file_path.exists() and _is_supported_image_file(file_path):
                file_path.unlink(missing_ok=True)
                deleted.append(file_path.name)
            emotion_store.emotions.pop(emotion_id, None)
            deleted_ids.append(emotion_id)
        if deleted_ids:
            emotion_store.recent_emotion_ids = [emotion_id for emotion_id in emotion_store.recent_emotion_ids if emotion_id not in deleted_ids]
            await save_emotion_store(emotion_store)
            try:
                client = await get_qdrant_client()
                if client is not None:
                    await client.delete(
                        collection_name=plugin.get_vector_collection_name(),
                        points_selector=qdrant_models.PointIdsList(points=[int(emotion_id, 16) for emotion_id in deleted_ids]),
                    )
            except Exception as e:
                logger.warning(f"清空分类时删除Qdrant中的表情点失败: {e}")
        return {"status": "ok", "category": safe_category, "deleted": deleted}

    @router.get("/api/image-host/overview", summary="获取图床概览", dependencies=[Depends(webui_auth_dependency)])
    async def api_image_host_overview():
        try:
            return await asyncio.to_thread(get_image_host_overview)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.post("/api/image-host/{task}", summary="执行图床同步任务", dependencies=[Depends(webui_auth_dependency)])
    async def api_image_host_task(task: str):
        try:
            return await run_image_sync_task(task)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    return router


# endregion: Web 管理路由


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
