import hashlib
import hmac
import json
from typing import Dict

from nekro_agent.api import core
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger
from nekro_agent.services.message_service import message_service

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
    core.logger.debug(f"GitHub webhook原始请求: headers={headers}")
    core.logger.debug(f"GitHub webhook原始请求体: body类型={type(body)}, 内容={body}")

    try:
        # 如果配置了webhook密钥，验证签名
        if config.WEBHOOK_SECRET and headers:
            # 获取GitHub的签名头
            signature_header = headers.get("X-Hub-Signature-256")
            core.logger.debug(
                f"GitHub签名头: {signature_header}, WEBHOOK_SECRET配置: {'已设置' if config.WEBHOOK_SECRET else '未设置'}",
            )

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
                        core.logger.warning(f"GitHub 签名不匹配: 预期 {expected_signature}, 实际 {signature_header}")
                        core.logger.warning("GitHub webhook 验证失败，请检查 WEBHOOK_SECRET 配置")
                        return
                    core.logger.info("GitHub webhook签名验证成功")
                except Exception as e:
                    core.logger.error(f"验证GitHub签名时出错: {e}")
                    return
            else:
                core.logger.warning("未找到X-Hub-Signature-256头，但配置了WEBHOOK_SECRET，拒绝请求")
                return

        # 从body中获取事件类型
        event_type = headers.get("x-github-event")
        core.logger.debug(f"GitHub webhook事件类型: {event_type}, 请求头: {headers}")

        # 如果没有event_type，直接打印错误信息
        if not event_type:
            core.logger.error("未能识别GitHub事件类型")
            return

        core.logger.info(f"收到GitHub {event_type} 事件")

        # 提取仓库信息
        repository = body.get("repository", {})
        core.logger.debug(f"提取repository结果: 类型={type(repository)}, 值={repository}")
        repo_full_name = repository.get("full_name", "unknown/unknown")
        core.logger.debug(f"提取repo_full_name结果: {repo_full_name}")

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
        elif event_type == "workflow_run":
            # 工作流运行事件
            await _handle_generic_event(repo_full_name, event_type, body)
        elif event_type == "workflow_job":
            # 工作流作业事件
            await _handle_generic_event(repo_full_name, event_type, body)
        elif event_type == "check_run" or event_type == "check_suite":
            # 检查运行/检查套件事件
            await _handle_generic_event(repo_full_name, event_type, body)
        elif event_type == "ping":
            core.logger.info(f"收到来自仓库 {repo_full_name} 的ping事件，GitHub webhook配置成功")
        else:
            # 处理其他类型的事件
            await _handle_generic_event(repo_full_name, event_type, body)

    except Exception as e:
        core.logger.error(f"处理GitHub webhook事件失败: {e!s}")


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
        before = body.get("before", "")
        after = body.get("after", "")
        is_deleted = after == "0000000000000000000000000000000000000000"
        is_created = before == "0000000000000000000000000000000000000000"
        is_forced = body.get("forced", False)

        # 提取提交信息
        commits = body.get("commits", [])
        commit_count = len(commits)

        # 获取比较链接
        compare_url = body.get("compare", "")

        # 格式化消息
        message = "📢 GitHub 推送事件\n\n"
        message += f"仓库: {repo_full_name}\n"
        message += f"推送者: {pusher}\n"

        # 根据不同的推送类型显示不同的信息
        if is_deleted:
            message += f"分支删除: {ref}\n"
        elif is_created:
            message += f"新分支: {ref}\n"
        elif is_forced:
            message += f"强制推送: {ref}\n"
        else:
            message += f"分支: {ref}\n"

        message += f"提交数: {commit_count}\n"

        # 添加比较链接
        if compare_url and not is_deleted and not is_created:
            message += f"比较: {compare_url}\n"

        # 如果是删除分支，显示特殊信息
        if is_deleted:
            message += "此分支已被删除\n"
        # 如果是强制推送，显示警告
        elif is_forced:
            message += "这是一次强制推送，历史记录可能已被重写\n"
        # 如果有提交且不是删除分支，显示提交信息
        elif commits and not is_deleted:
            message += "\n最近提交:\n"
            for _i, commit in enumerate(commits[:3]):  # 最多显示3条提交
                commit_message = commit.get("message", "")
                first_line = commit_message.split("\n")[0] if commit_message else ""
                commit_id = commit.get("id", "")[:7]  # 短 commit ID
                author = commit.get("author", {})
                author_name = author.get("name", "Unknown")

                message += f"[{commit_id}] {first_line} (作者: {author_name})\n"

                # 显示文件变更统计
                added = len(commit.get("added", []))
                modified = len(commit.get("modified", []))
                removed = len(commit.get("removed", []))
                if added > 0 or modified > 0 or removed > 0:
                    message += f"变更: +{added} ~{modified} -{removed} 个文件\n"

        # 向所有订阅的频道发送消息
        await send_to_subscribers(repo_full_name, "push", message)

    except Exception as e:
        core.logger.error(f"处理GitHub Push事件失败: {e!s}")


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
        issue_body = issue.get("body", "无内容") or "无内容"
        issue_url = issue.get("html_url", "")
        issue_state = issue.get("state", "unknown")

        # 提取标签信息
        labels = issue.get("labels", [])
        label_names = [label.get("name", "") for label in labels]

        # 提取里程碑信息
        milestone = issue.get("milestone", {})
        milestone_title = milestone.get("title", "无") if milestone else "无"

        # 提取分配者信息
        assignees = issue.get("assignees", [])
        assignee_names = [assignee.get("login", "") for assignee in assignees]

        # 提取创建者信息
        creator = issue.get("user", {})
        creator_name = creator.get("login", "Unknown")

        # 格式化消息
        message = "📢 GitHub Issue 事件\n\n"
        message += f"仓库: {repo_full_name}\n"
        message += f"动作: {action}\n"
        message += f"Issue #{issue_number}: {issue_title}\n"
        message += f"创建者: {creator_name}\n"

        # 显示Issue状态
        if issue_state == "closed":
            message += "状态: 已关闭\n"
        else:
            message += "状态: 开放中\n"

        # 显示标签（如果有）
        if label_names:
            message += f"标签: {', '.join(label_names)}\n"

        # 显示里程碑（如果有）
        if milestone_title != "无":
            message += f"里程碑: {milestone_title}\n"

        # 显示分配者（如果有）
        if assignee_names:
            message += f"分配给: {', '.join(assignee_names)}\n"

        # 添加链接
        message += f"链接: {issue_url}\n"

        # 添加内容预览（如果不是太长）
        if len(issue_body) > 200:
            issue_body = issue_body[:200] + "..."
        message += f"\n内容预览:\n{issue_body}\n"

        # 如果是特定动作，添加额外信息
        if action == "assigned":
            assignee = body.get("assignee", {})
            assignee_name = assignee.get("login", "Unknown") if assignee else "Unknown"
            message += f"分配给: {assignee_name}\n"
        elif action == "labeled":
            label = body.get("label", {})
            label_name = label.get("name", "Unknown") if label else "Unknown"
            message += f"添加标签: {label_name}\n"

        # 向所有订阅的频道发送消息
        await send_to_subscribers(repo_full_name, "issues", message)

    except Exception as e:
        core.logger.error(f"处理GitHub Issues事件失败: {e!s}")


