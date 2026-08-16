import asyncio
import base64
import difflib
import hashlib
import ipaddress
import mimetypes
import os
import random
import re
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

import aiofiles
import httpx
import magic
import toml
from PIL import Image

from nekro_agent.core import logger
from nekro_agent.core.config import CoreConfig
from nekro_agent.core.os_env import USER_UPLOAD_DIR
from nekro_agent.tools.path_convertor import is_url_path, sanitize_chat_key_for_path

_APP_VERSION: str = ""

# 解析 URL 主机名后拒绝的地址段(环回/内网/链路本地/云元数据等)
_SSRF_BLOCKED_NETWORKS = [
    ipaddress.ip_network(n)
    for n in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "224.0.0.0/4",
        "240.0.0.0/4",
        # IPv4-mapped(::ffff:0:0/96)与 NAT64(64:ff9b::/96)不整体封禁:
        # 由 _candidate_ips 解出内嵌 IPv4 后按上述 IPv4 段判断,
        # 保证编码公网地址(如 ::ffff:8.8.8.8)仍可正常放行
        "::/127",  # 含 ::(未指定)与 ::1(环回)
        "100::/64",  # 丢弃前缀
        "2001:db8::/32",  # 文档示例段
        "fc00::/7",  # ULA
        "fe80::/10",  # 链路本地
    )
]


def _candidate_ips(ip_text: str) -> list[str]:
    """展开一个地址文本为需逐一检查的等价地址列表

    IPv6 的多种形式可编码可达 IPv4 的目标:
    - ::ffff:127.0.0.1(IPv4-mapped)
    - 64:ff9b::127.0.0.1(NAT64)
    - 2002:7f00:1::(6to4,内嵌任意 IPv4)
    全部解出后与原始形式一起比对,阻断经 IPv6 记法绕过 IPv4 封锁。
    """
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return [ip_text]
    candidates = [ip]
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            candidates.append(ip.ipv4_mapped)
        sixtofour = ip.sixtofour
        if sixtofour:
            candidates.append(sixtofour)
        teredo = ip.teredo
        if teredo:
            # teredo 返回 (server, client);client 才是实际通信对端
            candidates.append(teredo[1])
        if ip in ipaddress.ip_network("64:ff9b::/96"):
            # NAT64(Well-Known Prefix):低 32 位即被编码的 IPv4,
            # ipaddress 不自动解出,需手动提取
            candidates.append(ipaddress.ip_address(int(ip) & 0xFFFFFFFF))
    return [str(c) for c in candidates]


def _extra_blocked_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """读取运维追加的封锁网段(NEKRO_SSRF_EXTRA_BLOCKED_CIDRS)

    逗号分隔的 CIDR 列表,如 "172.20.0.0/16,fd00::/8"。
    仅支持追加:内置网段不可通过配置移除——若允许"放宽",
    能写配置的人(或诱导修改配置的攻击者)即可解除防护。
    非法条目记日志跳过,不影响其余条目生效。
    """
    raw = os.environ.get("NEKRO_SSRF_EXTRA_BLOCKED_CIDRS", "")
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            logger.warning(f"NEKRO_SSRF_EXTRA_BLOCKED_CIDRS 中的非法 CIDR 已忽略: {item}")
    return networks


def _is_ip_blocked(ip_text: str) -> bool:
    """判断地址(含 IPv6 编码的 IPv4 等价形式)是否落在被拒绝的保留地址段内"""
    try:
        for candidate in _candidate_ips(ip_text):
            ip = ipaddress.ip_address(candidate)
            if any(ip in network for network in _SSRF_BLOCKED_NETWORKS):
                return True
            if any(ip in network for network in _extra_blocked_networks()):
                return True
        return False
    except ValueError:
        return True


class UnsafeDownloadUrl(ValueError):
    """URL 本身不合法(格式错误/协议不支持/域名无法解析)

    与 BlockedDownloadAddress 区分:调用方可将本错误作为用户输入校验
    问题处理(提示修改 URL),而不是安全拦截。
    """


class BlockedDownloadAddress(ValueError):
    """URL 指向内网/环回/链路本地等保留地址,被 SSRF 防护拦截"""


async def assert_safe_download_url(url: str) -> None:
    """下载前校验 URL,不通过时抛出分类异常

    用于在下载用户(或 LLM 生成代码)提供的文件前拦截 SSRF:
    阻止访问本机 API、内网 Postgres/Qdrant、云元数据服务等。

    异常分类:
    - UnsafeDownloadUrl:URL 格式非法、协议不受支持或域名解析失败
      (输入本身有问题,重试无意义)
    - BlockedDownloadAddress:URL 指向保留地址段(安全拦截)

    限制说明(调用方需知):
    - 校验时与 httpx 实际连接时各自做一次 DNS 解析,理论存在重绑定
      TOCTOU 窗口;当前 httpx 默认不跟随重定向,公网 302 → 内网的
      绕径不可行。若未来开启 follow_redirects,需在传输层固定已校验 IP。
    - DNS 解析通过事件循环的 getaddrinfo 执行,不阻塞其他协程。
    """
    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise UnsafeDownloadUrl(f"URL 格式无效: {limited_text_output(url)}") from e
    if parsed.scheme not in ("http", "https"):
        raise UnsafeDownloadUrl(f"仅支持 http/https 协议: {limited_text_output(url)}")
    host = parsed.hostname
    if not host:
        raise UnsafeDownloadUrl(f"URL 缺少主机名: {limited_text_output(url)}")
    try:
        loop = asyncio.get_running_loop()
        addr_infos = await loop.getaddrinfo(host, None)
    except OSError as e:
        raise UnsafeDownloadUrl(f"域名无法解析: {limited_text_output(host)}") from e
    for _, _, _, _, sockaddr in addr_infos:
        if _is_ip_blocked(sockaddr[0]):
            raise BlockedDownloadAddress(
                f"不允许下载内网或保留地址的资源: {limited_text_output(url)}"
            )




