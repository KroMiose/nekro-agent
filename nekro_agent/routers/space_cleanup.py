"""空间清理路由"""

from fastapi import APIRouter, Depends

from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.schemas.space_cleanup import (
    CleanupProgress,
    CleanupRequest,
    CleanupResult,
    DiskInfo,
    ScanResult,
    ScanStatusResponse,
)
from nekro_agent.services.space_cleanup.cleaner import cleanup_service
from nekro_agent.services.space_cleanup.scanner import scanner_service
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/space-cleanup", tags=["Space Cleanup"])


@router.post("/scan/start", summary="启动扫描")
@require_role(Role.Admin)
async def start_scan(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """启动空间扫描任务

    Returns:
        Ret: 包含扫描任务ID的响应
    """
    try:
        scan_id = await scanner_service.start_scan()
        return Ret.success(msg="扫描任务已启动", data={"scan_id": scan_id})
    except Exception as e:
        return Ret.error(msg=f"启动扫描失败: {e}")


@router.get("/scan/status", summary="获取扫描状态")
@require_role(Role.Admin)
async def get_scan_status(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取扫描状态和进度

    Returns:
        Ret: 包含扫描状态的响应
    """
    try:
        status = await scanner_service.get_scan_status()
        return Ret.success(msg="获取成功", data=status.model_dump())
    except Exception as e:
        return Ret.error(msg=f"获取扫描状态失败: {e}")


@router.get("/scan/progress", summary="获取扫描进度")
@require_role(Role.Admin)
async def get_scan_progress(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取扫描进度

    Returns:
        Ret: 包含扫描进度的响应
    """
    try:
        progress = await scanner_service.get_scan_progress()
        return Ret.success(msg="获取成功", data=progress)
    except Exception as e:
        return Ret.error(msg=f"获取扫描进度失败: {e!s}")


@router.get("/scan/result", summary="获取扫描结果")
@require_role(Role.Admin)
async def get_scan_result(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取扫描结果

    Returns:
        Ret: 包含扫描结果的响应
    """
    try:
        result = await scanner_service.get_scan_result()
        if result is None:
            return Ret.fail(msg="暂无扫描结果，请先启动扫描")
        return Ret.success(msg="获取成功", data=result.model_dump())
    except Exception as e:
        return Ret.error(msg=f"获取扫描结果失败: {e!s}")


@router.get("/scan/load-cache", summary="从缓存加载扫描结果")
@require_role(Role.Admin)
async def load_scan_result_from_cache(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """从缓存文件加载最新的空间扫描结果

    Returns:
        Ret: 包含扫描结果的响应
    """
    try:
        result = await scanner_service.load_scan_result_from_cache()
        if result is None:
            return Ret.fail(msg="缓存中无扫描结果")
        return Ret.success(msg="从缓存加载成功", data=result.model_dump())
    except Exception as e:
        return Ret.error(msg=f"从缓存加载扫描结果失败: {e!s}")


@router.post("/cleanup/start", summary="启动清理任务")
@require_role(Role.Admin)
async def start_cleanup(
    request: CleanupRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """启动清理任务

    Args:
        request: 清理请求

    Returns:
        Ret: 包含清理任务ID的响应
    """
    try:
        task_id = await cleanup_service.create_cleanup_task(request)
        return Ret.success(msg="清理任务已启动", data={"task_id": task_id})
    except Exception as e:
        return Ret.error(msg=f"启动清理失败: {e}")


@router.get("/cleanup/progress/{task_id}", summary="获取清理进度")
@require_role(Role.Admin)
async def get_cleanup_progress(
    task_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取清理进度

    Args:
        task_id: 任务ID

    Returns:
        Ret: 包含清理进度的响应
    """
    try:
        progress = await cleanup_service.get_cleanup_progress(task_id)
        if progress is None:
            return Ret.fail(msg="清理任务不存在")
        return Ret.success(msg="获取成功", data=progress.model_dump())
    except Exception as e:
        return Ret.error(msg=f"获取清理进度失败: {e}")


@router.get("/cleanup/result/{task_id}", summary="获取清理结果")
@require_role(Role.Admin)
async def get_cleanup_result(
    task_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取清理结果

    Args:
        task_id: 任务ID

    Returns:
        Ret: 包含清理结果的响应
    """
    try:
        result = await cleanup_service.get_cleanup_result(task_id)
        if result is None:
            return Ret.fail(msg="清理任务不存在或未完成")
        return Ret.success(msg="获取成功", data=result.model_dump())
    except Exception as e:
        return Ret.error(msg=f"获取清理结果失败: {e}")


@router.get("/disk-info", summary="获取磁盘信息")
@require_role(Role.Admin)
async def get_disk_info(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取磁盘信息

    Returns:
        Ret: 包含磁盘信息的响应
    """
    try:
        # 获取最新扫描结果中的磁盘信息
        scan_result = await scanner_service.get_scan_result()
        if scan_result and scan_result.disk_info:
            return Ret.success(msg="获取成功", data=scan_result.disk_info.model_dump())
        return Ret.fail(msg="暂无磁盘信息，请先启动扫描")
    except Exception as e:
        return Ret.error(msg=f"获取磁盘信息失败: {e!s}")
