"""知识库索引 staging 与原子切换语义测试。

两条核心不变量：
1. 全部 chunk 的 embedding 成功之前，绝不触碰既有的 chunk 行 / 向量点 / 规范化文本；
2. 重建失败时，原本 ready 的索引必须继续被 search_service 选中，而不是变成 failed 后从搜索里消失。
"""

import asyncio
import hashlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

from nekro_agent.services.kb import index_service, library_index_service
from nekro_agent.services.kb.chunker import ChunkDraft
from nekro_agent.services.kb.search_service import _source_is_search_ready

_NEW_TEXT = "新的规范化文本"
_OLD_TEXT = "旧的规范化文本"


def _draft(content: str) -> ChunkDraft:
    return ChunkDraft(heading_path="", content=content, char_start=0, char_end=len(content))


def _expected_rel_path(document_id: int, text: str) -> str:
    return f"{document_id}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]}.md"


@dataclass
class _FakeDocument:
    id: int = 1
    workspace_id: int = 1
    is_enabled: bool = True
    source_path: str = "source.md"
    file_name: str = "source.md"
    title: str = "doc"
    normalized_text_path: str = "1.md"
    normalized_text_hash: str = "old-hash"
    extract_status: str = "ready"
    sync_status: str = "ready"
    last_error: str | None = None
    chunk_count: int = 3
    last_indexed_at: object = "old-timestamp"
    saved_fields: list[list[str]] = field(default_factory=list)

    async def save(self, update_fields: list[str] | None = None, using_db: object = None) -> None:
        self.saved_fields.append(list(update_fields or []))


@dataclass
class _IndexHarness:
    document: _FakeDocument
    normalized_dir: Path
    live_file: Path
    swap_kwargs: list[dict[str, object]]

    @property
    def new_file(self) -> Path:
        return self.normalized_dir / _expected_rel_path(self.document.id, _NEW_TEXT)


def _install_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    embedding_ok: bool,
    document: _FakeDocument | None = None,
) -> _IndexHarness:
    """把 index_document 的外部依赖（DB / 文件 / 向量库）替换成可观测的假实现。"""
    normalized_dir = Path(tempfile.mkdtemp(prefix="nekro-kb-index-"))
    document = document or _FakeDocument()
    live_file = normalized_dir / document.normalized_text_path
    live_file.write_text(_OLD_TEXT, "utf-8")
    swap_kwargs: list[dict[str, object]] = []

    async def _noop(*_args: object, **_kwargs: object) -> None:
        return None

    async def _fake_embed(texts: list[str]) -> list[list[float] | None]:
        return [[1.0] if embedding_ok else None for _ in texts]

    async def _recording_swap(*_args: object, **kwargs: object) -> int:
        # 忠实模拟真实 _swap_document_index：元数据在同一事务内一并 flip
        swap_kwargs.append(kwargs)
        assert document is not None
        document.normalized_text_path = str(kwargs["normalized_rel_path"])
        document.normalized_text_hash = str(kwargs["normalized_text_hash"])
        document.chunk_count = 7
        document.extract_status = "ready"
        document.sync_status = "ready"
        document.last_indexed_at = "new-timestamp"
        document.last_error = None
        return 7

    monkeypatch.setattr(index_service, "_publish_index_progress", _noop)
    monkeypatch.setattr(index_service, "detect_and_sync_document_references", _noop)
    monkeypatch.setattr(index_service, "embed_kb_batch", _fake_embed)
    monkeypatch.setattr(index_service, "_swap_document_index", _recording_swap)
    monkeypatch.setattr(index_service, "extract_source_file", lambda *_args: SimpleNamespace(text=_NEW_TEXT))
    monkeypatch.setattr(
        index_service,
        "WorkspaceService",
        SimpleNamespace(
            ensure_kb_dirs=lambda _workspace_id: None,
            resolve_kb_source_path=lambda _workspace_id, _path: normalized_dir / "source.md",
            resolve_kb_normalized_path=lambda _workspace_id, rel_path: normalized_dir / rel_path,
        ),
    )

    return _IndexHarness(
        document=document,
        normalized_dir=normalized_dir,
        live_file=live_file,
        swap_kwargs=swap_kwargs,
    )


