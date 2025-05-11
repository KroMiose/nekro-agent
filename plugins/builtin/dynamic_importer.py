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
