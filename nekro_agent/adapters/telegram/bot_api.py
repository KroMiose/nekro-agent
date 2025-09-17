"""
Telegram Bot API (HTTP) 客户端实现
只需 BOT_TOKEN，无需 API_ID/API_HASH。
"""
import time
import json
from typing import List, Optional, Tuple

import httpx
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_message import ChatMessageSegment, ChatMessageSegmentType, ChatType
from nekro_agent.adapters.interface.schemas.platform import PlatformMessage, PlatformUser, PlatformChannel, PlatformMessageExt
from .tools import format_telegram_message

class TelegramBotAPIClient:
    def __init__(self, token: str, polling_timeout: int = 30, proxy_url: str = ""):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.polling_timeout = polling_timeout
        self.offset = 0
        self.running = False
        self._bot_username = None
        self._bot_id: Optional[int] = None
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
                                try:
                                    self._bot_id = int(data["result"].get("id"))
                                except Exception:
                                    self._bot_id = None
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
                                params={
                                    "timeout": self.polling_timeout,
                                    "offset": self.offset + 1,
                                    # 监听普通消息与频道消息（需 JSON 字符串）
                                    "allowed_updates": json.dumps(["message", "channel_post"]),
                                },
                                timeout=self.polling_timeout + 10
                            )
                            data = resp.json()
                            if data.get("ok"):
                                for update in data["result"]:
                                    self.offset = update["update_id"]
                                    message = update.get("message") or update.get("channel_post")
                                    if not message:
                                        continue

                                    chat = message["chat"]
                                    raw_chat_id = str(chat["id"])
                                    raw_type = chat.get("type", "")
                                    chat_type = ChatType.PRIVATE if raw_type == "private" else ChatType.GROUP
                                    # OneBot 风格的频道ID：private_<id>/group_<id>
                                    if raw_type == "private":
                                        channel_id_fmt = f"private_{raw_chat_id}"
                                    else:
                                        # group/supergroup/channel 统一按 group 处理
                                        channel_id_fmt = f"group_{raw_chat_id}"
                                    platform_channel = PlatformChannel(
                                        channel_id=channel_id_fmt,
                                        channel_name=chat.get("title", chat.get("username", raw_chat_id)),
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

                                    # 私聊默认触发自动响应；群/频道需@或命中其他触发规则
                                    is_tome = (raw_type == "private")
                                    if (not is_tome) and content_text and self._bot_username and f"@{self._bot_username}" in content_text:
                                        is_tome = True

                                    # 引用消息
                                    reply_to = message.get("reply_to_message")
                                    ref_msg_id = ""
                                    if reply_to and reply_to.get("message_id") is not None:
                                        ref_msg_id = str(reply_to.get("message_id"))

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
                                        is_self=(self._bot_id is not None and from_user.get("id") == self._bot_id),
                                        ext_data=PlatformMessageExt(ref_chat_key=platform_channel.channel_id, ref_msg_id=ref_msg_id),
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

    async def send_message(
        self,
        chat_id: str,
        text: str = "",
    files: Optional[List[Tuple[str, str]]] = None,
    reply_to: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        client_args = {}
        if self.proxy_url:
            client_args["proxies"] = self.proxy_url
        async with httpx.AsyncClient(**client_args) as client:
            try:
                last_message_id: Optional[str] = None
                overall_success = True

                # 优先发送文件（OneBot 风格常见做法）
                if files:
                    first_reply = reply_to
                    for file_path, kind in files:
                        endpoint = "sendPhoto" if kind == "image" else "sendDocument"
                        field_name = "photo" if kind == "image" else "document"
                        data = {"chat_id": chat_id}
                        if first_reply:
                            # 统一为字符串，避免类型检查告警
                            try:
                                data["reply_to_message_id"] = str(int(first_reply))
                            except Exception:
                                data["reply_to_message_id"] = str(first_reply)
                            first_reply = None  # 只在首条使用引用

                        files_param = None
                        try:
                            f = open(file_path, "rb")
                        except Exception as e:
                            logger.error(f"打开文件失败: {file_path}, {e}")
                            overall_success = False
                            continue
                        files_param = {field_name: (file_path.split("/")[-1], f)}

                        try:
                            resp = await client.post(f"{self.base_url}/{endpoint}", data=data, files=files_param)
                        finally:
                            try:
                                f.close()
                            except Exception:
                                pass
                        resp_data = resp.json()
                        if not resp_data.get("ok"):
                            overall_success = False
                            logger.error(f"Bot API 发送文件失败: {resp_data}")
                        else:
                            last_message_id = str(resp_data.get("result", {}).get("message_id"))

                # 发送文本（自动切分长文本）
                if text and text.strip():
                    chunks = format_telegram_message(text)
                    first_reply = reply_to if not files else None  # 若已用在文件上，则不再使用
                    for chunk in chunks:
                        payload = {"chat_id": chat_id, "text": chunk}
                        # 仅当存在我们构造的 HTML mention 片段时才启用 HTML 解析，避免尖括号引起 400
                        if "tg://user?id=" in chunk or ("<a href=" in chunk and ">" in chunk):
                            payload["parse_mode"] = "HTML"
                        if first_reply:
                            try:
                                payload["reply_to_message_id"] = str(int(first_reply))
                            except Exception:
                                payload["reply_to_message_id"] = str(first_reply)
                            first_reply = None
                        resp = await client.post(f"{self.base_url}/sendMessage", json=payload)
                        resp_data = resp.json()
                        if not resp_data.get("ok"):
                            overall_success = False
                            logger.error(f"Bot API 发送文本失败: {resp_data}")
                        else:
                            last_message_id = str(resp_data.get("result", {}).get("message_id"))

                return overall_success, last_message_id
            except Exception as e:
                logger.error(f"Bot API 发送消息失败: {e}")
                return False, None
