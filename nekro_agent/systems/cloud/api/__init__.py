"""Nekro Cloud API 客户端模块"""

from .auth import check_official_repos_starred  # noqa: F401
from .plugin import (  # noqa: F401
    create_plugin,
    delete_plugin,
    get_plugin,
    list_plugins,
    list_user_plugins,
    update_plugin,
)
from .preset import (  # noqa: F401
    create_preset,
    delete_preset,
    get_preset,
    list_presets,
    list_user_presets,
    update_preset,
)
from .telemetry import get_community_stats, send_telemetry_report  # noqa: F401