async def _handle_pull_request_event(repo_full_name: str, body: Dict) -> None:
    """处理GitHub Pull Request事件 - 深度增强版

    增强点:
    1. 分支流向明确化: [目标分支 <- 来源分支] 格式
    2. 变更规模可视化: +additions/-deletions 紧凑格式
    3. 状态标签增强: 使用emoji和明确的中文状态描述
    4. 元数据补充: Commit数量、Labels标签
    5. 结构优化: 更符合中文阅读习惯的排版

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
        pr_merged = pr.get("merged", False)
        pr_state = pr.get("state", "unknown")

        # 提取PR创建者信息
        pr_creator = pr.get("user", {})
        pr_creator_name = pr_creator.get("login", "Unknown")

        # 提取合并者信息（如果已合并）
        merged_by = pr.get("merged_by", {})
        merged_by_name = merged_by.get("login", "Unknown") if merged_by else "Unknown"

        # 提取分支信息
        head_branch = pr.get("head", {}).get("ref", "unknown")
        base_branch = pr.get("base", {}).get("ref", "unknown")

        # 提取分支所属者信息
        head_repo = pr.get("head", {}).get("repo", {})
        head_repo_owner = head_repo.get("owner", {}).get("login", "Unknown") if head_repo else "Unknown"
        base_repo = pr.get("base", {}).get("repo", {})
        base_repo_owner = base_repo.get("owner", {}).get("login", "Unknown") if base_repo else "Unknown"

        # 提取代码变更统计
        additions = pr.get("additions", 0)
        deletions = pr.get("deletions", 0)
        changed_files = pr.get("changed_files", 0)

        # 提取Commit数量
        commits_count = pr.get("commits", 0)

        # 提取Labels标签
        labels = pr.get("labels", [])
        label_names = [label.get("name", "") for label in labels if label.get("name")]

        # 格式化消息 - 使用更清晰的结构和中文阅读习惯
        message = f"📢 GitHub Pull Request #{pr_number}\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n"

        # 第一行: 状态和动作标签（最显眼的位置）
        # 注意: GitHub的action字段在closed时不会区分merged/unmerged，需要手动判断
        if action == "closed":
            if pr_merged:
                action_display = "✅ 已合并"
                action_detail = f"由 {merged_by_name} 执行合并"
            else:
                action_display = "❌ 已关闭(未合入)"
                action_detail = "PR被关闭，代码未进入目标分支"
        elif action == "opened":
            action_display = "🆕 新建"
            action_detail = f"由 {pr_creator_name} 发起"
        elif action == "reopened":
            action_display = "🔄 重新开启"
            action_detail = f"由 {pr_creator_name} 重新打开"
        else:
            action_display = f"📝 {action}"
            action_detail = "PR状态变更"

        message += f"【{action_display}】{action_detail}\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n"

        # PR标题和链接
        message += f"📌 {pr_title}\n"
        message += f"🔗 {pr_url}\n"

        # 分支流向: 明确显示 [目标分支 <- 来源分支]
        # 格式: [base_repo:base_branch] <- [head_repo:head_branch]
        # 这种格式让Agent一眼看出代码流向
        if head_repo_owner == base_repo_owner:
            # 同仓库PR，简化显示
            branch_flow = f"[{base_branch}] <- [{head_branch}]"
        else:
            # 跨仓库PR，显示完整信息
            branch_flow = f"[{base_repo_owner}:{base_branch}] <- [{head_repo_owner}:{head_branch}]"
        message += f"🌿 {branch_flow}\n"

        # 代码变更统计: 使用 +123/-45 的紧凑可视化格式
        # 绿色 additions 在前，红色 deletions 在后，符合GitHub习惯
        message += f"📊 变更: +{additions}/-{deletions} ({changed_files} 个文件)"
        if commits_count > 0:
            message += f" | {commits_count} 个提交"
        message += "\n"

        # Labels标签（如果有）
        if label_names:
            labels_str = ", ".join(label_names[:5])  # 最多显示5个标签
            if len(label_names) > 5:
                labels_str += f" 等{len(label_names)}个标签"
            message += f"🏷️ 标签: {labels_str}\n"

        # 创建者信息（如果不是创建动作，补充显示）
        if action not in ["opened", "reopened"]:
            message += f"👤 创建者: {pr_creator_name}\n"

        # 内容预览（如果不是太长）
        if pr_body and pr_body != "无内容":
            if len(pr_body) > 150:
                pr_body = pr_body[:150] + "..."
            message += f"━━━━━━━━━━━━━━━━━━━━\n"
            message += f"📝 内容:\n{pr_body}\n"

        # 合并相关信息（仅当合并时显示）
        if pr_merged:
            merge_commit_sha = pr.get("merge_commit_sha", "")
            if merge_commit_sha:
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += f"🔀 合并提交: {merge_commit_sha[:7]}\n"

        # 向所有订阅的频道发送消息
        await send_to_subscribers(repo_full_name, "pull_request", message)

    except Exception as e:
        core.logger.error(f"处理GitHub Pull Request事件失败: {e!s}")


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
        release_name = release.get("name", tag_name) or tag_name
        release_body = release.get("body", "无内容") or "无内容"
        release_url = release.get("html_url", "")
        is_prerelease = release.get("prerelease", False)
        is_draft = release.get("draft", False)

        # 提取发布者信息
        author = release.get("author", {})
        author_name = author.get("login", "Unknown") if author else "Unknown"

        # 提取资源文件信息
        assets = release.get("assets", [])
        asset_count = len(assets)

        # 提取目标提交信息
        target_commitish = release.get("target_commitish", "")

        # 格式化消息
        message = "📢 GitHub Release 事件\n\n"
        message += f"仓库: {repo_full_name}\n"
        message += f"动作: {action}\n"
        message += f"版本: {release_name} ({tag_name})\n"
        message += f"发布者: {author_name}\n"

        # 显示发布状态
        if is_draft:
            message += "状态: 草稿\n"
        elif is_prerelease:
            message += "状态: 预发布版本\n"
        else:
            message += "状态: 正式发布\n"

        # 显示目标分支/提交
        if target_commitish:
            message += f"目标: {target_commitish}\n"

        # 显示资源文件信息
        if asset_count > 0:
            message += f"资源文件数: {asset_count}\n"

        # 添加链接
        message += f"链接: {release_url}\n"

        # 显示资源文件列表（如果有）
        if assets:
            message += "\n资源文件列表:\n"
            for _i, asset in enumerate(assets[:3]):  # 最多显示3个资源文件
                asset_name = asset.get("name", "未命名")
                asset_size = asset.get("size", 0)

                # 格式化文件大小
                size_str = "未知"
                if asset_size:
                    if asset_size < 1024:
                        size_str = f"{asset_size} B"
                    elif asset_size < 1024 * 1024:
                        size_str = f"{asset_size / 1024:.1f} KB"
                    else:
                        size_str = f"{asset_size / (1024 * 1024):.1f} MB"

                message += f"{asset_name} ({size_str})\n"

        # 添加内容预览（如果不是太长）
        if len(release_body) > 200:
            release_body = release_body[:200] + "..."
        message += f"\n发布说明:\n{release_body}\n"

        # 向所有订阅的频道发送消息
        await send_to_subscribers(repo_full_name, "release", message)

    except Exception as e:
        core.logger.error(f"处理GitHub Release事件失败: {e!s}")


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

        # 提取仓库信息
        repository = body.get("repository", {})
        star_count = repository.get("stargazers_count", 0)
        fork_count = repository.get("forks_count", 0)
        repo_description = repository.get("description", "无描述") or "无描述"
        repo_language = repository.get("language", "未知")
        repo_owner = repository.get("owner", {}).get("login", "Unknown")

        # 格式化消息
        message = "📢 GitHub Star 事件\n\n"
        message += f"仓库: {repo_full_name}\n"
        message += f"用户: {user_name}\n"
        message += f"动作: {'添加了star' if action == 'created' else '移除了star'}\n"
        message += f"当前star数: {star_count}\n"

        # 添加仓库基本信息
        if len(repo_description) > 50:
            repo_description = repo_description[:50] + "..."
        message += f"描述: {repo_description}\n"
        message += f"所有者: {repo_owner}\n"

        if repo_language:
            message += f"主要语言: {repo_language}\n"

        # 添加仓库统计信息
        message += f"Fork数: {fork_count}\n"

        # 如果是添加star，添加简短祝贺信息
        if action == "created" and (star_count == 1 or star_count % 100 == 0):
            message += f"恭喜！仓库达到了 {star_count} 个star！\n"

        # 向所有订阅的频道发送消息
        await send_to_subscribers(repo_full_name, "star", message)

    except Exception as e:
        core.logger.error(f"处理GitHub Star事件失败: {e!s}")


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
        message = f"📢 GitHub {event_type.title()} 事件\n\n"
        message += f"仓库: {repo_full_name}\n"
        message += f"用户: {user_name}\n"
        if action:
            message += f"动作: {action}\n"

        # 根据不同的事件类型添加特定信息
        if event_type == "fork":
            # Fork事件
            forkee = body.get("forkee", {})
            fork_full_name = forkee.get("full_name", "unknown/unknown")
            fork_url = forkee.get("html_url", "")

            message += f"Fork目标: {fork_full_name}\n"
            message += f"Fork链接: {fork_url}\n"

        elif event_type == "workflow_run":
            # Workflow运行事件
            workflow_run = body.get("workflow_run", {})
            workflow_name = workflow_run.get("name", "未知工作流")
            workflow_status = workflow_run.get("status", "unknown")
            workflow_conclusion = workflow_run.get("conclusion", "unknown")
            workflow_url = workflow_run.get("html_url", "")
            run_number = workflow_run.get("run_number", "")
            run_attempt = workflow_run.get("run_attempt", 1)

            # 获取工作流触发事件
            workflow_trigger = workflow_run.get("event", "unknown")

            # 获取工作流相关分支/标签
            head_branch = workflow_run.get("head_branch", "")
            head_sha = workflow_run.get("head_sha", "")[:7] if workflow_run.get("head_sha") else ""

            message += f"工作流: {workflow_name}\n"
            if run_number:
                message += f"运行编号: #{run_number}"
                if run_attempt > 1:
                    message += f" (第{run_attempt}次尝试)"
                message += "\n"

            if head_branch:
                message += f"分支: {head_branch}"
                if head_sha:
                    message += f" ({head_sha})"
                message += "\n"

            if workflow_trigger:
                message += f"触发事件: {workflow_trigger}\n"

            message += f"状态: {workflow_status}\n"

            # 特别处理工作流结果，尤其是失败情况
            if workflow_conclusion:
                if workflow_conclusion == "success":
                    message += "结果: 成功\n"
                elif workflow_conclusion == "failure":
                    message += "结果: 失败\n"
                    # 添加更多失败相关信息
                    jobs_url = workflow_run.get("jobs_url", "")
                    if jobs_url:
                        message += f"查看失败详情: {jobs_url}\n"
                elif workflow_conclusion == "cancelled":
                    message += "结果: 已取消\n"
                elif workflow_conclusion == "skipped":
                    message += "结果: 已跳过\n"
                elif workflow_conclusion == "timed_out":
                    message += "结果: 超时\n"
                else:
                    message += f"结果: {workflow_conclusion}\n"

            # 添加工作流链接
            if workflow_url:
                message += f"链接: {workflow_url}\n"

            # 如果工作流失败，添加特别提示
            if workflow_conclusion in ["failure", "timed_out"]:
                message += "\n⚠️ 工作流执行失败，请检查日志了解详情\n"

        elif event_type == "workflow_job":
            # 工作流作业事件
            action = body.get("action", "unknown")
            workflow_job = body.get("workflow_job", {})
            job_name = workflow_job.get("name", "未知作业")
            job_status = workflow_job.get("status", "unknown")
            job_conclusion = workflow_job.get("conclusion", "unknown")
            job_url = workflow_job.get("html_url", "")

            # 获取作业步骤信息
            steps = workflow_job.get("steps", [])
            failed_steps = [step for step in steps if step.get("conclusion") == "failure"]

            # 获取运行器信息
            runner_name = workflow_job.get("runner_name", "")
            runner_group_name = workflow_job.get("runner_group_name", "")

            # 获取工作流相关信息
            run_url = workflow_job.get("run_url", "")

            message += f"作业: {job_name}\n"
            message += f"状态: {job_status}\n"

            if job_conclusion:
                if job_conclusion == "success":
                    message += "结果: 成功\n"
                elif job_conclusion == "failure":
                    message += "结果: 失败\n"
                elif job_conclusion == "cancelled":
                    message += "结果: 已取消\n"
                elif job_conclusion == "skipped":
                    message += "结果: 已跳过\n"
                else:
                    message += f"结果: {job_conclusion}\n"

            if runner_name:
                message += f"运行器: {runner_name}"
                if runner_group_name:
                    message += f" ({runner_group_name})"
                message += "\n"

            # 如果作业失败，显示失败的步骤
            if failed_steps and job_conclusion == "failure":
                message += "\n失败步骤:\n"
                for step in failed_steps[:3]:  # 最多显示3个失败步骤
                    step_name = step.get("name", "未知步骤")
                    message += f"- {step_name}\n"

                if len(failed_steps) > 3:
                    message += f"...还有 {len(failed_steps) - 3} 个失败步骤\n"

            # 添加作业链接
            if job_url:
                message += f"作业链接: {job_url}\n"

            # 添加工作流运行链接
            if run_url:
                message += f"工作流链接: {run_url}\n"

        elif event_type == "check_run" or event_type == "check_suite":
            # 检查运行/检查套件事件
            check_obj = body.get("check_run", {}) if event_type == "check_run" else body.get("check_suite", {})
            check_name = check_obj.get("name", "未知检查")
            check_status = check_obj.get("status", "unknown")
            check_conclusion = check_obj.get("conclusion", "unknown")
            check_url = check_obj.get("html_url", "")

            message += f"检查: {check_name}\n"
            message += f"状态: {check_status}\n"

            if check_conclusion:
                if check_conclusion == "success":
                    message += "结果: 成功\n"
                elif check_conclusion == "failure":
                    message += "结果: 失败\n"
                elif check_conclusion == "neutral":
                    message += "结果: 中立\n"
                elif check_conclusion == "cancelled":
                    message += "结果: 已取消\n"
                elif check_conclusion == "skipped":
                    message += "结果: 已跳过\n"
                elif check_conclusion == "timed_out":
                    message += "结果: 超时\n"
                else:
                    message += f"结果: {check_conclusion}\n"

            # 添加检查链接
            if check_url:
                message += f"链接: {check_url}\n"

            # 如果检查失败，添加特别提示
            if check_conclusion in ["failure", "timed_out"]:
                message += "\n检查未通过，请查看详情\n"

        elif event_type == "create" or event_type == "delete":
            # 创建/删除分支或标签
            ref_type = body.get("ref_type", "unknown")
            ref = body.get("ref", "unknown")

            message += f"类型: {ref_type}\n"
            message += f"引用: {ref}\n"

        elif event_type == "issue_comment":
            # Issue评论
            issue = body.get("issue", {})
            issue_number = issue.get("number", "?")
            issue_title = issue.get("title", "无标题")

            comment = body.get("comment", {})
            comment_body = comment.get("body", "无内容") or "无内容"

            message += f"Issue #{issue_number}: {issue_title}\n"

            if len(comment_body) > 200:
                comment_body = comment_body[:200] + "..."
            message += f"\n评论内容:\n{comment_body}\n"

        elif event_type == "pull_request_review" or event_type == "pull_request_review_comment":
            # PR审核或PR审核评论
            pr = body.get("pull_request", {})
            pr_number = pr.get("number", "?")
            pr_title = pr.get("title", "无标题")

            review = body.get("review", {})
            review_state = review.get("state", "unknown") if review else "unknown"

            comment = body.get("comment", {})
            comment_body = comment.get("body", "") if comment else ""

            message += f"PR #{pr_number}: {pr_title}\n"

            if review_state:
                message += f"审核状态: {review_state}\n"

            # 显示评论内容
            if comment_body:
                if len(comment_body) > 200:
                    comment_body = comment_body[:200] + "..."
                message += f"\n评论内容:\n{comment_body}\n"

        elif "comment" in event_type and "comment" in body:
            # 通用评论处理
            comment = body.get("comment", {})
            comment_body = comment.get("body", "无内容") or "无内容"

            if len(comment_body) > 200:
                comment_body = comment_body[:200] + "..."
            message += f"\n评论内容:\n{comment_body}\n"

        elif event_type == "gollum":
            # Wiki页面更新
            pages = body.get("pages", [])
            page_count = len(pages)

            message += f"Wiki更新: 共 {page_count} 个页面\n"

            for _i, page in enumerate(pages[:3]):  # 最多显示3个页面
                page_name = page.get("title", "未命名")
                page_action = page.get("action", "unknown")

                message += f"{page_name} ({page_action})\n"

        elif event_type == "member":
            # 仓库成员变更
            member = body.get("member", {})
            member_name = member.get("login", "Unknown")

            message += f"成员: {member_name}\n"

            if action == "added":
                message += "已添加为仓库协作者\n"
            elif action == "removed":
                message += "已从仓库协作者中移除\n"
            elif action == "edited":
                message += "权限已编辑\n"

        # 向所有订阅的频道发送消息
        await send_to_subscribers(repo_full_name, event_type, message)

    except Exception as e:
        core.logger.error(f"处理GitHub {event_type} 事件失败: {e!s}")


async def send_to_subscribers(repo_name: str, event_type: str, message: str):
    """向所有订阅的频道发送消息

    Args:
        repo_name: 仓库名称
        event_type: 事件类型
        message: 要发送的消息
    """
    # 获取所有聊天频道
    from nekro_agent.models.db_chat_channel import DBChatChannel

    chat_channels = await DBChatChannel.all()

    message += "\n\n[Attention] This message is visible for you only. Transfer to the chat channel to make other users see it."

    # 遍历所有频道，查找订阅了该仓库的频道
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
                core.logger.info(f"已向频道 {chat_key} 推送 {repo_name} 的 {event_type} 事件")
            except Exception as e:
                core.logger.error(f"向频道 {chat_key} 推送消息失败: {e!s}")

    core.logger.info(f"共向 {sent_count} 个频道推送了 {repo_name} 的 {event_type} 事件")
