"""
# GitHub 动态订阅 (GitHub)

一个将 GitHub 仓库动态实时推送到聊天的插件。

## 设计理念：信息聚合

很多时候，我们需要关注某个开源项目的进展，但又不想频繁地去 GitHub 网站上查看。此插件通过 Webhook 机制，将 GitHub 的动态（如代码提交、新的 Issue、发布新版本等）变成聊天消息，让信息主动来找你。

## 主要功能

- **订阅仓库**: 可以在任何聊天中，订阅一个或多个 GitHub 仓库的指定事件。
- **事件推送**: 当订阅的仓库发生动态时，插件会自动将格式化后的消息推送到对应的聊天中。
- **订阅管理**: AI 提供了完整的工具来添加、移除、查看和更新仓库订阅。

## 使用方法

- **与 AI 对话**: 你可以直接对 AI 说："帮我订阅 `owner/repo` 这个仓库的动态"，AI 就会调用工具来完成订阅。
- **Webhook 配置**:
    1.  在需要接收通知的 GitHub 仓库的 `Settings -> Webhooks` 页面，点击 `Add webhook`。
    2.  在 `Payload URL` 中填入你的 Nekro-Agent 服务地址，并加上 `/api/webhook/plugins/github` 路径（例如 `http://<你的 Nekro-Agent 服务地址>/api/webhook/plugins/github`）。
    3.  `Content type` 选择 `application/json`。
    4.  （可选但推荐）设置一个 `Secret`，并将同样的内容填写到本插件的 `WEBHOOK_SECRET` 配置中，以确保不会被滥用访问。
    5.  选择你希望接收通知的事件类型，然后保存。

完成以上步骤后，当仓库有新动态时，你就能在订阅了该仓库的聊天中收到通知了。
"""

from . import handlers, methods, models
from .plugin import plugin

__all__ = ["plugin"]
