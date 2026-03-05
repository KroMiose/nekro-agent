import asyncio
import io
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import SKILLS_LOCAL_DIR, SKILLS_REPOS_DIR
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import (
    AppFileNotFoundError,
    InvalidFileTypeError,
    NotFoundError,
    ValidationError,
)
from nekro_agent.schemas.workspace import AutoInjectSkillsResponse, AutoInjectSkillsUpdate, SkillItem
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.services.workspace.manager import WorkspaceService

router = APIRouter(prefix="/skills", tags=["Skills"])


# ─────────────────────────────────────────────────────────────
# 响应模型
# ─────────────────────────────────────────────────────────────


class SkillListResponse(BaseModel):
    total: int
    items: List[SkillItem]


class AllSkillItem(BaseModel):
    name: str
    display_name: str
    description: str
    source: Literal["builtin", "user", "repo"]
    repo_name: Optional[str] = None


class AllSkillsResponse(BaseModel):
    total: int
    items: List[AllSkillItem]


class SkillReadmeResponse(BaseModel):
    readme: str


class ActionOkResponse(BaseModel):
    ok: bool = True


class SkillUploadResponse(BaseModel):
    name: str
    ok: bool = True


class SkillTreeNode(BaseModel):
    """技能库目录树节点"""

    name: str
    path: str  # 相对于 SKILLS_DIR 的路径
    type: Literal["skill", "repo", "dir", "doc"]
    skill_name: Optional[str] = None
    skill_description: Optional[str] = None
    has_git: bool = False
    repo_url: Optional[str] = None
    repo_branch: Optional[str] = None
    children: Optional[List["SkillTreeNode"]] = None


SkillTreeNode.model_rebuild()


class SkillTreeResponse(BaseModel):
    nodes: List[SkillTreeNode]


class SkillDirEntry(BaseModel):
    """skill 目录内的单个条目"""

    name: str
    rel_path: str  # 相对于 skill 根目录
    type: Literal["file", "dir"]
    size: Optional[int] = None  # 文件大小（字节），仅文件有效


class SkillDirResponse(BaseModel):
    entries: List[SkillDirEntry]


class SkillFileSaveRequest(BaseModel):
    path: str  # 相对于 SKILLS_DIR 的文件路径
    content: str


class CloneRequest(BaseModel):
    repo_url: str
    target_dir: str  # 顶层目录名（不含路径分隔符）


class CloneResponse(BaseModel):
    path: str
    ok: bool = True


class PullRequest(BaseModel):
    path: str  # 相对于 SKILLS_DIR 的路径


class PullResponse(BaseModel):
    ok: bool = True
    output: str = ""


# ── 仓库订阅 ──

class RepoSubscribeRequest(BaseModel):
    repo_url: str
    repo_name: str  # 本地目录名


class RepoMeta(BaseModel):
    repo_name: str
    repo_url: Optional[str] = None
    repo_branch: Optional[str] = None
    subscribed_at: Optional[str] = None
    skill_count: int = 0


class RepoListResponse(BaseModel):
    repos: List[RepoMeta]


# ── 同步到工作区 ──

class SyncToWorkspacesRequest(BaseModel):
    skill_id: str


class SyncToWorkspacesResponse(BaseModel):
    ok: bool = True
    synced_count: int = 0


# ─────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────


_SKILL_MAIN_FILES = frozenset({"SKILL.md", "README.md", "README.txt", "readme.md", "readme.txt", "README"})