# --------------------------------------------------------------------------------------
# staging：embedding 全部成功前不触碰任何既有索引数据
# --------------------------------------------------------------------------------------


@pytest.fixture
def _silence_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(index_service, "_publish_index_progress", _noop)
    monkeypatch.setattr(library_index_service, "_publish_index_progress", _noop)


@pytest.mark.usefixtures("_silence_progress")
async def test_embed_chunk_drafts_returns_vectors_aligned_with_drafts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_embed_kb_batch(texts: list[str]) -> list[list[float] | None]:
        return [[float(len(text))] for text in texts]

    monkeypatch.setattr(index_service, "embed_kb_batch", fake_embed_kb_batch)

    vectors = await index_service._embed_chunk_drafts(
        SimpleNamespace(id=1, workspace_id=1),  # type: ignore[arg-type]
        [_draft("a"), _draft("bb"), _draft("ccc")],
        started_at=0,
    )

    assert vectors == [[1.0], [2.0], [3.0]]


@pytest.mark.usefixtures("_silence_progress")
async def test_embed_chunk_drafts_raises_when_any_embedding_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_embed_kb_batch(texts: list[str]) -> list[list[float] | None]:
        return [None if text == "bb" else [1.0] for text in texts]

    monkeypatch.setattr(index_service, "embed_kb_batch", fake_embed_kb_batch)

    with pytest.raises(RuntimeError, match="1/3"):
        await index_service._embed_chunk_drafts(
            SimpleNamespace(id=1, workspace_id=1),  # type: ignore[arg-type]
            [_draft("a"), _draft("bb"), _draft("ccc")],
            started_at=0,
        )


@pytest.mark.usefixtures("_silence_progress")
async def test_embed_chunk_drafts_raises_when_provider_returns_short_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """provider 少返回条目时必须算作失败，不能静默丢块。"""

    async def fake_embed_kb_batch(texts: list[str]) -> list[list[float] | None]:
        return [[1.0] for _ in texts[:-1]]

    monkeypatch.setattr(index_service, "embed_kb_batch", fake_embed_kb_batch)

    with pytest.raises(RuntimeError, match="1/3"):
        await index_service._embed_chunk_drafts(
            SimpleNamespace(id=1, workspace_id=1),  # type: ignore[arg-type]
            [_draft("a"), _draft("bb"), _draft("ccc")],
            started_at=0,
        )


@pytest.mark.usefixtures("_silence_progress")
async def test_library_embed_chunk_drafts_raises_when_any_embedding_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_embed_kb_batch(texts: list[str]) -> list[list[float] | None]:
        return [None for _ in texts]

    monkeypatch.setattr(library_index_service, "embed_kb_batch", fake_embed_kb_batch)

    with pytest.raises(RuntimeError, match="2/2"):
        await library_index_service._embed_chunk_drafts(
            SimpleNamespace(id=1),  # type: ignore[arg-type]
            [_draft("a"), _draft("bb")],
            started_at=0,
        )


# --------------------------------------------------------------------------------------
# 失败路径：旧索引必须保持对 search_service 可见
# --------------------------------------------------------------------------------------


