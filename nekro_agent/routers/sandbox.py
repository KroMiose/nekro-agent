from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from tortoise.functions import Count

from nekro_agent.models.db_exec_code import DBExecCode, ExecStopType
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/sandbox", tags=["Sandbox"])


@router.get("/logs", summary="获取沙盒执行日志")
@require_role(Role.Admin)
async def get_sandbox_logs(
    page: int = 1,
    page_size: int = 20,
    chat_key: Optional[str] = None,
    success: Optional[bool] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取沙盒执行日志列表"""
    query = DBExecCode.all()

    if chat_key:
        query = query.filter(chat_key=chat_key)
    if success is not None:
        query = query.filter(success=success)

    total = await query.count()
    logs = await query.order_by("-create_time").offset((page - 1) * page_size).limit(page_size)

    return Ret.success(
        msg="获取成功",
        data={
            "total": total,
            "items": [
                {
                    "id": log.id,
                    "chat_key": log.chat_key,
                    "trigger_user_id": log.trigger_user_id,
                    "trigger_user_name": log.trigger_user_name,
                    "success": log.success,
                    "code_text": log.code_text,
                    "outputs": log.outputs,
                    "create_time": log.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "thought_chain": log.thought_chain,
                    "stop_type": log.stop_type,
                    "exec_time_ms": log.exec_time_ms,
                    "generation_time_ms": log.generation_time_ms,
                    "total_time_ms": log.total_time_ms,
                    "use_model": log.use_model,
                }
                for log in logs
            ],
        },
    )


@router.get("/stats", summary="获取沙盒执行统计")
@require_role(Role.Admin)
async def get_sandbox_stats(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取沙盒执行统计信息"""
    total = await DBExecCode.all().count()
    success = await DBExecCode.filter(success=True).count()
    failed = await DBExecCode.filter(success=False).count()
    agent_count = await DBExecCode.filter(stop_type=ExecStopType.AGENT).count()

    return Ret.success(
        msg="获取成功",
        data={
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(success / total * 100, 2) if total > 0 else 0,
            "agent_count": agent_count,
        },
    )
