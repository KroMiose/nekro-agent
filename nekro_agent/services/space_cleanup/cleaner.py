
"""空间清理服务"""

import asyncio
import json
import stat
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import (
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
from nekro_agent.schemas.space_cleanup import (
    CleanupProgress,
    CleanupRequest,
    CleanupResult,
    CleanupStatus,
    ResourceType,
)

# 清理任务缓存目录

logger = get_sub_logger("space_cleanup")
CLEANUP_CACHE_DIR = Path(APP_SYSTEM_DIR) / "space_cleanup" / "tasks"
CLEANUP_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_datetime(dt: datetime) -> datetime:
    """规范化 datetime，确保是 timezone-naive（本地时间）

    Args:
        dt: datetime 对象

    Returns:
        datetime: timezone-naive 的 datetime
    """
    if dt.tzinfo is not None:
        # 如果是 timezone-aware，转换为本地时间（timezone-naive）
        return dt.astimezone().replace(tzinfo=None)
    return dt


def _remove_readonly(func, path, _):
    """错误处理函数，用于删除只读文件"""
    try:
        Path(path).chmod(stat.S_IWRITE)
        func(path)
    except Exception as e:
        logger.warning(f"无法删除文件 {path}: {e}")


class CleanupService:
    """空间清理服务"""

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._task_progress: Dict[str, CleanupProgress] = {}
        self._task_results: Dict[str, CleanupResult] = {}

    async def create_cleanup_task(self, request: CleanupRequest) -> str:
        """创建清理任务

        Args:
            request: 清理请求

        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())

        # 初始化进度
        progress = CleanupProgress(
            task_id=task_id,
            status=CleanupStatus.PENDING,
            progress=0.0,
            processed_files=0,
            total_files=0,
            freed_space=0,
            current_file=None,
            message=None,
        )
        self._task_progress[task_id] = progress
        await self._save_task_progress(task_id, progress)

        # 启动清理任务
        task = asyncio.create_task(self._execute_cleanup(task_id, request))
        self._tasks[task_id] = task

        return task_id

    async def get_cleanup_progress(self, task_id: str) -> Optional[CleanupProgress]:
        """获取清理进度

        Args:
            task_id: 任务ID

        Returns:
            Optional[CleanupProgress]: 清理进度，如果任务不存在则返回None
        """
        # 先从内存中获取
        if task_id in self._task_progress:
            return self._task_progress[task_id]

            # 从文件中读取
        progress_file = CLEANUP_CACHE_DIR / f"{task_id}_progress.json"
        if progress_file.exists():
            try:
                data = json.loads(progress_file.read_text(encoding="utf-8"))
                return CleanupProgress.model_validate(data)
            except Exception as e:
                logger.error(f"读取清理进度失败: {e}")

        return None

    async def get_cleanup_result(self, task_id: str) -> Optional[CleanupResult]:
        """获取清理结果

        Args:
            task_id: 任务ID

        Returns:
            Optional[CleanupResult]: 清理结果，如果任务未完成则返回None
        """
        # 先从内存中获取
        if task_id in self._task_results:
            return self._task_results[task_id]

        # 从文件中读取
        result_file = CLEANUP_CACHE_DIR / f"{task_id}_result.json"
        if result_file.exists():
            try:
                data = json.loads(result_file.read_text(encoding="utf-8"))
                return CleanupResult.model_validate(data)
            except Exception as e:
                logger.error(f"读取清理结果失败: {e}")

        return None

    async def _execute_cleanup(self, task_id: str, request: CleanupRequest) -> None:
        """执行清理任务

        Args:
            task_id: 任务ID
            request: 清理请求
        """
        start_time = datetime.now()
        deleted_files = 0
        failed_files = 0
        freed_space = 0
        failed_file_list: List[str] = []

        try:
            # 更新状态为运行中
            progress = self._task_progress[task_id]
            progress.status = CleanupStatus.RUNNING
            await self._save_task_progress(task_id, progress)

            # 收集要清理的文件
            files_to_clean = await self._collect_files_to_clean(request)
            total_files = len(files_to_clean)

            progress.total_files = total_files
            await self._save_task_progress(task_id, progress)

            logger.info(f"开始清理任务 {task_id}, 共 {total_files} 个文件")

            # 不支持时间过滤的资源类型（删除文件后需要清理空目录）
            no_time_filter_types = {
                ResourceType.SANDBOX_SHARED,
                ResourceType.SANDBOX_PIP_CACHE,
                ResourceType.SANDBOX_PACKAGES,
                ResourceType.PLUGIN_DYNAMIC_PACKAGES,
            }

            # 资源类型到目录的映射（用于清理空目录）
            resource_dirs = {
                ResourceType.USER_UPLOADS: Path(USER_UPLOAD_DIR),
                ResourceType.SANDBOX_SHARED: Path(SANDBOX_SHARED_HOST_DIR),
                ResourceType.SANDBOX_PIP_CACHE: Path(SANDBOX_PIP_CACHE_DIR),
                ResourceType.SANDBOX_PACKAGES: Path(SANDBOX_PACKAGE_DIR),
                ResourceType.PLUGIN_DYNAMIC_PACKAGES: Path(PLUGIN_DYNAMIC_PACKAGE_DIR),
                ResourceType.PROMPT_LOGS: Path(PROMPT_LOG_DIR),
                ResourceType.PROMPT_ERROR_LOGS: Path(PROMPT_ERROR_LOG_DIR),
                ResourceType.NAPCAT_TEMP: Path(NAPCAT_TEMPFILE_DIR),
            }

            # 逐个删除文件
            for idx, file_path in enumerate(files_to_clean):
                progress.current_file = str(file_path)
                progress.processed_files = idx + 1
                progress.progress = (idx + 1) / total_files * 100 if total_files > 0 else 100

                if not request.dry_run:
                    try:
                        file_size = file_path.stat().st_size if file_path.exists() else 0
                        success = self._safe_remove_file(file_path)
                        if success:
                            deleted_files += 1
                            freed_space += file_size
                            progress.freed_space = freed_space
                        else:
                            failed_files += 1
                            failed_file_list.append(str(file_path))
                    except Exception as e:
                        logger.warning(f"删除文件失败 {file_path}: {e}")
                        failed_files += 1
                        failed_file_list.append(str(file_path))
                else:
                    # 模拟运行，只统计不删除
                    try:
                        file_size = file_path.stat().st_size if file_path.exists() else 0
                        deleted_files += 1
                        freed_space += file_size
                        progress.freed_space = freed_space
                    except Exception as e:
                        logger.warning(f"统计文件失败 {file_path}: {e}")
                        failed_files += 1
                        failed_file_list.append(str(file_path))

                # 每处理10个文件保存一次进度
                if idx % 10 == 0:
                    await self._save_task_progress(task_id, progress)

            # 对于不支持时间过滤的资源类型，删除文件后清理空目录
            if not request.dry_run:
                for resource_type in request.resource_types:
                    if resource_type not in no_time_filter_types:
                        continue

                    if resource_type not in resource_dirs:
                        continue

                    base_directory = resource_dirs[resource_type]
                    if not base_directory.exists():
                        continue

                    try:
                        await self._cleanup_empty_subdirectories(base_directory)
                    except Exception as e:
                        logger.warning(f"清理空目录失败 {base_directory}: {e}")

            # 完成
            end_time = datetime.now()
            result = CleanupResult(
                task_id=task_id,
                status=CleanupStatus.COMPLETED,
                total_files=total_files,
                deleted_files=deleted_files,
                failed_files=failed_files,
                freed_space=freed_space,
                start_time=start_time,
                end_time=end_time,
                error_message=None,
                duration_seconds=(end_time - start_time).total_seconds(),
                failed_file_list=failed_file_list[:100],  # 最多保存100个失败文件
            )

            self._task_results[task_id] = result
            await self._save_task_result(task_id, result)

            progress.status = CleanupStatus.COMPLETED
            progress.progress = 100.0
            await self._save_task_progress(task_id, progress)

            logger.info(
                f"清理任务完成 {task_id}: 删除 {deleted_files}/{total_files} 个文件, "
                f"释放 {freed_space} 字节, 失败 {failed_files} 个",
            )

        except Exception as e:
            logger.exception(f"清理任务失败 {task_id}: {e}")

            # 保存失败结果
            end_time = datetime.now()
            result = CleanupResult(
                task_id=task_id,
                status=CleanupStatus.FAILED,
                total_files=0,
                deleted_files=deleted_files,
                failed_files=failed_files,
                freed_space=freed_space,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=(end_time - start_time).total_seconds(),
                error_message=str(e),
                failed_file_list=failed_file_list[:100],
            )

            self._task_results[task_id] = result
            await self._save_task_result(task_id, result)

            progress = self._task_progress[task_id]
            progress.status = CleanupStatus.FAILED
            progress.message = str(e)
            await self._save_task_progress(task_id, progress)

    async def _collect_files_to_clean(self, request: CleanupRequest) -> List[Path]:
        """收集要清理的文件

        Args:
            request: 清理请求

        Returns:
            List[Path]: 文件路径列表
        """
        files_to_clean: List[Path] = []

        # 资源类型到目录的映射
        resource_dirs = {
            ResourceType.USER_UPLOADS: Path(USER_UPLOAD_DIR),
            ResourceType.SANDBOX_SHARED: Path(SANDBOX_SHARED_HOST_DIR),
            ResourceType.SANDBOX_PIP_CACHE: Path(SANDBOX_PIP_CACHE_DIR),
            ResourceType.SANDBOX_PACKAGES: Path(SANDBOX_PACKAGE_DIR),
            ResourceType.PLUGIN_DYNAMIC_PACKAGES: Path(PLUGIN_DYNAMIC_PACKAGE_DIR),
            ResourceType.PROMPT_LOGS: Path(PROMPT_LOG_DIR),
            ResourceType.PROMPT_ERROR_LOGS: Path(PROMPT_ERROR_LOG_DIR),
            ResourceType.NAPCAT_TEMP: Path(NAPCAT_TEMPFILE_DIR),
        }

        # 按chat_key组织的资源类型
        chat_based_types = {
            ResourceType.USER_UPLOADS,
            ResourceType.SANDBOX_SHARED,
        }

        data_dir = Path(OsEnv.DATA_DIR).resolve()

        for resource_type in request.resource_types:
            if resource_type not in resource_dirs:
                continue

            directory = resource_dirs[resource_type]
            if not directory.exists():
                continue

            # 验证路径在DATA_DIR内
            try:
                directory = directory.resolve()
                if not directory.is_relative_to(data_dir):
                    logger.warning(f"跳过非法路径: {directory}")
                    continue
            except Exception as e:
                logger.warning(f"路径验证失败 {directory}: {e}")
                continue

            # 按chat_key组织的资源
            if resource_type in chat_based_types:
                files = await self._collect_chat_based_files(directory, request)
            else:
                files = await self._collect_simple_files(directory, request)

            files_to_clean.extend(files)

        return files_to_clean

    async def _collect_chat_based_files(self, directory: Path, request: CleanupRequest) -> List[Path]:
        """收集按chat_key组织的文件

        Args:
            directory: 目录路径
            request: 清理请求

        Returns:
            List[Path]: 文件路径列表
        """
        files: List[Path] = []

        try:
            for chat_dir in directory.iterdir():
                if not chat_dir.is_dir():
                    continue

                chat_key = chat_dir.name

                # 如果是沙盒共享目录，跳过 .pip_cache 和 .packages
                if directory.name == "sandboxes" and chat_key in {".pip_cache", ".packages"}:
                    continue

                # 检查chat_key过滤
                if request.chat_keys and chat_key not in request.chat_keys:
                    continue

                # 收集该聊天目录下的文件
                for file_path in chat_dir.rglob("*"):
                    if file_path.is_file():
                        # 检查时间过滤（使用修改时间）
                        if request.before_date:
                            try:
                                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                                before_date_naive = _normalize_datetime(request.before_date)
                                if file_mtime >= before_date_naive:
                                    continue
                            except (OSError, PermissionError):
                                continue

                        files.append(file_path)

        except Exception as e:
            logger.warning(f"收集文件失败 {directory}: {e}")

        return files

    async def _collect_simple_files(self, directory: Path, request: CleanupRequest) -> List[Path]:
        """收集简单目录下的文件

        Args:
            directory: 目录路径
            request: 清理请求

        Returns:
            List[Path]: 文件路径列表
        """
        files: List[Path] = []

        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    # 检查时间过滤（使用修改时间）
                    if request.before_date:
                        try:
                            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            before_date_naive = _normalize_datetime(request.before_date)
                            if file_mtime >= before_date_naive:
                                continue
                        except (OSError, PermissionError):
                            continue

                    files.append(file_path)

        except Exception as e:
            logger.warning(f"收集文件失败 {directory}: {e}")

        return files

    def _safe_remove_file(self, file_path: Path) -> bool:
        """安全删除文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否成功删除
        """
        if not file_path.exists():
            return True

        if not file_path.is_file():
            return False

        try:
            # 尝试删除
            file_path.unlink()
        except PermissionError:
            # 尝试修改权限后删除
            try:
                file_path.chmod(stat.S_IWRITE)
                file_path.unlink()
            except Exception as e:
                logger.warning(f"删除文件失败（权限问题）{file_path}: {e}")
                return False
            else:
                return True
        except Exception as e:
            logger.warning(f"删除文件失败 {file_path}: {e}")
            return False
        else:
            return True

    async def _cleanup_empty_subdirectories(self, base_directory: Path) -> None:
        """清理基础目录下的空子目录（不包括基础目录本身）

        Args:
            base_directory: 基础目录路径
        """
        if not base_directory.exists():
            return

        try:
            # 从最深层开始删除空目录
            # 使用 rglob 获取所有子目录，按深度从深到浅排序
            # rglob("*") 不会包含基础目录本身，所以不需要额外检查
            all_dirs = [p for p in base_directory.rglob("*") if p.is_dir()]
            # 按路径深度从深到浅排序，确保先删除深层目录
            sorted_dirs = sorted(all_dirs, key=lambda p: len(p.parts), reverse=True)

            for dirpath in sorted_dirs:
                try:
                    # 检查目录是否为空
                    if not any(dirpath.iterdir()):
                        dirpath.rmdir()
                except OSError:
                    # 目录不为空或删除失败，忽略
                    pass
                except Exception as e:
                    logger.warning(f"删除空目录失败 {dirpath}: {e}")

        except Exception as e:
            logger.warning(f"清理空目录失败 {base_directory}: {e}")

    async def _cleanup_empty_directories(self, request: CleanupRequest) -> None:
        """清理空目录

        Args:
            request: 清理请求
        """
        resource_dirs = {
            ResourceType.USER_UPLOADS: Path(USER_UPLOAD_DIR),
            ResourceType.SANDBOX_SHARED: Path(SANDBOX_SHARED_HOST_DIR),
            ResourceType.SANDBOX_PIP_CACHE: Path(SANDBOX_PIP_CACHE_DIR),
            ResourceType.SANDBOX_PACKAGES: Path(SANDBOX_PACKAGE_DIR),
            ResourceType.PLUGIN_DYNAMIC_PACKAGES: Path(PLUGIN_DYNAMIC_PACKAGE_DIR),
            ResourceType.PROMPT_LOGS: Path(PROMPT_LOG_DIR),
            ResourceType.PROMPT_ERROR_LOGS: Path(PROMPT_ERROR_LOG_DIR),
            ResourceType.NAPCAT_TEMP: Path(NAPCAT_TEMPFILE_DIR),
        }

        for resource_type in request.resource_types:
            if resource_type not in resource_dirs:
                continue

            directory = resource_dirs[resource_type]
            if not directory.exists():
                continue

            try:
                await self._cleanup_empty_subdirectories(directory)
            except Exception as e:
                logger.warning(f"清理空目录失败 {directory}: {e}")

    async def _save_task_progress(self, task_id: str, progress: CleanupProgress) -> None:
        """保存任务进度

        Args:
            task_id: 任务ID
            progress: 清理进度
        """
        try:
            progress_file = CLEANUP_CACHE_DIR / f"{task_id}_progress.json"
            progress_file.write_text(
                json.dumps(progress.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"保存任务进度失败: {e}")

    async def _save_task_result(self, task_id: str, result: CleanupResult) -> None:
        """保存任务结果

        Args:
            task_id: 任务ID
            result: 清理结果
        """
        try:
            result_file = CLEANUP_CACHE_DIR / f"{task_id}_result.json"
            result_file.write_text(
                json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"保存任务结果失败: {e}")


# 全局清理服务实例
cleanup_service = CleanupService()
