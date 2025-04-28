import random

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from pydantic import Field

from nekro_agent.api import core, message
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.matchers.command import command_guard, finish_with, on_command
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="掷骰姬",
    module_name="dice",
    description="提供掷骰检定能力",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
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
        _ctx.from_chat_key,
        f"【检定事件】{event_name} ({difficulty}/20)\n> {description}\n========\n{fix_str}掷骰结果：{roll_result}{fix_diff_show} 【{result_str}】",
        _ctx,
        record=False,  # 掷骰结果不需要记录到上下文
    )
    return (
        f"[{event_name}] ({difficulty}/20) {fix_str_en} roll result: {roll_result}{fix_diff_show}【{result_str}】\n"
        "Please continue to generate responses based on the results"
    )


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
    global _ASSERT_DICE_NUM, _LOCKED_DICE_NUM
    _ASSERT_DICE_NUM = 0
    _LOCKED_DICE_NUM = 0
