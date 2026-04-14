from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import Field

from nekro_agent.schemas.i18n import SupportedLang, i18n_text, set_system_lang

from .core_utils import ConfigBase, ExtraField
from .os_env import OsEnv

CONFIG_DIR = Path(OsEnv.DATA_DIR) / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = Path(OsEnv.DATA_DIR) / "configs" / "nekro-agent.yaml"
CHANNEL_CONFIG_DIR = CONFIG_DIR / "channels"
CHANNEL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class ModelConfigGroup(ConfigBase):
    """模型配置组"""

    GROUP_NAME: str = Field(default="", title="模型组名称")
    CHAT_MODEL: str = Field(default="", title="聊天模型名称")
    CHAT_PROXY: str = Field(default="", title="聊天模型访问代理")
    BASE_URL: str = Field(default="", title="聊天模型 API 地址")
    API_KEY: str = Field(default="", title="聊天模型 API 密钥")
    MODEL_TYPE: Literal["chat", "embedding", "draw"] = Field(
        default="chat",
        title="模型类型",
        description="模型的用途类型，可以是聊天(chat)、向量嵌入(embedding)或绘图(draw)",
    )
    ENABLE_VISION: bool = Field(
        default=False,
        title="启用视觉功能",
        description="是否启用视觉能力，如果模型不支持请关闭此选项",
    )
    ENABLE_COT: bool = Field(
        default=False,
        title="启用外置思维链",
        description="启用后会强制 AI 在回答前输出思考过程，可以在一定程度提高回复质量，如果模型原生支持思维链请关闭此选项",
    )
    TOKEN_INPUT_RATE: float = Field(default=1.0, title="输入 Token 倍率")
    TOKEN_COMPLETION_RATE: float = Field(default=1.0, title="补全 Token 倍率")
    MODEL_PRICE_RATE: float = Field(default=1.0, title="模型价格倍率")
    TEMPERATURE: Optional[float] = Field(default=None, title="温度值")
    TOP_P: Optional[float] = Field(default=None, title="Top P")
    TOP_K: Optional[int] = Field(default=None, title="Top K")
    PRESENCE_PENALTY: Optional[float] = Field(default=None, title="提示重复惩罚")
    FREQUENCY_PENALTY: Optional[float] = Field(default=None, title="补全重复惩罚")
    EXTRA_BODY: Optional[str] = Field(default=None, title="额外参数 (JSON)")


