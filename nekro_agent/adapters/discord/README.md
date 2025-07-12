# Discord 适配器

本适配器用于将 Nekro Agent 连接到 Discord 平台，使其能够作为 Discord Bot 与服务器内的用户进行实时交互。

## 功能特性

- **实时消息**：接收并响应服务器频道和私聊消息。
- **富文本支持**：支持发送和接收文本、文件、图片以及 @提及。
- **多服务器支持**：可以被邀请到多个 Discord 服务器中同时工作。

## 配置指南

要使用此适配器，您需要先在 Discord 开发者平台创建一个应用程序和对应的 Bot。

### 1. 创建 Discord 应用程序

1.  访问 [Discord Developer Portal](https://discord.com/developers/applications)。
2.  点击右上角的 **"New Application"**。
3.  为您的应用命名，然后点击 **"Create"**。

### 2. 创建 Bot

1.  在应用页面，点击左侧菜单的 **"Bot"** 选项。
2.  点击 **"Add Bot"**，然后确认创建。
3.  在 Bot 设置页面，您可以自定义 Bot 的用户名和头像。

### 3. 获取 Bot Token

- 在 Bot 设置页面，找到 **"TOKEN"** 部分，点击 **"Reset Token"** (如果是首次创建则为 "View Token" 或 "Copy")。
- **请妥善保管此 Token，不要泄露给任何人！** 这是控制您 Bot 的唯一凭证。

### 4. 配置特权网关意图 (Privileged Gateway Intents)

为了让您的 Bot 能够读取消息内容，必须开启必要的 "Intents"。

- 在 Bot 设置页面，向下滚动找到 **"Privileged Gateway Intents"** 部分。
- 开启以下两个选项：
    - **PRESENCE INTENT**
    - **MESSAGE CONTENT INTENT** (最重要！)

### 5. 邀请 Bot 到您的服务器

1.  在应用页面，点击左侧菜单的 **"OAuth2"** -> **"URL Generator"**。
2.  在 **"SCOPES"** 中，勾选 `bot` 和 `applications.commands`。
3.  在下方出现的 **"BOT PERMISSIONS"** 中，勾选以下推荐权限：
    - `Read Messages/View Channels`
    - `Send Messages`
    - `Send Messages in Threads`
    - `Embed Links`
    - `Attach Files`
    - `Read Message History`
    - `Mention @everyone, @here, and All Roles`
    - `Use External Emojis`
    - `Add Reactions`
4.  复制页面底部生成的 **URL**，在浏览器中打开，然后选择您想邀请 Bot 加入的服务器。

## 安装与启用

### 1. 安装依赖

通过 `poetry` 安装此适配器的可选依赖：

```bash
poetry install -E discord
```

### 2. 启用适配器

此适配器在系统中默认注册，您只需在 `data/configs/adapter_discord/config.yaml` 文件中填入您的 Bot Token 即可。

如果文件不存在，请手动创建它，并填入以下内容：

```yaml
# data/configs/adapter_discord/config.yaml
BOT_TOKEN: "在这里粘贴你从 Discord Developer Portal 获取的 Bot Token"
```

完成以上步骤后，重启 Nekro Agent，Discord 适配器即可加载并连接。 