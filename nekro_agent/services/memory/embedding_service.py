"""Embedding 服务

提供文本向量化功能，复用项目现有的 OpenAI 兼容 API。
"""

import asyncio
from typing import Any

import httpx

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.services.agent.openai import gen_openai_embeddings

logger = get_sub_logger("memory.embedding")

# 默认配置
DEFAULT_EMBEDDING_MODEL_GROUP = "text-embedding"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1.0


def get_memory_embedding_dimension() -> int:
    """获取记忆系统当前配置的 embedding 维度"""
    return max(1, int(getattr(config, "MEMORY_EMBEDDING_DIMENSION", 1024)))


class EmbeddingService:
    """Embedding 服务

    封装向量化调用，提供重试机制和批量处理能力。
    """

    def __init__(
        self,
        model_group: str = DEFAULT_EMBEDDING_MODEL_GROUP,
        dimension: int | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.model_group = model_group
        self.dimension = dimension
        self.timeout = timeout

    @property
    def resolved_dimension(self) -> int:
        """解析当前应使用的 embedding 维度"""
        return self.dimension if self.dimension is not None else get_memory_embedding_dimension()

    def _get_model_config(self) -> dict[str, Any]:
        """获取模型配置"""
        try:
            model_info = config.get_model_group_info(self.model_group)
            return {
                "model": model_info.CHAT_MODEL,
                "api_key": model_info.API_KEY,
                "base_url": model_info.BASE_URL,
            }
        except Exception as e:
            logger.error(f"获取 Embedding 模型配置失败: {e}")
            raise ValueError(f"Embedding 模型组 '{self.model_group}' 配置无效") from e

    async def embed_text(self, text: str) -> list[float]:
        """生成单条文本的向量

        Args:
            text: 输入文本

        Returns:
            向量列表

        Raises:
            ValueError: 模型配置无效或向量维度不匹配
            Exception: API 调用失败
        """
        if not text or not text.strip():
            raise ValueError("输入文本不能为空")

        model_config = self._get_model_config()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                embedding = await gen_openai_embeddings(
                    model=model_config["model"],
                    input=text.strip(),
                    dimensions=self.resolved_dimension,
                    api_key=model_config["api_key"],
                    base_url=model_config["base_url"],
                    timeout=self.timeout,
                )

                # 验证维度
                if len(embedding) != self.resolved_dimension:
                    logger.warning(
                        f"向量维度不匹配: 期望 {self.resolved_dimension}, 实际 {len(embedding)}",
                    )

                logger.debug(f"文本向量化成功: {text[:30]}... -> {len(embedding)}维")
                return embedding

            except httpx.HTTPStatusError as e:
                last_error = e
                response_preview = e.response.text[:300] if e.response is not None else ""
                logger.warning(
                    f"Embedding 请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): "
                    f"status={e.response.status_code if e.response else 'unknown'} "
                    f"model={model_config['model']} dimension={self.resolved_dimension} "
                    f"detail={response_preview}",
                )
                if e.response is not None and e.response.status_code < 500:
                    break
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            except Exception as e:
                last_error = e
                logger.warning(f"Embedding 请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))

        raise last_error or Exception("Embedding 请求失败")

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 10,
    ) -> list[list[float] | None]:
        """批量生成文本向量

        Args:
            texts: 文本列表
            batch_size: 并发批次大小

        Returns:
            向量列表（失败的位置为 None）
        """
        results: list[list[float] | None] = [None] * len(texts)

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            tasks = [self.embed_text(t) for t in batch]

            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"批量 Embedding 第 {i + j} 条失败: {result}")
                        results[i + j] = None
                    else:
                        results[i + j] = result
            except Exception as e:
                logger.exception(f"批量 Embedding 失败: {e}")

        success_count = sum(1 for r in results if r is not None)
        logger.info(f"批量 Embedding 完成: {success_count}/{len(texts)} 成功")
        return results

    async def compute_similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        """计算两个文本的语义相似度

        Args:
            text1: 文本 1
            text2: 文本 2

        Returns:
            余弦相似度 (0-1)
        """
        emb1, emb2 = await asyncio.gather(
            self.embed_text(text1),
            self.embed_text(text2),
        )
        return self._cosine_similarity(emb1, emb2)

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


# 全局单例
embedding_service = EmbeddingService()


async def embed_text(text: str) -> list[float]:
    """便捷函数：生成文本向量"""
    return await embedding_service.embed_text(text)


async def embed_batch(texts: list[str]) -> list[list[float] | None]:
    """便捷函数：批量生成文本向量"""
    return await embedding_service.embed_batch(texts)
