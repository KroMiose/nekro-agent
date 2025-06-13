# OneBot V11 适配器

## 概述

OneBot V11 适配器用于与兼容 OneBot V11 标准的 QQ 机器人实现进行通信，支持群聊和私聊消息的收发。

## 支持的实现

- **go-cqhttp**: 基于 Mirai 的 OneBot 实现
- **NapCat**: 基于官方 QQ 的 OneBot 实现
- **Lagrange.OneBot**: 基于 Lagrange.Core 的 OneBot 实现

## 功能特性

### 消息类型支持

- ✅ 纯文本消息
- ✅ @用户消息
- ✅ 图片消息（支持本地文件和网络链接）
- ✅ 文件上传（群文件/私聊文件）

### 聊天类型支持

- ✅ 群聊消息收发
- ✅ 私聊消息收发
- ✅ 群成员信息获取
- ✅ 群信息获取

### 高级功能

- ✅ 消息反应（emoji 点赞）
- ✅ CQ 码解析（可配置）
- ✅ 文本中@用户自动解析

## 配置说明

### 必需配置

适配器会自动连接到 NoneBot2 配置的 OneBot V11 协议端，无需额外配置连接信息。

## 聊天标识规则

OneBot V11 适配器使用以下格式标识聊天频道：

- **群聊**: `onebot_v11-group_123456` （123456 为群号）
- **私聊**: `onebot_v11-private_123456` （123456 为用户 QQ 号）

## 依赖要求

- NoneBot2 框架
- nonebot-adapter-onebot 插件
- 兼容的 OneBot V11 实现（如 go-cqhttp、NapCat 等）

## 常见问题

### Q: 无法发送消息？

A: 请检查：

1. OneBot 实现是否正常运行
2. NoneBot2 是否成功连接到 OneBot 实现
3. 机器人是否在目标群聊中

### Q: 图片无法发送？

A: 请确保：

1. 图片文件存在且可读
2. 图片格式被 OneBot 实现支持
3. 图片大小符合平台限制

### Q: 文件上传失败？

A: 请检查：

1. `SANDBOX_ONEBOT_SERVER_MOUNT_DIR` 配置是否正确
2. OneBot 实现是否支持文件上传
3. 文件路径映射是否正确
