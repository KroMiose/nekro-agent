"""知识库批量操作通用执行器：去重、数量上限、限流并发、单条错误隔离。"""

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


async def run_batched_ids(
    ids: list[int],
    max_size: int,
    concurrency: int,
    op: BatchOpFn,
    label: str,
) -> tuple[list[BatchItemResult], list[str]]:
    """批量执行单元素操作：去重保序 → 数量上限校验 → 限流并发 → 单条失败隔离。

    - op 对单个 id 执行操作，返回该条目的清理警告列表（best-effort，不失败）；
    - 业务错误（AppError）返回本地化消息，其他异常记录日志并返回通用文案。
    返回 (逐条结果, 格式化后的错误列表)；清理警告由调用方通过 aggregate_batch_results 聚合。
    """
    unique_ids = list(dict.fromkeys(ids))
    if len(unique_ids) > max_size:
        raise ValidationError(reason=_MSG_EXCEED_LIMIT.format(max_size=max_size))
    if not unique_ids:
        return [], []

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

    results = await asyncio.gather(*(run_one(i) for i in unique_ids))
    errors = [f"{label} {r.id}: {r.error}" for r in results if not r.success and r.error]
    return results, errors


def aggregate_batch_results(results: list[BatchItemResult], label: str) -> tuple[list[int], list[str]]:
    """从批量结果中聚合成功 id 列表与清理警告列表（供各批量接口构建响应复用）。"""
    success_ids = [r.id for r in results if r.success]
    warnings = [f"{label} {r.id}: {w}" for r in results if r.success for w in r.warnings]
    return success_ids, warnings
