from __future__ import annotations

import inspect
from collections import defaultdict
from typing import Any

from qdrant_client import models as qdrant_models

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.vector_db import get_qdrant_client

logger = get_sub_logger("kb.qdrant")

KB_CHUNK_COLLECTION = "nekro_kb_chunks"


class KBQdrantManager:
    def __init__(self, collection_name: str = KB_CHUNK_COLLECTION):
        self.collection_name = collection_name

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    @staticmethod
    def _read_value(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @classmethod
    def _normalize_point(cls, result: Any) -> dict[str, Any] | None:
        point_id = cls._coerce_int(cls._read_value(result, "id"))
        if point_id is None:
            return None
        payload = cls._read_value(result, "payload", {})
        score = cls._read_value(result, "score", 0.0)
        return {
            "id": point_id,
            "score": float(score or 0.0),
            "payload": payload if isinstance(payload, dict) else {},
        }

    @classmethod
    def _normalize_groups(cls, result: Any) -> list[dict[str, Any]]:
        raw_groups = cls._read_value(result, "groups", [])
        normalized_groups: list[dict[str, Any]] = []
        for raw_group in raw_groups:
            raw_hits = cls._read_value(raw_group, "hits", [])
            hits = [hit for raw_hit in raw_hits if (hit := cls._normalize_point(raw_hit)) is not None]
            if not hits:
                continue
            group_id = cls._coerce_int(cls._read_value(raw_group, "group_id"))
            if group_id is None:
                group_id = cls._coerce_int(cls._read_value(raw_group, "id"))
            if group_id is None:
                group_id = cls._coerce_int(hits[0]["payload"].get("document_id"))
            if group_id is None:
                continue
            normalized_groups.append({"document_id": group_id, "hits": hits})
        return normalized_groups

    def _build_filter(
        self,
        *,
        workspace_id: int,
        category: str = "",
        tags: list[str] | None = None,
    ) -> qdrant_models.Filter:
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
        return qdrant_models.Filter(must=must_conditions)

    async def _ensure_payload_indexes(self, client: Any) -> None:
        for field_name, field_schema in (
            ("workspace_id", qdrant_models.PayloadSchemaType.INTEGER),
            ("document_id", qdrant_models.PayloadSchemaType.INTEGER),
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
                logger.debug(f"知识库 payload index 跳过: field={field_name}, error={e}")

    async def ensure_collection(self, dimension: int) -> bool:
        client = await get_qdrant_client()
        if client is None:
            logger.warning("Qdrant 客户端不可用，跳过 KB Collection 初始化")
            return False

        collections = await client.get_collections()
        existing_names = [collection.name for collection in collections.collections]
        if self.collection_name in existing_names:
            try:
                info = await client.get_collection(self.collection_name)
                current_size = info.config.params.vectors.size
                if current_size != dimension:
                    logger.error(
                        f"知识库 Collection 向量维度不匹配（当前={current_size}，期望={dimension}），"
                        f"向量检索结果可能无效，请切换回原 embedding 模型或重建全部知识库索引",
                    )
            except Exception as e:
                logger.debug(f"读取知识库 Collection 信息失败: {e}")
            await self._ensure_payload_indexes(client)
            return False

        await client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=dimension,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        await self._ensure_payload_indexes(client)
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

    async def set_payload(self, *, chunk_ids: list[int], payload: dict[str, Any]) -> None:
        if not chunk_ids or not payload:
            return
        client = await get_qdrant_client()
        if client is None:
            return
        await client.set_payload(
            collection_name=self.collection_name,
            payload=payload,
            points=qdrant_models.PointIdsList(points=chunk_ids),
        )

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

        results = await client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=self._build_filter(workspace_id=workspace_id, category=category, tags=tags),
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [item for result in results if (item := self._normalize_point(result)) is not None]

    async def search_grouped(
        self,
        *,
        query_vector: list[float],
        workspace_id: int,
        limit: int,
        group_size: int,
        score_threshold: float = 0.4,
        category: str = "",
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        client = await get_qdrant_client()
        if client is None:
            return []

        query_filter = self._build_filter(workspace_id=workspace_id, category=category, tags=tags)
        payload_fields = [
            "document_id",
            "heading_path",
            "content_preview",
            "char_start",
            "char_end",
            "category",
            "tags",
            "is_enabled",
        ]

        for method_name in ("query_points_groups", "search_groups"):
            method = getattr(client, method_name, None)
            if not callable(method):
                continue
            try:
                parameters = inspect.signature(method).parameters
                kwargs: dict[str, Any] = {
                    "collection_name": self.collection_name,
                    "group_by": "document_id",
                    "limit": limit,
                    "group_size": group_size,
                    "score_threshold": score_threshold,
                }
                if "query" in parameters:
                    kwargs["query"] = query_vector
                elif "query_vector" in parameters:
                    kwargs["query_vector"] = query_vector
                else:
                    continue
                if "query_filter" in parameters:
                    kwargs["query_filter"] = query_filter
                elif "filter" in parameters:
                    kwargs["filter"] = query_filter
                if "with_payload" in parameters:
                    kwargs["with_payload"] = payload_fields
                if "with_vector" in parameters:
                    kwargs["with_vector"] = False
                elif "with_vectors" in parameters:
                    kwargs["with_vectors"] = False
                grouped = await method(**kwargs)
                return self._normalize_groups(grouped)
            except Exception as e:
                logger.warning(f"知识库 grouped search 调用失败，回退普通检索: method={method_name}, error={e}")

        flat_results = await self.search(
            query_vector=query_vector,
            workspace_id=workspace_id,
            limit=max(limit * max(1, group_size) * 4, limit),
            score_threshold=score_threshold,
            category=category,
            tags=tags,
        )
        grouped_map: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        for result in flat_results:
            document_id = self._coerce_int(result["payload"].get("document_id"))
            if document_id is None:
                continue
            grouped_map[document_id].append(result)

        grouped_results: list[dict[str, Any]] = []
        for document_id, hits in grouped_map.items():
            grouped_results.append(
                {
                    "document_id": document_id,
                    "hits": sorted(hits, key=lambda item: float(item["score"]), reverse=True)[:group_size],
                }
            )
        grouped_results.sort(
            key=lambda item: max((float(hit["score"]) for hit in item["hits"]), default=0.0),
            reverse=True,
        )
        return grouped_results[:limit]

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
