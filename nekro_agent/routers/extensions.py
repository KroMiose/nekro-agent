import json
from typing import AsyncGenerator, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.message import Ret
from nekro_agent.services.extension import (
    apply_extension_code,
    delete_ext_file,
    generate_extension_code,
    generate_extension_code_stream,
    generate_extension_template,
    get_ext_workdir_files,
    read_ext_file,
    reload_ext_workdir,
    save_ext_file,
)
from nekro_agent.services.extension.manager import get_all_ext_meta_data
from nekro_agent.systems.user.deps import get_current_active_user
from nekro_agent.tools.collector import MethodType, agent_collector

router = APIRouter(prefix="/extensions", tags=["Extensions"])


@router.get("", summary="获取扩展列表")
async def get_extensions(_=Depends(get_current_active_user)) -> Ret:
    """获取所有已加载的扩展信息"""
    extensions = []

    # 获取所有方法及其所属的标签
    all_methods = {}
    for _tag, methods in agent_collector.tag_map.items():
        for method in methods:
            if method.__doc__:
                try:
                    method_type = agent_collector.get_method_type(method)
                    # 使用方法所在模块的文件名作为扩展名
                    ext_name = method.__module__.split(".")[-1]
                    if ext_name not in all_methods:
                        all_methods[ext_name] = []
                    all_methods[ext_name].append(
                        {"name": method.__name__, "type": method_type, "description": method.__doc__.strip()},
                    )
                except ValueError:
                    continue

    # 为每个扩展添加其对应的方法
    for ext in get_all_ext_meta_data():
        if ext.name not in all_methods:
            logger.warning(f"扩展: {ext.name} 未找到挂载方法列表，请确认扩展元数据与包名是否对应")
        extensions.append(
            {
                "name": ext.name,
                "version": ext.version,
                "description": ext.description,
                "author": ext.author,
                "methods": all_methods.get(ext.name, []),  # 获取该扩展对应的方法列表
                "is_enabled": True,
            },
        )

    return Ret.success(msg="获取扩展列表成功", data=extensions)


@router.get("/files", summary="获取扩展文件列表")
async def get_extension_files(_=Depends(get_current_active_user)) -> Ret:
    """获取工作目录下的所有扩展文件"""
    try:
        files = get_ext_workdir_files()
        return Ret.success(msg="获取扩展文件列表成功", data=files)
    except Exception as e:
        return Ret.error(msg=f"获取扩展文件列表失败: {e!s}")


@router.get("/file/{file_path:path}", summary="获取扩展文件内容")
async def get_extension_file(file_path: str, _=Depends(get_current_active_user)) -> Ret:
    """获取指定扩展文件的内容"""
    try:
        content = read_ext_file(file_path)
        return Ret.success(msg="获取扩展文件内容成功", data={"content": content})
    except Exception as e:
        return Ret.error(msg=f"获取扩展文件内容失败: {e!s}")


@router.post("/file/{file_path:path}", summary="保存扩展文件内容")
async def save_extension_file(file_path: str, content: str = Body(...), _=Depends(get_current_active_user)) -> Ret:
    """保存扩展文件内容"""
    try:
        save_ext_file(file_path, content)
        return Ret.success(msg="保存扩展文件内容成功")
    except Exception as e:
        return Ret.error(msg=f"保存扩展文件内容失败: {e!s}")


@router.post("/generate", summary="生成扩展代码")
async def generate_extension(
    file_path: str = Body(..., description="文件路径"),
    prompt: str = Body(..., description="提示词"),
    current_code: str = Body(None, description="当前代码"),
    _=Depends(get_current_active_user),
) -> Ret:
    """生成扩展代码"""
    try:
        generated_code = await generate_extension_code(file_path, prompt, current_code)
        return Ret.success(msg="生成代码成功", data={"code": generated_code})
    except Exception as e:
        return Ret.error(msg=f"生成代码失败: {e!s}")


@router.post("/template", summary="生成扩展模板")
async def create_extension_template(
    name: str = Body(..., description="扩展名称"),
    description: str = Body(..., description="扩展描述"),
    _=Depends(get_current_active_user),
) -> Ret:
    """生成扩展模板"""
    try:
        template = generate_extension_template(name, description)
        return Ret.success(msg="生成扩展模板成功", data={"template": template})
    except Exception as e:
        return Ret.error(msg=f"生成扩展模板失败: {e!s}")


@router.post("/generate/stream", summary="流式生成扩展代码")
async def stream_generate_extension(
    file_path: str = Body(..., description="文件路径"),
    prompt: str = Body(..., description="提示词"),
    current_code: str | None = Body(None, description="当前代码"),
    _=Depends(get_current_active_user),
) -> EventSourceResponse:
    """流式生成扩展代码"""

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in generate_extension_code_stream(file_path, prompt, current_code):
                yield f'{{"type": "content", "content": {json.dumps(chunk)}}}\n\n'
            yield '{"type": "done"}\n\n'
        except Exception as e:
            logger.error(f"生成代码失败: {e!s}")
            yield f'{{"type": "error", "error": {json.dumps(str(e))}}}\n\n'

    return EventSourceResponse(event_generator())


@router.post("/apply", summary="应用生成的代码")
async def apply_extension(
    file_path: str = Body(..., description="文件路径"),
    prompt: str = Body(..., description="提示词"),
    current_code: str = Body(..., description="当前代码"),
    _=Depends(get_current_active_user),
) -> Ret:
    """应用生成的代码"""
    try:
        applied_code = await apply_extension_code(file_path, prompt, current_code)
        return Ret.success(msg="应用代码成功", data={"code": applied_code})
    except Exception as e:
        return Ret.error(msg=f"应用代码失败: {e!s}")


@router.get("/files")
async def list_extension_files() -> List[str]:
    """获取所有扩展文件"""
    return get_ext_workdir_files()


@router.delete("/files/{file_path:path}")
async def delete_extension_file(file_path: str) -> Dict[str, str]:
    """删除扩展文件"""
    try:
        delete_ext_file(file_path)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    else:
        return {"message": "文件删除成功"}


@router.get("/files/{file_path:path}")
async def read_extension_file(file_path: str) -> str:
    """读取扩展文件内容"""
    try:
        return read_ext_file(file_path)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/reload", summary="重载所有扩展")
async def reload_extensions(_=Depends(get_current_active_user)) -> Ret:
    """重载所有扩展"""
    try:
        reload_ext_workdir()
        return Ret.success(msg="重载扩展成功")
    except Exception as e:
        return Ret.error(msg=f"重载扩展失败: {e!s}")
