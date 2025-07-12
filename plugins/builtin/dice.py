"""
# 掷骰姬 (Dice)

为 AI 提供强大的随机性工具，用于处理不确定性事件、角色扮演和互动游戏。

## 主要功能

- **掷骰检定**: 模拟跑团（TRPG）中的 D20 骰子，用于判定各种行为的成功与否。这是 AI 进行角色扮演时的核心工具，能为故事增加不确定性和趣味性。
- **概率轮盘**: 当一个事件有多种可能的结果时，可以使用此功能。可以为每个结果分配不同的概率，由轮盘来决定最终发生什么。
- **后台控制**: 管理员可以通过命令预设或锁定骰子点数，方便调试或引导特定剧情。

## 使用方法

- **AI 自动使用**: 在进行角色扮演或处理需要随机性的任务时，AI 会自动调用此插件。例如，当 AI 决定"尝试撬开一个锁"时，它会使用"掷骰检定"来判断自己是否成功。
- **命令控制**: 管理员可以使用 `dice_lock` 等命令在后台影响掷骰结果。

## 命令列表

**注意：所有命令目前仅在 OneBot v11 适配器下可用。**

- `dice_assert <1-20>`: 预设下一次掷骰的结果。
- `dice_lock <1-20>`: 锁定之后所有掷骰的结果。
- `dice_unlock`: 解除锁定。
"""
import random
from typing import Dict, List, Tuple

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from nekro_agent.adapters.onebot_v11.matchers.command import (
    command_guard,
    finish_with,
    on_command,
)
from nekro_agent.api import core, message
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx

plugin = NekroPlugin(
    name="掷骰姬",
    module_name="dice",
    description="提供掷骰检定能力和概率轮盘选择功能",
    version="0.2.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11", "discord"],
)

_ASSERT_DICE_NUM: int = 0
_LOCKED_DICE_NUM: int = 0


