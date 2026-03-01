"""内置命令 - 模型类: model_test"""

import re
import time
from typing import Annotated, Any

from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class ModelTestCommand(BaseCommand):
    """模型测试"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="model_test",
            aliases=["model-test"],
            description="测试模型连通性和响应速度",
            usage="model_test <model_name> [-g] [--stream] [--use-system]",
            permission=CommandPermission.USER,
            category="模型",
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        args_str: Annotated[str, Arg("模型名/组名和参数", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.core.config import ModelConfigGroup, config
        from nekro_agent.services.agent.openai import OpenAIResponse, gen_openai_chat_response

        if not args_str:
            return CmdCtl.failed("请指定要测试的模型名 (model_test <model_name1> <model_name2> ...)")

        parts = args_str.strip().split()
        use_group_name = "-g" in parts
        stream_mode = "--stream" in parts
        use_system = "--use-system" in parts

        model_names = [p for p in parts if p not in ("-g", "--stream", "--use-system")]

        if not model_names:
            return CmdCtl.failed("请指定要测试的模型名")

        test_model_groups: list[ModelConfigGroup] = []
        if use_group_name:
            for group_name in model_names:
                if "*" in group_name:
                    pattern = group_name.replace("*", ".*")
                    matching_groups = [g for g in config.MODEL_GROUPS if re.match(pattern, g)]
                    test_model_groups.extend(
                        config.MODEL_GROUPS[g]
                        for g in matching_groups
                        if config.MODEL_GROUPS[g].MODEL_TYPE == "chat"
                    )
                elif group_name in config.MODEL_GROUPS and config.MODEL_GROUPS[group_name].MODEL_TYPE == "chat":
                    test_model_groups.append(config.MODEL_GROUPS[group_name])
        else:
            for model_name in model_names:
                if "*" in model_name:
                    pattern = model_name.replace("*", ".*")
                    test_model_groups.extend(
                        g
                        for g in config.MODEL_GROUPS.values()
                        if g.MODEL_TYPE == "chat" and re.match(pattern, g.CHAT_MODEL)
                    )
                else:
                    test_model_groups.extend(
                        g
                        for g in config.MODEL_GROUPS.values()
                        if model_name == g.CHAT_MODEL and g.MODEL_TYPE == "chat"
                    )

        if not test_model_groups:
            return CmdCtl.failed("未找到符合条件的模型组")

        model_test_success_result_map: dict[str, int] = {}
        model_test_fail_result_map: dict[str, int] = {}
        model_speed_map: dict[str, list[float]] = {}

        for model_group in test_model_groups:
            model_test_success_result_map.setdefault(model_group.CHAT_MODEL, 0)
            model_test_fail_result_map.setdefault(model_group.CHAT_MODEL, 0)
            model_speed_map.setdefault(model_group.CHAT_MODEL, [])

            try:
                start_time = time.time()
                messages: list[dict[str, Any]] = [
                    {"role": "user", "content": "Repeat the following text without any thinking or explanation: Test"}
                ]
                if use_system:
                    messages.insert(
                        0,
                        {"role": "system", "content": "You are a helpful assistant that follows instructions precisely."},
                    )
                llm_response: OpenAIResponse = await gen_openai_chat_response(
                    messages=messages,
                    **_build_chat_params(model_group, stream_mode),
                )
                end_time = time.time()
                assert llm_response.response_content  # noqa: S101
                model_test_success_result_map[model_group.CHAT_MODEL] += 1
                model_speed_map[model_group.CHAT_MODEL].append(end_time - start_time)
            except Exception:
                model_test_fail_result_map[model_group.CHAT_MODEL] += 1

        result_lines = ["[模型测试结果]"]
        for model_name in set(list(model_test_success_result_map.keys()) + list(model_test_fail_result_map.keys())):
            success = model_test_success_result_map.get(model_name, 0)
            fail = model_test_fail_result_map.get(model_name, 0)
            if fail > 0:
                status = "失败"
            elif success > 0:
                status = "通过"
            else:
                status = "未知"

            speed_info = ""
            speeds = model_speed_map.get(model_name)
            if speeds:
                avg_speed = sum(speeds) / len(speeds)
                if len(speeds) > 1:
                    speed_info = (
                        f" | 速度: {avg_speed:.2f}s (最快: {min(speeds):.2f}s, 最慢: {max(speeds):.2f}s)"
                    )
                else:
                    speed_info = f" | 速度: {avg_speed:.2f}s"

            result_lines.append(f"{status} {model_name}: (成功: {success}, 失败: {fail}){speed_info}")

        return CmdCtl.success("\n".join(result_lines))


def _build_chat_params(model_group: Any, stream_mode: bool) -> dict[str, Any]:
    """构建聊天参数"""
    return {
        "model": model_group.CHAT_MODEL,
        "temperature": model_group.TEMPERATURE,
        "top_p": model_group.TOP_P,
        "top_k": model_group.TOP_K,
        "frequency_penalty": model_group.FREQUENCY_PENALTY,
        "presence_penalty": model_group.PRESENCE_PENALTY,
        "extra_body": model_group.EXTRA_BODY,
        "base_url": model_group.BASE_URL,
        "api_key": model_group.API_KEY,
        "stream_mode": stream_mode,
        "proxy_url": model_group.CHAT_PROXY,
    }
