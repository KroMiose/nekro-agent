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

## 注意事项

- 极其非常强烈不建议用大号玩任何微信机器人框架，包括本适配器所用的WeChatPadPro，很容易触发微信风控，甚至导致账号被封！
- 若API运行环境与手机端地理位置、IP差异大，请自己额外配置s5代理把IP至少放到同一城市，否则很容易被标记异常限制功能。如果扫码登录显示：“在新设备完成验证以继续登录”，那就是触发了微信风控目前该框架还登录不了。
- 建议API服务和实际手机端尽可能靠近，并避免跳板、异地代理频繁登录等行为。
- 长时间未手动互动的账号进行频繁自动化操作也很容易触发风控标记账号异常。
- 作者现在镜像更新比较慢，docker拉的镜像可能不是最新的，如果需要最新版本请直接从github下载对应平台压缩包自己手动部署。


## 使用

### 1. 部署 WeChatPadPro 服务

1.  **克隆项目**
    ```sh
    git clone https://github.com/WeChatPadPro/WeChatPadPro.git
    ```

2.  **进入部署目录**
    ```sh
    cd WeChatPadPro/deploy
    ```

3.  **修改.env配置文件**
    (建议手动修改`ADMIN_KEY`，实在懒得改那不改也行)

4.  **配置网络（同机部署）**
    如果是在同一台机器上部署`nekro_agent`和`WeChatPadPro`，需要修改`docker-compose.yml`文件，把service里所有容器的网络（network）更改为`nekro_network`，以便与`nekro_agent`容器通信。

5.  **启动服务**
    ```sh
    docker-compose up -d
    ```

6.  **查看服务状态**
    ```sh
    docker-compose ps
    ```

### 2. 登录微信

1.  **访问 Swagger 界面**
    成功启动 WeChatPadPro 后根据你的 `serverip:port` 访问 WeChatPadPro 的 Swagger

2.  **填入 ADMIN_KEY**
    在 Swagger 界面中填入你的 `ADMIN_KEY`

3.  **获取 AuthKey**
    - 使用 `/admin/GanAuthKey1` 接口
    - **Try it out** → body 中的 `days` 改为 `365` 即可（AuthKey有效期365天）

4.  **登录微信**
    - 使用 `/login/GetLoginQrCodeNew` 接口
    - **Try it out** → 获取登录二维码
    - 返回的参数中有登录二维码链接，打开扫码登录即可
    - 如果是云服务器（和服务器不是同市或同省），可能需要设置代理填入 Proxy 参数才能正常登录

5.  **记录 AuthKey**
    记住你的 `AuthKey`，后面配置适配器时需要填入。

### 3. 配置适配器

1.  **填写核心配置**
    - 适配器目前只需要填写 `WECHATPAD_API_URL` 和 `WECHATPAD_AUTH_KEY`，`WECHATPAD_CALLBACK_URL` 可以不填（暂时还是ws接收实时消息，webhook功能还未实现）。

2.  **配置API地址 (`WECHATPAD_API_URL`)**
    - 填写你的 WeChatPadPro API 地址。
    - 如果两者部署在同一台机器上，填入 `http://wechatpadpro:8080`
    - 如果两者部署在不同台机器上，填入 `http://yourserverip:8080`

3.  **配置认证密钥 (`WECHATPAD_AUTH_KEY`)**
    - 填写你的 WeChatPadPro `AuthKey`。

#### 环境变量配置

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
