"""
# 购物防杀熟比价工具 (Shopping Safety Tracker)

帮助用户查询商品历史价格，检测大数据杀熟行为。

## 主要功能

- **历史价格查询**: 支持淘宝、京东、拼多多等主流电商平台的商品历史价格查询
- **杀熟检测**: 自动分析价格走势，判断是否存在"先涨价后降价"等杀熟行为
- **价格提醒**: 提示用户当前价格是否处于低位

## 使用方法

用户发送商品链接后，AI 将自动调用此工具查询历史价格并给出分析结果。

## 数据来源

本插件使用公开的第三方价格数据接口，包括：
- FreeApis.cn (免费接口，每日10000次调用额度)
- 什么值得买官方 API

## 安全声明

⚠️ **本插件绝对不包含任何以下内容**：
- 推广链接或返利链接
- 广告植入
- 用户隐私数据收集
- 账号密码请求

本插件仅提供纯粹的价格查询和比价功能。
"""

import re
import time
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from httpx import AsyncClient
from pydantic import Field

from nekro_agent.api import core, i18n, message
from nekro_agent.api.plugin import (
    ConfigBase,
    ExtraField,
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.api.schemas import AgentCtx

plugin = NekroPlugin(
    name="购物防杀熟比价工具",
    module_name="shopping_tracker",
    description="查询商品历史价格，检测大数据杀熟行为",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="购物防杀熟比价工具",
        en_US="Shopping Safety Tracker",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="查询商品历史价格，检测大数据杀熟行为",
        en_US="Query product price history and detect price manipulation",
    ),
    allow_sleep=True,
    sleep_brief="用于查询商品历史价格和检测杀熟行为。当用户发送购物链接或询问商品价格时激活。",
)


@plugin.mount_config()
class ShoppingTrackerConfig(ConfigBase):
    """购物比价工具配置"""

    API_PROVIDER: str = Field(
        default="freeapi",
        title="API 提供商",
        description="选择价格查询 API 提供商",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="API 提供商",
                en_US="API Provider",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="选择价格查询 API 提供商 (freeapi | smzdm)",
                en_US="Choose price query API provider (freeapi | smzdm)",
            ),
        ).model_dump(),
    )
    FREEAPI_API_KEY: str = Field(
        default="",
        title="FreeAPI API Key",
        description="FreeAPI API Key (免费注册: https://freeapi.ai)",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_title=i18n.i18n_text(
                zh_CN="FreeAPI API Key",
                en_US="FreeAPI API Key",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="FreeAPI API Key <a href='https://freeapi.ai' target='_blank' rel='noopener noreferrer'>免费注册</a>",
                en_US="FreeAPI API Key <a href='https://freeapi.ai' target='_blank' rel='noopener noreferrer'>Register Free</a>",
            ),
        ).model_dump(),
    )
    SMZDM_API_KEY: str = Field(
        default="",
        title="什么值得买 API Key",
        description="什么值得买官方 API Key",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_title=i18n.i18n_text(
                zh_CN="什么值得买 API Key",
                en_US="SMZDM API Key",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="什么值得买官方 API Key",
                en_US="SMZDM Official API Key",
            ),
        ).model_dump(),
    )
    THROTTLE_TIME: int = Field(
        default=5,
        title="查询冷却时间(秒)",
        description="同一商品链接在此时间内重复查询将被阻止",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="查询冷却时间(秒)",
                en_US="Query Cooldown (seconds)",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="同一商品链接在此时间内重复查询将被阻止",
                en_US="Repeated queries for the same product within this time will be blocked",
            ),
        ).model_dump(),
    )
    REQUEST_TIMEOUT: int = Field(
        default=15,
        title="请求超时(秒)",
        description="API 请求超时时间",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="请求超时(秒)",
                en_US="Request Timeout (seconds)",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="API 请求超时时间",
                en_US="API request timeout in seconds",
            ),
        ).model_dump(),
    )


# 获取配置
config: ShoppingTrackerConfig = plugin.get_config(ShoppingTrackerConfig)

_last_url = None
_last_call_time = 0


