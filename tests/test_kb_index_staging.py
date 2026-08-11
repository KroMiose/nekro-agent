"""知识库索引 staging 语义测试。

核心不变量：全部 chunk 的 embedding 成功之前，绝不触碰既有的 chunk 行 / 向量点 / 规范化文本，
从而保证 embedding 临时失败不会摧毁原本 ready 的可检索索引。
"""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

from nekro_agent.services.kb import index_service, library_index_service
from nekro_agent.services.kb.chunker import ChunkDraft


def _draft(content: str) -> ChunkDraft:
    return ChunkDraft(heading_path="", content=content, char_start=0, char_end=len(content))


@dataclass
class _FakeDocument:
    id: int = 1
    workspace_id: int = 1
    source_path: str = "source.md"
    file_name: str = "source.md"
    title: str = "doc"
    normalized_text_path: str = "1.md"
    normalized_text_hash: str = "old-hash"
    extract_status: str = "ready"
    sync_status: str = "ready"
    last_error: str | None = None
    chunk_count: int = 3
    last_indexed_at: object = None
    saved_fields: list[list[str]] = field(default_factory=list)

    async def save(self, update_fields: list[str] | None = None) -> None:
        self.saved_fields.append(list(update_fields or []))


@dataclass
class _IndexHarness:
    document: _FakeDocument
    normalized_file: Path
    staged_file: Path
    swap_calls: list[tuple[object, ...]]


def _install_index_document_harness(monkeypatch: pytest.MonkeyPatch, *, embedding_ok: bool) -> _IndexHarness:
    """把 index_document 的外部依赖（DB/文件/向量库）替换成可观测的假实现。"""
    temp_dir = Path(tempfile.mkdtemp(prefix="nekro-kb-index-"))
    normalized_file = temp_dir / "1.md"
    normalized_file.write_text("旧的规范化文本", "utf-8")
    document = _FakeDocument()
    swap_calls: list[tuple[object, ...]] = []

    async def _noop_progress(*_args: object, **_kwargs: object) -> None:
        return None

    async def _noop_references(*_args: object, **_kwargs: object) -> None:
        return None

    async def _fake_embed(texts: list[str]) -> list[list[float] | None]:
        return [[1.0] if embedding_ok else None for _ in texts]

    async def _recording_swap(*args: object) -> int:
        swap_calls.append(args)
        return 7

    monkeypatch.setattr(index_service, "_publish_index_progress", _noop_progress)
    monkeypatch.setattr(index_service, "detect_and_sync_document_references", _noop_references)
    monkeypatch.setattr(index_service, "embed_kb_batch", _fake_embed)
    monkeypatch.setattr(index_service, "_swap_document_index", _recording_swap)
    monkeypatch.setattr(index_service, "extract_source_file", lambda *_args: SimpleNamespace(text="新的规范化文本"))
    monkeypatch.setattr(
        index_service,
        "WorkspaceService",
        SimpleNamespace(
            ensure_kb_dirs=lambda _workspace_id: None,
            resolve_kb_source_path=lambda _workspace_id, _path: temp_dir / "source.md",
            resolve_kb_normalized_path=lambda _workspace_id, _path: normalized_file,
        ),
    )

    return _IndexHarness(
        document=document,
        normalized_file=normalized_file,
        staged_file=normalized_file.with_name(f"{normalized_file.name}.staging"),
        swap_calls=swap_calls,
    )


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
    drafts = [_draft("a"), _draft("bb"), _draft("ccc")]

    vectors = await index_service._embed_chunk_drafts(
        SimpleNamespace(id=1, workspace_id=1),  # type: ignore[arg-type]
        drafts,
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


async def test_embedding_failure_never_reaches_index_swap(monkeypatch: pytest.MonkeyPatch) -> None:
    """embedding 失败时，切换阶段完全不被调用，线上规范化文本也保持旧内容。"""
    harness = _install_index_document_harness(monkeypatch, embedding_ok=False)

    with pytest.raises(RuntimeError, match="知识库向量化失败"):
        await index_service.index_document(harness.document)  # type: ignore[arg-type]

    assert harness.swap_calls == []
    assert harness.normalized_file.read_text("utf-8") == "旧的规范化文本"
    assert not harness.staged_file.exists()
    assert harness.document.normalized_text_hash == "old-hash"


async def test_successful_index_commits_staged_normalized_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """索引成功后才把规范化文本切到线上，并落库新的 hash。"""
    harness = _install_index_document_harness(monkeypatch, embedding_ok=True)

    chunk_count = await index_service.index_document(harness.document)  # type: ignore[arg-type]

    assert chunk_count == 7
    assert len(harness.swap_calls) == 1
    assert harness.normalized_file.read_text("utf-8") == "新的规范化文本"
    assert not harness.staged_file.exists()
    assert harness.document.sync_status == "ready"
    assert harness.document.normalized_text_hash != "old-hash"
