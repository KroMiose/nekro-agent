# 企业微信智能机器人适配器

连接企业微信自定义智能机器人，实现企业内部 AI 助手功能。

## 快速配置

### 1. 在企业微信后台生成密钥

在创建智能机器人配置页面：

1. **Token**: 点击"随机获取"按钮，生成 Token
   - 例如：`xxxxxxxxxx`
2. **EncodingAESKey**: 点击"随机获取"按钮，生成 43 位密钥
   - 例如：`xxxxxxxxxx`

**先不要点"保存"！** 复制这两个值，先去配置 Nekro Agent。

### 2. 在 Nekro Agent 中配置

在 Nekro Agent 企业微信适配器的配置界面中填写刚才复制的值：

```yaml
TOKEN: "xxxxxxxxxx"
ENCODING_AES_KEY: "xxxxxxxxxx"
```

保存配置后，确保服务已重启并正常运行。

### 3. 回到企业微信后台验证 URL

在企业微信机器人配置页面填写回调地址：

- **URL**: `http://<你的 Nekro Agent 服务访问地址>/api/adapters/wxwork/callback`

> ⚠️ 注意：需要先绑定企业域名进行验证

现在可以点击"保存"按钮，企业微信会向你的服务器发送验证请求。

验证通过后即可开始使用。

## 相关文档

- [企业微信开发者中心 - 智能机器人](https://developer.work.weixin.qq.com/document/path/101039)
