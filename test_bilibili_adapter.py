#!/usr/bin/env python3
"""测试Bilibili直播适配器"""

import asyncio
import json
from nekro_agent.adapters.bilibili_live.core.client import Danmaku


async def test_danmaku_parsing():
    """测试弹幕数据解析"""
    test_data = {
        "from_live_room": 12345678,
        "uid": "user123",
        "username": "测试用户",
        "text": "这是一条测试弹幕",
        "time": 1672531200,
        "url": "",
        "is_trigget": True,
        "is_system": False
    }
    
    try:
        danmaku = Danmaku.model_validate(test_data)
        print(f"弹幕解析成功: {danmaku}")
        return True
    except Exception as e:
        print(f"弹幕解析失败: {e}")
        return False


async def test_websocket_client():
    """测试WebSocket客户端(模拟)"""
    async def mock_handler(danmaku: Danmaku):
        print(f"接收到弹幕: [{danmaku.from_live_room}] {danmaku.username}: {danmaku.text}")
    
    # 这里只是演示客户端创建，不进行实际连接
    from nekro_agent.adapters.bilibili_live.core.client import BilibiliWebSocketClient
    
    client = BilibiliWebSocketClient("ws://localhost:8080", mock_handler)
    print(f"WebSocket客户端创建成功: {client.ws_url}")
    
    return True


async def main():
    """主测试函数"""
    print("=== Bilibili直播适配器测试 ===")
    
    # 测试弹幕解析
    print("\n1. 测试弹幕数据解析...")
    result1 = await test_danmaku_parsing()
    
    # 测试WebSocket客户端
    print("\n2. 测试WebSocket客户端创建...")
    result2 = await test_websocket_client()
    
    # 输出结果
    print(f"\n=== 测试结果 ===")
    print(f"弹幕解析: {'✓' if result1 else '✗'}")
    print(f"WebSocket客户端: {'✓' if result2 else '✗'}")
    
    if result1 and result2:
        print("\n所有测试通过！Bilibili直播适配器基础功能正常。")
    else:
        print("\n部分测试失败，请检查实现。")


if __name__ == "__main__":
    asyncio.run(main())
