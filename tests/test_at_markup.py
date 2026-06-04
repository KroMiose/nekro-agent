import random
from collections.abc import Iterator

import pytest

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformSendRequest,
    PlatformSendSegment,
    PlatformSendSegmentType,
)
from nekro_agent.services.agent.resolver import fix_raw_response
from nekro_agent.tools.at_markup import AT_MARKUP_PATTERN, neutralize_at_all_markup, normalize_malformed_at_markup
from nekro_agent.tools.message_id import normalize_ref_msg_id


def _random_id_generator() -> Iterator[str]:
    rng = random.Random(20260604)
    used_ids: set[str] = set()

    while True:
        uid = str(rng.randrange(100_000_000, 999_999_999))
        if uid in used_ids:
            continue
        used_ids.add(uid)
        yield uid


_ID_GENERATOR = _random_id_generator()


def _next_user_id() -> str:
    return next(_ID_GENERATOR)


def _next_short_id(length: int) -> str:
    return _next_user_id()[:length]


def _next_named_user_id() -> str:
    return f"user_{_next_short_id(6)}-test"


def _next_hash_user_id() -> str:
    return f"alpha#{_next_short_id(4)}"


def _at_case(raw_template: str, expected_template: str, uid: str | None = None) -> tuple[str, str]:
    uid = uid or _next_user_id()
    return raw_template.format(uid=uid), expected_template.format(uid=uid)


def _at_cases() -> list[tuple[str, str]]:
    return [
        _at_case("[@id:{uid}@]", "[@id:{uid}@]"),
        _at_case("@id:{uid}@]", "[@id:{uid}@]"),
        _at_case("@id:{uid}@", "[@id:{uid}@]"),
        _at_case("@id:{uid}", "[@id:{uid}@]"),
        _at_case("[id:{uid}]", "[@id:{uid}@]"),
        _at_case("[id:{uid}@]", "[@id:{uid}@]"),
        _at_case("[@id:{uid}]", "[@id:{uid}@]"),
        _at_case("@[id:{uid}]", "[@id:{uid}@]"),
        _at_case("@[@id:{uid}@]", "[@id:{uid}@]"),
        _at_case("(@id:{uid};)", "[@id:{uid}@]"),
        _at_case("(@id:{uid})", "[@id:{uid}@]"),
        _at_case("（@id：{uid}）", "[@id:{uid}@]"),
        _at_case("(@{uid})", "[@id:{uid}@]"),
        _at_case("[@{uid}]", "[@id:{uid}@]"),
        _at_case("@{uid}@)", "[@id:{uid}@]"),
        _at_case("@{uid}", "[@id:{uid}@]"),
        _at_case("<@{uid}>", "[@id:{uid}@]"),
        _at_case("<@!{uid}>", "[@id:{uid}@]"),
        _at_case("<At:[@id:{uid}@]>", "[@id:{uid}@]"),
        _at_case("<At:[@id:{uid}]>", "[@id:{uid}@]"),
        _at_case("<7e56b348 | At:[@id:{uid}@]>", "[@id:{uid}@]"),
        _at_case("【 @ id ： {uid} @ 】", "[@id:{uid}@]", _next_named_user_id()),
        _at_case("[@id:{uid}@]", "[@id:{uid}@]", _next_hash_user_id()),
        _at_case("@id:{uid}@]", "[@id:{uid}@]", _next_hash_user_id()),
        _at_case("[@id:{uid};nickname=测试用户]", "[@id:{uid};nickname:测试用户@]"),
        _at_case("@id:{uid};nickname=测试用户@]", "[@id:{uid};nickname:测试用户@]"),
        _at_case("（@id：{uid}；nickname：测试用户）", "[@id:{uid};nickname:测试用户@]"),
        _at_case("[CQ:at,qq={uid}]", "[@id:{uid}@]"),
        _at_case("[CQ:at,qq={uid},name=测试用户]", "[@id:{uid};nickname:测试用户@]"),
        _at_case("[CQ:at,qq={uid},card=测试用户]", "[@id:{uid};nickname:测试用户@]"),
        ("[CQ:at,qq=all]", "[@id:all@]"),
        _at_case("CQ:at,qq={uid}", "[@id:{uid}@]"),
        _at_case("[CQ:at,qq={uid},foo=bar]", "[@id:{uid}@]"),
        _at_case("[cq:AT,qq={uid}]", "[@id:{uid}@]"),
        _at_case("[CQ:at, qq = {uid} , name = 测试用户 ]", "[@id:{uid};nickname:测试用户@]"),
        _at_case("@ ID = {uid}", "[@id:{uid}@]"),
        _at_case("@ id ： {uid}", "[@id:{uid}@]", _next_named_user_id()),
        _at_case("[@id:{uid};nickname:测试用户；]", "[@id:{uid};nickname:测试用户@]"),
        _at_case(" [CQ:at,qq={uid}] ", " [@id:{uid}@] "),
        _at_case("[CQ:at,qq={uid},nickname=测试用户,foo=bar]", "[@id:{uid};nickname:测试用户@]"),
        _at_case("<At:（@id:{uid}）>", "[@id:{uid}@]"),
        _at_case("（@[@id:{uid}@]）", "[@id:{uid}@]"),
    ]


