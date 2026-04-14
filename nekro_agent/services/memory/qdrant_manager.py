"""Qdrant 向量数据库管理服务

负责记忆系统的 Collection 管理、向量存储与检索。
"""

import asyncio
from typing import Any

from qdrant_client import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.vector_db import get_qdrant_client
from nekro_agent.models.db_mem_paragraph import DBMemParagraph
from nekro_agent.services.memory.embedding_service import embed_text, get_memory_embedding_dimension

logger = get_sub_logger("memory.qdrant")

# Collection 名称常量
MEMORY_PARAGRAPH_COLLECTION = "nekro_memory_paragraphs"
MAX_UPSERT_RETRIES = 3
UPSERT_RETRY_DELAY = 0.5

class MemoryQdrantManager:
    """记忆系统 Qdrant 管理器

    提供 Collection 初始化、向量 CRUD 操作。
    """

    def __init__(self, collection_name: str = MEMORY_PARAGRAPH_COLLECTION):
        self.collection_name = collection_name
        self._initialized = False

    @staticmethod
    def _is_retryable_qdrant_error(error: Exception) -> bool:
        """判断是否为可重试的 Qdrant 临时错误"""
        if isinstance(error, UnexpectedResponse):
            if error.status_code >= 500:
                return True
            if "Please retry" in str(error):
                return True
        return False

    async def _upsert_points_with_retry(
        self,
        points: list[qdrant_models.PointStruct],
    ) -> None:
        """执行带重试的 Qdrant upsert"""
        client = await get_qdrant_client()
        if client is None:
            raise RuntimeError("Qdrant 客户端不可用")

        last_error: Exception | None = None
        for attempt in range(MAX_UPSERT_RETRIES):
            try:
                await client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
                return
            except Exception as e:
                last_error = e
                if not self._is_retryable_qdrant_error(e) or attempt >= MAX_UPSERT_RETRIES - 1:
                    raise
                logger.warning(
                    f"Qdrant upsert 临时失败，准备重试: "
                    f"attempt={attempt + 1}/{MAX_UPSERT_RETRIES}, error={e}",
                )
                await asyncio.sleep(UPSERT_RETRY_DELAY * (attempt + 1))

        raise last_error or RuntimeError("Qdrant upsert 失败")

    async def ensure_collection(self, dimension: int | None = None) -> bool:
        """确保 Collection 存在，不存在则创建

        Args:
            dimension: 向量维度，未指定时读取当前配置

        Returns:
            是否新创建了 Collection
        """
        resolved_dimension = dimension or get_memory_embedding_dimension()
        client = await get_qdrant_client()
        if client is None:
            logger.warning("Qdrant 客户端不可用，跳过 Collection 初始化")
            return False

        try:
            collections = await client.get_collections()
            existing_names = [c.name for c in collections.collections]

            if self.collection_name in existing_names:
                info = await client.get_collection(self.collection_name)
                current_size = None
                try:
                    current_size = info.config.params.vectors.size
                except Exception:
                    current_size = None

                if current_size is not None and current_size != resolved_dimension:
                    points_count = int(info.points_count or 0)
                    if points_count == 0:
                        logger.warning(
                            f"记忆 Collection 维度不匹配且当前为空，准备重建: "
                            f"current={current_size}, expected={resolved_dimension}",
                        )
                        await client.delete_collection(self.collection_name)
                    else:
                        logger.warning(
                            f"记忆 Collection 维度不匹配，但已有数据，跳过自动重建: "
                            f"current={current_size}, expected={resolved_dimension}, points={points_count}",
                        )
                        self._initialized = True
                        return False
                else:
                    logger.debug(f"Collection {self.collection_name} 已存在")
                    self._initialized = True
                    return False

            if self.collection_name in existing_names:
                collections = await client.get_collections()
                existing_names = [c.name for c in collections.collections]
                if self.collection_name in existing_names:
                    logger.debug(f"Collection {self.collection_name} 已存在")
                    self._initialized = True
                    return False

            # 创建新 Collection
            await client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=resolved_dimension,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info(f"记忆系统 Collection {self.collection_name} 创建成功")
            self._initialized = True
            return True

        except Exception as e:
            logger.exception(f"初始化 Collection 失败: {e}")
            raise

    async def upsert_paragraph(
        self,
        paragraph_id: int,
        embedding: list[float],
        payload: dict[str, Any],
    ) -> bool:
        """插入或更新段落向量

        Args:
            paragraph_id: 段落 ID（作为 Qdrant point ID）
            embedding: 向量数据
            payload: 元数据

        Returns:
            是否成功
        """
        client = await get_qdrant_client()
        if client is None:
            logger.warning("Qdrant 客户端不可用")
            return False

        try:
            await self._upsert_points_with_retry(
                [
                    qdrant_models.PointStruct(
                        id=paragraph_id,
                        vector=embedding,
                        payload=payload,
                    ),
                ]
            )
            logger.debug(f"向量 upsert 成功: paragraph_id={paragraph_id}")
            return True
        except Exception as e:
            logger.exception(f"向量 upsert 失败: {e}")
            return False

    async def batch_upsert(
        self,
        points: list[tuple[int, list[float], dict[str, Any]]],
        batch_size: int = 100,
    ) -> int:
        """批量插入向量

        Args:
            points: (paragraph_id, embedding, payload) 元组列表
            batch_size: 批次大小

        Returns:
            成功插入的数量
        """
        client = await get_qdrant_client()
        if client is None:
            return 0

        success_count = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            try:
                await self._upsert_points_with_retry(
                    [
                        qdrant_models.PointStruct(
                            id=pid,
                            vector=emb,
                            payload=pl,
                        )
                        for pid, emb, pl in batch
                    ]
                )
                success_count += len(batch)
            except Exception as e:
                logger.exception(f"批量 upsert 失败: {e}")

        return success_count

    async def search(
        self,
        query_vector: list[float],
        workspace_id: int,
        limit: int = 10,
        score_threshold: float = 0.5,
        cognitive_type: str | None = None,
        include_inactive: bool = False,
        event_time_from: int | None = None,
        event_time_to: int | None = None,
    ) -> list[dict[str, Any]]:
        """语义搜索记忆段落

        Args:
            query_vector: 查询向量
            workspace_id: 工作区 ID（必须，隔离边界）
            limit: 返回数量
            score_threshold: 相似度阈值
            cognitive_type: 可选，过滤认知类型
            include_inactive: 是否包含已失活记忆

        Returns:
            搜索结果列表
        """
        client = await get_qdrant_client()
        if client is None:
            return []

        # 构建过滤条件
        must_conditions = [
            qdrant_models.FieldCondition(
                key="workspace_id",
                match=qdrant_models.MatchValue(value=workspace_id),
            ),
        ]

        if not include_inactive:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="is_inactive",
                    match=qdrant_models.MatchValue(value=False),
                ),
            )

        if cognitive_type:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="cognitive_type",
                    match=qdrant_models.MatchValue(value=cognitive_type),
                ),
            )

        if event_time_from is not None:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="event_time",
                    range=qdrant_models.Range(gte=event_time_from),
                ),
            )

        if event_time_to is not None:
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key="event_time",
                    range=qdrant_models.Range(lte=event_time_to),
                ),
            )

        try:
            results = await client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=qdrant_models.Filter(must=must_conditions),
                limit=limit,
                score_threshold=score_threshold,
            )

            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "payload": r.payload,
                }
                for r in results
            ]
        except Exception as e:
            logger.exception(f"向量搜索失败: {e}")
            return []

    async def delete_paragraph(self, paragraph_id: int) -> bool:
        """删除段落向量

        Args:
            paragraph_id: 段落 ID

        Returns:
            是否成功
        """
        client = await get_qdrant_client()
        if client is None:
            return False

        try:
            await client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=[paragraph_id],
                ),
            )
            logger.debug(f"向量删除成功: paragraph_id={paragraph_id}")
            return True
        except Exception as e:
            logger.exception(f"向量删除失败: {e}")
            return False

    async def delete_by_workspace(self, workspace_id: int) -> bool:
        """删除工作区所有向量（工作区清理时使用）

        Args:
            workspace_id: 工作区 ID

        Returns:
            是否成功
        """
        client = await get_qdrant_client()
        if client is None:
            return False

        try:
            await client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="workspace_id",
                                match=qdrant_models.MatchValue(value=workspace_id),
                            ),
                        ],
                    ),
                ),
            )
            logger.info(f"工作区 {workspace_id} 的所有向量已删除")
            return True
        except Exception as e:
            logger.exception(f"删除工作区向量失败: {e}")
            return False

    async def get_collection_info(self) -> dict[str, Any] | None:
        """获取 Collection 信息（用于监控）"""
        client = await get_qdrant_client()
        if client is None:
            return None

        try:
            info = await client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status.name,
            }
        except Exception as e:
            logger.exception(f"获取 Collection 信息失败: {e}")
            return None

    async def rebuild_collection(self, batch_size: int = 50) -> dict[str, int]:
        """重建记忆库 Qdrant 索引"""
        client = await get_qdrant_client()
        if client is None:
            raise RuntimeError("Qdrant 客户端不可用")

        dimension = get_memory_embedding_dimension()
        collections = await client.get_collections()
        existing_names = [collection.name for collection in collections.collections]

        if self.collection_name in existing_names:
            await client.delete_collection(collection_name=self.collection_name)
            logger.info(f"已删除现有记忆 Collection: {self.collection_name}")

        await client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=dimension,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        logger.info(f"已创建记忆 Collection: {self.collection_name} (dimension={dimension})")

        paragraphs = await DBMemParagraph.all().order_by("id")
        total_count = len(paragraphs)
        success_count = 0
        error_count = 0
        skipped_count = 0
        points: list[qdrant_models.PointStruct] = []

        for paragraph in paragraphs:
            content = paragraph.content.strip()
            if not content:
                skipped_count += 1
                continue

            try:
                embedding = await embed_text(content)
                points.append(
                    qdrant_models.PointStruct(
                        id=paragraph.id,
                        vector=embedding,
                        payload=paragraph.to_qdrant_payload(),
                    ),
                )
                paragraph.embedding_ref = str(paragraph.id)
                await paragraph.save(update_fields=["embedding_ref", "update_time"])
                success_count += 1

                if len(points) >= batch_size:
                    await self._upsert_points_with_retry(points)
                    points = []

            except Exception as e:
                logger.warning(f"重建记忆索引失败: paragraph_id={paragraph.id}, error={e}")
                error_count += 1

        if points:
            await self._upsert_points_with_retry(points)

        self._initialized = True
        return {
            "total": total_count,
            "success": success_count,
            "error": error_count,
            "skipped": skipped_count,
            "dimension": dimension,
        }


# 全局单例
memory_qdrant_manager = MemoryQdrantManager()
