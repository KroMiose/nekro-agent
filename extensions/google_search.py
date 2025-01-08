import time
from typing import Optional

from httpx import AsyncClient

from nekro_agent.core import config, logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector

__meta__ = ExtMetaData(
    name="google_search",
    description="[NA] Google搜索工具",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)

_last_keyword = None
_last_call_time = 0


@agent_collector.mount_method(MethodType.AGENT)
async def google_search(keyword: str, _ctx: AgentCtx) -> str:
    """使用 Google 搜索获取实时信息

    * 调用即此方法即结束响应，直到搜索结果返回

    Args:
        keyword (str): 搜索关键词
    """
    global _last_keyword, _last_call_time

    # 防止重复搜索和频繁调用
    if keyword == _last_keyword or time.time() - _last_call_time < 10:
        return "搜索太频繁，请稍后再试"

    proxy = config.DEFAULT_PROXY
    api_key = config.GOOGLE_SEARCH_API_KEY
    cx_key = config.GOOGLE_SEARCH_CX_KEY
    max_results = config.GOOGLE_SEARCH_MAX_RESULTS or 3

    if not api_key or not cx_key:
        return "[Google] 未配置 API Key 或 CX Key"

    if proxy and not proxy.startswith("http"):
        proxy = f"http://{proxy}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        async with AsyncClient(proxies=proxy) as cli:
            response = (
                await cli.get(
                    "https://www.googleapis.com/customsearch/v1",
                    headers=headers,
                    params={"key": api_key, "cx": cx_key, "q": keyword},
                )
            ).json()
    except Exception as e:
        logger.exception("Google搜索失败")
        return f"[Google] 搜索失败: {e!s}"

    try:
        items = response["items"]
        results = "\n".join([f"[{item['title']}] {item['snippet']} - from: {item['link']}" for item in items[:max_results]])
    except:
        return f"[Google] 未找到关于'{keyword}'的信息"

    _last_keyword = keyword
    _last_call_time = time.time()

    return f"[Google Search Results]\n{results}\nAnalyze and synthesize the above search results to provide insights. DO NOT directly repeat the search results - integrate them into a thoughtful response."
