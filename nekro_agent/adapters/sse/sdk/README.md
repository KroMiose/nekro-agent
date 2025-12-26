# NekroAgent SSE SDK

[![PyPI version](https://badge.fury.io/py/nekro-agent-sse-sdk.svg)](https://badge.fury.io/py/nekro-agent-sse-sdk)
[![Python Version](https://img.shields.io/pypi/pyversions/nekro-agent-sse-sdk.svg)](https://pypi.org/project/nekro-agent-sse-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SSE (Server-Sent Events) 客户端SDK，用于与 [NekroAgent](https://github.com/KroMiose/nekro-agent) SSE适配器进行通信。

## 特性

- 🚀 基于标准HTTP协议的实时通信
- 📦 完整的类型注解支持
- 🔄 自动重连机制
- 📨 支持文本、图片、文件等多种消息类型
- 🔧 灵活的事件处理框架
- 📡 支持大文件分块传输

## 安装

```bash
pip install nekro-agent-sse-sdk
```

或使用 uv：

```bash
uv add nekro-agent-sse-sdk
```

## 快速开始

### 基础示例

```python
import asyncio
from nekro_agent_sse_sdk import SSEClient, text

class MyClient(SSEClient):
    async def _handle_send_message(self, event_type: str, data):
        """处理发送消息请求"""
        print(f"收到消息发送请求: {data.channel_id}")
        print(f"频道名称: {data.channel_name}")
        print(f"消息内容: {data.segments}")
        
        # 实现你的消息发送逻辑
        # ...
        
        return {"message_id": "msg_123", "success": True}

async def main():
    client = MyClient(
        server_url="http://localhost:8080",
        platform="my_platform",
        client_name="my_client",
        client_version="1.0.0",
    )
    
    await client.start()
    
    # 发送消息到频道
    await client.send_message(
        channel_id="group_123",
        segments=[text("Hello, World!")]
    )
    
    # 保持运行
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

### 消息类型

SDK支持多种消息段类型：

```python
from nekro_agent_sse_sdk import text, image, file, at

# 文本消息
text_seg = text("Hello!")

# 图片消息（支持URL或base64）
image_seg = image(url="https://example.com/image.jpg")
image_seg = image(file_path="/path/to/image.jpg")

# 文件消息
file_seg = file(file_path="/path/to/file.pdf")

# @消息
at_seg = at(user_id="user123", nickname="张三")
```

### 频道订阅

```python
# 订阅频道
await client.subscribe_channels(["group_123", "group_456"])

# 取消订阅
await client.unsubscribe_channels(["group_123"])
```

### 获取信息

```python
# 获取用户信息
user_info = await client.get_user_info("user123")

# 获取频道信息
channel_info = await client.get_channel_info("group_123")

# 获取机器人自身信息
self_info = await client.get_self_info()
```

## 高级用法

### 自定义事件处理

继承 `SSEClient` 并重写事件处理方法：

```python
class MyClient(SSEClient):
    async def _handle_send_message(self, event_type: str, data):
        """处理发送消息请求"""
        # 自定义消息发送逻辑
        pass
    
    async def _handle_get_user_info(self, event_type: str, data):
        """处理获取用户信息请求"""
        # 返回用户信息
        return UserInfo(
            user_id=data.user_id,
            user_name="用户名",
            platform_name=self.platform
        )
    
    async def _handle_get_channel_info(self, event_type: str, data):
        """处理获取频道信息请求"""
        # 返回频道信息
        return ChannelInfo(
            channel_id=data.channel_id,
            channel_name="频道名称"
        )
```

### 自动重连配置

```python
client = MyClient(
    server_url="http://localhost:8080",
    platform="my_platform",
    client_name="my_client",
    client_version="1.0.0",
    auto_reconnect=True,        # 启用自动重连
    reconnect_interval=5,       # 重连间隔（秒）
)
```

### 访问密钥认证

```python
client = MyClient(
    server_url="http://localhost:8080",
    platform="my_platform",
    client_name="my_client",
    client_version="1.0.0",
    access_key="your_secret_key",  # 设置访问密钥
)
```

## API文档

### SSEClient

主要方法：

- `start()`: 启动客户端并连接到服务器
- `stop()`: 停止客户端
- `send_message(channel_id, segments)`: 发送消息
- `subscribe_channels(channel_ids)`: 订阅频道
- `unsubscribe_channels(channel_ids)`: 取消订阅频道
- `get_user_info(user_id)`: 获取用户信息
- `get_channel_info(channel_id)`: 获取频道信息
- `get_self_info()`: 获取机器人自身信息

### 消息模型

- `TextSegment`: 文本消息段
- `ImageSegment`: 图片消息段
- `FileSegment`: 文件消息段
- `AtSegment`: @消息段

### 辅助函数

- `text(content)`: 创建文本消息段
- `image(url=None, file_path=None, ...)`: 创建图片消息段
- `file(url=None, file_path=None, ...)`: 创建文件消息段
- `at(user_id, nickname=None)`: 创建@消息段

## 开发

### 从源码安装

```bash
git clone https://github.com/KroMiose/nekro-agent.git
cd nekro-agent/nekro_agent/adapters/sse/sdk
uv pip install -e .
```

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 相关链接

- [NekroAgent 主项目](https://github.com/KroMiose/nekro-agent)
- [问题反馈](https://github.com/KroMiose/nekro-agent/issues)
- [贡献指南](https://github.com/KroMiose/nekro-agent/blob/main/CONTRIBUTING.md)

## 更新日志

### 1.0.0 (2024-12-26)

- ✨ 首次发布
- 📦 支持基础的SSE通信功能
- 🔄 支持自动重连
- 📨 支持多种消息类型
- 📡 支持大文件分块传输
- 🎯 添加频道名称字段支持

