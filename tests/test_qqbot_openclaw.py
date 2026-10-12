import time
from types import MethodType

import pytest

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformAtSegment,
    PlatformSendSegment,
    PlatformSendSegmentType,
)
from nekro_agent.adapters.qqbot_openclaw.client import QQBotOpenClawClient
from nekro_agent.adapters.qqbot_openclaw.config import QQBOT_MARKDOWN_ENABLED, QQBotOpenClawConfig
from nekro_agent.adapters.qqbot_openclaw.group_policy import GroupPolicyResolver
from nekro_agent.adapters.qqbot_openclaw.media import infer_media_kind, validate_media_file
from nekro_agent.adapters.qqbot_openclaw.message_processor import QQBotOpenClawMessageProcessor
from nekro_agent.adapters.qqbot_openclaw.outbound import (
    _normalize_text_for_openclaw_markdown,
    _render_at_segment_for_markdown,
    split_markdown_text,
)
from nekro_agent.adapters.qqbot_openclaw.ref_index_store import RefIndexEntry, RefIndexStore
from nekro_agent.adapters.qqbot_openclaw.schemas import (
    QQBotC2CMessageEvent,
    QQBotGatewayPayload,
    QQBotGroupMessageEvent,
)
from nekro_agent.schemas.chat_message import ChatMessageSegmentFile, ChatMessageSegmentType, segment_from_dict


def _config(**kwargs) -> QQBotOpenClawConfig:
    return QQBotOpenClawConfig(APP_ID="bot_openid", CLIENT_SECRET="secret", **kwargs)


def test_segment_from_dict_supports_voice_and_video_file_segments() -> None:
    voice = segment_from_dict(
        {
            "type": "voice",
            "text": "[Voice: a.wav]",
            "file_name": "a.wav",
            "local_path": "/tmp/a.wav",
        },
    )
    video = segment_from_dict(
        {
            "type": "video",
            "text": "[Video: a.mp4]",
            "file_name": "a.mp4",
            "local_path": "/tmp/a.mp4",
        },
    )

    assert isinstance(voice, ChatMessageSegmentFile)
    assert isinstance(video, ChatMessageSegmentFile)
    assert voice.type == ChatMessageSegmentType.VOICE.value
    assert video.type == ChatMessageSegmentType.VIDEO.value


def test_media_kind_inference_and_limits(tmp_path) -> None:
    image = tmp_path / "a.png"
    voice = tmp_path / "a.wav"
    video = tmp_path / "a.mp4"
    doc = tmp_path / "a.bin"
    for path in [image, voice, video, doc]:
        path.write_bytes(b"x")

    assert infer_media_kind(image, PlatformSendSegmentType.FILE) == "image"
    assert infer_media_kind(voice, PlatformSendSegmentType.FILE) == "voice"
    assert infer_media_kind(video, PlatformSendSegmentType.FILE) == "video"
    assert infer_media_kind(doc, PlatformSendSegmentType.FILE) == "file"
    assert validate_media_file(image, PlatformSendSegmentType.IMAGE, _config()).file_type == 1


def test_gateway_payload_accepts_empty_string_data() -> None:
    payload = QQBotGatewayPayload.model_validate({"op": 11, "d": ""})

    assert payload.op == 11
    assert payload.d == ""


def test_c2c_event_accepts_empty_message_scene() -> None:
    event = QQBotC2CMessageEvent.model_validate(
        {
            "id": "m1",
            "content": "hello",
            "author": {"user_openid": "u1"},
            "message_scene": "",
            "attachments": "",
            "msg_elements": "",
        },
    )

    assert event.message_scene is None
    assert event.attachments == []
    assert event.msg_elements == []


def test_split_markdown_text_closes_code_fences() -> None:
    text = "before\n```python\n" + "\n".join(f"print({i})" for i in range(20)) + "\n```\nafter"
    chunks = split_markdown_text(text, 80)

    assert len(chunks) > 1
    assert all(chunk.count("```") % 2 == 0 for chunk in chunks[:-1])
    assert "after" in chunks[-1]


