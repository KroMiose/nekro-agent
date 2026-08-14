from pathlib import Path
from typing import Any

import pytest

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformSendRequest,
    PlatformSendSegment,
    PlatformSendSegmentType,
)
from nekro_agent.adapters.web.adapter import WebAdapter
from nekro_agent.schemas.agent_message import AgentMessageSegmentType


class _FakeMessageService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def push_bot_message(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append({"args": args, "kwargs": kwargs})


@pytest.mark.asyncio
async def test_web_adapter_forward_message_records_text_and_media(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from nekro_agent.services import message_service as message_service_mod

    image_path = tmp_path / "help.png"
    image_path.write_bytes(b"fake-png")
    recorder = _FakeMessageService()
    monkeypatch.setattr(message_service_mod, "message_service", recorder)

    adapter = WebAdapter()
    response = await adapter.forward_message(
        PlatformSendRequest(
            chat_key="web-session_test",
            segments=[
                PlatformSendSegment(type=PlatformSendSegmentType.TEXT, content="帮助结果"),
                PlatformSendSegment(type=PlatformSendSegmentType.IMAGE, file_path=str(image_path)),
            ],
            ref_msg_id="ref_1",
        ),
    )

    assert response.success is True
    assert response.recorded is True
    assert response.message_id and response.message_id.startswith("webout_")
    assert len(recorder.calls) == 1

    call = recorder.calls[0]
    assert call["args"][0] == "web-session_test"
    assert call["args"][2] is response
    assert call["kwargs"] == {"ref_msg_id": "ref_1", "normalize_at_markup": False}

    messages = call["args"][1]
    assert [message.type for message in messages] == [AgentMessageSegmentType.TEXT, AgentMessageSegmentType.IMAGE]
    assert messages[0].content == "帮助结果"
    assert messages[1].content == str(image_path)


@pytest.mark.asyncio
async def test_web_adapter_forward_message_downloads_remote_media(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from nekro_agent.adapters.web import adapter as adapter_mod
    from nekro_agent.services import message_service as message_service_mod

    downloaded_path = tmp_path / "remote.png"
    downloaded_path.write_bytes(b"remote-png")
    recorder = _FakeMessageService()
    monkeypatch.setattr(message_service_mod, "message_service", recorder)

    async def fake_download_file(url: str, *, from_chat_key: str, **kwargs: Any) -> tuple[str, str]:
        assert url == "https://example.com/remote.png"
        assert from_chat_key == "web-session_test"
        return str(downloaded_path), downloaded_path.name

    monkeypatch.setattr(adapter_mod, "download_file", fake_download_file)

    response = await WebAdapter().forward_message(
        PlatformSendRequest(
            chat_key="web-session_test",
            segments=[
                PlatformSendSegment(
                    type=PlatformSendSegmentType.IMAGE,
                    file_path="https://example.com/remote.png",
                ),
            ],
        ),
    )

    assert response.success is True
    assert response.recorded is True
    messages = recorder.calls[0]["args"][1]
    assert [message.type for message in messages] == [AgentMessageSegmentType.IMAGE]
    assert messages[0].content == str(downloaded_path)


@pytest.mark.asyncio
async def test_universal_chat_service_skips_duplicate_record_when_adapter_recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nekro_agent.adapters.interface.schemas.platform import PlatformSendResponse
    from nekro_agent.services import message_service as message_service_mod
    from nekro_agent.services.chat.universal_chat_service import universal_chat_service

    class Adapter:
        async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
            return PlatformSendResponse(success=True, message_id="webout_test", recorded=True)

    recorder = _FakeMessageService()
    monkeypatch.setattr(message_service_mod, "message_service", recorder)

    await universal_chat_service.send_agent_message(
        chat_key="web-session_test",
        messages="hello",
        adapter=Adapter(),
        record=True,
    )

    assert recorder.calls == []
