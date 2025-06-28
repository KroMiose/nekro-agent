from pydantic import BaseModel


class PlatformMessageExt(BaseModel):
    """平台消息扩展数据"""

    ref_chat_key: str = ""  # 引用聊天会话唯一标识
    ref_msg_id: str = ""  # 引用消息的平台消息 ID
    ref_sender_id: str = ""  # 引用消息的发送者平台 ID
