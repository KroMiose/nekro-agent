# 飞书适配器

本适配器用于将 Nekro Agent 连接到飞书（Feishu/Lark）开放平台，使其能够作为飞书机器人与用户进行实时交互。

## 功能特性

- **实时消息**：通过 WebSocket 长连接实时接收和响应消息
- **群聊/私聊**：支持群组和单聊场景
- **富媒体支持**：支持发送和接收文本、图片、文件及富文本（post）消息
- **@提及**：支持识别和发送 @用户 消息
- **表情回应**：支持为消息添加表情回应（处理中反馈）

## 配置指南

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击 **「创建企业自建应用」**
3. 填写应用名称和描述，完成创建

### 2. 添加机器人能力

1. 在应用详情页，点击左侧 **「添加应用能力」**
2. 选择 **「机器人」** 能力并添加

### 3. 获取 App ID 和 App Secret

- 在应用详情页的 **「凭证与基础信息」** 中找到 **App ID** 和 **App Secret**
- 将这两个值填入 NekroAgent 的飞书适配器配置中

### 4. 配置事件订阅

1. 在应用详情页，点击 **「事件与回调」** → **「事件配置」**
2. **重要：选择使用「长连接」模式**（WebSocket），无需配置公网回调地址
3. 添加事件：
   - `im.message.receive_v1`（接收消息）

### 5. 添加 API 权限

在 **「权限管理」** 中点击 **「批量导入/导出权限」**，粘贴以下 JSON 后导入：

```json
{
  "scopes": {
    "tenant": [
      "contact:contact.base:readonly",
      "contact:user.base:readonly",
      "im:chat",
      "im:message",
      "im:message.group_at_msg:readonly",
      "im:message.group_msg",
      "im:message.p2p_msg:readonly",
      "im:message.reactions:write_only",
      "im:message:send_as_bot",
      "im:resource"
    ],
    "user": []
  }
}
```

| 权限标识 | 说明 |
|---------|------|
| `contact:contact.base:readonly` | 获取通讯录基本信息 |
| `contact:user.base:readonly` | 获取用户基本信息（头像、昵称等） |
| `im:chat` | 获取与更新群组信息 |
| `im:message` | 获取与发送单聊、群组消息 |
| `im:message.group_at_msg:readonly` | 接收群聊中 @机器人 的消息 |
| `im:message.group_msg` | 接收群聊中的所有消息 |
| `im:message.p2p_msg:readonly` | 接收用户发送的单聊消息 |
| `im:message.reactions:write_only` | 为消息添加表情回应 |
| `im:message:send_as_bot` | 以机器人身份发送消息 |
| `im:resource` | 获取与上传图片或文件资源 |

### 6. 发布应用

- 完成以上配置后，在 **「版本管理与发布」** 中创建版本并提交审核
- 审核通过后，机器人即可正常使用

## 注意事项

- **必须使用 WebSocket 长连接模式**，不支持 HTTP 回调模式
- 图片和文件需要先通过 API 上传获取 key，再通过 key 引用发送
- 私聊场景下所有消息默认视为 `is_tome`（与机器人相关）
- 飞书消息中的 @机器人 占位符会被自动清理，不会出现在最终文本中
