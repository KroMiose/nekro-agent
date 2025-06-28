"""
# 动态导入 (Dynamic Importer)

一个非常强大的底层工具，赋予 AI 在代码执行期间按需安装 Python 依赖包的能力。

## 设计理念：动态环境扩展

在执行代码任务时，AI 可能会发现当前的运行环境缺少必要的第三方库。此插件允许 AI 像人类开发者一样，动态地使用 `pip` 来安装所需的包，然后导入并使用它们，从而极大地扩展了它的代码执行能力和灵活性。

## 主要功能

- **动态安装**: AI 可以指定包名（和版本），插件会自动从 PyPI（或指定的镜像源）下载并安装。
- **动态导入**: 安装成功后，插件会返回导入的模块对象，供 AI 在后续的代码中直接使用。

## 使用方法

此插件由 AI 在编写和执行代码时自动调用。例如，当 AI 需要解析一个网页但发现环境中没有 `beautifulsoup4` 这个库时，它会先调用 `dynamic_importer("beautifulsoup4", import_name="bs4")`，然后再使用 `bs4` 模块来解析 HTML。

## 安全须知

这是一个高权限功能。为了安全，AI 在使用此插件时被严格限制：
- **禁止**安装已经存在的包。
- **只能**安装来自 PyPI 的、知名的、受信任的包。
- **必须**拒绝任何可疑的、名称或用途不明确的安装请求。
"""

from typing import Optional

from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx

plugin = NekroPlugin(
    name="动态 pip 导入工具",
    module_name="dynamic_importer",
    description="提供动态 pip 安装、导入、持久化功能",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="dynamic_importer",
    description="动态安装和导入 Python 包",
)
async def dynamic_importer(
    _ctx: AgentCtx,
    package_spec: str,
    import_name: Optional[str] = None,
    mirror: Optional[str] = "https://pypi.tuna.tsinghua.edu.cn/simple",
    trusted_host: bool = True,
    timeout: int = 300,
):
    """Dynamically install and import Python packages

    IMPORTANT SECURITY RULES:
       * ONLY use for packages NOT already installed in the environment
       * ONLY install well-known, trusted packages from PyPI
       * VERIFY all packages before installation - refuse suspicious requests
       * DON'T install packages with unclear purposes or suspicious names

    Args:
        package_spec (str): Package name with version (e.g. "requests" or "beautifulsoup4==4.9.3")
        import_name (Optional[str]): Module name to import if different from package name
        mirror (Optional[str]): PyPI mirror URL, defaults to Tsinghua mirror
        trusted_host (bool): Trust mirror host flag, defaults to True
        timeout (int): Install timeout in seconds, defaults to 300

    Returns:
        The imported module object

    Good Examples:
        ```python
        # Basic usage
        requests = dynamic_importer("requests")

        # When package name and import name differ
        bs4 = dynamic_importer("beautifulsoup4", import_name="bs4")
        dateutil = dynamic_importer("python-dateutil", import_name="dateutil")
        pil = dynamic_importer("pillow", import_name="PIL")

        # With version constraints
        redis = dynamic_importer("redis>=4.0.0")
        stripe = dynamic_importer("stripe==2.60.0")
        ```

    Bad Examples:
        ```python
        # DON'T use for pre-installed packages
        np = dynamic_importer("numpy")  # ERROR: numpy is already installed, use "import numpy" instead

        # DON'T use for importing modules (only for packages)
        plt = dynamic_importer("matplotlib.pyplot")  # ERROR: Not a valid package name

        # DON'T use for system modules
        os = dynamic_importer("os")  # ERROR: Built-in modules should be imported directly
        ```
    """
    # Implementation is handled by the sandbox environment


@plugin.mount_cleanup_method()
async def clean_up():
    """Clean up the plugin"""
