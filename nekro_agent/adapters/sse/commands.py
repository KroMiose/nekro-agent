"""
SSE 命令处理模块
==============

定义SSE协议使用的各种命令处理逻辑，包含:
1. 命令模型 (Command, RegisterCommand, SubscribeCommand等)
2. 命令处理器 (handle_register, handle_subscribe等)
3. 辅助函数和工具
"""

from functools import wraps
from typing import Any, Callable, Dict, Optional, Type

from fastapi import HTTPException
from pydantic import BaseModel, Field

from nekro_agent.adapters.interface import collect_message
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformUser,
)
from nekro_agent.adapters.sse.core.client import SseClientManager
from nekro_agent.adapters.sse.core.message import SseMessageConverter
from nekro_agent.adapters.sse.sdk.models import (
    ChannelSubscribeRequest,
    ChannelSubscribeResponse,
    ClientCommand,
    ReceiveMessage,
    RegisterRequest,
    RegisterResponse,
)
from nekro_agent.adapters.sse.sdk.models import (
    Response as SseResponse,
)
from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.core import logger
from nekro_agent.schemas.chat_message import ChatType

# 全局客户端管理器 - 从外部导入实例
client_manager: SseClientManager

# 消息转换器
message_converter = SseMessageConverter()

# 命令处理器注册表
_command_handlers: Dict[str, Callable] = {}

# 命令模型注册表
_command_models: Dict[str, Type[BaseModel]] = {}


# 装饰器：命令处理器
def command_handler(cmd: ClientCommand, model: Optional[Type[BaseModel]] = None):
    """命令处理器装饰器

    Args:
        cmd: 命令名称
        model: 命令数据模型（可选）
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # 注册命令处理器
        _command_handlers[cmd.value] = wrapper

        # 注册命令模型
        if model:
            _command_models[cmd.value] = model

        return wrapper

    return decorator


# 消息命令模型
class MessageCommand(BaseModel):
    """消息命令"""

    channel_id: str = Field(..., description="频道ID")
    message: ReceiveMessage = Field(..., description="消息内容")


# 消息响应模型
class MessageResponse(BaseModel):
    """消息响应"""

    message: str = Field(..., description="响应消息")


def set_client_manager(manager: SseClientManager) -> None:
    """设置全局客户端管理器

    Args:
        manager: 客户端管理器实例
    """
    global client_manager
    client_manager = manager


# 注册命令处理器
@command_handler(ClientCommand.REGISTER, RegisterRequest)
async def handle_register(command: RegisterRequest) -> RegisterResponse:
    """处理注册命令"""
    client = client_manager.register_client(command.client_name, command.platform)
    return RegisterResponse(
        client_id=client.client_id,
        message=f"客户端 {command.client_name} ({command.client_version}) 注册成功",
    )


# 订阅频道命令处理器
@command_handler(ClientCommand.SUBSCRIBE, ChannelSubscribeRequest)
async def handle_subscribe(command: ChannelSubscribeRequest, client_id: str) -> ChannelSubscribeResponse:
    """处理订阅频道命令"""
    client = client_manager.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"客户端 {client_id} 不存在")

    for channel_id in command.channel_ids:
        client.add_channel(channel_id)
    return ChannelSubscribeResponse(message=f"批量订阅 {len(command.channel_ids)} 个频道成功")


# 取消订阅频道命令处理器
@command_handler(ClientCommand.UNSUBSCRIBE, ChannelSubscribeRequest)
async def handle_unsubscribe(command: ChannelSubscribeRequest, client_id: str) -> ChannelSubscribeResponse:
    """处理取消订阅频道命令"""
    client = client_manager.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"客户端 {client_id} 不存在")

    for channel_id in command.channel_ids:
        client.remove_channel(channel_id)
    return ChannelSubscribeResponse(message=f"批量取消订阅 {len(command.channel_ids)} 个频道成功")


# 消息命令处理器
@command_handler(ClientCommand.MESSAGE, MessageCommand)
async def handle_message(command: MessageCommand, client_id: str) -> MessageResponse:
    """处理消息命令"""
    client = client_manager.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"客户端 {client_id} 不存在")

    # 消息已经由Pydantic模型自动解析
    sse_message = command.message

    # 创建平台消息
    platform_message = await message_converter.sse_to_platform_message(sse_message)

    platform_channel = PlatformChannel(
        channel_id=sse_message.channel_id,
        channel_name=sse_message.channel_name,
        channel_type=ChatType.GROUP,
    )

    # 创建用户信息
    platform_user = PlatformUser(
        platform_name=sse_message.platform_name,
        user_id=sse_message.from_id,
        user_name=sse_message.from_name,
        user_avatar="",
    )

    sse_adapter = adapter_utils.get_adapter("sse")

    # 调用消息收集器
    await collect_message(sse_adapter, platform_channel, platform_user, platform_message)

    return MessageResponse(message="消息接收成功")


# 响应命令处理器
@command_handler(ClientCommand.RESPONSE, SseResponse)
async def handle_response(command: SseResponse, client_id: str) -> Dict[str, bool]:
    """处理响应命令"""
    # 获取客户端
    client = client_manager.get_client(client_id)
    if not client:
        logger.error(f"客户端 {client_id} 不存在")
        return {"success": False}

    # 处理客户端响应
    result = await client.handle_response(command)

    return {"success": result}
