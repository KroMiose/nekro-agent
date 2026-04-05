# 企业微信自建应用适配器

企业微信自建应用模式，使用回调 URL 接收消息，并通过企业微信应用 API 发送消息。

## 必填配置

```yaml
CORP_ID: "wwxxxxxxxxxxxxxxxx"
CORP_APP_SECRET: "your-app-secret"
CORP_APP_AGENT_ID: "1000002"
CALLBACK_TOKEN: "your-callback-token"
CALLBACK_ENCODING_AES_KEY: "your-encoding-aes-key"
CORP_API_BASE_URL: "https://qyapi.weixin.qq.com"
```

## 回调地址

在企业微信后台配置：

`/api/adapters/wxwork_corp_app/callback`

例如：

`https://your-domain.example.com/api/adapters/wxwork_corp_app/callback`

## 说明

- URL 验证与消息接收都走同一回调地址
- 私聊发送走 `/cgi-bin/message/send`
- 当前仅支持私聊消息收发
- 群聊 `ChatId` 与 `/cgi-bin/appchat/send` 暂不启用
