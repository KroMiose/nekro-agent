"""统一错误类型系统

设计原则:
1. 通过继承定义具体错误类型，类名即错误标识
2. 每个错误类自包含国际化消息模板
3. 支持参数化消息，如 "配置项 '{key}' 不存在"
4. HTTP 状态码由错误类决定，非路由决定

使用示例:
    # 定义错误
    class ConfigNotFoundError(AppError):
        http_status = 404
        i18n_message = i18n_text(
            zh_CN="配置项 '{key}' 不存在",
            en_US="Configuration '{key}' not found",
        )
        def __init__(self, key: str, **kwargs):
            super().__init__(key=key, **kwargs)

    # 抛出错误
    raise ConfigNotFoundError(key="USE_MODEL_GROUP")
"""

from typing import Any, ClassVar, Dict, Optional

from .i18n import I18nDict, SupportedLang, i18n_text


class AppError(Exception):
    """应用基础异常类

    所有业务错误都应继承此类，并定义:
    - http_status: HTTP 状态码
    - i18n_message: 国际化消息模板（支持 {param} 插值）

    Attributes:
        detail: 技术细节，用于日志和调试，不暴露给用户
        data: 附加数据，可选返回给前端
        params: 消息模板插值参数
    """

    http_status: ClassVar[int] = 500
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="服务器内部错误",
        en_US="Internal server error",
    )

    def __init__(
        self,
        detail: Optional[str] = None,
        data: Any = None,
        **params: Any,
    ):
        self.detail = detail
        self.data = data
        self.params = params
        super().__init__(self.get_message(SupportedLang.ZH_CN))

    @classmethod
    def get_error_name(cls) -> str:
        """获取错误名称（类名）"""
        return cls.__name__

    def get_message(self, lang: SupportedLang) -> str:
        """获取本地化错误消息"""
        # 使用枚举的字符串值作为键来查找
        template = self.i18n_message.get(lang.value) or self.i18n_message.get(
            SupportedLang.ZH_CN.value,
            "Unknown error",
        )
        try:
            return template.format(**self.params) if self.params else template
        except KeyError:
            return template

    def to_response(self, lang: SupportedLang) -> Dict[str, Any]:
        """转换为 API 响应格式"""
        return {
            "error": self.get_error_name(),
            "message": self.get_message(lang),
            "detail": self.detail,
            "data": self.data,
        }


# ============================================================
# 通用错误
# ============================================================


class ValidationError(AppError):
    """请求参数验证失败"""

    http_status: ClassVar[int] = 400
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="请求参数无效: {reason}",
        en_US="Invalid request parameters: {reason}",
    )

    def __init__(self, reason: str, **kwargs: Any):
        super().__init__(reason=reason, **kwargs)


class NotFoundError(AppError):
    """资源不存在"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="{resource}不存在",
        en_US="{resource} not found",
    )

    def __init__(self, resource: str, **kwargs: Any):
        super().__init__(resource=resource, **kwargs)


class ConflictError(AppError):
    """资源冲突"""

    http_status: ClassVar[int] = 409
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="{resource}已存在",
        en_US="{resource} already exists",
    )

    def __init__(self, resource: str, **kwargs: Any):
        super().__init__(resource=resource, **kwargs)


class OperationFailedError(AppError):
    """操作失败（通用）"""

    http_status: ClassVar[int] = 500
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="{operation}失败",
        en_US="{operation} failed",
    )

    def __init__(self, operation: str, **kwargs: Any):
        super().__init__(operation=operation, **kwargs)


# ============================================================
# 认证授权错误
# ============================================================


class UnauthorizedError(AppError):
    """未授权访问"""

    http_status: ClassVar[int] = 401
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="未授权访问",
        en_US="Unauthorized access",
    )


class TokenExpiredError(AppError):
    """Token 已过期"""

    http_status: ClassVar[int] = 401
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="登录已过期，请重新登录",
        en_US="Login expired, please login again",
    )


class PermissionDeniedError(AppError):
    """权限不足"""

    http_status: ClassVar[int] = 403
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="无权限执行此操作",
        en_US="Permission denied",
    )


class InvalidCredentialsError(AppError):
    """凭证无效"""

    http_status: ClassVar[int] = 401
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="用户名或密码错误",
        en_US="Invalid username or password",
    )


class TooManyAttemptsError(AppError):
    """尝试次数过多"""

    http_status: ClassVar[int] = 429
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="尝试次数过多，账户已被临时锁定",
        en_US="Too many attempts, account is temporarily locked",
    )


# ============================================================
# 配置相关错误
# ============================================================


class ConfigNotFoundError(AppError):
    """配置不存在"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="配置项 '{key}' 不存在",
        en_US="Configuration '{key}' not found",
    )

    def __init__(self, key: str, **kwargs: Any):
        super().__init__(key=key, **kwargs)


class ConfigInvalidError(AppError):
    """配置值无效"""

    http_status: ClassVar[int] = 400
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="配置项 '{key}' 的值无效: {reason}",
        en_US="Invalid value for configuration '{key}': {reason}",
    )

    def __init__(self, key: str, reason: str, **kwargs: Any):
        super().__init__(key=key, reason=reason, **kwargs)


class ModelGroupNotFoundError(AppError):
    """模型组不存在"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="模型组 '{name}' 不存在，请确认配置正确",
        en_US="Model group '{name}' not found, please check configuration",
    )

    def __init__(self, name: str, **kwargs: Any):
        super().__init__(name=name, **kwargs)


class DefaultModelGroupDeleteError(AppError):
    """默认模型组不能删除"""

    http_status: ClassVar[int] = 400
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="默认模型组不能删除",
        en_US="Default model group cannot be deleted",
    )


# ============================================================
# 插件相关错误
# ============================================================


class PluginNotFoundError(AppError):
    """插件不存在"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="插件 '{plugin_id}' 不存在",
        en_US="Plugin '{plugin_id}' not found",
    )

    def __init__(self, plugin_id: str, **kwargs: Any):
        super().__init__(plugin_id=plugin_id, **kwargs)


