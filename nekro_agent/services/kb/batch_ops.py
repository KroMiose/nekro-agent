"""知识库批量操作通用执行器：去重/上限校验、限流并发、单条错误隔离、结果聚合。"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.errors import AppError, ValidationError

logger = get_sub_logger("kb.batch_ops")

# 面向用户的通用文案（与服务端 AppError 的 zh 文案保持一致；项目暂无按请求语言的错误本地化管线）
_MSG_INTERNAL_ERROR = "内部错误（详见服务端日志）"
_MSG_EXCEED_LIMIT = "单次批量操作最多 {max_size} 个"


@dataclass
class BatchItemResult:
    """批量操作单条目结果"""

    id: int
    success: bool
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


# op 对单个 id 执行操作，返回该条目的外部资源清理警告（best-effort，无警告时返回 None）
BatchOpFn = Callable[[int], Awaitable[list[str] | None]]


def normalize_batch_ids(ids: list[int], max_size: int) -> list[int]:
    """去重保序 + 数量上限校验。"""
    unique_ids = list(dict.fromkeys(ids))
    if len(unique_ids) > max_size:
        raise ValidationError(reason=_MSG_EXCEED_LIMIT.format(max_size=max_size))
    return unique_ids


async def run_batched_ids(
    ids: list[int],
    concurrency: int,
    op: BatchOpFn,
) -> list[BatchItemResult]:
    """限流并发执行单元素操作，单条失败隔离；不做去重/校验（由 normalize_batch_ids 负责）。"""
    if not ids:
        return []

    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(item_id: int) -> BatchItemResult:
        async with semaphore:
            try:
                warnings = await op(item_id) or []
                return BatchItemResult(id=item_id, success=True, warnings=warnings)
            except AppError as e:
                # 业务错误（不存在/冲突等）：返回本地化消息，不暴露内部细节
                return BatchItemResult(id=item_id, success=False, error=str(e))
            except Exception as e:
                logger.warning(f"批量操作失败: id={item_id}, error={e}", exc_info=True)
                return BatchItemResult(id=item_id, success=False, error=_MSG_INTERNAL_ERROR)

    return await asyncio.gather(*(run_one(i) for i in ids))


def aggregate_batch_results(
    results: list[BatchItemResult], label: str
) -> tuple[list[int], list[int], list[str], list[str]]:
    """聚合批量结果：成功 id、失败 id、清理警告（格式化）、错误消息（格式化）。"""
    success_ids = [r.id for r in results if r.success]
    failed_ids = [r.id for r in results if not r.success]
    warnings = [f"{label} {r.id}: {w}" for r in results if r.success for w in r.warnings]
    errors = [f"{label} {r.id}: {r.error}" for r in results if not r.success and r.error]
    return success_ids, failed_ids, warnings, errors
