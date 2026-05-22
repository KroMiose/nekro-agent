from nekro_agent.schemas.errors import ConfigInvalidError
from nekro_agent.services.memory.embedding_service import ensure_kb_embedding_available


def ensure_kb_embedding_configured() -> None:
    """确保知识库 embedding 配置可用，否则抛出统一配置错误。"""
    try:
        ensure_kb_embedding_available()
    except ValueError as e:
        raise ConfigInvalidError(
            key="KB_EMBEDDING_MODEL_GROUP",
            reason=f"{e}，暂不允许创建、上传或重建知识库索引",
        ) from e
