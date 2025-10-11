"""
Telegram HTTP 客户端
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx

from nekro_agent.core.logger import logger


class TelegramHTTPClient:
    """Telegram HTTP API 客户端"""

    def __init__(self, bot_token: str, proxy_url: Optional[str] = None):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.client: Optional[httpx.AsyncClient] = None
        self.proxy_url = proxy_url

    async def __aenter__(self):
        """异步上下文管理器入口"""
        proxies = None
        if self.proxy_url and self.proxy_url.strip():
            proxies = {
                "all://": self.proxy_url.strip(),
            }
            logger.info(f"Telegram HTTP客户端使用代理: {proxies}")
        
        self.client = httpx.AsyncClient(timeout=30.0, proxies=proxies)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.client:
            await self.client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        if not self.client:
            proxies = None
            if self.proxy_url and self.proxy_url.strip():
                proxies = {
                    "all://": self.proxy_url.strip(),
                }
            
            self.client = httpx.AsyncClient(timeout=30.0, proxies=proxies)

        url = f"{self.base_url}/{endpoint}"

        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                return result
            logger.error(f"Telegram API 错误: {result}")
            return {}
        except Exception as e:
            logger.error(f"Telegram HTTP 请求失败: {e}")
            return {}

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        reply_to_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """发送文本消息"""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        result = await self._request("POST", "sendMessage", json=data)

        if result and result.get("result"):
            return str(result["result"]["message_id"])
        return None

    async def send_photo(
        self,
        chat_id: str,
        photo_data: bytes,
        caption: str = "",
        reply_to_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """发送图片"""
        data = {
            "chat_id": chat_id,
            "caption": caption,
        }

        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        files = {"photo": ("photo.jpg", photo_data, "image/jpeg")}

        result = await self._request("POST", "sendPhoto", data=data, files=files)

        if result and result.get("result"):
            return str(result["result"]["message_id"])
        return None

    async def send_document(
        self,
        chat_id: str,
        document_data: bytes,
        filename: str,
        caption: str = "",
        reply_to_message_id: Optional[str] = None,
    ) -> Optional[str]:
        """发送文档"""
        data = {
            "chat_id": chat_id,
            "caption": caption,
        }

        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        files = {"document": (filename, document_data, "application/octet-stream")}

        result = await self._request("POST", "sendDocument", data=data, files=files)

        if result and result.get("result"):
            return str(result["result"]["message_id"])
        return None

    async def get_me(self) -> Dict[str, Any]:
        """获取机器人信息"""
        result = await self._request("GET", "getMe")
        return result.get("result", {})

    async def get_chat(self, chat_id: str) -> Dict[str, Any]:
        """获取聊天信息"""
        result = await self._request("GET", "getChat", params={"chat_id": chat_id})
        return result.get("result", {})

    async def get_chat_member(self, chat_id: str, user_id: str) -> Dict[str, Any]:
        """获取聊天成员信息"""
        result = await self._request(
            "GET",
            "getChatMember",
            params={"chat_id": chat_id, "user_id": user_id},
        )
        return result.get("result", {})
