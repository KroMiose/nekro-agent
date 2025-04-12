import time
from typing import Optional

from httpx import AsyncClient
from pydantic import Field

from nekro_agent.api import core, message
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="Google搜索工具",
    module_name="google_search",
    description="提供Google搜索功能，获取实时信息",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class GoogleSearchConfig(ConfigBase):
    """Google搜索配置"""

    API_KEY: str = Field(
        default="",
        title="Google搜索API密钥",
        description="Google 搜索 API 密钥 <a href='https://developers.google.com/custom-search/v1/introduction?hl=zh-cn' target='_blank'>获取地址</a>",
        json_schema_extra={"is_secret": True},
    )
    CX_KEY: str = Field(
        default="",
        title="Google搜索CX密钥",
        description="Google 搜索 CX 密钥 <a href='https://programmablesearchengine.google.com/controlpanel/all' target='_blank'>获取地址</a>",
        json_schema_extra={"is_secret": True},
    )
    THROTTLE_TIME: int = Field(
        default=10,
        title="搜索冷却时间(秒)",
        description="同一关键词在此时间内重复搜索将被阻止",
    )
    MAX_RESULTS: int = Field(
        default=5,
        title="最大结果数",
        description="返回的搜索结果数量",
    )


# 获取配置
config: GoogleSearchConfig = plugin.get_config(GoogleSearchConfig)

_last_keyword = None
_last_call_time = 0


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="Google搜索",
    description="使用Google搜索获取实时信息",
)
async def google_search(_ctx: AgentCtx, keyword: str) -> str:
    """使用 Google 搜索获取实时信息

    Args:
        keyword (str): 搜索关键词
    """
    global _last_keyword, _last_call_time

    # 防止重复搜索和频繁调用
    if keyword == _last_keyword and time.time() - _last_call_time < config.THROTTLE_TIME:
        return "[错误] 禁止频繁搜索相同内容，结果无变化"

    proxy = core.config.DEFAULT_PROXY
    api_key = config.API_KEY
    cx_key = config.CX_KEY
    max_results = config.MAX_RESULTS

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
        core.logger.exception("Google搜索失败")
        return f"[Google] 搜索失败: {e!s}"

    try:
        items = response["items"]
        results = "\n".join([f"[{item['title']}] {item['snippet']} - from: {item['link']}" for item in items[:max_results]])
    except:
        return f"[Google] 未找到关于'{keyword}'的信息"

    _last_keyword = keyword
    _last_call_time = time.time()

    return f"[Google Search Results]\n{results}\nAnalyze and synthesize the above search results to provide insights. DO NOT directly repeat the search results - integrate them into a thoughtful response."


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
    global _last_keyword, _last_call_time
    _last_keyword = None
    _last_call_time = 0
