"""Pydantic schemas for the WebUI deployment API."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UnavailableReason(BaseModel):
    code: str
    message: str


class DeploymentCapabilitiesResponse(BaseModel):
    enabled: bool
    provider: str | None = None
    platform: str = "unknown"
    protocol_version: str | None = None
    instance_id: str | None = None
    supports: dict[str, bool] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)
    unavailable_reason: UnavailableReason | None = None


class DeploymentInstanceResponse(BaseModel):
    channel: str | None = None
    image: str | None = None
    container_status: str | None = None
    app_health: str | None = None
    docker_ok: bool = False
    compose_ok: bool = False


class DeploymentAgentVersionResponse(BaseModel):
    current_version: str
    latest_version: str | None = None
    update_available: bool = False
    checked: bool = False
    error_code: str | None = None
    error_message: str | None = None


class DeploymentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["stable", "preview", "rollback"]
    backup: bool = True
    update_sandbox: bool = True
    update_cc_sandbox: bool = False
    restore_pre_preview: bool = False
    client_request_id: str | None = None


class DeploymentBackupSummary(BaseModel):
    backup_id: str
    filename: str
    name: str | None = None
    created_at: str
    size_bytes: int


class DeploymentBackupsResponse(BaseModel):
    backups: list[DeploymentBackupSummary] = Field(default_factory=list)


class DeploymentCreateBackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    client_request_id: str | None = None


class DeploymentRestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backup_id: str
    client_request_id: str | None = None
