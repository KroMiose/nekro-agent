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

你是 **NekroAgent**（NA）系统中的执行层子 Agent，运行在独立的 cc-sandbox 容器中。

**代理执行模型**（必须理解）：
```
[人类用户] ←IM聊天→ [NA 主 Agent] ←任务委托→ [你]
     ↑                                        ↑
  只能看到 NA 的消息               你的工作区用户完全无法访问
```
- 真正的最终用户在 IM 端，你应当默认其**无法访问**你的 `/workspace/` 目录、代码、文件或命令输出
- NA 是你的直接通信方，负责将你的成果转化为用户可获取的形式
- 任务"完成"的标准不是"代码改完了"，而是**用户能够获取/使用你的成果**

**你的职责**：执行编程、文件处理、命令执行等任务，并确保成果可交付。

**你是工作区的第一手知识持有者**：NA 无法主动读取你的工作区。当 NA 指令与实际状态矛盾时，基于现实调整并说明原因。

**你不应该**：修改 `settings.json`、`.mcp.json` 等配置文件；访问 `/workspace/` 外的资源；盲目执行包含错误假设的指令。

## 成果交付（核心）

**用户无法访问你的工作区。** 每次任务完成前必须确保成果可达：

| 任务类型 | 交付方式 |
|----------|----------|
| 外部仓库代码修改 | 创建 PR 或推送分支，**响应中返回链接** |
| 生成文件/报告 | 放入 `/workspace/default/shared/`，NA 会获取并发送给用户 |
| 分析/调研 | 响应中详细说明；内容较长时同时写入 `shared/` |
| 无远程权限的代码修改 | 生成 patch/压缩包到 `shared/`，或说明 clone 方式 |

**错误示范** ❌：`我已修改了 src/utils.py`（用户无法访问）
**正确示范** ✅：`已修改并创建 PR: https://github.com/xxx/repo/pull/42`

## 工作环境

### 目录路径

| 目录 | 路径 | 说明 |
|------|------|------|
| 工作目录（cwd） | `/workspace/default/` | Claude Code 默认工作目录 |
| 共享目录 | `/workspace/default/shared/` | 与 NA 交换文件（NA 实时感知目录内容，将产出物放在这里） |
| 技能目录 | `~/.claude/skills/` | Claude Code 可发现的 workspace 本地技能目录 |
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
- 持久化方案：`echo 'export GH_TOKEN=your_pat' >> ~/.bashrc`

**Python 开发**：
- 工作区内用 `uv add <包名>` 安装依赖（持久化在工作区目录）
- 运行脚本：`python3 script.py` 或 `uv run script.py`

**Node.js 开发**：
- 直接运行 `node script.js` 或 `npx <包名>`
- 安装包：`npm install <包名>` 或 `npm install -g <包名>`（全局）

**Skills（Claude Code 技能）**：
- Claude Code 从 `~/.claude/skills/<skill-name>/SKILL.md` 发现技能
- 如需创建 workspace 本地技能，直接在 `~/.claude/skills/<skill-name>/` 下写入技能文件
- 不要手动编造平台级来源元数据；若平台需要，它会在后续扫描、晋升或发布时自动补齐

## 记忆系统

统一记忆与经验沉淀由 NekroAgent 在工作区外部集中管理，你只需要：

1. 在任务结果中清晰写出结论、改动位置、验证结果和风险
2. 遇到可复用的技术经验、排障结论、关键约束时，明确写在回复正文中
3. 不要额外创建、更新或依赖任何本地记忆文件

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
6. **记忆沉淀约定**：每次任务完成后，确保回复中包含足够清晰的结论、改动和注意事项，供上层统一记忆系统提炼
7. **任务来源**：每条任务消息头部可能包含 `[任务来源频道: <chat_key>]` 标记，标识该任务来自哪个 NA 会话频道。在多频道共用同一工作区场景下，可利用此信息在记忆文件中区分不同频道的任务背景。
8. **态度认真**：对于来自 NA 的任何指示，必须进行足够深入的分析、思考与研究，时刻思考**我是否真的高质量地完成了任务?**，严禁敷衍了事或形式完成！

