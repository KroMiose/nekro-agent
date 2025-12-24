import os
import re
import time
from pathlib import Path
from typing import Tuple

import requests

# PROXY = "http://127.0.0.1:7890"
PROXY = None


def get_current_pkg() -> Tuple[str, str]:
    """获取当前包的名称和版本号"""
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    pkg_name, pkg_version = (
        re.findall(r'name ?= ?"(.*)"', pyproject_text)[0],
        re.findall(r'version ?= ?"(.*)"', pyproject_text)[0],
    )

    if pkg_name and pkg_version:
        return pkg_name, pkg_version
    raise Exception("No valid pyproject.toml found.")


def fetch_pkg_latest_version(pkg_name: str, proxy=PROXY) -> str:
    """在线获取包最新版本号"""
    try:
        res = requests.get(
            f"https://pypi.org/pypi/{pkg_name}/json",
            proxies={"http": proxy, "https": proxy} if proxy else None,
        ).json()
    except Exception:
        return ""

    try:
        if res["info"]["version"]:
            return res["info"]["version"]
    except Exception:
        pass
    try:
        if res["message"] == "Not Found":
            return "-"
    except Exception:
        pass
    return ""


def install_package():
    """安装包与依赖"""
    pkg_name, pkg_version = get_current_pkg()
    print("Installing package...")
    if Path("uv.lock").exists():
        # 更新 uv.lock
        os.system("uv lock")
    # 安装依赖
    os.system("uv sync")

    print("Package install success!\n")


def test_package():
    """测试包"""
    install_package()

    pkg_name, pkg_version = get_current_pkg()
    # 执行测试
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    if "test" in pyproject:
        print("Running tests...")
        try:
            assert os.system("uv run poe test") == 0
        except AssertionError:
            print("Package test failed.")
            exit(1)
    else:
        print("No tests found. Skipping...")

    print("Package test passed.\n")


def build_package():
    """构建包"""
    install_package()

    pkg_name, pkg_version = get_current_pkg()
    # 删除旧的构建文件
    for file in Path("dist").glob("*"):
        file.unlink()
    # 执行构建
    try:
        assert os.system("uv build") == 0
    except AssertionError:
        print("Package build failed.")
        exit(1)

    print("Package build success!\n")


def publish_package():
    """发布包"""
    build_package()

    pkg_name, pkg_version = get_current_pkg()
    # 检查是否已经发布
    latest_version = fetch_pkg_latest_version(pkg_name)
    if latest_version == pkg_version:
        print("Package is already published.")
        return
    # 执行发布
    try:
        assert os.system("uv publish") == 0
    except AssertionError:
        print("Package publish failed.")
        exit(1)

    print("Package publish success!\n")
