import pytest

from nekro_agent.services.agent.resolver import fix_raw_response
from nekro_agent.tools.at_markup import AT_MARKUP_PATTERN, neutralize_at_all_markup, normalize_malformed_at_markup
from nekro_agent.tools.message_id import normalize_ref_msg_id


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("[@id:260674044@]", "[@id:260674044@]"),
        ("@id:260674044@]", "[@id:260674044@]"),
        ("@id:260674044@", "[@id:260674044@]"),
        ("@id:260674044", "[@id:260674044@]"),
        ("[id:260674044]", "[@id:260674044@]"),
        ("[id:260674044@]", "[@id:260674044@]"),
        ("[@id:260674044]", "[@id:260674044@]"),
        ("@[id:260674044]", "[@id:260674044@]"),
        ("@[@id:260674044@]", "[@id:260674044@]"),
        ("(@id:260674044;)", "[@id:260674044@]"),
        ("(@id:260674044)", "[@id:260674044@]"),
        ("（@id：260674044）", "[@id:260674044@]"),
        ("(@260674044)", "[@id:260674044@]"),
        ("[@260674044]", "[@id:260674044@]"),
        ("@260674044@)", "[@id:260674044@]"),
        ("@260674044", "[@id:260674044@]"),
        ("<@260674044>", "[@id:260674044@]"),
        ("<@!260674044>", "[@id:260674044@]"),
        ("<At:[@id:260674044@]>", "[@id:260674044@]"),
        ("<At:[@id:260674044]>", "[@id:260674044@]"),
        ("<7e56b348 | At:[@id:260674044@]>", "[@id:260674044@]"),
        ("【 @ id ： user_abc-01.test @ 】", "[@id:user_abc-01.test@]"),
        ("[@id:abcd#1234@]", "[@id:abcd#1234@]"),
        ("@id:abcd#1234@]", "[@id:abcd#1234@]"),
        ("[@id:260674044;nickname=测试用户]", "[@id:260674044;nickname:测试用户@]"),
        ("@id:260674044;nickname=测试用户@]", "[@id:260674044;nickname:测试用户@]"),
        ("（@id：260674044；nickname：测试用户）", "[@id:260674044;nickname:测试用户@]"),
        ("[CQ:at,qq=260674044]", "[@id:260674044@]"),
        ("[CQ:at,qq=260674044,name=测试用户]", "[@id:260674044;nickname:测试用户@]"),
        ("[CQ:at,qq=260674044,card=测试用户]", "[@id:260674044;nickname:测试用户@]"),
        ("[CQ:at,qq=all]", "[@id:all@]"),
        ("CQ:at,qq=260674044", "[@id:260674044@]"),
        ("[CQ:at,qq=260674044,foo=bar]", "[@id:260674044@]"),
        ("[cq:AT,qq=260674044]", "[@id:260674044@]"),
        ("[CQ:at, qq = 260674044 , name = 测试用户 ]", "[@id:260674044;nickname:测试用户@]"),
        ("@ ID = 260674044", "[@id:260674044@]"),
        ("@ id ： user_abc-01.test", "[@id:user_abc-01.test@]"),
        ("[@id:260674044;nickname:测试用户；]", "[@id:260674044;nickname:测试用户@]"),
        (" [CQ:at,qq=260674044] ", " [@id:260674044@] "),
        ("[CQ:at,qq=260674044,nickname=测试用户,foo=bar]", "[@id:260674044;nickname:测试用户@]"),
        ("<At:（@id:260674044）>", "[@id:260674044@]"),
        ("（@[@id:260674044@]）", "[@id:260674044@]"),
    ],
)
def test_normalize_malformed_at_markup(raw_text: str, expected: str) -> None:
    assert normalize_malformed_at_markup(raw_text) == expected


def test_normalize_malformed_at_markup_inside_sentence() -> None:
    # basic malformed bare @id pattern inside a sentence
    assert normalize_malformed_at_markup("你好 @id:260674044@] 请看这里") == "你好 [@id:260674044@] 请看这里"

    # CQ at-code embedded in text with punctuation should normalize in-place
    assert (
        normalize_malformed_at_markup("你好 [CQ:at,qq=260674044]，请看这里")
        == "你好 [@id:260674044@]，请看这里"
    )

    # angle-bracket at pattern embedded in text with surrounding whitespace
    assert (
        normalize_malformed_at_markup("你好，<@260674044> 请看这里") == "你好，[@id:260674044@] 请看这里"
    )


