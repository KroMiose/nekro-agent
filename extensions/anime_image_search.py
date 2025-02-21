import httpx


from typing import List, Optional
from nekro_agent.core import config, logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector
from nekro_agent.services.chat import chat_service

__meta__ = ExtMetaData(
    name="lolicon_image",
    description="[NA] 二次元图片获取插件",
    version="0.1.0",
    author="Zaxpris, wess09",
    url="https://github.com/zxjwzn",
)


async def get_lolicon_image(tags: List[str], _ctx: AgentCtx) -> str:
    """获取二次元图片字节流
    
    Args:
        tags (List[str]): 搜索标签列表
        
    Returns:
        bytes: 二次元图片的字节流，如果失败则返回错误消息
    """
    # 合并配置参数
    params = {
        "r18": 0,
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
            
            if response.status_code != 200:
                error_msg = f"API 返回异常状态码: {response.status_code}"
                if error_data := response.json().get("error"):
                    error_msg += f" | {error_data}"
                return f"[Lolicon] {error_msg}"

            data = response.json()
            
            # 检查错误信息
            if data.get("error"):
                return f"[Lolicon] API 错误: {data['error']}"
                
            if not data.get("data"):
                return "[Lolicon] 未找到匹配的图片"

            # 提取第一个结果的原始图片地址
            first_item = data["data"][0]
            return first_item["urls"].get("original", "[Lolicon] 无效的图片规格")

    except httpx.NetworkError as e:
        logger.error(f"网络连接失败 | {str(e)}")
        return f"[Lolicon] 网络错误: {str(e)}"
    except Exception as e:
        logger.exception("图片获取失败")
        return f"[Lolicon] 请求失败: {str(e)}"

@agent_collector.mount_method(MethodType.TOOL)
async def lolicon_image_search(tags: List[str], _ctx: AgentCtx) -> bytes:
    """二次元图片搜索
    获取二次元图片并返回字节流
    
    Args:
        tags (List[str]): 搜索标签列表
    Returns:
        bytes: 二次元图片的字节流，如果失败则返回错误消息
    """

    # 空标签过滤
    clean_tags = [t.strip() for t in tags if t.strip()]
    if not clean_tags:
        return "[错误] 至少需要提供一个有效标签"

    # 限制标签数量
    if len(clean_tags) > 3:
        return "[错误] 最多支持 3 个标签组合"
    
    # 执行搜索
    result = await get_lolicon_image(clean_tags, _ctx)
    
    # 格式化输出
    if result.startswith("http"):
        async with httpx.AsyncClient(timeout=10.0) as client:
            image_result = await client.get(result)
            image_result.raise_for_status()
            return image_result.content
    return result
