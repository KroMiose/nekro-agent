"""Email 适配器账户管理路由的鉴权约束测试。

账户管理接口会读写邮箱凭据、OAuth token 并触发收信/取原始邮件，
必须整体处于登录态之后，禁止出现未鉴权的路由。
"""

from nekro_agent.adapters.email.routers import router
from nekro_agent.services.user.deps import get_current_active_user


def test_all_email_adapter_routes_require_active_user_dependency() -> None:
    routes = [route for route in router.routes if hasattr(route, "dependant")]

    assert routes
    for route in routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_current_active_user in dependency_calls, f"路由 {route.path} 缺少登录态依赖"


def test_email_adapter_router_declares_router_level_auth() -> None:
    """鉴权声明在 router 级别，避免新增路由时漏加依赖。"""
    router_dependency_calls = {dependency.dependency for dependency in router.dependencies}

    assert get_current_active_user in router_dependency_calls
