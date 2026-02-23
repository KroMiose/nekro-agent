import json
from collections.abc import Awaitable, Callable
from typing import AsyncGenerator, List

import httpx

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_workspace import DBWorkspace

logger = get_sub_logger("cc_sandbox_client")


class CCSandboxError(Exception):
    pass


class CCSandboxClient:
    def __init__(self, workspace: DBWorkspace, timeout: float = 300.0) -> None:
        self._base_url = workspace.api_endpoint
        self._timeout = timeout

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/health")
                return resp.status_code == 200 and resp.json().get("status") == "healthy"
        except Exception:
            return False

    async def send_message(
        self,
        content: str,
        workspace_id: str = "default",
        source_chat_key: str = "",
        env_vars: "dict[str, str] | None" = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/message",
                json={
                    "role": "user",
                    "content": content,
                    "workspace_id": workspace_id,
                    "source_chat_key": source_chat_key,
                    "env_vars": env_vars or {},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                err = data.get("error") or {}
                raise CCSandboxError(f"CC 响应错误: {err.get('message', 'unknown')}")
            return str(data.get("message", ""))

    async def stream_message(
        self,
        content: str,
        workspace_id: str = "default",
        source_chat_key: str = "",
        on_queued: Callable[[dict], Awaitable[None]] | None = None,
        env_vars: "dict[str, str] | None" = None,
    ) -> AsyncGenerator[str | dict, None]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/v1/message/stream",
                json={
                    "role": "user",
                    "content": content,
                    "workspace_id": workspace_id,
                    "source_chat_key": source_chat_key,
                    "env_vars": env_vars or {},
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    try:
                        chunk = json.loads(raw)
                    except Exception:
                        continue
                    chunk_type = chunk.get("type")
                    if chunk_type == "chunk":
                        yield chunk.get("chunk", "")
                    elif chunk_type == "queued":
                        if on_queued is not None:
                            await on_queued(chunk)
                    elif chunk_type in ("tool_call", "tool_result"):
                        yield chunk
                    elif chunk_type == "error":
                        raise CCSandboxError(chunk.get("message", "stream error"))

    async def reset_session(self, workspace_id: str = "default") -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self._base_url}/api/v1/workspaces/{workspace_id}/session/reset")
            resp.raise_for_status()

    async def get_tools(self) -> List[str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self._base_url}/api/v1/capabilities/tools")
            resp.raise_for_status()
            data = resp.json()
            return list(data.get("tools") or [])

    async def refresh_tools(self) -> List[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self._base_url}/api/v1/capabilities/tools/refresh")
            resp.raise_for_status()
            data = resp.json()
            return list(data.get("tools") or [])

    async def get_sandbox_status(self, workspace_id: str = "default") -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._base_url}/api/v1/workspaces/{workspace_id}")
            if resp.status_code == 200:
                return dict(resp.json())
            return {}

    async def get_workspace_queue(self, workspace_id: str = "default") -> dict:
        """获取工作区任务队列状态（当前任务 + 等待列表）。"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/v1/workspaces/{workspace_id}/queue")
                if resp.status_code == 200:
                    return dict(resp.json())
        except Exception:
            pass
        return {"workspace_id": workspace_id, "current_task": None, "queued_tasks": [], "queue_length": 0}

    async def force_cancel_current_task(self, workspace_id: str = "default") -> bool:
        """强制取消工作区当前正在运行的任务。"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(f"{self._base_url}/api/v1/workspaces/{workspace_id}/queue/current")
                if resp.status_code == 200:
                    return bool(resp.json().get("cancelled", False))
        except Exception:
            pass
        return False
