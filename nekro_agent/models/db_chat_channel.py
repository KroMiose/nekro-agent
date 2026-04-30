import json
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional, Union

from pydantic import BaseModel
from tortoise import fields
from tortoise.models import Model

from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.core import config
from nekro_agent.core.logger import logger
from nekro_agent.models.db_preset import DBPreset
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.config_resolver import config_resolver
from nekro_agent.services.plugin.collector import plugin_collector

if TYPE_CHECKING:
    from nekro_agent.adapters.interface.base import BaseAdapter
    from nekro_agent.core.config import CoreConfig


class ChannelStatus(StrEnum):
    """频道状态枚举"""

    ACTIVE = "active"
    OBSERVE = "observe"
    DISABLED = "disabled"


class DefaultPreset(BaseModel):
    """默认人设"""

    name: str
    content: str


class DBChatChannel(Model):
    """数据库聊天频道模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    is_active = fields.BooleanField(default=True, description="是否激活")
    observe_mode = fields.BooleanField(default=False, description="旁观模式")
    preset_id = fields.IntField(default=None, null=True, description="人设 ID")
    data = fields.TextField(description="频道数据")

    adapter_key = fields.CharField(max_length=64, index=True, description="适配器标识")
    channel_id = fields.CharField(max_length=64, index=True, description="频道 ID")
    channel_name = fields.CharField(max_length=64, null=True, description="频道名称")
    channel_type = fields.CharField(max_length=32, null=True, description="频道类型")

    chat_key = fields.CharField(max_length=64, index=True, description="全局聊天频道唯一标识")
    conversation_start_time = fields.DatetimeField(auto_now_add=True, description="对话起始时间")
    workspace_id = fields.IntField(null=True, description="关联工作区 ID")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    _effective_config: Optional["CoreConfig"] = None

    class Meta:  # type: ignore
        table = "chat_channel"

    @classmethod
    def _normalize_status_value(cls, value: str, source: str) -> ChannelStatus:
        """将配置值标准化为 ChannelStatus，兼容旧版布尔值格式

        Args:
            value: 配置值（可能是 "active"/"observe"/"disabled" 或旧版 "true"/"false"）
            source: 来源描述（用于日志）

        Returns:
            ChannelStatus 枚举值
        """
        # 兼容旧版布尔值格式
        if value.lower() in ("true", "1"):
            logger.debug(f"{source} 检测到旧版布尔值 '{value}'，自动转换为 'active'")
            return ChannelStatus.ACTIVE
        if value.lower() in ("false", "0"):
            logger.debug(f"{source} 检测到旧版布尔值 '{value}'，自动转换为 'disabled'")
            return ChannelStatus.DISABLED

        try:
            return ChannelStatus(value)
        except ValueError:
            logger.warning(f"{source} 无效的频道状态值: {value}，回退到 active")
            return ChannelStatus.ACTIVE

    @classmethod
    def _resolve_default_channel_status(
        cls,
        channel_type: ChatType,
        adapter: Optional["BaseAdapter"] = None,
    ) -> ChannelStatus:
        """解析新频道的默认状态

        优先级：适配器覆盖 > 全局配置

        Args:
            channel_type: 频道类型
            adapter: 适配器实例（可选）

        Returns:
            ChannelStatus 枚举值
        """
        # 1. 检查适配器覆盖
        if adapter is not None:
            adapter_status = adapter.get_default_channel_status(channel_type)
            if adapter_status is not None:
                return cls._normalize_status_value(str(adapter_status), f"适配器 {adapter.key}")

        # 2. 回退到全局配置
        if channel_type == ChatType.GROUP:
            return cls._normalize_status_value(
                config.SESSION_GROUP_ACTIVE_DEFAULT, "SESSION_GROUP_ACTIVE_DEFAULT",
            )
        if channel_type == ChatType.PRIVATE:
            return cls._normalize_status_value(
                config.SESSION_PRIVATE_ACTIVE_DEFAULT, "SESSION_PRIVATE_ACTIVE_DEFAULT",
            )

        logger.warning(f"未知的频道类型: {channel_type}，使用默认状态 active")
        return ChannelStatus.ACTIVE

    @classmethod
    async def get_or_create(
        cls,
        adapter_key: str,
        channel_id: str,
        channel_type: ChatType,
        channel_name: str = "",
        adapter: Optional["BaseAdapter"] = None,
    ) -> "DBChatChannel":
        """获取或创建聊天频道"""
        channel = await cls.get_or_none(adapter_key=adapter_key, channel_id=channel_id)
        if not channel:
            default_status = cls._resolve_default_channel_status(channel_type, adapter)
            is_active = default_status != ChannelStatus.DISABLED
            observe_mode = default_status == ChannelStatus.OBSERVE
            channel = await cls.create(
                adapter_key=adapter_key,
                channel_id=channel_id,
                channel_type=channel_type.value,
                channel_name=channel_name,
                chat_key=f"{adapter_key}-{channel_id}",
                is_active=is_active,
                observe_mode=observe_mode,
                data=json.dumps({}),
            )
        else:
            if channel_name and channel.channel_name != channel_name:
                logger.info(f"更新频道名称: {channel.channel_name} -> {channel_name}")
                channel.channel_name = channel_name
                await channel.save()
            if channel_type and channel.channel_type != channel_type.value:
                logger.info(f"更新频道类型: {channel.channel_type} -> {channel_type.value}")
                channel.channel_type = channel_type.value
                await channel.save()
        return channel

    @classmethod
    async def get_channel(cls, chat_key: str) -> "DBChatChannel":
        """获取聊天频道"""
        assert chat_key, "获取聊天频道失败，chat_key 为空"
        channel = await cls.filter(chat_key=chat_key).first()
        if not channel:
            raise ValueError(f"聊天频道不存在: {chat_key}")
        return channel

    async def sync_channel_name(self):
        """同步频道名称"""
        try:
            self.channel_name = await self.get_channel_name()
        except Exception as e:
            logger.error(f"同步频道名称失败: {e!s}")
        else:
            await self.save()

    async def get_channel_name(self) -> str:
        """获取频道名称"""

        adapter = adapter_utils.get_adapter(self.adapter_key)
        return (await adapter.get_channel_info(self.channel_id)).channel_name

    async def reset_channel(self):
        """重置聊天频道"""
        from nekro_agent.schemas.agent_ctx import AgentCtx

        self.conversation_start_time = datetime.now()  # 重置对话起始时间
        await self.save()

        # 执行重置回调
        await plugin_collector.chat_channel_on_reset(await AgentCtx.create_by_chat_key(chat_key=self.chat_key))

    async def set_active(self, is_active: bool):
        """设置频道是否激活"""
        self.is_active = is_active
        if not is_active:
            self.observe_mode = False
        await self.save()

    @property
    def channel_status(self) -> ChannelStatus:
        """获取频道状态"""
        if not self.is_active:
            return ChannelStatus.DISABLED
        if self.observe_mode:
            return ChannelStatus.OBSERVE
        return ChannelStatus.ACTIVE

    async def set_channel_status(self, status: ChannelStatus | str):
        """设置频道状态

        Args:
            status: ChannelStatus 枚举值或字符串
        """
        status = ChannelStatus(status)
        if status == ChannelStatus.ACTIVE:
            self.is_active = True
            self.observe_mode = False
        elif status == ChannelStatus.OBSERVE:
            self.is_active = True
            self.observe_mode = True
        elif status == ChannelStatus.DISABLED:
            self.is_active = False
            self.observe_mode = False
        else:
            raise ValueError(f"无效的频道状态: {status}")
        await self.save()

    @property
    def chat_type(self) -> ChatType:
        """获取聊天频道类型"""
        try:
            return ChatType(self.channel_type)
        except ValueError as e:
            logger.error(f"获取聊天频道类型失败: {e!s}")
            return ChatType.UNKNOWN

    async def get_preset(self) -> Union[DBPreset, DefaultPreset]:
        """获取人设"""
        # 先尝试频道自身的 preset_id
        preset = await DBPreset.get_or_none(id=self.preset_id)
        if preset:
            return preset
        # 再尝试系统默认人设 ID
        if config.AI_CHAT_DEFAULT_PRESET_ID is not None:
            default_preset = await DBPreset.get_or_none(id=config.AI_CHAT_DEFAULT_PRESET_ID)
            if default_preset:
                return default_preset
        # 最终回退到内置默认人设
        from nekro_agent.services.preset_service import DEFAULT_PRESET_CONTENT, DEFAULT_PRESET_NAME

        return DefaultPreset(name=DEFAULT_PRESET_NAME, content=DEFAULT_PRESET_CONTENT)

    @property
    def adapter(self) -> "BaseAdapter":
        """获取适配器"""
        return adapter_utils.get_adapter(self.adapter_key)

    async def get_effective_config(self) -> "CoreConfig":
        if self._effective_config is None:
            self._effective_config = await config_resolver.get_effective_config(self.chat_key)
        return self._effective_config

    async def set_preset(self, preset_id: Optional[int] = None) -> str:
        """设置聊天频道人设

        Args:
            preset_id: 人设ID，传入None则使用默认人设

        Returns:
            str: 设置成功的消息，包含当前人设名称
        """
        # 设置人设ID，None需要作为null处理
        if preset_id is None or preset_id == -1:
            self.preset_id = None  # type: ignore  # 在数据库模型中允许为null
        else:
            self.preset_id = preset_id
        await self.save()

        # 获取人设信息
        preset = await self.get_preset()
        preset_name = preset.name if hasattr(preset, "name") else "默认人设"

        return f"设置成功，当前人设: {preset_name}"
