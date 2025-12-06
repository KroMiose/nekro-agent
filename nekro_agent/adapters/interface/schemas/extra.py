from pydantic import BaseModel


class PlatformMessageExt(BaseModel):
    """平台消息扩展数据"""

<<<<<<< HEAD
    ref_chat_key: str = ""  # 引用聊天频道唯一标识
=======
<<<<<<< HEAD
    ref_chat_key: str = ""  # 引用聊天频道唯一标识
=======
<<<<<<< HEAD
    ref_chat_key: str = ""  # 引用聊天频道唯一标识
=======
    ref_chat_key: str = ""  # 引用聊天会话唯一标识
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    ref_msg_id: str = ""  # 引用消息的平台消息 ID
    ref_sender_id: str = ""  # 引用消息的发送者平台 ID
