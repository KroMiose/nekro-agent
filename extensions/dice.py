import random

from nonebot.adapters.onebot.v11 import Bot

from nekro_agent.core import logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector

__meta__ = ExtMetaData(
    name="dice",
    description="Nekro-Agent 掷骰姬",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@agent_collector.mount_method(MethodType.AGENT)
async def dice_roll(event_name: str, description: str, difficulty: int, _ctx: AgentCtx) -> str:
    """对可能产生不同结果的事件发起掷骰检定请求以确认执行结果 (use lang: zh-CN)

    **应用场景: 战斗、防护、反抗、逃跑、随机事件、行为等 (!你需要在这些场景中积极使用掷骰检定!)**

    Args:
        event_name (str): 事件名称
        description (str): 事件详细描述
        difficulty (int): 事件难度 - 分析场景，给出一个客观合理的预期的难度值 (范围: 1-20)
    """

    assert 1 <= difficulty <= 20, "Difficulty should be between 1 and 20"

    def get_result_str(roll_result: int, difficulty: int) -> str:
        if roll_result == 1 and roll_result < difficulty:
            return "大失败!"
        if roll_result == 20 and roll_result >= difficulty:
            return "大成功!"
        if roll_result < difficulty:
            return "失败"
        if roll_result >= difficulty:
            return "成功"
        raise ValueError("Invalid roll result")

    roll_result = random.randint(1, 20)
    result_str = get_result_str(roll_result, difficulty)
    await chat_service.send_message(
        _ctx.from_chat_key,
        f"【检定事件】{event_name} ({difficulty}/20)\n> {description}\n========\n掷骰结果：{result_str} 【{roll_result}】",
    )
    return (
        f"[{event_name}] ({difficulty}/20) roll result: {roll_result}【{result_str}】\n"
        "Please continue to generate responses based on the results"
    )
