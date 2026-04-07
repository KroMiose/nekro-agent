import importlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, FastAPI

from nekro_agent.core.core_utils import ConfigManager
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.errors import AdapterUnavailableError

from .interface.base import BaseAdapter


logger = get_sub_logger("adapter.core")


@dataclass(frozen=True)
class AdapterSpec:
    key: str
    adapter_path: str
    config_path: str
    name: str
    description: str
    default_enabled: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)


ADAPTER_REGISTRY: Dict[str, AdapterSpec] = {
    "onebot_v11": AdapterSpec(
        key="onebot_v11",
        adapter_path="nekro_agent.adapters.onebot_v11.adapter.OnebotV11Adapter",
        config_path="nekro_agent.adapters.onebot_v11.adapter.OnebotV11Config",
        name="OneBot V11",
        description="OneBot V11 协议适配器",
        default_enabled=True,
        tags=("qq", "onebot", "v11"),
    ),
    "minecraft": AdapterSpec(
        key="minecraft",
        adapter_path="nekro_agent.adapters.minecraft.adapter.MinecraftAdapter",
        config_path="nekro_agent.adapters.minecraft.adapter.MinecraftConfig",
        name="Minecraft",
        description="Minecraft 适配器",
        tags=("minecraft",),
    ),
    "sse": AdapterSpec(
        key="sse",
        adapter_path="nekro_agent.adapters.sse.adapter.SSEAdapter",
        config_path="nekro_agent.adapters.sse.adapter.SSEConfig",
        name="SSE",
        description="SSE 协议适配器",
        tags=("sse", "http"),
    ),
    "bilibili_live": AdapterSpec(
        key="bilibili_live",
        adapter_path="nekro_agent.adapters.bilibili_live.adapter.BilibiliLiveAdapter",
        config_path="nekro_agent.adapters.bilibili_live.adapter.BilibiliLiveConfig",
        name="Bilibili Live",
        description="Bilibili 直播适配器",
        tags=("bilibili", "live"),
    ),
    "discord": AdapterSpec(
        key="discord",
        adapter_path="nekro_agent.adapters.discord.adapter.DiscordAdapter",
        config_path="nekro_agent.adapters.discord.config.DiscordConfig",
        name="Discord",
        description="Discord 适配器",
        tags=("discord",),
    ),
    "wechatpad": AdapterSpec(
        key="wechatpad",
        adapter_path="nekro_agent.adapters.wechatpad.adapter.WeChatPadAdapter",
        config_path="nekro_agent.adapters.wechatpad.config.WeChatPadConfig",
        name="WeChatPad Pro",
        description="WeChatPad 微信适配器",
        tags=("wechat", "wechatpad"),
    ),
    "telegram": AdapterSpec(
        key="telegram",
        adapter_path="nekro_agent.adapters.telegram.adapter.TelegramAdapter",
        config_path="nekro_agent.adapters.telegram.config.TelegramConfig",
        name="Telegram",
        description="Telegram 适配器",
        tags=("telegram",),
    ),
    "email": AdapterSpec(
        key="email",
        adapter_path="nekro_agent.adapters.email.adapter.EmailAdapter",
        config_path="nekro_agent.adapters.email.config.EmailConfig",
        name="Email",
        description="邮箱适配器",
        tags=("email", "imap", "smtp"),
    ),
    "feishu": AdapterSpec(
        key="feishu",
        adapter_path="nekro_agent.adapters.feishu.adapter.FeishuAdapter",
        config_path="nekro_agent.adapters.feishu.config.FeishuConfig",
        name="Feishu",
        description="飞书适配器",
        tags=("feishu",),
    ),
    "wxwork": AdapterSpec(
        key="wxwork",
        adapter_path="nekro_agent.adapters.wxwork.adapter.WxWorkAdapter",
        config_path="nekro_agent.adapters.wxwork.config.WxWorkConfig",
        name="WeCom AI Bot",
        description="企业微信智能机器人（AI Bot）适配器",
        tags=("wxwork", "wecom", "wechat_work"),
    ),
    "wxwork_corp_app": AdapterSpec(
        key="wxwork_corp_app",
        adapter_path="nekro_agent.adapters.wxwork_corp_app.adapter.WxWorkCorpAppAdapter",
        config_path="nekro_agent.adapters.wxwork_corp_app.config.WxWorkCorpAppConfig",
        name="WeCom Corp App",
        description="企业微信自建应用适配器",
        tags=("wxwork", "wecom", "corp_app"),
    ),
}

