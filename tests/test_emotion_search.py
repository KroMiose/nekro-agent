"""Unit tests for emotion plugin search / write helpers.

These tests cover the pure-Python helpers introduced by the tag-aware
search optimization. The full ``plugins.builtin.emotion`` module pulls in
heavy dependencies (aiofiles / libmagic / qdrant client stack) that may
not be available in every sandbox / CI runner, so we extract the helpers
via AST instead of importing the module directly. This keeps the tests
fast, deterministic, and aligned with the actual production code: any
change to the helper bodies will fail these tests immediately.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List, Optional

import pytest

EMOTION_PLUGIN_PATH = Path(__file__).resolve().parent.parent / "plugins" / "builtin" / "emotion.py"


# region: AST-based helper extraction


def _extract_function(source: str, func_name: str) -> str:
    """Return the source of the top-level function `func_name` from `source`."""
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return textwrap.dedent(ast.get_source_segment(source, node) or "")
    raise AssertionError(f"function {func_name!r} not found in source")


def _load_helpers() -> dict:
    """Compile the three pure helpers (`_build_emotion_embedding_text`,
    `_normalize_tag`, `_build_tags_filter`) into an isolated namespace.

    We avoid executing the rest of the plugin module — the helpers only
    depend on `qdrant_client.models` for the Filter / FieldCondition /
    MatchValue types, which we substitute with lightweight stand-ins that
    share the same construction interface.
    """
    source = EMOTION_PLUGIN_PATH.read_text(encoding="utf-8")
    func_sources = [
        _extract_function(source, "_build_emotion_embedding_text"),
        _extract_function(source, "_normalize_tag"),
        _extract_function(source, "_build_tags_filter"),
    ]

    class _MatchValue:
        def __init__(self, value: Any) -> None:
            self.value = value

    class _FieldCondition:
        def __init__(self, *, key: str, match: Any) -> None:
            self.key = key
            self.match = match

    class _Filter:
        def __init__(self, must: Optional[List[Any]] = None) -> None:
            self.must = list(must or [])

    stub_models = SimpleNamespace(
        Filter=_Filter,
        FieldCondition=_FieldCondition,
        MatchValue=_MatchValue,
    )

    namespace: dict = {
        "qdrant_models": stub_models,
        "List": List,
        "Optional": Optional,
    }
    exec("\n\n".join(func_sources), namespace)
    return {
        "build_text": namespace["_build_emotion_embedding_text"],
        "normalize": namespace["_normalize_tag"],
        "filter": namespace["_build_tags_filter"],
    }


helpers = pytest.lazy_fixture if False else _load_helpers()
build_text = helpers["build_text"]
normalize_tag = helpers["normalize"]
build_filter = helpers["filter"]


# endregion


# region: _build_emotion_embedding_text


def test_build_emotion_embedding_text_uses_label_marker() -> None:
    text = build_text("一只开心的猫", ["开心", "猫", "动漫"])
    assert text == "一只开心的猫 标签: 开心 猫 动漫"


def test_build_emotion_embedding_text_omits_marker_when_no_tags() -> None:
    assert build_text("描述文本", []) == "描述文本"
    assert build_text("描述文本", None) == "描述文本"


def test_build_emotion_embedding_text_handles_empty_description() -> None:
    assert build_text("", ["a"]) == " 标签: a"
    assert build_text("   ", ["a", "b"]) == " 标签: a b"


def test_build_emotion_embedding_text_strips_whitespace_in_tags() -> None:
    text = build_text("desc", ["  hello ", "", "  ", "world"])
    assert text == "desc 标签: hello world"


# endregion


# region: _normalize_tag / _build_tags_filter


def test_normalize_tag_lowercases_and_strips() -> None:
    assert normalize_tag("  Cat  ") == "cat"
    assert normalize_tag("动漫") == "动漫"


def test_build_tags_filter_returns_none_when_no_tags() -> None:
    assert build_filter(None) is None
    assert build_filter([]) is None


def test_build_tags_filter_returns_none_for_only_empty_tags() -> None:
    assert build_filter(["", "  "]) is None


def test_build_tags_filter_dedupes_case_insensitive() -> None:
    filt = build_filter(["Cat", "cat", "CAT", "Dog"])
    assert filt is not None
    assert len(filt.must) == 2
    values = {cond.match.value for cond in filt.must}
    assert values == {"cat", "dog"}


def test_build_tags_filter_uses_and_semantics_on_tags_field() -> None:
    filt = build_filter(["开心", "动漫"])
    assert filt is not None
    assert len(filt.must) == 2
    for cond in filt.must:
        assert cond.key == "tags"
        assert cond.match.value in {"开心", "动漫"}


def test_build_tags_filter_preserves_input_order_for_distinct_tags() -> None:
    filt = build_filter(["z", "a", "m"])
    assert filt is not None
    values = [cond.match.value for cond in filt.must]
    assert values == ["z", "a", "m"]


# endregion


# region: search_emotion signature compatibility (static check)


def test_search_emotion_signature_accepts_optional_tags() -> None:
    """Static guarantee that `search_emotion` exposes the new tags parameter
    so the optimization is reachable from the LLM tool surface."""
    source = EMOTION_PLUGIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "search_emotion":
            arg_names = {a.arg for a in node.args.args}
            assert "tags" in arg_names, "search_emotion must expose a `tags` parameter"
            # Default must be None so old callers without tags keep working
            for default, arg in zip(
                reversed(node.args.defaults),
                reversed(node.args.args),
            ):
                if arg.arg == "tags":
                    assert isinstance(default, ast.Constant) and default.value is None
                    return
            pytest.fail("search_emotion.tags must default to None")
    pytest.fail("search_emotion not found in plugin source")


def test_init_vector_db_creates_tags_payload_index() -> None:
    """The plugin must register a payload index on `tags` so that
    Qdrant accepts Filter(MatchValue) on array-typed keyword fields."""
    source = EMOTION_PLUGIN_PATH.read_text(encoding="utf-8")
    assert "create_payload_index" in source, "init_vector_db must call create_payload_index"
    assert "PayloadSchemaType.KEYWORD" in source, "tags index must be of KEYWORD type"


def test_write_sites_use_helper_instead_of_inline_concat() -> None:
    """All four write-side embedding-text constructions must go through
    the helper, otherwise new write paths will drift from the search side."""
    source = EMOTION_PLUGIN_PATH.read_text(encoding="utf-8")
    forbidden_patterns = [
        "f\"{description} {' '.join(tags)}\"",
        "f\"{metadata.description} {' '.join(metadata.tags)}\"",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in source, (
            f"inline embedding-text concat found, replace with _build_emotion_embedding_text: {pattern}"
        )


# endregion