@pytest.mark.parametrize(("raw_text", "expected"), _at_cases())
def test_normalize_malformed_at_markup(raw_text: str, expected: str) -> None:
    assert normalize_malformed_at_markup(raw_text) == expected


def test_normalize_malformed_at_markup_inside_sentence() -> None:
    uid = _next_user_id()
    assert normalize_malformed_at_markup(f"你好 @id:{uid}@] 请看这里") == f"你好 [@id:{uid}@] 请看这里"

    uid = _next_user_id()
    assert normalize_malformed_at_markup(f"你好 [CQ:at,qq={uid}]，请看这里") == f"你好 [@id:{uid}@]，请看这里"

    uid = _next_user_id()
    assert normalize_malformed_at_markup(f"你好，<@{uid}> 请看这里") == f"你好，[@id:{uid}@] 请看这里"


def test_normalize_malformed_at_markup_handles_multiple_mentions() -> None:
    uid_a = _next_user_id()
    uid_b = _next_user_id()
    uid_c = _next_user_id()
    assert (
        normalize_malformed_at_markup(f"你好 @id:{uid_a}@] 和 [CQ:at,qq={uid_b},name=测试用户]，请看 <@{uid_c}>")
        == f"你好 [@id:{uid_a}@] 和 [@id:{uid_b};nickname:测试用户@]，请看 [@id:{uid_c}@]"
    )

    uid_a = _next_user_id()
    uid_b = _next_hash_user_id()
    uid_c = _next_named_user_id()
    assert (
        normalize_malformed_at_markup(f"混合：(@{uid_a})、@id:{uid_b}@]、【 @ id ： {uid_c} @ 】")
        == f"混合：[@id:{uid_a}@]、[@id:{uid_b}@]、[@id:{uid_c}@]"
    )

    uid_a = _next_user_id()
    uid_b = _next_user_id()
    uid_c = _next_user_id()
    assert (
        normalize_malformed_at_markup(f"[CQ:at,qq={uid_a}][CQ:at,qq={uid_b}]<@{uid_c}>")
        == f"[@id:{uid_a}@][@id:{uid_b}@][@id:{uid_c}@]"
    )

    uid_a = _next_user_id()
    uid_b = _next_user_id()
    uid_c = _next_user_id()
    assert (
        normalize_malformed_at_markup(f"第一行 @id:{uid_a}@]\n第二行 <@{uid_b}>\n第三行 [CQ:at,qq={uid_c}]")
        == f"第一行 [@id:{uid_a}@]\n第二行 [@id:{uid_b}@]\n第三行 [@id:{uid_c}@]"
    )


def test_normalize_malformed_at_markup_is_idempotent() -> None:
    uid_a = _next_user_id()
    uid_b = _next_user_id()
    uid_c = _next_user_id()
    text = f"你好 @id:{uid_a}@] 和 [CQ:at,qq={uid_b},name=测试用户]，请看 <@{uid_c}>"
    normalized = normalize_malformed_at_markup(text)

    assert normalize_malformed_at_markup(normalized) == normalized


