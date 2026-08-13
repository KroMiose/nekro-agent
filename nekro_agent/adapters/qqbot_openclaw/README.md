# QQBot OpenClaw Adapter

这是面向 OpenClaw QQBot 渠道行为实现的 Nekro 原生适配器，用于替代不稳定的 Napcat/OneBot 链路。

实现准绳为 `tencent-connect/openclaw-qqbot` 插件源码与实测行为，不按公开 QQ 官方 Bot 文档做泛化产品行为。

## Chat Key

- 私聊：`qqoc-c2c:{user_openid}`
- 群聊：`qqoc-group:{group_openid}`

## 首版范围

- 单账号 `APP_ID` / `CLIENT_SECRET`
- C2C 私聊文本与媒体收发
- QQ 群 @、普通群消息上下文记录、引用机器人消息触发
- 图片、语音、视频、文件按 OpenClaw 上传流程发送
- 主动发送默认放行，失败会记录并返回错误

OpenClaw 渠道的用户身份是 openid，不是传统 QQ 号。
