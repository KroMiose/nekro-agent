"""下载 URL SSRF 防护测试

对应 PR 安全修复: download_file 下载前校验 URL,
阻断环回/内网/链路本地/云元数据及 IPv6 编码形式(ipv4-mapped/6to4/NAT64/Teredo)的绕过。
"""

import asyncio
import ipaddress

import pytest

from nekro_agent.tools.common_util import (
    BlockedDownloadAddress,
    UnsafeDownloadUrl,
    _candidate_ips,
    _is_ip_blocked,
    assert_safe_download_url,
)


@pytest.mark.parametrize(
    ("ip_text", "expect_blocked", "label"),
    [
        # 常规 IPv4 保留段
        ("127.0.0.1", True, "环回"),
        ("10.0.0.5", True, "RFC1918 10/8"),
        ("172.16.0.1", True, "RFC1918 172.16/12"),
        ("192.168.1.1", True, "RFC1918 192.168/16"),
        ("169.254.169.254", True, "云元数据"),
        ("100.64.0.1", True, "CGNAT"),
        # IPv4-mapped IPv6(曾可绕过的 PoC)
        ("::ffff:127.0.0.1", True, "IPv4-mapped 环回"),
        ("::ffff:10.0.0.5", True, "IPv4-mapped 内网"),
        ("::ffff:169.254.169.254", True, "IPv4-mapped 云元数据"),
        # 6to4 内嵌 IPv4
        ("2002:7f00:1::", True, "6to4 编码 127.0.0.1"),
        ("2002:0a00:0005::", True, "6to4 编码 10.0.0.5"),
        # NAT64(Well-Known Prefix)编码 IPv4
        ("64:ff9b::7f00:1", True, "NAT64 编码 127.0.0.1"),
        ("64:ff9b::a00:2", True, "NAT64 编码 10.0.2"),
        # 其他 IPv6 保留段
        ("::1", True, "IPv6 环回"),
        ("::", True, "未指定地址"),
        ("fe80::1", True, "链路本地"),
        ("fd12::1", True, "ULA"),
        # 公网地址不应误伤(编码形式的公网同样放行)
        ("8.8.8.8", False, "公网 IPv4"),
        ("1.1.1.1", False, "公网 IPv4"),
        ("::ffff:8.8.8.8", False, "IPv4-mapped 公网"),
        ("2002:808:808::", False, "6to4 编码公网 8.8.8.8"),
        ("64:ff9b::808:808", False, "NAT64 编码公网"),
        ("2606:4700::1111", False, "公网 IPv6"),
        # 非法输入按拦截处理(fail-closed)
        ("not-an-ip", True, "非法输入"),
    ],
)
def test_is_ip_blocked_matrix(ip_text: str, expect_blocked: bool, label: str):
    assert _is_ip_blocked(ip_text) is expect_blocked, label


def test_candidate_ips_expands_nat64():
    """ipaddress 不自动解码 NAT64,防护需手动展开低 32 位"""
    candidates = _candidate_ips("64:ff9b::7f00:1")
    assert "127.0.0.1" in candidates


def test_candidate_ips_expands_ipv4_mapped():
    candidates = _candidate_ips("::ffff:127.0.0.1")
    assert "127.0.0.1" in candidates


@pytest.mark.asyncio
async def test_assert_safe_url_blocks_internal():
    """URL 层面:字面量内网地址应被分类拦截(字面量解析不依赖网络)"""
    with pytest.raises(BlockedDownloadAddress):
        await assert_safe_download_url("http://127.0.0.1:8021/api/health")
    with pytest.raises(BlockedDownloadAddress):
        await assert_safe_download_url("http://[::ffff:169.254.169.254]/latest/meta-data")


@pytest.mark.asyncio
async def test_assert_safe_url_classifies_malformed():
    """URL 层面:格式/协议问题应归类为 UnsafeDownloadUrl 而非安全拦截"""
    with pytest.raises(UnsafeDownloadUrl):
        await assert_safe_download_url("ftp://example.com/x")
    with pytest.raises(UnsafeDownloadUrl):
        await assert_safe_download_url("not-a-url")


def test_extra_blocked_cidrs_append_only(monkeypatch: pytest.MonkeyPatch):
    """NEKRO_SSRF_EXTRA_BLOCKED_CIDRS 仅追加网段,不影响内置与对照段"""
    monkeypatch.setenv("NEKRO_SSRF_EXTRA_BLOCKED_CIDRS", "172.20.0.0/16, garbage@@, fd99::/8")
    assert _is_ip_blocked("172.20.1.1") is True  # 追加段生效
    assert _is_ip_blocked("fd99::1") is True  # 追加 IPv6 段生效
    assert _is_ip_blocked("203.0.114.1") is False  # 未涉及的公网段不受影响
    assert _is_ip_blocked("127.0.0.1") is True  # 内置段不受影响


