import random  # 导入 random 模块
import httpx
from typing import Optional, List
from pydantic import BaseModel, Field

from nekro_agent.core import config, logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector

class ALAPIResponse(BaseModel):
    """ALAPI 接口返回数据模型"""
    code: int = Field(description="状态码")
    msg: Optional[str] = Field(default="无消息", description="消息")  # 将 msg 设置为可选
    data: Optional[List[str]] = Field(default=None, description="数据")  # 确保 data 是一个列表

__meta__ = ExtMetaData(
    name="emo",
    description="[NA] 表情包获取",
    version="0.1.0",
    author="wess09",
    url="https://github.com/KroMiose/nekro-agent",
)

@core.agent_collector.mount_method(core.MethodType.TOOL)
async def get_emoticon(keyword: str, _ctx: AgentCtx) -> bytes:
    """根据关键词获取表情包 URL 并返回字节流
    **在任何表达情绪的时候使用**
    Args:
        keyword (str): 搜索关键词，如 "猫咪"、"搞笑"

    Returns:
        bytes: 表情包图片的字节流，如果获取失败则返回错误消息

    Example:
        get_emoticon("柴郡")
    """
    # 自定义请求方便自定义API
    url = config.EMO_API_URL
    api_token = config.EMO_API_API_TOKEN
    api_type = config.EMO_API_TYPE
    api_page = config.EMO_API_PAGE
    
    # 构建请求参数
    querystring = {"keyword": keyword}
    if api_token:
        querystring["token"] = api_token
    if api_page:
        querystring["page"] = api_page
    if api_type:
        querystring["type"] = api_type

    headers = {'Content-Type': 'application/json'}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=querystring, timeout=10)
            result = response.json()
            alapi_response = ALAPIResponse(**result)
            if alapi_response.data:
                # 过滤掉后缀不是 .jpg 的 URL
                valid_urls = [url for url in alapi_response.data if url.endswith('.jpg')]
                if valid_urls:
                    selected_url = random.choice(valid_urls)
                    # 下载图片并返回字节流
                    image_response = await client.get(selected_url)
                    image_response.raise_for_status()
                    return image_response.content
                else:
                    raise Exception("未找到有效的表情包链接，请更换关键词重试。")
            else:
                raise Exception("未找到相关表情包，请更换关键词重试。")
    except Exception as e:
        core.logger.exception(f"错误: {e}")
