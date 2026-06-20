"""Client for proxying WebUI deployment requests to the NA-Tools daemon."""

from __future__ import annotations

import json
import os
import re
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import aclosing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from socksio.exceptions import ProtocolError as SocksProtocolError

from nekro_agent.services.deployment.schemas import (
    DeploymentBackupsResponse,
    DeploymentCapabilitiesResponse,
    DeploymentCreateBackupRequest,
    DeploymentInstanceResponse,
    DeploymentRestoreRequest,
    DeploymentUpdateRequest,
    UnavailableReason,
)
from nekro_agent.services.deployment.signer import build_signature_headers

DEFAULT_DAEMON_API_BASE = "http://na-tools.local/v1"

_TRUE_VALUES = {"1", "true", "yes", "on"}
_HIDDEN_KEY_PARTS = ("token", "secret", "password", "api_key", "authorization", "signature")
_DROPPED_KEYS = {
    "data_dir",
    "compose_file",
    "env_file",
    "token_file",
    "token_file_path",
    "daemon_token",
    "health_url",
    "expose_port",
    "api_base",
    "socks_proxy",
    "backup_file",
}
_INTERNAL_ENDPOINT_RE = re.compile(
    r"(?i)\b(?:https?|socks5h?)://(?:127\.0\.0\.1|localhost|host\.docker\.internal|na-tools\.local)(?::\d+)?[^\s'\",)]*"
)
_UNIX_ABSOLUTE_PATH_RE = re.compile(r"(?<!:)/(?:home|root|srv|var|opt|etc|tmp|usr|mnt|data)/[^\s'\",)]*")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s'\",)]+")


@dataclass(frozen=True)
class DeploymentDaemonConfig:
    enabled: bool
    api_base: str = DEFAULT_DAEMON_API_BASE
    socks_proxy: str | None = None
    instance_id: str | None = None
    token_file: str | None = None

    @classmethod
    def from_env(cls) -> "DeploymentDaemonConfig":
        enabled = os.getenv("NA_TOOLS_DAEMON_ENABLED", "").strip().lower() in _TRUE_VALUES
        api_base = (os.getenv("NA_TOOLS_DAEMON_API_BASE") or DEFAULT_DAEMON_API_BASE).strip()
        return cls(
            enabled=enabled,
            api_base=api_base.rstrip("/") or DEFAULT_DAEMON_API_BASE,
            socks_proxy=(os.getenv("NA_TOOLS_DAEMON_SOCKS") or "").strip() or None,
            instance_id=(os.getenv("NA_TOOLS_DAEMON_INSTANCE_ID") or "").strip() or None,
            token_file=(os.getenv("NA_TOOLS_DAEMON_TOKEN_FILE") or "").strip() or None,
        )


