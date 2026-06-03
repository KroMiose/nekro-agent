import pytest

from nekro_agent.services.agent.resolver import fix_raw_response
from nekro_agent.tools.at_markup import AT_MARKUP_PATTERN, normalize_malformed_at_markup


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
    ],
)
def test_normalize_malformed_at_markup(raw_text: str, expected: str) -> None:
    assert normalize_malformed_at_markup(raw_text) == expected


def test_normalize_malformed_at_markup_inside_sentence() -> None:
    assert normalize_malformed_at_markup("你好 @id:260674044@] 请看这里") == "你好 [@id:260674044@] 请看这里"


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