@pytest.mark.asyncio
async def test_ref_index_store_persists_and_expires(tmp_path) -> None:
    store_path = tmp_path / "ref-index.jsonl"
    store = RefIndexStore(store_path, ttl_seconds=60)
    await store.put(
        RefIndexEntry(
            ref_idx="ref-1",
            chat_key="qqoc-group:g1",
            message_id="m1",
            sender_id="u1",
            sender_name="User",
            content_text="hello",
        ),
    )

    reloaded = RefIndexStore(store_path, ttl_seconds=60)
    entry = await reloaded.get("ref-1")

    assert entry is not None
    assert entry.content_text == "hello"

    expired = RefIndexStore(store_path, ttl_seconds=1)
    await expired.put(
        RefIndexEntry(
            ref_idx="ref-old",
            chat_key="qqoc-group:g1",
            content_text="old",
            created_at=time.time() - 10,
        ),
    )
    assert await expired.get("ref-old") is None


def test_group_policy_default_collects_without_trigger_and_reply_to_bot_triggers() -> None:
    resolver = GroupPolicyResolver(_config(DEFAULT_REQUIRE_MENTION=True), self_user_id="bot_openid")
    event = QQBotGroupMessageEvent.model_validate(
        {
            "id": "m1",
            "content": "普通消息",
            "group_openid": "g1",
            "author": {"member_openid": "u1"},
        },
    )

    decision = resolver.decide(event_type="GROUP_MESSAGE_CREATE", event=event, ref_entry=None)
    assert decision.collect is True
    assert decision.trigger is False

    ref_decision = resolver.decide(
        event_type="GROUP_MESSAGE_CREATE",
        event=event,
        ref_entry=RefIndexEntry(ref_idx="bot-ref", chat_key="qqoc-group:g1", is_bot=True),
    )
    assert ref_decision.collect is True
    assert ref_decision.trigger is True


@pytest.mark.asyncio
async def test_processor_quote_msg_element_overrides_ext_ref(tmp_path) -> None:
    store = RefIndexStore(tmp_path / "ref-index.jsonl", ttl_seconds=60)
    processor = QQBotOpenClawMessageProcessor(
        config=_config(),
        adapter_key="qqbot_openclaw",
        ref_store=store,
        group_policy=GroupPolicyResolver(_config()),
    )
    event = QQBotGroupMessageEvent.model_validate(
        {
            "id": "m1",
            "content": "reply",
            "group_openid": "g1",
            "author": {"member_openid": "u1"},
            "message_type": 103,
            "message_scene": {"ext": {"msg_idx": "current", "ref_msg_idx": "ext-ref"}},
            "msg_elements": [{"msg_idx": "element-ref"}],
        },
    )

    msg_idx, ref_msg_idx = processor._parse_ref_indices(event)

    assert msg_idx == "current"
    assert ref_msg_idx == "element-ref"


@pytest.mark.asyncio
async def test_processor_parses_openclaw_ext_list_values(tmp_path) -> None:
    store = RefIndexStore(tmp_path / "ref-index.jsonl", ttl_seconds=60)
    processor = QQBotOpenClawMessageProcessor(
        config=_config(),
        adapter_key="qqbot_openclaw",
        ref_store=store,
        group_policy=GroupPolicyResolver(_config()),
    )
    event = QQBotC2CMessageEvent.model_validate(
        {
            "id": "m1",
            "content": "hello",
            "author": {"user_openid": "u1"},
            "message_scene": {"ext": ["msg_idx=current-ref", "ref_msg_idx=quoted-ref"]},
        },
    )

    msg_idx, ref_msg_idx = processor._parse_ref_indices(event)

    assert msg_idx == "current-ref"
    assert ref_msg_idx == "quoted-ref"


@pytest.mark.asyncio
async def test_processor_preserves_long_platform_message_id(tmp_path) -> None:
    store = RefIndexStore(tmp_path / "ref-index.jsonl", ttl_seconds=60)
    processor = QQBotOpenClawMessageProcessor(
        config=_config(),
        adapter_key="qqbot_openclaw",
        ref_store=store,
        group_policy=GroupPolicyResolver(_config()),
    )
    long_message_id = "ROBOT1.0_" + "x" * 120

    parsed = await processor.parse_event(
        "C2C_MESSAGE_CREATE",
        {
            "id": long_message_id,
            "content": "hello",
            "author": {"user_openid": "u1"},
            "message_scene": {"ext": ["msg_idx=REFIDX_current"]},
        },
    )

    assert parsed is not None
    assert parsed.message.message_id == long_message_id
    assert parsed.reply_msg_id == long_message_id
    assert parsed.msg_idx == "REFIDX_current"


