"""
# 动态头像 (Dynamic Avatar)

根据特定逻辑（定时、状态变化或指令）自动切换机器人在合并转发消息中显示的头像名称。

## 主要功能

- **情绪头像**: 根据 Agent 的情绪状态自动切换到匹配的头像名称
- **指令切换**: Agent 可以通过工具调用主动切换头像
- **定时切换**: 支持根据时间自动切换头像（如工作时间/休息时间）
- **状态切换**: 根据 Agent 运行状态（如思考中、忙碌、空闲）切换头像

## 工作原理

1. **头像管理器 (AvatarManager)**: 核心组件，管理所有头像配置和切换逻辑
2. **头像配置 (AvatarProfile)**: 定义头像名称和关联的情绪标签
3. **切换触发器**: 支持情绪触发、指令触发、定时触发
4. **监听器机制**: 头像切换时通知所有注册的监听器

## 使用方法

Agent 可以通过以下方式切换头像：

1. **自动情绪切换**:
   - 当 Agent 情绪变为 "happy" 时，自动切换到 "NekroAgent 😊"
   - 当 Agent 情绪变为 "thinking" 时，自动切换到 "NekroAgent 🤔"

2. **手动指令切换**:
   - `switch_avatar("NekroAgent 😴", "用户休息了")`
   - `set_avatar_emotion("happy")`
   - `get_avatar_status()` - 查看当前状态
   - `list_avatar_profiles()` - 列出所有可用头像

## 技术细节

- **头像数据**: 仅更改合并转发消息中的发送者名称（Name），头像（Avatar）取决于 QQ 号
- **存储方式**: 头像配置存储在内存中，可通过 API 持久化
- **线程安全**: 使用 asyncio.Lock 保证并发安全
"""

from .plugin import plugin

__all__ = ["plugin"]
