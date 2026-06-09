# WeChat OpenILink 多实例适配器

基于 OpenILink 协议的微信多账号实例适配器。每个微信 Bot 作为独立实例管理，支持扫码绑定、消息收发、自动续期和状态观测。

## 配置

所有配置项定义在 `config.py` 的 `WeChatILinkMultiConfig` 中。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ENABLED` | `bool` | `False` | 是否启用适配器。默认关闭，等待具体协议传输实现接入后再开启。 |
| `API_BASE_URL` | `str` | `https://ilinkai.weixin.qq.com` | OpenILink 协议服务基础地址，不含具体资源路径。 |
| `DEFAULT_RENEW_BEFORE_MINUTES` | `int` | `60` | 会话凭据过期前多少分钟触发默认续期。可按实例单独覆盖。 |
| `BIND_TIMEOUT_SECONDS` | `int` | `180` | 二维码绑定流程等待完成的最长时间（秒）。 |
| `DEDUP_WINDOW_SECONDS` | `int` | `120` | 入站消息按 provider 消息 ID 去重的时间窗口（秒）。 |
| `MEDIA_DOWNLOAD_MAX_BYTES` | `int` | `20971520` (20 MB) | 单个媒体文件允许下载的最大字节数。 |
| `MEDIA_DOWNLOAD_TIMEOUT_SECONDS` | `int` | `60` | 单个媒体文件下载的超时时间（秒）。 |

## 管理 API 示例

所有 API 要求 admin 认证。先获取 token：

```bash
export NA_ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8021/api/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin&password=na-ilink-test-admin' | jq -r '.access_token')
AUTH="Authorization: Bearer $NA_ADMIN_TOKEN"
BASE="http://127.0.0.1:8021/api/adapters/wechat_ilink_multi/instances"
```

### 创建实例

```bash
curl -s -X POST "$BASE" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"instance_key":"my-bot-1","display_name":"客服 Bot","provider":"wechat"}'
```

首次创建返回 `201`，重复创建返回 `200` 且 `existing: true`。

### 开始二维码绑定

```bash
curl -s -X POST "$BASE/my-bot-1/bind/start" -H "$AUTH"
```

响应包含 `bind_session_id`、`qr_url`、`bind_status: "qr_generated"`。

### 轮询绑定状态

```bash
curl -s -X GET "$BASE/my-bot-1/bind/status/{bind_session_id}" -H "$AUTH"
```

`bind_status` 依次变化：`qr_generated` → `qr_scanned` → `login_confirmed` → `session_persisted`。状态为 `confirmed` 时提示 "绑定成功"。

### 启动 / 停止实例

```bash
curl -s -X POST "$BASE/my-bot-1/start" -H "$AUTH"    # 204 No Content
curl -s -X POST "$BASE/my-bot-1/stop" -H "$AUTH"     # 204 No Content
```

### 查看实例列表 / 详情

```bash
curl -s -X GET "$BASE" -H "$AUTH"                    # 实例列表
curl -s -X GET "$BASE/my-bot-1" -H "$AUTH"           # 实例详情（不含凭据）
```

### 触发续期 / 更新续期策略

```bash
curl -s -X POST "$BASE/my-bot-1/renew" -H "$AUTH"              # 手动触发续期
curl -s -X PATCH "$BASE/my-bot-1/renew-policy" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"renew_before_minutes":30}'                              # 修改提前续期分钟数
```

### 查看实例事件

```bash
curl -s -X GET "$BASE/my-bot-1/events" -H "$AUTH"
```

返回审计事件列表，含 `event_type`、`status_from`、`status_to`、`message`。

### 删除实例

```bash
curl -s -X DELETE "$BASE/my-bot-1" -H "$AUTH"        # 204 No Content，软删除
```

## 状态机

### 主生命周期状态

```
pending → binding → online ⟷ offline / renewing / session_expired / error
                                                              ↓
                                                           deleted
```

| 状态 | 说明 |
|------|------|
| `pending` | 实例已创建，尚未绑定 |
| `binding` | 绑定进行中（二维码已生成） |
| `online` | 监控连接已建立，可收发消息 |
| `offline` | 实例已停止或连接断开 |
| `renewing` | 会话续期中（临时状态） |
| `session_expired` | 会话凭据已过期，需重新绑定 |
| `error` | 运行异常，`last_error` 记录错误信息 |
| `deleted` | 已软删除（`enabled=False`） |

### 绑定成功定义

绑定流程中，二维码绑定子状态依次为：

```
qr_generated → qr_scanned → login_confirmed → session_persisted
```

