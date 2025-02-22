import random  # 导入 random 模块
import httpx
from typing import Optional, List
from pydantic import BaseModel, Field

from nekro_agent.core import config
from nekro_agent.api import core
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
    version="0.5.0",
    author="wess09",
    url="https://github.com/KroMiose/nekro-agent",
)

@core.agent_collector.mount_method(core.MethodType.TOOL)
async def get_emoticon(keyword: str, _ctx: AgentCtx) -> Optional[bytes]:
    """根据情绪获取表情包
    **在任何表达情绪的时候使用**
    Args:
        keyword (str): 情绪，如 "开心"、"生气"
        ！！只能填写情绪，如开心，生气，伤心，震惊！！
        不可以填写具体内容，如"害怕的xxx""生气的xxx"
        仅支持每次单个情绪搜索
    Returns:
        bytes: 表情包图片的字节流
        传回的字节流只存在jpg类型的图片

    Example:
        get_emoticon("生气")
    """
    # 自定义请求方便自定义API
    url = config.EMO_API_URL
    api_token = config.EMO_API_TOKEN
    api_type = 1
    api_page = 1
    
    # 合并关键词
    combined_keyword = f"{config.EMO_API_KEYWORD} {keyword}"
    
    # 构建请求参数
    querystring = {"keyword": combined_keyword}
    if api_token:
        querystring["token"] = api_token
    # 将 int 类型转换为 str 类型
    if api_page:
        querystring["page"] = str(api_page)  # 确保 page 是字符串
    if api_type:
        querystring["type"] = str(api_type)  # 确保 type 是字符串

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
    except Exception as e:
        core.logger.exception(f"错误: {e}")

async def clean_up():
    """清理扩展"""