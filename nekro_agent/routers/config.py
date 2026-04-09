import asyncio
import time
from typing import Any, Dict, List, Optional, get_args

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from nekro_agent.core.config import ModelConfigGroup, config, save_config
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import (
    ConfigInvalidError,
    ConfigNotFoundError,
    DefaultModelGroupDeleteError,
    ModelGroupNotFoundError,
    OperationFailedError,
)
from nekro_agent.services.config_service import UnifiedConfigService
from nekro_agent.services.model_test import (
    build_model_test_messages,
    build_openai_embedding_test_params,
    build_openai_model_test_params,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.tools.common_util import get_app_version


class BatchUpdateConfig(BaseModel):
    """批量更新配置请求体"""

    configs: Dict[str, str]


class ActionResponse(BaseModel):
    """简单操作响应"""

    ok: bool = True


class ConfigInfo(BaseModel):
    """配置基本信息"""

    config_key: str
    config_class: str
    config_file_path: Optional[str] = None
    config_type: str
    field_count: int


class ConfigItem(BaseModel):
    """配置项信息"""

    model_config = ConfigDict(extra="allow")

    key: str
    value: Any
    title: str
    description: Optional[str] = None
    placeholder: Optional[str] = None
    type: str
    is_complex: Optional[bool] = None
    element_type: Optional[str] = None
    key_type: Optional[str] = None
    value_type: Optional[str] = None
    field_schema: Optional[Dict[str, Any]] = None
    enum: Optional[List[str]] = None
    is_secret: Optional[bool] = None
    is_textarea: Optional[bool] = None
    ref_model_groups: Optional[bool] = None
    ref_presets: Optional[bool] = None
    ref_presets_multiple: Optional[bool] = None
    is_hidden: Optional[bool] = None
    required: Optional[bool] = None
    model_type: Optional[str] = None
    sub_item_name: Optional[str] = None
    enable_toggle: Optional[str] = None
    overridable: Optional[bool] = None
    is_need_restart: Optional[bool] = None
    i18n_title: Optional[Dict[str, str]] = None
    i18n_description: Optional[Dict[str, str]] = None
    i18n_category: Optional[Dict[str, str]] = None


class ModelTypeOption(BaseModel):
    """模型类型描述"""

    value: str
    label: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class FetchModelsRequest(BaseModel):
    """服务端拉取模型列表请求。"""

    base_url: str
    api_key: str
    proxy_url: Optional[str] = None


class FetchModelsResponse(BaseModel):
    """服务端拉取模型列表响应。"""

    models: List[str]


class ModelGroupTestItem(BaseModel):
    """基础模型组检测结果。"""

    group_name: str
    model_name: str
    success: bool
    latency_ms: int
    used_model: Optional[str] = None
    response_text: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: Optional[str] = None


class ModelGroupTestRequest(BaseModel):
    """基础模型组检测请求。"""

    group_names: List[str]


class ModelGroupInlineTestRequest(BaseModel):
    """基础模型组 inline 检测请求（直接传入配置，不依赖已保存数据）。"""

    group_name: str
    chat_model: str
    base_url: str
    api_key: str
    model_type: str
    chat_proxy: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    extra_body: Optional[str] = None


class ModelGroupTestResponse(BaseModel):
    """基础模型组检测响应。"""

    items: List[ModelGroupTestItem]


router = APIRouter(prefix="/config", tags=["Config"])


def _raise_config_error(
    *,
    config_key: str,
    item_key: Optional[str],
    error_msg: Optional[str],
    operation: str,
) -> None:
    if not error_msg:
        raise OperationFailedError(operation=operation)

    if "配置实例不存在" in error_msg:
        raise ConfigNotFoundError(key=config_key)

    if "配置项不存在" in error_msg:
        key = f"{config_key}.{item_key}" if item_key else config_key
        raise ConfigNotFoundError(key=key)

    if "无效" in error_msg or "invalid" in error_msg.lower():
        key = item_key or config_key
        raise ConfigInvalidError(key=key, reason=error_msg)

    raise OperationFailedError(operation=operation)


@router.get("/keys", summary="获取所有配置键列表", response_model=List[str])
@require_role(Role.Admin)
async def get_config_keys(_current_user: DBUser = Depends(get_current_active_user)) -> List[str]:
    """获取所有已注册的配置键列表"""
    return UnifiedConfigService.get_all_config_keys()


@router.get("/info/{config_key}", summary="获取配置基本信息", response_model=ConfigInfo)
@require_role(Role.Admin)
async def get_config_info(
    config_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ConfigInfo:
    """获取指定配置的基本信息"""
    config_info = UnifiedConfigService.get_config_info(config_key)
    if not config_info:
        raise ConfigNotFoundError(key=config_key)
    return ConfigInfo(**config_info)


@router.get("/list/{config_key}", summary="获取指定配置的配置列表", response_model=List[ConfigItem])
@require_role(Role.Admin)
async def get_config_list(
    config_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[ConfigItem]:
    """获取指定配置的配置列表"""
    try:
        config_list = UnifiedConfigService.get_config_list(config_key)
    except ValueError:
        raise ConfigNotFoundError(key=config_key) from None
    return [ConfigItem(**item) for item in config_list]


@router.get("/get/{config_key}/{item_key}", summary="获取配置项值", response_model=ConfigItem)
@require_role(Role.Admin)
async def get_config_item(
    config_key: str,
    item_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ConfigItem:
    """获取指定配置的配置项值"""
    config_item = UnifiedConfigService.get_config_item(config_key, item_key)
    if not config_item:
        raise ConfigNotFoundError(key=f"{config_key}.{item_key}")
    return ConfigItem(**config_item)


@router.post("/set/{config_key}/{item_key}", summary="设置配置项值", response_model=ActionResponse)
@require_role(Role.Admin)
async def set_config_value(
    config_key: str,
    item_key: str,
    value: str = Query(..., description="配置项值"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """设置指定配置的配置项值"""
    success, error_msg = UnifiedConfigService.set_config_value(config_key, item_key, value)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=item_key,
            error_msg=error_msg,
            operation="设置配置",
        )
    return ActionResponse(ok=True)


@router.post("/batch/{config_key}", summary="批量更新配置", response_model=ActionResponse)
@require_role(Role.Admin)
async def batch_update_config(
    config_key: str,
    body: BatchUpdateConfig,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """批量更新指定配置"""
    success, error_msg = UnifiedConfigService.batch_update_config(config_key, body.configs)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=None,
            error_msg=error_msg,
            operation="批量更新配置",
        )

    success, error_msg = UnifiedConfigService.save_config(config_key)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=None,
            error_msg=error_msg,
            operation="保存配置",
        )

    # 系统配置保存后同步全局语言
    if config_key == "system":
        from nekro_agent.schemas.i18n import SupportedLang, set_system_lang

        set_system_lang(SupportedLang(config.SYSTEM_LANG))

    return ActionResponse(ok=True)


@router.post("/save/{config_key}", summary="保存配置", response_model=ActionResponse)
@require_role(Role.Admin)
async def save_config_api(
    config_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """保存指定配置到文件"""
    success, error_msg = UnifiedConfigService.save_config(config_key)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=None,
            error_msg=error_msg,
            operation="保存配置",
        )
    return ActionResponse(ok=True)


@router.post("/reload/{config_key}", summary="重置配置", response_model=ActionResponse)
@require_role(Role.Admin)
async def reload_config_api(
    config_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """重置指定配置"""
    success, error_msg = UnifiedConfigService.reload_config(config_key)
    if not success:
        _raise_config_error(
            config_key=config_key,
            item_key=None,
            error_msg=error_msg,
            operation="重置配置",
        )
    return ActionResponse(ok=True)


# ==================== 模型组管理API ====================


@router.get("/model-groups", summary="获取模型组列表", response_model=Dict[str, ModelConfigGroup])
@require_role(Role.Admin)
async def get_model_groups(_current_user: DBUser = Depends(get_current_active_user)) -> Dict[str, ModelConfigGroup]:
    """获取所有模型组配置"""
    return config.MODEL_GROUPS


@router.post("/model-groups/{group_name}", summary="更新模型组", response_model=ActionResponse)
@require_role(Role.Admin)
async def update_model_group(
    group_name: str,
    model_config: ModelConfigGroup,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """更新或添加模型组配置"""
    config.MODEL_GROUPS[group_name] = model_config
    save_config()
    return ActionResponse(ok=True)


@router.delete("/model-groups/{group_name}", summary="删除模型组", response_model=ActionResponse)
@require_role(Role.Admin)
async def delete_model_group(
    group_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """删除模型组配置"""
    if group_name not in config.MODEL_GROUPS:
        raise ModelGroupNotFoundError(name=group_name)
    if group_name == "default":
        raise DefaultModelGroupDeleteError

    del config.MODEL_GROUPS[group_name]
    save_config()
    return ActionResponse(ok=True)


@router.get("/model-types", summary="获取支持的模型类型列表", response_model=List[ModelTypeOption])
@require_role(Role.Admin)
async def get_model_types(_current_user: DBUser = Depends(get_current_active_user)) -> List[ModelTypeOption]:
    """获取支持的模型类型列表"""
    model_types = get_args(ModelConfigGroup.model_fields["MODEL_TYPE"].annotation)

    type_info: Dict[str, Dict[str, str]] = {
        "chat": {
            "label": "聊天",
            "description": "用于对话的模型",
            "color": "primary",
            "icon": "Chat",
        },
        "embedding": {
            "label": "嵌入",
            "description": "用于将文本转换为向量的模型",
            "color": "secondary",
            "icon": "Code",
        },
        "draw": {
            "label": "绘图",
            "description": "用于生成图像的模型",
            "color": "warning",
            "icon": "Brush",
        },
    }

    return [
        ModelTypeOption(
            value=type_name,
            label=type_info.get(type_name, {}).get("label") or type_name,
            description=type_info.get(type_name, {}).get("description") or "",
            color=type_info.get(type_name, {}).get("color") or "default",
            icon=type_info.get(type_name, {}).get("icon") or "EmojiObjects",
        )
        for type_name in model_types
    ]


@router.post("/model-groups/actions/fetch-models", summary="通过服务端拉取可用模型列表", response_model=FetchModelsResponse)
@require_role(Role.Admin)
async def fetch_model_groups_models(
    body: FetchModelsRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> FetchModelsResponse:
    """通过后端真实出口拉取 OpenAI 兼容模型列表。"""
    from nekro_agent.services.agent.openai import list_openai_models

    try:
        models = await list_openai_models(
            base_url=body.base_url,
            api_key=body.api_key,
            proxy_url=body.proxy_url,
        )
    except Exception as e:
        raise OperationFailedError(operation="拉取模型列表", detail=str(e)) from e

    return FetchModelsResponse(models=models)


@router.post("/model-groups/actions/test", summary="测试基础模型组", response_model=ModelGroupTestResponse)
@require_role(Role.Admin)
async def test_model_groups(
    body: ModelGroupTestRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ModelGroupTestResponse:
    """通过真实请求测试基础模型组，聊天模型发送消息，嵌入模型调用 embeddings 接口。"""
    from nekro_agent.services.agent.openai import gen_openai_chat_response, gen_openai_embeddings

    async def run_single(group_name: str) -> ModelGroupTestItem:
        model_group = config.MODEL_GROUPS.get(group_name)
        if model_group is None:
            return ModelGroupTestItem(
                group_name=group_name,
                model_name="",
                success=False,
                latency_ms=0,
                error_message=f"模型组不存在: {group_name}",
            )

        started = time.perf_counter()

        if model_group.MODEL_TYPE == "embedding":
            try:
                embedding = await gen_openai_embeddings(
                    **build_openai_embedding_test_params(model_group),
                )
                latency_ms = int((time.perf_counter() - started) * 1000)
                dim = len(embedding)
                return ModelGroupTestItem(
                    group_name=group_name,
                    model_name=model_group.CHAT_MODEL,
                    success=True,
                    latency_ms=latency_ms,
                    response_text=f"向量维度: {dim}",
                )
            except Exception as e:
                latency_ms = int((time.perf_counter() - started) * 1000)
                return ModelGroupTestItem(
                    group_name=group_name,
                    model_name=model_group.CHAT_MODEL,
                    success=False,
                    latency_ms=latency_ms,
                    error_message=str(e),
                )

        if model_group.MODEL_TYPE != "chat":
            return ModelGroupTestItem(
                group_name=group_name,
                model_name=model_group.CHAT_MODEL,
                success=False,
                latency_ms=0,
                error_message="仅支持测试聊天模型组和嵌入模型组",
            )

        try:
            result = await gen_openai_chat_response(
                messages=build_model_test_messages(use_system=False),
                **build_openai_model_test_params(model_group, False),
                max_wait_time=45,
            )
            if not result.response_content:
                raise ValueError("模型未返回有效内容")
            latency_ms = int((time.perf_counter() - started) * 1000)
            return ModelGroupTestItem(
                group_name=group_name,
                model_name=model_group.CHAT_MODEL,
                success=True,
                latency_ms=latency_ms,
                used_model=result.use_model,
                response_text=result.response_content,
                input_tokens=result.token_input,
                output_tokens=result.token_output,
            )
        except Exception as e:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return ModelGroupTestItem(
                group_name=group_name,
                model_name=model_group.CHAT_MODEL,
                success=False,
                latency_ms=latency_ms,
                error_message=str(e),
            )

    unique_group_names = list(dict.fromkeys(body.group_names))
    items = await asyncio.gather(*(run_single(group_name) for group_name in unique_group_names))
    return ModelGroupTestResponse(items=items)


@router.post("/model-groups/actions/test-inline", summary="inline 测试模型配置（不依赖已保存数据）", response_model=ModelGroupTestItem)
@require_role(Role.Admin)
async def test_model_group_inline(
    body: ModelGroupInlineTestRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ModelGroupTestItem:
    """使用请求体中直接传入的配置执行测试，测试编辑中未保存的配置时使用。"""
    from nekro_agent.services.agent.openai import gen_openai_chat_response, gen_openai_embeddings

    # 构造临时 model_group 对象供 build_* 函数复用
    class _TempGroup:
        CHAT_MODEL = body.chat_model
        BASE_URL = body.base_url
        API_KEY = body.api_key
        CHAT_PROXY = body.chat_proxy or ""
        TEMPERATURE = body.temperature
        TOP_P = body.top_p
        TOP_K = body.top_k
        PRESENCE_PENALTY = body.presence_penalty
        FREQUENCY_PENALTY = body.frequency_penalty
        EXTRA_BODY = body.extra_body
        MODEL_TYPE = body.model_type

    model_group = _TempGroup()
    started = time.perf_counter()

    if body.model_type == "embedding":
        try:
            embedding = await gen_openai_embeddings(
                **build_openai_embedding_test_params(model_group),
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            return ModelGroupTestItem(
                group_name=body.group_name,
                model_name=body.chat_model,
                success=True,
                latency_ms=latency_ms,
                response_text=f"向量维度: {len(embedding)}",
            )
        except Exception as e:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return ModelGroupTestItem(
                group_name=body.group_name,
                model_name=body.chat_model,
                success=False,
                latency_ms=latency_ms,
                error_message=str(e),
            )

    if body.model_type != "chat":
        return ModelGroupTestItem(
            group_name=body.group_name,
            model_name=body.chat_model,
            success=False,
            latency_ms=0,
            error_message="仅支持测试聊天模型组和嵌入模型组",
        )

    try:
        result = await gen_openai_chat_response(
            messages=build_model_test_messages(use_system=False),
            **build_openai_model_test_params(model_group, False),
            max_wait_time=45,
        )
        if not result.response_content:
            raise ValueError("模型未返回有效内容")
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ModelGroupTestItem(
            group_name=body.group_name,
            model_name=body.chat_model,
            success=True,
            latency_ms=latency_ms,
            used_model=result.use_model,
            response_text=result.response_content,
            input_tokens=result.token_input,
            output_tokens=result.token_output,
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ModelGroupTestItem(
            group_name=body.group_name,
            model_name=body.chat_model,
            success=False,
            latency_ms=latency_ms,
            error_message=str(e),
        )


@router.get("/version", summary="获取应用版本", response_model=str)
@require_role(Role.User)
async def get_version(_current_user: DBUser = Depends(get_current_active_user)) -> str:
    """获取应用版本"""
    return get_app_version()
