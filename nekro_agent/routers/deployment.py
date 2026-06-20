"""Deployment update proxy routes."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from nekro_agent.models.db_user import DBUser
from nekro_agent.services.deployment.client import DeploymentDaemonClient, DeploymentProxyError
from nekro_agent.services.deployment.schemas import (
    DeploymentAgentVersionResponse,
    DeploymentBackupsResponse,
    DeploymentCapabilitiesResponse,
    DeploymentCreateBackupRequest,
    DeploymentInstanceResponse,
    DeploymentJobLogsResponse,
    DeploymentJobResponse,
    DeploymentProxyErrorResponse,
    DeploymentRestoreRequest,
    DeploymentUpdateRequest,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.tools.common_util import compare_semver, get_app_version

router = APIRouter(prefix="/deployment", tags=["Deployment"])
LATEST_AGENT_VERSION_URL = "https://cloud.nekro.ai/api/na/latest-version"
LatestAgentVersionFetcher = Callable[[], Awaitable[str | None]]


def get_deployment_client() -> DeploymentDaemonClient:
    return DeploymentDaemonClient()


async def fetch_latest_agent_version() -> str | None:
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        response = await client.get(LATEST_AGENT_VERSION_URL)
        response.raise_for_status()
    return _extract_latest_agent_version(response.json())


def _extract_latest_agent_version(payload: Any) -> str | None:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    latest_version = data.get("latestVersion")
    return str(latest_version).strip() if latest_version else None


def get_latest_agent_version_fetcher() -> LatestAgentVersionFetcher:
    return fetch_latest_agent_version


def _normalize_version(value: str | None) -> str:
    return (value or "").strip().lstrip("vV")


async def build_agent_version_response(
    fetch_latest_version: LatestAgentVersionFetcher,
) -> DeploymentAgentVersionResponse:
    current_version = get_app_version()
    normalized_current = _normalize_version(current_version)
    if not normalized_current or normalized_current == "unknown":
        return DeploymentAgentVersionResponse(
            current_version=current_version,
            checked=False,
            error_code="local_version_unknown",
            error_message="无法读取当前 Nekro Agent 版本",
        )

    try:
        latest_version = await fetch_latest_version()
    except (httpx.HTTPError, ValueError) as exc:
        return DeploymentAgentVersionResponse(
            current_version=current_version,
            checked=False,
            error_code="latest_version_unavailable",
            error_message=f"无法获取 Nekro Agent 最新版本: {exc}",
        )

    normalized_latest = _normalize_version(latest_version)
    if not normalized_latest:
        return DeploymentAgentVersionResponse(
            current_version=current_version,
            latest_version=latest_version,
            checked=False,
            error_code="latest_version_missing",
            error_message="云端版本接口未返回有效的 Nekro Agent 最新版本",
        )

    return DeploymentAgentVersionResponse(
        current_version=current_version,
        latest_version=latest_version,
        update_available=compare_semver(normalized_current, normalized_latest) < 0,
        checked=True,
    )


def _error_response(exc: DeploymentProxyError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.payload())


DEPLOYMENT_ERROR_RESPONSES = {
    400: {"model": DeploymentProxyErrorResponse},
    404: {"model": DeploymentProxyErrorResponse},
    409: {"model": DeploymentProxyErrorResponse},
    502: {"model": DeploymentProxyErrorResponse},
    503: {"model": DeploymentProxyErrorResponse},
}


@router.get("/capabilities", summary="获取部署更新能力", response_model=DeploymentCapabilitiesResponse)
async def get_deployment_capabilities(
    _current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> DeploymentCapabilitiesResponse:
    return await client.get_capabilities()


@router.get(
    "/instance",
    summary="获取当前部署实例",
    response_model=DeploymentInstanceResponse,
    responses=DEPLOYMENT_ERROR_RESPONSES,
)
async def get_deployment_instance(
    _current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> DeploymentInstanceResponse | JSONResponse:
    try:
        return await client.get_instance()
    except DeploymentProxyError as exc:
        return _error_response(exc)


@router.get("/agent-version", summary="检查 Nekro Agent 应用版本", response_model=DeploymentAgentVersionResponse)
async def get_deployment_agent_version(
    _current_user: DBUser = Depends(get_current_active_user),
    fetch_latest_version: LatestAgentVersionFetcher = Depends(get_latest_agent_version_fetcher),
) -> DeploymentAgentVersionResponse:
    return await build_agent_version_response(fetch_latest_version)


@router.post(
    "/update",
    summary="创建部署更新任务",
    response_model=DeploymentJobResponse,
    responses=DEPLOYMENT_ERROR_RESPONSES,
)
async def create_deployment_update(
    body: DeploymentUpdateRequest,
    current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> dict[str, Any] | JSONResponse:
    try:
        return await client.create_update(body, username=current_user.username)
    except DeploymentProxyError as exc:
        return _error_response(exc)


@router.get(
    "/backups",
    summary="查询部署备份列表",
    response_model=DeploymentBackupsResponse,
    responses=DEPLOYMENT_ERROR_RESPONSES,
)
async def list_deployment_backups(
    name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    _current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> DeploymentBackupsResponse | JSONResponse:
    try:
        return await client.list_backups(name=name, limit=limit)
    except DeploymentProxyError as exc:
        return _error_response(exc)


@router.post(
    "/backup",
    summary="创建部署备份任务",
    response_model=DeploymentJobResponse,
    responses=DEPLOYMENT_ERROR_RESPONSES,
)
async def create_deployment_backup(
    body: DeploymentCreateBackupRequest,
    current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> dict[str, Any] | JSONResponse:
    try:
        return await client.create_backup(body, username=current_user.username)
    except DeploymentProxyError as exc:
        return _error_response(exc)


@router.post(
    "/restore",
    summary="创建部署还原任务",
    response_model=DeploymentJobResponse,
    responses=DEPLOYMENT_ERROR_RESPONSES,
)
async def create_deployment_restore(
    body: DeploymentRestoreRequest,
    current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> dict[str, Any] | JSONResponse:
    try:
        return await client.create_restore(body, username=current_user.username)
    except DeploymentProxyError as exc:
        return _error_response(exc)


@router.get(
    "/jobs/{job_id}",
    summary="查询部署更新任务",
    response_model=DeploymentJobResponse,
    responses=DEPLOYMENT_ERROR_RESPONSES,
)
async def get_deployment_job(
    job_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> dict[str, Any] | JSONResponse:
    try:
        return await client.get_job(job_id)
    except DeploymentProxyError as exc:
        return _error_response(exc)


@router.get(
    "/jobs/{job_id}/logs",
    summary="查询部署更新日志",
    response_model=DeploymentJobLogsResponse,
    responses=DEPLOYMENT_ERROR_RESPONSES,
)
async def get_deployment_job_logs(
    job_id: str,
    after_seq: int | None = Query(default=None, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    _current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> dict[str, Any] | JSONResponse:
    try:
        return await client.get_job_logs(job_id, after_seq=after_seq, limit=limit)
    except DeploymentProxyError as exc:
        return _error_response(exc)


@router.get("/jobs/{job_id}/events", summary="代理部署更新事件流")
async def stream_deployment_job_events(
    request: Request,
    job_id: str,
    after_seq: int | None = Query(default=None, ge=0),
    _current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> EventSourceResponse:
    async def event_generator():
        try:
            async for event in client.stream_events(job_id, after_seq=after_seq):
                if await request.is_disconnected():
                    return
                yield event
        except DeploymentProxyError as exc:
            yield {
                "event": "error",
                "data": json.dumps(exc.payload()["error"], ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())


@router.post(
    "/jobs/{job_id}/cancel",
    summary="取消部署更新任务",
    response_model=DeploymentJobResponse,
    responses=DEPLOYMENT_ERROR_RESPONSES,
)
async def cancel_deployment_job(
    job_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
    client: DeploymentDaemonClient = Depends(get_deployment_client),
) -> dict[str, Any] | JSONResponse:
    try:
        return await client.cancel_job(job_id)
    except DeploymentProxyError as exc:
        return _error_response(exc)