@on_command("dice_assert", aliases={"dice-assert"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)
    global _ASSERT_DICE_NUM

    if not cmd_content:
        await finish_with(matcher, message="需要指定一个难度值")
        return

    _ASSERT_DICE_NUM = int(cmd_content)
    assert 1 <= _ASSERT_DICE_NUM <= 20, "难度值应在 1 到 20 之间"

    await finish_with(matcher, message=f"掷骰检定预言: {_ASSERT_DICE_NUM}/20")


@on_command("dice_lock", aliases={"dice-lock"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)
    global _LOCKED_DICE_NUM

    if not cmd_content:
        await finish_with(matcher, message="需要指定一个锁定的骰点值")
        return

    try:
        dice_num = int(cmd_content)
        if not 1 <= dice_num <= 20:
            await finish_with(matcher, message="骰点值应在 1 到 20 之间")
            return

        _LOCKED_DICE_NUM = dice_num
        await finish_with(matcher, message=f"骰点已锁定为 {_LOCKED_DICE_NUM}")
    except ValueError:
        await finish_with(matcher, message="请输入有效的数字")


@on_command("dice_unlock", aliases={"dice-unlock"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)
    global _LOCKED_DICE_NUM

    _LOCKED_DICE_NUM = 0
    await finish_with(matcher, message="骰点锁定已解除")


def _weighted_random_choice(choices: Dict[str, float]) -> str:
    """纯概率轮盘选择，根据权重随机选择一个结果

    Args:
        choices: 选择项和权重的字典

    Returns:
        选中的结果名称
    """
    if not choices:
        return ""

    # 过滤掉权重为0或负数的选项
    valid_choices = {k: v for k, v in choices.items() if v > 0}
    if not valid_choices:
        # 如果所有权重都无效，随机选择一个原始选项
        return next(iter(choices.keys()))

    # 使用Python标准库的加权随机选择
    items = list(valid_choices.keys())
    weights = list(valid_choices.values())

    return random.choices(items, weights=weights, k=1)[0]


def _calculate_probabilities_with_fallback(
    event_choices: Dict[str, float],
    fallback_choice: str,
    total_probability: float = 100.0,
) -> Tuple[Dict[str, float], str]:
    """计算包含兜底事件的概率分布

    Args:
        event_choices: 事件选择和概率值的字典
        fallback_choice: 兜底事件名称
        total_probability: 总概率值

    Returns:
        (最终概率分布字典, 实际使用的兜底事件名称)
    """
    # 计算已分配的概率
    allocated_probability = 0.0
    valid_choices = {}

    for choice, prob in event_choices.items():
        if prob < 0:
            raise ValueError(f"概率值不能为负数: {choice} = {prob}")
        if prob > 0:
            valid_choices[choice] = prob
            allocated_probability += prob

    # 检查概率是否超出总值
    if allocated_probability > total_probability:
        raise ValueError(f"已分配概率 {allocated_probability} 超过总概率 {total_probability}")

    # 计算兜底事件的概率
    fallback_probability = total_probability - allocated_probability

    # 构建最终的概率分布
    final_probabilities = valid_choices.copy()

    # 确定兜底事件名称
    actual_fallback_choice = fallback_choice
    if not actual_fallback_choice:
        actual_fallback_choice = "其他情况"

    # 添加兜底事件（即使概率为0也添加，保持完整性）
    if actual_fallback_choice not in final_probabilities:
        final_probabilities[actual_fallback_choice] = fallback_probability
    else:
        # 如果兜底事件已在选择中，累加概率
        final_probabilities[actual_fallback_choice] += fallback_probability

    return final_probabilities, actual_fallback_choice


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="掷骰检定请求",
    description="设定一个待检定的目标事件和难度，投掷一次 20 面骰子，根据其结果成功与否进行接下来的行动",
)
async def dice_roll(_ctx: AgentCtx, event_name: str, description: str, difficulty: int) -> str:
    """对可能产生不同结果的事件发起掷骰检定请求以确认执行结果 (use lang: zh-CN)

    **应用场景: 战斗、施法、防护、反抗、逃跑、随机事件、行为、交互等 (!!!你需要在这些场景中积极使用掷骰检定!!!)**

    Args:
        event_name (str): 事件名称
        description (str): 事件详细描述
        difficulty (int): 事件难度 - 分析场景，给出一个客观合理的预期的难度值 (范围: 1-20)
    """

    assert 1 <= difficulty <= 20, "Difficulty should be between 1 and 20"

    # 由于 LLM 倾向指定难度值偏高，因此在指定高难度时随机降低难度
    if difficulty >= 19 and random.randint(1, 20) < 12:
        add_coin = random.randint(1, 3)
        fix_diff_show = f"(+{add_coin})"
        fix_str = f"(幸运祝福: 骰点 +{add_coin})\n"
        fix_str_en = f"(Lucky bonus: +{add_coin})"
    else:
        fix_diff_show = ""
        add_coin = 0
        fix_str = ""
        fix_str_en = ""

    def get_result_str(roll_result: int, fixed_roll_result: int, difficulty: int) -> str:
        if fixed_roll_result == 1 and fixed_roll_result < difficulty:
            return "大失败！"
        if roll_result == 20 and fixed_roll_result >= difficulty:
            return "大成功！"
        if fixed_roll_result < difficulty:
            return "失败"
        if fixed_roll_result >= difficulty:
            return "成功"
        raise ValueError("Invalid roll result")

    global _ASSERT_DICE_NUM, _LOCKED_DICE_NUM

    # 优先级：预言骰点 > 锁定骰点 > 随机骰点
    if _ASSERT_DICE_NUM > 0:
        roll_result = _ASSERT_DICE_NUM
        _ASSERT_DICE_NUM = 0
    elif _LOCKED_DICE_NUM > 0:
        roll_result = _LOCKED_DICE_NUM
    else:
        roll_result = random.randint(1, 20)

    result_str = get_result_str(roll_result, roll_result + add_coin, difficulty)

    await message.send_text(
        _ctx.chat_key,
        f"【检定事件】{event_name} ({difficulty}/20)\n> {description}\n========\n{fix_str}掷骰结果：{roll_result}{fix_diff_show} 【{result_str}】",
        _ctx,
        record=False,  # 掷骰结果不需要记录到上下文
    )
    return (
        f"[{event_name}] ({difficulty}/20) {fix_str_en} roll result: {roll_result}{fix_diff_show}【{result_str}】\n"
        "Note: This is only an effect check for the action, not a substitute for the action itself. You still need to actually perform (and be able to perform) the corresponding action.\n"
        "Please continue to generate responses based on the results"
    )


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="概率轮盘选择",
    description="基于概率分配的轮盘选择，用于多分支随机事件的结果确定",
)
async def probability_wheel(
    _ctx: AgentCtx,
    event_name: str,
    description: str,
    event_choices: Dict[str, float],
    fallback_choice: str = "其他情况",
    total_probability: float = 100.0,
) -> str:
    """基于概率分配的轮盘选择系统

    **应用场景: 多分支随机事件、概率性奖励、复合结果判定、随机遭遇等**
    **逻辑: 兜底事件自动占据剩余的未分配概率空间**

    Args:
        event_name (str): 事件名称
        description (str): 事件详细描述
        event_choices (Dict[str, float]): 选择项和概率值，格式: {"选择项描述": 概率值}
        fallback_choice (str): 兜底事件名称，自动获得剩余概率
        total_probability (float): 总概率值，默认100.0

    Returns:
        str: 选择结果和概率信息

    Example:
        probability_wheel(
            event_name="探索神秘宝箱",
            description="打开一个散发着奇异光芒的古老宝箱",
            event_choices={
                "获得稀有魔法武器": 5.0,     # 分配 5 概率
                "获得一些金币": 30.0,        # 分配 30 概率
                "触发陷阱机关": 15.0,        # 分配 15 概率
            },
            fallback_choice="宝箱是空的",    # 自动获得剩余 50 概率
            total_probability=100.0           # 总概率 100
        )
    """

    # 参数验证
    if total_probability <= 0:
        raise ValueError("总概率必须大于0")

    if not event_choices and not fallback_choice:
        raise ValueError("必须提供事件选择或兜底事件")

    # 计算最终概率分布
    final_probabilities, actual_fallback = _calculate_probabilities_with_fallback(
        event_choices,
        fallback_choice,
        total_probability,
    )

    # 执行概率选择
    selected_choice = _weighted_random_choice(final_probabilities)

        # 格式化概率显示 - 只显示概率大于0的事件
    probability_lines = []
    sorted_probs = sorted(final_probabilities.items(), key=lambda x: x[1], reverse=True)
    
    for choice, probability in sorted_probs:
        if probability > 0:  # 只显示概率大于0的事件
            marker = "🎯" if choice == selected_choice else "  "
            percentage = (probability / total_probability) * 100
            probability_lines.append(f"{marker} {choice}: {percentage:.1f}%")
    
    probability_text = "\n".join(probability_lines)
    
    # 计算兜底事件概率用于返回信息
    fallback_prob = final_probabilities.get(actual_fallback, 0)
    fallback_percentage = (fallback_prob / total_probability) * 100
    
    # 发送结果到聊天
    await message.send_text(
        _ctx.chat_key,
        f"【轮盘事件】{event_name}\n> {description}\n========\n"
        f"概率分配:\n{probability_text}\n\n"
        f"🎯 选择结果: 【{selected_choice}】",
        _ctx,
        record=False,
    )

    selected_percentage = (final_probabilities.get(selected_choice, 0) / total_probability) * 100

    return (
        f"[Probability Wheel: {event_name}]\n"
        f"Selected: {selected_choice}\n"
        f"Probability: {final_probabilities.get(selected_choice, 0):.1f}/{total_probability} ({selected_percentage:.1f}%)\n"
        f"Fallback '{actual_fallback}' had: {fallback_prob:.1f}/{total_probability} ({fallback_percentage:.1f}%)\n"
        f"Total distributed: {total_probability}\n"
        "Continue your response based on the selected outcome."
    )


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
    global _ASSERT_DICE_NUM, _LOCKED_DICE_NUM
    _ASSERT_DICE_NUM = 0
    _LOCKED_DICE_NUM = 0
