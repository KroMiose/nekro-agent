from enum import Enum


class MsgSignal(Enum):
    """
    用于控制消息处理流程的信号类型枚举。
    处理顺序是：记录消息 -> 触发处理。
    """

    CONTINUE = 0  # 继续处理消息，默认行为
    BLOCK_TRIGGER = 1  # 允许消息被记录到历史，但阻止消息触发后续处理
    BLOCK_ALL = 2  # 阻止消息被记录到历史，同时也会阻止消息触发后续处理
