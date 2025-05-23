import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel

from nekro_agent.api.schemas import AgentCtx, WebhookRequest
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.http_exception import forbidden_exception, not_found_exception
from nekro_agent.services.plugin.collector import plugin_collector

router = APIRouter(prefix="/webhook", tags=["Webhook"])


class WebhookResponse(BaseModel):
    """Webhook响应"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


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
    logger.info(f"收到 Webhook 请求: {endpoint}")

    # 获取所有处理这个endpoint的webhook方法
    webhook_methods = plugin_collector.get_webhook_methods_by_endpoint(endpoint)
    if not webhook_methods:
        logger.warning(f"未找到处理 {endpoint} 的 Webhook 方法")
        raise not_found_exception

    results = []
    errors = []

    try:
        # 获取请求数据
        headers = dict(request.headers.items())
        content_type = headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
        else:
            body_bytes = await request.body()
            try:
                body = json.loads(body_bytes.decode())
            except:
                body = {"raw_content": body_bytes.decode()}

        # 创建上下文
        ctx: AgentCtx = await AgentCtx.create_by_webhook(
            webhook_request=WebhookRequest(headers=headers, body=body),
        )

        # 调用所有匹配的webhook方法
        for plugin_key, method in webhook_methods:
            try:
                logger.info(f"调用插件 {plugin_key} 的 {endpoint} 方法")
                await method(ctx)

            except Exception as e:
                logger.exception(f"插件 {plugin_key} 处理 {endpoint} 失败: {e}")
                errors.append({"plugin_key": plugin_key, "error": str(e)})

        return WebhookResponse(
            success=len(errors) == 0,
            message=f"Webhook 处理完成，成功: {len(results)}，失败: {len(errors)}",
            data={"results": results, "errors": errors},
        )
    except Exception as e:
        logger.exception(f"处理 Webhook 请求失败: {e}")
        return WebhookResponse(
            success=False,
            message=f"处理 Webhook 请求失败: {e!s}",
        )
