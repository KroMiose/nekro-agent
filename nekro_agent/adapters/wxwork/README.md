# 企业微信 AI Bot 适配器

企业微信智能机器人（AI Bot）长连接模式，使用官方 WebSocket 协议收发消息。

## 必填配置

```yaml
BOT_ID: "your-bot-id"
BOT_SECRET: "your-bot-secret"
WS_URL: "wss://openws.work.weixin.qq.com"
```

## 说明

- 使用官方长连接命令：
  - `aibot_subscribe`
  - `aibot_msg_callback`
  - `aibot_event_callback`
  - `aibot_send_msg`
- 不需要公网回调地址

## 当前限制

- 发送侧当前优先支持文本消息
- 图片、文件等媒体消息后续再补齐
- 用户名和群名暂以原始 ID 为主，后续再结合真实事件结构补全
