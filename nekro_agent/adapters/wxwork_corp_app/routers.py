import asyncio
import urllib.parse
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse, Response

from nekro_agent.core.logger import get_sub_logger


logger = get_sub_logger("adapter.wxwork_corp_app")

if TYPE_CHECKING:
    from .adapter import WxWorkCorpAppAdapter


router = APIRouter()
_adapter: Optional["WxWorkCorpAppAdapter"] = None


def set_adapter(adapter: "WxWorkCorpAppAdapter") -> None:
    global _adapter
    _adapter = adapter


@router.get("/callback", summary="企业微信自建应用 URL 验证")
async def verify_url(
    msg_signature: str = Query(..., description="企业微信加密签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
    echostr: str = Query(..., description="加密的随机字符串"),
) -> PlainTextResponse:
    if not _adapter:
        return PlainTextResponse(content="Adapter not initialized", status_code=500)

    if not _adapter.crypto:
        return PlainTextResponse(content="Crypto not initialized", status_code=500)

    try:
        decrypted_msg = _adapter.crypto.verify_url(
            msg_signature=urllib.parse.unquote(msg_signature),
            timestamp=urllib.parse.unquote(timestamp),
            nonce=urllib.parse.unquote(nonce),
            echostr=urllib.parse.unquote(echostr),
        )
        logger.info("企业微信自建应用 URL 验证成功")
        return PlainTextResponse(content=decrypted_msg.strip(), status_code=200)
    except Exception as e:
        logger.exception(f"企业微信自建应用 URL 验证失败: {e}")
        return PlainTextResponse(content="Verification failed", status_code=403)


@router.post("/callback", summary="接收企业微信自建应用消息")
async def receive_message(
    request: Request,
    msg_signature: str = Query(..., description="企业微信加密签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
) -> Response:
    if not _adapter:
        return PlainTextResponse(content="success", status_code=200)

    if not _adapter.crypto:
        logger.error("企业微信自建应用加密工具未初始化")
        return PlainTextResponse(content="success", status_code=200)

    try:
        body_text = (await request.body()).decode("utf-8")
        decrypted_xml = _adapter.crypto.decrypt_message(
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce,
            body_text=body_text,
        )

        asyncio.create_task(
            _adapter.handle_corp_app_callback(
                decrypted_xml=decrypted_xml,
                raw_body=body_text,
                msg_signature=msg_signature,
                timestamp=timestamp,
                nonce=nonce,
            )
        )
    except Exception as e:
        logger.exception(f"处理企业微信自建应用回调失败: {e}")

    return PlainTextResponse(content="success", status_code=200)


@router.get("/health", summary="健康检查")
async def health_check():
    return {"status": "healthy"}
