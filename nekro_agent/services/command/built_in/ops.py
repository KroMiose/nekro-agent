"""内置命令 - 运维类: clear_sandbox_cache, docker_restart, docker_logs, sh, instance_id, github_stars_check, log_err_list"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated

from nekro_agent.schemas.i18n import i18n_text, t
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class ClearSandboxCacheCommand(BaseCommand):
    """清理沙盒缓存"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="clear_sandbox_cache",
            aliases=["clear-sandbox-cache", "na_csc", "na-csc"],
            description="清理沙盒环境缓存",
            i18n_description=i18n_text(zh_CN="清理沙盒环境缓存", en_US="Clear sandbox environment cache"),
            permission=CommandPermission.SUPER_USER,
            category="运维",
            i18n_category=i18n_text(zh_CN="运维", en_US="Operations"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.core.os_env import SANDBOX_PACKAGE_DIR, SANDBOX_PIP_CACHE_DIR

        cleared_size = 0
        cleared_files = 0

        for cache_dir in [SANDBOX_PIP_CACHE_DIR, SANDBOX_PACKAGE_DIR]:
            cache_path = Path(cache_dir)
            if cache_path.exists():
                for root, _, files in os.walk(cache_dir):
                    root_path = Path(root)
                    for file in files:
                        file_path = root_path / file
                        try:
                            cleared_size += file_path.stat().st_size
                            file_path.unlink()
                            cleared_files += 1
                        except Exception:
                            pass

                for item in cache_path.iterdir():
                    if item.is_dir():
                        try:
                            shutil.rmtree(item)
                        except Exception:
                            pass

        Path(SANDBOX_PIP_CACHE_DIR).mkdir(parents=True, exist_ok=True)
        Path(SANDBOX_PACKAGE_DIR).mkdir(parents=True, exist_ok=True)

        size_in_mb = cleared_size / (1024 * 1024)
        return CmdCtl.success(
            t(
                zh_CN=f"沙盒缓存清理完成！\n已清理文件：{cleared_files} 个\n释放空间：{size_in_mb:.2f} MB",
                en_US=f"Sandbox cache cleared!\nFiles removed: {cleared_files}\nSpace freed: {size_in_mb:.2f} MB",
            )
        )


class DockerRestartCommand(BaseCommand):
    """重启 Docker 容器"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="docker_restart",
            aliases=["docker-restart"],
            description="重启 Docker 容器",
            i18n_description=i18n_text(zh_CN="重启 Docker 容器", en_US="Restart Docker container"),
            usage="docker_restart [container_name]",
            permission=CommandPermission.ADVANCED,
            category="运维",
            i18n_category=i18n_text(zh_CN="运维", en_US="Operations"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        container: Annotated[str, Arg("容器名称", positional=True)] = "nekro_agent",
    ) -> CommandResponse:
        from nekro_agent.core.os_env import OsEnv

        if not OsEnv.RUN_IN_DOCKER:
            return CmdCtl.failed(
                t(zh_CN="当前环境不在 Docker 容器中，无法执行此操作", en_US="Not running in Docker, cannot perform this operation")
            )

        os.system(f"docker restart {container}")  # noqa: S605
        return CmdCtl.success(
            t(zh_CN=f"已发送重启命令: docker restart {container}", en_US=f"Restart command sent: docker restart {container}")
        )


class DockerLogsCommand(BaseCommand):
    """获取 Docker 容器日志"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="docker_logs",
            aliases=["docker-logs"],
            description="获取 Docker 容器日志",
            i18n_description=i18n_text(zh_CN="获取 Docker 容器日志", en_US="Get Docker container logs"),
            usage="docker_logs [container_name]",
            permission=CommandPermission.ADVANCED,
            category="运维",
            i18n_category=i18n_text(zh_CN="运维", en_US="Operations"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        container: Annotated[str, Arg("容器名称", positional=True)] = "nekro_agent",
    ) -> CommandResponse:
        from nekro_agent.core.os_env import OsEnv

        if not OsEnv.RUN_IN_DOCKER:
            return CmdCtl.failed(
                t(zh_CN="当前环境不在 Docker 容器中，无法执行此操作", en_US="Not running in Docker, cannot perform this operation")
            )

        logs = os.popen(f"docker logs {container} --tail 100").read()  # noqa: S605
        return CmdCtl.success(
            t(zh_CN=f"容器日志: \n{logs}", en_US=f"Container logs: \n{logs}")
        )


class ShCommand(BaseCommand):
    """执行 Shell 命令"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="sh",
            description="执行 Shell 命令",
            i18n_description=i18n_text(zh_CN="执行 Shell 命令", en_US="Execute Shell command"),
            usage="sh <command>",
            permission=CommandPermission.ADVANCED,
            category="运维",
            i18n_category=i18n_text(zh_CN="运维", en_US="Operations"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        command: Annotated[str, Arg("Shell 命令", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        if not command:
            return CmdCtl.failed(t(zh_CN="请输入要执行的命令", en_US="Please enter a command to execute"))

        outputs = os.popen(command).read()  # noqa: S605
        return CmdCtl.success(
            t(zh_CN=f"命令 `{command}` 输出: \n{outputs or '<Empty>'}", en_US=f"Command `{command}` output: \n{outputs or '<Empty>'}")
        )


class InstanceIdCommand(BaseCommand):
    """获取实例唯一 ID"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="instance_id",
            aliases=["instance-id", "na_instance_id", "na-instance-id"],
            description="获取实例唯一 ID",
            i18n_description=i18n_text(zh_CN="获取实例唯一 ID", en_US="Get instance unique ID"),
            permission=CommandPermission.SUPER_USER,
            category="运维",
            i18n_category=i18n_text(zh_CN="运维", en_US="Operations"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.core.config import config
        from nekro_agent.tools.telemetry_util import generate_instance_id, is_running_in_docker

        instance_id = generate_instance_id()

        title = t(zh_CN="[实例ID信息]", en_US="[Instance ID Info]")
        id_label = t(zh_CN="实例ID", en_US="Instance ID")
        env_label = t(zh_CN="运行环境", en_US="Environment")
        docker_env = t(zh_CN="Docker容器", en_US="Docker Container")
        local_env = t(zh_CN="本地环境", en_US="Local Environment")
        enabled = t(zh_CN="已启用", en_US="Enabled")
        disabled = t(zh_CN="未启用", en_US="Disabled")

        return CmdCtl.success(
            f"{title}\n"
            f"{id_label}: {instance_id}\n"
            f"{env_label}: {docker_env if is_running_in_docker() else local_env}\n"
            f"NekroCloud: {enabled if config.ENABLE_NEKRO_CLOUD else disabled}"
        )


class GithubStarsCheckCommand(BaseCommand):
    """检查 GitHub Star 状态"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="github_stars_check",
            aliases=["github-stars-check"],
            description="检查 GitHub Star 状态",
            i18n_description=i18n_text(zh_CN="检查 GitHub Star 状态", en_US="Check GitHub Star status"),
            permission=CommandPermission.SUPER_USER,
            category="运维",
            i18n_category=i18n_text(zh_CN="运维", en_US="Operations"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.systems.cloud.api.auth import check_official_repos_starred

        try:
            result = await check_official_repos_starred()

            if not result.success:
                return CmdCtl.failed(
                    t(zh_CN=f"检查GitHub Star状态失败: {result.message}", en_US=f"Failed to check GitHub Star status: {result.message}")
                )

            if not result.data:
                return CmdCtl.failed(t(zh_CN="获取Star状态数据为空", en_US="Star status data is empty"))

            starred = ", ".join(result.data.starred_repositories) if result.data.starred_repositories else t(zh_CN="无", en_US="None")
            unstarred = ", ".join(result.data.unstarred_repositories) if result.data.unstarred_repositories else t(zh_CN="无", en_US="None")
            status = t(zh_CN="已Star所有官方仓库", en_US="All official repos starred") if result.data.all_starred else t(zh_CN="还有未Star的官方仓库", en_US="Some official repos not starred")

            title = t(zh_CN="[GitHub Star 状态]", en_US="[GitHub Star Status]")
            status_label = t(zh_CN="状态", en_US="Status")
            starred_label = t(zh_CN="已Star", en_US="Starred")
            unstarred_label = t(zh_CN="未Star", en_US="Not Starred")
            return CmdCtl.success(f"{title}\n{status_label}: {status}\n{starred_label}: {starred}\n{unstarred_label}: {unstarred}")
        except Exception as e:
            return CmdCtl.failed(t(zh_CN=f"执行失败: {e}", en_US=f"Execution failed: {e}"))


class LogErrListCommand(BaseCommand):
    """查看错误日志列表"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="log_err_list",
            aliases=["log-err-list", "log_err_ls", "log-err-ls"],
            description="查看错误日志列表",
            i18n_description=i18n_text(zh_CN="查看错误日志列表", en_US="View error log list"),
            usage="log_err_list [-p <页码>] [-s <每页数量>] [-a]",
            permission=CommandPermission.SUPER_USER,
            category="运维",
            i18n_category=i18n_text(zh_CN="运维", en_US="Operations"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        args_str: Annotated[str, Arg("参数", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.core.os_env import PROMPT_ERROR_LOG_DIR
        from nekro_agent.services.agent.run_agent import RECENT_ERR_LOGS

        args = args_str.strip().split() if args_str else []
        page = 1
        page_size = 10
        use_dir_files = False

        for i, arg in enumerate(args):
            if arg == "-p" and i + 1 < len(args):
                try:
                    page = int(args[i + 1])
                except ValueError:
                    return CmdCtl.failed(t(zh_CN="分页参数格式错误", en_US="Invalid page parameter format"))
            elif arg == "-s" and i + 1 < len(args):
                try:
                    page_size = int(args[i + 1])
                except ValueError:
                    return CmdCtl.failed(t(zh_CN="每页显示数量参数格式错误", en_US="Invalid page size parameter format"))
            elif arg in ("-a", "--all"):
                use_dir_files = True

        page = max(1, page)
        page_size = max(1, min(50, page_size))

        if use_dir_files:
            log_dir = Path(PROMPT_ERROR_LOG_DIR)
            if not log_dir.exists():
                return CmdCtl.failed(t(zh_CN="错误日志目录不存在", en_US="Error log directory does not exist"))
            logs = sorted(log_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        else:
            logs = list(RECENT_ERR_LOGS)

        total_logs = len(logs)
        total_pages = (total_logs + page_size - 1) // page_size if total_logs > 0 else 1
        page = min(page, total_pages)

        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_logs)
        current_page_logs = logs[start_idx:end_idx]

        if not current_page_logs:
            return CmdCtl.success(t(zh_CN="没有错误日志记录", en_US="No error log records"))

        result_lines = [
            t(
                zh_CN=f"错误日志列表 (第 {page}/{total_pages} 页，共 {total_logs} 条):",
                en_US=f"Error log list (page {page}/{total_pages}, total {total_logs}):",
            )
        ]

        for i, log_path in enumerate(current_page_logs, start=start_idx + 1):
            try:
                mod_time = datetime.fromtimestamp(log_path.stat().st_mtime).strftime("%m-%d %H:%M:%S")
                result_lines.append(f"{i}. [{mod_time}] {log_path.name}")
            except Exception:
                result_lines.append(f"{i}. {log_path.name}")

        usage_title = t(zh_CN="\n使用方法:", en_US="\nUsage:")
        result_lines.append(usage_title)
        result_lines.append(
            t(
                zh_CN="log_err_list -p <页码> -s <每页数量>: 查看最近错误日志列表",
                en_US="log_err_list -p <page> -s <page_size>: View recent error log list",
            )
        )
        result_lines.append(
            t(
                zh_CN="log_err_list -a/--all: 查看所有日志文件",
                en_US="log_err_list -a/--all: View all log files",
            )
        )

        return CmdCtl.success("\n".join(result_lines))
