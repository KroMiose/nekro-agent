"""知识库 Rerank 服务（OpenAI 兼容 /v1/rerank 接口）

复用项目现有的 openai SDK 客户端与模型组配置，支持 SiliconFlow / Jina 等
提供 /v1/rerank 端点的服务，用于对检索候选进行相关性二次打分。

未配置 KB_RERANK_MODEL_GROUP 时调用方应捕获 ValueError 并跳过重排。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
from openai import APIStatusError, AsyncOpenAI

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.services.agent.openai import _OPENAI_BASE_URL, _create_http_client

logger = get_sub_logger("kb.rerank")

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1.0


@dataclass(frozen=True)
class RerankResult:
    """单条重排结果"""

    index: int  # 在输入 documents 中的原始下标
    score: float  # 相关性分数（服务端归一化范围，通常 0~1）


def get_kb_rerank_model_group() -> str:
    """获取知识库重排模型组名（可能为空字符串，表示未配置）"""
    return config.KB_RERANK_MODEL_GROUP.strip()


def get_kb_rerank_endpoint() -> str:
    """获取 rerank 接口路径（相对 BASE_URL，默认 /rerank；阿里云百炼为 /reranks）"""
    return config.KB_RERANK_ENDPOINT.strip() or "/rerank"


def validate_rerank_model_group() -> str:
    """校验知识库重排模型组存在且类型正确，返回模型组名。

    Raises:
        ValueError: 未配置或模型组不存在 / 类型不是 rerank
    """
    group_name = get_kb_rerank_model_group()
    if not group_name:
        raise ValueError("知识库重排模型组未配置")

    try:
        model_group = config.get_model_group_info(group_name)
    except KeyError as e:
        raise ValueError(f"知识库重排模型组 '{group_name}' 不存在") from e

    if model_group.MODEL_TYPE != "rerank":
        raise ValueError(
            f"知识库重排模型组 '{group_name}' 类型不是 rerank，当前为 {model_group.MODEL_TYPE}",
        )

    return group_name


def _get_model_config(group_name: str) -> dict[str, str]:
    """获取模型组的请求参数"""
    model_group = config.get_model_group_info(group_name)
    return {
        "model": model_group.CHAT_MODEL,
        "api_key": model_group.API_KEY,
        "base_url": model_group.BASE_URL,
        "proxy_url": model_group.CHAT_PROXY or "",
    }


async def rerank(
    query: str,
    documents: list[str],
    top_n: int | None = None,
) -> list[RerankResult]:
    """对候选文档执行相关性重排（OpenAI 兼容 /v1/rerank）。

    Args:
        query: 查询文本
        documents: 候选文档列表（最多可传数百条，具体上限取决于服务）
        top_n: 只返回得分最高的前 N 条（不传则由服务端决定）

    Returns:
        按相关性降序排列的重排结果（原始下标 + 分数）

    Raises:
        ValueError: 重排模型组未配置 / 配置无效
    """
    group_name = validate_rerank_model_group()
    model_config = _get_model_config(group_name)
    payload: dict[str, object] = {
        "model": model_config["model"],
        "query": query,
        "documents": documents,
    }
    if top_n is not None:
        payload["top_n"] = top_n

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            async with (
                _create_http_client(
                    proxy_url=model_config["proxy_url"] or None,
                    read_timeout=DEFAULT_TIMEOUT,
                    write_timeout=DEFAULT_TIMEOUT,
                ) as http_client,
                AsyncOpenAI(
                    api_key=model_config["api_key"].strip() or None,
                    base_url=model_config["base_url"] or _OPENAI_BASE_URL,
                    http_client=http_client,
                    max_retries=0,
                ) as client,
            ):
                response = await client.post(
                    get_kb_rerank_endpoint(),
                    cast_to=httpx.Response,
                    body=payload,
                )

            data = response.json()
            raw_results = data.get("results", []) if isinstance(data, dict) else []
            results = [
                RerankResult(
                    index=int(item["index"]),
                    score=float(item.get("relevance_score", 0.0)),
                )
                for item in raw_results
                if isinstance(item, dict) and "index" in item
            ]
            results.sort(key=lambda item: item.score, reverse=True)
            if top_n is not None:
                # 服务端可能不严格遵守 top_n，本地兜底截断
                results = results[:top_n]
            logger.debug(
                f"知识库重排完成: query={query[:30]}..., candidates={len(documents)}, "
                f"returned={len(results)}",
            )
            return results

        except APIStatusError as e:
            last_error = e
            logger.warning(
                f"Rerank 请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): "
                f"status={e.status_code} detail={e.response.text[:300] if e.response else ''}",
            )
            if e.status_code < 500:
                break
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        except Exception as e:
            last_error = e
            logger.warning(f"Rerank 请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))

    raise last_error or Exception("Rerank 请求失败")