绑定成功的必要条件：

1. `login_confirmed`：OpenILink 侧确认登录
2. `session_persisted`：凭据与同步状态写入 `DBAdapterInstanceSession`
3. `BotConnection` 监控任务成功启动
4. 主生命周期状态切换为 `online`

以上任一条件失败，绑定视为失败。`qr_scanned` 不等同于绑定成功。

### QR 绑定子状态

| 子状态 | 来源 | 说明 |
|--------|------|------|
| `qr_generated` | `start_bind()` | 二维码或授权 URL 已生成 |
| `qr_scanned` | `poll_bind()` 返回 `scanned` | 用户在手机上已扫码 |
| `login_confirmed` | `poll_bind()` 返回 `confirmed` | 绑定登录已确认 |
| `session_persisted` | `_complete_bind()` | 凭据和同步状态已持久化 |
| `expired` | `poll_bind()` 返回 `expired` | 绑定会话已过期 |
| `failed` | `poll_bind()` 返回其他失败 | 绑定出错 |

绑定子状态保存在 `DBAdapterInstanceSession.session_state` 中，通过 `set_session_state()` 更新。子状态变化时产生 `bind_state_change` 事件记录。

## 续期策略

### 默认行为

- 默认在凭据过期前 **60 分钟** 触发自动续期（`DEFAULT_RENEW_BEFORE_MINUTES=60`）
- 可按实例通过 `PATCH /instances/{key}/renew-policy` 单独覆盖
- 实例的 `next_renew_at` 在每次凭据持久化时重新计算

### 续期流程

1. `BotConnection._run_renew_loop` 后台任务等待至 `next_renew_at`
2. 到期时调用 `renew_once()`，主状态切换为 `renewing`
3. 成功后更新凭据、同步状态和 `renewed_at`，主状态恢复为先前状态（`online` 或 `offline`）
4. 重新计算 `next_renew_at`，继续等待下一轮

### 失败恢复

续期失败时：

- 若凭据已过期 → 主状态设为 `session_expired`
- 其他错误 → 主状态设为 `error`，`last_error` 记录异常信息
- 凭据和会话行**保留不删除**，可手动调用 `POST /renew` 或 `POST /bind/start` 恢复
- 后台续期任务在失败后**不会退出**，而是按指数退避（60s 起、上限 30min）继续重试，直至成功或实例被停止；避免 `next_renew_at` 处于过去时间时产生 1 秒紧循环

## 消息支持矩阵

| 消息类型 | 接收 | 发送 | 说明 |
|----------|------|------|------|
| 文本 (Text) | ✅ | ✅ | 双向支持 |
| 图片 (Image) | ✅ | ✅ | 接收解析为 `ChatMessageSegmentImage`；发送通过 `send_file()` 上传 |
| 文件 (File) | ✅ | ✅ | 接收解析为 `ChatMessageSegmentFile`；发送通过 `send_file()` 上传 |
| 语音 (Voice) | ✅ | ❌ | 接收映射为 `ChatMessageSegmentFile`（`.mp3` / `.amr`），文本显示 `[Voice: filename]`。不新增 VOICE 段类型以保持序列化兼容。 |
| 视频 (Video) | ❌ | ❌ | 不支持 |
| 贴纸 (Stickers) | ❌ | ❌ | 不支持 |
| 复杂撤回 | ❌ | ❌ | 不支持复杂撤回逻辑 |

> **会话范围说明**：iLink 协议的微信 bot **不能加入群聊**，仅存在 1:1 私聊场景。所有入站消息均按私聊处理
> （`channel_id = {instance_key}:private:{user_id}`，`ChatType.PRIVATE`，`is_tome=True`）。
> 代码中保留的 group 作用域分支为防御性兜底，正常运行中不会被触发。

### 消息去重

每个 `BotConnection` 实例维护独立的去重缓存，按 `(instance_key, remote_message_id)` 去重，窗口默认 120 秒。重复消息不会传递到 `collect_message()` 管道。

### 媒体下载限制

- 超过 `MEDIA_DOWNLOAD_MAX_BYTES`（默认 20 MB）的媒体会被替换为可见错误文本段 `[媒体文件过大: ...]`
- 下载失败的媒体返回错误文本 `[图片下载失败]` / `[语音下载失败]` / `[文件下载失败]`
- 消息解析失败时使用兜底文本 `[OpenILink 消息解析失败: ...]`

## 兼容性

