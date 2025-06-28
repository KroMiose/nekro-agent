"""
# 谷歌搜索 (Google Search)

赋予 AI 连接现实世界、获取实时信息的能力。

## 主要功能

- **网页搜索**: AI 可以通过调用 Google Custom Search API，输入关键词来搜索互联网上的信息。
- **获取新知**: 当遇到自身知识库无法回答的问题（例如今天的天气、最新的新闻事件、某个冷门知识等）时，AI 可以利用此插件来查找答案。

## 使用方法

此插件主要由 AI 在后台根据需要自动调用。当 AI 判断自己的知识不足以回答当前问题时，它会自动使用此工具进行搜索，然后整理搜索结果并回复用户。

## 配置说明

要使用此插件，您必须拥有一个 Google 账号，并按照插件配置页面中的链接指引，申请自己的 `API Key` 和 `CX Key`。这是一个免费但有一定配额限制的服务。
"""

import time
from typing import Optional

from httpx import AsyncClient
from pydantic import Field

from nekro_agent.api import core, message
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx

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
