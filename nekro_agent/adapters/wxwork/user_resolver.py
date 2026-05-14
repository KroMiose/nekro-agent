import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_user import DBUser
from nekro_agent.tools.telemetry_util import generate_instance_id


if TYPE_CHECKING:
    from .adapter import WxWorkAdapter


logger = get_sub_logger("adapter.wxwork.user_resolver")
USER_INFO_FETCHED_AT_KEY = "wxwork_user_name_fetched_at"
USER_INFO_SOURCE_KEY = "wxwork_user_name_source"
FAILED_LOOKUP_BACKOFF_SECONDS = 600
WXWORK_OFFICIAL_API_BASE_URL = "https://qyapi.weixin.qq.com"


@dataclass(slots=True)
class _CacheEntry:
    user_name: str
    expires_at: float


class _TTLCache:
    """进程内 TTL 缓存，使用线程锁保护单进程并发访问；多进程间不共享状态。"""

    def __init__(self, default_min_ttl: int = 60) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._default_min_ttl = default_min_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> str:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return ""
            if now >= entry.expires_at:
                self._store.pop(key, None)
                return ""
            return entry.user_name

    def set(self, key: str, user_name: str, ttl_seconds: int) -> None:
        expires_at = time.time() + max(ttl_seconds, self._default_min_ttl)
        with self._lock:
            self._store[key] = _CacheEntry(user_name=user_name, expires_at=expires_at)


