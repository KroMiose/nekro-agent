"""记忆重建文件状态仓库。"""

from __future__ import annotations

import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Iterator, TypeVar

from pydantic import BaseModel, Field

from nekro_agent.core.os_env import APP_SYSTEM_DIR, OsEnv

REBUILD_SYSTEM_DIR = Path(APP_SYSTEM_DIR) / "memory" / "rebuilds"
REBUILD_WORKSPACE_DIR = REBUILD_SYSTEM_DIR / "workspaces"
REBUILD_JOB_DIR = REBUILD_SYSTEM_DIR / "jobs"
REBUILD_LEASE_SECONDS = 30
TModel = TypeVar("TModel", bound=BaseModel)


class RebuildJobStatus(StrEnum):
    QUEUED = "queued"
    INITIALIZING = "initializing"
    REPLAYING_SEMANTIC = "replaying_semantic"
    REBUILDING_CHANNELS = "rebuilding_channels"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    STALLED = "stalled"


class RebuildJobPhase(StrEnum):
    QUEUED = "queued"
    SNAPSHOT = "snapshot"
    CLEAR_MEMORY = "clear_memory"
    REPLAY_SEMANTIC = "replay_semantic"
    CHANNEL_BATCH = "channel_batch"
    FINALIZE = "finalize"


class RebuildFailureCode(StrEnum):
    NONE = "none"
    INIT_FAILED = "init_failed"
    SEMANTIC_REPLAY_FAILED = "semantic_replay_failed"
    CHANNEL_BATCH_FAILED = "channel_batch_failed"
    NO_FORWARD_PROGRESS = "no_forward_progress"
    RECOVERY_EXHAUSTED = "recovery_exhausted"
    CANCELLED_BY_USER = "cancelled_by_user"
    UNKNOWN = "unknown"


class RebuildChannelStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RebuildCheckpoints(BaseModel):
    snapshot_built: bool = False
    channels_initialized: bool = False
    memory_cleared: bool = False
    semantic_replayed: bool = False


class RebuildSnapshot(BaseModel):
    cutoff: str | None = None
    channel_count: int = 0
    message_count_total: int = 0
    semantic_log_count_total: int = 0


class RebuildProgress(BaseModel):
    phase_percent: float = 0.0
    overall_percent: float = 0.0
    processed_messages: int = 0
    processed_semantic_logs: int = 0
    completed_channels: int = 0
    total_channels: int = 0


class MemoryRebuildChannelState(BaseModel):
    status: RebuildChannelStatus = RebuildChannelStatus.PENDING
    message_count_total: int = 0
    message_count_processed: int = 0
    cursor_start_db_id: int = 0
    cursor_current_db_id: int = 0
    cursor_upper_bound_db_id: int = 0
    last_batch_started_at: str | None = None
    last_batch_finished_at: str | None = None
    last_error: str | None = None
    retry_count: int = 0


class MemoryRebuildChannelsFile(BaseModel):
    channels: dict[str, MemoryRebuildChannelState] = Field(default_factory=dict)


class WorkspaceRebuildIndex(BaseModel):
    workspace_id: int
    active_job_id: str | None = None
    latest_job_id: str | None = None
    updated_at: str


class MemoryRebuildJobState(BaseModel):
    job_id: str
    workspace_id: int
    status: RebuildJobStatus
    phase: RebuildJobPhase
    requested_by: str | None = None
    request_id: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    last_heartbeat_at: str | None = None
    lease_owner: str | None = None
    lease_expires_at: str | None = None
    cancel_requested: bool = False
    recovery_count: int = 0
    failure_code: RebuildFailureCode = RebuildFailureCode.NONE
    failure_reason: str | None = None
    current_chat_key: str | None = None
    checkpoints: RebuildCheckpoints = Field(default_factory=RebuildCheckpoints)
    snapshot: RebuildSnapshot = Field(default_factory=RebuildSnapshot)
    progress: RebuildProgress = Field(default_factory=RebuildProgress)

    def is_terminal(self) -> bool:
        return self.status in {
            RebuildJobStatus.COMPLETED,
            RebuildJobStatus.FAILED,
            RebuildJobStatus.CANCELLED,
        }

    def is_active(self) -> bool:
        return not self.is_terminal()

    def lease_expired(self, now: datetime | None = None) -> bool:
        if not self.lease_expires_at:
            return True
        reference = now or datetime.now(timezone.utc)
        return datetime.fromisoformat(self.lease_expires_at) <= reference


class RebuildEventLine(BaseModel):
    ts: str
    event: str
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


