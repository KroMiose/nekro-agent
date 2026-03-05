"""Manage the list of skills to auto-inject when creating a new workspace."""

import json
from pathlib import Path
from typing import List

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv

_AUTO_INJECT_PATH = Path(OsEnv.DATA_DIR) / "configs" / "auto-inject-skills.json"


def _ensure_file() -> None:
    _AUTO_INJECT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _AUTO_INJECT_PATH.exists():
        _AUTO_INJECT_PATH.write_text(json.dumps({"skills": []}, indent=2), encoding="utf-8")


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
