import time
from typing import Any

import httpx

from nekro_agent.core.logger import get_sub_logger


logger = get_sub_logger("adapter.wxwork")


class WxWorkCorpAppClient:
    """企业微信自建应用发送客户端。

    说明：
    - 私聊发送走 `/cgi-bin/message/send`
    - 群聊发送尝试走 `/cgi-bin/appchat/send`
    - 群聊 chatid 仅适用于自建应用侧可识别的群聊会话；普通 AI Bot 收到的内部群 chatid 不保证可直接复用
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
            chatid = channel_id[len("group_") :]
            return await self._send_appchat_text_message(access_token, chatid, content)
        raise RuntimeError(f"不支持的企业微信频道 ID: {channel_id}")

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

    async def _send_appchat_text_message(self, access_token: str, chatid: str, content: str) -> dict[str, Any]:
        url = f"{self._adapter.config.CORP_API_BASE_URL.rstrip('/')}/cgi-bin/appchat/send"
        payload = {
            "chatid": chatid,
            "msgtype": "text",
            "text": {"content": content},
            "safe": 0,
        }
        return await self._post_json(url, access_token, payload)

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

    def _parse_agent_id(self) -> int | str:
        agent_id = self._adapter.config.CORP_APP_AGENT_ID.strip()
        return int(agent_id) if agent_id.isdigit() else agent_id
