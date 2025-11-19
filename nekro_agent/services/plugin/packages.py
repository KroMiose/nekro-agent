# nekro_agent/services/plugin/packages.py
import importlib
import shlex
import subprocess
import sys
import urllib.parse
from importlib.metadata import distributions
from pathlib import Path
from typing import Any, Optional

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import parse as parse_version

from nekro_agent.core.os_env import PLUGIN_DYNAMIC_PACKAGE_DIR


# ---------- 公开 API ----------
def dynamic_import_pkg(
    package_spec: str,
    import_name: Optional[str] = None,
    *,
    mirror: Optional[str] = "https://pypi.tuna.tsinghua.edu.cn/simple",
    trusted_host: bool = True,
    timeout: int = 300,
    repo_dir: Optional[Path] = None,
) -> Any:
    """
    动态安装并导入 Python 包
     Raises
        RuntimeError: 安装失败
        ImportError:  导入失败
    """
    req = _parse_spec(package_spec)
    repo_dir = repo_dir or Path(PLUGIN_DYNAMIC_PACKAGE_DIR)
    site_dir = _ensure_repo(repo_dir)

    if not _is_installed(req, site_dir):
        _install_package(req, mirror, trusted_host, timeout, repo_dir)

    return _import_module(import_name or req.name, site_dir)


# ---------- 内部辅助 ----------
def _parse_spec(spec: str) -> Requirement:
    """解析 'requests>=2.25,<3' 这类规范"""
    try:
        return Requirement(spec)
    except Exception as e:
        raise ValueError(f"非法包规范 {spec!r}: {e}") from e


def _ensure_repo(repo_dir: Path) -> Path:
    """确保仓库目录存在，返回 site-packages 路径"""
    site_dir = repo_dir.resolve() / "site-packages"
    site_dir.mkdir(parents=True, exist_ok=True)
    # 注入 import 路径
    for p in (repo_dir.resolve(), site_dir):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    return site_dir


def _is_installed(req: Requirement, site_dir: Path) -> bool:
    """检查 site_dir 是否已满足规范"""
    for dist in distributions(path=[str(site_dir)]):
        # if dist.metadata["Name"] == req.name and (not req.specifier or parse_version(dist.version) in req.specifier):
        if dist.metadata["Name"] == req.name:
            return True
    return False


def _install_package(
    req: Requirement,
    mirror: Optional[str],
    trusted_host: bool,
    timeout: int,
    repo_dir: Path,
) -> None:
    """pip 安装到指定目录"""
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--quiet",
        "--no-input",
        "--no-warn-script-location",
        "--target",
        str(repo_dir),
        str(req),
    ]
    if mirror:
        cmd.extend(["--index-url", mirror])
        if trusted_host and (host := urllib.parse.urlparse(mirror).hostname):
            cmd.extend(["--trusted-host", shlex.quote(host)])

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(_parse_pip_error(e.stderr or e.stdout)) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"安装 {req} 超时（{timeout}s）") from e


def _import_module(name: str, site_dir: Path) -> Any:
    """导入模块，失败时刷新 site 目录再试一次"""
    try:
        return importlib.import_module(name)
    except ImportError:
        import site

        site.addsitedir(str(site_dir))
        try:
            return importlib.import_module(name)
        except ImportError as e:
            raise ImportError(f"安装成功但无法导入 {name}") from e


def _parse_pip_error(output: str) -> str:
    """友好化 pip 报错"""
    patterns = {
        "No matching distribution": "包不存在或版本不可用",
        "Could not find a version": "找不到指定版本",
        "SSL: CERTIFICATE_VERIFY_FAILED": "SSL 验证失败，尝试 trusted_host=True",
        "403": "访问被拒绝（镜像源可能需要认证）",
        "404": "资源不存在",
        "Connection refused": "连接被拒绝，检查镜像源地址",
        "Network is unreachable": "网络不可达",
    }
    for k, v in patterns.items():
        if k in output:
            return v
    return output[:200] + "..." if len(output) > 200 else output