def get_app_version() -> str:
    """获取当前应用版本号

    Returns:
        str: 应用版本号
    """
    global _APP_VERSION
    if _APP_VERSION:
        return _APP_VERSION
    pyproject = toml.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    try:
        _APP_VERSION = pyproject["project"]["version"]
    except KeyError:
        _APP_VERSION = "unknown"
    return _APP_VERSION


def compare_semver(a: str, b: str) -> int:
    """比较两个语义化版本号

    按 major.minor.patch 逐段比较，不支持预发布标签。
    格式异常的版本号视为无约束，返回 0。

    Args:
        a: 版本号字符串，如 "2.3.0"
        b: 版本号字符串，如 "2.4.1"

    Returns:
        int: a < b 返回 -1，a == b 返回 0，a > b 返回 1
    """
    def parse(v: str) -> list[int]:
        parts = [p for p in v.strip().split(".") if p]
        result: list[int] = []
        for p in parts[:3]:
            if not p.isdigit():
                raise ValueError(f"非法版本段: {p!r}")
            result.append(int(p))
        return result

    try:
        pa, pb = parse(a), parse(b)
    except (ValueError, AttributeError):
        return 0

    # 补齐长度到 3 段
    while len(pa) < 3:
        pa.append(0)
    while len(pb) < 3:
        pb.append(0)

    for x, y in zip(pa, pb):
        if x < y:
            return -1
        if x > y:
            return 1
    return 0


async def download_file(
    url: str,
    file_path: str = "",
    file_name: str = "",
    use_suffix: str = "",
    retry_count: int = 3,
    from_chat_key: str = "",
) -> Tuple[str, str]:
    """下载文件

    Args:
        url (str): 下载链接
        file_path (str): 保存路径

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """

    try:
        await assert_safe_download_url(url)
    except UnsafeDownloadUrl:
        # URL 本身不合法,重试无意义,直接抛出(ValueError 子类,向后兼容)
        raise
    except BlockedDownloadAddress:
        logger.warning(f"已拦截指向内网/保留地址的下载请求: {limited_text_output(url)}")
        raise

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content
            if not use_suffix:
                mime = magic.from_buffer(content, mime=True)
                use_suffix = f'.{mime.split("/")[1]}' if mime and len(mime.split("/")) > 1 else ""
            if not file_path:
                file_name = file_name or f"{hashlib.md5(response.content).hexdigest()}{use_suffix}"
                if from_chat_key:
                    save_path = Path(USER_UPLOAD_DIR) / sanitize_chat_key_for_path(from_chat_key) / Path(file_name)
                else:
                    save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                file_path = str(save_path)
            Path(file_path).write_bytes(content)
            Path(file_path).chmod(0o755)
    except Exception:
        if retry_count > 0:
            return await download_file(
                url,
                file_path,
                file_name,
                use_suffix,
                retry_count=retry_count - 1,
                from_chat_key=from_chat_key,
            )
        raise
    else:
        return file_path, file_name


async def download_file_from_bytes(
    bytes_data: bytes,
    file_path: str = "",
    file_name: str = "",
    use_suffix: str = "",
    from_chat_key: str = "",
) -> Tuple[str, str]:
    """下载文件

    Args:
        url (str): 下载链接
        file_path (str): 保存路径

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """

    if not file_path:
        file_name = file_name or f"{hashlib.md5(bytes_data).hexdigest()}{use_suffix}"
        if from_chat_key:
            save_path = Path(USER_UPLOAD_DIR) / sanitize_chat_key_for_path(from_chat_key) / Path(file_name)
        else:
            save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = str(save_path)
    Path(file_path).write_bytes(bytes_data)
    Path(file_path).chmod(0o755)
    return file_path, file_name


