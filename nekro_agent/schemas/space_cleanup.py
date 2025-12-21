"""空间清理相关数据模型"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from nekro_agent.schemas.i18n import I18nDict


class ResourceType(str, Enum):
    """资源类型枚举"""

    USER_UPLOADS = "user_uploads"  # 用户上传资源
    SANDBOX_SHARED = "sandbox_shared"  # 沙盒共享目录
    SANDBOX_PIP_CACHE = "sandbox_pip_cache"  # pip缓存
    SANDBOX_PACKAGES = "sandbox_packages"  # 沙盒包
    PLUGIN_DYNAMIC_PACKAGES = "plugin_dynamic_packages"  # 插件动态包
    PROMPT_LOGS = "prompt_logs"  # 提示词日志
    PROMPT_ERROR_LOGS = "prompt_error_logs"  # 错误日志
    NAPCAT_TEMP = "napcat_temp"  # NapCat临时文件
    PLUGIN_DATA = "plugin_data"  # 插件数据（按插件分组）
    APP_LOGS = "app_logs"  # 应用日志（仅统计）
    OTHER_DATA = "other_data"  # 其他数据（仅统计）


class ScanStatus(str, Enum):
    """扫描状态枚举"""

    IDLE = "idle"  # 空闲
    SCANNING = "scanning"  # 扫描中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败


class CleanupStatus(str, Enum):
    """清理状态枚举"""

    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败


class FileInfo(BaseModel):
    """文件信息"""

    relative_path: str = Field(..., description="相对路径")
    name: str = Field(..., description="文件名")
    size: int = Field(..., description="文件大小（字节）")
    created_time: float = Field(..., description="创建时间（时间戳）")
    modified_time: float = Field(..., description="修改时间（时间戳）")
    chat_key: Optional[str] = Field(None, description="所属聊天key")
    plugin_key: Optional[str] = Field(None, description="所属插件key")


class ChatResourceInfo(BaseModel):
    """聊天资源信息"""

    chat_key: str = Field(..., description="聊天key")
    chat_name: Optional[str] = Field(None, description="聊天名称")
    total_size: int = Field(0, description="总大小（字节）")
    file_count: int = Field(0, description="文件数量")
    files: List[FileInfo] = Field(default_factory=list, description="文件列表")


class PluginResourceInfo(BaseModel):
    """插件资源信息"""

    plugin_key: str = Field(..., description="插件key")
    plugin_name: Optional[str] = Field(None, description="插件名称")
    total_size: int = Field(0, description="总大小（字节）")
    file_count: int = Field(0, description="文件数量")


class ResourceCategory(BaseModel):
    """资源分类"""

    resource_type: ResourceType = Field(..., description="资源类型")
    display_name: str = Field(..., description="显示名称（向后兼容）")
    description: str = Field(..., description="描述（向后兼容）")
    total_size: int = Field(0, description="总大小（字节）")
    file_count: int = Field(0, description="文件数量")
    can_cleanup: bool = Field(True, description="是否可清理")
    risk_level: str = Field("safe", description="风险等级: safe/warning/danger")
    risk_message: Optional[str] = Field(None, description="风险提示（向后兼容）")
    supports_time_filter: bool = Field(True, description="是否支持按时间过滤（False表示只能完全清理）")
    chat_resources: List[ChatResourceInfo] = Field(default_factory=list, description="按聊天分组的资源")
    plugin_resources: List[PluginResourceInfo] = Field(default_factory=list, description="按插件分组的资源")

    # i18n 扩展字段（可选，向后兼容，以 i18n_ 前缀便于字母排序聚合）
    i18n_description: Optional[I18nDict] = Field(None, description="描述国际化")
    i18n_display_name: Optional[I18nDict] = Field(None, description="显示名称国际化")
    i18n_risk_message: Optional[I18nDict] = Field(None, description="风险提示国际化")


class DiskInfo(BaseModel):
    """磁盘信息"""

    total_space: int = Field(..., description="系统总空间（字节）")
    used_space: int = Field(..., description="已使用空间（字节）")
    free_space: int = Field(..., description="可用空间（字节）")
    data_dir_size: int = Field(..., description="DATA_DIR占用空间（字节）")
    data_dir_path: str = Field(..., description="DATA_DIR路径")


class ScanSummary(BaseModel):
    """扫描摘要"""

    total_size: int = Field(0, description="总大小（字节）")
    total_files: int = Field(0, description="总文件数")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[float] = Field(None, description="持续时长（秒）")
    scanned_categories: int = Field(0, description="扫描的分类数")


class ScanResult(BaseModel):
    """扫描结果"""

    scan_id: str = Field(..., description="扫描ID")
    status: ScanStatus = Field(..., description="扫描状态")
    disk_info: Optional[DiskInfo] = Field(None, description="磁盘信息")
    categories: List[ResourceCategory] = Field(default_factory=list, description="资源分类列表")
    summary: ScanSummary = Field(
        default_factory=lambda: ScanSummary(
            total_size=0,
            total_files=0,
            start_time=None,
            end_time=None,
            duration_seconds=None,
            scanned_categories=0,
        ),
        description="扫描摘要",
    )
    error_message: Optional[str] = Field(None, description="错误信息")


class ScanStatusResponse(BaseModel):
    """扫描状态响应"""

    status: ScanStatus = Field(..., description="扫描状态")
    progress: float = Field(0, description="进度（0-100）")
    current_category: Optional[str] = Field(None, description="当前扫描的分类")
    message: Optional[str] = Field(None, description="状态消息")


class CleanupRequest(BaseModel):
    """清理请求"""

    resource_types: List[ResourceType] = Field(..., description="要清理的资源类型")
    chat_keys: Optional[List[str]] = Field(None, description="要清理的聊天key列表")
    before_date: Optional[datetime] = Field(None, description="清理此日期之前的文件")
    dry_run: bool = Field(False, description="是否为模拟运行（不实际删除）")


class CleanupProgress(BaseModel):
    """清理进度"""

    task_id: str = Field(..., description="任务ID")
    status: CleanupStatus = Field(..., description="清理状态")
    progress: float = Field(0, description="进度（0-100）")
    processed_files: int = Field(0, description="已处理文件数")
    total_files: int = Field(0, description="总文件数")
    freed_space: int = Field(0, description="已释放空间（字节）")
    current_file: Optional[str] = Field(None, description="当前处理的文件")
    message: Optional[str] = Field(None, description="状态消息")


class CleanupResult(BaseModel):
    """清理结果"""

    task_id: str = Field(..., description="任务ID")
    status: CleanupStatus = Field(..., description="清理状态")
    total_files: int = Field(0, description="总文件数")
    deleted_files: int = Field(0, description="已删除文件数")
    failed_files: int = Field(0, description="删除失败文件数")
    freed_space: int = Field(0, description="释放的空间（字节）")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[float] = Field(None, description="持续时长（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    failed_file_list: List[str] = Field(default_factory=list, description="删除失败的文件列表")


# ============================================================
# 简单响应模型（避免返回无约束字典）
# ============================================================


class ScanStartResponse(BaseModel):
    """扫描启动响应"""

    scan_id: str = Field(..., description="扫描任务ID")


class CleanupStartResponse(BaseModel):
    """清理启动响应"""

    task_id: str = Field(..., description="清理任务ID")


class ScanProgressResponse(BaseModel):
    """扫描进度响应"""

    status: str = Field(..., description="扫描状态")
    progress: float = Field(0, description="进度（0-100）")
    message: Optional[str] = Field(None, description="状态消息")
