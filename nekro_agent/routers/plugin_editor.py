import json
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi import Path as PathParam
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core import logger
from nekro_agent.core.config import config
from nekro_agent.core.os_env import WORKDIR_PLUGIN_DIR
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
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


@router.get("/files", summary="获取插件文件列表")
@require_role(Role.Admin)
async def get_plugin_files(
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取插件文件列表"""
    try:
        if not WORKDIR_PLUGIN_DIR:
            return Ret.fail(msg="工作目录插件目录未配置")

        plugin_dir = Path(WORKDIR_PLUGIN_DIR)
        if not plugin_dir.exists():
            plugin_dir.mkdir(parents=True, exist_ok=True)
            return Ret.success(msg="获取成功", data=[])

        files = []
        for pattern in ["**/*.py", "**/*.py.disabled"]:
            for file in plugin_dir.glob(pattern):
                files.append(str(file.relative_to(plugin_dir)))

        return Ret.success(msg="获取成功", data=files)
    except Exception as e:
        logger.error(f"获取插件文件列表失败: {e}")
        return Ret.error(msg=f"获取失败: {e!s}")


@router.get("/file/{file_path:path}", summary="获取插件文件内容")
@require_role(Role.Admin)
async def get_plugin_file_content(
    file_path: str = PathParam(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取插件文件内容"""
    try:
        if not WORKDIR_PLUGIN_DIR:
            return Ret.fail(msg="工作目录插件目录未配置")

        # 安全检查：确保路径在工作目录内
        plugin_dir = Path(WORKDIR_PLUGIN_DIR)
        full_path = plugin_dir / file_path

        if not full_path.exists():
            return Ret.fail(msg=f"文件 {file_path} 不存在")

        # 检查文件是否在插件目录内
        try:
            full_path.relative_to(plugin_dir)
        except ValueError:
            return Ret.fail(msg="文件路径非法")

        # 读取文件内容
        content = full_path.read_text(encoding="utf-8")
        return Ret.success(msg="获取成功", data={"content": content})
    except Exception as e:
        logger.error(f"获取插件文件内容失败: {e}")
        return Ret.error(msg=f"获取失败: {e!s}")


@router.post("/file/{file_path:path}", summary="保存插件文件")
@require_role(Role.Admin)
async def save_plugin_file(
    request: Request,
    file_path: str = PathParam(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """保存插件文件"""
    try:
        if not WORKDIR_PLUGIN_DIR:
            return Ret.fail(msg="工作目录插件目录未配置")

        # 安全检查：确保路径在工作目录内
        plugin_dir = Path(WORKDIR_PLUGIN_DIR)
        full_path = plugin_dir / file_path

        # 检查文件是否在插件目录内
        try:
            full_path.relative_to(plugin_dir)
        except ValueError:
            return Ret.fail(msg="文件路径非法")

        # 确保目标目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 读取请求体
        content = await request.body()
        content_str = content.decode("utf-8")

        # 写入文件
        full_path.write_text(content_str, encoding="utf-8")
        return Ret.success(msg="保存成功")
    except Exception as e:
        logger.error(f"保存插件文件失败: {e}")
        return Ret.error(msg=f"保存失败: {e!s}")


@router.delete("/files/{file_path:path}", summary="删除插件文件")
@require_role(Role.Admin)
async def delete_plugin_file(
    file_path: str = PathParam(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """删除插件文件"""
    try:
        if not WORKDIR_PLUGIN_DIR:
            return Ret.fail(msg="工作目录插件目录未配置")

        # 安全检查：确保路径在工作目录内
        plugin_dir = Path(WORKDIR_PLUGIN_DIR)
        full_path = plugin_dir / file_path

        # 检查文件是否在插件目录内
        try:
            full_path.relative_to(plugin_dir)
        except ValueError:
            return Ret.fail(msg="文件路径非法")

        # 检查文件是否存在
        if not full_path.exists():
            return Ret.fail(msg=f"文件 {file_path} 不存在")

        await plugin_collector.unload_plugin_by_module_name(full_path.stem)

        # 删除文件
        full_path.unlink()
        return Ret.success(msg="删除成功")
    except Exception as e:
        logger.error(f"删除插件文件失败: {e}")
        return Ret.error(msg=f"删除失败: {e!s}")


class GenerateCodeRequest(BaseModel):
    """生成代码请求体"""

    file_path: str
    prompt: str
    current_code: Optional[str] = None


class GenerateCodeResponse(BaseModel):
    """生成代码响应体"""

    code: str


@router.post("/generate", summary="生成插件代码")
@require_role(Role.Admin)
async def generate_code(
    body: GenerateCodeRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """生成插件代码"""
    try:
        if not body.prompt:
            return Ret.fail(msg="提示词不能为空")

        code = await generate_plugin_code(
            file_path=body.file_path,
            prompt=body.prompt,
            current_code=body.current_code,
        )
        return Ret.success(msg="生成成功", data={"code": code})
    except Exception as e:
        logger.error(f"生成插件代码失败: {e}")
        return Ret.error(msg=f"生成失败: {e!s}")


@router.post("/generate/stream", summary="流式生成插件代码")
@require_role(Role.Admin)
async def generate_code_stream(
    body: GenerateCodeRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> EventSourceResponse:
    """流式生成插件代码"""

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # 使用简化的流式生成器直接产生内容
            async for chunk in generate_plugin_code_stream(
                file_path=body.file_path,
                prompt=body.prompt,
                current_code=body.current_code,
            ):
                # 每个chunk都作为内容发送
                yield json.dumps({"type": "content", "content": chunk})

            # 生成完成后发送完成信号
            yield json.dumps({"type": "done"})
        except Exception as e:
            logger.error(f"流式生成插件代码失败: {e}")
            yield json.dumps({"type": "error", "error": str(e)})

    return EventSourceResponse(event_generator())


@router.post("/apply", summary="应用生成的代码")
@require_role(Role.Admin)
async def apply_code(
    body: GenerateCodeRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """应用生成的代码"""
    try:
        if not body.prompt or not body.current_code:
            return Ret.fail(msg="参数不完整")

        code = await apply_plugin_code(
            file_path=body.file_path,
            prompt=body.prompt,
            current_code=body.current_code,
        )
        return Ret.success(msg="应用成功", data={"code": code})
    except Exception as e:
        logger.error(f"应用生成的代码失败: {e}")
        return Ret.error(msg=f"应用失败: {e!s}")


class TemplateRequest(BaseModel):
    """模板请求体"""

    name: str
    description: str


class TemplateResponse(BaseModel):
    """模板响应体"""

    template: str


@router.post("/template", summary="生成插件模板")
@require_role(Role.Admin)
async def create_plugin_template(
    body: TemplateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """生成插件模板"""
    try:
        template = generate_plugin_template(name=body.name, description=body.description)
        return Ret.success(msg="生成成功", data={"template": template})
    except Exception as e:
        logger.error(f"生成插件模板失败: {e}")
        return Ret.error(msg=f"生成失败: {e!s}")
