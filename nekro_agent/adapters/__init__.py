import importlib
from typing import Dict, Type

from fastapi import APIRouter, FastAPI

from nekro_agent.core import logger

from .interface.base import BaseAdapter

ADAPTER_DICT: Dict[str, str] = {
    "onebot_v11": "nekro_agent.adapters.onebot_v11.adapter.OnebotV11Adapter",
    "minecraft": "nekro_agent.adapters.minecraft.adapter.MinecraftAdapter",
    "bilibili": "nekro_agent.adapters.bilibili_live.adapter.BilibiliLiveAdapter",
}


loaded_adapters: Dict[str, BaseAdapter] = {}


def load_adapters_api() -> APIRouter:
    api = APIRouter()
    for adapter_key, adapter_path in ADAPTER_DICT.items():
        module_path = adapter_path.split(".")[:-1]
        module = importlib.import_module(".".join(module_path))
        adapter_class: Type[BaseAdapter] = getattr(module, adapter_path.split(".")[-1])
        adapter: BaseAdapter = adapter_class()
        api.include_router(adapter.router, prefix=f"/adapters/{adapter_key}", tags=[f"Adapter:{adapter_key}"])
        loaded_adapters[adapter_key] = adapter
    return api


async def init_adapters(_app: FastAPI):
    for adapter_key, adapter in loaded_adapters.items():
        await adapter.init()
        logger.info(f"Adapter {adapter_key} initialized")


def get_adapter(adapter_key: str) -> BaseAdapter:
    return loaded_adapters[adapter_key]
