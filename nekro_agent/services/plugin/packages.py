import importlib
import subprocess
import sys
import urllib.parse
from importlib.metadata import PackageNotFoundError, distributions
from pathlib import Path
from typing import Any, Optional

from packaging.specifiers import SpecifierSet
from packaging.version import parse

from nekro_agent.core.os_env import OsEnv

def load_packages(
    package_spec: str,
    import_name: Optional[str] = None,
    mirror: Optional[str] = "https://pypi.tuna.tsinghua.edu.cn/simple",
    trusted_host: bool = True,
    timeout: int = 300,
    repo_dir: Optional[str] = Path(OsEnv.DATA_DIR) / "packages",
) -> Any:
    """动态安装并导入Python包

    Args:
        package_spec: 包名称和版本规范 (如 "requests" 或 "numpy==1.21.0")
        import_name: 导入名称（如果与包名不同）
        mirror: PyPI镜像源URL
        trusted_host: 是否信任镜像源主机
        timeout: 安装超时时间（秒）
        repo_dir: 持久化存储目录 (默认使用系统路径)

    Returns:
        导入的模块对象

    Raises:
        RuntimeError: 安装失败时抛出
        ImportError: 导入失败时抛出
    """
    # 提取基础包名和版本约束
    package_name = package_spec.strip()
    version_spec = ""
    for sep in ["==", ">=", "<=", "!=", ">", "<", "~="]:
        if sep in package_name:
            package_name, version_spec = package_name.split(sep, 1)
            package_name = package_name.strip()
            version_spec = f"{sep}{version_spec.strip()}"
            break

    # 配置持久化仓库路径
    if repo_dir:
        repo_path = Path(repo_dir)
        repo_path.mkdir(parents=True, exist_ok=True)
        repo_site_packages = repo_path / "site-packages"
        repo_site_packages.mkdir(parents=True, exist_ok=True)

        # 添加路径到sys.path
        for path in [str(repo_path), str(repo_site_packages)]:
            if path not in sys.path:
                sys.path.insert(0, path)

    # 检查是否已安装符合条件的版本
    need_install = True
    try:
        # 处理distributions函数的path参数
        if repo_dir:
            path_list = [repo_dir]
            dists = distributions(path=path_list)
        else:
            dists = distributions()

        for dist in dists:
            metadata = dist.metadata
            dist_name = getattr(metadata, "Name", None) or dist.name
            if dist_name.lower() == package_name.lower() and (
                not version_spec or parse(dist.version) in SpecifierSet(version_spec)
            ):
                need_install = False
                break
    except PackageNotFoundError:
        pass

    # 构建安装命令
    if need_install:
        install_cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--quiet",
            "--no-input",
            "--no-warn-script-location",
        ]

        # 添加持久化目录参数
        if repo_dir:
            install_cmd += ["--target", repo_dir]

        # 添加镜像源配置
        if mirror:
            install_cmd += ["--index-url", mirror]
            if trusted_host:
                host = urllib.parse.urlparse(mirror).hostname
                if host:
                    install_cmd += ["--trusted-host", host]

        install_cmd.append(package_spec)

        # 执行安装
        try:
            subprocess.run(install_cmd, capture_output=True, text=True, check=True, timeout=timeout)
        except subprocess.CalledProcessError as e:
            error_msg = _parse_pip_error(e.stderr or e.stdout)
            print(f"安装 {package_spec} 失败: {error_msg}")
            exit(1)
        except subprocess.TimeoutExpired:
            print(f"安装 {package_spec} 超时（{timeout}秒），请检查网络连接")
            exit(1)

    # 确定导入模块名称
    module_name = import_name if import_name is not None else package_name

    # 动态导入模块
    try:
        module = importlib.import_module(module_name)
        module = importlib.reload(module)  # 确保加载最新版本
    except ImportError:
        # 尝试刷新导入路径
        if repo_dir:
            import site

            site.addsitedir(repo_dir)
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                print(f"安装成功但无法导入 {module_name}，请确认模块名正确")
                exit(1)
        else:
            print(f"安装成功但无法导入 {module_name}，请确认模块名正确")
            exit(1)

    return module