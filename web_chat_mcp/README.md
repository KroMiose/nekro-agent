# Web Chat MCP

Web Chat MCP 内置在 Nekro Agent 进程里，用于让 MCP Client 操控 Nekro Agent 的网页聊天功能：创建测试会话、发送消息、等待 Agent 回复、读取历史和清理测试会话。

## 启动方式

不需要单独启动 MCP Server。Nekro Agent 启动后会挂载 Streamable HTTP MCP：

```text
http://<nekro-agent-host>:8021/api/mcp/web-chat/mcp
```

接口由 Nekro Agent 统一鉴权。通常不需要手动配置 token：NA 会为内置的 Web Chat MCP 生成专用随机 token，并在全局 MCP 库条目中自动注入 Header。

```json
{
  "mcpServers": {
    "nekro-web-chat": {
      "type": "http",
      "url": "http://host.docker.internal:8021/api/mcp/web-chat/mcp",
      "headers": {
        "Authorization": "Bearer <NA 自动生成的 Web Chat MCP 专用 Token>"
      }
    }
  }
}
```

该 token 只被 Web Chat MCP 入口接受，不能用于调用其它 NA API。也可以使用 Nekro Agent 既有的管理员 JWT 或 `?token=` 查询参数鉴权，但推荐让 NA 自动注入专用 Header。

## 环境变量

- `NEKRO_WAIT_TIMEOUT`：等待 Agent 回复的默认超时秒数，默认 `60`。
- `NEKRO_POLL_INTERVAL`：等待回复时的历史轮询间隔秒数，默认 `1.5`。
- `NEKRO_WEB_CHAT_MCP_FILE_ALLOWLIST`：允许上传文件的本地目录列表，使用系统路径分隔符分隔；未设置时 `send_web_chat_file` 会拒绝读取本地文件。

## Tools

- `check_web_chat_status`
- `list_web_chat_sessions`
- `create_web_chat_session`
- `rename_web_chat_session`
- `delete_web_chat_session`
- `send_web_chat_message`
- `send_web_chat_file`
- `get_web_chat_messages`
- `get_web_chat_channel_detail`
- `wait_for_web_chat_reply`
- `send_and_wait_web_chat_reply`

推荐测试顺序：

1. `check_web_chat_status`
2. `create_web_chat_session`
3. `send_and_wait_web_chat_reply`
4. `get_web_chat_messages`
5. 测试结束后按需调用 `delete_web_chat_session`，并显式传入 `confirm=true`

## 安全边界

- MCP 与 NA 同进程启动，不暴露独立 stdio/HTTP 进程。
- MCP HTTP 入口先通过 Nekro Agent 的 `Authorization: Bearer ...` 鉴权，再进入工具调用。
- NA 自动生成的专用 token 只对 Web Chat MCP 生效，不是通用管理员 API token。
- 仅管理员可以使用该 MCP 入口。
- 文件上传默认禁用本地任意路径读取，必须配置 allowlist 后才可使用。
- 删除会话会清理历史、插件数据、定时任务、上传目录和沙盒目录，因此默认需要显式确认。