def test_normalize_malformed_at_markup_preserves_canonical() -> None:
    uid = _next_user_id()
    text = f"你好 [@id:{uid};nickname:测试用户@]"

    assert normalize_malformed_at_markup(text) == text


def test_normalize_malformed_at_markup_preserves_non_mentions() -> None:
    uid = _next_user_id()
    assert normalize_malformed_at_markup(f"邮箱 test@{uid}.com 不应被改写") == f"邮箱 test@{uid}.com 不应被改写"

    short_id = _next_short_id(4)
    assert normalize_malformed_at_markup(f"版本号 @{short_id}abc 不应被改写") == f"版本号 @{short_id}abc 不应被改写"

    short_id = _next_short_id(4)
    assert normalize_malformed_at_markup(f"短号 @{short_id} 不应被改写") == f"短号 @{short_id} 不应被改写"

    short_id = _next_short_id(3)
    assert normalize_malformed_at_markup(f"数组 [@{short_id}] 不是平台用户标记") == f"数组 [@{short_id}] 不是平台用户标记"

    assert normalize_malformed_at_markup("文本 [CQ:at,name=测试用户] 缺少 qq 不应改写") == "文本 [CQ:at,name=测试用户] 缺少 qq 不应改写"

    uid = _next_user_id()
    assert normalize_malformed_at_markup(f"链接 https://example.com/@{uid}") == f"链接 https://example.com/@{uid}"

    uid = _next_user_id()
    assert normalize_malformed_at_markup(f"路径 /users/@{uid}/profile") == f"路径 /users/@{uid}/profile"

    uid = _next_user_id()
    assert normalize_malformed_at_markup(f"变量 user_@{uid} 不应改写") == f"变量 user_@{uid} 不应改写"

    face_id = _next_short_id(2)
    text = f"[CQ:image,file=test.png][CQ:face,id={face_id}]"
    assert normalize_malformed_at_markup(text) == text


def test_fix_raw_response_uses_shared_at_normalizer() -> None:
    uid = _next_user_id()
    assert fix_raw_response(f"你好 @id:{uid}@]") == f"你好 [@id:{uid}@]"


def test_at_markup_pattern_reads_normalized_nickname() -> None:
    uid = _next_user_id()
    match = AT_MARKUP_PATTERN.search(f"[@id:{uid};nickname:测试用户@]")

    assert match
    assert match.group("uid") == uid
    assert match.group("nickname") == "测试用户"


def test_at_markup_pattern_multiple_matches_in_order() -> None:
    uid_a = _next_user_id()
    uid_b = _next_user_id()
    text = f"hello [@id:{uid_a};nickname:用户一@] and [@id:{uid_b};nickname:用户二@]"

    matches = list(AT_MARKUP_PATTERN.finditer(text))

    assert [m.group("uid") for m in matches] == [uid_a, uid_b]
    assert [m.group("nickname") for m in matches] == ["用户一", "用户二"]


def test_at_markup_pattern_without_nickname() -> None:
    uid = _next_user_id()
    text = f"你好 [@id:{uid}@]"

    match = AT_MARKUP_PATTERN.search(text)

    assert match
    assert match.group("uid") == uid
    assert "nickname" in match.groupdict()
    assert match.group("nickname") is None


def test_normalize_malformed_at_markup_avoids_short_plain_numbers() -> None:
    uid = _next_short_id(3)
    assert normalize_malformed_at_markup(f"@{uid}") == f"@{uid}"