def test_blocked_networks_parse():
    """内置网段常量本身可被 ipaddress 解析(防止笔误引入失效条目)"""
    from nekro_agent.tools.common_util import _SSRF_BLOCKED_NETWORKS

    assert all(isinstance(n, (ipaddress.IPv4Network, ipaddress.IPv6Network)) for n in _SSRF_BLOCKED_NETWORKS)


# ===================== DNS 重绑定:连接固定 =====================


@pytest.mark.asyncio
async def test_assert_safe_url_returns_pinned_ip():
    """校验函数返回可用于连接固定的已校验 IP"""
    pinned = await assert_safe_download_url("http://one.one.one.one/x")
    ipaddress.ip_address(pinned)  # 返回值必须是合法 IP 文本


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "pinned_ip", "expected_host", "expected_sni"),
    [
        ("https://example.com/path", "93.184.216.34", "example.com", "example.com"),
        ("https://example.com:8443/path", "93.184.216.34", "example.com:8443", "example.com"),
        ("http://example.com:443/path", "93.184.216.34", "example.com:443", None),
        (
            "https://[2606:4700::1111]:8443/path",
            "2606:4700::1111",
            "[2606:4700::1111]:8443",
            "2606:4700::1111",
        ),
    ],
)
async def test_pinned_transport_preserves_authority_and_sni(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    pinned_ip: str,
    expected_host: str,
    expected_sni: str | None,
):
    import httpx

    import nekro_agent.tools.common_util as cu

    captured: dict[str, object] = {}

    async def capture_transport(_transport, request: httpx.Request) -> httpx.Response:
        captured.update(
            url_host=request.url.host,
            host=request.headers["Host"],
            sni=request.extensions.get("sni_hostname"),
        )
        return httpx.Response(200, content=b"ok", request=request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", capture_transport)
    request = httpx.Request("GET", url, headers={"Host": "attacker.invalid"}, extensions={"trace": "keep"})
    original_url = request.url
    original_headers = request.headers
    original_extensions = request.extensions
    transport = cu._PinnedAsyncTransport(pinned_ip)

    response = await transport.handle_async_request(request)

    assert response.status_code == 200
    assert captured == {"url_host": pinned_ip, "host": expected_host, "sni": expected_sni}
    assert request.url is original_url
    assert request.headers is original_headers
    assert request.headers["Host"] == "attacker.invalid"
    assert request.extensions is original_extensions
    assert request.extensions == {"trace": "keep"}


@pytest.mark.asyncio
async def test_pinned_transport_restores_request_after_error(monkeypatch: pytest.MonkeyPatch):
    import httpx

    import nekro_agent.tools.common_util as cu

    async def fail_transport(_transport, _request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("test failure")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", fail_transport)
    request = httpx.Request("GET", "https://example.com/path", extensions={"trace": "keep"})
    original_url = request.url
    original_headers = request.headers
    original_extensions = request.extensions
    transport = cu._PinnedAsyncTransport("93.184.216.34")

    with pytest.raises(httpx.ConnectError, match="test failure"):
        await transport.handle_async_request(request)

    assert request.url is original_url
    assert request.headers is original_headers
    assert request.extensions is original_extensions
    assert "sni_hostname" not in request.extensions


@pytest.mark.asyncio
async def test_download_pins_connection_and_revalidates_redirects(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """连接固定到首次解析的 IP,重定向目标在连接前重新校验"""
    import httpx

    import nekro_agent.tools.common_util as cu

    public_ip = "93.184.216.34"
    calls: dict[str, object] = {"dns": 0, "connect_hosts": [], "host_headers": []}

    async def rebinding_getaddrinfo(host, port=None, **_kwargs):
        calls["dns"] += 1
        ip = public_ip if calls["dns"] % 2 == 1 else "127.0.0.1"
        return [(0, 2, 6, "", (ip, port))]

    async def recording_transport(_transport, request: httpx.Request) -> httpx.Response:
        calls["connect_hosts"].append(str(request.url.host))
        calls["host_headers"].append(request.headers["Host"])
        return httpx.Response(
            302,
            headers={"location": "http://internal.rebind.example/x"},
            content=b"",
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", recording_transport)
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", rebinding_getaddrinfo)

    with pytest.raises(BlockedDownloadAddress):
        await cu.download_file(
            "http://first.rebind.example/x",
            file_path=str(tmp_path / "out.bin"),
            file_name="out.bin",
        )

    assert calls["connect_hosts"] == [public_ip]
    assert calls["host_headers"] == ["first.rebind.example"]
    assert calls["dns"] == 2
