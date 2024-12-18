from ..store import BaseStore
from .base import BaseComponent


class TextComponent(BaseComponent):
    _src_store: BaseStore
    _text_template: str

    def __init__(self, text_template, src_store: BaseStore):
        self._text_template = text_template
        self._src_store = src_store

    async def render(self) -> str:
        return self._text_template.format(**self._src_store.to_dict())