## Git/GitHub 协作规范（必读）

### 分支创建（最高优先级）

- ❌ **禁止**：`git checkout -b fix/xxx`（从当前 HEAD 创建，会继承所有历史 commit）
- ✅ **必须**：`git checkout -b <分支名> <远端名>/<分支名>`
  - 例如：`git checkout -b fix/this-bug origin/main`
  - 先执行 `git fetch <远端名> <分支名>` 确保远端最新

### PR 提交流程（每次必须执行）

**第一步：创建分支前**
```bash
git remote -v && git branch -vv   # 确认远端和当前分支
```

**第二步：创建干净分支**
```bash
git fetch origin main
git checkout -b <分支名> origin/main
```

**第三步：提交前验证**
```bash
git log --oneline -3              # 确认只有必要提交（通常 1 个）
git diff origin/main --stat       # 确认只有目标文件被修改
gh auth status                    # 确认 gh 认证正常
```

**第四步：创建 PR 后再次确认**
```bash
gh pr view --json files          # 确认文件列表干净
```

### 常见错误规避

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| `git checkout -b` 不指定起点 | PR 携带历史 commit | 必须指定 `origin/main` |
| 复用上次的旧分支继续开发 | 混入不相关提交 | 每次从最新 main 新建 |
| 不检查 diff 就提交 | 脏提交进入 PR | 提交前必须 `git diff` |

