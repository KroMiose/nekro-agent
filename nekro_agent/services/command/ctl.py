"""CmdCtl 流式控制器

命令处理函数通过 yield CmdCtl.xxx() 来控制执行流程。
"""

from typing import Optional, Union

from nekro_agent.schemas.i18n import I18nDict, resolve_i18n
from nekro_agent.services.command.schemas import (
    CommandOutputSegment,
    CommandResponse,
    CommandResponseStatus,
)


class CmdCtl:
    """命令流式控制器 - 参考 TaskCtl 模式

    命令处理函数通过 yield CmdCtl.xxx() 来控制执行流程：
    - CmdCtl.message(...)  -> 过程输出，不中断流程
    - CmdCtl.wait(...)     -> 交互挂起，等待用户后续输入
    - CmdCtl.success(...)  -> 成功终态
    - CmdCtl.failed(...)   -> 失败终态

    message / success / failed 的 text 参数支持两种类型：
    - str: 纯文本，直接使用
    - I18nDict (i18n_text 返回值): 按当前系统语言自动解析
    """

    @staticmethod
    def message(
        text: Union[str, I18nDict] = "",
        data: Optional[dict] = None,
        output_segments: Optional[list[CommandOutputSegment]] = None,
    ) -> CommandResponse:
        """过程输出 - 中间状态反馈，不中断命令执行"""
        return CommandResponse(
            status=CommandResponseStatus.PROCESSING,
            message=resolve_i18n(text),
            data=data,
            output_segments=output_segments,
        )

    @staticmethod
    def wait(
        message: str,
        callback_cmd: str,
        options: Optional[list[str]] = None,
        timeout: float = 60.0,
        on_timeout_message: str = "",
        context_data: Optional[dict] = None,
    ) -> CommandResponse:
        """交互等待 - 挂起命令，等待用户选择/输入后路由到 callback_cmd

        Args:
            message: 提示信息
            callback_cmd: 接收后续输入的命令名（需已注册，通常标记 internal=True）
            options: 可选项列表
            timeout: 超时秒数
            on_timeout_message: 超时提示
            context_data: 透传给 callback_cmd 的上下文数据
        """
        return CommandResponse(
            status=CommandResponseStatus.WAITING,
            message=message,
            callback_cmd=callback_cmd,
            wait_options=options,
            wait_timeout=timeout,
            on_timeout_message=on_timeout_message,
            context_data=context_data,
        )

    @staticmethod
    def success(
        message: Union[str, I18nDict] = "",
        data: Optional[dict] = None,
        output_segments: Optional[list[CommandOutputSegment]] = None,
    ) -> CommandResponse:
        """成功终态"""
        return CommandResponse(
            status=CommandResponseStatus.SUCCESS,
            message=resolve_i18n(message),
            data=data,
            output_segments=output_segments,
        )

    @staticmethod
    def failed(
        message: Union[str, I18nDict] = "",
        data: Optional[dict] = None,
        output_segments: Optional[list[CommandOutputSegment]] = None,
    ) -> CommandResponse:
        """失败终态"""
        return CommandResponse(
            status=CommandResponseStatus.ERROR,
            message=resolve_i18n(message),
            data=data,
            output_segments=output_segments,
        )