ADAPTER_DICT: Dict[str, str] = {key: spec.adapter_path for key, spec in ADAPTER_REGISTRY.items()}

loaded_adapters: Dict[str, BaseAdapter] = {}
adapter_load_errors: Dict[str, str] = {}


def _import_string(path: str):
    module_path, attr_name = path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)


def get_adapter_spec(adapter_key: str) -> AdapterSpec:
    return ADAPTER_REGISTRY[adapter_key]


def get_adapter_config_path(adapter_key: str) -> Path:
    return Path(OsEnv.DATA_DIR) / "configs" / adapter_key / "config.yaml"


def load_adapter_config(adapter_key: str):
    config_key = f"adapter_{adapter_key}"
    cached = ConfigManager.get_config(config_key)
    if cached is not None:
        return cached

    spec = get_adapter_spec(adapter_key)
    config_cls = _import_string(spec.config_path)
    config_path = get_adapter_config_path(adapter_key)
    config_obj = config_cls.load_from_path(config_path)
    config_obj.set_instance_config_file_path(config_path)
    if not config_path.exists():
        config_obj.dump_config(config_path)
    ConfigManager.register_config(config_key, config_obj)
    return config_obj


def is_adapter_enabled(adapter_key: str) -> bool:
    config_obj = load_adapter_config(adapter_key)
    return bool(getattr(config_obj, "ENABLED", get_adapter_spec(adapter_key).default_enabled))


def load_adapters_api() -> APIRouter:
    api = APIRouter()
    loaded_adapters.clear()
    adapter_load_errors.clear()

    for adapter_key, spec in ADAPTER_REGISTRY.items():
        if not is_adapter_enabled(adapter_key):
            logger.info(f"Adapter {adapter_key} disabled by config, skipping load")
            continue

        try:
            adapter_class = _import_string(spec.adapter_path)
            adapter: BaseAdapter = adapter_class()
            api.include_router(adapter.router, prefix=f"/adapters/{adapter_key}", tags=[f"Adapter:{adapter_key}"])
        except Exception as e:
            adapter_load_errors[adapter_key] = str(e)
            logger.exception(f'从 "{spec.adapter_path}" 加载协议端模块 "{adapter_key}" 失败')
            continue

        loaded_adapters[adapter_key] = adapter

    return api


async def init_adapters(_app: FastAPI):
    for adapter_key, adapter in loaded_adapters.items():
        await adapter.init()
        logger.info(f"Adapter {adapter_key} initialized")


async def cleanup_adapters(_app: FastAPI):
    cleanup_started_at = time.perf_counter()
    logger.debug(f"Adapter cleanup begin, total={len(loaded_adapters)}")
    for adapter_key, adapter in loaded_adapters.items():
        adapter_started_at = time.perf_counter()
        logger.debug(f"Adapter {adapter_key} cleanup begin")
        await adapter.cleanup()
        logger.debug(f"Adapter {adapter_key} cleanup finished in {time.perf_counter() - adapter_started_at:.3f}s")
        logger.info(f"Adapter {adapter_key} cleaned up")
    logger.debug(f"Adapter cleanup finished in {time.perf_counter() - cleanup_started_at:.3f}s")


def get_adapter(adapter_key: str) -> BaseAdapter:
    if adapter_key in loaded_adapters:
        return loaded_adapters[adapter_key]

    if adapter_key not in ADAPTER_REGISTRY:
        raise AdapterUnavailableError(adapter_key=adapter_key, reason="未注册")

    if not is_adapter_enabled(adapter_key):
        raise AdapterUnavailableError(adapter_key=adapter_key, reason="未启用")

    raise AdapterUnavailableError(
        adapter_key=adapter_key,
        reason=adapter_load_errors.get(adapter_key, "已启用但加载失败"),
    )
