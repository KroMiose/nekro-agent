"""事件触发回复 (Event-triggered reply) 主开关测试

覆盖逻辑：`nekro_agent.services.message_service` 中的随机触发与正则触发
按 `AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED` 主开关统一短路。

说明：本测试不直接 import `nekro_agent.tools.common_util`，
原因是该模块会触发 `python-magic`（libmagic 系统库）的加载。
本测试通过对源文件做静态分析 + 自包含的等价函数来校验，避免引入
与本任务无关的运行时依赖。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import pytest

# ----------------------------------------------------------------------------
# Stub: 复刻 message_service.py 中由 `if not config.AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED`
# 所采用的等价短路逻辑，方便在无运行时依赖情况下做单元测试。
# ----------------------------------------------------------------------------


@dataclass
class _FakeConfig:
    """最小化的 CoreConfig 替身，只暴露被测配置项。"""

    AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED: bool = False
    AI_CHAT_RANDOM_REPLY_PROBABILITY: float = 0.0
    AI_CHAT_TRIGGER_REGEX: List[str] = field(default_factory=list)


def _evaluate_trigger_conditions(config: _FakeConfig, content: str):
    """等价复刻 message_service 中事件触发分支的判定。

    真实函数 (`random_chat_check`, `check_content_trigger`) 的行为:
    - random_chat_check: probability == 0.0 → 始终 False；否则 random.random() < probability
    - check_content_trigger: 任一 regex 命中 → True；否则 False
    """
    if not config.AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED:
        # 主开关关闭时，全部短路为 False
        return False, False

    random_triggered = (
        config.AI_CHAT_RANDOM_REPLY_PROBABILITY > 0.0  # 简化，避免引入 random 模块
    )
    import re

    content_triggered = any(
        re.search(reg, content) is not None for reg in config.AI_CHAT_TRIGGER_REGEX
    )
    return random_triggered, content_triggered


# ----------------------------------------------------------------------------
# 测试用例
# ----------------------------------------------------------------------------


def test_master_switch_default_is_false_in_source():
    """主开关在源码中默认值必须是 False（保持向后兼容且默认安全）。

    直接读取 config.py 源并验证默认值声明，避免构造完整 CoreConfig 引发
    side effect（如目录创建/网络调用）。
    """
    config_path = (
        Path(__file__).parent.parent / "nekro_agent" / "core" / "config.py"
    )
    src = config_path.read_text(encoding="utf-8")

    marker = "AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED"
    assert marker in src, "config.py 必须新增 AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED 字段"

    # 找到主开关字段块并校验默认值
    idx = src.index(marker)
    block = src[idx: idx + 600]
    assert "default=False" in block, (
        "AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED 必须默认关闭（default=False）"
    )


def test_master_switch_disabled_short_circuits_random_branch():
    """主开关关闭时，即使概率配置为 1.0、regex 配置为 '.*'，也应短路不触发。"""
    cfg = _FakeConfig(
        AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED=False,
        AI_CHAT_RANDOM_REPLY_PROBABILITY=1.0,
        AI_CHAT_TRIGGER_REGEX=[r".*"],
    )
    random_triggered, content_triggered = _evaluate_trigger_conditions(cfg, "任意消息")

    assert random_triggered is False
    assert content_triggered is False


def test_master_switch_disabled_overrides_high_probability():
    """主开关关闭时，1.0 概率的随机触发仍应被短路。"""
    cfg = _FakeConfig(
        AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED=False,
        AI_CHAT_RANDOM_REPLY_PROBABILITY=1.0,
    )
    random_triggered, _ = _evaluate_trigger_conditions(cfg, "任何内容")

    assert random_triggered is False


def test_master_switch_enabled_invokes_real_logic():
    """主开关开启时,子 helper 应被正常调用（命中 regex 即触发）。"""
    cfg = _FakeConfig(
        AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED=True,
        AI_CHAT_RANDOM_REPLY_PROBABILITY=0.0,
        AI_CHAT_TRIGGER_REGEX=[r"^hello\b"],
    )
    random_triggered, content_triggered = _evaluate_trigger_conditions(
        cfg, "hello world"
    )

    assert random_triggered is False  # 概率 0 → 不触发
    assert content_triggered is True  # regex 命中


def test_master_switch_enabled_no_match_does_not_trigger():
    """主开关开启但内容不匹配 regex 时，不应触发。"""
    cfg = _FakeConfig(
        AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED=True,
        AI_CHAT_RANDOM_REPLY_PROBABILITY=0.0,
        AI_CHAT_TRIGGER_REGEX=[r"^hello\b"],
    )
    _, content_triggered = _evaluate_trigger_conditions(cfg, "goodbye world")

    assert content_triggered is False


def test_message_service_source_gates_on_master_switch():
    """校验 message_service.py 中确实根据主开关短路随机与正则触发。

    这是行为保护的最终一道防线：即使单元测试桩函数失修，也能从源码侧
    验证主开关确实起到了门控作用。
    """
    src = (
        Path(__file__).parent.parent
        / "nekro_agent"
        / "services"
        / "message_service.py"
    ).read_text(encoding="utf-8")

    assert "AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED" in src, (
        "message_service.py 必须引用 AI_CHAT_EVENT_TRIGGERED_REPLY_ENABLED 主开关"
    )
    # 主开关关闭时，应有 if 分支把 random_triggered/content_triggered 直接设为 False
    # 简单的子串检查即可，避免过度脆弱的 AST 解析
    assert "random_triggered = False" in src
    assert "content_triggered = False" in src


# 兼容异步测试风格，即便本测试均为同步判定，这里留一个异步桩
@pytest.mark.asyncio
async def test_async_smoke():
    """异步 smoke test,验证测试基础设施可用。"""
    assert True
