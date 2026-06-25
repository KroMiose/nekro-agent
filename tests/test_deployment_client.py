import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from socksio.exceptions import ProtocolError as SocksProtocolError

from nekro_agent.services.deployment.client import (
    DeploymentDaemonClient,
    DeploymentDaemonConfig,
    DeploymentProxyError,
)
from nekro_agent.services.deployment.schemas import (
    DeploymentCreateBackupRequest,
    DeploymentRestoreRequest,
    DeploymentUpdateRequest,
)


def _config(tmp_path: Path, *, enabled: bool = True, token_exists: bool = True) -> DeploymentDaemonConfig:
    token_file = tmp_path / "daemon.token"
    if token_exists:
        token_file.write_bytes(b"fixed-token")
    return DeploymentDaemonConfig(
        enabled=enabled,
        api_base="http://na-tools.local/v1",
        socks_proxy=None,
        instance_id="sha256:test",
        token_file=str(token_file),
    )


def _client(config: DeploymentDaemonConfig, handler: httpx.MockTransport) -> DeploymentDaemonClient:
    return DeploymentDaemonClient(config_loader=lambda: config, transport=handler)


@pytest.mark.asyncio
async def test_capabilities_disabled_does_not_call_daemon(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("daemon should not be called")

    client = _client(_config(tmp_path, enabled=False), httpx.MockTransport(handler))

    response = await client.get_capabilities()

    assert response.enabled is False
    assert response.supports == {}
    assert response.unavailable_reason is not None
    assert response.unavailable_reason.code == "daemon_disabled"


@pytest.mark.asyncio
async def test_capabilities_token_missing_returns_unavailable_reason(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("daemon should not be called")

    client = _client(_config(tmp_path, token_exists=False), httpx.MockTransport(handler))

    response = await client.get_capabilities()

    assert response.enabled is False
    assert response.unavailable_reason is not None
    assert response.unavailable_reason.code == "daemon_token_missing"
    assert str(tmp_path) not in response.unavailable_reason.message


@pytest.mark.asyncio
async def test_capabilities_token_read_error_maps_to_daemon_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("daemon should not be called")

    config = _config(tmp_path)
    token_path = Path(config.token_file or "")
    original_read_bytes = Path.read_bytes

    def read_bytes(path: Path) -> bytes:
        if path == token_path:
            raise PermissionError("permission denied")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    client = _client(config, httpx.MockTransport(handler))

    response = await client.get_capabilities()

    assert response.enabled is False
    assert response.unavailable_reason is not None
    assert response.unavailable_reason.code == "daemon_unavailable"


@pytest.mark.asyncio
async def test_capabilities_network_error_maps_to_daemon_unavailable(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    response = await client.get_capabilities()

    assert response.enabled is False
    assert response.unavailable_reason is not None
    assert response.unavailable_reason.code == "daemon_unavailable"


@pytest.mark.asyncio
async def test_capabilities_socks_protocol_error_maps_to_daemon_unavailable(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise SocksProtocolError("Malformed reply")

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    response = await client.get_capabilities()

    assert response.enabled is False
    assert response.unavailable_reason is not None
    assert response.unavailable_reason.code == "daemon_unavailable"


@pytest.mark.asyncio
async def test_create_client_accepts_socks5h_proxy_scheme(tmp_path: Path) -> None:
    config = DeploymentDaemonConfig(
        enabled=True,
        api_base="http://na-tools.local/v1",
        socks_proxy="socks5h://host.docker.internal:18082",
        instance_id="sha256:test",
        token_file=str(tmp_path / "daemon.token"),
    )
    client = DeploymentDaemonClient(config_loader=lambda: config)

    http_client = client._create_client(config, timeout=1.0)
    await http_client.aclose()


@pytest.mark.asyncio
async def test_create_update_adds_instance_and_requested_by(tmp_path: Path) -> None:
    seen_payload: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payload.update(json.loads(request.content.decode("utf-8")))
        assert request.url.path == "/v1/jobs/update"
        assert request.headers["X-NA-Instance"] == "sha256:test"
        return httpx.Response(200, json={"job_id": "upd_1", "status": "queued"}, request=request)

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    response = await client.create_update(
        DeploymentUpdateRequest(
            channel="stable",
            backup=True,
            update_sandbox=True,
            update_cc_sandbox=False,
            restore_pre_preview=False,
            client_request_id="request-1",
        ),
        username="admin",
    )

    assert response["job_id"] == "upd_1"
    assert seen_payload["instance_id"] == "sha256:test"
    assert seen_payload["client_request_id"] == "request-1"
    assert seen_payload["requested_by"] == {
        "source": "nekro-agent-webui",
        "username": "admin",
    }


@pytest.mark.asyncio
async def test_list_backups_returns_safe_summaries(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/backups"
        return httpx.Response(
            200,
            json={
                "backups": [
                    {
                        "backup_id": "nekro_backup_webui_20260611_010203.tar.gz",
                        "filename": "nekro_backup_webui_20260611_010203.tar.gz",
                        "name": "webui",
                        "created_at": "2026-06-11T01:02:03+00:00",
                        "size_bytes": 1024,
                        "backup_file": "/home/user/.config/na-tools/backup/private.tar.gz",
                    }
                ],
                "data_dir": "/home/user/nekro_agent",
            },
            request=request,
        )

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    response = await client.list_backups()
    serialized = response.model_dump_json()

    assert response.backups[0].name == "webui"
    assert response.backups[0].size_bytes == 1024
    assert "/home/user" not in serialized
    assert "backup_file" not in serialized


@pytest.mark.asyncio
async def test_create_backup_adds_instance_and_requested_by(tmp_path: Path) -> None:
    seen_payload: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payload.update(json.loads(request.content.decode("utf-8")))
        assert request.url.path == "/v1/jobs/backup"
        return httpx.Response(200, json={"job_id": "upd_1", "type": "backup", "status": "queued"}, request=request)

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    response = await client.create_backup(
        DeploymentCreateBackupRequest(name="webui", client_request_id="backup-1"),
        username="admin",
    )

    assert response["type"] == "backup"
    assert seen_payload["instance_id"] == "sha256:test"
    assert seen_payload["name"] == "webui"
    assert seen_payload["client_request_id"] == "backup-1"
    assert seen_payload["requested_by"] == {
        "source": "nekro-agent-webui",
        "username": "admin",
    }


@pytest.mark.asyncio
async def test_create_restore_adds_instance_and_requested_by(tmp_path: Path) -> None:
    seen_payload: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payload.update(json.loads(request.content.decode("utf-8")))
        assert request.url.path == "/v1/jobs/restore"
        return httpx.Response(200, json={"job_id": "upd_2", "type": "restore", "status": "queued"}, request=request)

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    response = await client.create_restore(
        DeploymentRestoreRequest(
            backup_id="nekro_backup_webui_20260611_010203.tar.gz",
            client_request_id="restore-1",
        ),
        username="admin",
    )

    assert response["type"] == "restore"
    assert seen_payload["instance_id"] == "sha256:test"
    assert seen_payload["backup_id"] == "nekro_backup_webui_20260611_010203.tar.gz"
    assert seen_payload["client_request_id"] == "restore-1"
    assert seen_payload["requested_by"] == {
        "source": "nekro-agent-webui",
        "username": "admin",
    }


@pytest.mark.asyncio
async def test_daemon_conflict_preserves_code_and_message(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "error": {
                    "code": "job_conflict",
                    "message": "已有更新任务正在运行",
                    "details": {"job_id": "upd_running"},
                }
            },
            request=request,
        )

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    with pytest.raises(DeploymentProxyError) as exc_info:
        await client.create_update(
            DeploymentUpdateRequest(channel="stable"),
            username="admin",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.payload()["error"]["code"] == "job_conflict"
    assert exc_info.value.payload()["error"]["message"] == "已有更新任务正在运行"


@pytest.mark.asyncio
async def test_instance_response_hides_paths_ports_and_health_url(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "instance_id": "sha256:test",
                "data_dir": "/home/user/srv/nekro_agent",
                "compose_file": "/home/user/srv/nekro_agent/docker-compose.yml",
                "env_file": "/home/user/srv/nekro_agent/.env",
                "channel": "stable",
                "available": True,
                "app": {
                    "expose_port": 8021,
                    "health_url": "http://127.0.0.1:8021/api/health",
                },
                "container": {
                    "status": "running",
                    "image": "kromiose/nekro-agent:latest",
                },
                "docker": {
                    "docker_installed": True,
                    "compose_installed": True,
                },
            },
            request=request,
        )

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    response = await client.get_instance()
    serialized = response.model_dump_json()

    assert response.channel == "stable"
    assert response.image == "kromiose/nekro-agent:latest"
    assert response.container_status == "running"
    assert response.app_health == "ok"
    assert response.docker_ok is True
    assert response.compose_ok is True
    assert "/home/user" not in serialized
    assert "8021" not in serialized
    assert "health_url" not in serialized


class _TrackingSSEStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self) -> Iterator[bytes]:
        yield b"event: log\n"
        yield b'data: {"seq":1,"line":"ok"}\n\n'
        await asyncio.sleep(60)

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_stream_events_closes_daemon_stream_when_generator_closes(tmp_path: Path) -> None:
    stream = _TrackingSSEStream()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/jobs/upd_1/events"
        return httpx.Response(200, stream=stream, request=request)

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    events = client.stream_events("upd_1")
    event = await anext(events)
    await events.aclose()

    assert event == {"event": "log", "data": '{"seq":1,"line":"ok"}'}
    assert stream.closed is True


class _SensitiveSSEStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> Iterator[bytes]:
        yield b"event: result\n"
        yield (
            b'data: {"seq":1,"status":"succeeded","result":'
            b'{"backup_file":"/home/user/.config/na-tools/backup/private.tar.gz",'
            b'"line":"stored at /home/user/private"}}\n\n'
        )


@pytest.mark.asyncio
async def test_stream_events_sanitizes_structured_payloads(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_SensitiveSSEStream(), request=request)

    client = _client(_config(tmp_path), httpx.MockTransport(handler))

    events = client.stream_events("upd_1")
    event = await anext(events)
    await events.aclose()

    assert event["event"] == "result"
    assert "backup_file" not in event["data"]
    assert "/home/user" not in event["data"]
