import json
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, Request
from fastapi import Path as PathParam
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core.os_env import WORKDIR_PLUGIN_DIR
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import NotFoundError, ValidationError
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.plugin.generator import (
    apply_plugin_code,
    generate_plugin_code,
    generate_plugin_code_stream,
    generate_plugin_template,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/plugin-editor", tags=["Plugin Editor"])


class FileContentResponse(BaseModel):
    """文件内容响应"""

    content: str


class ActionResponse(BaseModel):
    ok: bool = True


@router.get("/files", summary="获取插件文件列表", response_model=list[str])
@require_role(Role.Admin)
async def get_plugin_files(
    _current_user: DBUser = Depends(get_current_active_user),
) -> list[str]:
    """获取插件文件列表"""
    if not WORKDIR_PLUGIN_DIR:
        raise ValidationError(reason="工作目录插件目录未配置")

    plugin_dir = Path(WORKDIR_PLUGIN_DIR)
    if not plugin_dir.exists():
        plugin_dir.mkdir(parents=True, exist_ok=True)
        return []

    files: list[str] = []
    for pattern in ["**/*.py", "**/*.py.disabled"]:
        for file in plugin_dir.glob(pattern):
            files.append(str(file.relative_to(plugin_dir)))

    return files


@router.get("/file/{file_path:path}", summary="获取插件文件内容", response_model=FileContentResponse)
@require_role(Role.Admin)
async def get_plugin_file_content(
    file_path: str = PathParam(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> FileContentResponse:
    """获取插件文件内容"""
    if not WORKDIR_PLUGIN_DIR:
        raise ValidationError(reason="工作目录插件目录未配置")

    plugin_dir = Path(WORKDIR_PLUGIN_DIR)
    full_path = plugin_dir / file_path

    if not full_path.exists():
        raise NotFoundError(resource=f"文件 {file_path}")

    try:
        full_path.relative_to(plugin_dir)
    except ValueError as e:
        raise ValidationError(reason="文件路径非法") from e

    content = full_path.read_text(encoding="utf-8")
    return FileContentResponse(content=content)


@router.post("/file/{file_path:path}", summary="保存插件文件", response_model=ActionResponse)
@require_role(Role.Admin)
async def save_plugin_file(
    request: Request,
    file_path: str = PathParam(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """保存插件文件"""
    if not WORKDIR_PLUGIN_DIR:
        raise ValidationError(reason="工作目录插件目录未配置")

    plugin_dir = Path(WORKDIR_PLUGIN_DIR)
    full_path = plugin_dir / file_path

    try:
        full_path.relative_to(plugin_dir)
    except ValueError as e:
        raise ValidationError(reason="文件路径非法") from e

    full_path.parent.mkdir(parents=True, exist_ok=True)

    content = await request.body()
    content_str = content.decode("utf-8")

    full_path.write_text(content_str, encoding="utf-8")
    return ActionResponse(ok=True)


@router.delete("/files/{file_path:path}", summary="删除插件文件", response_model=ActionResponse)
@require_role(Role.Admin)
async def delete_plugin_file(
    file_path: str = PathParam(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """删除插件文件"""
    if not WORKDIR_PLUGIN_DIR:
        raise ValidationError(reason="工作目录插件目录未配置")

    plugin_dir = Path(WORKDIR_PLUGIN_DIR)
    full_path = plugin_dir / file_path

    try:
        full_path.relative_to(plugin_dir)
    except ValueError as e:
        raise ValidationError(reason="文件路径非法") from e

    if not full_path.exists():
        raise NotFoundError(resource=f"文件 {file_path}")

    await plugin_collector.unload_plugin_by_module_name(full_path.stem)

    full_path.unlink()
    return ActionResponse(ok=True)


class GenerateCodeRequest(BaseModel):
    """生成代码请求体"""

    file_path: str
    prompt: str
    current_code: Optional[str] = None


class GenerateCodeResponse(BaseModel):
    """生成代码响应体"""

    code: str


@router.post("/generate", summary="生成插件代码", response_model=GenerateCodeResponse)
@require_role(Role.Admin)
async def generate_code(
    body: GenerateCodeRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> GenerateCodeResponse:
    """生成插件代码"""
    if not body.prompt:
        raise ValidationError(reason="提示词不能为空")

    code = await generate_plugin_code(
        file_path=body.file_path,
        prompt=body.prompt,
        current_code=body.current_code,
    )
    return GenerateCodeResponse(code=code)


@router.post("/generate/stream", summary="流式生成插件代码")
@require_role(Role.Admin)
async def generate_code_stream(
    body: GenerateCodeRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> EventSourceResponse:
    """流式生成插件代码"""

    async def event_generator() -> AsyncGenerator[str, None]:
        async for chunk in generate_plugin_code_stream(
            file_path=body.file_path,
            prompt=body.prompt,
            current_code=body.current_code,
        ):
            yield json.dumps({"type": "content", "content": chunk})

        yield json.dumps({"type": "done"})

    return EventSourceResponse(event_generator())


@router.post("/apply", summary="应用生成的代码", response_model=GenerateCodeResponse)
@require_role(Role.Admin)
async def apply_code(
    body: GenerateCodeRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> GenerateCodeResponse:
    """应用生成的代码"""
    if not body.prompt or not body.current_code:
        raise ValidationError(reason="参数不完整")

    code = await apply_plugin_code(
        file_path=body.file_path,
        prompt=body.prompt,
        current_code=body.current_code,
    )
    return GenerateCodeResponse(code=code)


class TemplateRequest(BaseModel):
    """模板请求体"""

    name: str
    description: str


class TemplateResponse(BaseModel):
    """模板响应体"""

    template: str


@router.post("/template", summary="生成插件模板", response_model=TemplateResponse)
@require_role(Role.Admin)
async def create_plugin_template(
    body: TemplateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> TemplateResponse:
    """生成插件模板"""
    template = generate_plugin_template(name=body.name, description=body.description)
    return TemplateResponse(template=template)
