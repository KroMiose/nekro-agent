# Web Adapter

Web Adapter 是 Nekro Agent 官方内置的 WebUI 网页聊天适配器，用于在管理后台中创建本地测试会话、发送网页用户消息并观察 Agent 回复。

## 用途

- 在不接入 QQ、微信、Telegram 等外部平台时验证聊天闭环。
- 调试人设、插件命令、频道状态和覆盖配置。
- 复用现有频道详情、消息历史和实时展示能力。
- 管理 Web Chat 测试会话名称，并清理不再需要的测试会话。

## 启用方式

Web Adapter 默认启用。可在适配器配置中关闭 `ENABLED`，关闭后需要重启应用生效。

禁用时，WebUI 网页聊天页面会显示适配器未启用状态；会话与入站消息接口不会挂载。

## 会话标识规则

- `channel_id`: `session_<uuid>`
- `chat_key`: `web-session_<uuid>`
- `channel_type`: `private`
- 默认会话名: `网页测试会话`
- 会话列表按最后一条消息时间倒序排列。
- 网页用户名称默认按 `WEB_USER_NAME_TEMPLATE=web_user_{id}` 生成，支持 `{id}` 和 `{username}` 占位符；渲染为空或 `admin` 时回退为 `web_user_{id}`，避免与 WebUI 管理员保留用户名冲突。

网页用户消息会被转换为 `PlatformUser`、`PlatformChannel`、`PlatformMessage`，并通过 `collect_message()` 进入现有消息管线。

## 消息、文件与回复

- 支持文本入站消息，以及单个文件/图片随消息上传。
- 上传文件会保存到当前频道的 uploads 目录，并以现有 `file` / `image` 消息段进入消息管线；沙盒中可通过 `./uploads/<filename>` 只读访问。
- 单文件大小限制由 `FILE_UPLOAD_MAX_SIZE_MB` 配置控制，默认 100MB。
- 网页用户的普通消息默认视为私聊中对 Agent 的直接消息。
- Agent 回复通过 `WebAdapter.forward_message()` 返回发送结果，再由现有消息服务写入历史并通过实时流展示。
- Agent 可通过基础插件的 `send_msg_text()` / `send_msg_file()` 向网页会话回复文本或文件。
- 不使用 `/chat-channel/{chat_key}/send` 伪装用户入站消息；该接口仍保留机器人、SYSTEM 或命令输出发送语义。

## 权限与限制

- 网页聊天 API 仅允许已登录管理员访问。
- 不开放匿名聊天。
- 不返回 token、`.env`、宿主机路径、内部端口或密钥。
- 命令权限默认遵循现有平台用户权限规则，不因 WebUI 管理员登录态自动提升为超级用户。
- 如需让 Web Chat 中的 WebUI 管理员执行超级用户命令，可开启 `WEBUI_ADMIN_AS_COMMAND_SUPERUSER`。该配置默认关闭，仅影响 Web Adapter 的命令执行上下文，不会改写全局 `SUPER_USERS`。

## 测试建议

1. 从 WebUI 进入“聊天管理 > 网页聊天”。
2. 创建一个测试会话。
3. 发送普通文本，确认 Agent 回复进入消息历史。
4. 上传图片或文件，确认消息历史展示附件，Agent 沙盒可读取 `./uploads/<filename>`。
5. 发送命令前缀消息，确认命令权限和输出符合当前配置。
6. 编辑会话名称，确认右侧会话列表同步更新。
7. 删除不再需要的测试会话，确认消息、插件数据、定时任务和上传目录被清理。
8. 跳转频道详情，将频道设为 disabled，确认 Web Chat 禁止发送；恢复 active 后可继续聊天。
