# WeChatPad 适配器

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

WeChatPad 适配器是 nekro-agent 的一个组件，用于通过 WeChatPadPro 的 HTTP API 与微信进行交互。

## 功能特性

- ✅ 支持发送和接收文本消息
- ✅ 支持发送和接收图片消息
- ✅ 支持群聊和私聊消息处理
- ✅ 支持用户和群组信息获取
- ✅ 实时消息接收和处理
- ✅ 支持自定义 API 端点和认证

## 安装

1. 确保已安装 nekro-agent
2. 将 `wechatpad` 适配器目录复制到 `nekro_agent/adapters/` 目录下
3. 在 `nekro_agent/adapters/__init__.py` 中注册适配器

## 配置

适配器支持以下环境变量配置：

| 环境变量 | 描述 | 默认值 |
|---------|------|--------|
| `WECHATPAD_API_URL` | WeChatPadPro API 地址 | `http://localhost:8080` |
| `WECHATPAD_AUTH_KEY` | WeChatPadPro 认证密钥 | 无（必填） |
| `WECHATPAD_CALLBACK_URL` | 接收微信事件回调的地址 | `http://localhost:8000/wechatpad/callback` |


## 贡献

欢迎提交 Issue 和 Pull Request。

## 许可证

MIT

## 作者

Dirac - [GitHub](https://github.com/1A7432)