class CoreConfig(ConfigBase):
    """核心配置"""

    SYSTEM_LANG: Literal["zh-CN", "en-US"] = Field(
        default="zh-CN",
        title="系统语言",
        description="系统默认语言，影响命令响应等文本的语言",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="系统语言",
                en_US="System Language",
            ),
            i18n_description=i18n_text(
                zh_CN="系统默认语言，影响命令响应等文本的语言 (zh-CN / en-US)",
                en_US="Default system language for command responses and other text (zh-CN / en-US)",
            ),
        ).model_dump(),
    )

    """Nekro Cloud 云服务配置"""
    ENABLE_NEKRO_CLOUD: bool = Field(
        default=True,
        title="启用 NekroAI 云服务",
        description=(
            "是否启用 NekroAI 云服务，启用后可使用 NekroAI 提供的云服务共享能力，同时会收集并上报一些应用使用统计信息。"
            "敏感数据将经过不可逆摘要处理后仅用于统计分析，收集过程实现逻辑均公开开源，不包含任何具体用户/聊天/频道/代码执行等隐私信息！"
        ),
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="启用 NekroAI 云服务",
                en_US="Enable NekroAI Cloud Service",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后可使用 NekroAI 提供的云服务共享能力，同时会收集并上报一些应用使用统计信息。敏感数据将经过不可逆摘要处理后仅用于统计分析。",
                en_US="When enabled, you can use cloud services provided by NekroAI. Some usage statistics will be collected and reported. Sensitive data will be processed with irreversible hashing for statistical analysis only.",
            ),
        ).model_dump(),
    )
    NEKRO_CLOUD_API_KEY: str = Field(
        default="",
        title="NekroAI 云服务 API Key",
        description="NekroAI 云服务 API Key，可前往 <a href='https://cloud.nekro.ai/me'>NekroAI 社区</a> 获取",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            is_secret=True,
            placeholder="nk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            i18n_title=i18n_text(
                zh_CN="NekroAI 云服务 API Key",
                en_US="NekroAI Cloud Service API Key",
            ),
            i18n_description=i18n_text(
                zh_CN="NekroAI 云服务 API Key，可前往 <a href='https://cloud.nekro.ai/me' target='_blank' rel='noopener noreferrer'>NekroAI 社区</a> 获取",
                en_US="NekroAI Cloud Service API Key, get it from <a href='https://cloud.nekro.ai/me' target='_blank' rel='noopener noreferrer'>NekroAI Community</a>",
            ),
        ).model_dump(),
    )
    ENSURE_SFW_CONTENT: bool = Field(
        default=True,
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )

    """应用配置"""
    APP_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        title="应用日志级别",
        description="应用日志级别，需要重启应用后生效",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="应用日志级别",
                en_US="Application Log Level",
            ),
            i18n_description=i18n_text(
                zh_CN="应用日志级别，需要重启应用后生效",
                en_US="Application log level, requires restart to take effect",
            ),
        ).model_dump(),
    )
    SUPER_USERS: List[str] = Field(
        default=[],
        title="管理员列表",
        description="此处指定的管理员用户可在 OneBot V11 适配器频道中使用指令 (填写 QQ 号)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="管理员列表",
                en_US="Administrator List",
            ),
            i18n_description=i18n_text(
                zh_CN="此处指定的管理员用户可在 OneBot V11 适配器频道中使用指令 (填写 QQ 号)",
                en_US="Administrators specified here can use commands in the OneBot V11 adapter channel (fill in QQ number)",
            ),
        ).model_dump(),
    )
    COMMAND_ENABLED: bool = Field(
        default=True,
        title="全局命令开关",
        description="全局关闭后所有适配器不再处理命令",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="全局命令开关",
                en_US="Global Command Switch",
            ),
            i18n_description=i18n_text(
                zh_CN="全局关闭后所有适配器不再处理命令",
                en_US="When disabled, all adapters will stop processing commands",
            ),
        ).model_dump(),
    )
    COMMAND_MATCH_ALLOW_HYPHEN_FOR_UNDERSCORE: bool = Field(
        default=True,
        title="命令匹配允许连字符代替下划线",
        description="启用后，命令名匹配时会将连字符视为下划线，输入 cc-help 时可匹配 cc_help",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="命令匹配允许连字符代替下划线",
                en_US="Allow Hyphen Instead of Underscore in Command Matching",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后，命令名匹配时会将连字符视为下划线，输入 cc-help 时可匹配 cc_help",
                en_US="When enabled, command matching treats hyphens as underscores, so cc-help can match cc_help",
            ),
        ).model_dump(),
    )
    DEBUG_IN_CHAT: bool = Field(
        default=False,
        title="聊天调试模式",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="聊天调试模式",
                en_US="Chat Debug Mode",
            ),
        ).model_dump(),
    )
    SAVE_PROMPTS_LOG: bool = Field(
        default=False,
        title="保存聊天提示词生成日志",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="保存聊天提示词生成日志",
                en_US="Save Chat Prompt Generation Log",
            ),
        ).model_dump(),
    )
    MAX_UPLOAD_SIZE_MB: int = Field(
        default=10,
        title="上传文件大小限制 (MB)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="上传文件大小限制 (MB)",
                en_US="Upload File Size Limit (MB)",
            ),
        ).model_dump(),
    )
    ENABLE_COMMAND_UNAUTHORIZED_OUTPUT: bool = Field(
        default=False,
        title="启用未授权命令反馈",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="启用未授权命令反馈",
                en_US="Enable Unauthorized Command Feedback",
            ),
        ).model_dump(),
    )
    DEFAULT_PROXY: str = Field(
        default="",
        title="系统级默认代理地址",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="代理配置",
                en_US="Proxy Configuration",
            ),
            placeholder="例: http://127.0.0.1:7890",
            i18n_title=i18n_text(
                zh_CN="系统级默认代理地址",
                en_US="System Default Proxy URL",
            ),
            i18n_description=i18n_text(
                zh_CN="系统级功能使用的默认代理地址，不影响模型组代理；需包含协议头，例如 http:// 或 socks5://",
                en_US="Default proxy URL used by system-level features, without affecting model-group proxies; must include a scheme such as http:// or socks5://",
            ),
        ).model_dump(),
    )
    DEFAULT_PROXY_USERNAME: str = Field(
        default="",
        title="系统级代理用户名",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="代理配置",
                en_US="Proxy Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="系统级代理用户名",
                en_US="System Proxy Username",
            ),
            i18n_description=i18n_text(
                zh_CN="可选。系统级代理认证用户名，仅对接入系统级代理管理的功能生效",
                en_US="Optional. Username for system-level proxy authentication, effective only for features using the system proxy manager",
            ),
        ).model_dump(),
    )
    DEFAULT_PROXY_PASSWORD: str = Field(
        default="",
        title="系统级代理密码",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_category=i18n_text(
                zh_CN="代理配置",
                en_US="Proxy Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="系统级代理密码",
                en_US="System Proxy Password",
            ),
            i18n_description=i18n_text(
                zh_CN="可选。系统级代理认证密码，仅对接入系统级代理管理的功能生效",
                en_US="Optional. Password for system-level proxy authentication, effective only for features using the system proxy manager",
            ),
        ).model_dump(),
    )
    MEMORY_ENABLE_SYSTEM: bool = Field(
        default=False,
        title="启用记忆系统",
        description="控制记忆系统的自动运行主链路。关闭后将停止自动沉淀、自动检索注入、CC 记忆握手、自动恢复与后台维护；已存在的记忆数据不会被删除，只读观测与少数显式手动维护功能仍可使用",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="启用记忆系统", en_US="Enable Memory System"),
            i18n_description=i18n_text(
                zh_CN="控制记忆系统的自动运行主链路。关闭后将停止自动沉淀、自动检索注入、CC 记忆握手、自动恢复与后台维护；已存在的记忆数据不会被删除，只读观测与少数显式手动维护功能仍可使用",
                en_US="Controls the automatic memory pipeline. When disabled, automatic consolidation, retrieval injection, CC memory handshake, automatic recovery, and background maintenance stop; existing memory data is kept, while read-only inspection and a few explicit manual maintenance actions remain available",
            ),
        ).model_dump(),
    )
    MEMORY_CONTEXT_MAX_LENGTH: int = Field(
        default=1200,
        title="记忆上下文最大长度",
        description="记忆系统注入到 Agent 提示词中的最大字符长度。值越大，Agent 可参考的记忆越多，但也会占用更多上下文窗口",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="记忆上下文最大长度", en_US="Memory Context Max Length"),
            i18n_description=i18n_text(
                zh_CN="记忆系统注入到 Agent 提示词中的最大字符长度。值越大，Agent 可参考的记忆越多，但也会占用更多上下文窗口",
                en_US="Maximum character length of memory context injected into the Agent prompt. Larger values allow more memory context but consume more prompt window",
            ),
        ).model_dump(),
    )
    MEMORY_ENABLE_ENHANCED_RETRIEVAL: bool = Field(
        default=False,
        title="启用增强记忆检索",
        description="启用后会先使用专门的模型根据最近上下文生成结构化记忆检索条件，再执行记忆检索；模型不可用或输出异常时会自动回退到规则检索",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="启用增强记忆检索", en_US="Enable Enhanced Memory Retrieval"),
            i18n_description=i18n_text(
                zh_CN="启用后会先使用专门的模型根据最近上下文生成结构化记忆检索条件，再执行记忆检索；模型不可用或输出异常时会自动回退到规则检索",
                en_US="When enabled, a dedicated model first generates a structured memory retrieval plan from recent context before retrieval. It automatically falls back to rule-based retrieval when the model is unavailable or returns invalid output",
            ),
        ).model_dump(),
    )
    MEMORY_ENHANCED_RETRIEVAL_MODEL_GROUP: str = Field(
        default="",
        title="增强记忆检索模型组",
        description="用于增强记忆检索规划的聊天模型组。留空时回退到默认聊天模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            ref_model_groups=True,
            model_type="chat",
            i18n_title=i18n_text(zh_CN="增强记忆检索模型组", en_US="Enhanced Memory Retrieval Model Group"),
            i18n_description=i18n_text(
                zh_CN="用于增强记忆检索规划的聊天模型组。留空时回退到默认聊天模型组",
                en_US="Chat model group used for enhanced memory retrieval planning. Falls back to the default chat model group when empty",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_MODEL_GROUP: str = Field(
        default="default",
        title="情景沉淀模型组",
        description="用于情景记忆沉淀提取的模型组名称。留空时回退到默认聊天模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            ref_model_groups=True,
            model_type="chat",
            i18n_title=i18n_text(zh_CN="情景沉淀模型组", en_US="Memory Consolidation Model Group"),
            i18n_description=i18n_text(
                zh_CN="用于情景记忆沉淀提取的模型组名称。留空时回退到默认聊天模型组",
                en_US="Model group for episodic memory consolidation. Falls back to the default chat model group when empty",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_FALLBACK_MODEL_GROUP: str = Field(
        default="",
        title="情景沉淀备用模型组",
        description="当情景记忆沉淀在最后一次解析重试时，切换使用的备用模型组。留空时回退到情景沉淀主模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            ref_model_groups=True,
            model_type="chat",
            i18n_title=i18n_text(zh_CN="情景沉淀备用模型组", en_US="Memory Consolidation Fallback Model Group"),
            i18n_description=i18n_text(
                zh_CN="当情景记忆沉淀在最后一次解析重试时，切换使用的备用模型组。留空时回退到情景沉淀主模型组",
                en_US="Fallback model group used on the final parse retry of episodic memory consolidation. Falls back to the primary consolidation model group when empty",
            ),
            placeholder="例: api-nekro-pro-2.5",
        ).model_dump(),
    )
    MEMORY_EMBEDDING_MODEL_GROUP: str = Field(
        default="text-embedding",
        title="记忆 Embedding 模型组",
        description="用于记忆系统向量化的 embedding 模型组。应选择 MODEL_TYPE 为 embedding 的模型组，并与向量维度配置保持一致",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            ref_model_groups=True,
            model_type="embedding",
            i18n_title=i18n_text(zh_CN="记忆 Embedding 模型组", en_US="Memory Embedding Model Group"),
            i18n_description=i18n_text(
                zh_CN="用于记忆系统向量化的 embedding 模型组。应选择 MODEL_TYPE 为 embedding 的模型组，并与向量维度配置保持一致",
                en_US="Embedding model group used by the memory system for vectorization. It should use a model group with MODEL_TYPE set to embedding and match the configured vector dimension",
            ),
            placeholder="例: text-embedding",
        ).model_dump(),
    )
    MEMORY_EMBEDDING_DIMENSION: int = Field(
        default=1024,
        title="记忆 Embedding 维度",
        description="记忆系统向量化使用的维度，需要与所选 embedding 模型和 Qdrant 索引保持一致",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="记忆系统",
                en_US="Memory System",
            ),
            i18n_title=i18n_text(
                zh_CN="记忆 Embedding 维度",
                en_US="Memory Embedding Dimension",
            ),
            i18n_description=i18n_text(
                zh_CN="记忆系统向量化使用的维度，需要与所选 embedding 模型和 Qdrant 索引保持一致",
                en_US="Embedding dimension used by memory system, must match the selected embedding model and Qdrant index",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_FORCE_JSON_OUTPUT: bool = Field(
        default=True,
        title="强制沉淀模型输出 JSON",
        description="为记忆沉淀请求显式附加 JSON 输出约束，降低解析失败概率。关闭后仅适用于兼容性调试场景",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="强制沉淀模型输出 JSON", en_US="Force JSON Consolidation Output"),
            i18n_description=i18n_text(
                zh_CN="为记忆沉淀请求显式附加 JSON 输出约束，降低解析失败概率",
                en_US="Explicitly request JSON output for memory consolidation to reduce parse failures",
            ),
        ).model_dump(),
    )
    MEMORY_LLM_MAX_RETRIES: int = Field(
        default=3,
        title="记忆 LLM 调用最大重试次数",
        description="记忆沉淀调用模型接口时的最大重试次数。用于处理网络抖动、上游超时或模型临时不可用",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="LLM 最大重试次数", en_US="LLM Max Retries"),
            i18n_description=i18n_text(
                zh_CN="记忆沉淀调用模型接口时的最大重试次数。用于处理网络抖动、上游超时或模型临时不可用",
                en_US="Maximum retry count for model calls during memory consolidation, used for transient network issues, upstream timeouts, or temporary model unavailability",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_PARSE_MAX_RETRIES: int = Field(
        default=2,
        title="沉淀解析最大重试次数",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="沉淀解析最大重试次数", en_US="Consolidation Parse Max Retries"),
            i18n_description=i18n_text(
                zh_CN="当 LLM 返回内容无法解析为记忆 JSON 时，重新请求的最大次数",
                en_US="Maximum number of re-requests when LLM output cannot be parsed into memory JSON",
            ),
        ).model_dump(),
    )
    MEMORY_RETRIEVAL_DEFAULT_LIMIT: int = Field(
        default=10,
        title="默认检索数量",
        description="单次记忆检索默认返回的候选数量上限。过大可能增加噪声和上下文占用，过小可能遗漏相关记忆",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="默认检索数量", en_US="Default Retrieval Limit"),
            i18n_description=i18n_text(
                zh_CN="单次记忆检索默认返回的候选数量上限。过大可能增加噪声和上下文占用，过小可能遗漏相关记忆",
                en_US="Default maximum number of candidates returned by a memory retrieval. Too large may add noise and prompt cost, too small may miss relevant memories",
            ),
        ).model_dump(),
    )
    MEMORY_RETRIEVAL_MIN_SIMILARITY: float = Field(
        default=0.5,
        title="最低相似度",
        description="向量检索的最低相似度阈值。提高该值会减少低相关记忆，降低该值会提高召回率但可能带来噪声",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="最低相似度", en_US="Minimum Similarity"),
            i18n_description=i18n_text(
                zh_CN="向量检索的最低相似度阈值。提高该值会减少低相关记忆，降低该值会提高召回率但可能带来噪声",
                en_US="Minimum similarity threshold for vector retrieval. Higher values reduce weak matches; lower values improve recall but may increase noise",
            ),
        ).model_dump(),
    )
    MEMORY_RETRIEVAL_EPISODIC_BOOST: float = Field(
        default=1.2,
        title="情景记忆加权",
        description="检索排序时对情景记忆的额外权重系数。提高后更偏向近期经历和历史事件",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="情景记忆加权", en_US="Episodic Boost"),
            i18n_description=i18n_text(
                zh_CN="检索排序时对情景记忆的额外权重系数。提高后更偏向近期经历和历史事件",
                en_US="Extra weighting factor applied to episodic memories during retrieval ranking. Higher values bias toward experiences and events",
            ),
        ).model_dump(),
    )
    MEMORY_RETRIEVAL_RECENT_BOOST_HOURS: int = Field(
        default=24,
        title="近期记忆加权窗口",
        description="在该时间窗口内的记忆会被视为近期记忆，可额外获得近期加权",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="近期记忆加权窗口", en_US="Recent Boost Hours"),
            i18n_description=i18n_text(
                zh_CN="在该时间窗口内的记忆会被视为近期记忆，可额外获得近期加权",
                en_US="Memories within this time window are treated as recent and can receive an additional ranking boost",
            ),
        ).model_dump(),
    )
    MEMORY_RETRIEVAL_RECENT_BOOST_FACTOR: float = Field(
        default=1.1,
        title="近期记忆加权倍率",
        description="用于提升近期记忆排序分数的倍率，通常与近期记忆加权窗口配合使用",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="近期记忆加权倍率", en_US="Recent Boost Factor"),
            i18n_description=i18n_text(
                zh_CN="用于提升近期记忆排序分数的倍率，通常与近期记忆加权窗口配合使用",
                en_US="Multiplier used to boost the ranking score of recent memories, usually paired with the recent boost window",
            ),
        ).model_dump(),
    )
    MEMORY_RETRIEVAL_RELATION_BOOST: float = Field(
        default=1.05,
        title="关系记忆加权",
        description="关系检索结果合并回段落候选时的额外加权系数。提高后更容易命中实体关系相关记忆",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="关系记忆加权", en_US="Relation Boost"),
            i18n_description=i18n_text(
                zh_CN="关系检索结果合并回段落候选时的额外加权系数。提高后更容易命中实体关系相关记忆",
                en_US="Extra weighting applied when relation-based matches are merged back into paragraph candidates. Higher values favor entity-relation memories",
            ),
        ).model_dump(),
    )
    MEMORY_RETRIEVAL_RELATION_MATCH_LIMIT: int = Field(
        default=20,
        title="关系匹配实体上限",
        description="单次关系补召回时允许参与匹配的实体数量上限，用于限制关系扩展成本",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="关系匹配实体上限", en_US="Relation Match Limit"),
            i18n_description=i18n_text(
                zh_CN="单次关系补召回时允许参与匹配的实体数量上限，用于限制关系扩展成本",
                en_US="Maximum number of entities considered during relation-based recall expansion, used to cap relation matching cost",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_BATCH_SIZE: int = Field(
        default=50,
        title="单次沉淀消息数",
        description="每次情景记忆沉淀最多读取的消息数量。较大值有利于形成完整片段，但会增加单批处理耗时",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="单次沉淀消息数", en_US="Consolidation Batch Size"),
            i18n_description=i18n_text(
                zh_CN="每次情景记忆沉淀最多读取的消息数量。较大值有利于形成完整片段，但会增加单批处理耗时",
                en_US="Maximum number of messages read in one episodic consolidation batch. Larger values help form fuller context but increase batch latency",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_MIN_CONTENT_LENGTH: int = Field(
        default=10,
        title="最小沉淀内容长度",
        description="当合并后的消息内容低于该长度时，跳过本次情景记忆沉淀，避免产生价值过低的记忆",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="最小沉淀内容长度", en_US="Minimum Consolidation Content Length"),
            i18n_description=i18n_text(
                zh_CN="当合并后的消息内容低于该长度时，跳过本次情景记忆沉淀，避免产生价值过低的记忆",
                en_US="Skip episodic consolidation when the merged message content is shorter than this length to avoid very low-value memories",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_MAX_SUMMARY_LENGTH: int = Field(
        default=200,
        title="沉淀摘要最大长度",
        description="情景记忆摘要字段的最大长度，用于控制数据库展示和检索摘要的体积",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="沉淀摘要最大长度", en_US="Consolidation Summary Max Length"),
            i18n_description=i18n_text(
                zh_CN="情景记忆摘要字段的最大长度，用于控制数据库展示和检索摘要的体积",
                en_US="Maximum length of the episodic memory summary field, used to control display and retrieval summary size",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_MSG_THRESHOLD: int = Field(
        default=50,
        title="沉淀消息阈值",
        description="调度器判断是否触发自动情景沉淀时使用的消息数量阈值",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="沉淀消息阈值", en_US="Consolidation Message Threshold"),
            i18n_description=i18n_text(
                zh_CN="调度器判断是否触发自动情景沉淀时使用的消息数量阈值",
                en_US="Message-count threshold used by the scheduler to decide when automatic episodic consolidation should be triggered",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_TIME_THRESHOLD_HOURS: float = Field(
        default=2.0,
        title="沉淀时间阈值",
        description="距离上次沉淀超过该时长后，即使消息数不高，也可能触发自动沉淀",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="沉淀时间阈值", en_US="Consolidation Time Threshold"),
            i18n_description=i18n_text(
                zh_CN="距离上次沉淀超过该时长后，即使消息数不高，也可能触发自动沉淀",
                en_US="If this duration has passed since the last consolidation, automatic consolidation may still be triggered even with a low message count",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_MIN_INTERVAL_SECONDS: int = Field(
        default=300,
        title="最小沉淀间隔",
        description="两次自动情景沉淀之间的最小间隔，用于避免高活跃频道被频繁打断",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="最小沉淀间隔", en_US="Minimum Consolidation Interval"),
            i18n_description=i18n_text(
                zh_CN="两次自动情景沉淀之间的最小间隔，用于避免高活跃频道被频繁打断",
                en_US="Minimum interval between automatic episodic consolidations, used to avoid over-triggering on highly active channels",
            ),
        ).model_dump(),
    )
    MEMORY_CONSOLIDATION_BATCH_COOLDOWN_SECONDS: float = Field(
        default=0.2,
        title="沉淀批次冷却间隔（秒）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="沉淀批次冷却间隔（秒）", en_US="Consolidation Batch Cooldown Seconds"),
            i18n_description=i18n_text(
                zh_CN="单个沉淀批次结束后的短暂让步时间，用于降低对其他接口响应的影响",
                en_US="Short cooldown after each consolidation batch to reduce impact on other API responses",
            ),
        ).model_dump(),
    )
    MEMORY_RELATION_HALF_LIFE_SECONDS: int = Field(
        default=86400,
        title="关系半衰期",
        description="新创建关系记忆的默认半衰期秒数。值越小，关系有效权重衰减越快",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="关系半衰期", en_US="Relation Half-Life"),
            i18n_description=i18n_text(
                zh_CN="新创建关系记忆的默认半衰期秒数。值越小，关系有效权重衰减越快",
                en_US="Default half-life in seconds for newly created relation memories. Smaller values decay relation weight faster",
            ),
        ).model_dump(),
    )
    MEMORY_SEMANTIC_HALF_LIFE_DAYS: int = Field(
        default=30,
        title="语义记忆半衰期天数",
        description="CC 语义记忆的默认半衰期天数。较长的值更适合沉淀稳定可复用的经验结论",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="语义记忆半衰期天数", en_US="Semantic Half-Life Days"),
            i18n_description=i18n_text(
                zh_CN="CC 语义记忆的默认半衰期天数。较长的值更适合沉淀稳定可复用的经验结论",
                en_US="Default half-life in days for CC semantic memories. Larger values fit stable and reusable knowledge better",
            ),
        ).model_dump(),
    )
    MEMORY_SEMANTIC_MIN_RESULT_LENGTH: int = Field(
        default=60,
        title="语义沉淀最小结果长度",
        description="CC 任务结果短于该长度时不进行语义记忆沉淀，避免将过短回复误记为长期知识",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="语义沉淀最小结果长度", en_US="Semantic Minimum Result Length"),
            i18n_description=i18n_text(
                zh_CN="CC 任务结果短于该长度时不进行语义记忆沉淀，避免将过短回复误记为长期知识",
                en_US="Do not persist CC semantic memory when the task result is shorter than this length, to avoid storing very short replies as durable knowledge",
            ),
        ).model_dump(),
    )
    MEMORY_SEMANTIC_MAX_TASK_LENGTH: int = Field(
        default=300,
        title="语义沉淀任务摘要长度",
        description="CC 任务描述在写入语义记忆前保留的最大长度，用于控制摘要和正文体积",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="语义沉淀任务摘要长度", en_US="Semantic Task Max Length"),
            i18n_description=i18n_text(
                zh_CN="CC 任务描述在写入语义记忆前保留的最大长度，用于控制摘要和正文体积",
                en_US="Maximum preserved length of the CC task description before writing semantic memory, used to control summary and content size",
            ),
        ).model_dump(),
    )
    MEMORY_SEMANTIC_MAX_RESULT_LENGTH: int = Field(
        default=4000,
        title="语义沉淀结果最大长度",
        description="CC 任务结果写入语义记忆时保留的最大长度，用于限制超长产出对存储和检索的影响",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="语义沉淀结果最大长度", en_US="Semantic Result Max Length"),
            i18n_description=i18n_text(
                zh_CN="CC 任务结果写入语义记忆时保留的最大长度，用于限制超长产出对存储和检索的影响",
                en_US="Maximum preserved length of CC task results when writing semantic memory, used to cap storage and retrieval impact of very long outputs",
            ),
        ).model_dump(),
    )
    MEMORY_SEMANTIC_MAX_SUMMARY_LENGTH: int = Field(
        default=120,
        title="语义记忆摘要最大长度",
        description="CC 语义记忆摘要字段的最大长度，主要影响列表展示和简短检索摘要",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="语义记忆摘要最大长度", en_US="Semantic Summary Max Length"),
            i18n_description=i18n_text(
                zh_CN="CC 语义记忆摘要字段的最大长度，主要影响列表展示和简短检索摘要",
                en_US="Maximum length of the CC semantic memory summary field, mainly affecting list display and short retrieval summaries",
            ),
        ).model_dump(),
    )
    MEMORY_SCHEDULER_MAX_CONCURRENT: int = Field(
        default=3,
        title="最大并发沉淀数",
        description="后台调度器同时允许执行的最大沉淀任务数。增大可提高吞吐，但也会增加资源占用",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="最大并发沉淀数", en_US="Max Concurrent Consolidations"),
            i18n_description=i18n_text(
                zh_CN="后台调度器同时允许执行的最大沉淀任务数。增大可提高吞吐，但也会增加资源占用",
                en_US="Maximum number of consolidation tasks the background scheduler may run concurrently. Larger values improve throughput but increase resource usage",
            ),
        ).model_dump(),
    )
    MEMORY_SCHEDULER_STAGGER_DELAY_SECONDS: int = Field(
        default=5,
        title="错峰调度延迟",
        description="调度器为不同工作区任务增加的基础错峰延迟，用于降低多个沉淀任务同时抢占资源的概率",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="错峰调度延迟", en_US="Stagger Delay"),
            i18n_description=i18n_text(
                zh_CN="调度器为不同工作区任务增加的基础错峰延迟，用于降低多个沉淀任务同时抢占资源的概率",
                en_US="Base stagger delay added by the scheduler across workspace tasks to reduce simultaneous resource contention",
            ),
        ).model_dump(),
    )
    MEMORY_REBUILD_LOOKBACK_DAYS: int = Field(
        default=30,
        title="记忆重建回溯天数",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="记忆重建回溯天数", en_US="Memory Rebuild Lookback Days"),
            i18n_description=i18n_text(
                zh_CN="重建工作区记忆时，默认只从当前时间往前指定天数内的聊天和委托记录开始回放；设为 0 表示不限制",
                en_US="When rebuilding workspace memory, only replay chat and delegation records within the specified number of days from now by default; set to 0 for unlimited",
            ),
        ).model_dump(),
    )
    MEMORY_PRUNE_ENABLED: bool = Field(
        default=True,
        title="启用自动记忆清理",
        description="控制后台是否定期清理低价值记忆。关闭后不会自动 prune，但手动清理仍可使用",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="启用自动记忆清理", en_US="Enable Automatic Memory Pruning"),
            i18n_description=i18n_text(
                zh_CN="控制后台是否定期清理低价值记忆。关闭后不会自动 prune，但手动清理仍可使用",
                en_US="Controls whether low-value memories are pruned periodically in the background. When disabled, automatic pruning stops but manual pruning remains available",
            ),
        ).model_dump(),
    )
    MEMORY_PRUNE_INTERVAL_HOURS: int = Field(
        default=6,
        title="自动清理间隔（小时）",
        description="后台自动记忆清理的执行间隔，仅在启用自动记忆清理时生效",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="自动清理间隔（小时）", en_US="Automatic Prune Interval (Hours)"),
            i18n_description=i18n_text(
                zh_CN="后台自动记忆清理的执行间隔，仅在启用自动记忆清理时生效",
                en_US="Execution interval for background automatic memory pruning, only effective when automatic pruning is enabled",
            ),
        ).model_dump(),
    )
    MEMORY_PRUNE_PARAGRAPH_THRESHOLD: float = Field(
        default=0.05,
        title="段落清理阈值",
        description="段落记忆有效权重低于该阈值时可被自动清理。提高该值会更激进地淘汰低价值段落",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="段落清理阈值", en_US="Paragraph Prune Threshold"),
            i18n_description=i18n_text(
                zh_CN="段落记忆有效权重低于该阈值时可被自动清理。提高该值会更激进地淘汰低价值段落",
                en_US="Paragraph memories with effective weight below this threshold may be pruned automatically. Higher values prune low-value paragraphs more aggressively",
            ),
        ).model_dump(),
    )
    MEMORY_PRUNE_RELATION_THRESHOLD: float = Field(
        default=0.03,
        title="关系清理阈值",
        description="关系记忆有效权重低于该阈值时可被自动清理。提高该值会更激进地淘汰低价值关系",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="关系清理阈值", en_US="Relation Prune Threshold"),
            i18n_description=i18n_text(
                zh_CN="关系记忆有效权重低于该阈值时可被自动清理。提高该值会更激进地淘汰低价值关系",
                en_US="Relation memories with effective weight below this threshold may be pruned automatically. Higher values prune low-value relations more aggressively",
            ),
        ).model_dump(),
    )
    MEMORY_EPISODE_ENABLED: bool = Field(
        default=True,
        title="启用 Episode 聚合",
        description="控制是否启用 episodic paragraph 到 Episode 事件的聚合能力。关闭后不再自动或手动形成 Episode",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="启用 Episode 聚合", en_US="Enable Episode Aggregation"),
            i18n_description=i18n_text(
                zh_CN="控制是否启用 episodic paragraph 到 Episode 事件的聚合能力。关闭后不再自动或手动形成 Episode",
                en_US="Controls whether episodic paragraphs can be aggregated into Episode events. When disabled, Episode creation stops for both automatic and manual flows",
            ),
        ).model_dump(),
    )
    MEMORY_EPISODE_MIN_PARAGRAPHS: int = Field(
        default=3,
        title="Episode 最小段落数",
        description="形成一个 Episode 至少需要的情景段落数量。值越大，Episode 事件会更保守",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="Episode 最小段落数", en_US="Episode Minimum Paragraphs"),
            i18n_description=i18n_text(
                zh_CN="形成一个 Episode 至少需要的情景段落数量。值越大，Episode 事件会更保守",
                en_US="Minimum number of episodic paragraphs required to form an Episode. Larger values make Episode creation more conservative",
            ),
        ).model_dump(),
    )
    MEMORY_EPISODE_TIME_GAP_MINUTES: int = Field(
        default=30,
        title="Episode 时间间隔阈值",
        description="聚合 Episode 时，相邻段落允许的最大时间间隔。超过该间隔会被视为不同事件",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="Episode 时间间隔阈值", en_US="Episode Time Gap Minutes"),
            i18n_description=i18n_text(
                zh_CN="聚合 Episode 时，相邻段落允许的最大时间间隔。超过该间隔会被视为不同事件",
                en_US="Maximum allowed time gap between adjacent paragraphs when aggregating Episodes. Larger gaps are treated as different events",
            ),
        ).model_dump(),
    )
    MEMORY_EPISODE_AUTO_CONSOLIDATE: bool = Field(
        default=True,
        title="自动 Episode 聚合",
        description="控制情景记忆沉淀后是否顺带自动尝试 Episode 聚合。关闭后仅可通过手动入口触发",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="自动 Episode 聚合", en_US="Auto Episode Consolidation"),
            i18n_description=i18n_text(
                zh_CN="控制情景记忆沉淀后是否顺带自动尝试 Episode 聚合。关闭后仅可通过手动入口触发",
                en_US="Controls whether Episode aggregation is attempted automatically after episodic consolidation. When disabled, it can only be triggered manually",
            ),
        ).model_dump(),
    )
    MEMORY_EPISODE_SCAN_LIMIT: int = Field(
        default=200,
        title="Episode 聚合扫描上限",
        description="单次 Episode 聚合扫描的最大候选段落数，用于限制聚合成本",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="Episode 聚合扫描上限", en_US="Episode Scan Limit"),
            i18n_description=i18n_text(
                zh_CN="单次 Episode 聚合扫描的最大候选段落数，用于限制聚合成本",
                en_US="Maximum number of candidate paragraphs scanned in one Episode aggregation run, used to cap aggregation cost",
            ),
        ).model_dump(),
    )
    MEMORY_STARTUP_RECOVERY_ENABLED: bool = Field(
        default=False,
        title="启动时恢复历史沉淀任务",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="启动时恢复历史沉淀任务", en_US="Recover Historical Consolidations On Startup"),
            i18n_description=i18n_text(
                zh_CN="启用后会在启动时扫描工作区历史未沉淀消息并自动补跑，可能显著占用系统资源",
                en_US="When enabled, scans and resumes historical unconsolidated messages on startup, which may significantly consume system resources",
            ),
        ).model_dump(),
    )
    MEMORY_STARTUP_RECOVERY_MAX_TASKS: int = Field(
        default=1,
        title="启动恢复最大任务数",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="启动恢复最大任务数", en_US="Startup Recovery Max Tasks"),
            i18n_description=i18n_text(
                zh_CN="限制启动时自动恢复的沉淀任务数，0 表示不限制",
                en_US="Limit the number of consolidation tasks automatically recovered on startup, 0 means unlimited",
            ),
        ).model_dump(),
    )
    MEMORY_LOG_RETENTION_DAYS: int = Field(
        default=30,
        title="强化日志保留天数",
        description="记忆强化日志在数据库中的默认保留天数。当前主要影响 reinforcement log 清理，不影响手动导出的其他故障日志文件",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="记忆系统", en_US="Memory System"),
            i18n_title=i18n_text(zh_CN="强化日志保留天数", en_US="Reinforcement Log Retention Days"),
            i18n_description=i18n_text(
                zh_CN="记忆强化日志在数据库中的默认保留天数。当前主要影响 reinforcement log 清理，不影响手动导出的其他故障日志文件",
                en_US="Default retention days for memory reinforcement logs in the database. Currently affects reinforcement-log cleanup only, not other exported failure log files",
            ),
        ).model_dump(),
    )

    """OpenAI API 配置"""
    MODEL_GROUPS: Dict[str, ModelConfigGroup] = Field(
        default={
            "default": ModelConfigGroup(
                CHAT_MODEL="gemini-2.5-flash",
                CHAT_PROXY="",
                BASE_URL="https://api.nekro.ai/v1",
                API_KEY="",
                MODEL_TYPE="chat",
                ENABLE_VISION=True,
                ENABLE_COT=True,
            ),
            "default-draw": ModelConfigGroup(
                CHAT_MODEL="Kolors",
                CHAT_PROXY="",
                BASE_URL="https://api.nekro.ai/v1",
                API_KEY="",
                MODEL_TYPE="draw",
                ENABLE_VISION=False,
                ENABLE_COT=False,
            ),
            "default-draw-chat": ModelConfigGroup(
                CHAT_MODEL="gemini-2.5-flash-image-preview",
                CHAT_PROXY="",
                BASE_URL="https://api.nekro.ai/v1",
                API_KEY="",
                MODEL_TYPE="draw",
                ENABLE_VISION=False,
                ENABLE_COT=False,
            ),
            "text-embedding": ModelConfigGroup(
                CHAT_MODEL="text-embedding-v3",
                CHAT_PROXY="",
                BASE_URL="https://api.nekro.ai/v1",
                API_KEY="",
                MODEL_TYPE="embedding",
                ENABLE_VISION=False,
                ENABLE_COT=False,
            ),
        },
        title="模型组配置",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )
    USE_MODEL_GROUP: str = Field(
        default="default",
        title="使用的主模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            ref_model_groups=True,
            required=True,
            model_type="chat",
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="使用的主模型组",
                en_US="Primary Model Group",
            ),
            i18n_description=i18n_text(
                zh_CN="主要使用的模型组，可在 '模型组' 选项卡配置",
                en_US="Primary model group to use, can be configured in 'Model Groups' tab",
            ),
        ).model_dump(),
        description="主要使用的模型组，可在 `模型组` 选项卡配置",
    )
    DEBUG_MIGRATION_MODEL_GROUP: str = Field(
        default="default",
        title="调试/Agent 迁移模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            ref_model_groups=True,
            model_type="chat",
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="调试/Agent 迁移模型组",
                en_US="Debug/Agent Migration Model Group",
            ),
            i18n_description=i18n_text(
                zh_CN="主模型组编写的代码执行出错或产生 Agent 反馈时，迭代调用时使用的模型组",
                en_US="Model group used for iterative calls when code execution fails or Agent feedback is generated",
            ),
        ).model_dump(),
        description="主模型组编写的代码执行出错或产生 Agent 反馈时，迭代调用时使用的模型组",
    )
    FALLBACK_MODEL_GROUP: str = Field(
        default="default",
        title="备用模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            ref_model_groups=True,
            model_type="chat",
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="备用模型组",
                en_US="Fallback Model Group",
            ),
            i18n_description=i18n_text(
                zh_CN="当主模型组不可用时，使用备用模型组",
                en_US="Model group used when primary model group is unavailable",
            ),
        ).model_dump(),
        description="当主模型组不可用时, 使用备用模型组",
    )

    """聊天配置"""
    AI_CHAT_DEFAULT_PRESET_ID: Optional[int] = Field(
        default=None,
        title="默认人设",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            ref_presets=True,
            ref_presets_no_default=True,
            i18n_title=i18n_text(
                zh_CN="默认人设",
                en_US="Default Preset",
            ),
            i18n_description=i18n_text(
                zh_CN="为空时使用系统内置默认人设",
                en_US="Uses built-in default preset if empty",
            ),
        ).model_dump(),
    )
    AI_CHAT_PRESET_NAME: str = Field(
        default="",
        title="默认聊天人设名 (已弃用)",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="默认聊天人设名 (已弃用)",
                en_US="Default Chat Preset Name (Deprecated)",
            ),
            i18n_description=i18n_text(
                zh_CN="已弃用，请使用「默认人设 ID」代替",
                en_US="Deprecated, please use 'Default Preset ID' instead",
            ),
        ).model_dump(),
    )
    AI_CHAT_PRESET_SETTING: str = Field(
        default="",
        title="默认聊天人设详情 (已弃用)",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            is_textarea=True,
            i18n_title=i18n_text(
                zh_CN="默认聊天人设详情 (已弃用)",
                en_US="Default Chat Preset Details (Deprecated)",
            ),
            i18n_description=i18n_text(
                zh_CN="已弃用，请使用「默认人设 ID」代替",
                en_US="Deprecated, please use 'Default Preset ID' instead",
            ),
        ).model_dump(),
    )
    AI_CHAT_CONTEXT_EXPIRE_SECONDS: int = Field(
        default=60 * 30,
        title="对话上下文过期时间 (秒)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="对话上下文过期时间 (秒)",
                en_US="Context Expiration Time (seconds)",
            ),
            i18n_description=i18n_text(
                zh_CN="超出该时间范围的消息不会被 AI 回复时参考",
                en_US="Messages older than this will not be referenced by AI",
            ),
        ).model_dump(),
        description="超出该时间范围的消息不会被 AI 回复时参考",
    )
    AI_CHAT_CONTEXT_MAX_LENGTH: int = Field(
        default=32,
        title="对话上下文最大条数",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="对话上下文最大条数",
                en_US="Max Context Message Count",
            ),
            i18n_description=i18n_text(
                zh_CN="AI 对话上下文最大条数，超出该条数会自动截断",
                en_US="Maximum number of context messages, exceeding this will be truncated",
            ),
        ).model_dump(),
        description="AI 对话上下文最大条数, 超出该条数会自动截断",
    )
    AI_SCRIPT_MAX_RETRY_TIMES: int = Field(
        default=3,
        title="代码执行调试 / Agent 迭代最大次数",
        description="执行代码过程出错或者产生 Agent 反馈时，进行迭代调用允许的最大次数，增大该值可能略微增加调试成功概率，过大会造成响应时间增加、Token 消耗增加等",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="代码执行调试 / Agent 迭代最大次数",
                en_US="Max Code Debug / Agent Iteration Times",
            ),
            i18n_description=i18n_text(
                zh_CN="执行代码过程出错或产生 Agent 反馈时，进行迭代调用允许的最大次数",
                en_US="Maximum iterations when code execution fails or Agent feedback is generated",
            ),
        ).model_dump(),
    )
    AI_CHAT_LLM_API_MAX_RETRIES: int = Field(
        default=3,
        title="模型 API 调用重试次数",
        description="模型组调用失败后重试次数，重试的最后一次将使用备用模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="模型 API 调用重试次数",
                en_US="Model API Retry Count",
            ),
            i18n_description=i18n_text(
                zh_CN="模型组调用失败后重试次数，重试的最后一次将使用备用模型组",
                en_US="Retry count after model call failure, last retry will use fallback model group",
            ),
        ).model_dump(),
    )
    AI_DEBOUNCE_WAIT_SECONDS: float = Field(
        default=0.9,
        title="防抖等待时长 (秒)",
        description="收到触发消息时延迟指定时长再开始回复流程，防抖等待时长中继续收到的消息只会触发最后一条",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="防抖等待时长 (秒)",
                en_US="Debounce Wait Time (seconds)",
            ),
            i18n_description=i18n_text(
                zh_CN="收到触发消息时延迟指定时长再开始回复流程，防抖等待时长中继续收到的消息只会触发最后一条",
                en_US="Delay before starting reply process, only last message received during debounce will trigger",
            ),
        ).model_dump(),
    )
    AI_GENERATE_TIMEOUT: int = Field(
        default=180,
        title="AI 对话内容生成超时时间 (秒)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="AI 对话内容生成超时时间 (秒)",
                en_US="AI Response Generation Timeout (seconds)",
            ),
            i18n_description=i18n_text(
                zh_CN="AI 大模型生成响应结果的最大等待时间，超过该时间会自动停止生成并报错",
                en_US="Maximum wait time for AI response generation, will stop and error if exceeded",
            ),
        ).model_dump(),
        description="AI 大模型生成响应结果的最大等待时间，超过该时间会自动停止生成并报错",
    )
    AI_IGNORED_PREFIXES: List[str] = Field(
        default=["#", "＃", "[Debug]", "[Opt Output]", "≡NA≡"],
        title="忽略的消息前缀",
        description="带有这些前缀的消息不会被参考或者触发",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            sub_item_name="前缀",
            i18n_title=i18n_text(
                zh_CN="忽略的消息前缀",
                en_US="Ignored Message Prefixes",
            ),
            i18n_description=i18n_text(
                zh_CN="带有这些前缀的消息不会被参考或者触发",
                en_US="Messages with these prefixes will not be referenced or triggered",
            ),
        ).model_dump(),
    )
    AI_COMMAND_OUTPUT_PREFIX: str = Field(
        default="≡NA≡:",
        title="命令输出前缀",
        description="命令输出前缀，用于标识命令输出",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="命令输出前缀",
                en_US="Command Output Prefix",
            ),
            i18n_description=i18n_text(
                zh_CN="命令输出前缀，用于标识命令输出",
                en_US="Prefix for command output identification",
            ),
        ).model_dump(),
    )
    AI_CHAT_DAILY_REPLY_LIMIT: int = Field(
        default=0,
        title="每日回复数量限制",
        description="每个频道每日 AI 回复数量上限，0 表示不限制",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="回复配额",
                en_US="Reply Quota",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="每日回复数量限制",
                en_US="Daily Reply Limit",
            ),
            i18n_description=i18n_text(
                zh_CN="每个频道每日 AI 回复数量上限，0 表示不限制",
                en_US="Maximum AI replies per channel per day, 0 = unlimited",
            ),
        ).model_dump(),
    )
    AI_CHAT_ENABLE_HOURLY_LIMIT: bool = Field(
        default=False,
        title="启用每小时限额",
        description="启用后将根据每日限额自动计算每小时回复上限，使回复更均匀分布",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="回复配额",
                en_US="Reply Quota",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="启用每小时限额",
                en_US="Enable Hourly Limit",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后将根据每日限额自动计算每小时回复上限，使回复更均匀分布",
                en_US="Auto-calculate hourly reply limit from daily limit for even distribution",
            ),
        ).model_dump(),
    )
    AI_CHAT_QUOTA_WHITELIST_USERS: List[str] = Field(
        default=[],
        title="配额白名单用户",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="回复配额", en_US="Reply Quota"),
            i18n_title=i18n_text(zh_CN="配额白名单用户", en_US="Quota Whitelist Users"),
            i18n_description=i18n_text(
                zh_CN="列表中的用户（sender_id）发送的消息不受每日/每小时配额限制",
                en_US="Messages from users (sender_id) in this list bypass quota limits",
            ),
        ).model_dump(),
    )
    AI_CHAT_QUOTA_SUPER_USERS_EXEMPT: bool = Field(
        default=True,
        title="管理员不受配额限制",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="回复配额", en_US="Reply Quota"),
            i18n_title=i18n_text(zh_CN="管理员不受配额限制", en_US="Super Users Exempt from Quota"),
            i18n_description=i18n_text(
                zh_CN="启用后，SUPER_USERS 中的管理员发送的消息不受配额限制",
                en_US="When enabled, messages from SUPER_USERS bypass quota limits",
            ),
        ).model_dump(),
    )
    AI_CHAT_RANDOM_REPLY_PROBABILITY: float = Field(
        default=0.0,
        title="随机回复概率",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="随机回复概率",
                en_US="Random Reply Probability",
            ),
            i18n_description=i18n_text(
                zh_CN="随机回复概率，任意消息触发 AI 回复的概率，0.0 表示不启用，1.0 表示必定触发",
                en_US="Probability of AI replying to any message, 0.0 = disabled, 1.0 = always",
            ),
        ).model_dump(),
        description="随机回复概率，任意消息触发 AI 回复的概率，0.0 表示不启用，1.0 表示必定触发",
    )
    AI_CHAT_TRIGGER_REGEX: List[str] = Field(
        default=[],
        title="触发正则表达式",
        description="触发正则表达式，当消息匹配到正则表达式时，会触发 AI 回复",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            sub_item_name="表达式",
            i18n_title=i18n_text(
                zh_CN="触发正则表达式",
                en_US="Trigger Regex Patterns",
            ),
            i18n_description=i18n_text(
                zh_CN="当消息匹配到这些正则表达式时，会触发 AI 回复",
                en_US="AI will reply when message matches these regex patterns",
            ),
        ).model_dump(),
    )
    AI_CHAT_IGNORE_REGEX: List[str] = Field(
        default=[],
        title="忽略正则表达式",
        description="忽略正则表达式，当消息匹配到正则表达式时，不会触发 AI 回复",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            sub_item_name="表达式",
            i18n_title=i18n_text(
                zh_CN="忽略正则表达式",
                en_US="Ignore Regex Patterns",
            ),
            i18n_description=i18n_text(
                zh_CN="当消息匹配到这些正则表达式时，不会触发 AI 回复",
                en_US="AI will not reply when message matches these regex patterns",
            ),
        ).model_dump(),
    )
    AI_RESPONSE_PRE_DROP_REGEX: List[str] = Field(
        default=[],
        title="AI 响应预处理丢弃正则表达式",
        description="使用正则表达式匹配 AI 预响应结果，丢弃匹配到的内容段再执行后续思维链解析、代码解析等内容",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            sub_item_name="表达式",
            i18n_title=i18n_text(
                zh_CN="AI 响应预处理丢弃正则表达式",
                en_US="AI Response Pre-Drop Regex",
            ),
            i18n_description=i18n_text(
                zh_CN="匹配 AI 预响应结果，丢弃匹配到的内容段再执行后续解析",
                en_US="Match and drop content from AI pre-response before further parsing",
            ),
        ).model_dump(),
    )
    AI_CONTEXT_LENGTH_PER_MESSAGE: int = Field(
        default=768,
        title="单条消息最大长度 (字符)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="单条消息最大长度 (字符)",
                en_US="Max Length Per Message (characters)",
            ),
            i18n_description=i18n_text(
                zh_CN="聊天上下文单条消息最大长度，超出该长度会自动截取并缩略显示",
                en_US="Maximum length per message in context, exceeding will be truncated",
            ),
        ).model_dump(),
        description="聊天上下文单条消息最大长度，超出该长度会自动截取并缩略显示",
    )
    AI_CONTEXT_LENGTH_PER_SESSION: int = Field(
        default=5120,
        title="聊天上下文最大长度 (字符)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="聊天上下文最大长度 (字符)",
                en_US="Max Context Length (characters)",
            ),
            i18n_description=i18n_text(
                zh_CN="聊天历史记录上下文最大长度，超出该长度会自动截断",
                en_US="Maximum context length for chat history, exceeding will be truncated",
            ),
        ).model_dump(),
        description="聊天历史记录上下文最大长度，超出该长度会自动截断",
    )
    AI_VISION_IMAGE_LIMIT: int = Field(
        default=5,
        title="视觉参考图片数量限制",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="视觉参考图片数量限制",
                en_US="Vision Image Count Limit",
            ),
        ).model_dump(),
    )
    AI_VISION_IMAGE_SIZE_LIMIT_KB: int = Field(
        default=1024,
        title="视觉图片大小限制 (KB)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="视觉图片大小限制 (KB)",
                en_US="Vision Image Size Limit (KB)",
            ),
            i18n_description=i18n_text(
                zh_CN="每次传递的图片大小限制，超出此大小的图片会被自动压缩到限制内传递",
                en_US="Image size limit per transmission, exceeding images will be compressed",
            ),
        ).model_dump(),
        description="每次传递的图片大小限制，超出此大小的图片会被自动压缩到限制内传递",
    )
    AI_SYSTEM_NOTIFY_WINDOW_SIZE: int = Field(
        default=10,
        title="聊天上下文系统消息通知窗口大小",
        description="聊天上下文系统消息通知窗口大小，超出该大小的系统消息不会被参考",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="聊天上下文系统消息通知窗口大小",
                en_US="System Message Notification Window Size",
            ),
            i18n_description=i18n_text(
                zh_CN="聊天上下文系统消息通知窗口大小，超出该大小的系统消息不会被参考",
                en_US="System message notification window size, messages outside will not be referenced",
            ),
        ).model_dump(),
    )
    AI_SYSTEM_NOTIFY_LIMIT: int = Field(
        default=3,
        title="聊天上下文系统消息通知条数限制",
        description="聊天上下文系统消息通知条数限制，超出该条数不会被参考",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="聊天上下文系统消息通知条数限制",
                en_US="System Message Notification Count Limit",
            ),
            i18n_description=i18n_text(
                zh_CN="聊天上下文系统消息通知条数限制，超出该条数不会被参考",
                en_US="System message notification count limit, exceeding will not be referenced",
            ),
        ).model_dump(),
    )
    AI_ALWAYS_INCLUDE_MSG_ID: bool = Field(
        default=False,
        title="始终呈现所有消息的 ID",
        description="启用后上下文中将始终呈现所有消息的 ID，这将占用额外的上下文长度，但允许 AI 在回复时更灵活地引用消息或使用插件对特定消息进行处理",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="始终呈现所有消息的 ID",
                en_US="Always Include Message IDs",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后上下文中将始终呈现所有消息的 ID，允许 AI 更灵活地引用消息",
                en_US="When enabled, all message IDs will be included in context for flexible referencing",
            ),
        ).model_dump(),
    )
    AI_INCLUDE_TOME_INDICATOR: bool = Field(
        default=False,
        title="在历史消息中标注消息指向标记",
        description="启用后，群聊历史中每条人类消息会附加 tome:true/false 标记，表示该消息是否通过固定规则（如 @ 提及）判断为直接指向当前 Bot。AI 会将其作为辅助参考，不会盲信该标记，仍会结合上下文综合判断。",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="在历史消息中标注消息指向标记",
                en_US="Include Message Addressee Indicator",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后群聊历史中每条人类消息会附加 tome:true/false 标记，辅助 AI 识别消息归属，避免多 Bot 场景下错误接话",
                en_US="When enabled, each human message in group chat history will include a tome:true/false indicator to help AI identify message ownership in multi-bot scenarios",
            ),
        ).model_dump(),
    )
    AI_SHOW_REMOTE_URL: bool = Field(
        default=False,
        title="显示远程资源 URL",
        description="启用后若资源远程 URL 可用，将在上下文中追加提供远程 URL 供 AI 参考使用",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="显示远程资源 URL",
                en_US="Show Remote Resource URL",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后若资源远程 URL 可用，将在上下文中追加提供远程 URL 供 AI 参考使用",
                en_US="When enabled, if the resource remote URL is available, it will be appended to the context for AI to reference",
            ),
        ).model_dump(),
    )
    AI_REQUEST_STREAM_MODE: bool = Field(
        default=False,
        title="启用流式请求",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="启用流式请求",
                en_US="Enable Stream Mode",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后 AI 会以流式请求方式返回响应，可能解决某些 LLM 请求异常的问题",
                en_US="AI will use streaming mode for responses, may fix some LLM request issues",
            ),
        ).model_dump(),
        description="启用后 AI 会以流式请求方式返回响应，再合并解析，这可能解决某些 LLM 请求异常的问题，但是会丢失准确的 Token 统计信息",
    )
    AI_STREAM_FIRST_TOKEN_TIMEOUT: int = Field(
        default=60,
        title="流式首 Token 超时 (秒)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="流式首 Token 超时 (秒)",
                en_US="Stream First Token Timeout (seconds)",
            ),
            i18n_description=i18n_text(
                zh_CN="仅在启用流式请求时生效；若在指定时间内未收到首个有效流式片段，则判定本次请求失败并进入后续重试",
                en_US="Only effective when stream mode is enabled; if no first valid stream chunk is received within this time, the request fails and enters subsequent retries",
            ),
        ).model_dump(),
        description="仅在启用流式请求时生效。若供应商在指定时间内未返回首个有效流式片段（空块不计入），则立即判定本次请求失败并进入后续重试，用于减少长时间无响应等待。",
    )

    """聊天设置"""
    SESSION_GROUP_ACTIVE_DEFAULT: bool = Field(
        default=True,
        title="新群聊默认启用聊天",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="新群聊默认启用聊天",
                en_US="Enable Chat for New Groups by Default",
            ),
        ).model_dump(),
    )
    SESSION_PRIVATE_ACTIVE_DEFAULT: bool = Field(
        default=True,
        title="新私聊默认启用聊天",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="新私聊默认启用聊天",
                en_US="Enable Chat for New Private Chats by Default",
            ),
        ).model_dump(),
    )
    SESSION_ENABLE_FAILED_LLM_FEEDBACK: bool = Field(
        default=True,
        title="启用失败 LLM 反馈",
        description="启用后 AI 调用 LLM 失败时会发送反馈",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="聊天配置",
                en_US="Chat Configuration",
            ),
            overridable=True,
            i18n_title=i18n_text(
                zh_CN="启用失败 LLM 反馈",
                en_US="Enable Failed LLM Feedback",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后 AI 调用 LLM 失败时会发送反馈",
                en_US="Send feedback when AI LLM call fails",
            ),
        ).model_dump(),
    )

    """沙盒配置"""
    SANDBOX_IMAGE_NAME: str = Field(
        default="kromiose/nekro-agent-sandbox",
        title="沙盒镜像名称",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="沙盒镜像名称",
                en_US="Sandbox Image Name",
            ),
        ).model_dump(),
    )
    SANDBOX_RUNNING_TIMEOUT: int = Field(
        default=120,
        title="沙盒超时时间 (秒)",
        description="每个沙盒容器最长运行时间，超过该时间沙盒容器会被强制停止",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="沙盒超时时间 (秒)",
                en_US="Sandbox Timeout (seconds)",
            ),
            i18n_description=i18n_text(
                zh_CN="每个沙盒容器最长运行时间，超过该时间沙盒容器会被强制停止",
                en_US="Maximum runtime for each sandbox container, will be forcefully stopped if exceeded",
            ),
        ).model_dump(),
    )
    SANDBOX_MAX_CONCURRENT: int = Field(
        default=4,
        title="最大并发沙盒数",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="最大并发沙盒数",
                en_US="Max Concurrent Sandboxes",
            ),
        ).model_dump(),
    )
    SANDBOX_CHAT_API_URL: str = Field(
        default=f"http://host.docker.internal:{OsEnv.EXPOSE_PORT}/api",
        title="沙盒访问 Nekro API 地址",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="沙盒访问 Nekro API 地址",
                en_US="Sandbox Nekro API URL",
            ),
        ).model_dump(),
    )
    SANDBOX_ONEBOT_SERVER_MOUNT_DIR: str = Field(
        default="/app/nekro_agent_data",
        title="协议端挂载 NA 数据目录",
        description="该目录用于 NA 向 OneBot 协议端上传资源文件时，指定文件访问的路径使用，请确保协议端能通过该目录访问到 NA 的应用数据，如果协议端运行在 Docker 容器中则需要将此目录挂载到容器中对应位置",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="协议端挂载 NA 数据目录",
                en_US="OneBot Server NA Data Mount Directory",
            ),
            i18n_description=i18n_text(
                zh_CN="NA 向 OneBot 协议端上传资源文件时使用的路径，确保协议端能访问",
                en_US="Path for NA to upload resources to OneBot server, ensure server can access",
            ),
        ).model_dump(),
    )

    """CC Workspace 配置"""
    CC_SANDBOX_IMAGE: str = Field(
        default="kromiose/nekro-cc-sandbox",
        title="CC 沙盒镜像名称",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(zh_CN="CC 沙盒镜像名称", en_US="CC Sandbox Image Name"),
        ).model_dump(),
    )
    CC_SANDBOX_IMAGE_TAG: str = Field(
        default="latest",
        title="CC 沙盒镜像标签",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(zh_CN="CC 沙盒镜像标签", en_US="CC Sandbox Image Tag"),
        ).model_dump(),
    )
    CC_SANDBOX_INTERNAL_PORT: int = Field(
        default=7021,
        title="CC 沙盒容器内部端口",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(zh_CN="CC 沙盒容器内部端口", en_US="CC Sandbox Internal Port"),
        ).model_dump(),
    )
    CC_SANDBOX_PORT_RANGE_START: int = Field(
        default=40000,
        title="CC 沙盒宿主机端口段起始",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(zh_CN="CC 沙盒端口段起始", en_US="CC Sandbox Port Range Start"),
        ).model_dump(),
    )
    CC_SANDBOX_PORT_RANGE_END: int = Field(
        default=49999,
        title="CC 沙盒宿主机端口段结束",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(zh_CN="CC 沙盒端口段结束", en_US="CC Sandbox Port Range End"),
        ).model_dump(),
    )
    CC_SANDBOX_STARTUP_TIMEOUT: int = Field(
        default=120,
        title="CC 沙盒启动超时（秒）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="沙盒配置",
                en_US="Sandbox Configuration",
            ),
            i18n_title=i18n_text(zh_CN="CC 沙盒启动超时（秒）", en_US="CC Sandbox Startup Timeout (s)"),
        ).model_dump(),
    )

    """邮件通知配置"""
    MAIL_ENABLED: bool = Field(
        default=False,
        title="启用运行状态邮件通知",
        description="启用后 Bot 上下线时会发送邮件通知",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="邮件通知",
                en_US="Email Notification",
            ),
            i18n_title=i18n_text(
                zh_CN="启用运行状态邮件通知",
                en_US="Enable Runtime Status Email Notification",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后 Bot 上下线时会发送邮件通知",
                en_US="Send email notification when bot goes online/offline",
            ),
        ).model_dump(),
    )
    MAIL_USERNAME: str = Field(
        default="",
        title="邮件通知账号",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_category=i18n_text(
                zh_CN="邮件通知",
                en_US="Email Notification",
            ),
            i18n_title=i18n_text(
                zh_CN="邮件通知账号",
                en_US="Email Notification Account",
            ),
            i18n_description=i18n_text(
                zh_CN="用于发送通知的邮箱账号",
                en_US="Email account for sending notifications",
            ),
        ).model_dump(),
        description="用于发送通知的邮箱账号",
    )
    MAIL_PASSWORD: str = Field(
        default="",
        title="邮件通知密码/授权码",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_category=i18n_text(
                zh_CN="邮件通知",
                en_US="Email Notification",
            ),
            i18n_title=i18n_text(
                zh_CN="邮件通知密码/授权码",
                en_US="Email Password/Authorization Code",
            ),
            i18n_description=i18n_text(
                zh_CN="邮箱密码或授权码",
                en_US="Email password or authorization code",
            ),
        ).model_dump(),
        description="邮箱密码或授权码",
    )
    MAIL_TARGET: List[str] = Field(
        default=[],
        title="邮件通知目标",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="邮件通知",
                en_US="Email Notification",
            ),
            sub_item_name="目标邮箱",
            i18n_title=i18n_text(
                zh_CN="邮件通知目标",
                en_US="Email Notification Targets",
            ),
        ).model_dump(),
    )
    MAIL_HOSTNAME: str = Field(
        default="smtp.qq.com",
        title="邮件通知 SMTP 服务器",
        description="邮件服务器的 SMTP 地址",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="邮件通知",
                en_US="Email Notification",
            ),
            i18n_title=i18n_text(
                zh_CN="邮件通知 SMTP 服务器",
                en_US="Email SMTP Server",
            ),
            i18n_description=i18n_text(
                zh_CN="邮件服务器的 SMTP 地址",
                en_US="SMTP address of email server",
            ),
        ).model_dump(),
    )
    MAIL_PORT: int = Field(
        default=587,
        title="邮件通知 SMTP 端口",
        description="SMTP服务器端口, 一般为 587 或 465",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="邮件通知",
                en_US="Email Notification",
            ),
            i18n_title=i18n_text(
                zh_CN="邮件通知 SMTP 端口",
                en_US="Email SMTP Port",
            ),
            i18n_description=i18n_text(
                zh_CN="SMTP服务器端口，一般为 587 或 465",
                en_US="SMTP server port, usually 587 or 465",
            ),
        ).model_dump(),
    )
    MAIL_STARTTLS: bool = Field(
        default=True,
        title="邮件通知启用 TLS 加密",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="邮件通知",
                en_US="Email Notification",
            ),
            i18n_title=i18n_text(
                zh_CN="邮件通知启用 TLS 加密",
                en_US="Enable TLS Encryption for Email",
            ),
        ).model_dump(),
    )

    """插件配置"""
    PLUGIN_GENERATE_MODEL_GROUP: str = Field(
        default="default",
        title="插件代码生成模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            ref_model_groups=True,
            model_type="chat",
            i18n_title=i18n_text(
                zh_CN="插件代码生成模型组",
                en_US="Plugin Code Generation Model Group",
            ),
            i18n_description=i18n_text(
                zh_CN="用于生成插件代码的模型组，建议使用上下文长、逻辑推理能力强的模型",
                en_US="Model group for plugin code generation, recommend long-context models with strong reasoning",
            ),
        ).model_dump(),
        description="用于生成插件代码的模型组，建议使用上下文长，逻辑推理能力强的模型",
    )
    PLUGIN_APPLY_MODEL_GROUP: str = Field(
        default="default",
        title="插件代码应用模型组",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="模型配置",
                en_US="Model Configuration",
            ),
            ref_model_groups=True,
            model_type="chat",
            i18n_title=i18n_text(
                zh_CN="插件代码应用模型组",
                en_US="Plugin Code Application Model Group",
            ),
            i18n_description=i18n_text(
                zh_CN="用于应用插件代码的模型组，建议使用上下文长、响应速度快的模型",
                en_US="Model group for plugin code application, recommend long-context and fast models",
            ),
        ).model_dump(),
        description="用于应用插件代码的模型组，建议使用上下文长，响应速度快的模型",
    )
    PLUGIN_UPDATE_USE_PROXY: bool = Field(
        default=False,
        title="更新/克隆插件时使用代理",
        description="是否在克隆或更新插件 Git 仓库时使用系统级默认代理",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="代理配置",
                en_US="Proxy Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="更新/克隆插件时使用代理",
                en_US="Use Proxy for Plugin Update/Clone",
            ),
            i18n_description=i18n_text(
                zh_CN="是否在克隆或更新插件 Git 仓库时使用系统级默认代理",
                en_US="Whether to use the system default proxy when cloning or updating plugin Git repositories",
            ),
        ).model_dump(),
    )
    DYNAMIC_PLUGIN_INSTALL_USE_PROXY: bool = Field(
        default=False,
        title="动态安装插件依赖时使用代理",
        description="是否在动态安装插件依赖时使用系统级默认代理",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="代理配置",
                en_US="Proxy Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="动态安装插件依赖时使用代理",
                en_US="Use Proxy for Dynamic Plugin Installation",
            ),
            i18n_description=i18n_text(
                zh_CN="是否在动态安装插件依赖时使用系统级默认代理",
                en_US="Whether to use the system default proxy when dynamically installing plugin dependencies",
            ),
        ).model_dump(),
    )
    DYNAMIC_PLUGIN_INSTALL_MIRROR: Literal[
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.aliyun.com/pypi/simple",
        "https://mirrors.cloud.tencent.com/pypi/simple",
        "https://repo.huaweicloud.com/repository/pypi/simple",
        "https://pypi.org/simple",
    ] = Field(
        default="https://pypi.tuna.tsinghua.edu.cn/simple",
        title="动态插件依赖安装镜像源",
        description="动态安装插件依赖时使用的 PyPI 镜像源地址",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="插件配置",
                en_US="Plugin Configuration",
            ),
            i18n_title=i18n_text(
                zh_CN="动态插件依赖安装镜像源",
                en_US="Dynamic Plugin Dependency Installation Mirror",
            ),
            i18n_description=i18n_text(
                zh_CN="动态安装插件依赖时使用的 PyPI 镜像源地址",
                en_US="PyPI mirror for dynamically installing plugin dependencies",
            ),
        ).model_dump(),
    )

    """Postgresql 配置"""
    POSTGRES_HOST: str = Field(
        default="127.0.0.1",
        title="数据库主机",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        title="数据库端口",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )
    POSTGRES_USER: str = Field(
        default="db_username",
        title="数据库用户名",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )
    POSTGRES_PASSWORD: str = Field(
        default="db_password",
        title="数据库密码",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )
    POSTGRES_DATABASE: str = Field(
        default="nekro_agent",
        title="数据库名称",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )

    """Qdrant 配置"""
    QDRANT_URL: str = Field(
        default="http://127.0.0.1:6333",
        title="Qdrant 地址",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )
    QDRANT_API_KEY: str = Field(
        default="",
        title="Qdrant API Key",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )

    """其他功能"""
    ENABLE_FESTIVAL_REMINDER: bool = Field(
        default=True,
        title="启用节日祝福提醒 (已弃用)",
        description="已弃用，请使用节日祝福插件的配置代替",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="启用节日祝福提醒 (已弃用)",
                en_US="Enable Festival Greeting Reminder (Deprecated)",
            ),
            i18n_description=i18n_text(
                zh_CN="已弃用，请使用节日祝福插件的配置代替",
                en_US="Deprecated, please use the Festival Greeting plugin settings instead",
            ),
        ).model_dump(),
    )
    ENABLE_ADVANCED_COMMAND: bool = Field(
        default=False,
        title="启用高级管理命令",
        description="启用后可以执行包含危险操作的管理员高级命令，请谨慎使用",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(
                zh_CN="基础设置",
                en_US="Basic Settings",
            ),
            i18n_title=i18n_text(
                zh_CN="启用高级管理命令",
                en_US="Enable Advanced Admin Commands",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后可以执行包含危险操作的管理员高级命令，请谨慎使用",
                en_US="Enable advanced admin commands with dangerous operations, use with caution",
            ),
        ).model_dump(),
    )
    OPENAI_CLIENT_USER_AGENT: str = Field(
        default="nekro-agent",
        title="OpenAI Client User Agent",
        description="OpenAI Client User Agent",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )

    """插件配置"""
    PLUGIN_ENABLED: List[str] = Field(
        default=["KroMiose.basic", "KroMiose.plugin_activation"],
        title="启用插件",
        description="启用插件 key 列表",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )
    PLUGIN_ACTIVATION_STRATEGIES: Dict[str, Literal["auto", "allow_sleep", "forbid_sleep"]] = Field(
        default={},
        title="插件激活策略覆盖",
        description="按插件 module_name 覆盖插件提示词激活策略",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )

    def get_model_group_info(self, model_name: str) -> ModelConfigGroup:
        try:
            return self.MODEL_GROUPS[model_name]
        except KeyError as e:
            raise KeyError(f"模型组 '{model_name}' 不存在，请确认配置正确") from e

    def require_advanced_command(self) -> bool:
        if not self.ENABLE_ADVANCED_COMMAND:
            raise PermissionError("高级管理命令未启用，请在配置文件中启用")
        return True

    @classmethod
    def load_config(cls, file_path: Optional[Path] = None, auto_register: bool = True):
        """加载配置文件"""
        config = super().load_config(file_path=file_path, auto_register=auto_register)
        config.load_config_to_env()
        return config


# 设置配置键和文件路径
CoreConfig.set_config_key("system")
CoreConfig.set_config_file_path(CONFIG_PATH)

try:
    config = CoreConfig.load_config()
    config_schema = config.model_json_schema()
except Exception as e:
    print(f"Nekro Agent 配置文件加载失败: {e} | 请检查配置文件是否符合语法要求")
    print("应用将退出...")
    exit(1)

config.dump_config()
set_system_lang(SupportedLang(config.SYSTEM_LANG))


def save_config():
    """保存配置"""
    global config
    config.dump_config()
    set_system_lang(SupportedLang(config.SYSTEM_LANG))


def reload_config():
    """重新加载配置文件"""
    global config

    new_config = CoreConfig.load_config()
    # 更新配置字段
    for field_name in CoreConfig.model_fields:
        value = getattr(new_config, field_name)
        setattr(config, field_name, value)
    set_system_lang(SupportedLang(config.SYSTEM_LANG))
