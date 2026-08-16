import hmac
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from nekro_agent.api.schemas import AgentCtx, WebhookRequest
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.errors import NotFoundError, UnauthorizedError
from nekro_agent.services.plugin.collector import plugin_collector

logger = get_sub_logger("webhook")
router = APIRouter(prefix="/webhook", tags=["Webhook"])


class WebhookResponse(BaseModel):
    """WebhookResponse"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


def _verify_webhook_token(request: Request) -> None:
    """校验 Webhook 调用令牌

    设置 WEBHOOK_SECRET_KEY 后,调用方必须携带匹配的
    X-Webhook-Token 请求头(或 ?webhook_token= 查询参数)。
    未设置时保持旧行为(不校验);启动阶段的 mount_api_routes
    会输出一次性提醒日志。
    """
    secret = OsEnv.WEBHOOK_SECRET_KEY
    if not secret:
        return
    provided = request.headers.get("X-Webhook-Token") or request.query_params.get("webhook_token", "")
    # 常时比较,避免逐字节比较的时序侧信道泄露密钥
    if not hmac.compare_digest(provided.encode("utf-8"), secret.encode("utf-8")):
        logger.warning("Webhook 令牌校验失败")
        raise UnauthorizedError


@router.post("/{endpoint}", summary="Webhook 调用")
async def webhook_handler(
    endpoint: str,
    request: Request,
) -> WebhookResponse:
    """处理 Webhook 请求

    Args:
        endpoint: Webhook 端点
        request: 请求对象
        chat_key: 对话ID，可选，有助于消息推送

    Returns:
        WebhookResponse: Webhook 响应
    """
    _verify_webhook_token(request)
    logger.info(f"收到 Webhook 请求: {endpoint}")

    # 获取所有处理这个endpoint的webhook方法
    webhook_methods = plugin_collector.get_webhook_methods_by_endpoint(endpoint)
    if not webhook_methods:
        logger.warning(f"未找到处理 {endpoint} 的 Webhook 方法")
        raise NotFoundError(resource="Webhook 处理器")

    results = []
    errors = []

    # 获取请求数据
    headers = dict(request.headers.items())
    content_type = headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes.decode())
        except json.JSONDecodeError:
            body = {"raw_content": body_bytes.decode()}

    # 创建上下文
    ctx: AgentCtx = await AgentCtx.create_by_webhook(
        webhook_request=WebhookRequest(headers=headers, body=body),
    )

    # 调用所有匹配的webhook方法
    for plugin_key, method in webhook_methods:
        logger.info(f"调用插件 {plugin_key} 的 {endpoint} 方法")
        await method(ctx)

    return WebhookResponse(
        success=len(errors) == 0,
        message=f"Webhook 处理完成，成功: {len(results)}，失败: {len(errors)}",
        data={"results": results, "errors": errors},
    )