class WxWorkUserResolver:
    def __init__(self, adapter: "WxWorkAdapter"):
        self._adapter = adapter
        self._cache = _TTLCache()
        self._access_token: str = ""
        self._access_token_expire_at: float = 0.0

    def is_lookup_configured(self) -> bool:
        mode = self._adapter.config.USER_INFO_LOOKUP_MODE
        if mode == "proxy":
            return bool(
                self._adapter.config.USER_INFO_PROXY_URL.strip()
                and self._adapter.config.USER_INFO_PROXY_SHARED_SECRET.strip()
            )
        return bool(
            self._adapter.config.USER_INFO_CORP_ID.strip() and self._adapter.config.USER_INFO_APP_SECRET.strip()
        )

    async def resolve_user_name(self, user_id: str, fallback_name: str = "") -> str:
        candidate = self._normalize_candidate(user_id, fallback_name)
        if candidate:
            await self._apply_resolution(user_id=user_id, user_name=candidate, source="callback")
            logger.info(f"WeCom 用户名解析命中回调字段: user_id={user_id}, user_name={candidate}")
            return candidate

        cached_or_db_name = await self._resolve_from_cache_or_db(user_id)
        if cached_or_db_name:
            return cached_or_db_name

        if not self.is_lookup_configured():
            logger.info(f"WeCom 用户名解析未配置自建应用通讯录查询，退回 userid: user_id={user_id}")
            return user_id

        resolved_name = await self._fetch_user_name(user_id)
        if resolved_name and resolved_name != user_id:
            await self._apply_resolution(user_id=user_id, user_name=resolved_name, source="directory")
            logger.info(f"WeCom 用户名解析命中自建应用通讯录: user_id={user_id}, user_name={resolved_name}")
            return resolved_name

        self._set_cache(user_id, user_id, FAILED_LOOKUP_BACKOFF_SECONDS)
        logger.info(f"WeCom 用户名解析失败，短期退回 userid: user_id={user_id}")
        return user_id

    def _normalize_candidate(self, user_id: str, fallback_name: str) -> str:
        candidate = (fallback_name or "").strip()
        if candidate and candidate != user_id:
            return candidate
        return ""

    async def _resolve_from_cache_or_db(self, user_id: str) -> str:
        cached_name = self._get_cache(user_id)
        if cached_name:
            logger.info(f"WeCom 用户名解析命中内存缓存: user_id={user_id}, user_name={cached_name}")
            return cached_name

        db_name = await self._get_db_cached_name(user_id)
        if db_name:
            self._set_cache(user_id, db_name, self._adapter.config.USER_INFO_CACHE_TTL_SECONDS)
            logger.info(f"WeCom 用户名解析命中数据库缓存: user_id={user_id}, user_name={db_name}")
            return db_name

        return ""

    async def _apply_resolution(self, *, user_id: str, user_name: str, source: str) -> None:
        await self._persist_resolved_name(user_id=user_id, user_name=user_name, source=source)
        self._set_cache(user_id, user_name, self._adapter.config.USER_INFO_CACHE_TTL_SECONDS)

    async def _get_db_cached_name(self, user_id: str) -> str:
        user = await DBUser.get_by_union_id(adapter_key=self._adapter.key, platform_userid=user_id)
        if not user:
            return ""
        user_name = (user.username or "").strip()
        return user_name if user_name and user_name != user_id else ""

    async def _persist_resolved_name(self, *, user_id: str, user_name: str, source: str) -> None:
        user_name = user_name.strip()
        if not user_name or user_name == user_id:
            return

        user = await DBUser.get_by_union_id(adapter_key=self._adapter.key, platform_userid=user_id)
        if user and user.username != user_name:
            user.username = user_name
            ext_data = dict(user.ext_data or {})
            ext_data[USER_INFO_FETCHED_AT_KEY] = int(time.time())
            ext_data[USER_INFO_SOURCE_KEY] = source
            user.ext_data = ext_data
            await user.save()
            await self._backfill_chat_message_names(user_id=user_id, user_name=user_name)

    async def _backfill_chat_message_names(self, *, user_id: str, user_name: str) -> None:
        await DBChatMessage.filter(
            adapter_key=self._adapter.key,
            platform_userid=user_id,
        ).update(sender_name=user_name, sender_nickname=user_name)

    async def _fetch_user_name(self, user_id: str) -> str:
        try:
            if self._adapter.config.USER_INFO_LOOKUP_MODE == "proxy":
                payload = await self._get_proxy_user_info_payload(user_id=user_id)
            else:
                access_token = await self._get_access_token()
                payload = await self._get_user_info_payload(access_token=access_token, user_id=user_id)
        except Exception as exc:
            logger.warning(f"企业微信用户名补查失败，将暂时退回 userid: user_id={user_id}, error={exc}")
            return ""

        user_name = str(payload.get("name") or "").strip()
        return user_name

    async def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._access_token_expire_at:
            return self._access_token

        timeout = httpx.Timeout(self._adapter.config.REQUEST_TIMEOUT_SECONDS)
        url = f"{WXWORK_OFFICIAL_API_BASE_URL}/cgi-bin/gettoken"
        params = {
            "corpid": self._adapter.config.USER_INFO_CORP_ID,
            "corpsecret": self._adapter.config.USER_INFO_APP_SECRET,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"获取企业微信通讯录 access_token 失败: {data.get('errmsg', 'unknown error')}")

        access_token = str(data.get("access_token", "")).strip()
        if not access_token:
            raise RuntimeError("企业微信通讯录 access_token 响应缺少 access_token")

        expires_in = int(data.get("expires_in", 7200) or 7200)
        self._access_token = access_token
        self._access_token_expire_at = time.time() + max(expires_in - 300, 60)
        return self._access_token

    async def _get_user_info_payload(self, *, access_token: str, user_id: str) -> dict:
        timeout = httpx.Timeout(self._adapter.config.REQUEST_TIMEOUT_SECONDS)
        url = f"{WXWORK_OFFICIAL_API_BASE_URL}/cgi-bin/user/get"
        params = {
            "access_token": access_token,
            "userid": user_id,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("errcode", 0) == 40014:
            self._access_token = ""
            self._access_token_expire_at = 0.0
            refreshed_token = await self._get_access_token()
            params["access_token"] = refreshed_token
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"读取企业微信成员失败: {data.get('errmsg', 'unknown error')} ({data.get('errcode')})")
        return data

    async def _get_proxy_user_info_payload(self, *, user_id: str) -> dict:
        timeout = httpx.Timeout(self._adapter.config.REQUEST_TIMEOUT_SECONDS)
        request_body = {"user_id": user_id}
        request_body_json = json.dumps(request_body, ensure_ascii=False, separators=(",", ":"))
        timestamp = str(int(time.time()))
        instance_id = generate_instance_id()
        signature = self._build_proxy_signature(
            instance_id=instance_id,
            timestamp=timestamp,
            body=request_body_json,
        )
        headers = {
            "Content-Type": "application/json",
            "X-Nekro-Instance-Id": instance_id,
            "X-Nekro-Timestamp": timestamp,
            "X-Nekro-Signature": signature,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self._adapter.config.USER_INFO_PROXY_URL.strip(),
                content=request_body_json,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok", False):
            raise RuntimeError(str(data.get("error") or "用户名代理返回失败"))

        user_name = str(data.get("user_name") or "").strip()
        return {"name": user_name}

    def _build_proxy_signature(self, *, instance_id: str, timestamp: str, body: str) -> str:
        secret = self._adapter.config.USER_INFO_PROXY_SHARED_SECRET.strip().encode("utf-8")
        message = f"{instance_id}\n{timestamp}\n{body}".encode("utf-8")
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    def _get_cache(self, user_id: str) -> str:
        return self._cache.get(user_id)

    def _set_cache(self, user_id: str, user_name: str, ttl_seconds: int) -> None:
        self._cache.set(user_id, user_name, ttl_seconds)