class DeploymentProxyError(Exception):
    """Structured deployment proxy error returned to the WebUI."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = sanitize_public_payload(dict(details or {}))

    def payload(self) -> dict[str, dict[str, Any]]:
        return {
            "error": {
                "code": self.code,
                "message": sanitize_text(self.message),
                "details": self.details,
            }
        }


class DeploymentDaemonClient:
    """Lazy daemon client used by deployment routes."""

    def __init__(
        self,
        *,
        config_loader: Callable[[], DeploymentDaemonConfig] = DeploymentDaemonConfig.from_env,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config_loader = config_loader
        self._transport = transport

    async def get_capabilities(self) -> DeploymentCapabilitiesResponse:
        config = self._config_loader()
        unavailable = self._preflight_unavailable(config)
        if unavailable is not None:
            return self._unavailable_capabilities(unavailable)

        try:
            payload = await self._request_json("GET", "/capabilities", config=config)
        except DeploymentProxyError as exc:
            return self._unavailable_capabilities(UnavailableReason(code=exc.code, message=exc.message))

        unavailable_reason = _normalize_unavailable_reason(payload.get("unavailable_reason"))
        return DeploymentCapabilitiesResponse(
            enabled=bool(payload.get("enabled")) and unavailable_reason is None,
            provider=_safe_optional_str(payload.get("provider")),
            platform=_safe_optional_str(payload.get("platform")) or "unknown",
            protocol_version=_safe_optional_str(payload.get("protocol_version")),
            instance_id=_safe_optional_str(payload.get("instance_id")),
            supports=_bool_dict(payload.get("supports")),
            limits=sanitize_public_payload(payload.get("limits") if isinstance(payload.get("limits"), dict) else {}),
            unavailable_reason=unavailable_reason,
        )

    async def get_instance(self) -> DeploymentInstanceResponse:
        config = self._load_available_config()
        payload = await self._request_json("GET", "/instances/current", config=config)
        container = payload.get("container") if isinstance(payload.get("container"), dict) else {}
        docker = payload.get("docker") if isinstance(payload.get("docker"), dict) else {}
        available = payload.get("available")
        app_health = _safe_optional_str(payload.get("app_health"))
        if app_health is None and isinstance(available, bool):
            app_health = "ok" if available else "unavailable"
        return DeploymentInstanceResponse(
            channel=_safe_optional_str(payload.get("channel")),
            image=_safe_optional_str(container.get("image")),
            container_status=_safe_optional_str(container.get("status")),
            app_health=app_health,
            docker_ok=bool(docker.get("docker_installed")),
            compose_ok=bool(docker.get("compose_installed")),
        )

    async def create_update(self, request: DeploymentUpdateRequest, *, username: str) -> dict[str, Any]:
        config = self._load_available_config()
        payload = request.model_dump(exclude_none=True)
        payload["instance_id"] = config.instance_id
        payload["requested_by"] = {
            "source": "nekro-agent-webui",
            "username": username,
        }
        return await self._request_json("POST", "/jobs/update", config=config, json_body=payload, timeout=30.0)

    async def list_backups(
        self,
        *,
        name: str | None = None,
        limit: int = 50,
    ) -> DeploymentBackupsResponse:
        config = self._load_available_config()
        params: dict[str, Any] = {"limit": limit}
        if name:
            params["name"] = name
        payload = await self._request_json("GET", "/backups", config=config, params=params)
        return DeploymentBackupsResponse.model_validate(payload)

    async def create_backup(self, request: DeploymentCreateBackupRequest, *, username: str) -> dict[str, Any]:
        config = self._load_available_config()
        payload = request.model_dump(exclude_none=True)
        payload["instance_id"] = config.instance_id
        payload["requested_by"] = {
            "source": "nekro-agent-webui",
            "username": username,
        }
        return await self._request_json("POST", "/jobs/backup", config=config, json_body=payload, timeout=30.0)

    async def create_restore(self, request: DeploymentRestoreRequest, *, username: str) -> dict[str, Any]:
        config = self._load_available_config()
        payload = request.model_dump(exclude_none=True)
        payload["instance_id"] = config.instance_id
        payload["requested_by"] = {
            "source": "nekro-agent-webui",
            "username": username,
        }
        return await self._request_json("POST", "/jobs/restore", config=config, json_body=payload, timeout=30.0)

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return await self._request_json("GET", f"/jobs/{job_id}", config=self._load_available_config())

    async def get_job_logs(
        self,
        job_id: str,
        *,
        after_seq: int | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        params: dict[str, int] = {"limit": limit}
        if after_seq is not None:
            params["after_seq"] = after_seq
        return await self._request_json("GET", f"/jobs/{job_id}/logs", config=self._load_available_config(), params=params)

    async def cancel_job(self, job_id: str) -> dict[str, Any]:
        capabilities = await self.get_capabilities()
        if not capabilities.supports.get("cancel"):
            raise DeploymentProxyError(404, "unsupported_operation", "当前 daemon 不支持取消任务")
        return await self._request_json("POST", f"/jobs/{job_id}/cancel", config=self._load_available_config())

    async def stream_events(self, job_id: str, *, after_seq: int | None = None) -> AsyncIterator[dict[str, str]]:
        config = self._load_available_config()
        params = {"after_seq": after_seq} if after_seq is not None else None
        async with aclosing(self._request_sse(f"/jobs/{job_id}/events", config=config, params=params)) as events:
            async for event in events:
                yield event

    def _load_available_config(self) -> DeploymentDaemonConfig:
        config = self._config_loader()
        unavailable = self._preflight_unavailable(config)
        if unavailable is not None:
            raise DeploymentProxyError(503, unavailable.code, unavailable.message)
        return config

    def _preflight_unavailable(self, config: DeploymentDaemonConfig) -> UnavailableReason | None:
        if not config.enabled:
            return UnavailableReason(
                code="daemon_disabled",
                message="未启用在线更新，请启用 NA-Tools daemon 后再重试",
            )
        if not config.instance_id:
            return UnavailableReason(
                code="daemon_instance_missing",
                message="未找到 NA-Tools daemon 实例绑定信息，请重新运行 na-tools bind",
            )
        if not config.token_file:
            return UnavailableReason(
                code="daemon_token_missing",
                message="未找到 NA-Tools daemon token，请重新运行 na-tools bind 或检查 daemon 配置",
            )
        token_path = Path(config.token_file)
        if not token_path.is_file():
            return UnavailableReason(
                code="daemon_token_missing",
                message="未找到 NA-Tools daemon token，请重新运行 na-tools bind 或检查 daemon 配置",
            )
        if not token_path.read_bytes().strip():
            return UnavailableReason(
                code="daemon_token_missing",
                message="NA-Tools daemon token 为空，请重新运行 na-tools bind",
            )
        return None

    @staticmethod
    def _unavailable_capabilities(reason: UnavailableReason) -> DeploymentCapabilitiesResponse:
        return DeploymentCapabilitiesResponse(
            enabled=False,
            provider=None,
            platform="unknown",
            protocol_version=None,
            instance_id=None,
            supports={},
            limits={},
            unavailable_reason=UnavailableReason(code=reason.code, message=sanitize_text(reason.message)),
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        config: DeploymentDaemonConfig,
        json_body: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        timeout: float = 8.0,
    ) -> dict[str, Any]:
        request = self._build_request(method, path, config=config, json_body=json_body, params=params)
        try:
            async with self._create_client(config, timeout=timeout) as client:
                response = await client.request(
                    method.upper(),
                    request.url,
                    content=request.body,
                    headers=request.headers,
                )
        except httpx.TimeoutException as exc:
            raise DeploymentProxyError(503, "daemon_unavailable", "NA-Tools daemon 请求超时") from exc
        except httpx.RequestError as exc:
            raise DeploymentProxyError(503, "daemon_unavailable", "无法连接 NA-Tools daemon") from exc
        except SocksProtocolError as exc:
            raise DeploymentProxyError(503, "daemon_unavailable", "NA-Tools daemon SOCKS 代理响应无效") from exc

        payload = _json_payload(response)
        if response.status_code >= 400:
            raise _daemon_error(response.status_code, payload)
        if not isinstance(payload, dict):
            raise DeploymentProxyError(502, "daemon_protocol_error", "NA-Tools daemon 返回了无效响应")
        return sanitize_public_payload(payload)

    async def _request_sse(
        self,
        path: str,
        *,
        config: DeploymentDaemonConfig,
        params: Mapping[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        request = self._build_request("GET", path, config=config, params=params)
        try:
            async with self._create_client(config, timeout=httpx.Timeout(connect=8.0, read=None, write=8.0, pool=8.0)) as client:
                async with client.stream("GET", request.url, headers={**request.headers, "Accept": "text/event-stream"}) as response:
                    if response.status_code >= 400:
                        payload = await _json_payload_from_streaming_response(response)
                        raise _daemon_error(response.status_code, payload)
                    async for event in _iter_sse_events(response):
                        yield event
        except httpx.TimeoutException as exc:
            raise DeploymentProxyError(503, "daemon_unavailable", "NA-Tools daemon 事件流超时") from exc
        except httpx.RequestError as exc:
            raise DeploymentProxyError(503, "daemon_unavailable", "无法连接 NA-Tools daemon 事件流") from exc
        except SocksProtocolError as exc:
            raise DeploymentProxyError(503, "daemon_unavailable", "NA-Tools daemon SOCKS 代理响应无效") from exc

    def _build_request(
        self,
        method: str,
        path: str,
        *,
        config: DeploymentDaemonConfig,
        json_body: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> "_SignedRequest":
        body = _json_bytes(json_body)
        url = httpx.URL(f"{config.api_base}{path}", params={k: v for k, v in (params or {}).items() if v is not None})
        path_with_query = url.raw_path.decode("ascii")
        token = Path(config.token_file or "").read_bytes().strip()
        headers = build_signature_headers(
            token=token,
            instance_id=config.instance_id or "",
            method=method,
            path_with_query=path_with_query,
            body=body,
        )
        if body:
            headers["Content-Type"] = "application/json"
        return _SignedRequest(url=url, body=body, headers=headers)

    def _create_client(
        self,
        config: DeploymentDaemonConfig,
        *,
        timeout: float | httpx.Timeout,
    ) -> httpx.AsyncClient:
        kwargs: dict[str, Any] = {
            "timeout": timeout,
            "trust_env": False,
        }
        if self._transport is not None:
            kwargs["transport"] = self._transport
        elif config.socks_proxy:
            socks_proxy = _normalize_httpx_proxy_url(config.socks_proxy)
            kwargs["proxies"] = {
                "http://": socks_proxy,
                "https://": socks_proxy,
            }
        return httpx.AsyncClient(**kwargs)


@dataclass(frozen=True)
class _SignedRequest:
    url: httpx.URL
    body: bytes
    headers: dict[str, str]


def _json_bytes(payload: Mapping[str, Any] | None) -> bytes:
    if payload is None:
        return b""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _json_payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {}


async def _json_payload_from_streaming_response(response: httpx.Response) -> Any:
    content = await response.aread()
    if not content:
        return {}
    try:
        return json.loads(content)
    except ValueError:
        return {}


def _daemon_error(status_code: int, payload: Any) -> DeploymentProxyError:
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return DeploymentProxyError(status_code, "daemon_error", "NA-Tools daemon 请求失败")
    return DeploymentProxyError(
        status_code,
        _safe_optional_str(error.get("code")) or "daemon_error",
        _safe_optional_str(error.get("message")) or "NA-Tools daemon 请求失败",
        details=error.get("details") if isinstance(error.get("details"), dict) else None,
    )


async def _iter_sse_events(response: httpx.Response) -> AsyncIterator[dict[str, str]]:
    event_name = "message"
    data_lines: list[str] = []
    async for line in response.aiter_lines():
        if line == "":
            if data_lines:
                yield {"event": event_name, "data": _sanitize_sse_data("\n".join(data_lines))}
            event_name = "message"
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip() or "message"
            continue
        if line.startswith("data:"):
            data = line[5:]
            if data.startswith(" "):
                data = data[1:]
            data_lines.append(data)
    if data_lines:
        yield {"event": event_name, "data": _sanitize_sse_data("\n".join(data_lines))}


def _sanitize_sse_data(data: str) -> str:
    try:
        payload = json.loads(data)
    except ValueError:
        return sanitize_text(data)
    return json.dumps(sanitize_public_payload(payload), ensure_ascii=False, separators=(",", ":"))


def _normalize_unavailable_reason(value: Any) -> UnavailableReason | None:
    if value is None:
        return None
    if isinstance(value, dict):
        code = _safe_optional_str(value.get("code")) or "daemon_unavailable"
        message = _safe_optional_str(value.get("message")) or "NA-Tools daemon 不可用"
        return UnavailableReason(code=code, message=sanitize_text(message))
    text = _safe_optional_str(value)
    if not text:
        return None
    return UnavailableReason(code=text, message=_message_for_reason(text))


def _message_for_reason(code: str) -> str:
    return {
        "compose_missing": "未找到 Docker Compose 配置，请重新运行 na-tools bind",
        "env_missing": "未找到实例环境配置，请重新运行 na-tools bind",
        "docker_unavailable": "Docker 或 Docker Compose 当前不可用",
        "docker_not_running": "宿主 Docker 未运行或无法连接",
        "docker_permission_denied": (
            "NA-Tools daemon 无权访问宿主 Docker，请用具备 Docker 权限的用户重启 daemon"
        ),
        "docker_socket_missing": "未找到宿主 Docker socket，请确认 Docker 已启动",
    }.get(code, "NA-Tools daemon 当前不可用")


def _bool_dict(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    return {str(key): bool(item) for key, item in value.items()}


def _safe_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = sanitize_text(str(value)).strip()
    return text or None


def _normalize_httpx_proxy_url(proxy_url: str) -> str:
    url = httpx.URL(proxy_url)
    if url.scheme.lower() == "socks5h":
        return str(url.copy_with(scheme="socks5"))
    return proxy_url


def sanitize_public_payload(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if lowered in _DROPPED_KEYS or any(part in lowered for part in _HIDDEN_KEY_PARTS):
                continue
            clean[key_text] = sanitize_public_payload(item)
        return clean
    if isinstance(value, list):
        return [sanitize_public_payload(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_text(value: str) -> str:
    value = _INTERNAL_ENDPOINT_RE.sub("[redacted_endpoint]", value)
    value = _UNIX_ABSOLUTE_PATH_RE.sub("[redacted_path]", value)
    value = _WINDOWS_ABSOLUTE_PATH_RE.sub("[redacted_path]", value)
    return value