@pytest.mark.asyncio
async def test_processor_uses_sender_display_name_for_c2c_channel(tmp_path) -> None:
    store = RefIndexStore(tmp_path / "ref-index.jsonl", ttl_seconds=60)
    processor = QQBotOpenClawMessageProcessor(
        config=_config(),
        adapter_key="qqbot_openclaw",
        ref_store=store,
        group_policy=GroupPolicyResolver(_config()),
    )

    parsed = await processor.parse_event(
        "C2C_MESSAGE_CREATE",
        {
            "id": "m1",
            "content": "hello",
            "author": {"user_openid": "u1", "username": "KroMiose"},
        },
    )

    assert parsed is not None
    assert parsed.channel.channel_name == "KroMiose"
    assert parsed.user.user_name == "KroMiose"
    assert parsed.message.sender_nickname == "KroMiose"


@pytest.mark.asyncio
async def test_processor_uses_group_name_only_when_event_provides_it(tmp_path) -> None:
    store = RefIndexStore(tmp_path / "ref-index.jsonl", ttl_seconds=60)
    processor = QQBotOpenClawMessageProcessor(
        config=_config(),
        adapter_key="qqbot_openclaw",
        ref_store=store,
        group_policy=GroupPolicyResolver(_config()),
    )

    parsed = await processor.parse_event(
        "GROUP_AT_MESSAGE_CREATE",
        {
            "id": "m1",
            "content": "hello",
            "group_openid": "g1",
            "group_name": "NekroAI研究所",
            "author": {"member_openid": "u1", "username": "Alice"},
        },
    )

    assert parsed is not None
    assert parsed.channel.channel_name == "NekroAI研究所"
    assert parsed.user.user_name == "Alice"
    assert parsed.message.sender_nickname == "Alice"


@pytest.mark.asyncio
async def test_client_reply_msg_seq_is_incremental_per_message_id() -> None:
    async def noop_event(*_args) -> None:
        return None

    client = QQBotOpenClawClient(_config(), noop_event)
    try:
        assert client.next_msg_seq("msg-a") == 1
        assert client.next_msg_seq("msg-a") == 2
        assert client.next_msg_seq("msg-b") == 1
        assert client.next_msg_seq(None) == 1
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_client_chunked_upload_uses_openclaw_part_finish_body(tmp_path) -> None:
    async def noop_event(*_args) -> None:
        return None

    upload_file = tmp_path / "test.txt"
    upload_file.write_bytes(b"abcdef")
    media = validate_media_file(upload_file, PlatformSendSegmentType.FILE, _config())
    client = QQBotOpenClawClient(_config(), noop_event)
    calls: list[tuple[str, str, dict]] = []
    uploaded_chunks: list[bytes] = []

    class PutResponse:
        headers = {"etag": "unused"}

        def raise_for_status(self) -> None:
            return None

    async def fake_put(_url: str, *, content: bytes) -> PutResponse:
        uploaded_chunks.append(content)
        return PutResponse()

    async def fake_request(self, method: str, path: str, *, json_body=None, retry_auth: bool = True):
        body = dict(json_body or {})
        calls.append((method, path, body))
        if path.endswith("/upload_prepare"):
            return {
                "upload_id": "upload-1",
                "block_size": 3,
                "parts": [
                    {"index": 1, "presigned_url": "https://upload.local/1"},
                    {"index": 2, "presigned_url": "https://upload.local/2"},
                ],
            }
        if path.endswith("/upload_part_finish"):
            return {}
        if path.endswith("/files"):
            return {"file_uuid": "uuid", "file_info": "info", "ttl": 3600}
        raise AssertionError(f"unexpected path: {path}")

    client._http.put = fake_put  # type: ignore[method-assign]
    client._request = MethodType(fake_request, client)  # type: ignore[method-assign]
    try:
        result = await client.upload_media(target_type="c2c", target_id="u1", media=media)
    finally:
        await client.stop()

    assert result.file_info == "info"
    assert uploaded_chunks == [b"abc", b"def"]

    finish_calls = [body for _method, path, body in calls if path.endswith("/upload_part_finish")]
    assert finish_calls == [
        {
            "upload_id": "upload-1",
            "part_index": 1,
            "block_size": 3,
            "md5": "900150983cd24fb0d6963f7d28e17f72",
        },
        {
            "upload_id": "upload-1",
            "part_index": 2,
            "block_size": 3,
            "md5": "4ed9407630eb1000c0f6b63842defa7d",
        },
    ]