def ensure_rebuild_dirs() -> None:
    REBUILD_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    REBUILD_JOB_DIR.mkdir(parents=True, exist_ok=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    return utcnow().isoformat()


def lease_expiry_iso(now: datetime | None = None) -> str:
    reference = now or utcnow()
    return (reference + timedelta(seconds=REBUILD_LEASE_SECONDS)).isoformat()


def generate_job_id() -> str:
    timestamp = utcnow().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(3)
    return f"memrb_{timestamp}_{suffix}"


def instance_owner() -> str:
    return OsEnv.INSTANCE_NAME or f"pid-{os.getpid()}"


def get_workspace_index_path(workspace_id: int) -> Path:
    ensure_rebuild_dirs()
    return REBUILD_WORKSPACE_DIR / f"{workspace_id}.json"


def get_workspace_lock_path(workspace_id: int) -> Path:
    ensure_rebuild_dirs()
    return REBUILD_WORKSPACE_DIR / f"{workspace_id}.lock"


def get_job_dir(job_id: str) -> Path:
    ensure_rebuild_dirs()
    return REBUILD_JOB_DIR / job_id


def get_job_state_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "state.json"


def get_job_channels_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "channels.json"


def get_job_snapshot_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "snapshot.json"


def get_job_lock_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "lock"


def get_job_events_path(job_id: str) -> Path:
    return get_job_dir(job_id) / "events.log"


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    tmp_path.replace(path)


def _write_model(path: Path, model: BaseModel) -> None:
    _atomic_write_text(path, model.model_dump_json(indent=2))


def _read_model(path: Path, model_type: type[TModel]) -> TModel | None:
    try:
        if not path.exists():
            return None
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_workspace_index(workspace_id: int) -> WorkspaceRebuildIndex:
    existing = _read_model(get_workspace_index_path(workspace_id), WorkspaceRebuildIndex)
    if existing is not None:
        return existing
    return WorkspaceRebuildIndex(
        workspace_id=workspace_id,
        active_job_id=None,
        latest_job_id=None,
        updated_at=utcnow_iso(),
    )


def write_workspace_index(index: WorkspaceRebuildIndex) -> None:
    index.updated_at = utcnow_iso()
    _write_model(get_workspace_index_path(index.workspace_id), index)


def read_job_state(job_id: str) -> MemoryRebuildJobState | None:
    return _read_model(get_job_state_path(job_id), MemoryRebuildJobState)


def write_job_state(state: MemoryRebuildJobState) -> None:
    get_job_dir(state.job_id).mkdir(parents=True, exist_ok=True)
    _write_model(get_job_state_path(state.job_id), state)


def read_job_channels(job_id: str) -> MemoryRebuildChannelsFile:
    existing = _read_model(get_job_channels_path(job_id), MemoryRebuildChannelsFile)
    return existing or MemoryRebuildChannelsFile()


def write_job_channels(job_id: str, channels: MemoryRebuildChannelsFile) -> None:
    get_job_dir(job_id).mkdir(parents=True, exist_ok=True)
    _write_model(get_job_channels_path(job_id), channels)


def write_job_snapshot(job_id: str, snapshot: RebuildSnapshot) -> None:
    get_job_dir(job_id).mkdir(parents=True, exist_ok=True)
    _write_model(get_job_snapshot_path(job_id), snapshot)


def append_job_event(job_id: str, event: str, **payload: str | int | float | bool | None) -> None:
    get_job_dir(job_id).mkdir(parents=True, exist_ok=True)
    line = RebuildEventLine(ts=utcnow_iso(), event=event, payload=payload)
    with get_job_events_path(job_id).open("a", encoding="utf-8") as f:
        f.write(line.model_dump_json() + "\n")


def create_job_state(
    workspace_id: int,
    *,
    requested_by: str | None,
    request_id: str | None,
    cutoff: str | None,
) -> MemoryRebuildJobState:
    state = MemoryRebuildJobState(
        job_id=generate_job_id(),
        workspace_id=workspace_id,
        status=RebuildJobStatus.QUEUED,
        phase=RebuildJobPhase.QUEUED,
        requested_by=requested_by,
        request_id=request_id,
        created_at=utcnow_iso(),
        lease_owner=instance_owner(),
        snapshot=RebuildSnapshot(cutoff=cutoff),
    )
    write_job_state(state)
    write_job_channels(state.job_id, MemoryRebuildChannelsFile())
    append_job_event(state.job_id, "created", workspace_id=workspace_id, request_id=request_id)
    return state


def update_workspace_active_job(workspace_id: int, job_id: str) -> None:
    index = read_workspace_index(workspace_id)
    index.active_job_id = job_id
    index.latest_job_id = job_id
    write_workspace_index(index)


def clear_workspace_active_job(workspace_id: int, job_id: str | None = None) -> None:
    index = read_workspace_index(workspace_id)
    if job_id is not None and index.active_job_id != job_id:
        return
    index.active_job_id = None
    write_workspace_index(index)


def list_workspace_index_files() -> list[Path]:
    ensure_rebuild_dirs()
    return sorted(REBUILD_WORKSPACE_DIR.glob("*.json"))


@contextmanager
def exclusive_lock(path: Path) -> Iterator[bool]:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield True
        except BlockingIOError:
            yield False
        finally:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