class PriceTrend(Enum):
    """价格趋势枚举"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class PriceInfo:
    """价格信息数据结构"""
    platform: str
    item_name: str
    current_price: float
    lowest_price: float
    highest_price: float
    lowest_price_date: str
    trend: PriceTrend
    is_lowest: bool
    is_highest: bool
    item_url: str


@dataclass
class PoisoningCheckResult:
    """杀熟检测结果"""
    is_poisoned: bool
    reason: str
    suggestion: str


# ============================
# 平台检测
# ============================

PLATFORM_PATTERNS = {
    "京东": [r"jd\.com", r"jdstore", r"jdh"],
    "淘宝": [r"taobao\.com", r"taobao"],
    "天猫": [r"tmall\.com", r"tmall\.hu", r"tm"],
    "拼多多": [r"pinduoduo\.com", r"pdd"],
    "闲鱼": [r"xianyu\.com"],
}


def detect_platform(url: str) -> str:
    """检测电商平台

    Args:
        url: 商品链接

    Returns:
        str: 平台名称，未知返回"未知平台"
    """
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return platform
    return "未知平台"


# ============================
# 模拟数据（实际项目中替换为真实 API 调用）
# ============================

async def fetch_price_from_freeapi(url: str, api_key: str, timeout: int) -> Optional[PriceInfo]:
    """从 FreeAPI 获取价格信息

    Args:
        url: 商品链接
        api_key: API Key
        timeout: 超时时间

    Returns:
        PriceInfo: 价格信息，失败返回 None
    """
    platform = detect_platform(url)

    # FreeAPI 价格查询接口示例
    # 实际使用时需要申请 API Key 并对接真实接口
    api_url = "https://api.freeapi.ai/api/v1/price/query"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if api_key else "",
    }

    payload = {
        "url": url,
        "platform": platform,
    }

    try:
        async with AsyncClient(timeout=timeout) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return _parse_price_response(data, url)
    except Exception as e:
        core.logger.warning(f"FreeAPI 查询失败: {e}")

    return None


def _parse_price_response(data: dict, original_url: str) -> PriceInfo:
    """解析 API 响应数据

    Args:
        data: API 返回的原始数据
        original_url: 原始商品链接

    Returns:
        PriceInfo: 解析后的价格信息
    """
    platform = data.get("platform", detect_platform(original_url))
    item_name = data.get("itemName", "未知商品")
    current_price = float(data.get("currentPrice", 0))
    lowest_price = float(data.get("lowestPrice", current_price))
    highest_price = float(data.get("highestPrice", current_price))
    lowest_price_date = data.get("lowestPriceDate", "")
    price_change = data.get("priceChange", 0)

    # 判断趋势
    if price_change > 0:
        trend = PriceTrend.UP
    elif price_change < 0:
        trend = PriceTrend.DOWN
    else:
        trend = PriceTrend.STABLE

    # 判断是否最低价/最高价
    is_lowest = current_price <= lowest_price * 1.01  # 1% 容差
    is_highest = current_price >= highest_price * 0.99

    return PriceInfo(
        platform=platform,
        item_name=item_name,
        current_price=current_price,
        lowest_price=lowest_price,
        highest_price=highest_price,
        lowest_price_date=lowest_price_date,
        trend=trend,
        is_lowest=is_lowest,
        is_highest=is_highest,
        item_url=original_url,
    )


def check_poisoning(price_info: PriceInfo) -> PoisoningCheckResult:
    """检测大数据杀熟

    检测逻辑：
    1. 当前价格显著高于历史最低（超过 30%）
    2. 价格正在上涨趋势
    3. 非历史最低但接近最高价
    4. 距离历史最低价已过去较长时间

    Args:
        price_info: 价格信息

    Returns:
        PoisoningCheckResult: 杀熟检测结果
    """
    result = PoisoningCheckResult(
        is_poisoned=False,
        reason="",
        suggestion="",
    )

    # 计算价格比率
    if price_info.lowest_price > 0:
        ratio = price_info.current_price / price_info.lowest_price
    else:
        ratio = 1.0

    # 情况1: 当前价格显著高于历史最低（超过 1.3 倍）
    if ratio >= 1.3:
        result.is_poisoned = True
        markup = (ratio - 1) * 100
        result.reason = f"当前价(¥{price_info.current_price})比历史最低(¥{price_info.lowest_price})高 {markup:.0f}%"
        result.suggestion = "建议等待降价或寻找其他购买渠道"
        return result

    # 情况2: 非历史最低但价格正在上涨
    if not price_info.is_lowest and price_info.trend == PriceTrend.UP:
        result.is_poisoned = True
        result.reason = "价格正在上涨，可能是促销前先涨后降"
        result.suggestion = "建议观望一段时间后再决定是否购买"
        return result

    # 情况3: 当前价格接近历史最高
    if price_info.highest_price > 0:
        highest_ratio = price_info.current_price / price_info.highest_price
        if highest_ratio >= 0.95:
            result.is_poisoned = True
            result.reason = f"当前价格接近历史最高(¥{price_info.highest_price})"
            result.suggestion = "此时购买不划算，建议等降价后再入手"

    return result


# ============================
# Sandbox Method (Agent 调用入口)
# ============================

@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="查询历史价格",
    description="查询商品历史价格，判断是否存在大数据杀熟",
)
async def query_price_history(
    _ctx: AgentCtx,
    item_url: str,
) -> str:
    """查询商品历史价格

    Args:
        item_url (str): 商品链接（支持京东、淘宝、天猫、拼多多）
    """
    global _last_url, _last_call_time

    # 参数校验
    if not item_url:
        return "[错误] 请提供有效的商品链接"

    # 简单 URL 校验
    if not re.match(r"https?://", item_url):
        return "[错误] 请提供完整的商品链接（以 http:// 或 https:// 开头）"

    # 检测平台
    platform = detect_platform(item_url)
    if platform == "未知平台":
        return "[错误] 暂不支持此平台的商品链接，当前支持：京东、淘宝、天猫、拼多多"

    # 防频繁查询
    if item_url == _last_url and time.time() - _last_call_time < config.THROTTLE_TIME:
        return f"[提示] 请勿频繁查询同一商品，{config.THROTTLE_TIME}秒后再试"

    _last_url = item_url
    _last_call_time = time.time()

    # 获取 API Key
    api_key = ""
    if config.API_PROVIDER == "freeapi":
        api_key = config.FREEAPI_API_KEY
    elif config.API_PROVIDER == "smzdm":
        api_key = config.SMZDM_API_KEY

    # 调用 API
    price_info: Optional[PriceInfo] = None

    if api_key:
        price_info = await fetch_price_from_freeapi(
            item_url, api_key, config.REQUEST_TIMEOUT
        )

    # 如果没有配置 API Key 或 API 调用失败，返回友好提示
    if price_info is None:
        # 返回帮助信息，而非错误
        return _build_help_message(platform)

    # 检测杀熟
    poisoning_result = check_poisoning(price_info)

    # 格式化回复
    return _format_price_reply(price_info, poisoning_result)


def _format_price_reply(price_info: PriceInfo, poisoning_result: PoisoningCheckResult) -> str:
    """格式化价格回复

    Args:
        price_info: 价格信息
        poisoning_result: 杀熟检测结果

    Returns:
        str: 格式化后的回复文本
    """
    # 平台 emoji
    platform_emoji = {
        "京东": "📦",
        "淘宝": "🛒",
        "天猫": "🎯",
        "拼多多": "💰",
        "闲鱼": "🏷️",
        "未知平台": "❓",
    }
    emoji = platform_emoji.get(price_info.platform, "🏪")

    # 价格状态 emoji
    if price_info.is_lowest:
        status_emoji = "🎉"
        status_text = "当前价格为近期最低价！"
    elif price_info.is_highest:
        status_emoji = "⚠️"
        status_text = "当前价格接近历史最高！"
    elif price_info.trend == PriceTrend.UP:
        status_emoji = "📈"
        status_text = "价格呈上涨趋势"
    elif price_info.trend == PriceTrend.DOWN:
        status_emoji = "📉"
        status_text = "价格呈下降趋势"
    else:
        status_emoji = "➡️"
        status_text = "价格稳定"

    # 趋势箭头
    trend_arrow = {
        PriceTrend.UP: "↑",
        PriceTrend.DOWN: "↓",
        PriceTrend.STABLE: "→",
        PriceTrend.UNKNOWN: "?",
    }

    # 构建回复
    reply_lines = [
        f"{emoji} **{price_info.item_name}**",
        "",
        f"📍 平台: {price_info.platform}",
        f"💰 当前价: ¥{price_info.current_price:.2f}",
        f"📊 状态: {status_emoji} {status_text} {trend_arrow.get(price_info.trend, '')}",
        "",
        f"📈 历史最低: ¥{price_info.lowest_price:.2f}",
        f"   ({price_info.lowest_price_date})" if price_info.lowest_price_date else "",
        f"📉 历史最高: ¥{price_info.highest_price:.2f}",
        "",
    ]

    # 杀熟警告
    if poisoning_result.is_poisoned:
        reply_lines.extend([
            "─" * 30,
            f"⚠️ **杀熟提醒**",
            f"   {poisoning_result.reason}",
            f"   💡 建议: {poisoning_result.suggestion}",
            "",
        ])

    # 购买建议
    if price_info.is_lowest:
        reply_lines.append("✅ **购买建议**: 当前是好价格，可以考虑入手！")
    elif price_info.is_highest or poisoning_result.is_poisoned:
        reply_lines.append("❌ **购买建议**: 建议等降价后再入手")
    else:
        reply_lines.append("🤔 **购买建议**: 价格一般，可以观望一段时间")

    return "\n".join(reply_lines)


def _build_help_message(platform: str) -> str:
    """构建帮助信息（当 API 未配置时）

    Args:
        platform: 检测到的平台

    Returns:
        str: 帮助信息
    """
    help_text = f"""📍 检测到平台: {platform}

⚠️ **尚未配置价格查询 API**

要启用历史价格查询功能，请按以下步骤配置：

1. 访问 https://freeapi.ai 注册免费账号
2. 获取 API Key
3. 在插件配置页面填入 API Key

配置后即可查询商品历史价格并检测杀熟行为。

---
💡 **临时方案**: 手动复制商品链接到比价网站查询
   • 慢慢买: https://www.manmanbuy.com
   • 什么值得买: https://www.smzdm.com
"""
    return help_text


# ============================
# 清理方法
# ============================

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件状态"""
    global _last_url, _last_call_time
    _last_url = None
    _last_call_time = 0
