from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from pydantic import BaseModel, Field

from nekro_agent.core.os_env import OsEnv

DEFAULT_REF_TTL_SECONDS = 7 * 24 * 60 * 60
MAX_REF_ENTRIES = 50000


class RefIndexEntry(BaseModel):
    ref_idx: str
    chat_key: str
    message_id: str = ""
    sender_id: str = ""
    sender_name: str = ""
    content_text: str = ""
    attachments: list[str] = Field(default_factory=list)
    is_bot: bool = False
    created_at: float = Field(default_factory=time.time)


class RefIndexStore:
    """OpenClaw ref_idx/msg_idx 持久化索引。

    OpenClaw 渠道大量引用关系依赖 message_scene.ext / msg_elements 中的索引，
    这里持久化近期索引，便于引用上下文恢复和防自回复。
    """

    def __init__(self, path: Path | None = None, ttl_seconds: int = DEFAULT_REF_TTL_SECONDS) -> None:
        self.path = path or Path(OsEnv.DATA_DIR) / "adapters" / "qqbot_openclaw" / "ref-index.jsonl"
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, RefIndexEntry] = {}
        self._lock = asyncio.Lock()
        self._loaded = False

    async def load(self) -> None:
        async with self._lock:
            if self._loaded:
                return
            await asyncio.to_thread(self._load_sync)
            self._loaded = True

    async def get(self, ref_idx: str) -> RefIndexEntry | None:
        await self.load()
        entry = self._entries.get(str(ref_idx))
        if not entry:
            return None
        if self._is_expired(entry):
            async with self._lock:
                self._entries.pop(entry.ref_idx, None)
            return None
        return entry

    async def put(self, entry: RefIndexEntry) -> None:
        await self.load()
        if not entry.ref_idx:
            return
        async with self._lock:
            self._entries[entry.ref_idx] = entry
            self._trim_locked()
            await asyncio.to_thread(self._append_sync, entry)

    async def clear(self) -> int:
        await self.load()
        async with self._lock:
            count = len(self._entries)
            self._entries.clear()
            await asyncio.to_thread(self._rewrite_sync)
            return count

    async def stats(self) -> dict[str, int]:
        await self.load()
        return {"entries": len(self._entries), "ttl_seconds": self.ttl_seconds}

    def format_for_context(self, entry: RefIndexEntry) -> str:
        sender = entry.sender_name or entry.sender_id or "unknown"
        lines = ["引用消息开始", f"{sender}: {entry.content_text or '[非文本消息]'}"]
        lines.extend(entry.attachments)
        lines.append("引用消息结束")
        return "\n".join(lines)

    def _load_sync(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            return

        now = time.time()
        entries: dict[str, RefIndexEntry] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = RefIndexEntry.model_validate(json.loads(line))
            except Exception:
                continue
            if now - entry.created_at <= self.ttl_seconds:
                entries[entry.ref_idx] = entry
        self._entries = entries
        self._trim_locked()
        self._rewrite_sync()

    def _append_sync(self, entry: RefIndexEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

    def _rewrite_sync(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = "\n".join(entry.model_dump_json() for entry in self._entries.values())
        self.path.write_text(f"{data}\n" if data else "", encoding="utf-8")

    def _trim_locked(self) -> None:
        now = time.time()
        self._entries = {
            key: entry
            for key, entry in self._entries.items()
            if now - entry.created_at <= self.ttl_seconds
        }
        if len(self._entries) <= MAX_REF_ENTRIES:
            return
        keep = sorted(self._entries.values(), key=lambda item: item.created_at)[-MAX_REF_ENTRIES:]
        self._entries = {entry.ref_idx: entry for entry in keep}

    def _is_expired(self, entry: RefIndexEntry) -> bool:
        return time.time() - entry.created_at > self.ttl_seconds
