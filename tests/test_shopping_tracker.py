"""
测试模块: Shopping Tracker 插件单元测试

测试内容:
1. 平台检测
2. 杀熟检测逻辑
3. 价格信息解析
4. 格式化回复

运行方式:
    pytest tests/test_shopping_tracker.py -v
"""

import pytest
from plugins.builtin.shopping_tracker import (
    detect_platform,
    check_poisoning,
    PriceInfo,
    PriceTrend,
    PoisoningCheckResult,
    _format_price_reply,
)


class TestPlatformDetection:
    """测试平台检测功能"""

    def test_detect_jd(self):
        """测试京东平台检测"""
        urls = [
            "https://item.jd.com/100012043.html",
            "https://www.jd.com/product/123.html",
            "https://item.jdstore.com/sku/456",
        ]
        for url in urls:
            assert detect_platform(url) == "京东", f"Failed for: {url}"

    def test_detect_taobao(self):
        """测试淘宝平台检测"""
        urls = [
            "https://item.taobao.com/item.htm?id=1234567890",
            "https://taobao.com/item/123.html",
        ]
        for url in urls:
            assert detect_platform(url) == "淘宝", f"Failed for: {url}"

    def test_detect_tmall(self):
        """测试天猫平台检测"""
        urls = [
            "https://detail.tmall.com/item.htm?id=123456",
            "https://www.tmall.com/item/123.html",
        ]
        for url in urls:
            assert detect_platform(url) == "天猫", f"Failed for: {url}"

    def test_detect_pinduoduo(self):
        """测试拼多多平台检测"""
        urls = [
            "https://pinduoduo.com/goods.html?goods_id=123",
            "https://youpin.pinduoduo.com/detail/456",
        ]
        for url in urls:
            assert detect_platform(url) == "拼多多", f"Failed for: {url}"

    def test_detect_unknown(self):
        """测试未知平台"""
        urls = [
            "https://example.com/product/123",
            "not-a-url",
            "",
        ]
        for url in urls:
            assert detect_platform(url) == "未知平台", f"Failed for: {url}"


class TestPoisoningDetection:
    """测试杀熟检测逻辑"""

    def test_not_poisoned_lowest_price(self):
        """测试价格处于最低位 - 不杀熟"""
        price_info = PriceInfo(
            platform="京东",
            item_name="测试商品",
            current_price=99.0,
            lowest_price=99.0,
            highest_price=299.0,
            lowest_price_date="2026-03-15",
            trend=PriceTrend.STABLE,
            is_lowest=True,
            is_highest=False,
            item_url="https://item.jd.com/123.html",
        )

        result = check_poisoning(price_info)

        assert result.is_poisoned is False
        assert result.reason == ""
        assert result.suggestion == ""

    def test_poisoned_high_markup(self):
        """测试价格显著高于最低 - 杀熟"""
        price_info = PriceInfo(
            platform="京东",
            item_name="测试商品",
            current_price=299.0,  # 最低 99，当前是最低的 3 倍
            lowest_price=99.0,
            highest_price=299.0,
            lowest_price_date="2026-03-15",
            trend=PriceTrend.STABLE,
            is_lowest=False,
            is_highest=True,
            item_url="https://item.jd.com/123.html",
        )

        result = check_poisoning(price_info)

        assert result.is_poisoned is True
        assert "比历史最低高" in result.reason
        assert "¥299.0" in result.reason
        assert "¥99.0" in result.reason

    def test_poisoned_rising_trend(self):
        """测试价格上涨趋势 - 杀熟"""
        price_info = PriceInfo(
            platform="淘宝",
            item_name="测试商品",
            current_price=150.0,
            lowest_price=99.0,
            highest_price=199.0,
            lowest_price_date="2026-03-10",
            trend=PriceTrend.UP,  # 正在涨价
            is_lowest=False,
            is_highest=False,
            item_url="https://item.taobao.com/item.htm?id=123",
        )

        result = check_poisoning(price_info)

        assert result.is_poisoned is True
        assert "上涨" in result.reason

    def test_poisoned_near_highest(self):
        """测试价格接近历史最高 - 杀熟"""
        price_info = PriceInfo(
            platform="天猫",
            item_name="测试商品",
            current_price=195.0,  # 最高 199，当前是最高的 98%
            lowest_price=99.0,
            highest_price=199.0,
            lowest_price_date="2026-03-01",
            trend=PriceTrend.STABLE,
            is_lowest=False,
            is_highest=False,
            item_url="https://detail.tmall.com/item.htm?id=123",
        )

        result = check_poisoning(price_info)

        assert result.is_poisoned is True
        assert "接近历史最高" in result.reason

    def test_normal_price(self):
        """测试正常价格 - 不杀熟"""
        price_info = PriceInfo(
            platform="拼多多",
            item_name="测试商品",
            current_price=120.0,  # 中间价位
            lowest_price=99.0,
            highest_price=199.0,
            lowest_price_date="2026-03-15",
            trend=PriceTrend.DOWN,  # 正在降价
            is_lowest=False,
            is_highest=False,
            item_url="https://pinduoduo.com/goods.html?goods_id=123",
        )

        result = check_poisoning(price_info)

        assert result.is_poisoned is False


