# Telegram 适配器

这是 Nekro-Agent 的 Telegram 适配器，允许机器人与 Telegram 平台进行交互。

## 功能特点

- 支持接收和发送文本消息
- 支持处理图片、文件、语音、视频等多媒体内容
- 支持 @ 用户功能
- 支持贴纸(Sticker)和视频笔记(Video Note)
- 支持私聊和群聊
- 基于 python-telegram-bot 库，稳定可靠

## 技术实现

适配器基于 `python-telegram-bot 21.11.1` 版本开发，使用异步轮询方式接收消息。

## 配置说明

适配器需要在配置文件中设置以下参数：

- **BOT_TOKEN**: 从 [@BotFather](https://t.me/BotFather) 获取的 Telegram Bot Token（必填）

## 使用方法

1. 在 Nekro-Agent 中启用 Telegram 适配器
2. 配置必要参数（仅需 BOT_TOKEN）
3. 启动 Nekro-Agent，适配器会自动连接到 Telegram
4. 在 Telegram 中与机器人进行交互

## 支持的消息类型

### 接收消息
- **文本消息**: 普通文本内容
- **图片消息**: 转换为 ChatMessageSegmentImage
- **文档消息**: 转换为 ChatMessageSegmentFile
- **视频消息**: 转换为 ChatMessageSegmentFile
- **音频消息**: 转换为 ChatMessageSegmentFile
- **语音消息**: 转换为 ChatMessageSegmentFile
- **贴纸消息**: 转换为 ChatMessageSegmentImage
- **视频笔记**: 转换为 ChatMessageSegmentFile

### 发送消息
- **文本消息**: 支持发送纯文本
- **图片消息**: 支持发送图片文件
- **文件消息**: 支持发送任意文件
- **@用户**: 通过文本形式实现（@username）

## 注意事项

1. 机器人需要有足够的权限来读取和发送消息
2. 在群聊中，需要明确 @机器人 或在私聊中发送消息才会触发 AI 回复
3. 大文件可能需要较长时间传输，请耐心等待
4. 适配器会自动下载文件到临时目录并在处理完成后清理

## 常见问题

### Q: 如何获取 Telegram Bot Token？
A: 与 [@BotFather](https://t.me/BotFather) 对话，使用 `/newbot` 命令创建机器人并获取 Token。

### Q: 启动后看起来没有连接成功？
A: 请检查：
- `BOT_TOKEN` 是否已正确填写
- 机器人是否已通过 @BotFather 正确创建
- 网络连接是否正常（新版本基于 python-telegram-bot，网络要求较低）
- 通过接口 `/api/adapters/telegram/status` 或 `/api/adapters/telegram/info` 查看状态

### Q: 如何在群聊中使用机器人？
A: 在群聊中，需要：
- 将机器人添加到群组
- 给机器人管理员权限或确保能读取消息
- 发送消息时需要 @机器人用户名来触发回复

### Q: 如何获取用户或群组的 ID？
A: 可以使用一些第三方机器人（如 @userinfobot）来获取 ID，或通过适配器的日志查看。

### Q: 为什么机器人不响应我的消息？
A: 请检查：
- Bot Token 是否正确
- 在群聊中是否 @了机器人（群聊需要明确提及）
- 私聊中所有消息都会自动触发回复
- 机器人是否有权限读取消息（在 @BotFather 中设置权限）
- 检查适配器日志是否有错误信息

## 技术架构

### 核心组件
- **TelegramAdapter**: 主适配器类，管理连接和消息流
- **MessageProcessor**: 消息处理器，负责转换消息格式
- **TelegramHTTPClient**: HTTP 客户端，处理消息发送
- **TelegramConfig**: 配置管理类

### 消息流程
1. Telegram → python-telegram-bot → MessageProcessor
2. MessageProcessor → ChatMessageSegment → 核心引擎
3. 核心引擎 → PlatformSendRequest → TelegramHTTPClient → Telegram

## 开发者信息

- **作者**: nekro-agent 团队
- **版本**: 2.0.0
- **技术栈**: python-telegram-bot 21.11.1
- **主页**: https://github.com/KroMiose/nekro-agent