{env_vars_section}
{shared_section}
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
        prompt_layers = workspace.metadata.get("prompt_layers", {})
        shared_rules = ""
        if isinstance(prompt_layers, dict):
            shared_layer = prompt_layers.get("shared_manual_rules")
            if isinstance(shared_layer, dict):
                shared_rules = str(shared_layer.get("content") or "").strip()
        shared_section = f"## 共享固定事实\n\n{shared_rules}" if shared_rules else ""
        extra_section = f"## 自定义附加指令\n\n{raw_extra}" if raw_extra else ""
        return (
            WorkspaceService._CLAUDE_MD_TEMPLATE
            .replace("{runtime_policy}", workspace.runtime_policy or "agent")
            .replace("{env_vars_section}", env_vars_section)
            .replace("{shared_section}", shared_section)
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
    def get_effective_cc_preset_id(workspace: "DBWorkspace") -> Optional[int]:
        """获取工作区当前生效的 CC 模型预设 ID（未显式绑定时回退默认预设）。"""
        from nekro_agent.core.cc_model_presets import cc_presets_store

        raw_preset_id = (workspace.metadata or {}).get("cc_model_preset_id")
        if raw_preset_id is not None:
            try:
                return int(raw_preset_id)
            except (TypeError, ValueError):
                logger.warning(f"工作区 {workspace.id} 的 cc_model_preset_id 非法: {raw_preset_id!r}")
                return None

        default = cc_presets_store.get_default()
        return default.id if default else None

    @staticmethod
    async def sync_workspace_settings_for_preset(
        preset_id: int,
        cc_preset: "CCModelPresetItem",
    ) -> int:
        """将预设变更反向同步到所有引用该预设的工作区磁盘配置。"""
        workspaces = await DBWorkspace.all()
        synced_count = 0

        for workspace in workspaces:
            if WorkspaceService.get_effective_cc_preset_id(workspace) != preset_id:
                continue
            try:
                WorkspaceService.update_workspace_settings(workspace, cc_preset)
                synced_count += 1
            except Exception as e:
                logger.warning(
                    f"同步工作区 CC 模型预设失败: workspace_id={workspace.id}, preset_id={preset_id}, error={e}"
                )

        logger.info(f"CC 模型预设 {preset_id} 已同步到 {synced_count} 个工作区")
        return synced_count

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
    def write_na_context(
        workspace_id: int,
        body: str,
        *,
        updated_by: str = "manual",
        title: str = "协作现状摘要",
    ) -> None:
        """写入 _na_context.md，自动生成最小 frontmatter。"""
        memory_root = WorkspaceService.get_memory_root(workspace_id)
        memory_root.mkdir(parents=True, exist_ok=True)
        na_context_path = memory_root / "_na_context.md"
        updated = datetime.now(timezone.utc).isoformat()
        frontmatter = "\n".join([
            "---",
            f'title: "{title}"',
            'category: "coordination"',
            f'updated: "{updated}"',
            f'updated_by: "{updated_by}"',
            "---",
            "",
        ])
        na_context_path.write_text(frontmatter + body.strip() + "\n", encoding="utf-8")

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

        # 写入 .mcp.json 到 CC 工作目录（/workspace/default/.mcp.json）
        # 注意：与 CLAUDE.md 同理，必须放在 /workspace/default/ 下，CC 只在项目根目录查找
        mcp_config = workspace.metadata.get("mcp_config", {})
        if not mcp_config:
            mcp_config = {"mcpServers": {}}
        mcp_path = ws_dir / "default" / ".mcp.json"
        mcp_path.write_text(json.dumps(mcp_config, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"写入 .mcp.json: {mcp_path}")

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
        """将 metadata['skills'] 中选中的技能同步到沙盒 .claude_home/skills/。

        Claude Code only recognizes flat skill directories under ~/.claude/skills/<skill-name>/SKILL.md.
        Workspace-local dynamic skills are also stored in this same directory. A skill without
        .skill-origin.json is treated as a workspace-local dynamic skill.
        """
        ws_dir = WorkspaceService.get_workspace_dir(workspace.id)
        skills_home = ws_dir / ".claude_home" / "skills"
        skills_home.mkdir(parents=True, exist_ok=True)

        # 旧结构已废弃：~/.claude/skills/{builtin,user,dynamic}/
        for legacy_dir_name in ("builtin", "user", "dynamic"):
            legacy_dir = skills_home / legacy_dir_name
            if legacy_dir.exists() and legacy_dir.is_dir():
                shutil.rmtree(legacy_dir)
                logger.debug(f"清理旧版 skills 分层目录: {legacy_dir_name}")

        Path(SKILLS_LOCAL_DIR).mkdir(parents=True, exist_ok=True)
        Path(SKILLS_REPOS_DIR).mkdir(parents=True, exist_ok=True)

        selected_skills: List[str] = workspace.metadata.get("skills", [])
        selected_names = {sid.split("/")[-1] if "/" in sid else sid for sid in selected_skills}

        # 清理未选中的“受管理 skill”；未标记技能视为 workspace-local dynamic skill，保留。
        for d in list(skills_home.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            origin = WorkspaceService.read_skill_origin(d)
            if not origin:
                continue
            if d.name not in selected_names:
                shutil.rmtree(d)
                logger.debug(f"清理未选中的受管理 skill: {d.name}")

        # 复制/更新选中的 skill
        for skill_id in selected_skills:
            src, cat = WorkspaceService._resolve_skill_source(skill_id)
            if src is None or not src.is_dir():
                logger.warning(f"skill 不存在: {skill_id}")
                continue
            target_name = skill_id.split("/")[-1] if "/" in skill_id else skill_id
            dst = skills_home / target_name
            if dst.exists():
                existing_origin = WorkspaceService.read_skill_origin(dst)
                if not existing_origin:
                    logger.warning(
                        f"跳过同步 skill（与 workspace-local dynamic skill 同名冲突）: {skill_id} -> {target_name}"
                    )
                    continue
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            WorkspaceService._write_skill_origin(dst, origin=cat, source_skill_id=skill_id)
            logger.debug(f"同步 skill: {skill_id} → {target_name}")

    @staticmethod
    async def update_mcp_config(workspace: DBWorkspace, mcp_config: Dict[str, Any]) -> None:
        """更新 workspace 的 MCP 配置并写入文件"""
        metadata = dict(workspace.metadata)
        metadata["mcp_config"] = mcp_config
        workspace.metadata = metadata
        await workspace.save(update_fields=["metadata", "update_time"])

        ws_dir = WorkspaceService.get_workspace_dir(workspace.id)
        mcp_path = ws_dir / "default" / ".mcp.json"
        mcp_path.write_text(json.dumps(mcp_config, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def list_mcp_servers(workspace: DBWorkspace) -> list[Any]:
        """解析 metadata.mcp_config.mcpServers 为结构化服务器列表"""
        from nekro_agent.services.mcp.schemas import McpServerConfig, McpServerType

        mcp_config: Dict[str, Any] = (workspace.metadata or {}).get("mcp_config", {})
        mcp_servers: Dict[str, Any] = mcp_config.get("mcpServers", {})
        result: list[McpServerConfig] = []
        for name, cfg in mcp_servers.items():
            # 优先从显式 transport 字段派生类型，兼容旧配置
            transport = cfg.get("transport")
            if transport == "sse":
                server_type = McpServerType.sse
            elif transport == "http":
                server_type = McpServerType.http
            elif transport == "stdio":
                server_type = McpServerType.stdio
            elif "url" in cfg:
                server_type = McpServerType.http
            else:
                server_type = McpServerType.stdio
            result.append(
                McpServerConfig(
                    name=name,
                    type=server_type,
                    enabled=cfg.get("enabled", True),
                    command=cfg.get("command"),
                    args=cfg.get("args", []),
                    env=cfg.get("env", {}),
                    url=cfg.get("url"),
                    headers=cfg.get("headers", {}),
                )
            )
        return result

    @staticmethod
    async def add_mcp_server(workspace: DBWorkspace, server: Any) -> None:
        """添加一个 MCP 服务器到 mcpServers"""
        mcp_config: Dict[str, Any] = dict((workspace.metadata or {}).get("mcp_config", {}))
        mcp_servers: Dict[str, Any] = dict(mcp_config.get("mcpServers", {}))

        if server.name in mcp_servers:
            from nekro_agent.schemas.errors import ConflictError

            raise ConflictError(resource=f"MCP 服务器 {server.name}")

        mcp_servers[server.name] = WorkspaceService._server_to_raw(server)
        mcp_config["mcpServers"] = mcp_servers
        await WorkspaceService.update_mcp_config(workspace, mcp_config)

    @staticmethod
    async def update_mcp_server(workspace: DBWorkspace, old_name: str, server: Any) -> None:
        """更新指定的 MCP 服务器"""
        mcp_config: Dict[str, Any] = dict((workspace.metadata or {}).get("mcp_config", {}))
        mcp_servers: Dict[str, Any] = dict(mcp_config.get("mcpServers", {}))

        if old_name not in mcp_servers:
            from nekro_agent.schemas.errors import NotFoundError

            raise NotFoundError(resource=f"MCP 服务器 {old_name}")

        # 如果改名，删除旧的
        if server.name != old_name:
            del mcp_servers[old_name]
        mcp_servers[server.name] = WorkspaceService._server_to_raw(server)
        mcp_config["mcpServers"] = mcp_servers
        await WorkspaceService.update_mcp_config(workspace, mcp_config)

    @staticmethod
    async def remove_mcp_server(workspace: DBWorkspace, name: str) -> None:
        """删除指定的 MCP 服务器"""
        mcp_config: Dict[str, Any] = dict((workspace.metadata or {}).get("mcp_config", {}))
        mcp_servers: Dict[str, Any] = dict(mcp_config.get("mcpServers", {}))

        if name not in mcp_servers:
            from nekro_agent.schemas.errors import NotFoundError

            raise NotFoundError(resource=f"MCP 服务器 {name}")

        del mcp_servers[name]
        mcp_config["mcpServers"] = mcp_servers
        await WorkspaceService.update_mcp_config(workspace, mcp_config)

    @staticmethod
    def _server_to_raw(server: Any) -> Dict[str, Any]:
        """将 McpServerConfig 转换为 .mcp.json 兼容的 raw dict"""
        raw: Dict[str, Any] = {}
        if not server.enabled:
            raw["enabled"] = False
        # 持久化 transport 类型，确保 sse/http 能正确往返
        raw["transport"] = server.type if isinstance(server.type, str) else server.type.value
        if server.url:
            # sse/http 类型
            raw["url"] = server.url
            if server.headers:
                raw["headers"] = dict(server.headers)
        else:
            # stdio 类型
            if server.command:
                raw["command"] = server.command
            if server.args:
                raw["args"] = list(server.args)
            if server.env:
                raw["env"] = dict(server.env)
        return raw

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
    def get_workspace_skills_dir(workspace_id: int) -> Path:
        return WorkspaceService.get_workspace_dir(workspace_id) / ".claude_home" / "skills"

    @staticmethod
    def _is_workspace_local_dynamic_skill(skill_dir: Path) -> bool:
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            return False
        if not (skill_dir / "SKILL.md").exists():
            return False
        origin = WorkspaceService.read_skill_origin(skill_dir)
        return not origin or origin.get("origin") == "dynamic"

    @staticmethod
    def list_dynamic_skills(workspace_id: int) -> List[Dict[str, str]]:
        """列出工作区内所有未固化的 workspace-local dynamic skills。"""
        skills_root = WorkspaceService.get_workspace_skills_dir(workspace_id)
        if not skills_root.exists():
            return []
        skills: List[Dict[str, str]] = []
        for skill_dir in sorted(skills_root.iterdir()):
            if not WorkspaceService._is_workspace_local_dynamic_skill(skill_dir):
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
        """读取 workspace-local dynamic skill 的 SKILL.md 内容，不存在时返回 None。"""
        skill_dir = WorkspaceService.get_workspace_skills_dir(workspace_id) / dir_name
        if not WorkspaceService._is_workspace_local_dynamic_skill(skill_dir):
            return None
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None
        return skill_md.read_text(encoding="utf-8")

    @staticmethod
    def write_dynamic_skill(workspace_id: int, dir_name: str, content: str) -> None:
        """创建或更新 workspace-local dynamic skill（写入 SKILL.md）。"""
        skills_root = WorkspaceService.get_workspace_skills_dir(workspace_id)
        skills_root.mkdir(parents=True, exist_ok=True)
        skill_dir = skills_root / dir_name
        if skill_dir.exists() and not WorkspaceService._is_workspace_local_dynamic_skill(skill_dir):
            raise ValueError(f"技能 '{dir_name}' 已被受管理 skill 占用")
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    @staticmethod
    def delete_dynamic_skill(workspace_id: int, dir_name: str) -> bool:
        """删除 workspace-local dynamic skill，返回是否成功。"""
        skill_dir = WorkspaceService.get_workspace_skills_dir(workspace_id) / dir_name
        if not WorkspaceService._is_workspace_local_dynamic_skill(skill_dir):
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
        src = WorkspaceService.get_workspace_skills_dir(workspace_id) / dir_name
        if not WorkspaceService._is_workspace_local_dynamic_skill(src):
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
        WorkspaceService._write_skill_origin(
            dst,
            origin="promoted",
            promoted_from_workspace=workspace_id,
            source_skill_id=dir_name,
        )

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
        target_name = skill_id.split("/")[-1] if "/" in skill_id else skill_id
        dst_parent = WorkspaceService.get_workspace_skills_dir(workspace.id)
        dst_parent.mkdir(parents=True, exist_ok=True)
        dst = dst_parent / target_name
        if dst.exists():
            existing_origin = WorkspaceService.read_skill_origin(dst)
            if not existing_origin:
                logger.warning(f"重新同步 skill 跳过：与 workspace-local dynamic skill 同名冲突: {skill_id}")
                return False
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        WorkspaceService._write_skill_origin(dst, origin=cat, source_skill_id=skill_id)
        logger.debug(f"重新同步 skill: {skill_id} → {target_name}")
        return True

    @staticmethod
    def _write_skill_origin(
        skill_dir: Path,
        *,
        origin: str,
        source_skill_id: Optional[str] = None,
        promoted_from_workspace: Optional[int] = None,
        repo_url: Optional[str] = None,
        community_id: Optional[str] = None,
        community_slug: Optional[str] = None,
    ) -> None:
        """在 skill 目录下写入 .skill-origin.json 来源追溯文件。"""
        data = {
            "origin": origin,
            "source_skill_id": source_skill_id,
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
