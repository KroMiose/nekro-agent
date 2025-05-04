import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import magic

from nekro_agent.core import config, logger
from nekro_agent.core.bot import get_bot
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
    convert_agent_message_to_prompt,
)
from nekro_agent.schemas.chat_message import ChatMessage, ChatType
from nekro_agent.tools.common_util import (
    check_content_trigger,
    check_forbidden_message,
    copy_to_upload_dir,
    random_chat_check,
)


class MessageService:
    """消息服务类，处理所有类型的消息推送"""

    def __init__(self):
        # 全局状态追踪
        self.running_tasks: Dict[str, asyncio.Task] = {}  # 记录每个会话正在执行的agent任务
        self.debounce_timers: Dict[str, float] = {}  # 记录每个会话的防抖计时器
        self.pending_messages: Dict[str, ChatMessage] = {}  # 记录每个会话待处理的最新消息

    async def _message_validation_check(self, message: ChatMessage) -> bool:
        """消息校验"""
        plaint_text = message.content_text.strip().replace(" ", "").lower()
        is_fake_message = False

        # 检查伪造消息
        if re.match(r"<.{4,12}\|messageseparator>", plaint_text):
            is_fake_message = True
        if re.match(r"<.{4,12}\|messageseperator>", plaint_text):
            is_fake_message = True

        if "message" in plaint_text and "(qq:" in plaint_text:
            is_fake_message = True
        if "from_qq:" in plaint_text:  # noqa: SIM103
            is_fake_message = True

        if is_fake_message:
            logger.warning(f"检测到伪造消息: {message.content_text} | 跳过本次处理...")
            return False

        return True

    async def schedule_agent_task(self, chat_key: Optional[str] = None, message: Optional[ChatMessage] = None):
        """调度 agent 任务，实现防抖和任务控制"""
        if not message:
            if not chat_key:
                logger.error("调度 Agent 执行失败，目标 chat_key 为空")
                return
            message = ChatMessage.create_empty(chat_key)
        chat_key = message.chat_key

        current_time = time.time()

        # 更新待处理消息和防抖计时器
        self.pending_messages[chat_key] = message
        self.debounce_timers[chat_key] = current_time

        # 如果已有正在执行的任务，直接返回
        if chat_key in self.running_tasks and not self.running_tasks[chat_key].done():
            return

        # 创建防抖任务
        asyncio.create_task(self._debounce_task(chat_key, current_time))

    async def _debounce_task(self, chat_key: str, start_time: float):
        """防抖任务处理

        Args:
            chat_key (str): 会话标识
            start_time (float): 任务开始时间
        """
        # 等待防抖时间
        await asyncio.sleep(config.AI_DEBOUNCE_WAIT_SECONDS)

        # 检查是否在防抖期间有新消息
        if start_time != self.debounce_timers[chat_key]:
            return

        # 获取最终要处理的消息
        final_message = self.pending_messages.pop(chat_key, None)
        if not final_message:
            return

        # 创建新的agent任务
        task = asyncio.create_task(
            self._run_chat_agent_task(chat_key=chat_key, message=final_message if not final_message.is_empty() else None),
        )
        self.running_tasks[chat_key] = task

    async def _run_chat_agent_task(self, chat_key: str, message: Optional[ChatMessage] = None):
        """执行agent任务"""
        from nekro_agent.services.agent.run_agent import run_agent

        if message and config.SESSION_PROCESSING_WITH_EMOJI and message.message_id:
            try:
                await get_bot().call_api("set_msg_emoji_like", message_id=int(message.message_id), emoji_id="212")
            except Exception as e:
                logger.error(f"设置消息emoji失败: {e} | 如果协议端不支持该功能，请关闭配置 `SESSION_PROCESSING_WITH_EMOJI`")

        try:
            logger.info(f"Message From {chat_key} is ToMe, Running Chat Agent...")
            for _i in range(3):
                try:
                    await run_agent(chat_key=chat_key, chat_message=message)
                except Exception as e:
                    logger.exception(f"执行失败: {e}")
                else:
                    break
            else:
                logger.error("Failed to Run Chat Agent.")
        finally:
            # 清理任务状态
            if chat_key in self.running_tasks:
                del self.running_tasks[chat_key]

            final_message = self.pending_messages.pop(chat_key, None)
            self.debounce_timers.pop(chat_key, None)

            if config.SESSION_PROCESSING_WITH_EMOJI and message and message.message_id:
                try:
                    await get_bot().call_api(
                        "set_msg_emoji_like",
                        message_id=int(message.message_id),
                        emoji_id="212",
                        set="false",
                    )
                except Exception as e:
                    logger.error(f"设置消息emoji失败: {e} | 如果协议端不支持该功能，请关闭配置 `SESSION_PROCESSING_WITH_EMOJI`")

            # 如果有待处理消息，创建新的任务处理最后一条消息
            if final_message:
                new_task = asyncio.create_task(self._run_chat_agent_task(chat_key=chat_key, message=final_message))
                self.running_tasks[chat_key] = new_task

    async def push_human_message(
        self,
        message: ChatMessage,
        user: Optional[DBUser] = None,
        trigger_agent: bool = False,
        db_chat_channel: Optional[DBChatChannel] = None,
    ):
        """推送人类消息"""
        logger.info(f'Message Received: "{message.content_text}" From {message.sender_real_nickname}')
        db_chat_channel = db_chat_channel or await DBChatChannel.get_channel(chat_key=message.chat_key)
        preset = await db_chat_channel.get_preset()

        if not await self._message_validation_check(message):
            logger.warning("消息校验失败，跳过本次处理...")
            return

        content_data = [o.model_dump() for o in message.content_data]
        current_time: float = time.time()

        if check_forbidden_message(message.content_text):
            logger.info(f"消息 {message.content_text} 被禁止，跳过本次处理...")
            return

        # 添加聊天记录
        await DBChatMessage.create(
            message_id=message.message_id,
            sender_id=message.sender_id,
            sender_bind_qq=message.sender_bind_qq,
            sender_real_nickname=message.sender_real_nickname,
            sender_nickname=message.sender_nickname,
            is_tome=message.is_tome,
            is_recalled=message.is_recalled,
            chat_key=message.chat_key,
            chat_type=message.chat_type,
            content_text=message.content_text,
            content_data=json.dumps(content_data, ensure_ascii=False),
            raw_cq_code=message.raw_cq_code,
            ext_data=message.ext_data,
            send_timestamp=int(current_time),  # 使用处理后的时间戳
        )

        should_ignore = (user and user.is_prevent_trigger) or (user and not user.is_active)

        # 检查是否需要触发回复
        should_trigger = (
            trigger_agent
            or preset.name in message.content_text
            or message.is_tome
            or random_chat_check()
            or check_content_trigger(message.content_text)
        )

        if not should_ignore and should_trigger:
            if not db_chat_channel.is_active:
                logger.info(f"聊天频道 {message.chat_key} 已被禁用，跳过本次处理...")
                return

            await self.schedule_agent_task(message=message)

    async def push_bot_message(
        self,
        chat_key: str,
        agent_messages: Union[str, List[AgentMessageSegment]],
        db_chat_channel: Optional[DBChatChannel] = None,
    ):
        """推送机器人消息"""
        logger.info(f"Pushing Bot Message To Chat {chat_key}")
        db_chat_channel = db_chat_channel or await DBChatChannel.get_channel(chat_key=chat_key)
        preset = await db_chat_channel.get_preset()

        if isinstance(agent_messages, str):
            agent_messages = [AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=agent_messages)]

        send_timestamp = int(time.time())
        content_text = convert_agent_message_to_prompt(agent_messages)

        content_data = []
        for msg in agent_messages:
            if msg.type == AgentMessageSegmentType.FILE:
                # 使用magic库检测文件MIME类型
                file_path = Path(msg.content)
                if file_path.exists():
                    mime_type = magic.from_buffer(file_path.read_bytes(), mime=True)
                    if mime_type.startswith("image/"):
                        # 复制文件到uploads目录
                        local_path, file_name = await copy_to_upload_dir(
                            str(file_path),
                            file_name=file_path.name,
                            from_chat_key=chat_key,
                        )

                        content_data.append(
                            {
                                "type": "image",
                                "text": "",
                                "file_name": file_name,
                                "local_path": local_path,  # 使用复制后的路径
                                "remote_url": "",
                            },
                        )
            elif msg.type == AgentMessageSegmentType.TEXT:
                content_data.append(
                    {
                        "type": "text",
                        "text": msg.content,
                    },
                )

        await DBChatMessage.create(
            message_id="",
            sender_id=-1,
            sender_bind_qq=config.BOT_QQ or "0",
            sender_real_nickname=preset.name,
            sender_nickname=preset.name,
            is_tome=0,
            is_recalled=False,
            chat_key=chat_key,
            chat_type=ChatType.from_chat_key(chat_key).value,
            content_text=content_text,
            content_data=json.dumps(content_data, ensure_ascii=False),
            raw_cq_code="",
            ext_data={},
            send_timestamp=send_timestamp,
        )

    async def push_system_message(
        self,
        chat_key: str,
        agent_messages: Union[str, List[AgentMessageSegment]],
        trigger_agent: bool = False,
        db_chat_channel: Optional[DBChatChannel] = None,
    ):
        """推送系统消息"""
        logger.info(f"Pushing System Message To Chat {chat_key}")
        db_chat_channel = db_chat_channel or await DBChatChannel.get_channel(chat_key=chat_key)

        if isinstance(agent_messages, str):
            agent_messages = [AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=agent_messages)]

        send_timestamp = int(time.time())
        content_text = convert_agent_message_to_prompt(agent_messages)

        await DBChatMessage.create(
            message_id="",
            sender_id=-1,
            sender_bind_qq="0",
            sender_real_nickname="SYSTEM",
            sender_nickname="SYSTEM",
            is_tome=0,
            is_recalled=False,
            chat_key=chat_key,
            chat_type=ChatType.from_chat_key(chat_key).value,
            content_text=content_text,
            content_data=json.dumps([], ensure_ascii=False),
            raw_cq_code="",
            ext_data={},
            send_timestamp=send_timestamp,
        )

        if trigger_agent:
            if not db_chat_channel.is_active:
                logger.info(f"聊天频道 {chat_key} 已被禁用，跳过本次处理...")
                return
            await self.schedule_agent_task(chat_key=chat_key)


# 全局消息服务实例
message_service = MessageService()
