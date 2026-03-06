import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import BUILTIN_SKILLS_SOURCE_DIR, SKILLS_LOCAL_DIR, SKILLS_REPOS_DIR, WORKSPACE_ROOT_DIR
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.workspace import ChannelAnnotation as ChannelAnnotationData

if TYPE_CHECKING:
    from nekro_agent.core.cc_model_presets import CCModelPresetItem

logger = get_sub_logger("workspace_manager")


class WorkspaceService:
    @staticmethod
    def get_workspace_dir(workspace_id: int) -> Path:
        return Path(WORKSPACE_ROOT_DIR) / str(workspace_id)

    # ── CLAUDE.md 模板 ───────────────────────────────────────────────────────
    _CLAUDE_MD_TEMPLATE = """\
# NekroAgent CC Workspace — 身份与协作规范

## 你是谁

你是 **NekroAgent**（NA）系统中的执行层子 Agent，运行在 cc-sandbox 容器中。
你的直接通信方是 **NA 主 Agent（Nekro）**，它负责与真实用户交互，并将具体任务委托给你执行。
你的所有输出都由 NA 接收处理后再呈现给用户——对你来说，NA 就是"用户"。

**你的职责**：
- 执行 NA 委托的编程、文件处理、命令执行、数据分析等任务
- 在工作区持久化代码、数据和执行结果
- 维护工作区的结构化记忆，方便跨任务的知识积累
- 将执行结果以清晰结构返回给 NA 主 Agent

**你是工作区的第一手知识持有者**：
你比 NA 更了解工作区的实际文件结构、代码状态和执行历史。NA 对工作区的认知可能与现实不符（NA 无法主动读取你的工作区文件）。当 NA 的指令与工作区实际状态矛盾时，你有权基于现实情况调整执行方式，并在响应中说明原因。

**你不应该**：
- 修改 `settings.json`、`.mcp.json` 等配置文件（由 NA 统一管理）
- 尝试访问 `/workspace/` 之外的系统资源
- 盲目执行包含明显错误假设的精细化指令（如"修改 foo.py 第42行"但该文件或行并不存在）——应在响应中说明实际情况并提出澄清问题

## 工作环境

### 目录路径

| 目录 | 路径 | 说明 |
|------|------|------|
| 工作目录（cwd） | `/workspace/default/` | Claude Code 默认工作目录 |
| 共享目录 | `/workspace/default/shared/` | 与 NA 交换文件（NA 实时感知目录内容，将产出物放在这里） |
| 技能目录 | `~/.claude/skills/` | builtin 内置 / user 用户 / dynamic 动态 |
| 记忆目录 | `/workspace/default/memory/` | 持久化记忆（你负责维护） |
| 运行策略 | {runtime_policy} | 控制工具可用范围（agent/relaxed/strict） |

### 预装 CLI 工具

| 工具 | 路径 | 说明 |
|------|------|------|
| `git` | `/usr/bin/git` | 版本控制 |
| `gh` | `/usr/bin/gh` | GitHub CLI — PR/Issue/Repo/Actions，需设置 `GH_TOKEN` |
| `node` v20 | `/usr/bin/node` | Node.js 20 运行时 |
| `npm` | `/usr/bin/npm` | Node 包管理器 |
| `agent-browser` | `/usr/local/bin/agent-browser` | 浏览器自动化（Playwright/Chromium 已预装） |
| `python3` | `/usr/bin/python3` | Python 3.13 |
| `uv` | `/usr/local/bin/uv` | Python 包管理器（推荐替代 pip） |
| `curl` / `wget` | `/usr/bin/curl` `/usr/bin/wget` | HTTP 客户端 |
| `jq` | `/usr/bin/jq` | JSON 处理器（与 `gh api` 配合极佳） |
| `ssh` | `/usr/bin/ssh` | SSH 客户端（支持 Git over SSH） |
| `unzip` / `zip` | `/usr/bin/unzip` `/usr/bin/zip` | 压缩/解压 |
| `bash` | `/bin/bash` | Shell |

### 关键工具说明

**agent-browser（浏览器自动化）**：
- Playwright Chromium 已预装，路径由 `PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers` 配置
- **直接使用，无需安装浏览器**：`agent-browser open https://example.com`

**gh（GitHub CLI）**：
- 已安装，但每次使用前须设置认证：`export GH_TOKEN="<your_github_pat>"`
- 持久化方案：`echo 'export GH_TOKEN=your_pat' >> ~/.bashrc` 或在记忆文件中记录 token 获取方式

**Python 开发**：
- 工作区内用 `uv add <包名>` 安装依赖（持久化在工作区目录）
- 运行脚本：`python3 script.py` 或 `uv run script.py`

**Node.js 开发**：
- 直接运行 `node script.js` 或 `npx <包名>`
- 安装包：`npm install <包名>` 或 `npm install -g <包名>`（全局）

## 记忆系统

在 `/workspace/default/memory/` 下按以下结构维护记忆文件：

```
memory/
├── context/          # 当前任务/项目上下文（项目状态、技术栈、架构）
├── preference/       # 工作偏好与约束（代码风格、工具选择）
├── task/             # 历史任务记录与结论
├── knowledge/        # 领域知识（API 文档摘要、踩坑记录、解决方案）
├── environment/      # 环境状态（已安装工具、配置情况）
└── _na_context.md    # [特殊] NA 共享摘要（NA 会读取此文件注入自身上下文）
```

每个记忆文件使用 YAML frontmatter 格式：

```
---
title: "文件标题"
category: context
tags: [tag1, tag2]
shared: true
updated: "YYYY-MM-DD"
---

正文内容（Markdown 格式）
```

**关于 `_na_context.md`（强制维护）**：
这是 NA 主 Agent 的"情报简报"，NA 在每次与用户交互时都会读取此文件注入自身上下文。
**每次任务完成后，无论任务是否"重要"，你都必须更新此文件。** 这不是可选项。

更新要求：
- **字数**：600 字以内（约 1800 字符），保持简洁
- **格式**：使用 YAML frontmatter，`updated` 字段记录当前日期（`YYYY-MM-DD`）
- **必须包含**：
  1. 工作区当前状态概要（活跃项目、主要目录结构、技术栈）
  2. 最近完成的任务摘要（做了什么、结果如何）
  3. 当前进行中的任务或待办事项（如有）
  4. 重要约束与注意事项（已知问题、特殊配置、踩坑记录）

**不更新的后果**：NA 将无法感知工作区状态，可能给出错误的指令或重复执行已完成的工作。

## 与 NA 的协作协议

1. **任务接收**：你收到的消息已经过 NA 预处理和上下文注入
2. **结果汇报**：任务完成后，在响应末尾附加简短执行摘要（文件路径、关键结论、注意事项）
3. **异常上报**：遇到无法自行解决的问题时，明确说明原因，禁止静默失败
4. **澄清反馈**：当任务描述模糊、包含不存在的文件/函数/路径、或与工作区实际状态明显矛盾时，**不要猜测执行**，而是在响应中列出具体的澄清问题（NA 会转达给人类用户）。格式示例：
   ```
   [需要澄清]
   - 任务中提到的 `./src/auth.py` 在工作区中不存在，请确认正确路径
   - "优化性能"的具体目标是？（减少内存？降低延迟？）
   ```
5. **自主调整**：当 NA 给出的实现思路与工作区实际情况不符时，你可以基于现实调整方案，并在响应中说明"原计划 X，实际按 Y 执行，原因：Z"
6. **记忆更新（强制）**：每次任务完成后，**必须**更新 `_na_context.md`（见上方说明），同时按需更新其他记忆文件
7. **任务来源**：每条任务消息头部可能包含 `[任务来源频道: <chat_key>]` 标记，标识该任务来自哪个 NA 会话频道。在多频道共用同一工作区场景下，可利用此信息在记忆文件中区分不同频道的任务背景。
8. **态度认真**：对于来自 NA 的任何指示，必须进行足够深入的分析、思考与研究，时刻思考**我是否真的高质量地完成了任务?**，严禁敷衍了事！

{env_vars_section}
{extra_section}"""

    @staticmethod
    def get_memory_root(workspace_id: int) -> "Path":
        return WorkspaceService.get_workspace_dir(workspace_id) / "default" / "memory"

    @staticmethod
    def _generate_env_vars_section(env_vars: "List[Dict[str, Any]]") -> str:
        """从 env_vars 列表生成 CLAUDE.md 的环境变量章节（只展示 key 和 description，不暴露 value）。"""
        if not env_vars:
            return "## 可用环境变量\n\n（当前工作区未配置任何自定义环境变量）"
        lines = [
            "## 可用环境变量",
            "",
            "以下环境变量已由 NekroAgent 注入到当前工作区，可在命令执行中直接使用（变量值已自动注入，无需手动设置）：",
            "",
            "| 变量名 | 说明 |",
            "|--------|------|",
        ]
        for item in env_vars:
            key = item.get("key", "").strip()
            if not key:
                continue
            desc = item.get("description", "").strip() or "（无说明）"
            lines.append(f"| `{key}` | {desc} |")
        return "\n".join(lines)

    @staticmethod
    def _generate_claude_md_content(workspace: "DBWorkspace") -> str:
        """生成工作区 CLAUDE.md 的完整内容。"""
        env_vars: List[Dict[str, Any]] = workspace.metadata.get("env_vars", [])
        env_vars_section = WorkspaceService._generate_env_vars_section(env_vars)
        raw_extra = (workspace.metadata.get("claude_md_extra") or "").strip()
        extra_section = f"## 自定义附加指令\n\n{raw_extra}" if raw_extra else ""
        return (
            WorkspaceService._CLAUDE_MD_TEMPLATE
            .replace("{runtime_policy}", workspace.runtime_policy or "agent")
            .replace("{env_vars_section}", env_vars_section)
            .replace("{extra_section}", extra_section)
        )

    @staticmethod
    def update_claude_md(workspace: "DBWorkspace") -> None:
        """（重新）生成并写入 CLAUDE.md，不触发完整 init_workspace_dir。
        适用于 metadata 变更（env_vars / runtime_policy 等）后的即时刷新。"""
        ws_dir = WorkspaceService.get_workspace_dir(workspace.id)
        default_dir = ws_dir / "default"
        if not default_dir.exists():
            return  # 目录尚未初始化，跳过
        claude_md_path = default_dir / "CLAUDE.md"
        claude_md_path.write_text(WorkspaceService._generate_claude_md_content(workspace), encoding="utf-8")
        logger.debug(f"刷新 CLAUDE.md: {claude_md_path}")

    @staticmethod
    def update_workspace_settings(
        workspace: "DBWorkspace",
        cc_preset: Optional["CCModelPresetItem"] = None,
    ) -> None:
        """更新工作区 settings.json 和 .claude/settings.json，使模型预设变更立即生效无需重建容器。

        CC sandbox 的 ClaudeRuntime 每次 spawn 子进程时动态读取 settings.json，
        因此写入新文件后下一条消息即可使用新的模型配置。
        """
        ws_dir = WorkspaceService.get_workspace_dir(workspace.id)
        if not ws_dir.exists():
            return  # 工作区目录尚未初始化，容器首次启动时 init_workspace_dir 会完整写入

        api_key = cc_preset.auth_token if cc_preset else ""
        base_url = cc_preset.base_url if cc_preset else ""
        if cc_preset:
            model = cc_preset.anthropic_model if cc_preset.model_type == "manual" else ""
        else:
            model = ""
        timeout_ms = int(cc_preset.api_timeout_ms) if cc_preset and cc_preset.api_timeout_ms else 300000

        settings: Dict[str, Any] = {
            "provider": "anthropic",
            "providers": {
                "anthropic": {
                    "name": "Anthropic",
                    "base_url": base_url,
                    "auth_token": api_key,
                    "model": model,
                }
            },
            "active_provider": "anthropic",
            "timeout_ms": timeout_ms,
        }
        settings_path = ws_dir / "settings.json"
        settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"热更新 settings.json: {settings_path}")

        if cc_preset:
            claude_dir = ws_dir / ".claude"
            claude_dir.mkdir(exist_ok=True)
            claude_settings_path = claude_dir / "settings.json"
            claude_settings_path.write_text(
                json.dumps(cc_preset.to_config_json(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(f"热更新 .claude/settings.json: {claude_settings_path}")

    @staticmethod
    def _parse_frontmatter(raw: str) -> "tuple[Dict[str, Any], str]":
        """解析 YAML frontmatter，返回 (meta_dict, body)。不依赖 pyyaml，使用行解析。"""
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1].strip()
                body = parts[2].strip()
                meta: Dict[str, Any] = {}
                for line in fm_text.splitlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        key, _, value = line.partition(":")
                        value = value.strip().strip('"').strip("'")
                        if value.startswith("[") and value.endswith("]"):
                            items = value[1:-1].split(",")
                            meta[key.strip()] = [i.strip().strip('"').strip("'") for i in items if i.strip()]
                        elif value.lower() == "true":
                            meta[key.strip()] = True
                        elif value.lower() == "false":
                            meta[key.strip()] = False
                        else:
                            meta[key.strip()] = value
                return meta, body
        return {}, raw

    @staticmethod
    def list_memory_tree(workspace_id: int) -> "List[Dict[str, Any]]":
        """返回记忆目录树（仅包含 .md 文件和目录）。"""
        memory_root = WorkspaceService.get_memory_root(workspace_id)
        if not memory_root.exists():
            return []

        def _build(path: "Path", base: "Path") -> "List[Dict[str, Any]]":
            nodes: List[Dict[str, Any]] = []
            try:
                entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            except PermissionError:
                return []
            for entry in entries:
                rel = str(entry.relative_to(base))
                if entry.is_dir():
                    nodes.append({"name": entry.name, "type": "dir", "path": rel, "meta": None, "children": _build(entry, base)})
                elif entry.is_file() and entry.suffix == ".md":
                    try:
                        m, _ = WorkspaceService._parse_frontmatter(entry.read_text(encoding="utf-8"))
                    except Exception:
                        m = {}
                    tags = m.get("tags", [])
                    nodes.append({
                        "name": entry.name,
                        "type": "file",
                        "path": rel,
                        "meta": {
                            "path": rel,
                            "title": m.get("title", entry.stem),
                            "category": m.get("category", ""),
                            "tags": tags if isinstance(tags, list) else [],
                            "shared": bool(m.get("shared", False)),
                            "updated": str(m.get("updated", "")),
                        },
                        "children": None,
                    })
            return nodes

        return _build(memory_root, memory_root)

    @staticmethod
    def read_memory_file(workspace_id: int, rel_path: str) -> "Optional[Dict[str, Any]]":
        """读取记忆文件，返回 {path, raw, content, meta}，不存在则返回 None。"""
        memory_root = WorkspaceService.get_memory_root(workspace_id)
        try:
            target = (memory_root / rel_path).resolve()
            target.relative_to(memory_root.resolve())
        except ValueError:
            return None
        if not target.exists() or not target.is_file():
            return None
        raw = target.read_text(encoding="utf-8")
        m, body = WorkspaceService._parse_frontmatter(raw)
        tags = m.get("tags", [])
        return {
            "path": rel_path,
            "raw": raw,
            "content": body,
            "meta": {
                "path": rel_path,
                "title": m.get("title", target.stem),
                "category": m.get("category", ""),
                "tags": tags if isinstance(tags, list) else [],
                "shared": bool(m.get("shared", False)),
                "updated": str(m.get("updated", "")),
            },
        }

    @staticmethod
    def write_memory_file(workspace_id: int, rel_path: str, raw: str) -> None:
        """创建或更新记忆文件，自动创建父目录。路径穿越时抛出 ValueError。"""
        memory_root = WorkspaceService.get_memory_root(workspace_id)
        try:
            target = (memory_root / rel_path).resolve()
            target.relative_to(memory_root.resolve())
        except ValueError:
            raise ValueError(f"非法路径: {rel_path}")
        memory_root.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(raw, encoding="utf-8")

    @staticmethod
    def delete_memory_file(workspace_id: int, rel_path: str) -> bool:
        """删除记忆文件，返回是否成功。"""
        memory_root = WorkspaceService.get_memory_root(workspace_id)
        try:
            target = (memory_root / rel_path).resolve()
            target.relative_to(memory_root.resolve())
        except ValueError:
            return False
        if target.exists() and target.is_file():
            target.unlink()
            return True
        return False

    @staticmethod
    def reset_memory(workspace_id: int) -> int:
        """清空工作区记忆目录下的所有 .md 文件（保留目录结构）。返回删除的文件数量。"""
        memory_root = WorkspaceService.get_memory_root(workspace_id)
        if not memory_root.exists():
            return 0
        count = 0
        for md_file in memory_root.rglob("*.md"):
            try:
                md_file.unlink()
                count += 1
            except Exception:
                pass
        # 清理空目录（保留 memory_root 本身）
        for dirpath in sorted(memory_root.rglob("*"), reverse=True):
            if dirpath.is_dir() and dirpath != memory_root:
                try:
                    dirpath.rmdir()  # 只删除空目录
                except OSError:
                    pass
        return count

    @staticmethod
    def read_na_context(workspace_id: int) -> "tuple[str, str]":
        """读取 _na_context.md 正文与更新时间，截取前 1800 字符（约 600 中文字）。

        Returns:
            (body, updated): 正文内容（最多1800字符）和 frontmatter 中的 updated 字段（可能为空字符串）
        """
        na_context_path = WorkspaceService.get_memory_root(workspace_id) / "_na_context.md"
        if not na_context_path.exists():
            return "", ""
        raw = na_context_path.read_text(encoding="utf-8")
        meta, body = WorkspaceService._parse_frontmatter(raw)
        return body[:1800], str(meta.get("updated", ""))

    @staticmethod
    def get_capability_summary(workspace: "DBWorkspace") -> str:
        """生成工作区 CC 能力摘要：选中 Skills 和 MCP 服务。"""
        lines: List[str] = []

        selected_skills: List[str] = workspace.metadata.get("skills", [])
        if selected_skills:
            all_skills_map: Dict[str, Any] = {
                s["name"]: s for s in WorkspaceService.list_all_skills()
            }
            skill_lines: List[str] = []
            for name in selected_skills:
                info = all_skills_map.get(name, {})
                desc = info.get("description", "")
                skill_lines.append(f"  - {name}: {desc}" if desc else f"  - {name}")
            lines.append("已部署 Skills:\n" + "\n".join(skill_lines))

        # 动态 Skills（CC 创建）
        dynamic_skills = WorkspaceService.list_dynamic_skills(workspace.id)
        if dynamic_skills:
            dynamic_lines = [f"  - {s['name']}: {s['description']}" if s["description"] else f"  - {s['name']}" for s in dynamic_skills]
            lines.append("动态 Skills（CC 创建）:\n" + "\n".join(dynamic_lines))

        # MCP 服务
        mcp_config = workspace.metadata.get("mcp_config", {})
        mcp_servers = mcp_config.get("mcpServers", {})
        if mcp_servers:
            lines.append(f"MCP 服务: {', '.join(mcp_servers.keys())}")

        return "\n\n".join(lines) if lines else "（无扩展技能或 MCP 服务）"

    @staticmethod
    async def init_workspace_dir(
        workspace: DBWorkspace,
        cc_preset: Optional["CCModelPresetItem"] = None,
    ) -> None:
        """初始化 workspace 目录，写入 settings.json / .mcp.json / .claude/settings.json / skills/（幂等）"""
        ws_dir = WorkspaceService.get_workspace_dir(workspace.id)
        ws_dir.mkdir(parents=True, exist_ok=True)

        # 从 CC 模型预设中提取凭据（CC Sandbox 的 settings.json 格式）
        api_key = cc_preset.auth_token if cc_preset else ""
        base_url = cc_preset.base_url if cc_preset else ""
        if cc_preset:
            model = cc_preset.anthropic_model if cc_preset.model_type == "manual" else ""
        else:
            model = ""
        timeout_ms = int(cc_preset.api_timeout_ms) if cc_preset and cc_preset.api_timeout_ms else 300000

        # 写入 settings.json（CC Sandbox 读取的配置格式）
        settings_path = ws_dir / "settings.json"
        settings: Dict[str, Any] = {
            "provider": "anthropic",
            "providers": {
                "anthropic": {
                    "name": "Anthropic",
                    "base_url": base_url,
                    "auth_token": api_key,
                    "model": model,
                }
            },
            "active_provider": "anthropic",
            "timeout_ms": timeout_ms,
        }
        settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"写入 settings.json: {settings_path}")

        # 写入 .claude/settings.json（Claude Code Project 级配置，包含完整的模型映射和环境变量）
        if cc_preset:
            claude_dir = ws_dir / ".claude"
            claude_dir.mkdir(exist_ok=True)
            claude_settings_path = claude_dir / "settings.json"
            claude_settings_path.write_text(
                json.dumps(cc_preset.to_config_json(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(f"写入 .claude/settings.json: {claude_settings_path}")

        # 写入 .mcp.json（来自 metadata.mcp_config，若无则写空配置）
        mcp_config = workspace.metadata.get("mcp_config", {})
        if not mcp_config:
            mcp_config = {"mcpServers": {}}
        mcp_path = ws_dir / ".mcp.json"
        mcp_path.write_text(json.dumps(mcp_config, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"写入 .mcp.json: {mcp_path}")

        # 同步 skills 目录
        await WorkspaceService.sync_skills(workspace)

        # 创建 shared 目录（CC↔NA 文件共享目录，NA 实时感知）
        shared_dir = ws_dir / "default" / "shared"
        shared_dir.mkdir(parents=True, exist_ok=True)
        # 确保容器内的 appuser 有写入权限（bind mount 跨越用户边界时宿主机 owner 可能不匹配）
        shared_dir.chmod(0o777)

        # 创建 .claude_home 目录（挂载到容器内 ~/.claude/，持久化 Claude Code 会话历史）
        claude_home = ws_dir / ".claude_home"
        claude_home.mkdir(exist_ok=True)
        # 确保容器内的 appuser 有写入权限（bind mount 跨越用户边界时宿主机 owner 可能不匹配）
        claude_home.chmod(0o777)

        # 写入 CLAUDE.md 到 CC 工作目录（/workspace/default/CLAUDE.md）
        # 注意：不能放在 /workspace/CLAUDE.md，否则当 /workspace/default/ 成为 git 根目录时
        # Claude Code 会停止向上遍历，导致 CLAUDE.md 被忽略
        claude_md_path = ws_dir / "default" / "CLAUDE.md"
        claude_md_path.write_text(WorkspaceService._generate_claude_md_content(workspace), encoding="utf-8")
        logger.debug(f"写入 CLAUDE.md: {claude_md_path}")

    @staticmethod
    def scan_shared_dir(workspace_id: int, max_files: int = 10) -> list[dict[str, str]]:
        """扫描 CC 工作区共享目录，返回最近更新的文件列表。

        Args:
            workspace_id: 工作区 ID
            max_files: 最多返回的文件数量

        Returns:
            按修改时间倒序排列的文件信息列表，每项包含 name, size_human, mtime_str, rel_path。
        """
        shared_dir = Path(WORKSPACE_ROOT_DIR) / str(workspace_id) / "default" / "shared"
        if not shared_dir.is_dir():
            return []

        files: list[tuple[float, Path]] = []
        for item in shared_dir.iterdir():
            if item.is_file():
                files.append((item.stat().st_mtime, item))
            elif item.is_dir():
                # 浅层递归：只扫描 1 级子目录
                for sub_item in item.iterdir():
                    if sub_item.is_file():
                        files.append((sub_item.stat().st_mtime, sub_item))

        # 按修改时间倒序
        files.sort(key=lambda x: x[0], reverse=True)

        result: list[dict[str, str]] = []
        for mtime, fpath in files[:max_files]:
            size = fpath.stat().st_size
            if size < 1024:
                size_human = f"{size}B"
            elif size < 1024 * 1024:
                size_human = f"{size / 1024:.1f}KB"
            else:
                size_human = f"{size / (1024 * 1024):.1f}MB"

            mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc).astimezone()
            mtime_str = mtime_dt.strftime("%m-%d %H:%M")

            result.append({
                "name": fpath.name,
                "size_human": size_human,
                "mtime_str": mtime_str,
                "rel_path": str(fpath.relative_to(shared_dir)),
            })
        return result

    @staticmethod
    def _read_skill_meta(skill_dir: Path) -> Optional[Dict[str, str]]:
        """从 SKILL.md frontmatter 读取 skill 元信息，不存在时返回 None。"""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None
        try:
            content = skill_md.read_text(encoding="utf-8")
            meta: Dict[str, str] = {}
            lines = content.splitlines()
            in_frontmatter = False
            for i, line in enumerate(lines):
                if i == 0 and line.strip() == "---":
                    in_frontmatter = True
                    continue
                if in_frontmatter and line.strip() == "---":
                    break
                if in_frontmatter and ":" in line and not line.startswith("#"):
                    key, _, value = line.partition(":")
                    meta[key.strip()] = value.strip().strip('"').strip("'")
            return {
                "name": meta.get("name", skill_dir.name),
                "description": meta.get("description", ""),
            }
        except Exception as e:
            logger.warning(f"读取 SKILL.md 失败: {skill_dir.name}: {e}")
            return None

    @staticmethod
    def _resolve_skill_source(skill_id: str) -> "tuple[Optional[Path], str]":
        """根据 skill_id 解析源目录和类别。

        Returns:
            (source_dir, category): source_dir 为 None 表示未找到; category 为 "builtin"/"user"/"repo"
        """
        builtin_src = Path(BUILTIN_SKILLS_SOURCE_DIR)
        local_src = Path(SKILLS_LOCAL_DIR)
        repos_src = Path(SKILLS_REPOS_DIR)

        if "/" in skill_id:
            # 仓库技能：repos/{repo}/{skill}
            src = repos_src / skill_id
            return (src, "repo") if src.is_dir() else (None, "repo")

        # 不含 / → 先 builtin，再 local
        src = builtin_src / skill_id
        if src.is_dir():
            return src, "builtin"
        src = local_src / skill_id
        if src.is_dir():
            return src, "user"
        return None, "user"

    @staticmethod
    async def sync_skills(workspace: DBWorkspace) -> None:
        """将 metadata['skills'] 中选中的技能同步到沙盒 .claude_home/skills/"""
        ws_dir = WorkspaceService.get_workspace_dir(workspace.id)
        skills_home = ws_dir / ".claude_home" / "skills"
        skills_home.mkdir(parents=True, exist_ok=True)

        Path(SKILLS_LOCAL_DIR).mkdir(parents=True, exist_ok=True)
        Path(SKILLS_REPOS_DIR).mkdir(parents=True, exist_ok=True)

        builtin_dst = skills_home / "builtin"
        user_dst = skills_home / "user"
        builtin_dst.mkdir(exist_ok=True)
        user_dst.mkdir(exist_ok=True)

        selected_skills: List[str] = workspace.metadata.get("skills", [])
        # 构建选中 skill 的目标目录名集合（仓库技能取最后一段）
        selected_builtin_names: set[str] = set()
        selected_user_names: set[str] = set()
        for sid in selected_skills:
            _, cat = WorkspaceService._resolve_skill_source(sid)
            target_name = sid.split("/")[-1] if "/" in sid else sid
            if cat == "builtin":
                selected_builtin_names.add(target_name)
            else:
                selected_user_names.add(target_name)

        # 清理不在选中列表的
        for d in list(builtin_dst.iterdir()):
            if d.is_dir() and d.name not in selected_builtin_names:
                shutil.rmtree(d)
                logger.debug(f"清理内置 skill: {d.name}")
        for d in list(user_dst.iterdir()):
            if d.is_dir() and d.name not in selected_user_names:
                shutil.rmtree(d)
                logger.debug(f"清理用户 skill: {d.name}")

        # 复制/更新选中的 skill
        for skill_id in selected_skills:
            src, cat = WorkspaceService._resolve_skill_source(skill_id)
            if src is None or not src.is_dir():
                logger.warning(f"skill 不存在: {skill_id}")
                continue
            target_name = skill_id.split("/")[-1] if "/" in skill_id else skill_id
            dst_parent = builtin_dst if cat == "builtin" else user_dst
            dst = dst_parent / target_name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            logger.debug(f"同步 skill: {skill_id} → {dst_parent.name}/{target_name}")

        # dynamic 目录仅确保存在，不做任何清理
        (skills_home / "dynamic").mkdir(exist_ok=True)

    @staticmethod
    async def update_mcp_config(workspace: DBWorkspace, mcp_config: Dict[str, Any]) -> None:
        """更新 workspace 的 MCP 配置并写入文件"""
        metadata = dict(workspace.metadata)
        metadata["mcp_config"] = mcp_config
        workspace.metadata = metadata
        await workspace.save(update_fields=["metadata", "update_time"])

        ws_dir = WorkspaceService.get_workspace_dir(workspace.id)
        mcp_path = ws_dir / ".mcp.json"
        mcp_path.write_text(json.dumps(mcp_config, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    async def bind_channel(workspace: DBWorkspace, chat_key: str) -> None:
        """将频道绑定到工作区"""
        channel = await DBChatChannel.get_or_none(chat_key=chat_key)
        if channel is None:
            from nekro_agent.schemas.errors import NotFoundError

            raise NotFoundError(resource=f"频道 {chat_key}")
        channel.workspace_id = workspace.id
        await channel.save(update_fields=["workspace_id", "update_time"])

    @staticmethod
    async def unbind_channel(workspace: DBWorkspace, chat_key: str) -> None:
        """解除频道的工作区绑定，并同步清理工作区侧的频道注解。"""
        channel = await DBChatChannel.get_or_none(chat_key=chat_key)
        if channel is None:
            from nekro_agent.schemas.errors import NotFoundError

            raise NotFoundError(resource=f"频道 {chat_key}")
        channel.workspace_id = None  # type: ignore[assignment]
        await channel.save(update_fields=["workspace_id", "update_time"])
        # 同步清理工作区侧注解
        await WorkspaceService.remove_channel_annotation(workspace, chat_key)

    @staticmethod
    async def get_bound_channels(workspace_id: int) -> List[DBChatChannel]:
        """获取绑定到工作区的所有频道"""
        return await DBChatChannel.filter(workspace_id=workspace_id).all()

    # ── 频道注解管理（存储于 metadata.channel_annotations） ───────────────────

    @staticmethod
    def get_channel_annotations(workspace: DBWorkspace) -> Dict[str, "ChannelAnnotationData"]:
        """获取工作区所有频道注解，返回以 chat_key 为键的字典。"""
        raw: Dict[str, Any] = workspace.metadata.get("channel_annotations", {})
        result: Dict[str, ChannelAnnotationData] = {}
        for chat_key, data in raw.items():
            if isinstance(data, dict):
                result[chat_key] = ChannelAnnotationData(
                    description=str(data.get("description", "")),
                    is_primary=bool(data.get("is_primary", False)),
                )
        return result

    @staticmethod
    def get_primary_channel_chat_key(workspace: DBWorkspace, bound_chat_keys: List[str]) -> Optional[str]:
        """推断主频道 chat_key。
        - 只有一个绑定频道时，直接返回它（无需显式设置）
        - 多个频道时，从 annotations 中找 is_primary=True 的
        """
        if not bound_chat_keys:
            return None
        if len(bound_chat_keys) == 1:
            return bound_chat_keys[0]
        annotations = WorkspaceService.get_channel_annotations(workspace)
        for chat_key in bound_chat_keys:
            ann = annotations.get(chat_key)
            if ann and ann.is_primary:
                return chat_key
        return None

    @staticmethod
    async def update_channel_annotation(
        workspace: DBWorkspace,
        chat_key: str,
        description: str,
        is_primary: bool,
    ) -> None:
        """更新单个频道的注解。若 is_primary=True，自动清除其他频道的主频道标记。"""
        metadata = dict(workspace.metadata)
        annotations: Dict[str, Any] = dict(metadata.get("channel_annotations", {}))

        if is_primary:
            # 清除其他频道的 is_primary
            for key in annotations:
                if key != chat_key and annotations[key].get("is_primary"):
                    annotations[key] = dict(annotations[key])
                    annotations[key]["is_primary"] = False

        annotations[chat_key] = {
            "description": description,
            "is_primary": is_primary,
        }

        metadata["channel_annotations"] = annotations
        workspace.metadata = metadata
        await workspace.save(update_fields=["metadata", "update_time"])

    @staticmethod
    async def remove_channel_annotation(workspace: DBWorkspace, chat_key: str) -> None:
        """删除频道注解（解绑时调用）。若被删除的是主频道且还有其他频道，自动将剩余第一个设为主频道。"""
        metadata = dict(workspace.metadata)
        annotations: Dict[str, Any] = dict(metadata.get("channel_annotations", {}))

        was_primary = annotations.get(chat_key, {}).get("is_primary", False)
        annotations.pop(chat_key, None)

        # 若删除的是主频道，且还有其他注解，将第一个设为主频道
        if was_primary and annotations:
            first_key = next(iter(annotations))
            annotations[first_key] = dict(annotations[first_key])
            annotations[first_key]["is_primary"] = True

        metadata["channel_annotations"] = annotations
        workspace.metadata = metadata
        await workspace.save(update_fields=["metadata", "update_time"])

    @staticmethod
    def get_dynamic_skills_dir(workspace_id: int) -> Path:
        return WorkspaceService.get_workspace_dir(workspace_id) / ".claude_home" / "skills" / "dynamic"

    @staticmethod
    def list_dynamic_skills(workspace_id: int) -> List[Dict[str, str]]:
        """列出工作区 dynamic tier 中所有 skill"""
        dynamic_dir = WorkspaceService.get_dynamic_skills_dir(workspace_id)
        if not dynamic_dir.exists():
            return []
        skills: List[Dict[str, str]] = []
        for skill_dir in sorted(dynamic_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            meta = WorkspaceService._read_skill_meta(skill_dir)
            skills.append(
                {
                    "dir_name": skill_dir.name,
                    "name": meta["name"] if meta else skill_dir.name,
                    "description": meta["description"] if meta else "",
                }
            )
        return skills

    @staticmethod
    def read_dynamic_skill(workspace_id: int, dir_name: str) -> Optional[str]:
        """读取动态 skill 的 SKILL.md 内容，不存在时返回 None"""
        skill_md = WorkspaceService.get_dynamic_skills_dir(workspace_id) / dir_name / "SKILL.md"
        if not skill_md.exists():
            return None
        return skill_md.read_text(encoding="utf-8")

    @staticmethod
    def write_dynamic_skill(workspace_id: int, dir_name: str, content: str) -> None:
        """创建或更新动态 skill（写入 SKILL.md）"""
        dynamic_dir = WorkspaceService.get_dynamic_skills_dir(workspace_id)
        dynamic_dir.mkdir(parents=True, exist_ok=True)
        skill_dir = dynamic_dir / dir_name
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    @staticmethod
    def delete_dynamic_skill(workspace_id: int, dir_name: str) -> bool:
        """删除动态 skill，返回是否成功"""
        skill_dir = WorkspaceService.get_dynamic_skills_dir(workspace_id) / dir_name
        if not skill_dir.exists() or not skill_dir.is_dir():
            return False
        shutil.rmtree(skill_dir)
        return True

    @staticmethod
    def promote_dynamic_skill(workspace_id: int, dir_name: str, *, force: bool = False) -> str:
        """将动态 skill 晋升为全局用户 skill（复制到 SKILLS_LOCAL_DIR）。

        Args:
            force: 为 True 时覆盖已有同名技能，否则已存在时抛出 ConflictError。

        Returns:
            目录名

        Raises:
            ValueError: 源不存在或一致性校验失败
            ConflictError: 目标已存在且 force=False
        """
        src = WorkspaceService.get_dynamic_skills_dir(workspace_id) / dir_name
        if not src.exists() or not src.is_dir():
            raise ValueError(f"动态 skill 不存在: {dir_name}")

        # 一致性校验：frontmatter name 必须与 dir_name 一致
        meta = WorkspaceService._read_skill_meta(src)
        if meta:
            fm_name = meta.get("name", "")
            if fm_name and fm_name != dir_name:
                raise ValueError(
                    f"SKILL.md 中的 name '{fm_name}' 与目录名 '{dir_name}' 不一致，请修正后重试"
                )

        dst = Path(SKILLS_LOCAL_DIR) / dir_name
        Path(SKILLS_LOCAL_DIR).mkdir(parents=True, exist_ok=True)

        if dst.exists() and not force:
            from nekro_agent.schemas.errors import ConflictError
            raise ConflictError(resource=f"技能 '{dir_name}' 已存在于技能库中")

        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

        # 写入 .skill-origin.json
        WorkspaceService._write_skill_origin(dst, origin="promoted", promoted_from_workspace=workspace_id)

        return dir_name

    @staticmethod
    def list_builtin_skills() -> List[Dict[str, str]]:
        """列出所有内置 skill（来自源码 builtin_skills 目录）"""
        src = Path(BUILTIN_SKILLS_SOURCE_DIR)
        if not src.exists():
            return []
        skills: List[Dict[str, str]] = []
        for skill_dir in sorted(src.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            meta = WorkspaceService._read_skill_meta(skill_dir)
            if meta is None:
                continue
            skills.append({"name": meta["name"], "description": meta["description"], "dir_name": skill_dir.name})
        return skills

    @staticmethod
    def list_global_skills() -> List[Dict[str, str]]:
        """列出全局用户 skill 资源库（仅 local/ 下含有 SKILL.md 的目录）"""
        local_dir = Path(SKILLS_LOCAL_DIR)
        local_dir.mkdir(parents=True, exist_ok=True)
        skills: List[Dict[str, str]] = []
        for skill_dir in sorted(local_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            meta = WorkspaceService._read_skill_meta(skill_dir)
            if meta is None:
                continue
            skills.append({"name": meta["name"], "description": meta["description"]})
        return skills

    @staticmethod
    def _scan_repo_skills(repos_dir: Path) -> List[Dict[str, str]]:
        """递归扫描 repos/ 下所有含 SKILL.md 的目录，返回统一格式列表。

        标识格式：repo_name/skill_dir_name
        """
        results: List[Dict[str, str]] = []
        if not repos_dir.exists():
            return results
        for repo_dir in sorted(repos_dir.iterdir()):
            if not repo_dir.is_dir() or repo_dir.name.startswith("."):
                continue
            repo_name = repo_dir.name
            for skill_dir in sorted(repo_dir.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                    continue
                meta = WorkspaceService._read_skill_meta(skill_dir)
                if meta is None:
                    continue
                results.append({
                    "name": f"{repo_name}/{skill_dir.name}",
                    "display_name": meta["name"],
                    "description": meta["description"],
                    "source": "repo",
                    "repo_name": repo_name,
                })
        return results

    @staticmethod
    def list_all_skills() -> List[Dict[str, str]]:
        """列出所有可用技能候选（内置 + local + repos），每项含 source 字段"""
        seen: set[str] = set()
        result: List[Dict[str, str]] = []

        # 1. 内置
        builtin_src = Path(BUILTIN_SKILLS_SOURCE_DIR)
        if builtin_src.exists():
            for skill_dir in sorted(builtin_src.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                    continue
                meta = WorkspaceService._read_skill_meta(skill_dir)
                if meta is None:
                    continue
                result.append({
                    "name": skill_dir.name,
                    "display_name": meta["name"],
                    "description": meta["description"],
                    "source": "builtin",
                })
                seen.add(skill_dir.name)

        # 2. local（跳过与内置同名的）
        local_src = Path(SKILLS_LOCAL_DIR)
        local_src.mkdir(parents=True, exist_ok=True)
        for skill_dir in sorted(local_src.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            if skill_dir.name in seen:
                continue
            meta = WorkspaceService._read_skill_meta(skill_dir)
            if meta is None:
                continue
            result.append({
                "name": skill_dir.name,
                "display_name": meta["name"],
                "description": meta["description"],
                "source": "user",
            })
            seen.add(skill_dir.name)

        # 3. repos（嵌套，标识含 /）
        repos_src = Path(SKILLS_REPOS_DIR)
        repos_src.mkdir(parents=True, exist_ok=True)
        result.extend(WorkspaceService._scan_repo_skills(repos_src))

        return result

    @staticmethod
    async def sync_single_skill(workspace: "DBWorkspace", skill_id: str) -> bool:
        """从全局 skill 库重新同步单个 skill 到工作区（不修改选中列表）。

        支持 builtin/local/repo 三种来源，skill_id 可含 / (仓库技能)。
        """
        selected_skills: List[str] = workspace.metadata.get("skills", [])
        if skill_id not in selected_skills:
            return False
        src, cat = WorkspaceService._resolve_skill_source(skill_id)
        if src is None or not src.is_dir():
            logger.warning(f"全局 skill 不存在，无法同步: {skill_id}")
            return False
        ws_dir = WorkspaceService.get_workspace_dir(workspace.id)
        target_name = skill_id.split("/")[-1] if "/" in skill_id else skill_id
        dst_parent = ws_dir / ".claude_home" / "skills" / ("builtin" if cat == "builtin" else "user")
        dst_parent.mkdir(parents=True, exist_ok=True)
        dst = dst_parent / target_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        logger.debug(f"重新同步 skill: {skill_id} → {dst_parent.name}/{target_name}")
        return True

    @staticmethod
    def _write_skill_origin(
        skill_dir: Path,
        *,
        origin: str,
        promoted_from_workspace: Optional[int] = None,
        repo_url: Optional[str] = None,
        community_id: Optional[str] = None,
        community_slug: Optional[str] = None,
    ) -> None:
        """在 skill 目录下写入 .skill-origin.json 来源追溯文件。"""
        data = {
            "origin": origin,
            "promoted_from_workspace": promoted_from_workspace,
            "repo_url": repo_url,
            "community_id": community_id,
            "community_slug": community_slug,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        origin_path = skill_dir / ".skill-origin.json"
        origin_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def read_skill_origin(skill_dir: Path) -> Optional[Dict[str, Any]]:
        """读取 .skill-origin.json，不存在返回 None。"""
        origin_path = skill_dir / ".skill-origin.json"
        if not origin_path.exists():
            return None
        try:
            return json.loads(origin_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    async def sync_skill_to_all_workspaces(skill_id: str) -> int:
        """将指定技能同步到所有引用它的工作区。返回同步成功的工作区数量。"""
        workspaces = await DBWorkspace.all()
        count = 0
        for ws in workspaces:
            selected: List[str] = ws.metadata.get("skills", [])
            if skill_id in selected:
                ok = await WorkspaceService.sync_single_skill(ws, skill_id)
                if ok:
                    count += 1
        return count
