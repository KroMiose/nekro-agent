# Telegram 适配器

这是 Nekro-Agent 的 Telegram 适配器，允许机器人与 Telegram 平台进行交互。

## 功能特点

- 支持接收和发送文本消息
- 支持处理图片和文件
- 支持 @ 用户功能
- 支持代理设置
- 支持用户和群组权限控制

## 安装依赖

使用前，请先安装必要的依赖包：

```bash
pip install pyrogram tgcrypto
```

## 配置说明

适配器需要在配置文件中设置以下参数：

- **BOT_TOKEN**: 从 [@BotFather](https://t.me/BotFather) 获取的 Telegram Bot Token
- **API_ID**: 从 [my.telegram.org](https://my.telegram.org) 获取的 API ID（必填）
- **API_HASH**: 从 [my.telegram.org](https://my.telegram.org) 获取的 API Hash（必填）
- **ALLOWED_USERS**: 允许使用机器人的用户 ID 列表（留空表示允许所有用户）
- **ALLOWED_CHATS**: 允许使用机器人的群组 ID 列表（留空表示允许所有群组）
- **PROXY_URL**: 代理服务器地址（如: http://127.0.0.1:7890 或 socks5://127.0.0.1:7890）
- **PROXY_USERNAME**: 代理服务器用户名（如果需要认证）
- **PROXY_PASSWORD**: 代理服务器密码（如果需要认证）
- **MAX_MESSAGE_LENGTH**: Telegram 消息的最大长度限制（默认4096）
- **SESSION_FILE**: 会话文件名（默认"nekro_agent.session"）

## 使用方法

1. 在 Nekro-Agent 中启用 Telegram 适配器
2. 配置上述必要参数（BOT_TOKEN、API_ID、API_HASH 必填）
3. 启动 Nekro-Agent，适配器会自动连接到 Telegram
4. 在 Telegram 中与机器人进行交互

## 聊天键格式

Telegram 适配器的聊天键格式为：`telegram-{chat_id}`

其中 `{chat_id}` 是 Telegram 中的聊天 ID。

## 注意事项

1. 首次启动时，可能需要根据提示进行授权
2. 如果使用代理，请确保代理服务器可用
3. 某些功能可能需要额外的 Bot 权限，请在 @BotFather 中设置
4. 大文件可能需要较长时间传输，请耐心等待

## 常见问题

### Q: 如何获取 Telegram Bot Token？
A: 与 [@BotFather](https://t.me/BotFather) 对话，使用 `/newbot` 命令创建机器人并获取 Token。

### Q: 如何获取 API ID 和 API Hash？
A: 访问 [my.telegram.org](https://my.telegram.org)，登录并创建应用程序即可获取。注意需要在 `data/configs/telegram/config.yaml` 中填写。

### Q: 启动后看起来没有连接成功？
A: 请检查：
- 是否安装了依赖：`pyrogram` 和 `tgcrypto`（项目已在依赖中声明，若是手动环境需自行安装）
- `data/configs/telegram/config.yaml` 中 `BOT_TOKEN`、`API_ID`、`API_HASH` 是否已正确填写（全部为必填）
- 如在内地网络环境，`PROXY_URL` 是否配置正确（格式：`socks5://127.0.0.1:7890` 或 `http://127.0.0.1:7890`）
- 通过接口 `/api/adapters/telegram/status` 或 `/api/adapters/telegram/info` 查看状态

### Q: 如何获取用户或群组的 ID？
A: 可以使用一些第三方机器人（如 @userinfobot）来获取 ID，或通过适配器的日志查看。

### Q: 为什么机器人不响应我的消息？
A: 请检查：
- Bot Token 是否正确
- 用户或群组是否在 ALLOWED_USERS 或 ALLOWED_CHATS 列表中
- 机器人是否有权限读取消息（在 @BotFather 中设置权限）
- 代理服务器是否正常工作（如果使用了代理）

## 开发者信息

- **作者**: KroMiose
- **版本**: 1.0.0
- **主页**: https://github.com/KroMiose/nekro-agent