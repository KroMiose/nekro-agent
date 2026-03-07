from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generic, List, Optional, Tuple, Type, TypeVar, cast

from fastapi import APIRouter
from jinja2 import Environment
from nonebot import logger
from pydantic import BaseModel, Field

from nekro_agent.core.core_utils import ConfigBase

if TYPE_CHECKING:
    from nekro_agent.services.command.schemas import CommandResponse
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.agent.templates.base import PromptTemplate, register_template

from .schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformUser,
)


class AdapterMetadata(BaseModel):
    """适配器元数据"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    homepage: str = ""
    tags: List[str] = []


class BaseAdapterConfig(ConfigBase):
    """适配器配置基类"""

    SESSION_ENABLE_AT: bool = Field(
        default=True,
        title="启用 @用户 功能",
        description="关闭后 AI 发送的 @用户 消息将被解析为纯文本用户名，避免反复打扰用户",
    )
    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=True,
        title="显示处理中表情反馈",
        description="当 AI 开始处理消息时，对应消息会显示处理中表情反馈",
    )

    # 命令系统配置
    COMMAND_PREFIX: str = Field(
        default="/",
        title="命令前缀",
        description="触发命令的前缀字符，如 / 或 !",
    )
    COMMAND_ENABLED: bool = Field(
        default=True,
        title="启用命令系统",
        description="关闭后该适配器不再识别和处理命令",
    )
    COMMAND_UNAUTHORIZED_OUTPUT: bool = Field(
        default=True,
        title="权限不足提示",
        description="权限不足时是否向用户输出提示信息",
    )
    COMMAND_ENHANCED_OUTPUT: bool = Field(
        default=False,
        title="命令增强输出",
        description="启用后，较长的命令输出将使用平台特性进行优化展示（如合并转发、卡片等）",
    )
    COMMAND_ENHANCED_OUTPUT_MIN_LENGTH: int = Field(
        default=200,
        title="增强输出触发字数",
        description="命令输出超过此字数时触发增强输出（需启用命令增强输出）",
    )


# 定义配置类型变量，约束为 BaseAdapterConfig 子类
TConfig = TypeVar("TConfig", bound=BaseAdapterConfig)
T = TypeVar("T", bound="BaseAdapter")


class BaseAdapter(ABC, Generic[TConfig]):
    """适配器基类"""

    _router: APIRouter  # 实例变量的类型注解
    _Configs: Type[TConfig]
    _config: TConfig

    def __init__(self, config_cls: Type[TConfig] = BaseAdapterConfig):
        self._Configs = config_cls
        self._adapter_config_path = Path(OsEnv.DATA_DIR) / "configs" / self.key / "config.yaml"
        self._config = self.get_config(self._Configs)

        # 注册配置到统一配置系统
        from nekro_agent.core.core_utils import ConfigManager

        ConfigManager.register_config(f"adapter_{self.key}", self._config)

    @property
    @abstractmethod
    def key(self) -> str:
        """适配器唯一标识"""
        raise NotImplementedError

    @property
    @abstractmethod
    def metadata(self) -> AdapterMetadata:
        """适配器元数据"""
        raise NotImplementedError

    def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        return APIRouter()

    @property
    def router(self) -> APIRouter:
        """获取适配器路由"""
        if hasattr(self, "_router"):
            return self._router
        self._router = self.get_adapter_router()
        return self._router

    def get_config(self, config_cls: Type[TConfig]) -> TConfig:
        """获取适配器配置"""
        if not hasattr(self, "_config"):
            self._config = self._Configs.load_config(file_path=self._adapter_config_path)
            self._config.dump_config(self._adapter_config_path)
        return cast(config_cls, self._config)

    @property
    def config(self) -> TConfig:
        """获取适配器配置"""
        return self.get_config(self._Configs)

    @property
    def config_path(self) -> Path:
        """获取适配器配置路径"""
        return self._adapter_config_path

    def cast(self, adapter_type: Type[T]) -> T:
        """转换适配器类型"""
        return cast(adapter_type, self)

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "Group chat: `platform-group_123456` (where 123456 is the group number)",
            "Private chat: `platform-private_123456` (where 123456 is the user's QQ number)",
        ]

    def get_docs_path(self) -> Path:
        """获取适配器文档路径"""
        return Path(__file__).parent.parent / self.key / "README.md"

    @abstractmethod
    async def init(self) -> None:
        """初始化适配器"""
        raise NotImplementedError

    @abstractmethod
    async def cleanup(self) -> None:
        """清理适配器"""
        raise NotImplementedError

    async def set_dialog_example(self) -> Optional[List[PromptTemplate]]:
        """自定义对话示例"""
        return None

    async def get_jinja_env(self) -> Optional[Environment]:
        """返回jinja模板"""
        return None

    @abstractmethod
    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到协议端

        Args:
            request: 协议端发送请求，包含已经预处理好的消息数据

        Returns:
            PlatformSendResponse: 发送结果
        """
        raise NotImplementedError

    @abstractmethod
    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        raise NotImplementedError

    @abstractmethod
    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户(或者群聊用户)信息"""
        raise NotImplementedError

    @abstractmethod
    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        raise NotImplementedError

    @property
    def supports_webui_send(self) -> bool:
        """是否支持从 WebUI 发送消息（默认不支持，适配器可按需覆盖）"""
        return False

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:  # noqa: ARG002
        """设置消息反应（可选实现）

        Args:
            message_id (str): 消息ID
            status (bool): True为设置反应，False为取消反应

        Returns:
            bool: 是否成功设置
        """
        # 默认实现：不支持消息反应功能
        return False

    # region 辅助方法

    def build_chat_key(self, channel_id: str) -> str:
        """构建聊天标识"""
        return f"{self.key}-{channel_id}"

    def parse_chat_key(self, chat_key: str) -> Tuple[str, str]:
        """解析聊天标识

        Args:
            chat_key: 聊天标识

        Returns:
            Tuple[str, str]: (adapter_key, channel_id)
        """
        parts = chat_key.split("-", 1)

        if len(parts) != 2:
            raise ValueError(f"无效的聊天标识: {chat_key}")

        adapter_key = parts[0]
        channel_id = parts[1]

        return adapter_key, channel_id

    def parse_channel_id(self, chat_key: str) -> str:
        """解析聊天标识中的频道ID"""
        return self.parse_chat_key(chat_key)[1]

    # endregion

    # region 命令系统

    def detect_command(self, text: str) -> Optional[Tuple[str, str]]:
        """检测文本是否为命令，返回 (command_name, raw_args) 或 None"""
        prefix = self.config.COMMAND_PREFIX
        if not text.startswith(prefix):
            return None
        content = text[len(prefix):]
        parts = content.split(None, 1)
        if not parts:
            return None
        return parts[0], parts[1] if len(parts) > 1 else ""

    async def execute_command(
        self,
        chat_key: str,
        user_id: str,
        username: str,
        command_name: str,
        raw_args: str,
        is_super_user: bool = False,
        is_advanced_user: bool = False,
    ) -> Optional[List["CommandResponse"]]:
        """执行命令并消费流式输出 - 自动检查适配器级开关"""
        from nekro_agent.services.command.registry import command_registry
        from nekro_agent.services.command.schemas import (
            CommandExecutionContext,
            CommandRequest,
            CommandResponse,
            CommandResponseStatus,
        )
        from nekro_agent.services.command.wait_manager import wait_manager

        if not self.config.COMMAND_ENABLED:
            return None

        # 用户发送新命令时自动取消挂起的 wait
        wait_manager.cancel(chat_key, user_id)

        context = CommandExecutionContext(
            user_id=user_id,
            chat_key=chat_key,
            username=username,
            adapter_key=self.key,
            is_super_user=is_super_user,
            is_advanced_user=is_advanced_user,
        )
        request = CommandRequest(context=context, command_name=command_name, raw_args=raw_args)

        from nekro_agent.services.command_output_broadcaster import command_output_broadcaster

        responses: List[CommandResponse] = []
        async for response in command_registry.execute(request):
            responses.append(response)
            if response.status == CommandResponseStatus.PROCESSING:
                await self._send_command_message(chat_key, response.message)
            elif response.status == CommandResponseStatus.WAITING:
                await self._handle_command_wait(chat_key, user_id, response)
            elif response.status in (CommandResponseStatus.SUCCESS, CommandResponseStatus.ERROR):
                await self._send_command_message(chat_key, response.message)
            elif response.status == CommandResponseStatus.UNAUTHORIZED:
                if self.config.COMMAND_UNAUTHORIZED_OUTPUT:
                    await self._send_command_message(chat_key, response.message)

            # 广播到 WebUI（所有状态均广播，供管理员监控）
            await command_output_broadcaster.publish(
                chat_key=chat_key,
                command_name=command_name,
                status=response.status.value,
                message=response.message,
            )
        return responses

    async def try_handle_wait_input(
        self,
        chat_key: str,
        user_id: str,
        username: str,
        text: str,
        is_super_user: bool = False,
        is_advanced_user: bool = False,
    ) -> bool:
        """检查并处理挂起的 wait 交互

        当用户发送非命令消息时调用此方法，检查是否有匹配的 WaitSession。
        若存在，将用户输入路由到 callback_cmd，并返回 True 表示已消费。

        Returns:
            True 表示消息已被 wait 消费，调用方应终止后续处理
        """
        from nekro_agent.services.command.wait_manager import wait_manager

        session = wait_manager.try_consume(chat_key, user_id)
        if not session:
            return False

        # 将 context_data 中的内容作为额外参数拼接到 raw_args
        extra_args = " ".join(f'{k}:"{v}"' for k, v in session.context_data.items()) if session.context_data else ""
        raw_args = f"{text} {extra_args}".strip() if extra_args else text

        await self.execute_command(
            chat_key=chat_key,
            user_id=user_id,
            username=username,
            command_name=session.callback_cmd,
            raw_args=raw_args,
            is_super_user=is_super_user,
            is_advanced_user=is_advanced_user,
        )
        return True

    async def _send_command_message(self, chat_key: str, message: str) -> None:
        """发送命令输出消息到频道

        当启用增强输出且消息长度超过阈值时，尝试使用平台特性发送；
        若平台不支持或发送失败，回退为普通文本。
        """
        if (
            self.config.COMMAND_ENHANCED_OUTPUT
            and len(message) >= self.config.COMMAND_ENHANCED_OUTPUT_MIN_LENGTH
            and await self._try_send_enhanced_command_message(chat_key, message)
        ):
            return

        from nekro_agent.services.chat.universal_chat_service import universal_chat_service

        await universal_chat_service.send_operation_message(
            chat_key=chat_key,
            message=message,
        )

    async def _try_send_enhanced_command_message(self, chat_key: str, message: str) -> bool:  # noqa: ARG002
        """尝试以平台增强格式发送命令消息

        子类可重写此方法，利用平台特性（合并转发、卡片等）优化长消息展示。
        返回 True 表示发送成功，False 表示不支持或失败（将回退为普通文本）。
        """
        return False

    async def _handle_command_wait(self, chat_key: str, user_id: str, response: "CommandResponse") -> None:
        """处理 wait 状态（发送提示消息并注册 WaitSession）"""
        from nekro_agent.services.command.wait_manager import wait_manager

        # 发送 wait 提示消息（含可选项）
        wait_msg = response.message
        if response.wait_options:
            options_str = " / ".join(response.wait_options)
            wait_msg = f"{wait_msg}\n可选: {options_str}"
        await self._send_command_message(chat_key, wait_msg)

        if response.callback_cmd:
            await wait_manager.create_session(
                chat_key=chat_key,
                user_id=user_id,
                callback_cmd=response.callback_cmd,
                context_data=response.context_data,
                timeout=response.wait_timeout or 60.0,
                on_timeout_message=response.on_timeout_message or "操作超时，已取消",
            )

    @property
    def supports_command_completion(self) -> bool:
        """是否支持命令补全（子类可覆盖）"""
        return False

    async def sync_commands(self, chat_key: Optional[str] = None) -> None:
        """同步命令到平台（子类可覆盖实现 Slash Commands 等）"""

    # endregion
