"""
# 网页转 Markdown (HTML to Markdown)

赋予 AI 抓取任意网页并解析为 Markdown 的能力。

## 主要功能

- **网页抓取**: 通过 HTTP 请求获取网页 HTML 内容。
- **编码自适应**: 自动检测网页编码（通过 HTTP 头、meta 标签、apparent_encoding），避免乱码。
- **HTML 清洗**: 移除脚本、样式等干扰标签，提取正文内容。
- **Markdown 转换**: 将清洗后的 HTML 转为 Markdown，供大模型阅读。
- **解析器兼容**: 优先使用 lxml 解析器，若环境动态安装 lxml 后 bs4 未感知，自动刷新缓存并回退到 html.parser。

## 使用方法

此插件主要由 AI 在后台根据需要自动调用。当 AI 需要访问某个网页获取详细信息时，会调用 `fetch_html_to_markdown` 工具。
"""

from typing import Any, Optional

from nekro_agent.api import core, i18n
from nekro_agent.api.plugin import (
    ConfigBase,
    ExtraField,
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.api.schemas import AgentCtx
from pydantic import Field

plugin = NekroPlugin(
    name="网页转Markdown",
    module_name="html2md",
    description="抓取网页内容并转换为 Markdown",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="网页转Markdown",
        en_US="HTML to Markdown",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="抓取网页内容并转换为 Markdown",
        en_US="Fetch web page content and convert to Markdown",
    ),
    allow_sleep=True,
    sleep_brief="用于抓取网页并提取正文内容。仅在需要获取网页详细信息时激活。",
)


@plugin.mount_config()
class Html2MdConfig(ConfigBase):
    """网页转 Markdown 配置"""

    USER_AGENT: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        title="User-Agent",
        description="请求时使用的 User-Agent",
    )
    TIMEOUT: int = Field(
        default=20,
        title="请求超时(秒)",
        description="HTTP 请求超时时间",
    )
    MAX_LENGTH: int = Field(
        default=8000,
        title="最大返回长度",
        description="返回内容的最大字符数，0 表示不限制",
    )
    KEEP_LINKS: bool = Field(
        default=True,
        title="保留超链接",
        description="转换后的 Markdown 是否保留超链接",
    )
    REMOVE_SCRIPTS: bool = Field(
        default=True,
        title="移除脚本和样式",
        description="是否移除 <script>、<style> 等标签",
    )
    USE_LXML: bool = Field(
        default=True,
        title="优先使用 lxml 解析器",
        description="若环境中已安装 lxml，优先使用以获得更好的解析效果",
    )


config: Html2MdConfig = plugin.get_config(Html2MdConfig)


def _get_proxy() -> Optional[str]:
    """获取代理配置"""
    try:
        proxy = getattr(core.config, "DEFAULT_PROXY", None)
    except Exception:
        proxy = None
    if proxy:
        if isinstance(proxy, str) and proxy.startswith(("http://", "https://")):
            return proxy
        return f"http://{proxy}"
    return None


def _resolve_encoding(response) -> str:
    """智能检测响应编码，避免 ISO-8859-1 误判。

    优先级:
    1. HTTP Content-Type 头中的 charset
    2. <meta charset="..."> 标签
    3. <meta http-equiv="Content-Type" content="...charset=..."> 标签
    4. response.apparent_encoding (chardet 猜测)
    5. 回退 UTF-8
    """
    # 1. HTTP 头中的 charset
    encoding = response.encoding
    if encoding and encoding.lower() not in ("iso-8859-1", "latin-1"):
        return encoding

    # 2/3. 从 HTML 内容中解析 meta charset
    text = response.text
    import re

    # <meta charset="utf-8">
    m = re.search(r'<meta\s+charset=["\']([^"\']+)["\']', text, re.IGNORECASE)
    if m:
        return m.group(1)

    # <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    m = re.search(
        r'<meta\s+http-equiv=["\']?Content-Type["\']?\s+content=["\'][^"\']*charset=([^"\';\s]+)',
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # 4. apparent_encoding
    apparent = getattr(response, "apparent_encoding", None)
    if apparent:
        return apparent

    # 5. 回退
    return "utf-8"


