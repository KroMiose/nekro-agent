from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type, cast

from fastapi import APIRouter
from jinja2 import Environment
from nonebot import logger
from pydantic import Field

from nekro_agent.core.core_utils import ConfigBase
from nekro_agent.core.os_env import OsEnv
from nekro_agent.services.agent.templates.base import PromptTemplate, register_template

from .schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformUser,
)


class BaseAdapterConfig(ConfigBase):
    """适配器配置基类"""

    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=True,
        title="显示处理中表情",
        description="当 AI 处理消息时，对应消息会显示处理中表情回应",
    )
    SESSION_ENABLE_AT: bool = Field(
        default=True,
        title="启用 At 功能",
        description="关闭后 AI 发送的 At 消息将被解析为纯文本用户名，避免反复打扰用户",
    )


class BaseAdapter(ABC):
    """适配器基类"""

    _router: APIRouter  # 实例变量的类型注解
    _Configs: Type[BaseAdapterConfig] = BaseAdapterConfig
    _config: BaseAdapterConfig

    def __init__(self, config_cls: Type[BaseAdapterConfig] = BaseAdapterConfig):
        self._Configs = config_cls
        self._adapter_config_path = Path(OsEnv.DATA_DIR) / "configs" / self.key / "config.yaml"
        self._config = self.get_config(self._Configs)

    @property
    def key(self) -> str:
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

    def get_config(self, config_cls: Type[BaseAdapterConfig] = BaseAdapterConfig) -> BaseAdapterConfig:
        """获取适配器配置"""
        if not hasattr(self, "_config"):
            self._config = self._Configs.load_config(file_path=self._adapter_config_path)
            self._config.dump_config(self._adapter_config_path)
        return cast(config_cls, self._config)

    @property
    def config(self) -> BaseAdapterConfig:
        """获取适配器配置"""
        return self.get_config(self._Configs)

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "Group chat: `platform-group_123456` (where 123456 is the group number)",
            "Private chat: `platform-private_123456` (where 123456 is the user's QQ number)",
        ]

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
        parts = chat_key.split("-")

        if len(parts) != 2:
            raise ValueError(f"无效的聊天标识: {chat_key}")

        adapter_key = parts[0]
        channel_id = parts[1]

        return adapter_key, channel_id

    def parse_channel_id(self, chat_key: str) -> str:
        """解析聊天标识中的频道ID"""
        return self.parse_chat_key(chat_key)[1]

    # endregion
