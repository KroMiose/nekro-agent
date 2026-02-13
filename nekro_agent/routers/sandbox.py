import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core.os_env import PROMPT_LOG_DIR
from nekro_agent.models.db_exec_code import DBExecCode, ExecStopType
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import NotFoundError, OperationFailedError, PermissionDeniedError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/sandbox", tags=["Sandbox"])


class SandboxLog(BaseModel):
    id: int
    chat_key: str
    trigger_user_id: str
    trigger_user_name: str
    success: bool
    code_text: str
    outputs: str
    create_time: str
    thought_chain: Optional[str]
    stop_type: ExecStopType
    exec_time_ms: int
    generation_time_ms: int
    total_time_ms: int
    use_model: str
    extra_data: str


class SandboxLogListResponse(BaseModel):
    total: int
    items: List[SandboxLog]


class SandboxStats(BaseModel):
    total: int
    success: int
    failed: int
    success_rate: float
    agent_count: int


@router.get("/logs", summary="获取沙盒执行日志")
@require_role(Role.Admin)
async def get_sandbox_logs(
    page: int = 1,
    page_size: int = 20,
    chat_key: Optional[str] = None,
    success: Optional[bool] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> SandboxLogListResponse:
    """获取沙盒执行日志列表"""
    query = DBExecCode.all()

    if chat_key:
        query = query.filter(chat_key=chat_key)
    if success is not None:
        query = query.filter(success=success)

    total = await query.count()
    logs = await query.order_by("-create_time").offset((page - 1) * page_size).limit(page_size)

    return SandboxLogListResponse(
        total=total,
        items=[
            SandboxLog(
                id=log.id,
                chat_key=log.chat_key,
                trigger_user_id=log.trigger_user_id,
                trigger_user_name=log.trigger_user_name,
                success=log.success,
                code_text=log.code_text,
                outputs=log.outputs,
                create_time=log.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                thought_chain=log.thought_chain,
                stop_type=log.stop_type,
                exec_time_ms=log.exec_time_ms,
                generation_time_ms=log.generation_time_ms,
                total_time_ms=log.total_time_ms,
                use_model=log.use_model,
                extra_data=log.extra_data,
            )
            for log in logs
        ],
    )


@router.get("/log-content", summary="获取沙盒执行日志内容")
@require_role(Role.Admin)
async def get_sandbox_log_content(
    log_path: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """根据路径获取沙盒执行日志的详细内容"""
    allowed_dir = Path(PROMPT_LOG_DIR).parent.resolve()
    target_path = Path(log_path).resolve()

    if not target_path.is_file():
        raise NotFoundError(resource="日志文件")

    try:
        target_path.relative_to(allowed_dir)
    except ValueError as e:
        raise PermissionDeniedError() from e

    try:
        log_content = target_path.read_text(encoding="utf-8")
        return json.loads(log_content)
    except (OSError, json.JSONDecodeError) as e:
        raise OperationFailedError(operation="读取日志文件") from e


@router.get("/stats", summary="获取沙盒执行统计")
@require_role(Role.Admin)
async def get_sandbox_stats(_current_user: DBUser = Depends(get_current_active_user)) -> SandboxStats:
    """获取沙盒执行统计信息"""
    total = await DBExecCode.all().count()
    success = await DBExecCode.filter(success=True).count()
    failed = await DBExecCode.filter(success=False).count()
    agent_count = await DBExecCode.filter(stop_type=ExecStopType.AGENT).count()

    return SandboxStats(
        total=total,
        success=success,
        failed=failed,
        success_rate=round(success / total * 100, 2) if total > 0 else 0,
        agent_count=agent_count,
    )