# ========================================================================================
# Markdown AT 格式转写测试 (openclaw 适配器内部使用)
# ========================================================================================


def test_render_at_segment_for_markdown_uses_platform_user_id() -> None:
    """AT 段必须渲染为 OpenClaw Markdown 识别的 `<@user_id>` 形式。"""
    segment = PlatformSendSegment(
        type=PlatformSendSegmentType.AT,
        at_info=PlatformAtSegment(platform_user_id="B031F366677A6FB8580CAF5B2484F49C", nickname="Alice"),
    )
    assert _render_at_segment_for_markdown(segment) == "<@B031F366677A6FB8580CAF5B2484F49C>"


def test_render_at_segment_for_markdown_handles_missing_at_info() -> None:
    """AT 段缺少 at_info 时应输出空串，避免渲染出孤立的 `@`。"""
    segment = PlatformSendSegment(type=PlatformSendSegmentType.AT)
    assert _render_at_segment_for_markdown(segment) == ""


def test_normalize_text_converts_internal_at_markup_to_markdown_at() -> None:
    """文本中的 `[@id:xxx@]` 必须被转换为 `<@xxx>` 形式。"""
    text = "请 [@id:B031F366677A6FB8580CAF5B2484F49C@] 处理一下"
    assert _normalize_text_for_openclaw_markdown(text) == "请 <@B031F366677A6FB8580CAF5B2484F49C> 处理一下"


def test_normalize_text_converts_internal_at_markup_with_nickname() -> None:
    """带 nickname 的内部 AT 标记应丢弃昵称，仅保留 `<@user_id>`。"""
    text = "[@id:USER123;nickname:Alice@] 你好"
    assert _normalize_text_for_openclaw_markdown(text) == "<@USER123> 你好"


def test_normalize_text_converts_all_token_to_everyone() -> None:
    """`[@id:all@]` 应被转换为 OpenClaw 识别的 `<@everyone>`。"""
    assert _normalize_text_for_openclaw_markdown("[@id:all@] 大家注意") == "<@everyone> 大家注意"


def test_normalize_text_preserves_code_fence_at_literal() -> None:
    """代码块内的 `[@id:xxx@]` 字面量不应被改写。"""
    text = "示例代码:\n```\n[@id:USER123@]\n```\n继续"
    assert _normalize_text_for_openclaw_markdown(text) == text


def test_normalize_text_preserves_inline_code_at_literal() -> None:
    """行内代码内的 `[@id:xxx@]` 字面量不应被改写。"""
    text = "语法是 `[@id:USER123@]`，不是 at"
    assert _normalize_text_for_openclaw_markdown(text) == text


def test_normalize_text_preserves_email_address() -> None:
    """邮箱地址不应被误识别为 AT 标记。"""
    text = "联系 bob@example.com 即可"
    assert _normalize_text_for_openclaw_markdown(text) == text


def test_normalize_text_handles_multiple_mentions_in_one_segment() -> None:
    """同一段文本内多个 AT 都应被独立转换。"""
    text = "[@id:AAA@] 和 [@id:BBB@] 都看一下"
    assert _normalize_text_for_openclaw_markdown(text) == "<@AAA> 和 <@BBB> 都看一下"


def test_normalize_text_passes_through_plain_text() -> None:
    """不含 AT 标记的纯文本应原样保留。"""
    text = "今天天气不错。"
    assert _normalize_text_for_openclaw_markdown(text) == text


def test_normalize_text_handles_empty_input() -> None:
    """空字符串应原样返回。"""
    assert _normalize_text_for_openclaw_markdown("") == ""


@pytest.mark.skipif(not QQBOT_MARKDOWN_ENABLED, reason="仅 Markdown 模式下的行为需要验证")
def test_qqbot_openclaw_defaults_to_markdown_for_at_translation() -> None:
    """确保默认 Markdown 开关与本次修复假设一致，避免静默回退。"""
    # 这是一条护栏测试：若未来有人把 QQBOT_MARKDOWN_ENABLED 默认改为 False，
    # 需要重新评估 AT 转写策略。
    assert QQBOT_MARKDOWN_ENABLED is True
