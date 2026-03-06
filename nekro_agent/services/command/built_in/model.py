"""内置命令 - 模型类: model_test"""

import re
import time
from collections.abc import AsyncIterator
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
            usage="model_test [model_name] [-g group_name] [--stream] [--use-system]",
            permission=CommandPermission.SUPER_USER,
            category="模型",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        args_str: Annotated[str, Arg("模型名/组名和参数", positional=True, greedy=True)] = "",
    ) -> AsyncIterator[CommandResponse]:
        from nekro_agent.core.config import ModelConfigGroup, config
        from nekro_agent.services.agent.openai import OpenAIResponse, gen_openai_chat_response

        if not args_str:
            yield CmdCtl.failed(
                "用法: model_test [model_name] [-g group_name] [--stream] [--use-system]\n"
                "  model_test gpt-4o          按模型名测试\n"
                "  model_test -g default      按模型组名测试\n"
                "  model_test gpt-4o -g def*  模型名 + 组名筛选\n"
                "  model_test -g *            测试所有模型组"
            )
            return

        parts = args_str.strip().split()
        stream_mode = "--stream" in parts
        use_system = "--use-system" in parts
        filtered_parts = [p for p in parts if p not in ("--stream", "--use-system")]

        # 解析 -g <group_name> 参数
        group_names: list[str] = []
        model_names: list[str] = []
        i = 0
        while i < len(filtered_parts):
            if filtered_parts[i] == "-g" and i + 1 < len(filtered_parts):
                group_names.append(filtered_parts[i + 1])
                i += 2
            elif filtered_parts[i] == "-g":
                i += 1  # -g 后无值，跳过
            else:
                model_names.append(filtered_parts[i])
                i += 1

        if not model_names and not group_names:
            yield CmdCtl.failed("请指定模型名或使用 -g 指定模型组名")
            return

        test_model_groups: list[tuple[str, ModelConfigGroup]] = []

        if group_names and not model_names:
            # 仅指定组名: model_test -g <group_name>
            for gn in group_names:
                if "*" in gn:
                    pattern = gn.replace("*", ".*")
                    test_model_groups.extend(
                        (g, config.MODEL_GROUPS[g])
                        for g in config.MODEL_GROUPS
                        if re.match(pattern, g) and config.MODEL_GROUPS[g].MODEL_TYPE == "chat"
                    )
                elif gn in config.MODEL_GROUPS and config.MODEL_GROUPS[gn].MODEL_TYPE == "chat":
                    test_model_groups.append((gn, config.MODEL_GROUPS[gn]))
        elif model_names and not group_names:
            # 仅指定模型名: model_test <model_name>
            for mn in model_names:
                if "*" in mn:
                    pattern = mn.replace("*", ".*")
                    test_model_groups.extend(
                        (gk, g)
                        for gk, g in config.MODEL_GROUPS.items()
                        if g.MODEL_TYPE == "chat" and re.match(pattern, g.CHAT_MODEL)
                    )
                else:
                    test_model_groups.extend(
                        (gk, g)
                        for gk, g in config.MODEL_GROUPS.items()
                        if mn == g.CHAT_MODEL and g.MODEL_TYPE == "chat"
                    )
        else:
            # 同时指定模型名和组名: model_test <model_name> -g <group_name>
            for mn in model_names:
                for gn in group_names:
                    for group_key, group_cfg in config.MODEL_GROUPS.items():
                        if group_cfg.MODEL_TYPE != "chat":
                            continue
                        model_match = re.match(mn.replace("*", ".*"), group_cfg.CHAT_MODEL) if "*" in mn else (mn == group_cfg.CHAT_MODEL)
                        group_match = re.match(gn.replace("*", ".*"), group_key) if "*" in gn else (gn == group_key)
                        if model_match and group_match:
                            test_model_groups.append((group_key, group_cfg))

        if not test_model_groups:
            yield CmdCtl.failed("未找到符合条件的模型组")
            return

        result_keys: list[str] = []
        success_map: dict[str, int] = {}
        fail_map: dict[str, int] = {}
        speed_map: dict[str, list[float]] = {}

        total = len(test_model_groups)
        yield CmdCtl.message(f"开始测试 {total} 个模型组...")

        for i, (group_key, model_group) in enumerate(test_model_groups, 1):
            label = f"{model_group.CHAT_MODEL} [{group_key}]"
            if label not in success_map:
                result_keys.append(label)
            success_map.setdefault(label, 0)
            fail_map.setdefault(label, 0)
            speed_map.setdefault(label, [])

            yield CmdCtl.message(f"[{i}/{total}] 测试 {label} ...")

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
                elapsed = end_time - start_time
                success_map[label] += 1
                speed_map[label].append(elapsed)
                yield CmdCtl.message(f"[{i}/{total}] ✓ {label} 通过 ({elapsed:.2f}s)")
            except Exception:
                fail_map[label] += 1
                yield CmdCtl.message(f"[{i}/{total}] ✗ {label} 失败")

        result_lines = ["[模型测试结果]"]
        for label in result_keys:
            success = success_map.get(label, 0)
            fail = fail_map.get(label, 0)
            if fail > 0:
                status = "失败"
            elif success > 0:
                status = "通过"
            else:
                status = "未知"

            speed_info = ""
            speeds = speed_map.get(label)
            if speeds:
                avg_speed = sum(speeds) / len(speeds)
                if len(speeds) > 1:
                    speed_info = (
                        f" | 速度: {avg_speed:.2f}s (最快: {min(speeds):.2f}s, 最慢: {max(speeds):.2f}s)"
                    )
                else:
                    speed_info = f" | 速度: {avg_speed:.2f}s"

            result_lines.append(f"{status} {label}: (成功: {success}, 失败: {fail}){speed_info}")

        yield CmdCtl.success("\n".join(result_lines))


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
