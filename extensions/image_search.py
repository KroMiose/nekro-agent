import httpx

from typing import List, Optional
from nekro_agent.core import logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector
from nekro_agent.services.chat import chat_service
from nekro_agent.core import config

__meta__ = ExtMetaData(
    name="lolicon_image",
    description="[NA] 二次元图片获取插件",
    version="0.2.0",
    author="Zaxpris, wess09",
    url="https://github.com/zxjwzn",
)

#给人看的
async def get_lolicon_image(tags: List[str], _ctx: AgentCtx) -> str:
    """获取二次元图片字节流
    
    Args:
        tags (List[str]): 搜索标签列表
        
    Returns:
        bytes: 二次元图片的字节流，如果失败则返回错误消息
    """
    # 合并配置参数
    r18_config = config.R18_CONFIG
    params = {
        "r18": 2 if r18_config else 0,
        "num": 1,
        "tag": tags,
        "size": "original"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 发送 POST 请求
            response = await client.post(
                "https://api.lolicon.app/setu/v2",
                json=params
            )
            data = response.json()
            # 提取第一个结果的原始图片地址
            first_item = data["data"][0]
            return first_item["urls"].get("original", "[Lolicon] Invalid image specification")
    except Exception as e:
        logger.error(f"获取图片时发生未知错误: {e}")
        return "未知错误"

#给AI看的
@agent_collector.mount_method(MethodType.TOOL)
async def lolicon_image_search(tags: List[str], _ctx: AgentCtx) -> bytes:
    """二次元图片搜索
    获取二次元图片并返回字节流
    *仅会返回.jpg格式的图片字节流*
    Args:
        tags (List[str]): 搜索标签列表，只能同时3个标签
    Returns:
        bytes: 二次元图片的字节流
    """

    clean_tags = [t.strip() for t in tags if t.strip()]

    # 执行搜索
    result = await get_lolicon_image(clean_tags, _ctx)
    
    # 格式化输出
    if result.startswith("http"):
        async with httpx.AsyncClient(timeout=10.0) as client:
            image_result = await client.get(result)
            image_result.raise_for_status()
            return image_result.content
    return result.encode()

async def clean_up():
    """清理扩展"""
