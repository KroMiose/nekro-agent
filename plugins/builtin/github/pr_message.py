from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class PullRequestEventSummary:
    repo_full_name: str
    pr_number: str
    title: str
    url: str
    headline: str
    detail: str
    branch_flow: str
    creator_name: str
    actor_name: str
    additions: int
    deletions: int
    changed_files: int
    commits_count: int
    labels: list[str] = field(default_factory=list)
    extra_lines: list[str] = field(default_factory=list)
    body_preview: str | None = None
    merge_commit_sha: str | None = None


def build_pull_request_event_summary(repo_full_name: str, body: Mapping[str, Any]) -> PullRequestEventSummary:
    action = _get_str(body, "action", default="unknown")
    pr = _get_mapping(body, "pull_request")
    sender = _get_mapping(body, "sender")

    pr_number = _get_str(pr, "number", default="?")
    title = _get_str(pr, "title", default="无标题")
    url = _get_str(pr, "html_url")
    creator_name = _get_nested_str(pr, "user", "login", default="Unknown")
    actor_name = _get_str(sender, "login", default=creator_name)

    head_branch = _get_nested_str(pr, "head", "ref", default="unknown")
    base_branch = _get_nested_str(pr, "base", "ref", default="unknown")
    head_owner = _get_nested_str(pr, "head", "repo", "owner", "login", default="Unknown")
    base_owner = _get_nested_str(pr, "base", "repo", "owner", "login", default="Unknown")

    additions = _get_int(pr, "additions")
    deletions = _get_int(pr, "deletions")
    changed_files = _get_int(pr, "changed_files")
    commits_count = _get_int(pr, "commits")
    labels = _extract_label_names(pr)
    body_preview = _build_body_preview(_get_str(pr, "body"))
    merge_commit_sha = _short_sha(_get_str(pr, "merge_commit_sha")) or None

    headline, detail, extra_lines = _describe_pull_request_action(action=action, pr=pr, body=body, actor_name=actor_name)

    return PullRequestEventSummary(
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        title=title,
        url=url,
        headline=headline,
        detail=detail,
        branch_flow=_build_branch_flow(base_owner, base_branch, head_owner, head_branch),
        creator_name=creator_name,
        actor_name=actor_name,
        additions=additions,
        deletions=deletions,
        changed_files=changed_files,
        commits_count=commits_count,
        labels=labels,
        extra_lines=extra_lines,
        body_preview=body_preview,
        merge_commit_sha=merge_commit_sha,
    )


def render_pull_request_event_message(summary: PullRequestEventSummary) -> str:
    lines = [
        f"📢 GitHub Pull Request #{summary.pr_number} @ {summary.repo_full_name}",
        f"【{summary.headline}】{summary.detail}",
        f"📌 {summary.title}",
    ]
    if summary.url:
        lines.append(f"🔗 {summary.url}")
    lines.append(f"🌿 {summary.branch_flow}")

    stats_line = f"📊 变更: +{summary.additions}/-{summary.deletions} ({summary.changed_files} 个文件)"
    if summary.commits_count > 0:
        stats_line += f" | {summary.commits_count} 个提交"
    lines.append(stats_line)

    if summary.labels:
        labels_preview = "，".join(summary.labels[:5])
        if len(summary.labels) > 5:
            labels_preview += f" 等 {len(summary.labels)} 个标签"
        lines.append(f"🏷️ 标签: {labels_preview}")

    lines.append(f"👤 发起者: {summary.creator_name}")
    if summary.actor_name != summary.creator_name:
        lines.append(f"👤 操作者: {summary.actor_name}")

    lines.extend(f"ℹ️ {line}" for line in summary.extra_lines)

    if summary.body_preview:
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("📝 内容预览:")
        lines.append(summary.body_preview)

    if summary.merge_commit_sha:
        lines.append(f"🔀 合并提交: {summary.merge_commit_sha}")

    return "\n".join(lines)


