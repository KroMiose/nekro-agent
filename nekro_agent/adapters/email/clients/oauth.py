import base64
import json
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import httpx

from nekro_agent.adapters.email.config import EmailAccount

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_GMAIL_SCOPES = ["https://mail.google.com/"]
MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
def _get_microsoft_scopes(account: EmailAccount) -> list[str]:
    if account.TRANSPORT_TYPE == "microsoft_graph":
        return ["offline_access", "https://graph.microsoft.com/Mail.ReadWrite"]
    return ["offline_access", "https://outlook.office.com/IMAP.AccessAsUser.All", "https://outlook.office.com/SMTP.Send"]


MICROSOFT_GRAPH_SCOPES = ["offline_access", "https://graph.microsoft.com/Mail.ReadWrite"]


def build_oauth_authorize_url(account: EmailAccount, redirect_uri: str, state: str) -> str:
    if not account.CLIENT_ID:
        raise RuntimeError("OAuth Client ID 未配置")
    if account.OAUTH_PROVIDER == "google":
        query = urlencode(
            {
                "client_id": account.CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(GOOGLE_GMAIL_SCOPES),
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            },
        )
        return f"{GOOGLE_AUTH_URL}?{query}"
    if account.OAUTH_PROVIDER == "microsoft":
        tenant_id = account.TENANT_ID or "common"
        query = urlencode(
            {
                "client_id": account.CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(_get_microsoft_scopes(account)),
                "response_mode": "query",
                "prompt": "select_account",
                "state": state,
            },
        )
        return f"{MICROSOFT_AUTH_URL.format(tenant_id=tenant_id)}?{query}"
    raise RuntimeError(f"不支持的 OAuth 提供商: {account.OAUTH_PROVIDER}")


def _httpx_client_kwargs(proxy_url: str | None) -> dict[str, Any]:
    return {"timeout": 30, "proxy": proxy_url} if proxy_url else {"timeout": 30}


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except Exception:
        return {}


async def fetch_oauth_email_address(
    account: EmailAccount,
    access_token: str,
    proxy_url: str = "",
    id_token: str = "",
) -> str:
    if account.OAUTH_PROVIDER == "google":
        url = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
        email_key = "emailAddress"
    elif account.OAUTH_PROVIDER == "microsoft":
        payload = _decode_jwt_payload(id_token)
        email_address = str(
            payload.get("preferred_username")
            or payload.get("email")
            or payload.get("upn")
            or account.USERNAME
            or ""
        )
        if not email_address:
            raise RuntimeError("OAuth 用户信息响应缺少邮箱地址")
        return email_address
    else:
        raise RuntimeError(f"不支持的 OAuth 提供商: {account.OAUTH_PROVIDER}")

    async with httpx.AsyncClient(**_httpx_client_kwargs(proxy_url)) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        response.raise_for_status()
        payload: dict[str, Any] = response.json()

    email_address = str(payload.get(email_key) or payload.get("userPrincipalName") or "")
    if not email_address:
        raise RuntimeError("OAuth 用户信息响应缺少邮箱地址")
    return email_address


async def exchange_oauth_code(account: EmailAccount, code: str, redirect_uri: str, proxy_url: str = "") -> dict[str, Any]:
    if not account.CLIENT_ID:
        raise RuntimeError("OAuth Client ID 未配置")
    if not account.CLIENT_SECRET:
        raise RuntimeError("OAuth Client Secret 未配置")
    token_url = OAuthTokenManager(account)._get_token_url()
    data = {
        "client_id": account.CLIENT_ID,
        "client_secret": account.CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(**_httpx_client_kwargs(proxy_url)) as client:
        response = await client.post(token_url, data=data)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    access_token = str(payload.get("access_token") or "")
    id_token = str(payload.get("id_token") or "")
    if not access_token:
        raise RuntimeError("OAuth 回调响应缺少 access_token")
    refresh_token = str(payload.get("refresh_token") or account.REFRESH_TOKEN or "")
    if not refresh_token:
        raise RuntimeError("OAuth 回调响应缺少 refresh_token，请确认授权请求包含离线访问权限")
    expires_in = int(payload.get("expires_in") or 3600)
    account.ACCESS_TOKEN = access_token
    account.REFRESH_TOKEN = refresh_token
    account.TOKEN_EXPIRES_AT = int(time.time()) + expires_in
    account.USERNAME = await fetch_oauth_email_address(account, access_token, proxy_url, id_token)
    return payload


class OAuthTokenManager:
    def __init__(self, account: EmailAccount, proxy_url: str = "", on_token_update: Callable[[], None] | None = None):
        self.account = account
        self.proxy_url = proxy_url
        self.on_token_update = on_token_update

    async def get_access_token(self) -> str:
        if self.account.ACCESS_TOKEN and self.account.TOKEN_EXPIRES_AT > int(time.time()) + 60:
            return self.account.ACCESS_TOKEN
        return await self.refresh_access_token()

    async def refresh_access_token(self) -> str:
        if not self.account.CLIENT_ID:
            raise RuntimeError("OAuth Client ID 未配置")
        if not self.account.CLIENT_SECRET:
            raise RuntimeError("OAuth Client Secret 未配置")
        if not self.account.REFRESH_TOKEN:
            raise RuntimeError("OAuth Refresh Token 未配置，请先完成授权登录")

        token_url = self._get_token_url()
        data = {
            "client_id": self.account.CLIENT_ID,
            "client_secret": self.account.CLIENT_SECRET,
            "refresh_token": self.account.REFRESH_TOKEN,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient(**_httpx_client_kwargs(self.proxy_url)) as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        access_token = str(payload.get("access_token") or "")
        if not access_token:
            raise RuntimeError("OAuth 刷新响应缺少 access_token")
        expires_in = int(payload.get("expires_in") or 3600)
        self.account.ACCESS_TOKEN = access_token
        self.account.TOKEN_EXPIRES_AT = int(time.time()) + expires_in
        refresh_token = payload.get("refresh_token")
        if refresh_token:
            self.account.REFRESH_TOKEN = str(refresh_token)
        if self.on_token_update:
            self.on_token_update()
        return access_token

    def _get_token_url(self) -> str:
        if self.account.OAUTH_PROVIDER == "google":
            return GOOGLE_TOKEN_URL
        if self.account.OAUTH_PROVIDER == "microsoft":
            tenant_id = self.account.TENANT_ID or "common"
            return MICROSOFT_TOKEN_URL.format(tenant_id=tenant_id)
        raise RuntimeError(f"不支持的 OAuth 提供商: {self.account.OAUTH_PROVIDER}")
