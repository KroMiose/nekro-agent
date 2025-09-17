"""
Telegram 适配器路由
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from nekro_agent.services.user.deps import get_current_user
from nekro_agent.schemas.user import User
from nekro_agent.core.logger import logger

from .adapter import TelegramAdapter

# 创建路由
router = APIRouter(prefix="/adapters/telegram", tags=["adapters", "telegram"])


@router.get("/chats")
async def get_telegram_chats(
    current_user: User = Depends(get_current_user)
):
    """
    获取机器人加入的所有聊天列表
    
    此接口需要管理员权限
    """
    from nekro_agent.adapters import adapter_manager
    
    # 检查用户权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 获取Telegram适配器
    adapter = adapter_manager.get_adapter("telegram")
    if not adapter or not isinstance(adapter, TelegramAdapter):
        raise HTTPException(status_code=503, detail="Telegram适配器未启用")
    
    # 在实际实现中，这里应该调用Telegram API获取聊天列表
    # 这里返回模拟数据
    return {
        "status": "success",
        "chats": [
            {
                "id": "123456789",
                "name": "个人聊天",
                "type": "private"
            },
            {
                "id": "-1001234567890",
                "name": "测试群组",
                "type": "group"
            }
        ]
    }


@router.post("/send_message")
async def send_telegram_message(
    chat_id: str,
    text: str,
    current_user: User = Depends(get_current_user)
):
    """
    发送消息到指定的Telegram聊天
    
    此接口需要管理员权限
    """
    from nekro_agent.adapters import adapter_manager
    
    # 检查用户权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 获取Telegram适配器
    adapter = adapter_manager.get_adapter("telegram")
    if not adapter or not isinstance(adapter, TelegramAdapter):
        raise HTTPException(status_code=503, detail="Telegram适配器未启用")
    
    try:
        # 构建聊天键（OneBot 风格），根据 chat_id 正负判断类型
        # Telegram 中群/频道 chat_id 通常为负数（如 -100xxxxxxxxxx），私聊为正数
        channel_id = f"group_{chat_id}" if str(chat_id).startswith("-") else f"private_{chat_id}"
        chat_key = adapter.build_chat_key(channel_id)
        
        # 创建发送请求
        from nekro_agent.adapters.interface.schemas.platform import (
            PlatformSendRequest,
            PlatformSendSegment,
            PlatformSendSegmentType
        )
        
        request = PlatformSendRequest(
            chat_key=chat_key,
            segments=[
                PlatformSendSegment(
                    type=PlatformSendSegmentType.TEXT,
                    content=text
                )
            ]
        )
        
        # 发送消息
        result = await adapter.forward_message(request)
        
        if result.success:
            return {
                "status": "success",
                "message": "消息发送成功"
            }
        else:
            raise HTTPException(status_code=500, detail=result.error_message)
    except Exception as e:
        logger.error(f"发送Telegram消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.get("/status")
async def get_telegram_status():
    """
    获取Telegram适配器的状态
    """
    from nekro_agent.adapters import adapter_manager
    
    # 获取Telegram适配器
    adapter = adapter_manager.get_adapter("telegram")
    if not adapter or not isinstance(adapter, TelegramAdapter):
        return {
            "status": "disconnected",
            "message": "Telegram适配器未启用"
        }
    
    # 检查客户端状态
    client = getattr(adapter, "client", None)
    if not client:
        return {
            "status": "disconnected",
            "message": "Telegram客户端未初始化"
        }
    
    # 检查连接状态
    # 在实际实现中，这里应该检查Pyrogram客户端的连接状态
    is_connected = False
    if hasattr(client, "_client") and hasattr(client._client, "is_connected"):
        is_connected = client._client.is_connected
    
    return {
        "status": "connected" if is_connected else "disconnected",
        "metadata": adapter.metadata.model_dump()
    }


@router.get("/users/{user_id}")
async def get_telegram_user_info(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取Telegram用户信息
    
    此接口需要管理员权限
    """
    from nekro_agent.adapters import adapter_manager
    
    # 检查用户权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # 获取Telegram适配器
    adapter = adapter_manager.get_adapter("telegram")
    if not adapter or not isinstance(adapter, TelegramAdapter):
        raise HTTPException(status_code=503, detail="Telegram适配器未启用")
    
    try:
        # 获取用户信息
        user_info = await adapter.get_platform_user(user_id)
        
        if user_info:
            return {
                "status": "success",
                "user": user_info.model_dump()
            }
        else:
            raise HTTPException(status_code=404, detail="用户不存在")
    except Exception as e:
        logger.error(f"获取Telegram用户信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")