def _import_bs4_with_lxml_fallback():
    """导入 bs4，处理 lxml 动态安装后的缓存感知延迟问题。

    如果 lxml 是在 bs4 首次 import 之后才安装的，bs4 的 builder 注册表中不会包含 'lxml'。
    本函数通过 sys.modules 清理 + reload 强制刷新注册表。
    """
    import importlib
    import sys

    try:
        from nekro_agent.services.plugin.packages import dynamic_import_pkg
    except Exception:
        from nekro_agent.api.plugin import dynamic_import_pkg  # type: ignore

    # 先确保 lxml 已安装（如果配置要求）
    lxml_available = False
    if config.USE_LXML:
        try:
            dynamic_import_pkg("lxml", import_name="lxml")
            lxml_available = True
        except Exception:
            pass

    # 如果 bs4 之前已被缓存，且当时没有 lxml，需要刷新 builder 注册表
    if "bs4" in sys.modules and lxml_available:
        # 清除 bs4 子模块缓存
        bs4_keys = [k for k in list(sys.modules.keys()) if k.startswith("bs4.")]
        for key in bs4_keys:
            del sys.modules[key]
        importlib.reload(sys.modules["bs4"])

    # 现在安全地导入 bs4（会正确扫描到 lxml）
    bs4 = dynamic_import_pkg("beautifulsoup4>=4.9.0", import_name="bs4")
    return bs4, lxml_available


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="fetch_html_to_markdown",
    description="抓取指定 URL 的网页内容，清洗后转换为 Markdown 返回。参数：url(str)",
)
async def fetch_html_to_markdown(_ctx: AgentCtx, url: str) -> str:
    """抓取网页并转换为 Markdown

    Args:
        url (str): 目标网页 URL（必须以 http:// 或 https:// 开头）

    Returns:
        str: 网页内容的 Markdown 表示
    """
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("请提供有效的 http/https 网页链接")

    try:
        from nekro_agent.services.plugin.packages import dynamic_import_pkg
    except Exception:
        from nekro_agent.api.plugin import dynamic_import_pkg  # type: ignore

    requests = dynamic_import_pkg("requests>=2.25.0")
    bs4, lxml_available = _import_bs4_with_lxml_fallback()

    proxy = _get_proxy()
    proxies = {"http": proxy, "https": proxy} if proxy else None

    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=config.TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return f"# 网页抓取失败\n\n- URL: {url}\n- 错误: {e}"

    # === 编码修复：智能检测并设置正确编码 ===
    detected_encoding = _resolve_encoding(resp)
    if detected_encoding and resp.encoding != detected_encoding:
        resp.encoding = detected_encoding

    html = resp.text
    if not html:
        return f"# 网页内容为空\n\n- URL: {url}"

    # === 解析器选择：优先 lxml，动态安装后已刷新缓存 ===
    parser = "lxml" if (config.USE_LXML and lxml_available) else "html.parser"
    try:
        soup = bs4.BeautifulSoup(html, parser)
    except Exception:
        # 最后的回退
        soup = bs4.BeautifulSoup(html, "html.parser")

    # 清洗 HTML
    if config.REMOVE_SCRIPTS:
        for tag in soup(["script", "noscript", "style", "link", "nav", "footer", "header", "aside"]):
            tag.decompose()

    # 提取标题
    title = ""
    try:
        t = soup.select_one("title")
        title = t.get_text(strip=True) if t else ""
    except Exception:
        pass

    # 提取正文（优先 article/main，否则 body）
    body = soup.select_one("article") or soup.select_one("main") or soup.select_one("body") or soup

    # 转换为 Markdown
    md_text = ""
    try:
        markdownify = dynamic_import_pkg("markdownify>=0.11.6", import_name="markdownify")
        md_text = markdownify.markdownify(
            str(body),
            heading_style="ATX",
            bullets="-",
            keep_inline_images=True,
        )
    except Exception:
        try:
            html2text = dynamic_import_pkg("html2text>=2020.1.16", import_name="html2text")
            conv = html2text.HTML2Text()
            conv.ignore_links = not config.KEEP_LINKS
            conv.body_width = 0
            conv.unicode_snob = True
            md_text = conv.handle(str(body))
        except Exception:
            # 最简回退：直接提取纯文本
            md_text = body.get_text(separator="\n", strip=True)

    # 组装结果
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
    else:
        lines.append("# 网页内容")
    lines.append(f"- 来源: {url}")
    lines.append("")
    lines.append(md_text.strip())

    result = "\n".join(lines)

    if config.MAX_LENGTH > 0 and len(result) > config.MAX_LENGTH:
        result = result[: config.MAX_LENGTH - 3] + "..."

    return result
