from enum import StrEnum
from typing import Mapping, Optional
from urllib.parse import quote, urlsplit, urlunsplit

from nekro_agent.core.config import config


class SystemProxyFeature(StrEnum):
    PLUGIN_UPDATE = "plugin_update"
    DYNAMIC_PLUGIN_INSTALL = "dynamic_plugin_install"


_FEATURE_FLAG_MAP: dict[SystemProxyFeature, str] = {
    SystemProxyFeature.PLUGIN_UPDATE: "PLUGIN_UPDATE_USE_PROXY",
    SystemProxyFeature.DYNAMIC_PLUGIN_INSTALL: "DYNAMIC_PLUGIN_INSTALL_USE_PROXY",
}


def is_proxy_enabled(feature: SystemProxyFeature) -> bool:
    return bool(getattr(config, _FEATURE_FLAG_MAP[feature], False))


def _get_proxy_credentials() -> tuple[str, str]:
    username = (config.DEFAULT_PROXY_USERNAME or "").strip()
    password = config.DEFAULT_PROXY_PASSWORD or ""
    if password and not username:
        raise ValueError("系统级代理密码已设置，但未提供代理用户名")
    return username, password


def _build_authenticated_proxy_url(raw_proxy_url: str, username: str, password: str) -> str:
    split = urlsplit(raw_proxy_url)
    if not split.scheme or not split.hostname:
        raise ValueError("系统级默认代理地址无效，必须包含协议头和主机名")

    if split.username or split.password:
        if username or password:
            raise ValueError("系统级默认代理地址已包含认证信息，请勿与单独的代理用户名/密码同时配置")
        return raw_proxy_url

    if not username:
        return raw_proxy_url

    quoted_username = quote(username, safe="")
    quoted_password = quote(password, safe="")
    auth_part = quoted_username if not quoted_password else f"{quoted_username}:{quoted_password}"
    host_part = split.hostname
    if split.port is not None:
        host_part = f"{host_part}:{split.port}"

    return urlunsplit((split.scheme, f"{auth_part}@{host_part}", split.path, split.query, split.fragment))


def build_proxy_url(feature: SystemProxyFeature) -> Optional[str]:
    if not is_proxy_enabled(feature):
        return None

    raw_proxy_url = (config.DEFAULT_PROXY or "").strip()
    if not raw_proxy_url:
        return None

    username, password = _get_proxy_credentials()
    return _build_authenticated_proxy_url(raw_proxy_url, username, password)


def build_httpx_proxies(feature: SystemProxyFeature) -> Optional[dict[str, str]]:
    proxy_url = build_proxy_url(feature)
    if not proxy_url:
        return None
    return {
        "http://": proxy_url,
        "https://": proxy_url,
    }


def build_subprocess_proxy_env(
    feature: SystemProxyFeature,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, str]:
    merged_env = dict(env or {})
    proxy_url = build_proxy_url(feature)
    if not proxy_url:
        return merged_env

    merged_env["HTTP_PROXY"] = proxy_url
    merged_env["HTTPS_PROXY"] = proxy_url
    merged_env["http_proxy"] = proxy_url
    merged_env["https_proxy"] = proxy_url
    return merged_env


def mask_proxy_url(proxy_url: Optional[str]) -> str:
    if not proxy_url:
        return ""

    split = urlsplit(proxy_url)
    if not split.username and not split.password:
        return proxy_url

    host_part = split.hostname or ""
    if split.port is not None:
        host_part = f"{host_part}:{split.port}"
    return urlunsplit((split.scheme, f"***:***@{host_part}", split.path, split.query, split.fragment))
