from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from starlette.datastructures import Headers, UploadFile

from nekro_agent.schemas.chat_message import ChatMessageSegmentImage, ChatMessageSegmentType


class _FakeConfig:
    MESSAGE_MAX_LENGTH = 8000
    FILE_UPLOAD_MAX_SIZE_MB = 10


class _FakeAdapter:
    config = _FakeConfig()


class _FakeChannel:
    chat_key = "web-session_test"


class _FakeUser:
    id = 1
    username = "admin"
    perm_level = 3


@pytest.mark.asyncio
async def test_web_upload_message_records_saved_local_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from nekro_agent.adapters.web import routers

    captured: dict[str, Any] = {}

    async def fake_get_web_channel(chat_key: str) -> _FakeChannel:
        assert chat_key == _FakeChannel.chat_key
        return _FakeChannel()

    async def fake_collect_web_message(
        adapter: _FakeAdapter,
        channel: _FakeChannel,
        current_user: _FakeUser,
        content: str,
        content_data: list[Any],
    ) -> routers.WebMessageCreateResponse:
        captured["content"] = content
        captured["content_data"] = content_data
        return routers.WebMessageCreateResponse(ok=True, chat_key=channel.chat_key, message_id="webmsg_test")

    async def fake_save_upload_file(chat_key: str, file: Any, max_size_mb: int) -> tuple[str, str]:
        assert chat_key == _FakeChannel.chat_key
        assert file.filename == "cat.png"
        assert max_size_mb == _FakeConfig.FILE_UPLOAD_MAX_SIZE_MB
        saved_path = tmp_path / "uploads" / chat_key / "cat.png"
        saved_path.parent.mkdir(parents=True)
        saved_path.write_bytes(b"fake-png")
        return str(saved_path), "cat.png"

    monkeypatch.setattr(routers, "_save_upload_file", fake_save_upload_file)
    monkeypatch.setattr(routers, "_get_adapter", lambda: _FakeAdapter())
    monkeypatch.setattr(routers, "_get_web_channel", fake_get_web_channel)
    monkeypatch.setattr(routers, "_collect_web_message", fake_collect_web_message)

    upload = UploadFile(
        file=io.BytesIO(b"fake-png"),
        filename="cat.png",
        headers=Headers({"content-type": "image/png"}),
    )

    response = await routers.create_web_upload_message(
        _FakeChannel.chat_key,
        content="看看这张图",
        file=upload,
        _current_user=_FakeUser(),
    )

    assert response.ok is True
    image_segment = captured["content_data"][1]
    assert isinstance(image_segment, ChatMessageSegmentImage)
    assert image_segment.type == ChatMessageSegmentType.IMAGE.value
    assert image_segment.file_name.endswith("cat.png")
    assert image_segment.local_path
    assert Path(image_segment.local_path).is_file()
    assert Path(image_segment.local_path).parent == tmp_path / "uploads" / _FakeChannel.chat_key


@pytest.mark.asyncio
async def test_web_chat_mcp_send_file_records_saved_local_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from nekro_agent.adapters.web import routers
    from nekro_agent.services.mcp.web_chat_mcp import service as service_mod

    source = tmp_path / "source.png"
    source.write_bytes(b"fake-png")
    captured: dict[str, Any] = {}

    async def fake_get_web_channel(chat_key: str) -> _FakeChannel:
        assert chat_key == _FakeChannel.chat_key
        return _FakeChannel()

    async def fake_collect_message(
        adapter: _FakeAdapter,
        channel: _FakeChannel,
        content: str,
        content_data: list[Any],
    ) -> dict[str, Any]:
        captured["content"] = content
        captured["content_data"] = content_data
        return {"ok": True, "chat_key": channel.chat_key, "message_id": "webmsg_test"}

    async def fake_save_upload_file(chat_key: str, upload: Any, max_size_mb: int) -> tuple[str, str]:
        assert chat_key == _FakeChannel.chat_key
        assert upload.filename == source.name
        assert max_size_mb == _FakeConfig.FILE_UPLOAD_MAX_SIZE_MB
        saved_path = tmp_path / "uploads" / chat_key / source.name
        saved_path.parent.mkdir(parents=True)
        saved_path.write_bytes(source.read_bytes())
        return str(saved_path), source.name

    monkeypatch.setattr(routers, "_save_upload_file", fake_save_upload_file)
    monkeypatch.setattr(service_mod, "_get_web_adapter", lambda: _FakeAdapter())
    monkeypatch.setattr(service_mod, "_get_web_channel", fake_get_web_channel)
    monkeypatch.setattr(service_mod, "_collect_message", fake_collect_message)

    service = service_mod.WebChatMcpService(
        settings=service_mod.WebChatMcpSettings(file_allowlist=[tmp_path.resolve()]),
    )
    result = await service.send_file(_FakeChannel.chat_key, file_path=str(source), content="看看")

    assert result["ok"] is True
    image_segment = captured["content_data"][1]
    assert isinstance(image_segment, ChatMessageSegmentImage)
    assert image_segment.local_path
    assert Path(image_segment.local_path).is_file()


def test_history_image_access_path_falls_back_to_file_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from nekro_agent.services.agent.templates import history

    image_path = tmp_path / "uploads" / _FakeChannel.chat_key / "old.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake-png")

    monkeypatch.setattr(
        history,
        "convert_filename_to_access_path",
        lambda file_name, chat_key: tmp_path / "uploads" / chat_key / Path(file_name).name,
    )

    segment = ChatMessageSegmentImage(
        type=ChatMessageSegmentType.IMAGE,
        text="[Image: old.png]",
        file_name="old.png",
    )

    assert history._resolve_image_access_path(segment, _FakeChannel.chat_key) == image_path
