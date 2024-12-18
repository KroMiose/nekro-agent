class MioseToolkitLLMError(Exception):
    """miose_toolkit_llm 工具库基础异常类"""

    def __init__(self, message: str):
        self.message = message


class ClientError(MioseToolkitLLMError):
    """LLM 客户端异常类"""


class RunOutOfCredentialException(ClientError):
    """凭据耗尽异常类"""

    def __init__(self):
        self.message = "Run out of credentials"


class InvalidCredentialException(ClientError):
    """无效的凭据异常类"""

    def __init__(self, key: str = ""):
        self.message = (
            f"Invalid credential: (credential: {_gen_key_preview(key)})"
            if key
            else "Invalid credential"
        )


class QuotaLimitException(ClientError):
    """配额限制异常类"""

    def __init__(self, key: str = ""):
        self.message = (
            f"Quota limit reached: (credential: {_gen_key_preview(key)})"
            if key
            else "Quota limit reached"
        )


class RequestTimeoutException(ClientError):
    """请求超时异常类"""

    def __init__(self, key: str = ""):
        self.message = (
            f"Request timeout: (credential: {_gen_key_preview(key)})"
            if key
            else "Request timeout"
        )


class PromptError(MioseToolkitLLMError):
    """提示词构造异常类"""


class RenderPromptError(PromptError):
    """渲染提示词异常类"""


class ArgumentTypeError(PromptError):
    """参数类型异常类"""


class ComponentError(MioseToolkitLLMError):
    """组件异常类"""


class NoSuchParameterError(ComponentError):
    """无此参数异常类"""


class StoreNotSetError(ComponentError):
    """存储未设置异常类"""

    def __init__(self):
        self.message = "Component's store is not set"


class ComponentRuntimeError(ComponentError):
    """组件运行时异常类"""


class ResolveError(MioseToolkitLLMError):
    """解析结果异常类"""


class StoreError(MioseToolkitLLMError):
    """存储异常类"""


class TokenizerError(MioseToolkitLLMError):
    """分词器异常类"""


class SceneError(MioseToolkitLLMError):
    """场景异常类"""


class SceneRuntimeError(SceneError):
    """场景运行时异常类"""


def _gen_key_preview(key: str) -> str:
    """生成密钥的预览字符串"""
    return f"{key[:8]}...{key[-8:]}" if len(key) > 16 else key
