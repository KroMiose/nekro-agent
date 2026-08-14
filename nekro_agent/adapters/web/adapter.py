from pathlib import Path
from typing import TYPE_CHECKING, List, Type
from uuid import uuid4

from fastapi import APIRouter

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.agent_message import AgentMessageSegment, AgentMessageSegmentType
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.tools.common_util import download_file
from nekro_agent.tools.path_convertor import is_url_path

from .config import WebAdapterConfig

if TYPE_CHECKING:
    from nekro_agent.services.command.schemas import CommandResponse

logger = get_sub_logger("adapter.web")


class WebAdapter(BaseAdapter[WebAdapterConfig]):
    """官方 WebUI 网页聊天适配器。"""

    def __init__(self, config_cls: Type[WebAdapterConfig] = WebAdapterConfig):
        super().__init__(config_cls)

    @property
    def key(self) -> str:
        return "web"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="Web Chat",
            description="Nekro Agent WebUI 内置网页聊天适配器，用于本地测试与功能验证。",
            version="1.0.0",
            author="NekroAI",
            homepage="https://github.com/KroMiose/nekro-agent",
            tags=["web", "webui", "chat", "test"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "网页会话: `web-session_<uuid>`",
        ]

    @property
    def record_command_input(self) -> bool:
        return True

    def get_adapter_router(self) -> APIRouter:
        from .routers import router, set_adapter

        set_adapter(self)
        return router

    async def init(self) -> None:
        logger.info("Web Adapter 已初始化")

    async def cleanup(self) -> None:
        logger.info("Web Adapter 已清理")

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        if not request.segments:
            return PlatformSendResponse(success=False, error_message="消息内容为空")

        message_id = f"webout_{uuid4().hex}"
        agent_messages = await self._build_agent_messages_from_platform_segments(request)
        if not agent_messages:
            return PlatformSendResponse(success=False, error_message="消息内容为空")

        response = PlatformSendResponse(success=True, message_id=message_id, recorded=True)
        from nekro_agent.services.message_service import message_service

        await message_service.push_bot_message(
            request.chat_key,
            agent_messages,
            response,
            ref_msg_id=request.ref_msg_id,
            normalize_at_markup=False,
        )

        return response

    async def _build_agent_messages_from_platform_segments(
        self,
        request: PlatformSendRequest,
    ) -> List[AgentMessageSegment]:
        agent_messages: List[AgentMessageSegment] = []
        for segment in request.segments:
            if segment.type == PlatformSendSegmentType.TEXT:
                if segment.content.strip():
                    agent_messages.append(AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=segment.content))
            elif segment.type == PlatformSendSegmentType.AT:
                text = self._format_at_segment(segment.content, segment.at_info.nickname if segment.at_info else None)
                if text:
                    agent_messages.append(AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=text))
            elif segment.type in {PlatformSendSegmentType.IMAGE, PlatformSendSegmentType.FILE}:
                file_path = await self._resolve_send_file_path(request.chat_key, segment.file_path or segment.content)
                if not file_path:
                    logger.warning(f"Web Adapter 收到无效媒体片段，已跳过: type={segment.type}, file_path={segment.file_path}")
                    continue
                message_type = (
                    AgentMessageSegmentType.IMAGE
                    if segment.type == PlatformSendSegmentType.IMAGE
                    else AgentMessageSegmentType.FILE
                )
                agent_messages.append(AgentMessageSegment(type=message_type, content=file_path))
            else:
                logger.info(f"Web Adapter 收到暂不支持的发送片段，已跳过: {segment.type}")
        return agent_messages

    @staticmethod
    def _format_at_segment(content: str, nickname: str | None) -> str:
        target = (nickname or content).strip()
        return f"@{target}" if target else ""

    @staticmethod
    async def _resolve_send_file_path(chat_key: str, file_path: str) -> str:
        if not file_path:
            return ""
        if is_url_path(file_path):
            local_path, _file_name = await download_file(file_path, from_chat_key=chat_key)
            return local_path
        return file_path if Path(file_path).exists() else ""

    async def execute_command(
        self,
        chat_key: str,
        user_id: str,
        username: str,
        command_name: str,
        raw_args: str,
        is_super_user: bool = False,
        is_advanced_user: bool = False,
    ) -> "List[CommandResponse] | None":
        from nekro_agent.services.command.schemas import CommandResponseStatus

        web_admin_superuser = self.config.WEBUI_ADMIN_AS_COMMAND_SUPERUSER and user_id.startswith("admin_")
        effective_is_super_user = is_super_user or web_admin_superuser
        effective_is_advanced_user = is_advanced_user or web_admin_superuser

        responses = await super().execute_command(
            chat_key=chat_key,
            user_id=user_id,
            username=username,
            command_name=command_name,
            raw_args=raw_args,
            is_super_user=effective_is_super_user,
            is_advanced_user=effective_is_advanced_user,
        )
        if not responses:
            return responses

        silent_statuses = {
            CommandResponseStatus.NOT_FOUND,
            CommandResponseStatus.DISABLED,
            CommandResponseStatus.INVALID_ARGS,
        }
        for response in responses:
            if response.status in silent_statuses and response.message:
                await self._send_command_response(chat_key, response)

        return responses

    async def _send_command_message(self, chat_key: str, message: str) -> None:
        from nekro_agent.schemas.agent_message import AgentMessageSegment, AgentMessageSegmentType
        from nekro_agent.services.chat.universal_chat_service import universal_chat_service
        from nekro_agent.services.config_resolver import config_resolver

        effective_config = await config_resolver.get_effective_config(chat_key)
        content = f"{effective_config.AI_COMMAND_OUTPUT_PREFIX} {message}".strip()
        await universal_chat_service.send_agent_message(
            chat_key=chat_key,
            messages=[AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=content)],
            adapter=self,
            record=True,
        )

    async def _send_command_response(self, chat_key: str, response: "CommandResponse") -> None:
        from nekro_agent.services.chat.universal_chat_service import universal_chat_service
        from nekro_agent.services.command.output import build_command_output_messages

        messages = await build_command_output_messages(response, chat_key)
        if not messages:
            await self._send_command_plain_if_any(chat_key, response)
            return

        await universal_chat_service.send_agent_message(
            chat_key=chat_key,
            messages=messages,
            adapter=self,
            file_mode=True,
            record=True,
        )

    async def get_self_info(self) -> PlatformUser:
        return PlatformUser(
            platform_name="Web",
            user_id="web_agent",
            user_name="Nekro Agent",
            user_avatar="",
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:  # noqa: ARG002
        return PlatformUser(
            platform_name="Web",
            user_id=user_id,
            user_name=user_id,
            user_avatar="",
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        return PlatformChannel(
            channel_id=channel_id,
            channel_name=channel_id,
            channel_type=ChatType.PRIVATE,
            channel_avatar="",
        )
