
"""空间扫描服务"""

import asyncio
import contextlib
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import (
    APP_LOG_DIR,
    APP_SYSTEM_DIR,
    NAPCAT_TEMPFILE_DIR,
    PLUGIN_DYNAMIC_PACKAGE_DIR,
    PROMPT_ERROR_LOG_DIR,
    PROMPT_LOG_DIR,
    SANDBOX_PACKAGE_DIR,
    SANDBOX_PIP_CACHE_DIR,
    SANDBOX_SHARED_HOST_DIR,
    USER_UPLOAD_DIR,
    OsEnv,
)
from nekro_agent.schemas.i18n import i18n_text
from nekro_agent.schemas.space_cleanup import (
    ChatResourceInfo,
    DiskInfo,
    FileInfo,
    PluginResourceInfo,
    ResourceCategory,
    ResourceType,
    ScanResult,
    ScanStatus,
    ScanStatusResponse,
    ScanSummary,
)
from nekro_agent.services.plugin.collector import plugin_collector

# 扫描缓存目录

logger = get_sub_logger("space_cleanup")
SCAN_CACHE_DIR = Path(APP_SYSTEM_DIR) / "space_cleanup"
SCAN_CACHE_DIR.mkdir(parents=True, exist_ok=True)

SCAN_RESULT_FILE = SCAN_CACHE_DIR / "latest_scan.json"
SCAN_STATUS_FILE = SCAN_CACHE_DIR / "scan_status.json"


