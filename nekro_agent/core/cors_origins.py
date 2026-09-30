"""CORS 允许来源配置的严格解析

安全约束背景:
allow_origins=["*"] 与 allow_credentials=True 组合会让 Starlette 反射
任意请求 Origin(CWE-942),任何恶意网页都能以受害者浏览器凭据调用
管理 API。因此来源列表必须:
- 禁止任何通配符(含 "*" 单独成项或混在条目中);
- 每项必须是规范的 http/https Origin:有主机名,无路径、查询、
  片段、用户信息;
- 违反时直接抛错终止启动(fail-fast),不静默降级。
"""

from urllib.parse import urlparse


def parse_cors_origins(raw: str) -> list[str]:
    """解析逗号分隔的 Origin 白名单,非法条目抛 ValueError(阻止启动)"""
    origins: list[str] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "*" in item:
            raise ValueError(f"NEKRO_CORS_ORIGINS 不允许通配符来源: {item}")
        parsed = urlparse(item)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.params
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError(f"NEKRO_CORS_ORIGINS 含非法 Origin(须为 http(s)://host[:port]): {item}")
        origins.append(item)
    return origins
