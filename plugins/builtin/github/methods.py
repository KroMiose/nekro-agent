from datetime import datetime
from typing import Any, Dict, List, Optional

from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger
from nekro_agent.services.plugin.schema import SandboxMethodType

from .models import ChatSubscriptions
from .plugin import plugin, store


@plugin.mount_prompt_inject_method("github_subscriptions_prompt")
async def github_subscriptions_prompt(_ctx: AgentCtx) -> str:
    """GitHub订阅提示"""
    data = await store.get(chat_key=_ctx.chat_key, store_key="github_subs")
    chat_subs: ChatSubscriptions = ChatSubscriptions.model_validate_json(data) if data else ChatSubscriptions()
    return chat_subs.render_prompts()


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "订阅GitHub仓库")
async def subscribe_github_repo(_ctx: AgentCtx, repo_name: str, events: Optional[List[str]] = None) -> str:
    """订阅GitHub仓库消息

    Args:
        repo_name: 仓库名称，格式为 'owner/repo'
        events: 要订阅的事件类型列表，默认包括 ["push", "issues", "pull_request", "release", "star"]

    Returns:
        str: 订阅结果消息
    """
    try:
        # 获取当前会话的订阅数据
        data = await store.get(chat_key=_ctx.chat_key, store_key="github_subs")
        chat_subs = ChatSubscriptions.model_validate_json(data) if data else ChatSubscriptions()
        # 创建或更新订阅
        await chat_subs.subscribe_repo(repo_name, events)
        # 保存订阅数据
        await store.set(chat_key=_ctx.chat_key, store_key="github_subs", value=chat_subs.model_dump_json())
        if not events:
            events = ["push", "issues", "pull_request", "release", "star"]
        events_str = ", ".join(events)
    except Exception as e:
        return f"订阅GitHub仓库失败: {e!s}"
    else:
        return f"成功订阅仓库 {repo_name} 的 {events_str} 事件"


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "取消订阅GitHub仓库")
async def unsubscribe_github_repo(_ctx: AgentCtx, repo_name: str) -> str:
    """取消订阅GitHub仓库消息

    Args:
        repo_name: 仓库名称，格式为 'owner/repo'

    Returns:
        str: 取消订阅结果消息
    """
    # 获取当前会话的订阅数据
    data = await store.get(chat_key=_ctx.chat_key, store_key="github_subs")
    if not data:
        raise ValueError(f"未找到仓库 {repo_name} 的订阅")
    chat_subs = ChatSubscriptions.model_validate_json(data)
    # 取消订阅
    await chat_subs.unsubscribe_repo(repo_name)
    # 保存订阅数据
    await store.set(chat_key=_ctx.chat_key, store_key="github_subs", value=chat_subs.model_dump_json())
    return f"成功取消订阅仓库 {repo_name}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "获取GitHub仓库订阅列表")
async def get_github_subscriptions(_ctx: AgentCtx) -> Dict[str, Any]:
    """获取当前会话的GitHub仓库订阅列表

    Returns:
        Dict: 订阅列表信息
    """
    try:
        # 获取当前会话的订阅数据
        data = await store.get(chat_key=_ctx.chat_key, store_key="github_subs")
        chat_subs = ChatSubscriptions.model_validate_json(data) if data else ChatSubscriptions()

        # 构建订阅列表
        result = {}
        for repo_name, sub in chat_subs.subscriptions.items():
            result[repo_name] = {
                "events": list(sub.events),
                "created_at": datetime.fromtimestamp(sub.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                "last_updated": datetime.fromtimestamp(sub.last_updated).strftime("%Y-%m-%d %H:%M:%S"),
            }

    except Exception as e:
        logger.error(f"获取GitHub仓库订阅列表失败: {e!s}")
        return {}
    else:
        return result


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "更新GitHub仓库订阅事件")
async def update_github_subscription_events(_ctx: AgentCtx, repo_name: str, events: List[str]) -> str:
    """更新GitHub仓库订阅的事件类型

    Args:
        repo_name: 仓库名称，格式为 'owner/repo'
        events: 要订阅的事件类型列表

    Returns:
        str: 更新结果消息
    """
    try:
        # 获取当前会话的订阅数据
        data = await store.get(chat_key=_ctx.chat_key, store_key="github_subs")
        if not data:
            return f"未找到仓库 {repo_name} 的订阅"

        chat_subs = ChatSubscriptions.model_validate_json(data)

        # 获取订阅信息
        sub = chat_subs.get_subscription(repo_name)
        if not sub:
            return f"未找到仓库 {repo_name} 的订阅"

        # 更新订阅事件
        sub.update_events(events)

        # 保存订阅数据
        await store.set(chat_key=_ctx.chat_key, store_key="github_subs", value=chat_subs.model_dump_json())

        events_str = ", ".join(events)
    except Exception as e:
        return f"更新GitHub仓库订阅事件失败: {e!s}"
    else:
        return f"成功更新仓库 {repo_name} 的订阅事件为: {events_str}"


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
