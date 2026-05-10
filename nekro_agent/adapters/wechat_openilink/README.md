# WeChat OpenILink 适配器

基于 `wechatbot-sdk` 的微信适配器。

## 当前能力（MVP）

- 支持微信文本消息接收
- 支持 AI 文本回复发送
- 支持图片/文件/语音消息发送
- 支持群聊 / 私聊基础会话映射

## 登录方式

- 通过 `wechatbot-sdk` 的二维码登录能力完成认证
- 启动阶段会在控制台输出二维码登录网址（不打印 ASCII 二维码）
- 扫码成功后凭据写入 `CRED_PATH`，后续重启可直接复用凭据

## 主要配置

- `BASE_URL`：微信 iLink API 地址（默认 `https://ilinkai.weixin.qq.com`）
- `CRED_PATH`：登录凭据文件保存路径（默认 `data/nekro_agent/configs/wechat_openilink/credentials.json`）
- `LOGIN_TIMEOUT_SECONDS`：二维码登录超时秒数
- `TREAT_PRIVATE_AS_TOME`：私聊是否默认触发
- `GROUP_REQUIRE_MENTION`：群聊是否必须 @ 触发
- `DEDUP_WINDOW_SECONDS`：消息去重窗口

## 重要说明

- 初始化阶段若登录或启动失败，会输出异常日志并导致适配器初始化失败
- 媒体消息发送（图片/文件/语音）使用异步文件读取，避免阻塞事件循环
- 群聊默认仅在 @ 机器人时触发（可通过配置关闭）
