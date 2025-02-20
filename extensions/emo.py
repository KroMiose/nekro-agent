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
    name="web",
    description="[NA] 表情包获取",
    version="0.1.0",
    author="wess09",
    url="https://github.com/KroMiose/nekro-agent",
)

@core.agent_collector.mount_method(core.MethodType.AGENT)
async def get_emoticon(keyword: str, _ctx: AgentCtx) -> str:
    """根据关键词获取表情包 URL 列表

    Args:
        keyword (str): 搜索关键词，如 "猫咪"、"搞笑"

    Returns:
        str: 表情包URL，如果获取失败则返回错误消息

    Example:
        get_emoticon("猫咪")
    """
    
    api_token = core.config.ALAPI_API_TOKEN
    url = "https://v3.alapi.cn/api/doutu"
    querystring = {"token": api_token, "keyword": keyword, "page": "1"}
    headers = {'Content-Type': 'application/json'}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=querystring, timeout=10)
            response.raise_for_status()  # 确保抛出 HTTPStatusError
            result = response.json()
            core.logger.debug(f"API 返回结果: {result}")  # 添加调试日志
            alapi_response = ALAPIResponse(**result)

            if alapi_response.code == 200:
                if alapi_response.data:
                    # 随机选择一个 URL 并在前面加上字符串
                    selected_url = random.choice(alapi_response.data)
                    return f"[表情包直链需下载发送] {selected_url}"
                else:
                    return "未找到相关表情包，请更换关键词重试。"
            else:
                return f"表情包获取失败: {alapi_response.msg}"

    except httpx.TimeoutException as e:
        core.logger.error(f"请求超时: {e}")
        return "请求超时，请稍后重试。"
    except httpx.HTTPStatusError as e:
        core.logger.error(f"HTTP 错误: {e}")
        return f"服务器返回错误: {e}"
    except Exception as e:
        core.logger.exception(f"发生未知错误: {e}")
        core.logger.debug(f"完整的响应内容: {response.text}")  # 添加完整响应内容的调试信息
        return f"发生未知错误，请联系管理员。"