def _describe_pull_request_action(
    *,
    action: str,
    pr: Mapping[str, Any],
    body: Mapping[str, Any],
    actor_name: str,
) -> tuple[str, str, list[str]]:
    merged = bool(pr.get("merged", False))
    merged_by_name = _get_nested_str(pr, "merged_by", "login")
    extra_lines: list[str] = []

    if action == "closed":
        if merged:
            return "✅ 已合并", f"由 {merged_by_name or actor_name} 合并", extra_lines
        return "❌ 已关闭", f"由 {actor_name} 关闭，未合入目标分支", extra_lines

    if action == "opened":
        return "🆕 新建", f"由 {actor_name} 发起", extra_lines

    if action == "reopened":
        return "🔄 重新开启", f"由 {actor_name} 重新打开", extra_lines

    if action == "synchronize":
        head_sha = _short_sha(_get_nested_str(pr, "head", "sha"))
        if head_sha:
            extra_lines.append(f"最新提交: {head_sha}")
        return "🔁 提交更新", f"由 {actor_name} 推送了新的提交", extra_lines

    if action == "ready_for_review":
        return "👀 待审查", f"由 {actor_name} 标记为可审查", extra_lines

    if action == "converted_to_draft":
        return "📝 草稿", f"由 {actor_name} 转为 Draft", extra_lines

    if action == "review_requested":
        reviewer = _get_nested_str(body, "requested_reviewer", "login")
        requested_team = _get_nested_str(body, "requested_team", "name")
        if reviewer:
            extra_lines.append(f"请求审查人: {reviewer}")
        elif requested_team:
            extra_lines.append(f"请求审查团队: {requested_team}")
        return "🙋 请求审查", f"由 {actor_name} 发起审查请求", extra_lines

    if action == "review_request_removed":
        reviewer = _get_nested_str(body, "requested_reviewer", "login")
        requested_team = _get_nested_str(body, "requested_team", "name")
        if reviewer:
            extra_lines.append(f"移除审查人: {reviewer}")
        elif requested_team:
            extra_lines.append(f"移除审查团队: {requested_team}")
        return "➖ 移除审查", f"由 {actor_name} 移除了审查请求", extra_lines

    if action in {"assigned", "unassigned"}:
        assignee = _get_nested_str(body, "assignee", "login")
        if assignee:
            prefix = "指派给" if action == "assigned" else "取消指派"
            extra_lines.append(f"{prefix}: {assignee}")
        headline = "👤 已指派" if action == "assigned" else "👤 取消指派"
        return headline, f"由 {actor_name} 更新了负责人", extra_lines

    if action in {"labeled", "unlabeled"}:
        label_name = _get_nested_str(body, "label", "name")
        if label_name:
            prefix = "新增标签" if action == "labeled" else "移除标签"
            extra_lines.append(f"{prefix}: {label_name}")
        return "🏷️ 标签变更", f"由 {actor_name} 更新了标签", extra_lines

    if action == "edited":
        changed_fields = sorted(_get_mapping(body, "changes").keys())
        if changed_fields:
            extra_lines.append(f"修改字段: {', '.join(changed_fields)}")
        return "✏️ 已编辑", f"由 {actor_name} 修改了 PR 信息", extra_lines

    if action in {"locked", "unlocked"}:
        headline = "🔒 已锁定" if action == "locked" else "🔓 已解锁"
        return headline, f"由 {actor_name} 更新了讨论状态", extra_lines

    if action in {"auto_merge_enabled", "auto_merge_disabled"}:
        headline = "🤖 自动合并已开启" if action == "auto_merge_enabled" else "🤖 自动合并已关闭"
        return headline, f"由 {actor_name} 更新了自动合并", extra_lines

    if action in {"enqueued", "dequeued"}:
        headline = "🚦 已加入合并队列" if action == "enqueued" else "🚦 已移出合并队列"
        reason = _get_str(body, "reason")
        if reason:
            extra_lines.append(f"原因: {reason}")
        return headline, f"由 {actor_name} 更新了合并队列状态", extra_lines

    return f"📝 {action}", f"由 {actor_name} 触发", extra_lines


def _build_branch_flow(base_owner: str, base_branch: str, head_owner: str, head_branch: str) -> str:
    if base_owner == head_owner:
        return f"[{base_branch}] <- [{head_branch}]"
    return f"[{base_owner}:{base_branch}] <- [{head_owner}:{head_branch}]"


def _extract_label_names(pr: Mapping[str, Any]) -> list[str]:
    labels = pr.get("labels", [])
    if not isinstance(labels, list):
        return []
    result: list[str] = []
    for label in labels:
        if isinstance(label, Mapping):
            name = label.get("name")
            if isinstance(name, str) and name.strip():
                result.append(name.strip())
    return result


def _build_body_preview(content: str) -> str | None:
    text = content.strip()
    if not text or text == "无内容":
        return None
    if len(text) > 180:
        return text[:180].rstrip() + "..."
    return text


def _short_sha(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    return cleaned[:7]


def _get_mapping(source: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = source.get(key)
    if isinstance(value, Mapping):
        return value
    return {}


def _get_nested_str(source: Mapping[str, Any], *keys: str, default: str = "") -> str:
    current: Any = source
    for key in keys:
        if not isinstance(current, Mapping):
            return default
        current = current.get(key)
    if isinstance(current, str):
        return current
    if isinstance(current, int):
        return str(current)
    return default


def _get_str(source: Mapping[str, Any], key: str, default: str = "") -> str:
    value = source.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return default


def _get_int(source: Mapping[str, Any], key: str) -> int:
    value = source.get(key)
    return value if isinstance(value, int) else 0