async def download_file_from_base64(
    base64_str: str,
    file_path: str = "",
    file_name: str = "",
    use_suffix: str = "",
    from_chat_key: str = "",
) -> Tuple[str, str]:
    """下载文件(从base64字符串)

    Args:
        base64_str (str): base64字符串
        file_path (str): 保存路径

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """
    logger.debug(f"下载文件(从base64字符串): {base64_str[:100]}")
    if base64_str.startswith("data:") and not use_suffix:
        mime_type = mimetypes.guess_type(base64_str)[0] or ""
        use_suffix = f".{mime_type.split('/')[1]}" if mime_type and len(mime_type.split("/")) > 1 else ""
    if base64_str.startswith("data:"):
        base64_str = base64_str.split(",")[1]

    if not file_path:
        file_name = file_name or f"{hashlib.md5(base64_str.encode()).hexdigest()}{use_suffix}"
        if from_chat_key:
            save_path = Path(USER_UPLOAD_DIR) / sanitize_chat_key_for_path(from_chat_key) / Path(file_name)
        else:
            save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = str(save_path)
    Path(file_path).write_bytes(base64.b64decode(base64_str.encode(encoding="utf-8")))
    Path(file_path).chmod(0o755)
    return file_path, file_name


async def copy_to_upload_dir(
    file_path: str,
    file_name: str = "",
    use_suffix: str = "",
    from_chat_key: str = "",
) -> Tuple[str, str]:
    """复制文件到上传目录

    Args:
        file_path (str): 文件路径
        file_name (str): 文件名

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """
    if not file_name:
        file_name = f"{hashlib.md5(Path(file_path).read_bytes()).hexdigest()}{use_suffix}"
    if from_chat_key:
        save_path = Path(USER_UPLOAD_DIR) / sanitize_chat_key_for_path(from_chat_key) / Path(file_name)
    else:
        save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    Path(save_path).write_bytes(Path(file_path).read_bytes())
    Path(save_path).chmod(0o755)
    return str(save_path), file_name


def random_chat_check(config: CoreConfig) -> bool:
    """随机聊天检测

    Returns:
        bool: 是否随机聊天
    """

    return random.random() < config.AI_CHAT_RANDOM_REPLY_PROBABILITY


def check_content_trigger(content: str, config: CoreConfig) -> bool:
    """内容触发检测

    Args:
        content (str): 内容

    Returns:
        bool: 是否触发
    """

    for reg_text in config.AI_CHAT_TRIGGER_REGEX:
        reg = re.compile(reg_text)
        if reg.search(content):
            return True
    return False


def check_forbidden_message(content: str, config: CoreConfig) -> bool:
    """忽略消息检测

    Args:
        content (str): 内容

    Returns:
        bool: 是否忽略
    """

    for reg_text in config.AI_CHAT_IGNORE_REGEX:
        reg = re.compile(reg_text)
        _r = reg.search(content)
        if _r:
            logger.info(f'忽略消息: "{content}" - 命中正则: "{reg_text}" 匹配内容: "{_r.group(0)}"')
            return True
    return False


def compress_image(image_path: Path, size_limit_kb: int) -> Path:
    """压缩图片到指定大小以下，仅通过降低分辨率实现

    Args:
        image_path: 原图片路径
        size_limit_kb: 目标大小（KB）

    Returns:
        压缩后的图片路径
    """
    compressed_suffix = "_compressed"
    # 检查是否已经有压缩版本
    compressed_path = image_path.parent / f"{image_path.stem}{compressed_suffix}{image_path.suffix}"
    if compressed_path.exists():
        return compressed_path

    # 打开图片
    img = Image.open(image_path)

    # 确保图片在 RGB 模式
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 初始缩放比例
    scale = 1.0
    output_path = compressed_path

    while True:
        # 计算新的尺寸
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 保存压缩后的图片（使用最高质量）
        resized_img.save(output_path, quality=100)

        # 检查文件大小
        if output_path.stat().st_size <= size_limit_kb * 1024 or scale < 0.1:
            break

        # 降低分辨率继续尝试
        scale *= 0.8

    return output_path


def limited_text_output(text: str, limit: int = 1000, placeholder: str = "...") -> str:
    """限制文本输出

    Args:
        text (str): 文本
        limit (int): 限制长度
    """

    if len(text) <= limit:
        return text
    left_limit = limit // 2 - len(placeholder) // 2
    right_limit = limit - left_limit
    return text[:left_limit] + placeholder + text[-right_limit:]


async def calculate_file_md5(file_path: str, strict: bool = False) -> str:
    """计算文件的 MD5 值或获取标识

    Args:
        file_path (str): 文件路径或 URL

    Returns:
        str: 本地文件返回 MD5 哈希值，URL 返回其链接
    """
    # 对于网络资源，直接返回 URL 作为标识
    if is_url_path(file_path):
        return hashlib.md5(file_path.encode()).hexdigest()

    # 处理本地文件
    try:
        md5_hash = hashlib.md5()
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(4096)
                if not chunk:
                    break
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        if strict:
            raise
        logger.warning(f"计算文件 MD5 失败: {e}")
        return file_path  # 如果无法计算 MD5，则返回文件路径作为标识


def calculate_text_similarity(text1: str, text2: str, min_length: int = 12) -> float:
    """计算两段文本的相似度

    Args:
        text1 (str): 第一段文本
        text2 (str): 第二段文本

    Returns:
        float: 相似度（0-1）
    """
    if len(text1) < min_length or len(text2) < min_length:
        return 0
    return difflib.SequenceMatcher(None, text1, text2).ratio()
