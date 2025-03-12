import hashlib
import hmac
import json
from typing import Dict

from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.services.message.message_service import message_service

from .models import ChatSubscriptions
from .plugin import config, plugin, store


@plugin.mount_webhook_method(endpoint="github", name="处理GitHub webhook事件")
async def handle_github_webhook(_ctx: AgentCtx) -> None:
    """处理GitHub webhook事件

    Args:
        _ctx: 上下文
        body: GitHub webhook请求体
    """
    if not _ctx.webhook_request:
        raise ValueError("webhook_request is required")
    body = _ctx.webhook_request.body
    headers = _ctx.webhook_request.headers
    logger.debug(f"收到GitHub webhook请求: {headers}\n===\n {body}")

    try:
        # 如果配置了webhook密钥，验证签名
        if config.WEBHOOK_SECRET and headers:
            # 获取GitHub的签名头
            signature_header = headers.get("X-Hub-Signature-256")
            if signature_header:
                # 重新获取请求体进行验证
                try:
                    # 计算签名
                    hash_object = hmac.new(
                        key=config.WEBHOOK_SECRET.encode("utf-8"),
                        msg=json.dumps(body).encode("utf-8"),
                        digestmod=hashlib.sha256,
                    )
                    expected_signature = "sha256=" + hash_object.hexdigest()

                    # 使用安全比较方法
                    if not hmac.compare_digest(expected_signature, signature_header):
                        logger.warning(f"GitHub 签名不匹配: 预期 {expected_signature}, 实际 {signature_header}")
                        logger.warning("GitHub webhook 验证失败，请检查 WEBHOOK_SECRET 配置")
                        return
                    logger.info("GitHub webhook签名验证成功")
                except Exception as e:
                    logger.error(f"验证GitHub签名时出错: {e}")
                    return
            else:
                logger.warning("未找到X-Hub-Signature-256头，但配置了WEBHOOK_SECRET，拒绝请求")
                return

        # 从body中获取事件类型
        event_type = headers.get("x-github-event")

        # 如果没有event_type，直接打印错误信息
        if not event_type:
            logger.error("未能识别GitHub事件类型")
            return

        logger.info(f"收到GitHub {event_type} 事件")

        # 提取仓库信息
        repository = body.get("repository", {})
        repo_full_name = repository.get("full_name", "unknown/unknown")

        # 根据事件类型路由到不同的处理逻辑
        if event_type == "push":
            await _handle_push_event(repo_full_name, body)
        elif event_type == "issues":
            await _handle_issues_event(repo_full_name, body)
        elif event_type == "pull_request":
            await _handle_pull_request_event(repo_full_name, body)
        elif event_type == "release":
            await _handle_release_event(repo_full_name, body)
        elif event_type == "star":
            await _handle_star_event(repo_full_name, body)
        elif event_type == "ping":
            logger.info(f"收到来自仓库 {repo_full_name} 的ping事件，GitHub webhook配置成功")
        else:
            # 处理其他类型的事件
            await _handle_generic_event(repo_full_name, event_type, body)

    except Exception as e:
        logger.error(f"处理GitHub webhook事件失败: {e!s}")


async def _handle_push_event(repo_full_name: str, body: Dict) -> None:
    """处理GitHub Push事件

    Args:
        repo_full_name: 仓库全名
        body: GitHub Push事件的webhook请求体
    """
    try:
        # 提取推送信息
        pusher = body.get("pusher", {}).get("name", "Unknown")
        ref = body.get("ref", "").replace("refs/heads/", "")

        # 提取提交信息
        commits = body.get("commits", [])
        commit_count = len(commits)

        # 格式化消息
        message = "📢 GitHub 推送通知\n\n"
        message += f"📦 仓库: {repo_full_name}\n"
        message += f"👤 推送者: {pusher}\n"
        message += f"🌿 分支: {ref}\n"
        message += f"📝 提交数: {commit_count}\n\n"

        if commits:
            message += "📋 最近提交:\n"
            for i, commit in enumerate(commits[:5]):  # 最多显示5条提交
                # 使用字符串分割和拼接方法来避免转义问题
                commit_message = commit.get("message", "")
                first_line = commit_message.split("\n")[0] if commit_message else ""
                message += f"{i+1}. {first_line}\n"
                message += f"   作者: {commit.get('author', {}).get('name', 'Unknown')}\n"
                message += f"   时间: {commit.get('timestamp', '')}\n"
                message += f"   链接: {commit.get('url', '')}\n\n"

        # 向所有订阅的会话发送消息
        await send_to_subscribers(repo_full_name, "push", message)

    except Exception as e:
        logger.error(f"处理GitHub Push事件失败: {e!s}")


