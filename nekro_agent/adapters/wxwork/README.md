# 企业微信 AI Bot 适配器

企业微信智能机器人（AI Bot）长连接模式，使用官方 WebSocket 协议收发消息。

## 必填配置

```yaml
BOT_ID: "your-bot-id"
BOT_SECRET: "your-bot-secret"
```

## 说明

- 使用官方长连接命令：
  - `aibot_subscribe`
  - `aibot_msg_callback`
  - `aibot_event_callback`
  - `aibot_send_msg`
- WebSocket 地址固定为官方地址 `wss://openws.work.weixin.qq.com`
- 不需要公网回调地址

## 当前限制

- 主动发送支持 Markdown、图片、文件
- 语音、视频、模板卡片后续再补齐
- 用户名和群名暂以原始 ID 为主，后续再结合真实事件结构补全