def test_normalize_malformed_at_markup_keeps_other_cq_codes() -> None:
    assert normalize_malformed_at_markup("[CQ:image,file=test.png]") == "[CQ:image,file=test.png]"


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("[@all@]", "@全体成员"),
        ("[@id:all@]", "@全体成员"),
        ("[CQ:at,qq=all]", "@全体成员"),
        ("[CQ:at,qq=all,name=全体成员]", "@全体成员"),
        ("提醒 [CQ:at,qq=all] 不要刷屏", "提醒 @全体成员 不要刷屏"),
        ("提醒 @id:all@] 不要刷屏", "提醒 @全体成员 不要刷屏"),
        ("提醒 [CQ:at,qq=all,name=全体成员] 不要刷屏", "提醒 @全体成员 不要刷屏"),
    ],
)
def test_neutralize_at_all_markup(raw_text: str, expected: str) -> None:
    assert neutralize_at_all_markup(raw_text) == expected


def _ref_msg_id_cases() -> list[tuple[str | None, str | None]]:
    plain_id = _next_user_id()
    prefixed_id = _next_user_id()
    message_id = _next_user_id()
    wrapped_id = _next_user_id()
    metadata_id = _next_user_id()
    quoted_id = _next_user_id()
    opaque_id = _next_user_id()
    nested_id = _next_user_id()
    nested_message_id = _next_user_id()
    nested_alias_id = _next_user_id()
    ref_id = _next_user_id()
    ref_arg_id = _next_user_id()
    reply_arg_id = _next_user_id()
    quote_wrapped_id = _next_user_id()
    square_wrapped_id = _next_user_id()
    chinese_wrapped_id = _next_user_id()
    angle_wrapped_id = _next_user_id()
    cq_reply_id = _next_user_id()
    bare_cq_reply_id = _next_user_id()
    assignment_id = _next_user_id()
    reply_assignment_id = _next_user_id()
    chinese_message_id = _next_user_id()
    metadata_prefix_id = _next_user_id()

    return [
        (None, None),
        ("", None),
        (plain_id, plain_id),
        (f"msg_id:{prefixed_id}", prefixed_id),
        (f"message_id={message_id}", message_id),
        (f"(msg_id:{wrapped_id})", wrapped_id),
        (f"msg_id：{metadata_id}, ref:{ref_id}", metadata_id),
        (f'msg_id:"{quoted_id}"', quoted_id),
        (f"`{opaque_id}`", f"`{opaque_id}`"),
        ("[opaque-id]", "[opaque-id]"),
        # 嵌套前缀：应剥离内层 msg_id/message_id
        (f'message_id="msg_id:{nested_id}"', nested_id),
        (f"msg_id: msg_id:{nested_message_id}", nested_message_id),
        (f"message_id=message_id:{nested_alias_id}", nested_alias_id),
        (f'ref_msg_id="msg_id:{ref_arg_id}"', ref_arg_id),
        (f"reply-msg-id: message_id:{reply_arg_id}", reply_arg_id),
        (f"'msg_id:{quote_wrapped_id}'", quote_wrapped_id),
        (f"[{square_wrapped_id}]", square_wrapped_id),
        (f"（{chinese_wrapped_id}）", chinese_wrapped_id),
        (f"<{angle_wrapped_id}>", angle_wrapped_id),
        (f"[CQ:reply,id={cq_reply_id}]", cq_reply_id),
        (f"CQ:reply,id={bare_cq_reply_id}", bare_cq_reply_id),
        (f"id={assignment_id}", assignment_id),
        (f"reply_id：{reply_assignment_id}", reply_assignment_id),
        (f"引用消息ID：{chinese_message_id}", chinese_message_id),
        (f"(msg_id:{metadata_prefix_id}, ref:{ref_id}, tome:true)", metadata_prefix_id),
    ]


@pytest.mark.parametrize(("raw_ref_msg_id", "expected"), _ref_msg_id_cases())
def test_normalize_ref_msg_id(raw_ref_msg_id: str | None, expected: str | None) -> None:
    assert normalize_ref_msg_id(raw_ref_msg_id) == expected


def test_platform_send_request_normalizes_ref_msg_id_implicitly() -> None:
    uid = _next_user_id()
    request = PlatformSendRequest(
        chat_key="onebot_v11-group_10000",
        segments=[PlatformSendSegment(type=PlatformSendSegmentType.TEXT, content="测试")],
        ref_msg_id=f'ref_msg_id="msg_id:{uid}"',
    )

    assert request.ref_msg_id == uid
