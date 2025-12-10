"""
企业微信智能机器人适配器路由模块

实现 URL 验证和消息接收的 webhook 接口
"""

import urllib.parse
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse, Response

from nekro_agent.core.logger import logger

if TYPE_CHECKING:
    from .adapter import WxWorkAdapter

router = APIRouter()

# 全局适配器实例，由 adapter.py 设置
_adapter: Optional["WxWorkAdapter"] = None


def set_adapter(adapter: "WxWorkAdapter") -> None:
    """设置适配器实例"""
    global _adapter
    _adapter = adapter


@router.get("/callback", summary="验证 URL 有效性")
async def verify_url(
    msg_signature: str = Query(..., description="企业微信加密签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
    echostr: str = Query(..., description="加密的随机字符串"),
) -> PlainTextResponse:
    """
    验证 URL 有效性接口（GET 请求）

    企业微信在配置接收消息URL时，会发送一个GET请求到此接口进行验证。
    需要：
    1. 对请求参数进行 URL decode 处理
    2. 验证签名是否正确
    3. 解密 echostr 得到消息内容明文（msg 字段）
    4. 在 1 秒内响应，返回明文内容（不能加引号，不能带 BOM 头，不能带换行符）

    配置路径示例：http://your-domain/adapters/wxwork/callback
    """
    if not _adapter:
        logger.error("企业微信适配器未初始化")
        return PlainTextResponse(content="Adapter not initialized", status_code=500)

    if not _adapter.crypto:
        logger.error("企业微信加密工具未初始化，请检查 Token 和 EncodingAESKey 配置")
        return PlainTextResponse(content="Crypto not initialized", status_code=500)

    try:
        # 对参数进行 URL decode 处理（FastAPI 会自动处理，但为了保险再做一次）
        echostr_decoded = urllib.parse.unquote(echostr)
        msg_signature_decoded = urllib.parse.unquote(msg_signature)
        timestamp_decoded = urllib.parse.unquote(timestamp)
        nonce_decoded = urllib.parse.unquote(nonce)

        # 验证并解密 echostr，得到 msg 字段内容
        decrypted_msg = _adapter.crypto.verify_url(
            msg_signature=msg_signature_decoded,
            timestamp=timestamp_decoded,
            nonce=nonce_decoded,
            echostr=echostr_decoded,
        )

        logger.success(f"企业微信智能机器人 URL 验证成功，解密内容: {decrypted_msg[:100]}")

        # 返回明文消息内容（不加引号，不带换行符）
        return PlainTextResponse(content=decrypted_msg.strip(), status_code=200)

    except ValueError as e:
        logger.error(f"企业微信 URL 验证失败: {e}")
        return PlainTextResponse(content="Verification failed", status_code=403)
    except Exception as e:
        logger.exception(f"企业微信 URL 验证异常: {e}")
        return PlainTextResponse(content="Internal error", status_code=500)


@router.post("/callback", summary="接收企业微信智能机器人消息")
async def receive_message(
    request: Request,
    msg_signature: str = Query(..., description="企业微信加密签名"),
    timestamp: str = Query(..., description="时间戳"),
    nonce: str = Query(..., description="随机数"),
) -> Response:
    """
    接收企业微信智能机器人消息接口（POST 请求）

    企业微信会将用户消息通过 POST 请求推送到此接口。
    消息格式为 JSON: {"encrypt": "msg_encrypt"}

    需要：
    1. 验证签名是否正确
    2. 解密 encrypt 字段得到消息明文 JSON
    3. 处理消息内容
    4. 可选：直接回复消息或返回空包

    配置路径示例：http://your-domain/adapters/wxwork/callback
    """
    if not _adapter:
        logger.error("企业微信适配器未初始化")
        return Response(content="", status_code=200)  # 返回空包避免重复推送

    if not _adapter.crypto:
        logger.error("企业微信加密工具未初始化，请检查配置")
        return Response(content="", status_code=200)

    try:
        # 1. 读取请求体
        body = await request.body()
        body_text = body.decode("utf-8")

        logger.debug(f"收到企业微信消息，签名: {msg_signature}, 时间戳: {timestamp}, nonce: {nonce}")
        logger.debug(f"请求体长度: {len(body_text)}, 前200字符: {body_text[:200]}")

        # 2. 解析请求体提取 encrypt 字段（兼容 JSON 和 XML 两种格式）
        import json
        import xml.etree.ElementTree as ET

        encrypt_msg = None

        # 尝试解析 JSON 格式
        if body_text.strip().startswith("{"):
            try:
                request_data = json.loads(body_text)
                encrypt_msg = request_data.get("encrypt")
                logger.debug("成功解析 JSON 格式消息体")
            except json.JSONDecodeError:
                logger.warning("JSON 格式解析失败，尝试 XML 格式")

        # 尝试解析 XML 格式
        if not encrypt_msg and body_text.strip().startswith("<"):
            try:
                root = ET.fromstring(body_text)
                encrypt_element = root.find("Encrypt")
                if encrypt_element is not None and encrypt_element.text:
                    encrypt_msg = encrypt_element.text
                    logger.debug("成功解析 XML 格式消息体")
            except ET.ParseError as e:
                logger.error(f"XML 格式解析失败: {e}")

        if not encrypt_msg:
            logger.error(f"无法从请求体中提取 encrypt 字段，请求体: {body_text[:500]}")
            return Response(content="", status_code=200)

        # 3. 解密消息
        message_data = _adapter.crypto.decrypt_message(
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce,
            encrypt_data=encrypt_msg,
        )

        logger.info("成功解密企业微信智能机器人消息")
        logger.debug(f"消息内容: {json.dumps(message_data, ensure_ascii=False, indent=2)}")

        # 4. 处理消息（异步，不阻塞响应）
        # TODO: 在后续开发中实现消息处理逻辑
        # asyncio.create_task(_adapter.handle_message(message_data, nonce, timestamp))

        # 5. 返回空包表示接收成功（也可以选择直接回复消息）
        return Response(content="", status_code=200)

    except ValueError as e:
        logger.exception(f"企业微信消息验证失败: {e}")
        return Response(content="", status_code=200)  # 返回空包避免重复推送
    except Exception as e:
        logger.exception(f"处理企业微信消息异常: {e}")
        return Response(content="", status_code=200)  # 返回空包避免重复推送


@router.get("/info", summary="获取企业微信适配器信息")
async def get_adapter_info():
    """获取企业微信智能机器人适配器信息"""
    if not _adapter:
        return {
            "adapter": "wxwork",
            "type": "智能机器人",
            "status": "not_initialized",
            "message": "企业微信适配器未初始化",
        }

    config = _adapter.config
    is_configured = bool(config.TOKEN and config.ENCODING_AES_KEY)

    return {
        "adapter": "wxwork",
        "type": "智能机器人",
        "status": "ready" if is_configured else "not_configured",
        "message": "企业微信智能机器人适配器已准备就绪" if is_configured else "请在配置文件中填写 Token 和 EncodingAESKey",
        "token_configured": bool(config.TOKEN),
        "encoding_aes_key_configured": bool(config.ENCODING_AES_KEY),
    }


@router.get("/health", summary="健康检查")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