- 现有 `wechat_openilink` 适配器**未做任何修改**，行为保持不变
- 新适配器使用独立 adapter key `wechat_ilink_multi`，与旧适配器并行存在
- chat key 格式：`wxim-{instance_key}:private:{user_id}`。
  本适配器 **重写了 `build_chat_key()`**，使用短前缀 `wxim-` 而非默认的 `wechat_ilink_multi-`：
  因为 `wechat_ilink_multi`（18 字符）+ 实例作用域 channel_id 容易超出 `DBChatChannel.chat_key` 的 64 字符上限
  （iLink 用户 id 形如 `xxxxxxxx@im.wechat`，较长）。
- 由于短前缀 `wxim` ≠ adapter_key，配置解析层（`config_resolver` / `config_service`）改用
  `nekro_agent.adapters.resolve_adapter_key_from_chat_key()` 经别名映射还原 adapter_key，保证适配器级配置覆盖生效。
- channel ID 作用域：`{instance_id}:private:{user_id}`（iLink 仅 1:1 私聊，无群聊；详见“消息支持矩阵”）
- message ID 作用域：`{instance_id}:{remote_message_id}`
- chat_key 含 `:`、`@` 等字符，作为文件系统/Docker 卷路径片段时由 `sanitize_chat_key_for_path()`
  统一清洗（写入、宿主机路径换算、沙盒挂载三处一致）；该函数对现有适配器的无特殊字符 chat_key 为恒等变换，零回归。
- 为支持上述短前缀，`collector.py` 与 `DBChatChannel.get_or_create` 增加了透传 `adapter.build_chat_key()`
  结果的能力（默认仍为 `{adapter_key}-{channel_id}`，对其它适配器无行为变化）。不修改 `DBUser`、`DBPluginData`。
- 凭据不在任何 API 响应中暴露

## 架构概览

```
WeChatILinkMultiAdapter (adapter.py)
  └── BotManager (bot_manager.py)          ← 生命周期编排
        ├── BotConnection × N               ← 每实例独立连接
        │     ├── OpenILinkMultiClient       ← 协议边界（client.py）
        │     ├── OpenILinkMultiMessageProcessor ← 消息解析
        │     ├── monitor task               ← 消息监控
        │     └── renew task                 ← 自动续期
        └── AdapterInstanceService           ← 通用持久化底座
              ├── DBAdapterInstance
              ├── DBAdapterInstanceSession
              └── DBAdapterInstanceEvent
```

## 本地开发

### 依赖服务（OrbStack / Docker）

NA 主服务从源码运行，依赖服务通过 Docker Compose 提供：

```bash
# 方式 A：全新构建（推荐）
docker compose -f docker/docker-compose.dev.yml pull nekro_postgres nekro_qdrant nekro_napcat
docker compose -f docker/docker-compose.dev.yml up -d nekro_postgres nekro_qdrant nekro_napcat
```

> 注意：如果之前使用过 `postgres:14`，需要先停止并移除旧容器，删除或重命名 `../data/dev_postgres_data`，再启动 `postgres:16`。不要将 PG14 数据目录直接挂载到 PG16。

### 启动开发服务器

```bash
ADMIN_PASSWORD=na-ilink-test-admin poe dev-docs
```

服务默认运行在 `http://127.0.0.1:8022`。API 文档地址为 `http://127.0.0.1:8022/api/docs`。

### 健康检查

```bash
curl -s http://127.0.0.1:8022/api/health          # → {"ok": true}
```

### 数据库迁移

```bash
poe db-revision <name>   # 生成迁移文件
poe db-migrate           # 执行迁移
```

### 验证命令

```bash
poe check        # typecheck + lint
poe load-test    # 适配器加载测试
```

## 重要说明

- 适配器初始化不发出网络请求。监控连接仅在 `init()` 加载 DB 实例后启动。
- 传输实现应继承 `OpenILinkMultiClient`（`client.py`），当前默认使用 `UnsupportedOpenILinkMultiClient` 占位。
- 外部协议返回的原始字典只在 `schemas.py` 的 `parse_*_payload` 函数中读取，业务逻辑仅消费 Pydantic 模型。
- 多账号场景下每个连接创建独立 client 实例，凭据与同步状态由上层持久化。
- iLink bot 仅 1:1 私聊：私聊消息恒 `is_tome=True`。（保留的群聊 `is_tome` 分支为兜底，正常不触发。）
- 停止实例会取消 monitor 和 renew 后台任务并等待完成。
- 相同 `(adapter_key, provider_account_id)` 已绑定到其他非删除实例时，新绑定会返回 HTTP 409（`ProviderAccountAlreadyBound`）。