def test_normalize_malformed_at_markup_handles_multiple_mentions() -> None:
    assert (
        normalize_malformed_at_markup("你好 @id:260674044@] 和 [CQ:at,qq=123456789,name=测试用户]，请看 <@987654321>")
        == "你好 [@id:260674044@] 和 [@id:123456789;nickname:测试用户@]，请看 [@id:987654321@]"
    )

    assert (
        normalize_malformed_at_markup("混合：(@11111111)、@id:abcd#1234@]、【 @ id ： user_abc-01.test @ 】")
        == "混合：[@id:11111111@]、[@id:abcd#1234@]、[@id:user_abc-01.test@]"
    )

    assert (
        normalize_malformed_at_markup("[CQ:at,qq=11111111][CQ:at,qq=22222222]<@33333333>")
        == "[@id:11111111@][@id:22222222@][@id:33333333@]"
    )

    assert (
        normalize_malformed_at_markup("第一行 @id:11111111@]\n第二行 <@22222222>\n第三行 [CQ:at,qq=33333333]")
        == "第一行 [@id:11111111@]\n第二行 [@id:22222222@]\n第三行 [@id:33333333@]"
    )


def test_normalize_malformed_at_markup_is_idempotent() -> None:
    text = "你好 @id:260674044@] 和 [CQ:at,qq=123456789,name=测试用户]，请看 <@987654321>"
    normalized = normalize_malformed_at_markup(text)

    assert normalize_malformed_at_markup(normalized) == normalized


def test_normalize_malformed_at_markup_preserves_canonical() -> None:
    text = "你好 [@id:260674044;nickname:测试用户@]"

    assert normalize_malformed_at_markup(text) == text


def test_normalize_malformed_at_markup_preserves_non_mentions() -> None:
    assert normalize_malformed_at_markup("邮箱 test@260674044.com 不应被改写") == "邮箱 test@260674044.com 不应被改写"
    assert normalize_malformed_at_markup("版本号 @1234abc 不应被改写") == "版本号 @1234abc 不应被改写"
    assert normalize_malformed_at_markup("短号 @1234 不应被改写") == "短号 @1234 不应被改写"
    assert normalize_malformed_at_markup("数组 [@123] 不是平台用户标记") == "数组 [@123] 不是平台用户标记"
    assert normalize_malformed_at_markup("文本 [CQ:at,name=测试用户] 缺少 qq 不应改写") == "文本 [CQ:at,name=测试用户] 缺少 qq 不应改写"
    assert normalize_malformed_at_markup("链接 https://example.com/@260674044") == "链接 https://example.com/@260674044"
    assert normalize_malformed_at_markup("路径 /users/@260674044/profile") == "路径 /users/@260674044/profile"
    assert normalize_malformed_at_markup("变量 user_@260674044 不应改写") == "变量 user_@260674044 不应改写"
    assert normalize_malformed_at_markup("[CQ:image,file=test.png][CQ:face,id=14]") == "[CQ:image,file=test.png][CQ:face,id=14]"


def test_fix_raw_response_uses_shared_at_normalizer() -> None:
    assert fix_raw_response("你好 @id:260674044@]") == "你好 [@id:260674044@]"


def test_at_markup_pattern_reads_normalized_nickname() -> None:
    match = AT_MARKUP_PATTERN.search("[@id:260674044;nickname:测试用户@]")

    assert match
    assert match.group("uid") == "260674044"
    assert match.group("nickname") == "测试用户"


def test_normalize_malformed_at_markup_avoids_short_plain_numbers() -> None:
    assert normalize_malformed_at_markup("@123") == "@123"


def test_normalize_malformed_at_markup_keeps_other_cq_codes() -> None:
    assert normalize_malformed_at_markup("[CQ:image,file=test.png]") == "[CQ:image,file=test.png]"


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("[@all@]", "@全体成员"),
        ("[@id:all@]", "@全体成员"),
        ("[CQ:at,qq=all]", "@全体成员"),
        ("提醒 [CQ:at,qq=all] 不要刷屏", "提醒 @全体成员 不要刷屏"),
        ("提醒 @id:all@] 不要刷屏", "提醒 @全体成员 不要刷屏"),
    ],
)
def test_neutralize_at_all_markup(raw_text: str, expected: str) -> None:
    assert neutralize_at_all_markup(raw_text) == expected


@pytest.mark.parametrize(
    ("raw_ref_msg_id", "expected"),
    [
        (None, None),
        ("", None),
        ("255799348", "255799348"),
        ("msg_id:255799348", "255799348"),
        ("message_id=255799348", "255799348"),
        ("(msg_id:255799348)", "255799348"),
        ("msg_id：255799348, ref:123", "255799348"),
        ("`255799348`", "255799348"),
    ],
)
def test_normalize_ref_msg_id(raw_ref_msg_id: str | None, expected: str | None) -> None:
    assert normalize_ref_msg_id(raw_ref_msg_id) == expected