async def test_failed_rebuild_keeps_existing_index_searchable(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _install_harness(monkeypatch, embedding_ok=False)

    with pytest.raises(RuntimeError, match="知识库向量化失败"):
        await index_service.rebuild_document(harness.document)  # type: ignore[arg-type]

    document = harness.document
    # 关键断言：失败后仍然满足 search_workspace_kb 的入选条件
    assert _source_is_search_ready(document) is True  # type: ignore[arg-type]
    assert (document.extract_status, document.sync_status) == ("ready", "ready")
    # 旧索引的统计与文本指针原样保留
    assert document.chunk_count == 3
    assert document.normalized_text_path == "1.md"
    assert document.normalized_text_hash == "old-hash"
    assert document.last_indexed_at == "old-timestamp"
    assert document.last_error is not None
    # 切换阶段完全没被调用，线上规范化文本没被动过，staging 文件已清理
    assert harness.swap_kwargs == []
    assert harness.live_file.read_text("utf-8") == _OLD_TEXT
    assert not harness.new_file.exists()


async def test_failed_first_index_is_marked_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """没有可用旧索引时不做保护性回退，仍如实标记 failed。"""
    fresh = _FakeDocument(extract_status="pending", sync_status="pending", chunk_count=0)
    harness = _install_harness(monkeypatch, embedding_ok=False, document=fresh)

    with pytest.raises(RuntimeError, match="知识库向量化失败"):
        await index_service.rebuild_document(harness.document)  # type: ignore[arg-type]

    assert (fresh.extract_status, fresh.sync_status) == ("failed", "failed")
    assert _source_is_search_ready(fresh) is False  # type: ignore[arg-type]
    assert not harness.new_file.exists()


async def test_cancelled_rebuild_keeps_existing_index_searchable(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _install_harness(monkeypatch, embedding_ok=True)

    async def _cancel(*_args: object, **_kwargs: object) -> int:
        raise asyncio.CancelledError

    monkeypatch.setattr(index_service, "_swap_document_index", _cancel)

    with pytest.raises(asyncio.CancelledError):
        await index_service.rebuild_document(harness.document)  # type: ignore[arg-type]

    assert _source_is_search_ready(harness.document) is True  # type: ignore[arg-type]
    assert harness.live_file.read_text("utf-8") == _OLD_TEXT


# --------------------------------------------------------------------------------------
# 成功路径：新文本写到独立路径，切换交给单事务完成
# --------------------------------------------------------------------------------------


async def test_successful_index_writes_new_text_to_separate_path(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = _install_harness(monkeypatch, embedding_ok=True)

    chunk_count = await index_service.index_document(harness.document)  # type: ignore[arg-type]

    assert chunk_count == 7
    # 新文本落在内容寻址的新路径上，旧文本在切换前保持不变
    assert harness.new_file.read_text("utf-8") == _NEW_TEXT
    assert harness.live_file.read_text("utf-8") == _OLD_TEXT
    # 新路径与新 hash 交给 _swap_document_index 在单个事务内 flip
    assert len(harness.swap_kwargs) == 1
    assert harness.swap_kwargs[0]["normalized_rel_path"] == _expected_rel_path(1, _NEW_TEXT)
    assert harness.swap_kwargs[0]["normalized_text_hash"] == hashlib.sha256(_NEW_TEXT.encode("utf-8")).hexdigest()


async def test_ready_document_status_not_downgraded_during_rebuild(monkeypatch: pytest.MonkeyPatch) -> None:
    """重建期间不得把 ready 索引改成 indexing/pending，否则搜索端会直接过滤掉。"""
    harness = _install_harness(monkeypatch, embedding_ok=True)
    observed: list[tuple[str, str]] = []

    async def _observing_swap(*_args: object, **kwargs: object) -> int:
        observed.append((harness.document.extract_status, harness.document.sync_status))
        harness.swap_kwargs.append(kwargs)
        return 7

    monkeypatch.setattr(index_service, "_swap_document_index", _observing_swap)

    await index_service.index_document(harness.document)  # type: ignore[arg-type]

    assert observed == [("ready", "ready")]
    assert all("sync_status" not in fields for fields in harness.document.saved_fields)


async def test_post_commit_failure_does_not_roll_back_committed_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """切换提交后收尾步骤失败，不得把元数据回滚到已被删除的旧规范化文本。"""
    harness = _install_harness(monkeypatch, embedding_ok=True)

    async def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("reference sync down")

    monkeypatch.setattr(index_service, "detect_and_sync_document_references", _boom)

    chunk_count = await index_service.rebuild_document(harness.document)  # type: ignore[arg-type]

    document = harness.document
    assert chunk_count == 7
    # 新索引已生效：路径/统计/状态都必须停留在切换后的值
    assert document.normalized_text_path == _expected_rel_path(1, _NEW_TEXT)
    assert document.chunk_count == 7
    assert document.last_indexed_at == "new-timestamp"
    assert _source_is_search_ready(document) is True  # type: ignore[arg-type]


# --------------------------------------------------------------------------------------
# 两阶段切换：Qdrant 写入不受 DB 事务保护，新点必须先不可检索
# --------------------------------------------------------------------------------------


class _FakeQdrant:
    """记录 Qdrant 侧调用，用于断言 staging 点的可见性与清理。"""

    def __init__(self) -> None:
        self.upserted: list[tuple[int, list[float], dict[str, object]]] = []
        self.activated: list[tuple[list[int], dict[str, object]]] = []
        self.deleted: list[list[int]] = []

    async def batch_upsert(self, points: list[tuple[int, list[float], dict[str, object]]]) -> int:
        self.upserted.extend(points)
        return len(points)

    async def set_payload(self, *, chunk_ids: list[int], payload: dict[str, object]) -> None:
        if not chunk_ids:
            return
        self.activated.append((list(chunk_ids), dict(payload)))

    async def delete_chunk_points(self, chunk_ids: list[int]) -> None:
        self.deleted.append(list(chunk_ids))


class _FakeChunk:
    def __init__(self, chunk_id: int, chunk_index: int) -> None:
        self.id = chunk_id
        self.chunk_index = chunk_index
        self.embedding_ref: str | None = None

    def to_qdrant_payload(self, *, document: object, content_preview: str) -> dict[str, object]:
        return {
            "document_id": getattr(document, "id", 0),
            "chunk_index": self.chunk_index,
            "content_preview": content_preview,
            "is_enabled": getattr(document, "is_enabled", True),
        }


class _FakeChunkQuerySet:
    def __init__(self, model: "_FakeChunkModel") -> None:
        self._model = model

    def using_db(self, _conn: object) -> "_FakeChunkQuerySet":
        return self

    def order_by(self, _field: str) -> "_FakeChunkQuerySet":
        return self

    async def all(self) -> list[_FakeChunk]:
        return list(self._model.rows)

    async def delete(self) -> int:
        removed = len(self._model.rows)
        self._model.rows = []
        return removed

    async def values_list(self, _field: str, flat: bool = True) -> list[int]:
        return [row.id for row in self._model.rows]


class _FakeChunkModel:
    """够用的 DBKBChunk 替身：只覆盖 _swap_document_index 用到的接口。"""

    def __init__(self, existing_ids: list[int]) -> None:
        self.rows: list[_FakeChunk] = [_FakeChunk(chunk_id, index) for index, chunk_id in enumerate(existing_ids)]
        self._next_id = 100  # 新建行的 id 与旧行不重叠，模拟自增主键不会复用

    def __call__(self, **kwargs: object) -> _FakeChunk:
        return _FakeChunk(0, int(kwargs.get("chunk_index", 0)))

    def filter(self, **_kwargs: object) -> _FakeChunkQuerySet:
        return _FakeChunkQuerySet(self)

    async def bulk_create(self, objects: list[_FakeChunk], **_kwargs: object) -> None:
        for obj in objects:
            obj.id = self._next_id
            self._next_id += 1
            self.rows.append(obj)

    async def bulk_update(self, _objects: list[_FakeChunk], **_kwargs: object) -> None:
        return None


class _FakeTransaction:
    """带回滚语义的假事务：异常或提交失败都把 chunk 行还原到进入事务前。"""

    def __init__(self, model: _FakeChunkModel, snapshot_rows: list[_FakeChunk], *, fail_commit: bool) -> None:
        self._model = model
        self._snapshot_rows = snapshot_rows
        self._fail_commit = fail_commit

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type: object, *_exc: object) -> bool:
        if exc_type is not None:
            self._model.rows = list(self._snapshot_rows)
            return False
        if self._fail_commit:
            self._model.rows = list(self._snapshot_rows)
            raise RuntimeError("commit failed")
        return False


def _install_swap_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    fail_commit: bool = False,
    fail_activation: bool = False,
) -> tuple[_FakeQdrant, _FakeChunkModel, _FakeDocument]:
    qdrant = _FakeQdrant()
    if fail_activation:

        async def _failing_set_payload(*, chunk_ids: list[int], payload: dict[str, object]) -> None:
            raise RuntimeError("qdrant activation down")

        qdrant.set_payload = _failing_set_payload  # type: ignore[method-assign]

    model = _FakeChunkModel(existing_ids=[11, 12])
    snapshot_rows = list(model.rows)
    document = _FakeDocument()

    monkeypatch.setattr(index_service, "kb_qdrant_manager", qdrant)
    monkeypatch.setattr(index_service, "DBKBChunk", model)
    monkeypatch.setattr(
        index_service,
        "WorkspaceService",
        SimpleNamespace(resolve_kb_normalized_path=lambda _workspace_id, rel_path: Path(tempfile.gettempdir()) / rel_path),
    )
    monkeypatch.setattr(
        index_service,
        "in_transaction",
        lambda: _FakeTransaction(model, snapshot_rows, fail_commit=fail_commit),
    )

    return qdrant, model, document


def _swap_kwargs(document: _FakeDocument) -> dict[str, object]:
    return {
        "snapshot": index_service._snapshot_document_state(document),  # type: ignore[arg-type]
        "normalized_rel_path": _expected_rel_path(document.id, _NEW_TEXT),
        "normalized_text_hash": "new-hash",
    }


async def test_staged_points_are_written_unsearchable_before_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    """upsert 时新点必须 is_enabled=False，提交前才被激活成文档自身的可见性。"""
    qdrant, _model, document = _install_swap_harness(monkeypatch)

    created = await index_service._swap_document_index(
        document,  # type: ignore[arg-type]
        [_draft("a"), _draft("bb")],
        [[1.0], [2.0]],
        **_swap_kwargs(document),  # type: ignore[arg-type]
    )

    assert created == 2
    assert [payload["is_enabled"] for _id, _vec, payload in qdrant.upserted] == [False, False]
    assert qdrant.activated == [([100, 101], {"is_enabled": True})]
    # 旧点只在提交成功之后才清理
    assert qdrant.deleted == [[11, 12]]


async def test_activation_failure_keeps_old_index_intact(monkeypatch: pytest.MonkeyPatch) -> None:
    """set_payload 抛错必须整体回滚：旧 chunk 行与旧向量点都还在，旧索引仍可检索。"""
    qdrant, model, document = _install_swap_harness(monkeypatch, fail_activation=True)

    with pytest.raises(RuntimeError, match="qdrant activation down"):
        await index_service._swap_document_index(
            document,  # type: ignore[arg-type]
            [_draft("a"), _draft("bb")],
            [[1.0], [2.0]],
            **_swap_kwargs(document),  # type: ignore[arg-type]
        )

    # 旧 chunk 行随事务回滚，旧向量点绝不能被删除——两者齐全才谈得上仍可检索
    assert [row.id for row in model.rows] == [11, 12]
    assert [11, 12] not in qdrant.deleted
    # 新点从未变成可检索，并且已被清理
    assert all(payload["is_enabled"] is False for _id, _vec, payload in qdrant.upserted)
    assert qdrant.deleted == [[100, 101]]


async def test_rollback_after_upsert_leaves_no_searchable_orphan_points(monkeypatch: pytest.MonkeyPatch) -> None:
    """Qdrant upsert 成功后 DB commit 失败：新点必须被清理，旧点与旧行保留。"""
    qdrant, model, document = _install_swap_harness(monkeypatch, fail_commit=True)

    with pytest.raises(RuntimeError, match="commit failed"):
        await index_service._swap_document_index(
            document,  # type: ignore[arg-type]
            [_draft("a"), _draft("bb")],
            [[1.0], [2.0]],
            **_swap_kwargs(document),  # type: ignore[arg-type]
        )

    assert [row.id for row in model.rows] == [11, 12]
    assert [11, 12] not in qdrant.deleted
    assert qdrant.deleted == [[100, 101]]
