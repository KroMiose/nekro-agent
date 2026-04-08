from __future__ import annotations

from typing import Any

from qdrant_client import models as qdrant_models

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.vector_db import get_qdrant_client

logger = get_sub_logger("kb.qdrant")

KB_CHUNK_COLLECTION = "nekro_kb_chunks"


class KBQdrantManager:
    def __init__(self, collection_name: str = KB_CHUNK_COLLECTION):
        self.collection_name = collection_name

    async def ensure_collection(self, dimension: int) -> bool:
        client = await get_qdrant_client()
        if client is None:
            logger.warning("Qdrant 客户端不可用，跳过 KB Collection 初始化")
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
        logger.info(f"知识库 Collection 创建成功: {self.collection_name}")
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

    async def search(
        self,
        *,
        query_vector: list[float],
        workspace_id: int,
        limit: int,
        score_threshold: float = 0.4,
        category: str = "",
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        client = await get_qdrant_client()
        if client is None:
            return []

        must_conditions: list[qdrant_models.Condition] = [
            qdrant_models.FieldCondition(
                key="workspace_id",
                match=qdrant_models.MatchValue(value=workspace_id),
            ),
            qdrant_models.FieldCondition(
                key="is_enabled",
                match=qdrant_models.MatchValue(value=True),
            ),
        ]
        if category.strip():
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="category",
                    match=qdrant_models.MatchValue(value=category.strip()),
                ),
            )
        if tags:
            for tag in tags:
                if not tag.strip():
                    continue
                must_conditions.append(
                    qdrant_models.FieldCondition(
                        key="tags",
                        match=qdrant_models.MatchAny(any=[tag.strip()]),
                    ),
                )

        results = await client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_models.Filter(must=must_conditions),
            limit=limit,
            score_threshold=score_threshold,
        )
        return [
            {
                "id": result.id,
                "score": float(result.score),
                "payload": result.payload,
            }
            for result in results
        ]

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


kb_qdrant_manager = KBQdrantManager()
