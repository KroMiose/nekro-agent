"""File-based persistence store for CC model presets."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

from nekro_agent.core.os_env import OsEnv

CC_PRESETS_PATH = Path(OsEnv.DATA_DIR) / "configs" / "cc-model-presets.json"

DEFAULT_PRESET_NAME = "default"


class CCModelPresetItem(BaseModel):
    id: int
    name: str
    description: str = ""
    base_url: str = "https://api.nekro.ai/claude"
    auth_token: str = ""
    api_timeout_ms: str = "3000000"
    model_type: Literal["preset", "manual"] = "preset"
    preset_model: str = "opus"
    anthropic_model: str = ""
    small_fast_model: str = ""
    default_sonnet: str = ""
    default_opus: str = ""
    default_haiku: str = ""
    extra_env: Dict[str, str] = {}
    is_default: bool = False
    create_time: str = ""
    update_time: str = ""

    def to_config_json(self) -> Dict[str, Any]:
        env: Dict[str, str] = {
            "ANTHROPIC_BASE_URL": self.base_url,
            "ANTHROPIC_AUTH_TOKEN": self.auth_token,
            "API_TIMEOUT_MS": self.api_timeout_ms,
        }
        if self.model_type == "preset":
            env.update(self.extra_env)
            return {"env": env, "model": self.preset_model, "includeCoAuthoredBy": False}
        # manual — add non-empty model env vars
        for key, val in [
            ("ANTHROPIC_MODEL", self.anthropic_model),
            ("ANTHROPIC_SMALL_FAST_MODEL", self.small_fast_model),
            ("ANTHROPIC_DEFAULT_SONNET_MODEL", self.default_sonnet),
            ("ANTHROPIC_DEFAULT_OPUS_MODEL", self.default_opus),
            ("ANTHROPIC_DEFAULT_HAIKU_MODEL", self.default_haiku),
        ]:
            if val:
                env[key] = val
        env.update(self.extra_env)
        return {"env": env, "includeCoAuthoredBy": False}


class CCModelPresetsStore:
    def __init__(self, path: Path = CC_PRESETS_PATH):
        self.path = path
        self._default_checked = False

    def _load_raw(self) -> dict:
        if not self.path.exists():
            return {"presets": [], "_next_id": 1}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save_raw(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_default(self) -> "CCModelPresetItem":
        """确保默认预设存在，若不存在则自动创建。"""
        if self._default_checked:
            raw = self._load_raw()
            for p in raw["presets"]:
                if p.get("is_default"):
                    return CCModelPresetItem(**p)
        self._default_checked = True
        raw = self._load_raw()
        for p in raw["presets"]:
            if p.get("is_default"):
                return CCModelPresetItem(**p)
        # 创建默认预设
        now = datetime.now(timezone.utc).isoformat()
        preset_id = raw["_next_id"]
        item = CCModelPresetItem(
            id=preset_id,
            name=DEFAULT_PRESET_NAME,
            description="默认 CC 模型配置（不可删除）",
            is_default=True,
            extra_env={
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
            },
            create_time=now,
            update_time=now,
        )
        raw["presets"].insert(0, item.model_dump())
        raw["_next_id"] = preset_id + 1
        self._save_raw(raw)
        return item

    def get_default(self) -> Optional["CCModelPresetItem"]:
        """获取默认预设。"""
        raw = self._load_raw()
        for p in raw["presets"]:
            if p.get("is_default"):
                return CCModelPresetItem(**p)
        return None

    def list_all(self) -> List[CCModelPresetItem]:
        self.ensure_default()
        raw = self._load_raw()
        return [CCModelPresetItem(**p) for p in raw["presets"]]

    def get_by_id(self, preset_id: int) -> Optional[CCModelPresetItem]:
        raw = self._load_raw()
        for p in raw["presets"]:
            if p["id"] == preset_id:
                return CCModelPresetItem(**p)
        return None

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        raw = self._load_raw()
        for p in raw["presets"]:
            if p["name"] == name and p["id"] != exclude_id:
                return True
        return False

    def create(self, **kwargs) -> CCModelPresetItem:
        raw = self._load_raw()
        now = datetime.now(timezone.utc).isoformat()
        preset_id = raw["_next_id"]
        item = CCModelPresetItem(id=preset_id, create_time=now, update_time=now, **kwargs)
        raw["presets"].append(item.model_dump())
        raw["_next_id"] = preset_id + 1
        self._save_raw(raw)
        return item

    def update(self, preset_id: int, **kwargs) -> Optional[CCModelPresetItem]:
        raw = self._load_raw()
        for i, p in enumerate(raw["presets"]):
            if p["id"] == preset_id:
                # is_default 不允许通过 update 修改
                kwargs.pop("is_default", None)
                p.update(kwargs)
                p["update_time"] = datetime.now(timezone.utc).isoformat()
                raw["presets"][i] = p
                self._save_raw(raw)
                return CCModelPresetItem(**p)
        return None

    def delete(self, preset_id: int) -> str:
        """删除预设。返回 'ok' | 'not_found' | 'protected'"""
        raw = self._load_raw()
        for p in raw["presets"]:
            if p["id"] == preset_id:
                if p.get("is_default"):
                    return "protected"
                raw["presets"] = [x for x in raw["presets"] if x["id"] != preset_id]
                self._save_raw(raw)
                return "ok"
        return "not_found"


cc_presets_store = CCModelPresetsStore()
