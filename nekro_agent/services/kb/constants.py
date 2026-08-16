"""知识库批量操作共享常量（从集中配置读取，修改后需重启服务生效）。"""

from nekro_agent.core.config import config

# 批量操作单请求上限（删除/解绑/重建索引共用）
KB_BATCH_MAX_SIZE = max(1, int(config.KB_BATCH_MAX_SIZE))
# 批量操作服务端并发数
KB_BATCH_CONCURRENCY = max(1, int(config.KB_BATCH_CONCURRENCY))
