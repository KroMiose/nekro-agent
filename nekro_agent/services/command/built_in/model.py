"""内置命令 - 模型类: model_test"""

import re
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any

from nekro_agent.schemas.i18n import i18n_text
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.i18n_helper import t
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class ModelTestCommand(BaseCommand):
    """模型测试"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="model_test",
            aliases=["model-test"],
            description="测试模型连通性和响应速度",
            i18n_description=i18n_text(zh_CN="测试模型连通性和响应速度", en_US="Test model connectivity and response speed"),
            usage="model_test [model_name] [-g group_name] [--stream] [--use-system] [--detail]",
            permission=CommandPermission.SUPER_USER,
            category="模型",
            i18n_category=i18n_text(zh_CN="模型", en_US="Model"),
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
                t(
                    context.lang,
                    zh_CN=(
                        "用法: model_test [model_name] [-g group_name] [--stream] [--use-system] [--detail]\n"
                        "  model_test gpt-4o          按模型名测试\n"
                        "  model_test -g default      按模型组名测试\n"
                        "  model_test gpt-4o -g def*  模型名 + 组名筛选\n"
                        "  model_test -g *            测试所有模型组\n"
                        "  --detail                   显示模型组名等详细信息"
                    ),
                    en_US=(
                        "Usage: model_test [model_name] [-g group_name] [--stream] [--use-system] [--detail]\n"
                        "  model_test gpt-4o          Test by model name\n"
                        "  model_test -g default      Test by model group name\n"
                        "  model_test gpt-4o -g def*  Model name + group filter\n"
                        "  model_test -g *            Test all model groups\n"
                        "  --detail                   Show model group name and details"
                    ),
                )
            )
            return

        parts = args_str.strip().split()
        stream_mode = "--stream" in parts
        use_system = "--use-system" in parts
        detail_mode = "--detail" in parts
        filtered_parts = [p for p in parts if p not in ("--stream", "--use-system", "--detail")]

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
            yield CmdCtl.failed(
                t(context.lang, zh_CN="请指定模型名或使用 -g 指定模型组名", en_US="Please specify model name or use -g to specify model group name")
            )
            return

        test_model_groups: list[tuple[str, ModelConfigGroup]] = []

        if group_names and not model_names:
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
            yield CmdCtl.failed(
                t(context.lang, zh_CN="未找到符合条件的模型组", en_US="No matching model groups found")
            )
            return

        result_keys: list[str] = []
        display_labels: dict[str, str] = {}
        success_map: dict[str, int] = {}
        fail_map: dict[str, int] = {}
        speed_map: dict[str, list[float]] = {}

        total = len(test_model_groups)
        yield CmdCtl.message(
            t(context.lang, zh_CN=f"开始测试 {total} 个模型组...", en_US=f"Starting test for {total} model groups...")
        )

        for i, (group_key, model_group) in enumerate(test_model_groups, 1):
            label = f"{model_group.CHAT_MODEL} [{group_key}]"
            display = label if detail_mode else model_group.CHAT_MODEL
            if label not in success_map:
                result_keys.append(label)
                display_labels[label] = display
            success_map.setdefault(label, 0)
            fail_map.setdefault(label, 0)
            speed_map.setdefault(label, [])

            yield CmdCtl.message(
                t(context.lang, zh_CN=f"[{i}/{total}] 测试 {display} ...", en_US=f"[{i}/{total}] Testing {display} ...")
            )

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
                yield CmdCtl.message(
                    t(context.lang, zh_CN=f"[{i}/{total}] ✓ {display} 通过 ({elapsed:.2f}s)", en_US=f"[{i}/{total}] ✓ {display} passed ({elapsed:.2f}s)")
                )
            except Exception:
                fail_map[label] += 1
                yield CmdCtl.message(
                    t(context.lang, zh_CN=f"[{i}/{total}] ✗ {display} 失败", en_US=f"[{i}/{total}] ✗ {display} failed")
                )

        title = t(context.lang, zh_CN="[模型测试结果]", en_US="[Model Test Results]")
        result_lines = [title]
        for label in result_keys:
            success = success_map.get(label, 0)
            fail = fail_map.get(label, 0)
            if fail > 0:
                status = t(context.lang, zh_CN="❌ 失败", en_US="❌ FAIL")
            elif success > 0:
                status = t(context.lang, zh_CN="✅ 通过", en_US="✅ PASS")
            else:
                status = t(context.lang, zh_CN="⚠️ 未知", en_US="⚠️ UNKNOWN")

            speed_info = ""
            speeds = speed_map.get(label)
            if speeds:
                avg_speed = sum(speeds) / len(speeds)
                speed_label = t(context.lang, zh_CN="速度", en_US="Speed")
                if len(speeds) > 1:
                    fastest = t(context.lang, zh_CN="最快", en_US="fastest")
                    slowest = t(context.lang, zh_CN="最慢", en_US="slowest")
                    speed_info = (
                        f" | {speed_label}: {avg_speed:.2f}s ({fastest}: {min(speeds):.2f}s, {slowest}: {max(speeds):.2f}s)"
                    )
                else:
                    speed_info = f" | {speed_label}: {avg_speed:.2f}s"

            success_label = t(context.lang, zh_CN="成功", en_US="success")
            fail_label = t(context.lang, zh_CN="失败", en_US="fail")
            result_lines.append(f"{status} {display_labels[label]}: ({success_label}: {success}, {fail_label}: {fail}){speed_info}")

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