async def _handle_issues_event(repo_full_name: str, body: Dict) -> None:
    """处理GitHub Issues事件

    Args:
        repo_full_name: 仓库全名
        body: GitHub Issues事件的webhook请求体
    """
    try:
        # 提取issue信息
        action = body.get("action", "unknown")
        issue = body.get("issue", {})
        issue_number = issue.get("number", "?")
        issue_title = issue.get("title", "无标题")
        issue_body = issue.get("body", "无内容")
        issue_url = issue.get("html_url", "")

        # 提取用户信息
        user = body.get("sender", {})
        user_name = user.get("login", "Unknown")

        # 格式化消息
        message = "📢 GitHub Issue 通知\n\n"
        message += f"📦 仓库: {repo_full_name}\n"
        message += f"👤 用户: {user_name}\n"
        message += f"🔍 动作: {action}\n"
        message += f"🔢 Issue #{issue_number}: {issue_title}\n"
        message += f"🔗 链接: {issue_url}\n\n"

        if len(issue_body) > 300:
            issue_body = issue_body[:300] + "..."
        message += f"📄 内容预览:\n{issue_body}\n"

        # 向所有订阅的会话发送消息
        await send_to_subscribers(repo_full_name, "issues", message)

    except Exception as e:
        logger.error(f"处理GitHub Issues事件失败: {e!s}")


async def _handle_pull_request_event(repo_full_name: str, body: Dict) -> None:
    """处理GitHub Pull Request事件

    Args:
        repo_full_name: 仓库全名
        body: GitHub Pull Request事件的webhook请求体
    """
    try:
        # 提取PR信息
        action = body.get("action", "unknown")
        pr = body.get("pull_request", {})
        pr_number = pr.get("number", "?")
        pr_title = pr.get("title", "无标题")
        pr_body = pr.get("body", "无内容") or "无内容"
        pr_url = pr.get("html_url", "")

        # 提取用户信息
        user = body.get("sender", {})
        user_name = user.get("login", "Unknown")

        # 提取分支信息
        head_branch = pr.get("head", {}).get("ref", "unknown")
        base_branch = pr.get("base", {}).get("ref", "unknown")

        # 格式化消息
        message = "📢 GitHub Pull Request 通知\n\n"
        message += f"📦 仓库: {repo_full_name}\n"
        message += f"👤 用户: {user_name}\n"
        message += f"🔍 动作: {action}\n"
        message += f"🔢 PR #{pr_number}: {pr_title}\n"
        message += f"🌿 分支: {head_branch} → {base_branch}\n"
        message += f"🔗 链接: {pr_url}\n\n"

        if len(pr_body) > 300:
            pr_body = pr_body[:300] + "..."
        message += f"📄 内容预览:\n{pr_body}\n"

        # 向所有订阅的会话发送消息
        await send_to_subscribers(repo_full_name, "pull_request", message)

    except Exception as e:
        logger.error(f"处理GitHub Pull Request事件失败: {e!s}")


async def _handle_release_event(repo_full_name: str, body: Dict) -> None:
    """处理GitHub Release事件

    Args:
        repo_full_name: 仓库全名
        body: GitHub Release事件的webhook请求体
    """
    try:
        # 提取Release信息
        action = body.get("action", "unknown")
        release = body.get("release", {})
        tag_name = release.get("tag_name", "无标签")
        release_name = release.get("name", tag_name)
        release_body = release.get("body", "无内容") or "无内容"
        release_url = release.get("html_url", "")
        is_prerelease = release.get("prerelease", False)

        # 提取用户信息
        user = body.get("sender", {})
        user_name = user.get("login", "Unknown")

        # 格式化消息
        message = "📢 GitHub Release 通知\n\n"
        message += f"📦 仓库: {repo_full_name}\n"
        message += f"👤 用户: {user_name}\n"
        message += f"🔍 动作: {action}\n"
        message += f"🏷️ 版本: {release_name} ({tag_name})\n"
        if is_prerelease:
            message += "⚠️ 这是一个预发布版本\n"
        message += f"🔗 链接: {release_url}\n\n"

        if len(release_body) > 300:
            release_body = release_body[:300] + "..."
        message += f"📄 发布说明:\n{release_body}\n"

        # 向所有订阅的会话发送消息
        await send_to_subscribers(repo_full_name, "release", message)

    except Exception as e:
        logger.error(f"处理GitHub Release事件失败: {e!s}")


