from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CCModelPresetCreate(BaseModel):
    name: str = Field(..., max_length=64)
    description: str = Field(default="", max_length=512)
    base_url: str = Field(default="https://api.nekro.ai/claude", max_length=256)
    auth_token: str = Field(default="", max_length=256)
    api_timeout_ms: str = Field(default="3000000", max_length=16)
    model_type: Literal["preset", "manual"] = "preset"
    preset_model: str = Field(default="opus", max_length=64)
    anthropic_model: str = Field(default="", max_length=128)
    small_fast_model: str = Field(default="", max_length=128)
    default_sonnet: str = Field(default="", max_length=128)
    default_opus: str = Field(default="", max_length=128)
    default_haiku: str = Field(default="", max_length=128)
    extra_env: Dict[str, str] = {}


class CCModelPresetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = Field(default=None, max_length=512)
    base_url: Optional[str] = Field(default=None, max_length=256)
    auth_token: Optional[str] = Field(default=None, max_length=256)
    api_timeout_ms: Optional[str] = Field(default=None, max_length=16)
    model_type: Optional[Literal["preset", "manual"]] = None
    preset_model: Optional[str] = Field(default=None, max_length=64)
    anthropic_model: Optional[str] = Field(default=None, max_length=128)
    small_fast_model: Optional[str] = Field(default=None, max_length=128)
    default_sonnet: Optional[str] = Field(default=None, max_length=128)
    default_opus: Optional[str] = Field(default=None, max_length=128)
    default_haiku: Optional[str] = Field(default=None, max_length=128)
    extra_env: Optional[Dict[str, str]] = None


class CCModelPresetInfo(BaseModel):
    id: int
    name: str
    description: str
    base_url: str
    auth_token: str
    api_timeout_ms: str
    model_type: str
    preset_model: str
    anthropic_model: str
    small_fast_model: str
    default_sonnet: str
    default_opus: str
    default_haiku: str
    extra_env: Dict[str, str]
    is_default: bool
    create_time: str
    update_time: str
    config_json: Dict[str, Any]


class CCModelPresetListResponse(BaseModel):
    total: int
    items: List[CCModelPresetInfo]
