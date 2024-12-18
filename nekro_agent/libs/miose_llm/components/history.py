from typing import Optional, Type

from ..store import BaseStore
from ..tools.vector_dbs import BaseVectorDB
from .base import BaseComponent


class VecHistoryComponent(BaseComponent):
    """基于向量数据库的历史记录组件

    该组件基于向量数据库，实现历史记录功能。
    组件参数：
        - use_collection_name: 向量数据库使用的集合名称
    """

    class Params(BaseComponent.Params):
        use_collection_name: str

    _vector_db: BaseVectorDB

    def setup(self, use: Type[BaseVectorDB]):
        self._vector_db = use()
        return super().setup()

    async def render(self) -> str:
        """渲染组件"""
        return f"TestRender: VecHistoryComponent(use_collection_name='{self.params.use_collection_name}')"

    def bind_collection_name(
        self,
        collection_name: str,
        src_store: Optional[BaseStore] = None,
    ):
        """绑定向量数据库使用的集合名称"""
        return self.batch_bind(
            use_collection_name=collection_name,
            src_store=src_store,
        )
