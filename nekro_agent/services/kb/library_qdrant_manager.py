from __future__ import annotations

from typing import Any

from qdrant_client import models as qdrant_models

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.vector_db import get_qdrant_client

logger = get_sub_logger("kb.library_qdrant")

KB_LIBRARY_CHUNK_COLLECTION = "nekro_kb_library_chunks"


class KBLibraryQdrantManager:
    def __init__(self, collection_name: str = KB_LIBRARY_CHUNK_COLLECTION):
        self.collection_name = collection_name

    async def ensure_collection(self, dimension: int) -> bool:
        client = await get_qdrant_client()
        if client is None:
            logger.warning("Qdrant 客户端不可用，跳过 KB Library Collection 初始化")
            return False

        collections = await client.get_collections()
        existing_names = [collection.name for collection in collections.collections]
        if self.collection_name in existing_names:
            return False

        await client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=dimension,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        for field_name, field_schema in (
            ("asset_id", qdrant_models.PayloadSchemaType.INTEGER),
            ("category", qdrant_models.PayloadSchemaType.KEYWORD),
            ("tags", qdrant_models.PayloadSchemaType.KEYWORD),
            ("is_enabled", qdrant_models.PayloadSchemaType.BOOL),
        ):
            try:
                await client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                )
            except Exception as e:
                logger.debug(f"知识库资产 payload index 跳过: field={field_name}, error={e}")
        logger.info(f"全局知识库 Collection 创建成功: {self.collection_name}")
        return True

    async def batch_upsert(self, points: list[tuple[int, list[float], dict[str, Any]]]) -> int:
        client = await get_qdrant_client()
        if client is None or not points:
            return 0

        await client.upsert(
            collection_name=self.collection_name,
            points=[
                qdrant_models.PointStruct(id=point_id, vector=vector, payload=payload)
                for point_id, vector, payload in points
            ],
        )
        return len(points)

    async def delete_chunk_points(self, chunk_ids: list[int]) -> None:
        if not chunk_ids:
            return
        client = await get_qdrant_client()
        if client is None:
            return
        await client.delete(
            collection_name=self.collection_name,
            points_selector=qdrant_models.PointIdsList(points=chunk_ids),
        )


kb_library_qdrant_manager = KBLibraryQdrantManager()
