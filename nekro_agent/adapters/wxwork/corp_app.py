import time
from pathlib import Path
from typing import Any

import httpx

from nekro_agent.core.logger import get_sub_logger


logger = get_sub_logger("adapter.wxwork")


class WxWorkCorpAppClient:
    """企业微信自建应用发送客户端。

    说明：
    - 私聊发送走 `/cgi-bin/message/send`
    - 当前对齐 AstrBot 实现，暂仅支持私聊消息收发
    """

    def __init__(self, adapter: Any):
        self._adapter = adapter
        self._access_token: str = ""
        self._access_token_expire_at: float = 0.0

    def is_configured(self) -> bool:
        return bool(
            self._adapter.config.CORP_ID.strip()
            and self._adapter.config.CORP_APP_SECRET.strip()
            and self._adapter.config.CORP_APP_AGENT_ID.strip()
        )

    async def send_text_message(self, channel_id: str, content: str) -> dict[str, Any]:
        access_token = await self._get_access_token()
        if channel_id.startswith("private_"):
            userid = channel_id[len("private_") :]
            return await self._send_user_text_message(access_token, userid, content)
        if channel_id.startswith("group_"):
            raise RuntimeError("企业微信自建应用当前暂不支持群聊发送，仅支持私聊")
        raise RuntimeError(f"不支持的企业微信频道 ID: {channel_id}")

    async def send_media_message(self, channel_id: str, *, media_type: str, file_path: str) -> dict[str, Any]:
        if media_type not in {"image", "file"}:
            raise ValueError(f"企业微信自建应用暂不支持的媒体类型: {media_type}")

        access_token = await self._get_access_token()
        if not channel_id.startswith("private_"):
            raise RuntimeError("企业微信自建应用当前仅支持私聊媒体发送")

        userid = channel_id[len("private_") :]
        media_id = await self._upload_media(access_token, media_type=media_type, file_path=file_path)
        return await self._send_user_media_message(
            access_token,
            userid=userid,
            media_type=media_type,
            media_id=media_id,
        )

    async def send_kf_text_message(self, *, open_kfid: str, external_userid: str, content: str) -> dict[str, Any]:
        access_token = await self._get_access_token()
        await self._ensure_kf_session_sendable(
            access_token=access_token,
            open_kfid=open_kfid,
            external_userid=external_userid,
        )
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "text",
            "text": {"content": content},
        }
        return await self._post_json(
            f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/kf/send_msg",
            access_token,
            payload,
        )

    async def send_kf_media_message(
        self,
        *,
        open_kfid: str,
        external_userid: str,
        media_type: str,
        file_path: str,
    ) -> dict[str, Any]:
        if media_type not in {"image", "file"}:
            raise ValueError(f"企业微信自建应用客服暂不支持的媒体类型: {media_type}")

        access_token = await self._get_access_token()
        await self._ensure_kf_session_sendable(
            access_token=access_token,
            open_kfid=open_kfid,
            external_userid=external_userid,
        )
        media_id = await self._upload_media(access_token, media_type=media_type, file_path=file_path)
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": media_type,
            media_type: {"media_id": media_id},
        }
        return await self._post_json(
            f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/kf/send_msg",
            access_token,
            payload,
        )

    async def sync_kf_messages(
        self,
        *,
        token: str,
        open_kfid: str,
        cursor: str = "",
        limit: int = 1000,
    ) -> dict[str, Any]:
        access_token = await self._get_access_token()
        payload = {
            "token": token,
            "cursor": cursor,
            "limit": limit,
            "open_kfid": open_kfid,
        }
        return await self._post_json(
            f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/kf/sync_msg",
            access_token,
            payload,
        )

    async def get_kf_service_state(self, *, access_token: str, open_kfid: str, external_userid: str) -> dict[str, Any]:
        payload = {
            "open_kfid": open_kfid,
            "external_userid": external_userid,
        }
        return await self._post_json(
            f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/kf/service_state/get",
            access_token,
            payload,
        )

    async def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._access_token_expire_at:
            return self._access_token

        url = f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/gettoken"
        params = {
            "corpid": self._adapter.config.CORP_ID,
            "corpsecret": self._adapter.config.CORP_APP_SECRET,
        }
        timeout = httpx.Timeout(self._adapter.config.REQUEST_TIMEOUT_SECONDS)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"获取企业微信 access_token 失败: {data.get('errmsg', 'unknown error')}")

        access_token = str(data.get("access_token", "")).strip()
        if not access_token:
            raise RuntimeError("企业微信 access_token 响应缺少 access_token 字段")

        expires_in = int(data.get("expires_in", 7200) or 7200)
        self._access_token = access_token
        self._access_token_expire_at = time.time() + max(expires_in - 300, 60)
        return self._access_token

    async def _send_user_text_message(self, access_token: str, userid: str, content: str) -> dict[str, Any]:
        url = f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/message/send"
        payload = {
            "touser": userid,
            "msgtype": "text",
            "agentid": self._parse_agent_id(),
            "text": {"content": content},
            "safe": 0,
            "enable_id_trans": 0,
        }
        return await self._post_json(url, access_token, payload)

    async def _send_user_media_message(
        self,
        access_token: str,
        *,
        userid: str,
        media_type: str,
        media_id: str,
    ) -> dict[str, Any]:
        url = f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/message/send"
        payload = {
            "touser": userid,
            "msgtype": media_type,
            "agentid": self._parse_agent_id(),
            media_type: {"media_id": media_id},
            "safe": 0,
            "enable_id_trans": 0,
        }
        return await self._post_json(url, access_token, payload)

    async def _upload_media(self, access_token: str, *, media_type: str, file_path: str) -> str:
        file = Path(file_path)
        if not file.exists() or not file.is_file():
            raise FileNotFoundError(f"企业微信自建应用上传文件不存在: {file_path}")

        url = f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/media/upload"
        timeout = httpx.Timeout(self._adapter.config.REQUEST_TIMEOUT_SECONDS)
        files = {"media": (file.name, file.read_bytes())}
        return await self._upload_media_files(url, timeout, access_token, media_type, files, retry_label="媒体上传")

    async def _upload_media_files(
        self,
        url: str,
        timeout: httpx.Timeout,
        access_token: str,
        media_type: str,
        files: dict[str, tuple[str, bytes]],
        *,
        retry_label: str,
    ) -> str:

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                params={"access_token": access_token, "type": media_type},
                files=files,
            )
            response.raise_for_status()
            data = response.json()

        if data.get("errcode", 0) == 40014:
            logger.warning(f"企业微信 access_token 已失效，刷新后重试一次{retry_label}")
            self._access_token = ""
            self._access_token_expire_at = 0.0
            refreshed_token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    params={"access_token": refreshed_token, "type": media_type},
                    files=files,
                )
                response.raise_for_status()
                data = response.json()

        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"企业微信自建应用{retry_label}失败: {data.get('errmsg', 'unknown error')} ({data.get('errcode')})")

        media_id = str(data.get("media_id", "")).strip()
        if not media_id:
            raise RuntimeError(f"企业微信自建应用{retry_label}成功但响应缺少 media_id")
        return media_id

    async def _post_json(self, url: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        timeout = httpx.Timeout(self._adapter.config.REQUEST_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, params={"access_token": access_token}, json=payload)
            response.raise_for_status()
            data = response.json()

        if data.get("errcode", 0) == 40014:
            logger.warning("企业微信 access_token 已失效，刷新后重试一次")
            self._access_token = ""
            self._access_token_expire_at = 0.0
            refreshed_token = await self._get_access_token()
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, params={"access_token": refreshed_token}, json=payload)
                response.raise_for_status()
                data = response.json()

        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"企业微信自建应用发送失败: {data.get('errmsg', 'unknown error')} ({data.get('errcode')})")

        return data

    async def _ensure_kf_session_sendable(
        self,
        *,
        access_token: str,
        open_kfid: str,
        external_userid: str,
    ) -> None:
        state_resp = await self.get_kf_service_state(
            access_token=access_token,
            open_kfid=open_kfid,
            external_userid=external_userid,
        )
        service_state = int(state_resp.get("service_state", -1))
        if service_state in {0, 1}:
            return
        if service_state == 2:
            raise RuntimeError("企业微信客服当前会话处于待接入池，当前状态流转不允许直接由接口发送消息")
        if service_state == 3:
            raise RuntimeError("企业微信客服当前会话由人工接待中，API 不允许智能助手发送消息")
        if service_state == 4:
            raise RuntimeError("企业微信客服当前会话已结束，或已超过 48 小时可发送窗口")
        logger.warning(f"企业微信客服会话状态未知: service_state={service_state}, raw={state_resp}")
        raise RuntimeError(f"企业微信客服当前会话状态不允许发送消息: service_state={service_state}")

    def _parse_agent_id(self) -> int | str:
        agent_id = self._adapter.config.CORP_APP_AGENT_ID.strip()
        return int(agent_id) if agent_id.isdigit() else agent_id
