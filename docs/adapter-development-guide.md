# NekroAgent 适配器开发指南

本文档详细说明 NekroAgent 的适配器（Adapter）系统架构，以及如何从零开发一个新的平台适配器。

---

## 目录

- [架构概述](#架构概述)
- [核心概念](#核心概念)
- [数据流](#数据流)
- [目录结构](#目录结构)
- [从零开发适配器（分步教程）](#从零开发适配器分步教程)
  - [第 1 步：创建目录结构](#第-1-步创建目录结构)
  - [第 2 步：定义配置类](#第-2-步定义配置类)
  - [第 3 步：实现适配器主类](#第-3-步实现适配器主类)
  - [第 4 步：实现消息接收](#第-4-步实现消息接收)
  - [第 5 步：注册适配器](#第-5-步注册适配器)
  - [第 6 步：前端集成](#第-6-步前端集成)
  - [第 7 步：编写 README 文档](#第-7-步编写-readme-文档)
- [可选功能](#可选功能)
- [现有适配器参考](#现有适配器参考)
- [常见问题](#常见问题)

---

## 架构概述

NekroAgent 适配器系统采用**模板方法 + 适配器模式**设计，将不同平台（QQ、Discord、Telegram、微信等）的通信差异抽象为统一接口。所有适配器继承 `BaseAdapter` 基类，实现标准化的消息收发流程。

```
┌──────────────────────────────────────────────────┐
│                   NekroAgent 核心                 │
│  ┌────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ 消息服务    │  │  AI 代理     │  │  插件系统  │  │
│  └──────┬─────┘  └──────┬──────┘  └─────┬─────┘  │
│         └───────────────┼───────────────┘         │
│                         │                         │
│              ┌──────────┴──────────┐              │
│              │  BaseAdapter 接口   │              │
│              └──────────┬──────────┘              │
├──────────────────────── │ ────────────────────────┤
│              ┌──────────┴──────────┐              │
│    ┌─────────┤   适配器注册表      ├─────────┐    │
│    │         └─────────────────────┘         │    │
│    ▼              ▼            ▼             ▼    │
│ ┌──────┐   ┌──────────┐  ┌─────────┐  ┌───────┐ │
│ │OneBot│   │ Discord  │  │Telegram │  │  ...  │ │
│ │ V11  │   │ Adapter  │  │ Adapter │  │       │ │
│ └──┬───┘   └────┬─────┘  └────┬────┘  └───┬───┘ │
└──── │ ────────── │ ──────────  │ ────────── │ ───┘
      ▼            ▼             ▼            ▼
   QQ 平台     Discord 平台   Telegram     其他平台
```

**关键设计原则：**

1. **统一接口**：所有适配器实现相同的抽象方法，核心系统无需关心底层平台差异
2. **动态加载**：通过 `importlib` + 注册表实现适配器的动态发现和加载
3. **独立配置**：每个适配器拥有独立的 YAML 配置文件，并自动注册到统一配置系统
4. **消息标准化**：平台原生消息在适配器内部转换为 `PlatformMessage`，发送时从 `PlatformSendRequest` 转换为平台格式
5. **生命周期管理**：`init()` / `cleanup()` 钩子与 FastAPI 应用生命周期绑定

---

## 核心概念

### BaseAdapter 基类

位置：`nekro_agent/adapters/interface/base.py`

所有适配器必须继承此类并实现以下抽象方法：

| 方法/属性 | 类型 | 说明 |
|---|---|---|
| `key` | `property (str)` | 适配器唯一标识，如 `"discord"`、`"telegram"` |
| `metadata` | `property (AdapterMetadata)` | 适配器元数据（名称、描述、版本、作者等） |
| `init()` | `async method` | 初始化逻辑（应用启动时调用） |
| `cleanup()` | `async method` | 清理逻辑（应用关闭时调用） |
| `forward_message(request)` | `async method` | 发送消息到平台 |
| `get_self_info()` | `async method` | 获取机器人自身信息 |
| `get_user_info(user_id, channel_id)` | `async method` | 获取指定用户信息 |
| `get_channel_info(channel_id)` | `async method` | 获取频道/群组信息 |

### 平台消息数据结构

位置：`nekro_agent/adapters/interface/schemas/platform.py`

**接收侧（平台 → NekroAgent）：**

```python
PlatformUser       # 平台用户：user_id, user_name, user_avatar, platform_name
PlatformChannel    # 平台频道：channel_id, channel_name, channel_type (GROUP/PRIVATE)
PlatformMessage    # 平台消息：message_id, sender_id, content_text, content_data, is_tome, ...
PlatformMessageExt # 扩展数据：ref_msg_id (引用消息), ref_sender_id, ref_chat_key
```

**发送侧（NekroAgent → 平台）：**

```python
PlatformSendRequest       # 发送请求：chat_key, segments[], ref_msg_id
PlatformSendSegment       # 消息段：type (TEXT/AT/IMAGE/FILE), content, at_info, file_path
PlatformSendResponse      # 发送响应：success, error_message, message_id
```

### chat_key 聊天标识

`chat_key` 是 NekroAgent 中标识一个聊天会话的唯一字符串，格式为：

```
{adapter_key}-{channel_id}
```

示例：
- `discord-1234567890` — Discord 频道
- `onebot_v11-group_123456` — QQ 群
- `telegram-group_-1002768666191` — Telegram 群组

`BaseAdapter` 提供 `build_chat_key()` 和 `parse_chat_key()` 辅助方法来构建和解析。

### 消息收集器

位置：`nekro_agent/adapters/interface/collector.py`

`collect_message()` 是适配器接收消息后的统一入口。它负责：

1. 在数据库中创建或获取 `DBChatChannel` 记录
2. 注册或获取 `DBUser` 记录
3. 检查频道/用户是否处于激活状态
4. 过滤自身发送的消息
5. 转换为内部 `ChatMessage` 格式
6. 推送到 `message_service` 进行后续 AI 处理

**适配器只需构造好 `PlatformUser`、`PlatformChannel`、`PlatformMessage` 三个对象，然后调用 `collect_message()` 即可完成消息接收。**

### AdapterMetadata 元数据

```python
class AdapterMetadata(BaseModel):
    name: str              # 适配器显示名称，如 "Discord"
    description: str       # 简短描述
    version: str = "1.0.0" # 版本号
    author: str = ""       # 作者
    homepage: str = ""     # 主页 URL
    tags: List[str] = []   # 标签，如 ["discord", "chat", "im"]
```

---

## 数据流

### 消息接收流程（平台 → AI）

```
平台事件（WebSocket / HTTP Callback / Polling）
    │
    ▼
适配器事件处理器（on_message / webhook handler 等）
    │
    ▼
构造 PlatformUser + PlatformChannel + PlatformMessage
    │
    ▼
调用 collect_message(adapter, channel, user, message)
    │
    ▼
数据库处理（创建频道/注册用户/检查状态）
    │
    ▼
message_service.push_human_message()
    │
    ▼
AI 代理处理 → 生成回复
```

### 消息发送流程（AI → 平台）

```
AI 代理生成回复
    │
    ▼
构建 PlatformSendRequest（消息段列表）
    │
    ▼
adapter.forward_message(request)
    │
    ▼
适配器内部转换（PlatformSendSegment → 平台原生格式）
    │
    ▼
调用平台 API 发送消息
    │
    ▼
返回 PlatformSendResponse（成功/失败 + 消息 ID）
```

---

## 目录结构

一个标准适配器的文件结构：

```
nekro_agent/adapters/
└── my_platform/              # 适配器目录，名称 = adapter key
    ├── __init__.py            # 空文件
    ├── adapter.py             # 适配器主类（必需）
    ├── config.py              # 配置类定义（必需）
    ├── client.py              # 平台客户端/连接管理（推荐）
    ├── tools.py               # 工具函数（如消息解析、@ 处理）
    ├── routers.py             # 自定义 API 路由（可选）
    └── README.md              # 适配器说明文档（必需）
```

对于复杂适配器，可以进一步划分子目录：

```
nekro_agent/adapters/
└── my_platform/
    ├── __init__.py
    ├── adapter.py
    ├── config.py
    ├── README.md
    ├── core/                  # 核心模块
    │   ├── client.py          # 平台连接管理
    │   └── bot.py             # 机器人实例
    ├── matchers/              # 事件处理器
    │   ├── message.py         # 消息事件
    │   └── notice.py          # 通知事件
    └── tools/                 # 工具函数
        ├── convertor.py       # 消息转换
        └── at_parser.py       # @ 解析
```

---

## 从零开发适配器（分步教程）

以一个假想的 "MyChat" 平台为例，演示完整的适配器开发流程。

### 第 1 步：创建目录结构

```
nekro_agent/adapters/mychat/
├── __init__.py     # 空文件
├── adapter.py      # 适配器主类
├── config.py       # 配置定义
├── client.py       # 平台客户端
└── README.md       # 使用说明
```

### 第 2 步：定义配置类

文件：`nekro_agent/adapters/mychat/config.py`

```python
from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig


class MyChatConfig(BaseAdapterConfig):
    """MyChat 适配器配置"""

    # 继承自 BaseAdapterConfig 的配置项：
    # - SESSION_ENABLE_AT: bool （是否启用 @ 功能）
    # - SESSION_PROCESSING_WITH_EMOJI: bool （是否显示处理中表情）

    API_TOKEN: str = Field(
        default="",
        title="API Token",
        description="从 MyChat 平台获取的 Bot API Token",
    )
    API_BASE_URL: str = Field(
        default="https://api.mychat.example.com",
        title="API 地址",
        description="MyChat API 服务地址",
    )
    WEBHOOK_SECRET: str = Field(
        default="",
        title="Webhook 密钥",
        description="用于验证回调请求的密钥",
    )
```

**配置文件运行时自动生成在：** `$DATA_DIR/configs/mychat/config.yaml`

`BaseAdapterConfig` 继承自 `ConfigBase`，已集成 YAML 序列化/反序列化和统一配置管理。你只需要定义字段即可。

### 第 3 步：实现适配器主类

文件：`nekro_agent/adapters/mychat/adapter.py`

```python
from typing import List, Optional, Type

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatType

from .client import MyChatClient
from .config import MyChatConfig

logger = get_sub_logger("adapter.mychat")


class MyChatAdapter(BaseAdapter[MyChatConfig]):
    """MyChat 平台适配器"""

    client: Optional[MyChatClient]

    def __init__(self, config_cls: Type[MyChatConfig] = MyChatConfig):
        super().__init__(config_cls)
        # 根据配置决定是否初始化客户端
        if not self.config.API_TOKEN:
            logger.warning("MyChat 未启用，需要设置 API_TOKEN")
            self.client = None
            return
        self.client = MyChatClient(
            token=self.config.API_TOKEN,
            base_url=self.config.API_BASE_URL,
            adapter=self,
        )

    # ============================
    # 必需属性
    # ============================

    @property
    def key(self) -> str:
        """适配器唯一标识"""
        return "mychat"

    @property
    def metadata(self) -> AdapterMetadata:
        """适配器元数据"""
        return AdapterMetadata(
            name="MyChat",
            description="MyChat 平台适配器，支持群聊和私聊消息交互",
            version="1.0.0",
            author="Your Name",
            homepage="https://github.com/your/repo",
            tags=["mychat", "chat", "im"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        """聊天标识规则说明（前端高级信息页面展示）"""
        return [
            "群聊: `mychat-group_123456`（其中 123456 为群组 ID）",
            "私聊: `mychat-private_123456`（其中 123456 为用户 ID）",
        ]

    # ============================
    # 生命周期方法
    # ============================

    async def init(self) -> None:
        """应用启动时调用，初始化客户端连接"""
        if self.client is not None:
            await self.client.start()
            logger.info("MyChat 适配器已启动")

    async def cleanup(self) -> None:
        """应用关闭时调用，断开连接释放资源"""
        if self.client is not None:
            await self.client.stop()
            logger.info("MyChat 适配器已关闭")

    # ============================
    # 消息发送
    # ============================

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """将 NekroAgent 的回复发送到 MyChat 平台

        此方法接收标准化的 PlatformSendRequest，需要将其转换为平台 API 格式并发送。
        """
        if self.client is None:
            return PlatformSendResponse(
                success=False,
                error_message="MyChat 客户端未初始化，请检查 API_TOKEN 配置",
            )

        try:
            # 1. 从 chat_key 解析出 channel_id
            _, channel_id = self.parse_chat_key(request.chat_key)

            # 2. 遍历消息段，转换为平台格式
            text_parts: list[str] = []
            file_paths: list[str] = []

            for segment in request.segments:
                if segment.type == PlatformSendSegmentType.TEXT:
                    text_parts.append(segment.content)
                elif segment.type == PlatformSendSegmentType.AT:
                    if segment.at_info:
                        text_parts.append(f"@{segment.at_info.nickname or segment.at_info.platform_user_id}")
                elif segment.type in (PlatformSendSegmentType.IMAGE, PlatformSendSegmentType.FILE):
                    if segment.file_path:
                        file_paths.append(segment.file_path)

            # 3. 调用平台 API 发送
            final_text = "".join(text_parts)
            msg_id = await self.client.send_message(
                channel_id=channel_id,
                text=final_text,
                files=file_paths,
                reply_to=request.ref_msg_id,
            )

            return PlatformSendResponse(success=True, message_id=msg_id)

        except Exception as e:
            logger.exception(f"发送消息到 MyChat 失败: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))

    # ============================
    # 信息查询
    # ============================

    async def get_self_info(self) -> PlatformUser:
        """获取机器人自身信息"""
        if self.client is None:
            raise RuntimeError("MyChat 客户端未初始化")
        bot_info = await self.client.get_bot_info()
        return PlatformUser(
            platform_name="mychat",
            user_id=bot_info["id"],
            user_name=bot_info["name"],
            user_avatar=bot_info.get("avatar", ""),
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取指定用户信息"""
        if self.client is None:
            raise RuntimeError("MyChat 客户端未初始化")
        user_info = await self.client.get_user(user_id)
        return PlatformUser(
            platform_name="mychat",
            user_id=user_info["id"],
            user_name=user_info["name"],
            user_avatar=user_info.get("avatar", ""),
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道/群组信息"""
        if self.client is None:
            raise RuntimeError("MyChat 客户端未初始化")
        ch_info = await self.client.get_channel(channel_id)
        return PlatformChannel(
            channel_id=ch_info["id"],
            channel_name=ch_info["name"],
            channel_type=ChatType.GROUP if ch_info["type"] == "group" else ChatType.PRIVATE,
        )
```

### 第 4 步：实现消息接收

文件：`nekro_agent/adapters/mychat/client.py`

这是适配器中最关键的部分——接收平台事件并转换为标准格式。以 WebSocket 长连接为例：

```python
import asyncio
from typing import TYPE_CHECKING

from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.extra import PlatformMessageExt
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)

logger = get_sub_logger("adapter.mychat")

if TYPE_CHECKING:
    from .adapter import MyChatAdapter


class MyChatClient:
    """MyChat 平台客户端，负责与平台通信"""

    def __init__(self, token: str, base_url: str, adapter: "MyChatAdapter"):
        self._token = token
        self._base_url = base_url
        self._adapter = adapter
        self._ws = None
        self._task: asyncio.Task | None = None

    async def start(self):
        """启动客户端连接"""
        self._task = asyncio.create_task(self._listen())

    async def stop(self):
        """停止客户端连接"""
        if self._task:
            self._task.cancel()
        if self._ws:
            await self._ws.close()

    async def _listen(self):
        """监听平台事件（示例：WebSocket 长连接）"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"{self._base_url}/ws",
                headers={"Authorization": f"Bearer {self._token}"},
            ) as ws:
                self._ws = ws
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._handle_event(msg.json())

    async def _handle_event(self, event: dict):
        """处理平台事件"""
        event_type = event.get("type")
        if event_type != "message":
            return

        data = event["data"]

        # ============================
        # 核心步骤：构造三个标准对象
        # ============================

        # 1. 构造 PlatformUser
        platform_user = PlatformUser(
            platform_name="mychat",
            user_id=str(data["sender"]["id"]),
            user_name=data["sender"]["name"],
            user_avatar=data["sender"].get("avatar", ""),
        )

        # 2. 构造 PlatformChannel
        chat_type = ChatType.GROUP if data["channel"]["type"] == "group" else ChatType.PRIVATE
        platform_channel = PlatformChannel(
            channel_id=str(data["channel"]["id"]),
            channel_name=data["channel"].get("name", ""),
            channel_type=chat_type,
        )

        # 3. 构造 PlatformMessage
        #    处理消息内容段（文本、图片等）
        segments: list[ChatMessageSegment] = []
        content_text = data.get("text", "")

        if content_text:
            segments.append(ChatMessageSegment(
                type=ChatMessageSegmentType.TEXT,
                text=content_text,
            ))

        # 处理图片附件
        for attachment in data.get("attachments", []):
            if attachment["type"] == "image":
                chat_key = self._adapter.build_chat_key(str(data["channel"]["id"]))
                img_segment = await ChatMessageSegmentImage.create_from_url(
                    url=attachment["url"],
                    from_chat_key=chat_key,
                    file_name=attachment.get("filename", "image.png"),
                )
                segments.append(img_segment)
                content_text += f" {img_segment.text}"

        # 判断是否 @ 了机器人
        is_tome = data.get("is_mention_bot", False) or chat_type == ChatType.PRIVATE

        platform_message = PlatformMessage(
            message_id=str(data["message_id"]),
            sender_id=str(data["sender"]["id"]),
            sender_name=data["sender"]["name"],
            sender_nickname=data["sender"].get("nickname", data["sender"]["name"]),
            content_text=content_text.strip(),
            content_data=segments,
            is_tome=is_tome,
            is_self=False,  # 客户端通常已过滤自身消息
            ext_data=PlatformMessageExt(
                ref_msg_id=str(data["reply_to"]) if data.get("reply_to") else "",
            ),
        )

        # ============================
        # 调用消息收集器——剩下的交给框架
        # ============================
        await collect_message(
            adapter=self._adapter,
            platform_channel=platform_channel,
            platform_user=platform_user,
            platform_message=platform_message,
        )

    # ============================
    # 平台 API 调用方法
    # ============================

    async def send_message(
        self,
        channel_id: str,
        text: str,
        files: list[str] | None = None,
        reply_to: str | None = None,
    ) -> str:
        """发送消息到 MyChat 平台，返回消息 ID"""
        # 实现平台特定的消息发送逻辑
        ...

    async def get_bot_info(self) -> dict:
        """获取机器人信息"""
        ...

    async def get_user(self, user_id: str) -> dict:
        """获取用户信息"""
        ...

    async def get_channel(self, channel_id: str) -> dict:
        """获取频道信息"""
        ...
```

### 第 5 步：注册适配器

在 `nekro_agent/adapters/__init__.py` 的 `ADAPTER_DICT` 字典中添加一行：

```python
ADAPTER_DICT: Dict[str, str] = {
    "onebot_v11": "nekro_agent.adapters.onebot_v11.adapter.OnebotV11Adapter",
    "discord": "nekro_agent.adapters.discord.adapter.DiscordAdapter",
    # ...其他适配器...
    "mychat": "nekro_agent.adapters.mychat.adapter.MyChatAdapter",  # 新增
}
```

注册后，框架会自动完成以下工作：
- 通过 `importlib` 动态加载适配器类并实例化
- 将适配器的路由挂载到 `/api/adapters/mychat/` 前缀下
- 在应用启动时调用 `init()`，关闭时调用 `cleanup()`
- 将适配器配置注册到统一配置系统（`ConfigManager`）

### 第 6 步：前端集成

在 `frontend/src/config/adapters.tsx` 的 `ADAPTER_CONFIGS` 中添加适配器条目：

```tsx
mychat: {
  key: 'mychat',
  visual: {
    displayName: 'names.mychat',    // i18n 键名
    iconText: 'MC',                  // 图标文字
    navIcon: <ChatIcon />,           // MUI 图标
    description: 'MyChat 平台适配器',
    tags: ['MyChat', '聊天', 'IM'],
  },
  tabs: [
    {
      label: 'tabs.home',
      value: 'home',
      icon: <HomeIcon fontSize="small" />,
      path: '',
      component: <AdapterHomePage />,
    },
    {
      label: 'tabs.config',
      value: 'config',
      icon: <SettingsIcon fontSize="small" />,
      path: 'config',
      component: <AdapterConfigPage />,
    },
    {
      label: 'tabs.overrides',
      value: 'overrides',
      icon: <StyleIcon fontSize="small" />,
      path: 'overrides',
      component: <AdapterOverrideConfigPage />,
    },
    {
      label: 'tabs.advanced',
      value: 'advanced',
      icon: <EngineeringIcon fontSize="small" />,
      path: 'advanced',
      component: <AdapterAdvancedPage />,
    },
  ],
},
```

同时在翻译文件中添加对应条目：

**`frontend/src/locales/zh-CN/adapter.json`：**
```json
{
  "names": {
    "mychat": "MyChat"
  }
}
```

**`frontend/src/locales/en-US/adapter.json`：**
```json
{
  "names": {
    "mychat": "MyChat"
  }
}
```

> 注意：标准 4 个选项卡（主页、配置、覆盖配置、高级）使用通用组件，无需额外开发。如果需要适配器特有的管理页面（如 OneBot V11 的 NapCat 和日志页面），则需自行开发对应的 React 组件。

### 第 7 步：编写 README 文档

文件：`nekro_agent/adapters/mychat/README.md`

此文件会通过 `/api/adapters/mychat/docs` 端点提供给前端，展示在适配器主页上。内容应包含：

- 功能特性说明
- 配置指南（如何获取 Token、如何创建 Bot）
- 注意事项

参考 `nekro_agent/adapters/discord/README.md` 的格式。

---

## 可选功能

以下功能有默认实现（不支持/空操作），适配器可根据平台能力选择性覆盖：

### 消息反应（Emoji 反馈）

当 AI 开始处理消息时，框架会调用此方法给消息添加 "处理中" 表情：

```python
async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:
    """设置消息反应
    Args:
        message_id: 消息 ID
        status: True=添加反应, False=移除反应
    Returns:
        是否成功
    """
    # 默认返回 False（不支持）
    # 如果平台支持表情反应，可以覆盖此方法
    ...
```

### 自定义对话示例

为 AI 提供适配器特有的对话示例模板：

```python
async def set_dialog_example(self) -> Optional[List[PromptTemplate]]:
    """返回适配器特定的对话示例（可选）"""
    return None  # 默认不提供
```

### Jinja2 模板环境

为适配器提供自定义的模板渲染能力：

```python
async def get_jinja_env(self) -> Optional[Environment]:
    """返回 Jinja2 模板环境（可选）"""
    return None  # 默认不提供
```

### WebUI 消息发送支持

某些适配器（如 OneBot V11）支持从 WebUI 直接发送消息：

```python
@property
def supports_webui_send(self) -> bool:
    """是否支持从 WebUI 发送消息"""
    return False  # 默认不支持
```

### 自定义 API 路由

如果适配器需要暴露额外的 HTTP 端点（如接收 Webhook 回调），覆盖 `get_adapter_router()`：

```python
from fastapi import APIRouter

def get_adapter_router(self) -> APIRouter:
    """提供适配器自定义的 API 路由"""
    router = APIRouter()

    @router.post("/webhook")
    async def handle_webhook(request: Request):
        """接收平台 Webhook 回调"""
        ...

    @router.get("/status")
    async def get_status():
        """获取适配器运行状态"""
        ...

    return router
```

路由会自动挂载到 `/api/adapters/{adapter_key}/` 前缀下。

---

## 现有适配器参考

| 适配器 | Key | 复杂度 | 通信方式 | 适合参考的场景 |
|---|---|---|---|---|
| **Discord** | `discord` | 低 | WebSocket（discord.py） | 基于第三方 SDK 接入 |
| **Telegram** | `telegram` | 中 | 轮询（python-telegram-bot） | 轮询式消息获取 |
| **SSE** | `sse` | 高 | HTTP + Server-Sent Events | 通用 HTTP 协议适配 |
| **OneBot V11** | `onebot_v11` | 高 | NoneBot 框架 | 基于 NoneBot 适配器生态 |
| **WeChatPad** | `wechatpad` | 中 | HTTP 回调 | 基于 HTTP 回调接入 |
| **Email** | `email` | 中 | IMAP + SMTP | 非即时通信类适配 |
| **Minecraft** | `minecraft` | 低 | NoneBot 适配器 | 游戏聊天集成 |
| **Bilibili Live** | `bilibili_live` | 中 | WebSocket | 直播弹幕类接入 |

**推荐初学者从 Discord 适配器开始阅读**，它结构最清晰、代码量最少，完整展示了适配器开发的核心模式。

---

## 常见问题

### Q: 适配器配置文件在哪里？

配置自动生成在 `$DATA_DIR/configs/{adapter_key}/config.yaml`。首次实例化时会根据配置类的默认值创建文件。配置同时注册到统一配置系统，可通过 WebUI 的适配器配置页面在线修改。

### Q: 如何获取适配器实例？

```python
# 方式 1：直接获取
from nekro_agent.adapters import get_adapter
adapter = get_adapter("mychat")

# 方式 2：通过工具类
from nekro_agent.adapters.utils import adapter_utils
adapter = adapter_utils.get_adapter("mychat")

# 方式 3：带类型转换
adapter = adapter_utils.get_typed_adapter("mychat", MyChatAdapter)

# 方式 4：根据 chat_key 自动定位
adapter = await adapter_utils.get_adapter_for_chat("mychat-group_123")
```

### Q: 如何处理图片/文件消息？

接收时，使用 `ChatMessageSegmentImage.create_from_url()` 或 `ChatMessageSegmentFile.create_from_url()` 下载远程文件到本地：

```python
segment = await ChatMessageSegmentImage.create_from_url(
    url="https://example.com/image.png",
    from_chat_key=chat_key,
    file_name="image.png",
)
```

发送时，`PlatformSendSegment.file_path` 字段包含已转换为本地可访问的路径，直接读取即可。

### Q: 如何判断消息是否 @ 了机器人？

在构造 `PlatformMessage` 时设置 `is_tome=True`。常见的判断逻辑：

- 消息中包含机器人的 @ 标记
- 消息是私聊（私聊默认视为 @ 机器人）
- 消息中包含机器人的名字（部分平台）

### Q: 适配器加载失败会怎样？

不会影响其他适配器和系统的正常运行。框架会捕获异常并记录日志，该适配器跳过加载，其他适配器正常工作。

### Q: 如何支持消息引用/回复？

接收时，将引用消息的 ID 放入 `PlatformMessageExt.ref_msg_id` 字段：

```python
ext_data=PlatformMessageExt(
    ref_msg_id="原始消息ID",
)
```

发送时，`PlatformSendRequest.ref_msg_id` 会携带需要回复的消息 ID，在 `forward_message()` 中处理即可。
