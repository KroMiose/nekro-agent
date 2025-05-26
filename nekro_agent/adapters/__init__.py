from typing import List, Type

from fastapi import FastAPI

from .interface.base import BaseAdapter
from .minecraft.adapter import MinecraftAdapter
from .onebot_v11.adapter import OnebotV11Adapter
from .sse.adapter import SSEAdapter

ALL_ADAPTERS: List[Type[BaseAdapter]] = [
    OnebotV11Adapter,
    MinecraftAdapter,
    SSEAdapter,
]


loaded_adapters: List[BaseAdapter] = []


async def load_adapters(app: FastAPI):
    for Adapter in ALL_ADAPTERS:
        adapter = Adapter()
        await adapter.init()
        app.include_router(adapter.router)
        loaded_adapters.append(adapter)


def get_adapter(adapter_key: str) -> BaseAdapter:
    for adapter in loaded_adapters:
        if adapter.key == adapter_key:
            return adapter
    raise ValueError(f"Adapter {adapter_key} not found")
