from typing import List, Type

from fastapi import FastAPI

from .interface.base import BaseAdapter
from .nonebot.adapter import NoneBotAdapter

LOADED_ADAPTERS: List[Type[BaseAdapter]] = [
    NoneBotAdapter,
]


async def load_adapters(app: FastAPI):
    for Adapter in LOADED_ADAPTERS:
        adapter = Adapter()
        await adapter.init()
        app.include_router(await adapter.get_adapter_router())
