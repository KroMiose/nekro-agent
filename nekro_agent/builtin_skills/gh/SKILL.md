---
name: gh
description: 使用此技能进行 GitHub CLI 操作，包括 PR 审阅、Issue 管理、仓库操作、CI/CD 监控和 GitHub API 调用。
version: 2.0.0
allowed-tools: Read,Bash
---

# GitHub CLI (gh) 使用指南

> **环境提示**：`gh` 已在 nekro-cc-sandbox 中预装。如遇"命令未找到"错误，请读取本技能目录下的 `install.md`。

## 认证

```bash
# 环境变量认证（推荐，适合自动化场景）
export GH_TOKEN="your_github_personal_access_token"
# 或
export GITHUB_TOKEN="your_token"

# 检查当前认证状态
gh auth status
```

## PR 操作

```bash
gh pr list                              # 列出所有 PR
gh pr view <number>                     # 查看 PR 详情
gh pr checkout <number>                 # 检出 PR 分支
gh pr create                            # 交互式创建 PR
gh pr create --title "标题" --body "描述"  # 非交互创建
gh pr merge <number>                    # 合并 PR
gh pr review <number> --approve         # 批准 PR
gh pr review <number> --request-changes -b "原因"  # 要求修改
```

## Issue 操作

```bash
gh issue list                           # 列出 Issue
gh issue list --assignee @me            # 查看分配给我的
gh issue view <number>                  # 查看详情
gh issue create --title "标题" --body "内容"  # 创建 Issue
gh issue close <number>                 # 关闭 Issue
```

## 仓库操作

```bash
gh repo view                            # 查看当前仓库信息
gh repo view <owner>/<repo>             # 查看指定仓库
gh repo clone <repo>                    # 克隆仓库
gh repo fork                            # Fork 仓库
```

## CI/CD 操作

```bash
gh run list                             # 列出运行记录
gh run view <id>                        # 查看运行详情
gh run watch <id>                       # 实时监控运行
gh workflow list                        # 列出 workflow
gh workflow run <name>                  # 手动触发 workflow
```

## API 调用

```bash
# GET 请求
gh api repos/{owner}/{repo}
gh api user/repos --jq '.[].name'

# POST 请求
gh api repos/{owner}/{repo}/issues -f title="Bug" -f body="描述"

# GraphQL
gh api graphql -f query='query { viewer { login } }'

# 自动分页获取全部数据
gh api user/repos --paginate --jq '.[].name'
```

## 输出格式

```bash
gh repo view --json name,owner,description      # 指定 JSON 字段
gh pr list --jq '.[].number'                   # jq 过滤
gh api user/repos --jq '.[] | select(.fork == false) | .name'  # 条件过滤
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| 未认证 | 设置 `GH_TOKEN` 或 `GITHUB_TOKEN` 环境变量 |
| 找不到仓库 | 确保当前目录是 git 仓库，或设置 `GH_REPO=owner/repo` |
| API 限流 | 认证后提高限额，使用 `--paginate` 避免重复调用 |
| 权限错误 | 检查 PAT 权限范围（repo、workflow、read:org 等） |
