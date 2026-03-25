"""记忆重建服务。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from pydantic import BaseModel

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_mem_entity import DBMemEntity
from nekro_agent.models.db_mem_episode import DBMemEpisode
from nekro_agent.models.db_mem_paragraph import DBMemParagraph
from nekro_agent.models.db_mem_reinforcement_log import DBMemReinforcementLog
from nekro_agent.models.db_mem_relation import DBMemRelation
from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog
from nekro_agent.services.memory.consolidator import consolidate_workspace
from nekro_agent.services.memory.feature_flags import (
    MemoryOperation,
    ensure_memory_system_enabled,
    is_memory_system_enabled,
)
from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager
from nekro_agent.services.memory.rebuild_state_store import (
    MemoryRebuildChannelsFile,
    MemoryRebuildChannelState,
    MemoryRebuildJobState,
    RebuildChannelStatus,
    RebuildFailureCode,
    RebuildJobPhase,
    RebuildJobStatus,
    RebuildSnapshot,
    WorkspaceRebuildIndex,
    append_job_event,
    clear_workspace_active_job,
    create_job_state,
    exclusive_lock,
    get_job_lock_path,
    get_workspace_lock_path,
    instance_owner,
    lease_expiry_iso,
    list_workspace_index_files,
    read_job_channels,
    read_job_state,
    read_workspace_index,
    update_workspace_active_job,
    utcnow,
    utcnow_iso,
    write_job_channels,
    write_job_snapshot,
    write_job_state,
    write_workspace_index,
)
from nekro_agent.services.memory.semantic_writer import persist_cc_task_memory

logger = get_sub_logger("memory.rebuild")
_scheduled_jobs: set[str] = set()


class MemoryRebuildStartResult(BaseModel):
    job_id: str
    reused: bool
    status: str
    message: str


class MemoryRebuildResult(BaseModel):
    job_id: str
    paragraphs_deleted: int = 0
    channels_total: int = 0
    channels_completed: int = 0
    messages_processed: int = 0
    episodic_paragraphs_created: int = 0
    semantic_tasks_replayed: int = 0
    episodes_created: int = 0


class MemoryRebuildChannelStatusView(BaseModel):
    chat_key: str
    status: str
    upper_bound_message_db_id: int
    initial_cursor_db_id: int
    last_cursor_db_id: int
    message_count_total: int
    messages_processed: int
    completed: bool
    progress_ratio: float
    last_error: str | None = None


class MemoryRebuildStatus(BaseModel):
    workspace_id: int
    job_id: str | None = None
    is_running: bool
    status: str
    phase: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    cutoff: str | None = None
    semantic_replayed: bool = False
    cancel_requested: bool = False
    current_chat_key: str | None = None
    last_heartbeat_at: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    overall_progress_percent: float = 0.0
    total_channels: int = 0
    completed_channels: int = 0
    total_messages_processed: int = 0
    channels: list[MemoryRebuildChannelStatusView] = []


def _get_rebuild_cutoff() -> datetime | None:
    lookback_days = max(0, int(config.MEMORY_REBUILD_LOOKBACK_DAYS))
    if lookback_days == 0:
        return None
    return utcnow() - timedelta(days=lookback_days)


def _progress_percent(value: float) -> float:
    return round(max(0.0, min(1.0, value)) * 100, 2)


async def _find_last_message_db_id_before_cutoff(chat_key: str, cutoff: datetime | None) -> int:
    if cutoff is None:
        return 0
    message = (
        await DBChatMessage.filter(chat_key=chat_key, send_timestamp__lt=int(cutoff.timestamp()))
        .order_by("-send_timestamp", "-id")
        .first()
    )
    return message.id if message else 0


async def _find_latest_message_db_id(chat_key: str) -> int:
    message = await DBChatMessage.filter(chat_key=chat_key).order_by("-id").first()
    return message.id if message else 0


async def _count_channel_messages(chat_key: str, start_cursor: int, upper_bound: int) -> int:
    if upper_bound <= start_cursor:
        return 0
    return await DBChatMessage.filter(
        chat_key=chat_key,
        id__gt=start_cursor,
        id__lte=upper_bound,
    ).count()


async def _reset_workspace_structured_memory(workspace_id: int) -> int:
    paragraph_count = await DBMemParagraph.filter(workspace_id=workspace_id).count()
    await DBMemReinforcementLog.filter(workspace_id=workspace_id).delete()
    await DBMemRelation.filter(workspace_id=workspace_id).delete()
    await DBMemEntity.filter(workspace_id=workspace_id).delete()
    await DBMemEpisode.filter(workspace_id=workspace_id).delete()
    await DBMemParagraph.filter(workspace_id=workspace_id).delete()
    await memory_qdrant_manager.delete_by_workspace(workspace_id)
    return paragraph_count


async def _count_semantic_logs(workspace_id: int, cutoff: datetime | None) -> int:
    logs_qs = DBWorkspaceCommLog.filter(workspace_id=workspace_id, direction="CC_TO_NA")
    if cutoff is not None:
        logs_qs = logs_qs.filter(create_time__gte=cutoff)
    return await logs_qs.count()


def _compute_overall_progress(state: MemoryRebuildJobState, channels_file: MemoryRebuildChannelsFile) -> float:
    semantic_total = state.snapshot.semantic_log_count_total
    semantic_ratio = (
        1.0
        if semantic_total <= 0
        else state.progress.processed_semantic_logs / max(1, semantic_total)
    )
    channel_total = sum(channel.message_count_total for channel in channels_file.channels.values())
    channel_processed = sum(channel.message_count_processed for channel in channels_file.channels.values())
    channel_ratio = 1.0 if channel_total <= 0 else channel_processed / max(1, channel_total)
    phase_boost = state.progress.phase_percent
    return min(1.0, 0.05 + 0.15 * semantic_ratio + 0.7 * channel_ratio + 0.1 * phase_boost)


def _refresh_progress(state: MemoryRebuildJobState, channels_file: MemoryRebuildChannelsFile) -> None:
    state.progress.total_channels = len(channels_file.channels)
    state.progress.completed_channels = sum(
        1 for channel in channels_file.channels.values() if channel.status == RebuildChannelStatus.COMPLETED
    )
    state.progress.processed_messages = sum(channel.message_count_processed for channel in channels_file.channels.values())
    state.progress.overall_percent = _compute_overall_progress(state, channels_file)


def _mark_heartbeat(state: MemoryRebuildJobState) -> None:
    now_iso = utcnow_iso()
    state.last_heartbeat_at = now_iso
    state.lease_owner = instance_owner()
    state.lease_expires_at = lease_expiry_iso()


def _persist_state(state: MemoryRebuildJobState, channels_file: MemoryRebuildChannelsFile | None = None) -> None:
    _mark_heartbeat(state)
    write_job_state(state)
    if channels_file is not None:
        write_job_channels(state.job_id, channels_file)


def _mark_failed(
    state: MemoryRebuildJobState,
    *,
    code: RebuildFailureCode,
    reason: str,
    channels_file: MemoryRebuildChannelsFile | None = None,
) -> None:
    state.status = RebuildJobStatus.FAILED
    state.failure_code = code
    state.failure_reason = reason
    state.finished_at = utcnow_iso()
    state.phase = RebuildJobPhase.FINALIZE
    _persist_state(state, channels_file)
    clear_workspace_active_job(state.workspace_id, state.job_id)
    append_job_event(state.job_id, "failed", code=code.value, reason=reason)


def _mark_cancelled(state: MemoryRebuildJobState, channels_file: MemoryRebuildChannelsFile | None = None) -> None:
    state.status = RebuildJobStatus.CANCELLED
    state.failure_code = RebuildFailureCode.CANCELLED_BY_USER
    state.failure_reason = "cancelled by user"
    state.finished_at = utcnow_iso()
    state.phase = RebuildJobPhase.FINALIZE
    _persist_state(state, channels_file)
    clear_workspace_active_job(state.workspace_id, state.job_id)
    append_job_event(state.job_id, "cancelled")


def _mark_completed(state: MemoryRebuildJobState, channels_file: MemoryRebuildChannelsFile) -> None:
    state.status = RebuildJobStatus.COMPLETED
    state.phase = RebuildJobPhase.FINALIZE
    state.progress.phase_percent = 1.0
    _refresh_progress(state, channels_file)
    state.progress.overall_percent = 1.0
    state.finished_at = utcnow_iso()
    _persist_state(state, channels_file)
    clear_workspace_active_job(state.workspace_id, state.job_id)
    append_job_event(state.job_id, "completed")


async def _ensure_initialized(
    state: MemoryRebuildJobState,
    channels_file: MemoryRebuildChannelsFile,
) -> int:
    deleted_paragraphs = 0
    cutoff = datetime.fromisoformat(state.snapshot.cutoff) if state.snapshot.cutoff else None
    if not state.checkpoints.snapshot_built or not state.checkpoints.channels_initialized:
        state.status = RebuildJobStatus.INITIALIZING
        state.phase = RebuildJobPhase.SNAPSHOT
        state.started_at = state.started_at or utcnow_iso()
        workspace_channels = await DBChatChannel.filter(workspace_id=state.workspace_id).order_by("id")
        channels: dict[str, MemoryRebuildChannelState] = {}
        total_messages = 0
        for channel in workspace_channels:
            start_cursor = await _find_last_message_db_id_before_cutoff(channel.chat_key, cutoff)
            upper_bound = await _find_latest_message_db_id(channel.chat_key)
            total = await _count_channel_messages(channel.chat_key, start_cursor, upper_bound)
            channels[channel.chat_key] = MemoryRebuildChannelState(
                status=RebuildChannelStatus.COMPLETED if total == 0 else RebuildChannelStatus.PENDING,
                message_count_total=total,
                message_count_processed=0 if total > 0 else total,
                cursor_start_db_id=start_cursor,
                cursor_current_db_id=start_cursor,
                cursor_upper_bound_db_id=upper_bound,
            )
            total_messages += total
        channels_file.channels = channels
        state.snapshot = RebuildSnapshot(
            cutoff=state.snapshot.cutoff,
            channel_count=len(channels),
            message_count_total=total_messages,
            semantic_log_count_total=await _count_semantic_logs(state.workspace_id, cutoff),
        )
        state.checkpoints.snapshot_built = True
        state.checkpoints.channels_initialized = True
        state.progress.total_channels = len(channels)
        _refresh_progress(state, channels_file)
        write_job_snapshot(state.job_id, state.snapshot)
        _persist_state(state, channels_file)
        append_job_event(state.job_id, "snapshot_built", channels=len(channels), messages=total_messages)

    if state.cancel_requested:
        _mark_cancelled(state, channels_file)
        return deleted_paragraphs

    if not state.checkpoints.memory_cleared:
        state.phase = RebuildJobPhase.CLEAR_MEMORY
        state.progress.phase_percent = 0.3
        _persist_state(state, channels_file)
        deleted_paragraphs = await _reset_workspace_structured_memory(state.workspace_id)
        state.checkpoints.memory_cleared = True
        state.progress.phase_percent = 1.0
        _persist_state(state, channels_file)
        append_job_event(state.job_id, "memory_cleared", paragraphs_deleted=deleted_paragraphs)
    return deleted_paragraphs


async def _replay_cc_semantic_memories(state: MemoryRebuildJobState, channels_file: MemoryRebuildChannelsFile) -> int:
    if state.checkpoints.semantic_replayed:
        return state.progress.processed_semantic_logs
    state.status = RebuildJobStatus.REPLAYING_SEMANTIC
    state.phase = RebuildJobPhase.REPLAY_SEMANTIC
    _persist_state(state, channels_file)
    cutoff = datetime.fromisoformat(state.snapshot.cutoff) if state.snapshot.cutoff else None
    logs_qs = DBWorkspaceCommLog.filter(workspace_id=state.workspace_id, direction="CC_TO_NA")
    if cutoff is not None:
        logs_qs = logs_qs.filter(create_time__gte=cutoff)
    logs = await logs_qs.order_by("create_time")

    replayed = state.progress.processed_semantic_logs
    for reply_log in logs[replayed:]:
        if state.cancel_requested:
            _mark_cancelled(state, channels_file)
            return replayed
        if not reply_log.content.strip():
            replayed += 1
            state.progress.processed_semantic_logs = replayed
            state.progress.phase_percent = replayed / max(1, state.snapshot.semantic_log_count_total)
            _persist_state(state, channels_file)
            continue
        task_log = await DBWorkspaceCommLog.filter(
            workspace_id=state.workspace_id,
            task_id=reply_log.task_id,
            direction="USER_TO_CC",
        ).first()
        if task_log is None:
            task_log = await DBWorkspaceCommLog.filter(
                workspace_id=state.workspace_id,
                task_id=reply_log.task_id,
                direction="NA_TO_CC",
            ).first()
        if task_log is not None and task_log.content.strip():
            await persist_cc_task_memory(
                workspace_id=state.workspace_id,
                task_content=task_log.content,
                result_content=reply_log.content,
                source_chat_key=reply_log.source_chat_key or "__user__",
                origin_ref=reply_log.task_id or str(reply_log.id),
                event_time=reply_log.create_time,
            )
        replayed += 1
        state.progress.processed_semantic_logs = replayed
        state.progress.phase_percent = replayed / max(1, state.snapshot.semantic_log_count_total)
        _refresh_progress(state, channels_file)
        _persist_state(state, channels_file)
        await asyncio.sleep(0)

    state.checkpoints.semantic_replayed = True
    state.progress.phase_percent = 1.0
    _persist_state(state, channels_file)
    append_job_event(state.job_id, "semantic_replayed", count=replayed)
    return replayed


async def _rebuild_channels(
    state: MemoryRebuildJobState,
    channels_file: MemoryRebuildChannelsFile,
) -> tuple[int, int]:
    state.status = RebuildJobStatus.REBUILDING_CHANNELS
    state.phase = RebuildJobPhase.CHANNEL_BATCH
    _persist_state(state, channels_file)

    total_messages_processed = 0
    total_paragraphs_created = 0
    for chat_key, channel_state in channels_file.channels.items():
        if channel_state.status == RebuildChannelStatus.COMPLETED:
            continue
        if state.cancel_requested:
            _mark_cancelled(state, channels_file)
            return total_messages_processed, total_paragraphs_created

        state.current_chat_key = chat_key
        _persist_state(state, channels_file)

        while True:
            if state.cancel_requested:
                _mark_cancelled(state, channels_file)
                return total_messages_processed, total_paragraphs_created

            before_cursor = channel_state.cursor_current_db_id
            upper_bound = channel_state.cursor_upper_bound_db_id
            if upper_bound <= before_cursor or channel_state.message_count_total <= channel_state.message_count_processed:
                channel_state.status = RebuildChannelStatus.COMPLETED
                break

            channel_state.status = RebuildChannelStatus.RUNNING
            channel_state.last_batch_started_at = utcnow_iso()
            _persist_state(state, channels_file)

            consolidation = await consolidate_workspace(
                state.workspace_id,
                chat_key,
                max_message_db_id=upper_bound or None,
                start_after_db_id=before_cursor,
                persist_progress=False,
            )
            next_cursor = max(before_cursor, consolidation.last_processed_message_db_id)
            if consolidation.errors:
                channel_state.status = RebuildChannelStatus.FAILED
                channel_state.last_error = "; ".join(consolidation.errors)
                channel_state.retry_count += 1
                _persist_state(state, channels_file)
                _mark_failed(
                    state,
                    code=RebuildFailureCode.CHANNEL_BATCH_FAILED,
                    reason=f"{chat_key}: {channel_state.last_error}",
                    channels_file=channels_file,
                )
                return total_messages_processed, total_paragraphs_created

            if consolidation.messages_processed <= 0 or next_cursor <= before_cursor:
                channel_state.status = RebuildChannelStatus.FAILED
                channel_state.last_error = "rebuild batch finished without forward progress"
                channel_state.retry_count += 1
                _persist_state(state, channels_file)
                _mark_failed(
                    state,
                    code=RebuildFailureCode.NO_FORWARD_PROGRESS,
                    reason=f"{chat_key}: no forward progress",
                    channels_file=channels_file,
                )
                return total_messages_processed, total_paragraphs_created

            channel_state.cursor_current_db_id = next_cursor
            channel_state.message_count_processed = min(
                channel_state.message_count_total,
                channel_state.message_count_processed + consolidation.messages_processed,
            )
            channel_state.last_batch_finished_at = utcnow_iso()
            channel_state.last_error = None
            total_messages_processed += consolidation.messages_processed
            total_paragraphs_created += consolidation.paragraphs_created
            _refresh_progress(state, channels_file)
            _persist_state(state, channels_file)

            if (
                channel_state.cursor_current_db_id >= upper_bound
                or channel_state.message_count_processed >= channel_state.message_count_total
            ):
                channel_state.status = RebuildChannelStatus.COMPLETED
                channel_state.last_batch_finished_at = utcnow_iso()
                _refresh_progress(state, channels_file)
                _persist_state(state, channels_file)
                break
            await asyncio.sleep(0.05)

        append_job_event(
            state.job_id,
            "channel_completed",
            chat_key=chat_key,
            processed=channel_state.message_count_processed,
            total=channel_state.message_count_total,
        )
    return total_messages_processed, total_paragraphs_created


async def rebuild_workspace_memories(job_id: str) -> MemoryRebuildResult:
    state = read_job_state(job_id)
    if state is None:
        raise RuntimeError(f"memory rebuild job not found: {job_id}")
    channels_file = read_job_channels(job_id)
    result = MemoryRebuildResult(job_id=job_id)

    deleted_paragraphs = await _ensure_initialized(state, channels_file)
    result.paragraphs_deleted = deleted_paragraphs
    if state.is_terminal():
        return result

    result.semantic_tasks_replayed = await _replay_cc_semantic_memories(state, channels_file)
    if state.is_terminal():
        return result

    result.messages_processed, result.episodic_paragraphs_created = await _rebuild_channels(state, channels_file)
    if state.is_terminal():
        return result

    state.status = RebuildJobStatus.FINALIZING
    state.phase = RebuildJobPhase.FINALIZE
    state.progress.phase_percent = 0.5
    _persist_state(state, channels_file)
    result.channels_total = len(channels_file.channels)
    result.channels_completed = sum(
        1 for channel in channels_file.channels.values() if channel.status == RebuildChannelStatus.COMPLETED
    )
    result.episodes_created = await DBMemEpisode.filter(workspace_id=state.workspace_id).count()
    _mark_completed(state, channels_file)
    return result


def _schedule_job_runner(job_id: str) -> bool:
    if job_id in _scheduled_jobs:
        return False
    _scheduled_jobs.add(job_id)

    async def _runner() -> None:
        try:
            with exclusive_lock(get_job_lock_path(job_id)) as locked:
                if not locked:
                    return
                state = read_job_state(job_id)
                if state is None or state.is_terminal():
                    return
                if state.cancel_requested and state.status == RebuildJobStatus.QUEUED:
                    _mark_cancelled(state, read_job_channels(job_id))
                    return
                result = await rebuild_workspace_memories(job_id)
                logger.info(
                    "记忆重建完成: workspace=%s, job=%s, messages=%s, episodic=%s, semantic=%s",
                    state.workspace_id,
                    result.job_id,
                    result.messages_processed,
                    result.episodic_paragraphs_created,
                    result.semantic_tasks_replayed,
                )
        except Exception as e:
            logger.exception(f"工作区记忆重建失败: job={job_id}")
            state = read_job_state(job_id)
            if state is not None and not state.is_terminal():
                _mark_failed(state, code=RebuildFailureCode.UNKNOWN, reason=str(e), channels_file=read_job_channels(job_id))
        finally:
            _scheduled_jobs.discard(job_id)

    asyncio.create_task(_runner())
    return True


def start_workspace_memory_rebuild(
    workspace_id: int,
    *,
    requested_by: str | None = None,
    request_id: str | None = None,
) -> MemoryRebuildStartResult:
    ensure_memory_system_enabled(MemoryOperation.REBUILD)

    cutoff = _get_rebuild_cutoff()
    with exclusive_lock(get_workspace_lock_path(workspace_id)) as locked:
        if not locked:
            index = read_workspace_index(workspace_id)
            active_job_id = index.active_job_id or index.latest_job_id
            if active_job_id:
                state = read_job_state(active_job_id)
                if state is not None:
                    return MemoryRebuildStartResult(
                        job_id=active_job_id,
                        reused=True,
                        status=state.status.value,
                        message="当前工作区已有记忆重建任务在运行，已返回现有任务",
                    )
            raise RuntimeError("workspace rebuild lock busy")

        index = read_workspace_index(workspace_id)
        active_job_id = index.active_job_id
        if active_job_id:
            active_state = read_job_state(active_job_id)
            if active_state is not None and active_state.is_active():
                if active_state.lease_expired():
                    active_state.status = RebuildJobStatus.STALLED
                    active_state.recovery_count += 1
                    write_job_state(active_state)
                    append_job_event(active_job_id, "stalled", recovery_count=active_state.recovery_count)
                    _schedule_job_runner(active_job_id)
                return MemoryRebuildStartResult(
                    job_id=active_job_id,
                    reused=True,
                    status=active_state.status.value,
                    message="当前工作区已有记忆重建任务，已复用现有任务",
                )
            if active_state is None or active_state.is_terminal():
                index.active_job_id = None
                write_workspace_index(index)

        state = create_job_state(
            workspace_id,
            requested_by=requested_by,
            request_id=request_id,
            cutoff=cutoff.isoformat() if cutoff else None,
        )
        update_workspace_active_job(workspace_id, state.job_id)
        _schedule_job_runner(state.job_id)
        return MemoryRebuildStartResult(
            job_id=state.job_id,
            reused=False,
            status=state.status.value,
            message="记忆重建任务已创建",
        )


def cancel_workspace_memory_rebuild(workspace_id: int) -> MemoryRebuildStartResult:
    ensure_memory_system_enabled(MemoryOperation.REBUILD)

    with exclusive_lock(get_workspace_lock_path(workspace_id)) as locked:
        if not locked:
            raise RuntimeError("workspace rebuild lock busy")
        index = read_workspace_index(workspace_id)
        job_id = index.active_job_id
        if not job_id:
            return MemoryRebuildStartResult(job_id="", reused=True, status="idle", message="当前没有运行中的记忆重建任务")
        state = read_job_state(job_id)
        if state is None or state.is_terminal():
            clear_workspace_active_job(workspace_id, job_id)
            return MemoryRebuildStartResult(job_id=job_id, reused=True, status="idle", message="当前没有运行中的记忆重建任务")
        state.cancel_requested = True
        state.status = RebuildJobStatus.CANCEL_REQUESTED
        write_job_state(state)
        append_job_event(job_id, "cancel_requested")
        _schedule_job_runner(job_id)
        return MemoryRebuildStartResult(
            job_id=job_id,
            reused=True,
            status=state.status.value,
            message="已请求取消记忆重建任务",
        )


def _build_channel_status_view(chat_key: str, state: MemoryRebuildChannelState) -> MemoryRebuildChannelStatusView:
    ratio = 1.0 if state.message_count_total <= 0 else state.message_count_processed / max(1, state.message_count_total)
    return MemoryRebuildChannelStatusView(
        chat_key=chat_key,
        status=state.status.value,
        upper_bound_message_db_id=state.cursor_upper_bound_db_id,
        initial_cursor_db_id=state.cursor_start_db_id,
        last_cursor_db_id=state.cursor_current_db_id,
        message_count_total=state.message_count_total,
        messages_processed=state.message_count_processed,
        completed=state.status == RebuildChannelStatus.COMPLETED,
        progress_ratio=max(0.0, min(1.0, ratio)),
        last_error=state.last_error,
    )


async def get_workspace_memory_rebuild_status(workspace_id: int) -> MemoryRebuildStatus:
    index = read_workspace_index(workspace_id)
    job_id = index.active_job_id or index.latest_job_id
    if not job_id:
        return MemoryRebuildStatus(workspace_id=workspace_id, is_running=False, status="idle")
    state = read_job_state(job_id)
    if state is None:
        return MemoryRebuildStatus(workspace_id=workspace_id, is_running=False, status="idle")
    channels_file = read_job_channels(job_id)
    _refresh_progress(state, channels_file)
    write_job_state(state)
    channels = [
        _build_channel_status_view(chat_key, channel_state)
        for chat_key, channel_state in channels_file.channels.items()
    ]
    is_running = state.is_active() and state.status != RebuildJobStatus.STALLED
    return MemoryRebuildStatus(
        workspace_id=workspace_id,
        job_id=job_id,
        is_running=is_running,
        status=state.status.value,
        phase=state.phase.value,
        started_at=state.started_at,
        finished_at=state.finished_at,
        cutoff=state.snapshot.cutoff,
        semantic_replayed=state.checkpoints.semantic_replayed,
        cancel_requested=state.cancel_requested,
        current_chat_key=state.current_chat_key,
        last_heartbeat_at=state.last_heartbeat_at,
        failure_code=None if state.failure_code == RebuildFailureCode.NONE else state.failure_code.value,
        failure_reason=state.failure_reason,
        overall_progress_percent=_progress_percent(state.progress.overall_percent),
        total_channels=state.progress.total_channels,
        completed_channels=state.progress.completed_channels,
        total_messages_processed=state.progress.processed_messages,
        channels=channels,
    )


async def recover_pending_memory_rebuilds() -> int:
    if not is_memory_system_enabled():
        return 0

    recovered = 0
    for index_path in list_workspace_index_files():
        try:
            index = WorkspaceRebuildIndex.model_validate_json(index_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        active_job_id = index.active_job_id
        if not active_job_id:
            continue
        state = read_job_state(active_job_id)
        if state is None:
            clear_workspace_active_job(index.workspace_id, active_job_id)
            continue
        if state.is_terminal():
            clear_workspace_active_job(index.workspace_id, active_job_id)
            continue
        if state.lease_expired():
            state.status = RebuildJobStatus.STALLED
            state.recovery_count += 1
            write_job_state(state)
            append_job_event(active_job_id, "recovery_scheduled", recovery_count=state.recovery_count)
            if _schedule_job_runner(active_job_id):
                recovered += 1
    if recovered > 0:
        logger.info(f"已恢复未完成的记忆重建任务: {recovered} 个工作区")
    return recovered
