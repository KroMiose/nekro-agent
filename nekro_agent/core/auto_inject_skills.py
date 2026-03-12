"""Manage the list of skills to auto-inject when creating a new workspace."""

import json
from pathlib import Path
from typing import List

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv

_AUTO_INJECT_PATH = Path(OsEnv.DATA_DIR) / "configs" / "auto-inject-skills.json"
_DEFAULT_BUILTIN_SKILLS = [
    "agent-browser",
    "git-github-workflow",
    "skill-creator",
]


def _get_default_skills() -> List[str]:
    """Return the built-in skills that should be enabled by default."""
    try:
        from nekro_agent.services.workspace.manager import WorkspaceService

        valid_names = {skill["name"] for skill in WorkspaceService.list_all_skills()}
        defaults = [name for name in _DEFAULT_BUILTIN_SKILLS if name in valid_names]
        return defaults or _DEFAULT_BUILTIN_SKILLS.copy()
    except Exception as e:
        logger.warning(f"获取默认自动注入技能失败，将回退到静态列表: {e}")
        return _DEFAULT_BUILTIN_SKILLS.copy()


def _ensure_file() -> None:
    _AUTO_INJECT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _AUTO_INJECT_PATH.exists():
        _AUTO_INJECT_PATH.write_text(
            json.dumps({"skills": _get_default_skills()}, indent=2),
            encoding="utf-8",
        )


def get_auto_inject_skills() -> List[str]:
    """Return the list of skill names marked for auto-injection."""
    _ensure_file()
    try:
        data = json.loads(_AUTO_INJECT_PATH.read_text(encoding="utf-8"))
        return list(data.get("skills", []))
    except Exception as e:
        logger.warning(f"读取 auto-inject-skills.json 失败: {e}")
        return []


def set_auto_inject_skills(names: List[str]) -> None:
    """Overwrite the auto-inject skill list."""
    _ensure_file()
    _AUTO_INJECT_PATH.write_text(json.dumps({"skills": names}, indent=2), encoding="utf-8")