async def _handle_star_event(repo_full_name: str, body: Dict) -> None:
    """处理GitHub Star事件

    Args:
        repo_full_name: 仓库全名
        body: GitHub Star事件的webhook请求体
    """
    try:
        # 提取Star信息
        action = body.get("action", "unknown")

        # 提取用户信息
        user = body.get("sender", {})
        user_name = user.get("login", "Unknown")

        # 提取仓库信息和star数量
        repository = body.get("repository", {})
        star_count = repository.get("stargazers_count", 0)

        # 格式化消息
        message = "📢 GitHub Star 通知\n\n"
        message += f"📦 仓库: {repo_full_name}\n"
        message += f"👤 用户: {user_name}\n"
        message += f"🔍 动作: {'添加了star' if action == 'created' else '移除了star'}\n"
        message += f"⭐ 当前star数: {star_count}\n"

        # 向所有订阅的会话发送消息
        await send_to_subscribers(repo_full_name, "star", message)

    except Exception as e:
        logger.error(f"处理GitHub Star事件失败: {e!s}")


async def _handle_generic_event(repo_full_name: str, event_type: str, body: Dict) -> None:
    """处理其他类型的GitHub事件

    Args:
        repo_full_name: 仓库全名
        event_type: 事件类型
        body: GitHub webhook请求体
    """
    try:
        # 提取基本信息
        action = body.get("action", "unknown")

        # 提取用户信息
        user = body.get("sender", {})
        user_name = user.get("login", "Unknown")

        # 格式化消息
        message = f"📢 GitHub {event_type.title()} 事件通知\n\n"
        message += f"📦 仓库: {repo_full_name}\n"
        message += f"👤 用户: {user_name}\n"
        if action:
            message += f"🔍 动作: {action}\n"

        # 添加事件特定详情
        if "comment" in event_type and "comment" in body:
            comment = body.get("comment", {})
            comment_body = comment.get("body", "无内容") or "无内容"
            comment_url = comment.get("html_url", "")

            if len(comment_body) > 300:
                comment_body = comment_body[:300] + "..."
            message += f"🔗 链接: {comment_url}\n\n"
            message += f"📄 评论内容:\n{comment_body}\n"

        # 向所有订阅的会话发送消息
        await send_to_subscribers(repo_full_name, event_type, message)

    except Exception as e:
        logger.error(f"处理GitHub {event_type} 事件失败: {e!s}")


async def send_to_subscribers(repo_name: str, event_type: str, message: str):
    """向所有订阅的会话发送消息

    Args:
        repo_name: 仓库名称
        event_type: 事件类型
        message: 要发送的消息
    """
    # 获取所有聊天会话
    from nekro_agent.models.db_chat_channel import DBChatChannel

    chat_channels = await DBChatChannel.all()

    # 遍历所有会话，查找订阅了该仓库的会话
    sent_count = 0
    for channel in chat_channels:
        chat_key = channel.chat_key
        data = await store.get(chat_key=chat_key, store_key="github_subs")
        if not data:
            continue

        chat_subs = ChatSubscriptions.model_validate_json(data)
        if chat_subs.is_subscribed(repo_name, event_type):
            try:
                # 发送消息并触发AI响应
                await message_service.push_system_message(chat_key=chat_key, agent_messages=message, trigger_agent=True)
                sent_count += 1
                logger.info(f"已向会话 {chat_key} 推送 {repo_name} 的 {event_type} 事件")
            except Exception as e:
                logger.error(f"向会话 {chat_key} 推送消息失败: {e!s}")

    logger.info(f"共向 {sent_count} 个会话推送了 {repo_name} 的 {event_type} 事件")
