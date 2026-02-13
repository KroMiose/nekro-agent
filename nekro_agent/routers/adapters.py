from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from nekro_agent.adapters import ADAPTER_DICT, loaded_adapters
from nekro_agent.adapters.interface.base import AdapterMetadata
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import NotFoundError, OperationFailedError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role


class AdapterInfo(BaseModel):
    """适配器信息"""

    key: str
    name: str
    description: str
    status: str  # loaded, failed, disabled
    config_class: str
    chat_key_rules: List[str]
    has_config: bool
    version: str = ""
    author: str = ""
    tags: List[str] = Field(default_factory=list)


class AdapterDetailInfo(AdapterInfo):
    """适配器详细信息"""

    config_path: str
    has_router: bool
    router_prefix: str


class AdapterStatus(BaseModel):
    status: str
    loaded: bool
    initialized: bool
    has_config: bool
    config_file_exists: bool | None = None
    error_message: str | None = None


class AdapterDocs(BaseModel):
    content: str
    exists: bool


router = APIRouter(prefix="/adapters", tags=["Adapters"])


@router.get("/list", summary="获取所有适配器列表")
@require_role(Role.User)
async def get_adapters_list(_current_user: DBUser = Depends(get_current_active_user)) -> List[AdapterInfo]:
    """获取所有适配器的基本信息列表"""
    adapters: List[AdapterInfo] = []

    for adapter_key in ADAPTER_DICT:
        adapter_instance = loaded_adapters.get(adapter_key)

        if adapter_instance:
            status = "loaded"
            config_class = adapter_instance.config.__class__.__name__
            chat_key_rules = adapter_instance.chat_key_rules
            has_config = hasattr(adapter_instance, "config") and adapter_instance.config is not None
            metadata = adapter_instance.metadata
        else:
            status = "failed"
            config_class = "Unknown"
            chat_key_rules = []
            has_config = False
            metadata = AdapterMetadata(
                name=adapter_key.replace("_", " ").title(),
                description=f"{adapter_key} 适配器",
            )

        adapters.append(
            AdapterInfo(
                key=adapter_key,
                name=metadata.name,
                description=metadata.description,
                status=status,
                config_class=config_class,
                chat_key_rules=chat_key_rules,
                has_config=has_config,
                version=metadata.version,
                author=metadata.author,
                tags=metadata.tags,
            ),
        )

    return adapters


@router.get("/{adapter_key}/info", summary="获取指定适配器详细信息")
@require_role(Role.User)
async def get_adapter_info(
    adapter_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> AdapterDetailInfo:
    """获取指定适配器的详细信息"""
    if adapter_key not in ADAPTER_DICT:
        raise NotFoundError(resource="适配器")

    adapter_instance = loaded_adapters.get(adapter_key)

    if not adapter_instance:
        metadata = AdapterMetadata(
            name=adapter_key.replace("_", " ").title(),
            description=f"{adapter_key} 适配器",
        )
        return AdapterDetailInfo(
            key=adapter_key,
            name=metadata.name,
            description=metadata.description,
            status="failed",
            config_class="Unknown",
            chat_key_rules=[],
            has_config=False,
            config_path="",
            has_router=False,
            router_prefix="",
            version=metadata.version,
            author=metadata.author,
            tags=metadata.tags,
        )

    metadata = adapter_instance.metadata
    return AdapterDetailInfo(
        key=adapter_key,
        name=metadata.name,
        description=metadata.description,
        status="loaded",
        config_class=adapter_instance.config.__class__.__name__,
        chat_key_rules=adapter_instance.chat_key_rules,
        has_config=hasattr(adapter_instance, "config") and adapter_instance.config is not None,
        config_path=str(adapter_instance.config_path),
        has_router=hasattr(adapter_instance, "router"),
        router_prefix=f"/api/adapters/{adapter_key}",
        version=metadata.version,
        author=metadata.author,
        tags=metadata.tags,
    )


@router.get("/{adapter_key}/status", summary="获取适配器状态")
@require_role(Role.User)
async def get_adapter_status(
    adapter_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> AdapterStatus:
    """获取指定适配器的运行状态"""
    if adapter_key not in ADAPTER_DICT:
        raise NotFoundError(resource="适配器")

    adapter_instance = loaded_adapters.get(adapter_key)

    if not adapter_instance:
        return AdapterStatus(
            status="failed",
            loaded=False,
            initialized=False,
            has_config=False,
            error_message="适配器加载失败",
        )

    return AdapterStatus(
        status="loaded",
        loaded=True,
        initialized=True,
        has_config=hasattr(adapter_instance, "config") and adapter_instance.config is not None,
        config_file_exists=(
            adapter_instance.config_path.exists() if hasattr(adapter_instance, "config_path") else False
        ),
    )


@router.get("/{adapter_key}/docs", summary="获取适配器说明文档")
@require_role(Role.User)
async def get_adapter_docs(
    adapter_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> AdapterDocs:
    """获取指定适配器的说明文档"""
    if adapter_key not in ADAPTER_DICT:
        raise NotFoundError(resource="适配器")

    adapter_dir = Path(__file__).parent.parent / "adapters" / adapter_key
    docs_file = adapter_dir / "README.md"

    if not docs_file.exists():
        return AdapterDocs(content="", exists=False)

    try:
        content = docs_file.read_text(encoding="utf-8")
        return AdapterDocs(content=content, exists=True)
    except UnicodeDecodeError:
        try:
            content = docs_file.read_text(encoding="gbk")
            return AdapterDocs(content=content, exists=True)
        except UnicodeDecodeError as e:
            raise OperationFailedError(operation="读取适配器文档") from e