class PluginLoadError(AppError):
    """插件加载失败"""

    http_status: ClassVar[int] = 500
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="插件 '{plugin_id}' 加载失败",
        en_US="Failed to load plugin '{plugin_id}'",
    )

    def __init__(self, plugin_id: str, **kwargs: Any):
        super().__init__(plugin_id=plugin_id, **kwargs)


class PluginConfigError(AppError):
    """插件配置错误"""

    http_status: ClassVar[int] = 400
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="插件 '{plugin_id}' 配置错误: {reason}",
        en_US="Plugin '{plugin_id}' configuration error: {reason}",
    )

    def __init__(self, plugin_id: str, reason: str, **kwargs: Any):
        super().__init__(plugin_id=plugin_id, reason=reason, **kwargs)


# ============================================================
# 空间清理相关错误
# ============================================================


class ScanNotStartedError(AppError):
    """扫描未启动"""

    http_status: ClassVar[int] = 400
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="暂无扫描结果，请先启动扫描",
        en_US="No scan result available, please start a scan first",
    )


class ScanInProgressError(AppError):
    """扫描进行中"""

    http_status: ClassVar[int] = 409
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="扫描任务已在运行中",
        en_US="Scan task is already running",
    )


class ScanFailedError(AppError):
    """扫描失败"""

    http_status: ClassVar[int] = 500
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="扫描失败",
        en_US="Scan failed",
    )


class CleanupTaskNotFoundError(AppError):
    """清理任务不存在"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="清理任务不存在或未完成",
        en_US="Cleanup task not found or not completed",
    )


class CleanupFailedError(AppError):
    """清理失败"""

    http_status: ClassVar[int] = 500
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="清理失败",
        en_US="Cleanup failed",
    )


# ============================================================
# 聊天频道相关错误
# ============================================================


class ChannelNotFoundError(AppError):
    """聊天频道不存在"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="聊天频道 '{chat_key}' 不存在",
        en_US="Chat channel '{chat_key}' not found",
    )

    def __init__(self, chat_key: str, **kwargs: Any):
        super().__init__(chat_key=chat_key, **kwargs)


# ============================================================
# 文件操作相关错误
# ============================================================


class AppFileNotFoundError(AppError):
    """文件不存在（避免与内置 FileNotFoundError 冲突）"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="文件 '{filename}' 不存在",
        en_US="File '{filename}' not found",
    )

    def __init__(self, filename: str, **kwargs: Any):
        super().__init__(filename=filename, **kwargs)


class FileTooLargeError(AppError):
    """文件过大"""

    http_status: ClassVar[int] = 413
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="文件大小超过限制 ({limit}MB)",
        en_US="File size exceeds limit ({limit}MB)",
    )

    def __init__(self, limit: int, **kwargs: Any):
        super().__init__(limit=limit, **kwargs)


class InvalidFileTypeError(AppError):
    """文件类型无效"""

    http_status: ClassVar[int] = 400
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="不支持的文件类型: {file_type}",
        en_US="Unsupported file type: {file_type}",
    )

    def __init__(self, file_type: str, **kwargs: Any):
        super().__init__(file_type=file_type, **kwargs)


# ============================================================
# 人设相关错误
# ============================================================


class PresetNotFoundError(AppError):
    """人设不存在"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="人设 '{preset_id}' 不存在",
        en_US="Preset '{preset_id}' not found",
    )

    def __init__(self, preset_id: str, **kwargs: Any):
        super().__init__(preset_id=preset_id, **kwargs)


class PresetInUseError(AppError):
    """人设正在使用中"""

    http_status: ClassVar[int] = 409
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="人设 '{preset_id}' 正在被使用，无法删除",
        en_US="Preset '{preset_id}' is in use and cannot be deleted",
    )

    def __init__(self, preset_id: str, **kwargs: Any):
        super().__init__(preset_id=preset_id, **kwargs)


# ============================================================
# 用户相关错误
# ============================================================


class UserNotFoundError(AppError):
    """用户不存在"""

    http_status: ClassVar[int] = 404
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="用户 '{user_id}' 不存在",
        en_US="User '{user_id}' not found",
    )

    def __init__(self, user_id: str, **kwargs: Any):
        super().__init__(user_id=user_id, **kwargs)


class UserExistsError(AppError):
    """用户已存在"""

    http_status: ClassVar[int] = 409
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="用户名 '{username}' 已存在",
        en_US="Username '{username}' already exists",
    )

    def __init__(self, username: str, **kwargs: Any):
        super().__init__(username=username, **kwargs)


# ============================================================
# 云端服务相关错误
# ============================================================


class CloudServiceError(AppError):
    """云端服务错误"""

    http_status: ClassVar[int] = 502
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="云端服务请求失败: {reason}",
        en_US="Cloud service request failed: {reason}",
    )

    def __init__(self, reason: str, **kwargs: Any):
        super().__init__(reason=reason, **kwargs)


class CloudAuthError(AppError):
    """云端认证失败"""

    http_status: ClassVar[int] = 401
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="云端认证失败，请重新登录",
        en_US="Cloud authentication failed, please login again",
    )


# ============================================================
# 高级功能错误
# ============================================================


class AdvancedCommandDisabledError(AppError):
    """高级命令未启用"""

    http_status: ClassVar[int] = 403
    i18n_message: ClassVar[I18nDict] = i18n_text(
        zh_CN="高级管理命令未启用，请在配置文件中启用",
        en_US="Advanced commands are disabled, please enable in configuration",
    )

