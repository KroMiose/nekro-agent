"""
Telegram Bot API (HTTP) 客户端实现
只需 BOT_TOKEN，无需 API_ID/API_HASH。
"""
import time
import httpx
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_message import ChatMessageSegment, ChatMessageSegmentType, ChatType
from nekro_agent.adapters.interface.schemas.platform import PlatformMessage, PlatformUser, PlatformChannel, PlatformMessageExt

class TelegramBotAPIClient:
    def __init__(self, token: str, polling_timeout: int = 30, proxy_url: str = ""):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.polling_timeout = polling_timeout
        self.offset = 0
        self.running = False
        self._bot_username = None
        self.proxy_url = proxy_url

    async def start(self, on_message):
        """启动长轮询，收到消息时回调 on_message(platform_channel, platform_user, platform_message)"""
        self.running = True
        client_args = {}
        if self.proxy_url:
            client_args["proxies"] = self.proxy_url

        import asyncio

        while self.running:
            try:
                async with httpx.AsyncClient(**client_args) as client:
                    if not self._bot_username:
                        try:
                            resp = await client.get(f"{self.base_url}/getMe", timeout=10)
                            data = resp.json()
                            if data.get("ok"):
                                self._bot_username = data["result"].get("username")
                                logger.info(f"Telegram Bot @{self._bot_username} 连接成功。")
                            else:
                                logger.warning(f"获取 Bot 用户名失败: {data}")
                        except Exception as e:
                            logger.warning(f"获取 Bot 用户名失败，可能是代理或网络问题: {e}")
                            await asyncio.sleep(15)
                            continue

                    while self.running:
                        try:
                            resp = await client.get(
                                f"{self.base_url}/getUpdates",
                                params={"timeout": self.polling_timeout, "offset": self.offset + 1, "allowed_updates": ["message"]},
                                timeout=self.polling_timeout + 10
                            )
                            data = resp.json()
                            if data.get("ok"):
                                for update in data["result"]:
                                    self.offset = update["update_id"]
                                    message = update.get("message")
                                    if not message:
                                        continue

                                    chat = message["chat"]
                                    chat_id = str(chat["id"])
                                    chat_type = ChatType.PRIVATE if chat["type"] == "private" else ChatType.GROUP
                                    platform_channel = PlatformChannel(
                                        channel_id=chat_id,
                                        channel_name=chat.get("title", chat.get("username", chat_id)),
                                        channel_type=chat_type,
                                        channel_avatar=""
                                    )

                                    from_user = message.get("from", {})
                                    platform_user = PlatformUser(
                                        platform_name="telegram",
                                        user_id=str(from_user.get("id", "unknown")),
                                        user_name=from_user.get("first_name", "unknown"),
                                        user_avatar=""
                                    )

                                    content_text = message.get("text", message.get("caption", ""))
                                    segments = []
                                    if content_text:
                                        segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=content_text))
                                    
                                    if message.get("photo"):
                                        # TODO: 实现文件下载逻辑
                                        # file_path = await self.download_file(photo["file_id"])
                                        # if file_path:
                                        #     segments.append(ChatMessageSegmentImage(file_path=file_path))
                                        pass

                                    is_tome = False
                                    if self._bot_username and f"@{self._bot_username}" in content_text:
                                        is_tome = True

                                    platform_message = PlatformMessage(
                                        message_id=str(message.get("message_id")),
                                        sender_id=str(from_user.get("id", "unknown")),
                                        sender_name=from_user.get("first_name", "unknown"),
                                        sender_nickname=from_user.get("username", ""),
                                        sender_avatar="",
                                        content_data=segments,
                                        content_text=content_text,
                                        is_tome=is_tome,
                                        timestamp=int(message.get("date", time.time())),
                                        is_self=False,
                                        ext_data=PlatformMessageExt()
                                    )
                                    await on_message(platform_channel, platform_user, platform_message)
                            else:
                                logger.error(f"Bot API 轮询响应错误: {data}")
                                if "Unauthorized" in str(data):
                                    logger.error("BOT_TOKEN 无效，请检查配置。适配器将停止。")
                                    self.running = False
                                    break
                                await asyncio.sleep(10)
                        except httpx.ReadTimeout:
                            logger.debug("Bot API 轮询超时，正常现象，继续下一次轮询。")
                        except Exception as e:
                            logger.error(f"Bot API 轮询异常: {e}", exc_info=True)
                            await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Bot API 客户端启动或连接失败: {e}")
                await asyncio.sleep(15)

    async def stop(self):
        self.running = False

    async def send_message(self, chat_id: str, text: str = "", files=None) -> bool:
        client_args = {}
        if self.proxy_url:
            client_args["proxies"] = self.proxy_url
        async with httpx.AsyncClient(**client_args) as client:
            try:
                # TODO: 支持文件发送
                resp = await client.post(f"{self.base_url}/sendMessage", json={"chat_id": chat_id, "text": text})
                data = resp.json()
                return data.get("ok", False)
            except Exception as e:
                logger.error(f"Bot API 发送消息失败: {e}")
                return False
