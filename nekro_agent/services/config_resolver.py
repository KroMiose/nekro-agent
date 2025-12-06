from nekro_agent.core.config import CoreConfig
from nekro_agent.core.config import config as system_config
from nekro_agent.core.overridable_config import OverridableConfig
from nekro_agent.services.config_service import UnifiedConfigService


class ConfigResolver:
    """配置解析器
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
    根据 频道 > 适配器 > 系统 的优先级解析最终生效的配置。
    """

    async def get_effective_config(self, chat_key: str) -> CoreConfig:
        """获取指定频道的最终有效配置

        Args:
            chat_key: 频道标识
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
    根据 会话 > 适配器 > 系统 的优先级解析最终生效的配置。
    """

    async def get_effective_config(self, chat_key: str) -> CoreConfig:
        """获取指定会话的最终有效配置

        Args:
            chat_key: 会话标识
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

        Returns:
            CoreConfig: 一个包含已解析配置的新 CoreConfig 实例
        """
        # 1. 获取所有配置层
        adapter_key = chat_key.split("-")[0]

        # 系统配置是基础
        effective_config_data = system_config.model_dump()

<<<<<<< HEAD
        # 使用 UnifiedConfigService 加载适配器和频道的覆盖配置
=======
<<<<<<< HEAD
        # 使用 UnifiedConfigService 加载适配器和频道的覆盖配置
=======
<<<<<<< HEAD
        # 使用 UnifiedConfigService 加载适配器和频道的覆盖配置
=======
        # 使用 UnifiedConfigService 加载适配器和会话的覆盖配置
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
        # 这会利用缓存或从文件动态加载
        adapter_overrides = UnifiedConfigService._get_config_instance(f"adapter_override_{adapter_key}")  # noqa: SLF001
        channel_overrides = UnifiedConfigService._get_config_instance(f"channel_config_{chat_key}")  # noqa: SLF001

        # 2. 逐字段应用覆盖逻辑
        for field_name in effective_config_data:
<<<<<<< HEAD
            # 检查频道级覆盖
=======
<<<<<<< HEAD
            # 检查频道级覆盖
=======
<<<<<<< HEAD
            # 检查频道级覆盖
=======
            # 检查会话级覆盖
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
            if isinstance(channel_overrides, OverridableConfig):
                enable_key = f"enable_{field_name}"
                if hasattr(channel_overrides, enable_key) and getattr(channel_overrides, enable_key):
                    effective_config_data[field_name] = getattr(channel_overrides, field_name)
<<<<<<< HEAD
                    continue  # 已被频道覆盖，继续下一个字段
=======
<<<<<<< HEAD
                    continue  # 已被频道覆盖，继续下一个字段
=======
<<<<<<< HEAD
                    continue  # 已被频道覆盖，继续下一个字段
=======
                    continue  # 已被会话覆盖，继续下一个字段
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)

            # 检查适配器级覆盖
            if isinstance(adapter_overrides, OverridableConfig):
                enable_key = f"enable_{field_name}"
                if hasattr(adapter_overrides, enable_key) and getattr(adapter_overrides, enable_key):
                    effective_config_data[field_name] = getattr(adapter_overrides, field_name)
                    continue  # 已被适配器覆盖，继续下一个字段

        # 使用最终解析出的数据创建一个新的 CoreConfig 实例
        return CoreConfig(**effective_config_data)


# 创建配置解析器单例
config_resolver = ConfigResolver()