class TestPriceInfoFormatting:
    """测试价格信息格式化"""

    def test_format_lowest_price(self):
        """测试最低价格式化"""
        price_info = PriceInfo(
            platform="京东",
            item_name="iPhone 15 Pro",
            current_price=7999.0,
            lowest_price=7999.0,
            highest_price=9999.0,
            lowest_price_date="2026-03-15",
            trend=PriceTrend.STABLE,
            is_lowest=True,
            is_highest=False,
            item_url="https://item.jd.com/123.html",
        )
        poisoning = PoisoningCheckResult(
            is_poisoned=False,
            reason="",
            suggestion="",
        )

        reply = _format_price_reply(price_info, poisoning)

        assert "iPhone 15 Pro" in reply
        assert "¥7999.00" in reply
        assert "🎉" in reply or "最低价" in reply
        assert "✅" in reply and "入手" in reply

    def test_format_high_price(self):
        """测试高价格式化"""
        price_info = PriceInfo(
            platform="天猫",
            item_name="戴森吹风机",
            current_price=3499.0,
            lowest_price=1999.0,
            highest_price=3499.0,
            lowest_price_date="2026-02-01",
            trend=PriceTrend.UP,
            is_lowest=False,
            is_highest=True,
            item_url="https://detail.tmall.com/item.htm?id=456",
        )
        poisoning = PoisoningCheckResult(
            is_poisoned=True,
            reason="当前价格接近历史最高",
            suggestion="建议等降价后再入手",
        )

        reply = _format_price_reply(price_info, poisoning)

        assert "戴森吹风机" in reply
        assert "⚠️" in reply
        assert "杀熟" in reply or "⚠️" in reply
        assert "❌" in reply and "入手" in reply


class TestURLValidation:
    """测试 URL 验证逻辑（集成测试）"""

    def test_valid_urls(self):
        """测试有效 URL"""
        valid_urls = [
            "https://item.jd.com/100012043.html",
            "https://item.taobao.com/item.htm?id=1234567890",
            "https://detail.tmall.com/item.htm?id=123",
            "http://pinduoduo.com/goods.html?goods_id=123",
        ]
        for url in valid_urls:
            platform = detect_platform(url)
            assert platform != "未知平台", f"Should detect: {url}"

    def test_invalid_urls(self):
        """测试无效 URL"""
        invalid_urls = [
            "not-a-url",
            "",
            "just some text",
            "ftp://example.com",
        ]
        for url in invalid_urls:
            # 传入无效 URL 应该返回"未知平台"
            platform = detect_platform(url)
            assert platform == "未知平台", f"Should be unknown: {url}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
