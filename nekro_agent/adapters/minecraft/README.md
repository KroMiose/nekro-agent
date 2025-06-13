# Minecraft 适配器

## 概述

Minecraft 适配器用于与 Minecraft 服务器进行通信，支持游戏内聊天互动、服务器监控和玩家管理功能。

## 功能特性

### 连接协议

- ✅ RCON 远程控制协议
- ✅ 支持 Minecraft 1.16+
- ✅ UTF-8 编码支持
- ✅ 安全的身份验证

### 聊天功能

- ✅ 游戏内聊天消息双向同步
- ✅ 玩家消息接收
- ✅ 系统消息推送
- ✅ 自定义消息格式

### 服务器管理

- ✅ 实时服务器状态监控
- ✅ 在线玩家查看
- ✅ 服务器事件监听
- ✅ RCON 命令执行

## 配置说明

### 必需配置

- 服务器地址和端口
- RCON 密码
- 连接超时设置

### 可选配置

- 消息格式模板
- 事件过滤规则
- 重连策略

## 聊天标识规则

Minecraft 适配器使用以下格式标识聊天频道：

- **服务器聊天**: `minecraft-server_服务器ID`
- **玩家私聊**: `minecraft-player_玩家UUID`

## 依赖要求

- Minecraft 服务器 (1.16+)
- 启用 RCON 功能
- 网络连接稳定
- 正确的防火墙配置

## 配置示例

### server.properties 配置

```properties
enable-rcon=true
rcon.password=your_password_here
rcon.port=25575
```

## 支持的命令

### 基础命令

- `/list` - 查看在线玩家
- `/say <message>` - 发送服务器消息
- `/tellraw <player> <json>` - 发送富文本消息

### 管理命令

- `/kick <player>` - 踢出玩家
- `/ban <player>` - 封禁玩家
- `/whitelist add <player>` - 添加白名单

## 常见问题

### Q: 无法连接到服务器？

A: 请检查：

1. 服务器是否启用 RCON
2. 端口是否正确开放
3. 密码是否正确
4. 防火墙设置

### Q: 收不到聊天消息？

A: 确认：

1. 服务器版本兼容性
2. 消息格式配置
3. 权限设置

### Q: 命令执行失败？

A: 检查：

1. RCON 连接状态
2. 命令格式正确性
3. 服务器权限配置
