# Minecraft 适配器

## 概述

Minecraft 适配器用于与 Minecraft 服务器进行通信，支持游戏内聊天互动、服务器监控和玩家管理功能。

## 功能特性

### 连接协议

- ✅ RCON 远程控制协议
- ✅ Websocket 协议 (基于 [nonebot-adapter-minecraft](https://github.com/17TheWord/nonebot-adapter-minecraft) 适配器)

### 聊天功能

- ✅ 游戏内聊天消息双向同步
- ✅ 玩家消息接收
- ✅ 系统消息推送
- ✅ 富文本消息发送

## 配套插件/模组

此适配器需要配合在 Minecraft 服务端上安装 [QueQiao](https://github.com/17TheWord/QueQiao) 插件/模组才能使用 WebSocket 相关功能。

- **下载地址**:
  - [CurseForge](https://www.curseforge.com/minecraft/mc-mods/queqiao)
  - [Modrinth](https://modrinth.com/plugin/queqiao)

- **配置文档**:
  - [部署指南](https://github.com/17TheWord/QueQiao/wiki/1.-部署)
  - [配置文件说明](https://github.com/17TheWord/QueQiao/wiki/2.-配置文件)

## 配置说明

您需要在 Nekro Agent 的 Web UI 中配置此适配器。

### `MINECRAFT_ACCESS_TOKEN`

全局的 WebSocket 连接认证密钥，用于验证与所有配置的 Minecraft 服务器的连接。

### `SERVERS`

一个服务器列表，您可以在其中配置一个或多个 Minecraft 服务器。每个服务器配置包含以下字段：

- **`SERVER_NAME`**: 服务器的唯一名称，将用于生成聊天标识。**（必填）**
- **`SERVER_WS_URL`**: 服务器的 WebSocket 地址 (例如 `ws://127.0.0.1:8089`)。需要配合 Minecraft 服务端插件使用。
- **`IS_SERVER_RCON`**: 是否为此服务器启用 RCON。
- **`SERVER_RCON_PORT`**: RCON 端口，默认为 `25575`。
- **`SERVER_RCON_PASSWORD`**: RCON 密码。

## 聊天标识规则

Minecraft 适配器使用以下格式标识聊天频道：

- **服务器聊天**: `minecraft-<SERVER_NAME>` (其中 `SERVER_NAME` 是您在服务器配置中填写的服务器名称)

## 配置示例

### QueQiao 配置文件示例

以下是 QueQiao 插件/模组的配置文件示例 (配置文件实际路径请参考上文的 [部署指南](https://github.com/17TheWord/QueQiao/wiki/1.-部署)):

```yaml
enable: true # 是否启用插件/模组

debug: false # DEBUG，开启后会打印所有日志

server_name: "Server" # 服务器名称，对应上文中的SERVER_NAME

access_token: "" # 用于连接时进行验证

# 消息前缀
# 消息前面添加的前缀（不包含Title、ActionBar）
# 设置为空时，不会在消息前面添加前缀
message_prefix: "" #建议留空，此内容可不用修改

# WebSocket Server配置项
websocket_server:
  enable: true          # 是否启用
  host: "127.0.0.1"     # WebSocket Server 地址 如果是公网建议改为0.0.0.0
  port: 8080            # WebSocket Server 端口 按需修改

# WebSocket Client配置项，此配置项不需要修改
websocket_client:
  enable: false                 # 是否启用
  reconnect_interval: 5         # 重连间隔（秒）
  reconnect_max_times: 5        # 最大重连次数
  url_list:
    - "ws://127.0.0.1:8080/minecraft/ws"

# 订阅事件配置项
subscribe_event:
  player_chat: true       # 玩家聊天事件监听
  player_death: true      # 玩家死亡事件监听
  player_join: true       # 玩家登录事件监听
  player_quit: true       # 玩家退出事件监听
  player_command: true    # 玩家命令事件监听
```

### Minecraft `server.properties` 配置

如果启用了 RCON，请确保您的 `server.properties` 文件中有如下配置：

```properties
enable-rcon=true
rcon.password=your_rcon_password
rcon.port=25575
```