class ScannerService:
    """空间扫描服务"""

    def __init__(self):
        self._current_scan_id: Optional[str] = None
        self._scan_status: ScanStatus = ScanStatus.IDLE
        self._scan_progress: float = 0.0
        self._current_category: Optional[str] = None
        self._scan_task: Optional[asyncio.Task] = None

    async def start_scan(self) -> str:
        """启动扫描任务

        Returns:
            str: 扫描任务ID
        """
        if self._scan_status == ScanStatus.SCANNING:
            logger.warning("扫描任务已在运行中")
            return self._current_scan_id or ""

        scan_id = str(uuid.uuid4())
        self._current_scan_id = scan_id
        self._scan_status = ScanStatus.SCANNING
        self._scan_progress = 0.0

        # 保存初始状态
        await self._save_scan_status()

        # 启动异步扫描任务
        self._scan_task = asyncio.create_task(self._execute_scan(scan_id))

        return scan_id

    async def get_scan_status(self) -> ScanStatusResponse:
        """获取扫描状态

        Returns:
            ScanStatusResponse: 扫描状态响应
        """
        return ScanStatusResponse(
            status=self._scan_status,
            progress=self._scan_progress,
            current_category=self._current_category,
            message=self._get_status_message(),
        )

    async def get_scan_result(self) -> Optional[ScanResult]:
        """获取扫描结果

        Returns:
            Optional[ScanResult]: 扫描结果，如果未完成则返回None
        """
        if not SCAN_RESULT_FILE.exists():
            return None

        try:
            data = json.loads(SCAN_RESULT_FILE.read_text(encoding="utf-8"))
            return ScanResult.model_validate(data)
        except Exception as e:
            logger.error(f"读取扫描结果失败: {e}")
            return None

    async def _execute_scan(self, scan_id: str) -> None:
        """执行扫描任务

        Args:
            scan_id: 扫描ID
        """
        start_time = datetime.now()
        categories: List[ResourceCategory] = []

        try:
            # 获取磁盘信息
            disk_info = await self._get_disk_info()

            # 定义扫描任务
            scan_tasks = [
                (ResourceType.USER_UPLOADS, self._scan_user_uploads),
                (ResourceType.SANDBOX_SHARED, self._scan_sandbox_shared),
                (ResourceType.SANDBOX_PIP_CACHE, self._scan_sandbox_pip_cache),
                (ResourceType.SANDBOX_PACKAGES, self._scan_sandbox_packages),
                (ResourceType.PLUGIN_DYNAMIC_PACKAGES, self._scan_plugin_dynamic_packages),
                (ResourceType.PROMPT_LOGS, self._scan_prompt_logs),
                (ResourceType.PROMPT_ERROR_LOGS, self._scan_prompt_error_logs),
                (ResourceType.NAPCAT_TEMP, self._scan_napcat_temp),
                (ResourceType.PLUGIN_DATA, self._scan_plugin_data),
                (ResourceType.APP_LOGS, self._scan_app_logs),
            ]

            total_tasks = len(scan_tasks)

            # 逐个执行扫描任务
            for idx, (resource_type, scan_func) in enumerate(scan_tasks):
                self._current_category = resource_type.value
                # 更新进度：开始扫描这个分类
                self._scan_progress = (idx / total_tasks) * 100
                await self._save_scan_status()

                # 让出控制权，允许其他请求处理
                await asyncio.sleep(0)

                try:
                    category = await scan_func()
                    categories.append(category)

                    # 更新进度：完成这个分类
                    self._scan_progress = ((idx + 1) / total_tasks) * 100
                    await self._save_scan_status()

                    # 让出控制权
                    await asyncio.sleep(0)
                except Exception as e:
                    logger.error(f"扫描 {resource_type.value} 失败: {e}")
                    # 创建一个空的分类记录
                    categories.append(self._create_empty_category(resource_type))

                    # 即使失败也更新进度
                    self._scan_progress = ((idx + 1) / total_tasks) * 100
                    await self._save_scan_status()

                    # 让出控制权
                    await asyncio.sleep(0)

            # 计算其他数据
            other_category = await self._calculate_other_data(disk_info, categories)
            categories.append(other_category)

            # 计算摘要
            end_time = datetime.now()
            # 只统计可清理的资源类型
            cleanable_categories = [c for c in categories if c.can_cleanup]
            summary = ScanSummary(
                total_size=sum(c.total_size for c in cleanable_categories),
                total_files=sum(c.file_count for c in cleanable_categories),
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
                scanned_categories=len(categories),
            )

            # 创建扫描结果
            scan_result = ScanResult(
                scan_id=scan_id,
                status=ScanStatus.COMPLETED,
                disk_info=disk_info,
                categories=categories,
                summary=summary,
                error_message=None,
            )

            # 保存扫描结果
            await self._save_scan_result(scan_result)

            self._scan_status = ScanStatus.COMPLETED
            self._scan_progress = 100.0
            await self._save_scan_status()

            logger.info(f"扫描完成: {scan_id}, 总大小: {summary.total_size} 字节, 文件数: {summary.total_files}")

        except Exception as e:
            logger.exception(f"扫描任务失败: {e}")
            self._scan_status = ScanStatus.FAILED
            await self._save_scan_status()

            # 保存失败结果
            scan_result = ScanResult(
                scan_id=scan_id,
                status=ScanStatus.FAILED,
                disk_info=None,
                categories=[],
                summary=ScanSummary(
                    total_size=0,
                    total_files=0,
                    start_time=None,
                    end_time=None,
                    duration_seconds=None,
                    scanned_categories=0,
                ),
                error_message=str(e),
            )
            await self._save_scan_result(scan_result)

    async def _get_disk_info(self) -> DiskInfo:
        """获取磁盘信息

        Returns:
            DiskInfo: 磁盘信息
        """
        data_dir = Path(OsEnv.DATA_DIR).resolve()
        disk_usage = shutil.disk_usage(data_dir)

        # 计算DATA_DIR占用空间
        data_dir_size = await self._get_directory_size(data_dir)

        return DiskInfo(
            total_space=disk_usage.total,
            used_space=disk_usage.used,
            free_space=disk_usage.free,
            data_dir_size=data_dir_size,
            data_dir_path=str(data_dir),
        )

    async def _get_directory_size(self, directory: Path) -> int:
        """计算目录总大小

        Args:
            directory: 目录路径

        Returns:
            int: 目录大小（字节）
        """
        if not directory.exists():
            return 0

        total_size = 0
        file_count = 0
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    with contextlib.suppress(OSError, PermissionError):
                        total_size += item.stat().st_size
                        file_count += 1

                        # 每处理100个文件让出一次控制权
                        if file_count % 100 == 0:
                            await asyncio.sleep(0)
        except Exception as e:
            logger.warning(f"计算目录大小失败 {directory}: {e}")

        return total_size

    async def _scan_directory_with_chat_key(
        self,
        directory: Path,
        resource_type: ResourceType,  # noqa: ARG002
    ) -> Tuple[List[ChatResourceInfo], int, int]:
        """扫描目录并按chat_key分组

        Args:
            directory: 目录路径
            resource_type: 资源类型

        Returns:
            Tuple[List[ChatResourceInfo], int, int]: (聊天资源列表, 总大小, 总文件数)
        """
        if not directory.exists():
            return [], 0, 0

        chat_resources: Dict[str, ChatResourceInfo] = {}
        total_size = 0
        total_files = 0

        try:
            # 遍历第一级子目录（chat_key目录）
            for chat_dir in directory.iterdir():
                if not chat_dir.is_dir():
                    continue

                chat_key = chat_dir.name
                files: List[FileInfo] = []
                chat_size = 0
                file_count_in_chat = 0

                # 遍历该聊天目录下的所有文件
                for file_path in chat_dir.rglob("*"):
                    if file_path.is_file():
                        with contextlib.suppress(OSError, PermissionError):
                            stat = file_path.stat()
                            file_info = FileInfo(
                                relative_path=str(file_path.relative_to(directory)),
                                name=file_path.name,
                                size=stat.st_size,
                                created_time=stat.st_ctime,
                                modified_time=stat.st_mtime,
                                chat_key=chat_key,
                                plugin_key=None,
                            )
                            files.append(file_info)
                            chat_size += stat.st_size
                            total_files += 1
                            file_count_in_chat += 1

                            # 每处理50个文件让出一次控制权
                            if file_count_in_chat % 50 == 0:
                                await asyncio.sleep(0)

                if files:
                    chat_resources[chat_key] = ChatResourceInfo(
                        chat_key=chat_key,
                        chat_name=None,
                        total_size=chat_size,
                        file_count=len(files),
                        files=files,
                    )
                    total_size += chat_size

                # 每处理完一个聊天目录让出控制权
                await asyncio.sleep(0)

        except Exception as e:
            logger.warning(f"扫描目录失败 {directory}: {e}")

        return list(chat_resources.values()), total_size, total_files

    async def _scan_directory_simple(self, directory: Path) -> Tuple[int, int]:
        """简单扫描目录（仅统计大小和文件数）

        Args:
            directory: 目录路径

        Returns:
            Tuple[int, int]: (总大小, 总文件数)
        """
        if not directory.exists():
            return 0, 0

        total_size = 0
        total_files = 0

        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                        total_files += 1

                        # 每处理100个文件让出一次控制权
                        if total_files % 100 == 0:
                            await asyncio.sleep(0)
                    except (OSError, PermissionError):
                        pass
        except Exception as e:
            logger.warning(f"扫描目录失败 {directory}: {e}")

        return total_size, total_files

    async def _scan_user_uploads(self) -> ResourceCategory:
        """扫描用户上传资源"""
        directory = Path(USER_UPLOAD_DIR)
        chat_resources, total_size, total_files = await self._scan_directory_with_chat_key(
            directory,
            ResourceType.USER_UPLOADS,
        )

        return ResourceCategory(
            resource_type=ResourceType.USER_UPLOADS,
            display_name="聊天上传资源",
            description="聊天中接收到的文件和图片等资源",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=True,
            risk_level="warning",
            risk_message="清理后AI将无法访问历史消息中的资源文件",
            supports_time_filter=True,
            chat_resources=chat_resources,
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="聊天上传资源", en_US="Chat Uploads"),
            i18n_description=i18n_text(
                zh_CN="聊天中接收到的文件和图片等资源",
                en_US="Files and images received in chat",
            ),
            i18n_risk_message=i18n_text(
                zh_CN="清理后AI将无法访问历史消息中的资源文件",
                en_US="AI will not be able to access resource files in historical messages after cleanup",
            ),
        )

    async def _scan_sandbox_shared(self) -> ResourceCategory:
        """扫描沙盒共享目录（排除.pip_cache和.packages）"""
        directory = Path(SANDBOX_SHARED_HOST_DIR)

        if not directory.exists():
            return ResourceCategory(
                resource_type=ResourceType.SANDBOX_SHARED,
                display_name="沙盒临时代码",
                description="AI 执行代码时产生的临时文件",
                total_size=0,
                file_count=0,
                can_cleanup=True,
                risk_level="safe",
                risk_message=None,
                supports_time_filter=False,
                chat_resources=[],
                plugin_resources=[],
                i18n_display_name=i18n_text(zh_CN="沙盒临时代码", en_US="Sandbox Temp Code"),
                i18n_description=i18n_text(
                    zh_CN="AI 执行代码时产生的临时文件",
                    en_US="Temporary files generated when AI executes code",
                ),
                i18n_risk_message=None,
            )

        chat_resources: Dict[str, ChatResourceInfo] = {}
        total_size = 0
        total_files = 0

        try:
            # 遍历第一级子目录（chat_key目录）
            for chat_dir in directory.iterdir():
                if not chat_dir.is_dir():
                    continue

                # 跳过 .pip_cache 和 .packages 目录
                if chat_dir.name in {".pip_cache", ".packages"}:
                    continue

                chat_key = chat_dir.name
                files: List[FileInfo] = []
                chat_size = 0
                file_count_in_chat = 0

                # 遍历该聊天目录下的所有文件
                for file_path in chat_dir.rglob("*"):
                    if file_path.is_file():
                        with contextlib.suppress(OSError, PermissionError):
                            stat = file_path.stat()
                            file_info = FileInfo(
                                relative_path=str(file_path.relative_to(directory)),
                                name=file_path.name,
                                size=stat.st_size,
                                created_time=stat.st_ctime,
                                modified_time=stat.st_mtime,
                                chat_key=chat_key,
                                plugin_key=None,
                            )
                            files.append(file_info)
                            chat_size += stat.st_size
                            total_files += 1
                            file_count_in_chat += 1

                            # 每处理50个文件让出一次控制权
                            if file_count_in_chat % 50 == 0:
                                await asyncio.sleep(0)

                if files:
                    chat_resources[chat_key] = ChatResourceInfo(
                        chat_key=chat_key,
                        chat_name=None,
                        total_size=chat_size,
                        file_count=len(files),
                        files=files,
                    )
                    total_size += chat_size

                # 每处理完一个聊天目录让出控制权
                await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"扫描沙盒共享目录失败: {e}")

        return ResourceCategory(
            resource_type=ResourceType.SANDBOX_SHARED,
            display_name="沙盒临时代码",
            description="AI 执行代码时产生的临时文件",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=True,
            risk_level="safe",
            risk_message=None,
            supports_time_filter=False,
            chat_resources=list(chat_resources.values()),
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="沙盒临时代码", en_US="Sandbox Temp Code"),
            i18n_description=i18n_text(
                zh_CN="AI 执行代码时产生的临时文件",
                en_US="Temporary files generated when AI executes code",
            ),
            i18n_risk_message=None,
        )

    async def _scan_sandbox_pip_cache(self) -> ResourceCategory:
        """扫描沙盒pip缓存"""
        directory = Path(SANDBOX_PIP_CACHE_DIR)
        total_size, total_files = await self._scan_directory_simple(directory)

        return ResourceCategory(
            resource_type=ResourceType.SANDBOX_PIP_CACHE,
            display_name="沙盒 Pip 缓存",
            description="Python 包管理器的缓存文件",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=True,
            risk_level="safe",
            risk_message=None,
            supports_time_filter=False,
            chat_resources=[],
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="沙盒 Pip 缓存", en_US="Sandbox Pip Cache"),
            i18n_description=i18n_text(
                zh_CN="Python 包管理器的缓存文件",
                en_US="Cache files from Python package manager",
            ),
            i18n_risk_message=None,
        )

    async def _scan_sandbox_packages(self) -> ResourceCategory:
        """扫描沙盒包"""
        directory = Path(SANDBOX_PACKAGE_DIR)
        total_size, total_files = await self._scan_directory_simple(directory)

        return ResourceCategory(
            resource_type=ResourceType.SANDBOX_PACKAGES,
            display_name="沙盒依赖包",
            description="AI 动态安装的 Python 依赖包",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=True,
            risk_level="safe",
            risk_message=None,
            supports_time_filter=False,
            chat_resources=[],
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="沙盒依赖包", en_US="Sandbox Packages"),
            i18n_description=i18n_text(
                zh_CN="AI 动态安装的 Python 依赖包",
                en_US="Python packages dynamically installed by AI",
            ),
            i18n_risk_message=None,
        )

    async def _scan_plugin_dynamic_packages(self) -> ResourceCategory:
        """扫描插件动态包"""
        directory = Path(PLUGIN_DYNAMIC_PACKAGE_DIR)
        total_size, total_files = await self._scan_directory_simple(directory)

        return ResourceCategory(
            resource_type=ResourceType.PLUGIN_DYNAMIC_PACKAGES,
            display_name="插件依赖包",
            description="插件动态安装的 Python 依赖包",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=True,
            risk_level="danger",
            risk_message="清理后插件可能行为异常，需要重启服务",
            supports_time_filter=False,
            chat_resources=[],
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="插件依赖包", en_US="Plugin Packages"),
            i18n_description=i18n_text(
                zh_CN="插件动态安装的 Python 依赖包",
                en_US="Python packages dynamically installed by plugins",
            ),
            i18n_risk_message=i18n_text(
                zh_CN="清理后插件可能行为异常，需要重启服务",
                en_US="Plugins may behave abnormally after cleanup, restart required",
            ),
        )

    async def _scan_prompt_logs(self) -> ResourceCategory:
        """扫描提示词日志"""
        directory = Path(PROMPT_LOG_DIR)
        total_size, total_files = await self._scan_directory_simple(directory)

        return ResourceCategory(
            resource_type=ResourceType.PROMPT_LOGS,
            display_name="提示词日志",
            description="AI 对话的提示词记录",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=True,
            risk_level="safe",
            risk_message=None,
            supports_time_filter=True,
            chat_resources=[],
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="提示词日志", en_US="Prompt Logs"),
            i18n_description=i18n_text(
                zh_CN="AI 对话的提示词记录",
                en_US="Prompt records from AI conversations",
            ),
            i18n_risk_message=None,
        )

    async def _scan_prompt_error_logs(self) -> ResourceCategory:
        """扫描错误提示词日志"""
        directory = Path(PROMPT_ERROR_LOG_DIR)
        total_size, total_files = await self._scan_directory_simple(directory)

        return ResourceCategory(
            resource_type=ResourceType.PROMPT_ERROR_LOGS,
            display_name="错误提示词日志",
            description="请求失败时的提示词记录",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=True,
            risk_level="safe",
            risk_message=None,
            supports_time_filter=True,
            chat_resources=[],
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="错误提示词日志", en_US="Error Prompt Logs"),
            i18n_description=i18n_text(
                zh_CN="请求失败时的提示词记录",
                en_US="Prompt records when requests failed",
            ),
            i18n_risk_message=None,
        )

    async def _scan_napcat_temp(self) -> ResourceCategory:
        """扫描NapCat临时文件"""
        directory = Path(NAPCAT_TEMPFILE_DIR)
        total_size, total_files = await self._scan_directory_simple(directory)

        return ResourceCategory(
            resource_type=ResourceType.NAPCAT_TEMP,
            display_name="NapCat 临时文件",
            description="QQ 消息接收的临时文件",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=True,
            risk_level="safe",
            risk_message=None,
            supports_time_filter=True,
            chat_resources=[],
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="NapCat 临时文件", en_US="NapCat Temp Files"),
            i18n_description=i18n_text(
                zh_CN="QQ 消息接收的临时文件",
                en_US="Temporary files received from QQ messages",
            ),
            i18n_risk_message=None,
        )

    async def _scan_plugin_data(self) -> ResourceCategory:
        """扫描插件数据"""
        plugin_data_dir = Path(OsEnv.DATA_DIR) / "plugin_data"
        plugin_resources: List[PluginResourceInfo] = []
        total_size = 0
        total_files = 0

        if plugin_data_dir.exists():
            try:
                # 遍历插件数据目录
                for plugin_dir in plugin_data_dir.iterdir():
                    if not plugin_dir.is_dir():
                        continue

                    plugin_key = plugin_dir.name
                    plugin_size, plugin_file_count = await self._scan_directory_simple(plugin_dir)

                    # 尝试获取插件名称
                    plugin_name = None
                    plugin = plugin_collector.get_plugin(plugin_key)
                    if plugin:
                        plugin_name = plugin.name

                    plugin_resources.append(
                        PluginResourceInfo(
                            plugin_key=plugin_key,
                            plugin_name=plugin_name,
                            total_size=plugin_size,
                            file_count=plugin_file_count,
                        ),
                    )

                    total_size += plugin_size
                    total_files += plugin_file_count

                    # 每处理完一个插件目录让出控制权
                    await asyncio.sleep(0)

            except Exception as e:
                logger.warning(f"扫描插件数据失败: {e}")

        return ResourceCategory(
            resource_type=ResourceType.PLUGIN_DATA,
            display_name="插件数据",
            description="插件的配置和存储数据",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=False,
            risk_level="danger",
            risk_message="清理插件数据可能导致插件工作异常，暂时不支持清理",
            supports_time_filter=False,
            plugin_resources=plugin_resources,
            i18n_display_name=i18n_text(zh_CN="插件数据", en_US="Plugin Data"),
            i18n_description=i18n_text(
                zh_CN="插件的配置和存储数据",
                en_US="Plugin configuration and storage data",
            ),
            i18n_risk_message=i18n_text(
                zh_CN="清理插件数据可能导致插件工作异常，暂时不支持清理",
                en_US="Cleaning plugin data may cause plugins to malfunction, not supported yet",
            ),
        )

    async def _scan_app_logs(self) -> ResourceCategory:
        """扫描应用日志"""
        directory = Path(APP_LOG_DIR)
        total_size, total_files = await self._scan_directory_simple(directory)

        return ResourceCategory(
            resource_type=ResourceType.APP_LOGS,
            display_name="应用日志",
            description="系统运行日志文件",
            total_size=total_size,
            file_count=total_files,
            can_cleanup=False,
            risk_level="warning",
            risk_message="暂不支持清理应用日志文件",
            supports_time_filter=False,
            i18n_display_name=i18n_text(zh_CN="应用日志", en_US="Application Logs"),
            i18n_description=i18n_text(
                zh_CN="系统运行日志文件",
                en_US="System runtime log files",
            ),
            i18n_risk_message=i18n_text(
                zh_CN="暂不支持清理应用日志文件",
                en_US="Cleaning application logs is not supported yet",
            ),
        )

    async def _calculate_other_data(self, disk_info: DiskInfo, categories: List[ResourceCategory]) -> ResourceCategory:
        """计算其他数据大小

        Args:
            disk_info: 磁盘信息
            categories: 已扫描的分类列表

        Returns:
            ResourceCategory: 其他数据分类
        """
        # 计算已统计的总大小
        scanned_size = sum(c.total_size for c in categories)

        # 其他数据 = DATA_DIR总大小 - 已统计大小
        other_size = max(0, disk_info.data_dir_size - scanned_size)

        return ResourceCategory(
            resource_type=ResourceType.OTHER_DATA,
            display_name="其他数据",
            description="其他系统运行数据",
            total_size=other_size,
            file_count=0,
            can_cleanup=False,
            risk_level="danger",
            risk_message="未识别清理风险的其他数据或关键系统数据，不建议清理",
            supports_time_filter=False,
            chat_resources=[],
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN="其他数据", en_US="Other Data"),
            i18n_description=i18n_text(
                zh_CN="其他系统运行数据",
                en_US="Other system runtime data",
            ),
            i18n_risk_message=i18n_text(
                zh_CN="未识别清理风险的其他数据或关键系统数据，不建议清理",
                en_US="Unidentified data with cleanup risks or critical system data, not recommended to clean",
            ),
        )

    def _create_empty_category(self, resource_type: ResourceType, error_message: str = "") -> ResourceCategory:
        """创建空的资源分类

        Args:
            resource_type: 资源类型
            error_message: 错误信息

        Returns:
            ResourceCategory: 空的资源分类
        """
        return ResourceCategory(
            resource_type=resource_type,
            display_name=resource_type.value,
            description="扫描失败",
            total_size=0,
            file_count=0,
            can_cleanup=False,
            risk_level="danger",
            risk_message=error_message or None,
            supports_time_filter=False,
            chat_resources=[],
            plugin_resources=[],
            i18n_display_name=i18n_text(zh_CN=resource_type.value, en_US=resource_type.value),
            i18n_description=i18n_text(zh_CN="扫描失败", en_US="Scan failed"),
            i18n_risk_message=i18n_text(zh_CN=error_message, en_US=error_message) if error_message else None,
        )

    async def _save_scan_result(self, result: ScanResult) -> None:
        """保存扫描结果

        Args:
            result: 扫描结果
        """
        try:
            SCAN_RESULT_FILE.write_text(
                json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"保存扫描结果失败: {e}")

    async def _save_scan_status(self) -> None:
        """保存扫描状态"""
        try:
            status_data = {
                "scan_id": self._current_scan_id,
                "status": self._scan_status.value,
                "progress": self._scan_progress,
                "current_category": self._current_category,
            }
            SCAN_STATUS_FILE.write_text(
                json.dumps(status_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"保存扫描状态失败: {e}")

    def _get_status_message(self) -> str:
        """获取状态消息

        Returns:
            str: 状态消息
        """
        if self._scan_status == ScanStatus.SCANNING:
            return f"正在扫描: {self._current_category or '准备中'}"
        if self._scan_status == ScanStatus.COMPLETED:
            return "扫描完成"
        if self._scan_status == ScanStatus.FAILED:
            return "扫描失败"
        return "空闲"

    async def get_scan_progress(self) -> Dict:
        """获取扫描进度

        Returns:
            Dict: 包含状态、进度和消息的字典
        """
        return {
            "status": self._scan_status.value,
            "progress": self._scan_progress,
            "message": self._get_status_message(),
        }

    async def load_scan_result_from_cache(self) -> Optional[ScanResult]:
        """从缓存文件加载扫描结果

        Returns:
            Optional[ScanResult]: 扫描结果，如果缓存不存在则返回None
        """
        try:
            if not SCAN_RESULT_FILE.exists():
                logger.debug("扫描结果缓存文件不存在")
                return None

            content = SCAN_RESULT_FILE.read_text(encoding="utf-8")
            data = json.loads(content)
            result = ScanResult.model_validate(data)
            logger.info("从缓存加载扫描结果成功")
        except Exception as e:
            logger.error(f"从缓存加载扫描结果失败: {e}")
            return None
        else:
            return result


# 全局扫描服务实例
scanner_service = ScannerService()
