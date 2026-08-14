import pytest

from nekro_agent.adapters.wechat_openilink.config import WeChatOpenILinkConfig
from nekro_agent.adapters.wechat_openilink.message_processor import OpenILinkMessageProcessor
from nekro_agent.schemas.chat_message import (
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
)


def _processor() -> OpenILinkMessageProcessor:
    return OpenILinkMessageProcessor(
        config=WeChatOpenILinkConfig(),
        adapter_key="wechat_openilink",
        build_chat_key=lambda channel_id: f"wechat_openilink-{channel_id}",
    )


@pytest.mark.asyncio
async def test_parse_media_only_image_message(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str, str]] = []

    async def fake_create_from_url(
        cls,
        url: str,
        from_chat_key: str,
        file_name: str = "",
        use_suffix: str = "",
    ) -> ChatMessageSegmentImage:
        calls.append((url, from_chat_key, file_name, use_suffix))
        return cls(
            type=ChatMessageSegmentType.IMAGE,
            text=f"[Image: {file_name}]",
            file_name=file_name,
            local_path=f"/tmp/{file_name}",
            remote_url=url,
        )

    monkeypatch.setattr(ChatMessageSegmentImage, "create_from_url", classmethod(fake_create_from_url))

    parsed = await _processor().parse(
        {
            "user_id": "wxid_user",
            "message_id": "msg-image",
            "type": "image",
            "image_url": "https://example.test/image.jpg",
        },
    )

    assert parsed is not None
    assert parsed.message.content_text == "[Image: image.jpg]"
    assert parsed.message.content_data[0].type == ChatMessageSegmentType.IMAGE.value
    assert parsed.message.content_data[0].local_path == "/tmp/image.jpg"
    assert calls == [("https://example.test/image.jpg", "wechat_openilink-private_wxid__user", "image.jpg", ".jpg")]


@pytest.mark.asyncio
async def test_parse_media_only_file_message(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str, str]] = []

    async def fake_create_from_url(
        cls,
        url: str,
        from_chat_key: str,
        file_name: str = "",
        use_suffix: str = "",
    ) -> ChatMessageSegmentFile:
        calls.append((url, from_chat_key, file_name, use_suffix))
        return cls(
            type=ChatMessageSegmentType.FILE,
            text=f"[File: {file_name}]",
            file_name=file_name,
            local_path=f"/tmp/{file_name}",
            remote_url=url,
        )

    monkeypatch.setattr(ChatMessageSegmentFile, "create_from_url", classmethod(fake_create_from_url))

    parsed = await _processor().parse(
        {
            "user_id": "wxid_user",
            "message_id": "msg-file",
            "type": "file",
            "file_url": "https://example.test/report.pdf",
            "file_name": "report.pdf",
        },
    )

    assert parsed is not None
    assert parsed.message.content_text == "[File: report.pdf]"
    assert parsed.message.content_data[0].type == ChatMessageSegmentType.FILE.value
    assert parsed.message.content_data[0].local_path == "/tmp/report.pdf"
    assert calls == [("https://example.test/report.pdf", "wechat_openilink-private_wxid__user", "report.pdf", "")]