def _list_skill_extra_docs(skill_dir: Path, skill_rel_path: str) -> List[SkillTreeNode]:
    """扫描 skill 目录内除主文件以外的 .md / .txt 文档，返回 doc 类型节点列表。"""
    docs: List[SkillTreeNode] = []
    try:
        for f in sorted(skill_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in (".md", ".txt") and f.name not in _SKILL_MAIN_FILES:
                docs.append(
                    SkillTreeNode(
                        name=f.name,
                        path=f"{skill_rel_path}/{f.name}",
                        type="doc",
                        has_git=False,
                    )
                )
    except Exception:
        pass
    return docs


def _parse_skill_meta(skill_dir: Path) -> Optional[Dict[str, str]]:
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


def _parse_frontmatter_name(content: str) -> Optional[str]:
    """从 SKILL.md 内容中提取 frontmatter 的 name 字段，不存在返回 None。"""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:") or line.startswith("name :"):
            _, _, value = line.partition(":")
            return value.strip().strip('"').strip("'") or None
    return None


async def _get_git_info(repo_dir: Path) -> tuple:
    """获取 git 仓库的远程 URL 和当前分支"""
    repo_url: Optional[str] = None
    repo_branch: Optional[str] = None
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "remote",
            "get-url",
            "origin",
            cwd=str(repo_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            repo_url = stdout.decode(errors="replace").strip()
    except Exception:
        pass
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "branch",
            "--show-current",
            cwd=str(repo_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            repo_branch = stdout.decode(errors="replace").strip()
    except Exception:
        pass
    return repo_url, repo_branch


def _scan_directory_sync(directory: Path, base: Path, max_depth: int = 4) -> List[SkillTreeNode]:
    """递归扫描目录，构建技能树（同步）"""
    nodes: List[SkillTreeNode] = []
    if max_depth <= 0:
        return nodes
    try:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return nodes
    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        rel_path = str(entry.relative_to(base))
        has_git = (entry / ".git").is_dir()
        skill_meta = _parse_skill_meta(entry)
        if skill_meta is not None:
            extra_docs = _list_skill_extra_docs(entry, rel_path)
            nodes.append(
                SkillTreeNode(
                    name=entry.name,
                    path=rel_path,
                    type="skill",
                    skill_name=skill_meta["name"],
                    skill_description=skill_meta["description"],
                    has_git=has_git,
                    children=extra_docs if extra_docs else None,
                )
            )
        elif has_git:
            children = _scan_directory_sync(entry, base, max_depth - 1)
            nodes.append(
                SkillTreeNode(
                    name=entry.name,
                    path=rel_path,
                    type="repo",
                    has_git=True,
                    children=children if children else None,
                )
            )
        else:
            children = _scan_directory_sync(entry, base, max_depth - 1)
            if children:
                nodes.append(
                    SkillTreeNode(
                        name=entry.name,
                        path=rel_path,
                        type="dir",
                        has_git=False,
                        children=children,
                    )
                )
    return nodes


def _list_dir_entries(root: Path, current: Path, max_depth: int = 5) -> List[SkillDirEntry]:
    """递归列出目录内所有文件和子目录（跳过 .git 等隐藏目录）"""
    entries: List[SkillDirEntry] = []
    if max_depth <= 0:
        return entries
    try:
        items = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return entries
    for item in items:
        if item.name.startswith("."):
            continue
        rel = str(item.relative_to(root))
        if item.is_dir():
            entries.append(SkillDirEntry(name=item.name, rel_path=rel, type="dir"))
            entries.extend(_list_dir_entries(root, item, max_depth - 1))
        elif item.is_file():
            try:
                size = item.stat().st_size
            except OSError:
                size = None
            entries.append(SkillDirEntry(name=item.name, rel_path=rel, type="file", size=size))
    return entries


async def _build_skill_tree() -> List[SkillTreeNode]:
    """构建完整的技能库树，并填充 git 信息。扫描 local/ 目录。"""
    local_dir = Path(SKILLS_LOCAL_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)
    nodes = await asyncio.to_thread(_scan_directory_sync, local_dir, local_dir)

    async def fill_git_info(node: SkillTreeNode) -> None:
        if node.type == "repo" and node.has_git:
            node_dir = local_dir / node.path
            repo_url, repo_branch = await _get_git_info(node_dir)
            node.repo_url = repo_url
            node.repo_branch = repo_branch
        if node.children:
            await asyncio.gather(*[fill_git_info(child) for child in node.children])

    await asyncio.gather(*[fill_git_info(node) for node in nodes])
    return nodes


# ─────────────────────────────────────────────────────────────
# 路由
# ─────────────────────────────────────────────────────────────


@router.get("/builtin", summary="列出所有内置 skill", response_model=SkillListResponse)
@require_role(Role.Admin)
async def list_builtin_skills(
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillListResponse:
    from nekro_agent.core.os_env import BUILTIN_SKILLS_SOURCE_DIR

    raw = WorkspaceService.list_builtin_skills()
    items = []
    for s in raw:
        skill_dir = Path(BUILTIN_SKILLS_SOURCE_DIR) / s["name"]
        docs = _list_skill_extra_docs(skill_dir, s["name"])
        items.append(SkillItem(name=s["name"], description=s["description"], docs=[d.name for d in docs]))
    return SkillListResponse(total=len(items), items=items)


@router.get("/builtin/{name}", summary="读取内置 skill 内容", response_model=SkillReadmeResponse)
@require_role(Role.Admin)
async def get_builtin_skill_content(
    name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillReadmeResponse:
    from nekro_agent.core.os_env import BUILTIN_SKILLS_SOURCE_DIR

    skill_dir = Path(BUILTIN_SKILLS_SOURCE_DIR) / name
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise NotFoundError(resource=f"内置 skill '{name}'")
    for candidate in ("SKILL.md", "README.md", "README.txt", "readme.md", "readme.txt", "README"):
        f = skill_dir / candidate
        if f.exists():
            return SkillReadmeResponse(readme=f.read_text(encoding="utf-8"))
    raise AppFileNotFoundError(filename=f"builtin/{name}/README")


@router.get("/builtin/{name}/doc", summary="读取内置 skill 附属文档", response_model=SkillReadmeResponse)
@require_role(Role.Admin)
async def get_builtin_skill_doc(
    name: str,
    filename: str = Query(..., description="附属文档文件名，如 install.md"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillReadmeResponse:
    from nekro_agent.core.os_env import BUILTIN_SKILLS_SOURCE_DIR

    if filename in _SKILL_MAIN_FILES or ".." in filename or "/" in filename or "\\" in filename:
        raise ValidationError(reason="文件名不合法")
    skill_dir = Path(BUILTIN_SKILLS_SOURCE_DIR) / name
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise NotFoundError(resource=f"内置 skill '{name}'")
    target = skill_dir / filename
    if not target.exists() or not target.is_file():
        raise NotFoundError(resource=f"builtin/{name}/{filename}")
    return SkillReadmeResponse(readme=target.read_text(encoding="utf-8"))


@router.get("/builtin/{name}/file", summary="读取内置 skill 指定文件", response_model=SkillReadmeResponse)
@require_role(Role.Admin)
async def get_builtin_skill_file(
    name: str,
    path: str = Query(..., description="相对于 skill 目录的文件路径"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillReadmeResponse:
    from nekro_agent.core.os_env import BUILTIN_SKILLS_SOURCE_DIR

    rel = path.strip("/")
    if not rel or ".." in rel.split("/"):
        raise ValidationError(reason="路径不合法")
    skill_dir = Path(BUILTIN_SKILLS_SOURCE_DIR) / name
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise NotFoundError(resource=f"内置 skill '{name}'")
    target = (skill_dir / rel).resolve()
    if not str(target).startswith(str(skill_dir.resolve())):
        raise ValidationError(reason="路径不合法")
    if not target.exists() or not target.is_file():
        raise NotFoundError(resource=f"builtin/{name}/{rel}")
    return SkillReadmeResponse(readme=target.read_text(encoding="utf-8"))


@router.get("/tree", summary="获取 skill 目录树", response_model=SkillTreeResponse)
@require_role(Role.Admin)
async def get_skills_tree(
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillTreeResponse:
    nodes = await _build_skill_tree()
    return SkillTreeResponse(nodes=nodes)


@router.get("/content", summary="读取 skill 内容文件", response_model=SkillReadmeResponse)
@require_role(Role.Admin)
async def get_skill_content(
    path: str = Query(..., description="相对于 local/ 的路径"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillReadmeResponse:
    rel = path.strip("/")
    if not rel or ".." in rel.split("/"):
        raise ValidationError(reason="路径不合法")
    # 依次尝试 local/ 和 repos/
    node_dir: Optional[Path] = None
    for base in (Path(SKILLS_LOCAL_DIR), Path(SKILLS_REPOS_DIR)):
        candidate = base / rel
        if candidate.is_dir():
            node_dir = candidate
            break
    if node_dir is None:
        raise NotFoundError(resource=f"skill '{rel}'")
    for candidate_name in ("SKILL.md", "README.md", "README.txt", "readme.md", "readme.txt", "README"):
        f = node_dir / candidate_name
        if f.exists():
            return SkillReadmeResponse(readme=f.read_text(encoding="utf-8"))
    raise AppFileNotFoundError(filename=f"{rel}/README")


@router.get("/file", summary="读取 skill 目录内的指定文件", response_model=SkillReadmeResponse)
@require_role(Role.Admin)
async def get_skill_file(
    path: str = Query(..., description="相对于 local/ 的文件路径，如 my-skill/install.md"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillReadmeResponse:
    rel = path.strip("/")
    parts = rel.split("/")
    if not rel or ".." in parts or len(parts) < 2:
        raise ValidationError(reason="路径不合法")
    # 依次尝试 local/ 和 repos/
    target: Optional[Path] = None
    for base in (Path(SKILLS_LOCAL_DIR), Path(SKILLS_REPOS_DIR)):
        candidate = base / rel
        if candidate.is_file():
            target = candidate
            break
    if target is None:
        raise NotFoundError(resource=f"file '{rel}'")
    return SkillReadmeResponse(readme=target.read_text(encoding="utf-8"))


@router.get("/dir", summary="列出 skill 目录内所有文件", response_model=SkillDirResponse)
@require_role(Role.Admin)
async def list_skill_dir(
    name: str = Query(..., description="skill 名称（仓库技能用 repo/skill 格式）"),
    source: Literal["builtin", "user", "repo"] = Query("user", description="skill 来源"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillDirResponse:
    from nekro_agent.core.os_env import BUILTIN_SKILLS_SOURCE_DIR

    if ".." in name or name.startswith("."):
        raise ValidationError(reason="skill 名称不合法")

    if source == "builtin":
        if "/" in name or "\\" in name:
            raise ValidationError(reason="内置 skill 名称不合法")
        skill_dir = Path(BUILTIN_SKILLS_SOURCE_DIR) / name
    elif source == "repo":
        # 仓库技能：name 格式为 repo_name/skill_name
        if "\\" in name:
            raise ValidationError(reason="路径不合法")
        skill_dir = Path(SKILLS_REPOS_DIR) / name
    else:
        if "/" in name or "\\" in name:
            raise ValidationError(reason="用户 skill 名称不合法")
        skill_dir = Path(SKILLS_LOCAL_DIR) / name

    if not skill_dir.exists() or not skill_dir.is_dir():
        raise NotFoundError(resource=f"skill '{name}'")

    entries = await asyncio.to_thread(_list_dir_entries, skill_dir, skill_dir)
    return SkillDirResponse(entries=entries)


@router.put("/file", summary="保存用户 skill 文件", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def save_skill_file(
    body: SkillFileSaveRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    local_dir = Path(SKILLS_LOCAL_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)
    rel = body.path.strip("/")
    parts = rel.split("/")
    if not rel or ".." in parts or len(parts) < 2:
        raise ValidationError(reason="路径不合法，需包含 skill 名和文件名")

    target = (local_dir / rel).resolve()
    if not str(target).startswith(str(local_dir.resolve())):
        raise ValidationError(reason="路径不合法，不允许跳出 skills 目录")

    # 一致性校验：如果保存的是 SKILL.md，检查 frontmatter name 与目录名是否一致
    if parts[-1] == "SKILL.md":
        skill_dir_name = parts[0]
        meta = _parse_frontmatter_name(body.content)
        if meta and meta != skill_dir_name:
            raise ValidationError(
                reason=f"SKILL.md 中的 name '{meta}' 与目录名 '{skill_dir_name}' 不一致，请修正"
            )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.content, encoding="utf-8")
    return ActionOkResponse(ok=True)


@router.post("/clone", summary="从 git 仓库克隆独立 skill 到 local/", response_model=CloneResponse)
@require_role(Role.Admin)
async def clone_skill_repo(
    body: CloneRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> CloneResponse:
    local_dir = Path(SKILLS_LOCAL_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)
    target_name = body.target_dir.strip("/").strip()
    if not target_name or "/" in target_name or ".." in target_name or target_name.startswith("."):
        raise ValidationError(reason=f"目标目录名无效: {body.target_dir!r}")
    target_dir = local_dir / target_name
    if target_dir.exists():
        raise ValidationError(reason=f"目录已存在: {target_name}")
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", body.repo_url, str(target_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace").strip()
            raise ValidationError(reason=f"git clone 失败: {err_msg}")
    except ValidationError:
        raise
    except asyncio.TimeoutError as e:
        raise ValidationError(reason="克隆超时（120s）") from e
    except Exception as e:
        raise ValidationError(reason=f"克隆操作失败: {e}") from e

    # 写入 .skill-origin.json
    WorkspaceService._write_skill_origin(target_dir, origin="git", repo_url=body.repo_url)
    return CloneResponse(path=target_name, ok=True)


@router.post("/pull", summary="更新 git 仓库（local 或 repos）", response_model=PullResponse)
@require_role(Role.Admin)
async def pull_skill_repo(
    body: PullRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> PullResponse:
    rel_path = body.path.strip("/")
    if not rel_path or ".." in rel_path.split("/"):
        raise ValidationError(reason=f"路径无效: {body.path!r}")

    # 依次尝试 local/ 和 repos/ 下查找
    repo_dir: Optional[Path] = None
    for base in (Path(SKILLS_LOCAL_DIR), Path(SKILLS_REPOS_DIR)):
        candidate = base / rel_path
        if candidate.is_dir() and (candidate / ".git").is_dir():
            repo_dir = candidate
            break
    if repo_dir is None:
        raise NotFoundError(resource=f"git 仓库 '{rel_path}'")

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "pull", cwd=str(repo_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout + stderr).decode(errors="replace").strip()
        if proc.returncode != 0:
            raise ValidationError(reason=f"git pull 失败: {output}")
    except ValidationError:
        raise
    except asyncio.TimeoutError as e:
        raise ValidationError(reason="更新超时（120s）") from e
    except Exception as e:
        raise ValidationError(reason=f"更新操作失败: {e}") from e
    return PullResponse(ok=True, output=output)


@router.get("/all", summary="列出所有可用技能候选（内置 + local + repos）", response_model=AllSkillsResponse)
@require_role(Role.Admin)
async def list_all_skills(
    _current_user: DBUser = Depends(get_current_active_user),
) -> AllSkillsResponse:
    raw = WorkspaceService.list_all_skills()
    items = [AllSkillItem(
        name=s["name"],
        display_name=s["display_name"],
        description=s["description"],
        source=s["source"],  # type: ignore[arg-type]
        repo_name=s.get("repo_name"),
    ) for s in raw]
    return AllSkillsResponse(total=len(items), items=items)


@router.get("/auto-inject", summary="获取自动注入技能列表", response_model=AutoInjectSkillsResponse)
@require_role(Role.Admin)
async def get_auto_inject_skills(
    _current_user: DBUser = Depends(get_current_active_user),
) -> AutoInjectSkillsResponse:
    from nekro_agent.core.auto_inject_skills import get_auto_inject_skills as _get

    return AutoInjectSkillsResponse(skills=_get())


@router.put("/auto-inject", summary="更新自动注入技能列表", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_auto_inject_skills(
    body: AutoInjectSkillsUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    from nekro_agent.core.auto_inject_skills import set_auto_inject_skills as _set

    _set(body.skills)
    return ActionOkResponse(ok=True)


@router.get("", summary="列出全局 skill 资源库（扁平列表，仅 local/）", response_model=SkillListResponse)
@require_role(Role.Admin)
async def list_skills(
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillListResponse:
    raw = WorkspaceService.list_global_skills()
    items = [SkillItem(name=s["name"], description=s["description"]) for s in raw]
    return SkillListResponse(total=len(items), items=items)


@router.post("", summary="上传 skill（zip 包）到 local/", response_model=SkillUploadResponse)
@require_role(Role.Admin)
async def upload_skill(
    file: UploadFile = File(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillUploadResponse:
    filename = file.filename or ""
    if not filename.endswith(".zip"):
        raise InvalidFileTypeError(file_type=filename.rsplit(".", 1)[-1] if "." in filename else "unknown")
    content = await file.read()
    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise ValidationError(reason="上传的文件不是有效的 zip 压缩包")
    local_dir = Path(SKILLS_LOCAL_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = zf.namelist()
        if not names:
            raise ValidationError(reason="zip 包为空")
        top_dirs = {n.split("/")[0] for n in names if n.split("/")[0]}
        if len(top_dirs) != 1:
            raise ValidationError(reason="zip 包必须包含唯一的顶层目录作为 skill 名称")
        skill_name = top_dirs.pop()
        if not skill_name or skill_name.startswith("."):
            raise ValidationError(reason=f"skill 名称无效: {skill_name}")

        # 一致性校验：检查 zip 中 SKILL.md 的 frontmatter name
        skill_md_entry = f"{skill_name}/SKILL.md"
        if skill_md_entry in names:
            with zf.open(skill_md_entry) as f:
                md_content = f.read().decode("utf-8", errors="replace")
                fm_name = _parse_frontmatter_name(md_content)
                if fm_name and fm_name != skill_name:
                    raise ValidationError(
                        reason=f"SKILL.md 中的 name '{fm_name}' 与目录名 '{skill_name}' 不一致"
                    )

        target_dir = local_dir / skill_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        zf.extractall(local_dir)

    # 写入 .skill-origin.json
    WorkspaceService._write_skill_origin(local_dir / skill_name, origin="manual")
    return SkillUploadResponse(name=skill_name, ok=True)


@router.delete("/{name}", summary="删除 skill（local/）", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def delete_skill(
    name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    skill_dir = Path(SKILLS_LOCAL_DIR) / name
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise NotFoundError(resource=f"skill '{name}'")
    shutil.rmtree(skill_dir)
    return ActionOkResponse(ok=True)


@router.get("/{name}/readme", summary="读取 skill README（local/）", response_model=SkillReadmeResponse)
@require_role(Role.Admin)
async def get_skill_readme(
    name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> SkillReadmeResponse:
    skill_dir = Path(SKILLS_LOCAL_DIR) / name
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise NotFoundError(resource=f"skill '{name}'")
    for candidate in ("SKILL.md", "README.md", "README.txt", "readme.md", "readme.txt", "README"):
        readme_path = skill_dir / candidate
        if readme_path.exists():
            return SkillReadmeResponse(readme=readme_path.read_text(encoding="utf-8"))
    raise AppFileNotFoundError(filename=f"{name}/README")


# ── 仓库订阅 ──────────────────────────────────────────────────


@router.get("/repos", summary="列出已订阅仓库", response_model=RepoListResponse)
@require_role(Role.Admin)
async def list_repos(
    _current_user: DBUser = Depends(get_current_active_user),
) -> RepoListResponse:
    repos_dir = Path(SKILLS_REPOS_DIR)
    repos_dir.mkdir(parents=True, exist_ok=True)
    repos: List[RepoMeta] = []
    for d in sorted(repos_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        meta_path = d / ".repo-meta.json"
        meta_data: Dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        # 统计内部 skill 数量
        skill_count = sum(1 for sd in d.iterdir() if sd.is_dir() and not sd.name.startswith(".") and (sd / "SKILL.md").exists())
        repo_url_val = meta_data.get("repo_url")
        repos.append(RepoMeta(
            repo_name=d.name,
            repo_url=repo_url_val if isinstance(repo_url_val, str) else None,
            subscribed_at=meta_data.get("subscribed_at"),
            skill_count=skill_count,
        ))
    return RepoListResponse(repos=repos)


@router.post("/repos/subscribe", summary="订阅技能仓库（git clone 到 repos/）", response_model=CloneResponse)
@require_role(Role.Admin)
async def subscribe_repo(
    body: RepoSubscribeRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> CloneResponse:
    repos_dir = Path(SKILLS_REPOS_DIR)
    repos_dir.mkdir(parents=True, exist_ok=True)
    repo_name = body.repo_name.strip("/").strip()
    if not repo_name or "/" in repo_name or ".." in repo_name or repo_name.startswith("."):
        raise ValidationError(reason=f"仓库名无效: {body.repo_name!r}")
    target_dir = repos_dir / repo_name
    if target_dir.exists():
        raise ValidationError(reason=f"仓库已存在: {repo_name}")
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", body.repo_url, str(target_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace").strip()
            raise ValidationError(reason=f"git clone 失败: {err_msg}")
    except ValidationError:
        raise
    except asyncio.TimeoutError as e:
        raise ValidationError(reason="克隆超时（120s）") from e
    except Exception as e:
        raise ValidationError(reason=f"克隆操作失败: {e}") from e

    # 写入 .repo-meta.json
    import datetime as _dt
    meta = {
        "repo_url": body.repo_url,
        "community_id": None,
        "community_slug": None,
        "subscribed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
    (target_dir / ".repo-meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return CloneResponse(path=repo_name, ok=True)


@router.post("/repos/{repo_name}/pull", summary="更新订阅仓库（git pull）", response_model=PullResponse)
@require_role(Role.Admin)
async def pull_repo(
    repo_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> PullResponse:
    if ".." in repo_name or "/" in repo_name or repo_name.startswith("."):
        raise ValidationError(reason="仓库名无效")
    repo_dir = Path(SKILLS_REPOS_DIR) / repo_name
    if not repo_dir.is_dir():
        raise NotFoundError(resource=f"仓库 '{repo_name}'")
    if not (repo_dir / ".git").is_dir():
        raise ValidationError(reason=f"该目录不是 git 仓库: {repo_name}")
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "pull", cwd=str(repo_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout + stderr).decode(errors="replace").strip()
        if proc.returncode != 0:
            raise ValidationError(reason=f"git pull 失败: {output}")
    except ValidationError:
        raise
    except asyncio.TimeoutError as e:
        raise ValidationError(reason="更新超时（120s）") from e
    except Exception as e:
        raise ValidationError(reason=f"更新操作失败: {e}") from e

    # 自动同步该仓库内所有技能到引用它们的工作区
    synced = 0
    for skill_dir in sorted(repo_dir.iterdir()):
        if skill_dir.is_dir() and not skill_dir.name.startswith(".") and (skill_dir / "SKILL.md").exists():
            skill_id = f"{repo_name}/{skill_dir.name}"
            synced += await WorkspaceService.sync_skill_to_all_workspaces(skill_id)

    return PullResponse(ok=True, output=f"{output}\n同步了 {synced} 个工作区" if synced else output)


@router.delete("/repos/{repo_name}", summary="取消订阅仓库", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def unsubscribe_repo(
    repo_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    if ".." in repo_name or "/" in repo_name or repo_name.startswith("."):
        raise ValidationError(reason="仓库名无效")
    repo_dir = Path(SKILLS_REPOS_DIR) / repo_name
    if not repo_dir.is_dir():
        raise NotFoundError(resource=f"仓库 '{repo_name}'")
    shutil.rmtree(repo_dir)
    return ActionOkResponse(ok=True)


# ── 同步到工作区 ──────────────────────────────────────────────


@router.post("/sync-to-workspaces", summary="同步技能到所有使用它的工作区", response_model=SyncToWorkspacesResponse)
@require_role(Role.Admin)
async def sync_skill_to_workspaces(
    body: SyncToWorkspacesRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> SyncToWorkspacesResponse:
    count = await WorkspaceService.sync_skill_to_all_workspaces(body.skill_id)
    return SyncToWorkspacesResponse(ok=True, synced_count=count)
