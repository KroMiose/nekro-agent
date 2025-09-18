"""
Telegram 适配器路由
"""

from fastapi import APIRouter

router = APIRouter(prefix="/adapters/telegram", tags=["adapters", "telegram"])


@router.get("/info")
async def get_telegram_info():
    """获取 Telegram 适配器信息"""
    return {
        "adapter": "telegram",
        "status": "ready",
        "message": "Telegram 适配器已准备就绪"
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}