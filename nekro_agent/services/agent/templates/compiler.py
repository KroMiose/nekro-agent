from dataclasses import dataclass
from typing import List, Optional

from jinja2 import Environment

from nekro_agent.core.config import CoreConfig, ModelConfigGroup
from nekro_agent.models.db_chat_channel import DBChatChannel

from ..creator import OpenAIChatMessage
from .base import env as default_env
from .history import HistoryFirstStart, render_history_data
from .practice import (
    BasePracticePrompt_question,
    BasePracticePrompt_response,
    PracticePrompt_question_1,
    PracticePrompt_question_2,
    PracticePrompt_response_1,
    PracticePrompt_response_2,
)
from .system import PersonaPrompt, PolicyKernelPrompt, RuntimeContractPrompt, SystemPrompt

EXAMPLE_SESSION_TOKEN = "SESSION_TOKEN"


@dataclass
class PromptSegments:
    stable_static: str
    channel_static: str
    runtime_dynamic: str


class PromptCompiler:
    def __init__(
        self,
        *,
        platform_name: str,
        bot_platform_id: str,
        chat_preset: str,
        plugins_prompt: str,
        plugins_runtime_prompt: str,
        plugin_activation_rules: str,
        enable_cot: bool,
        chat_key_rules: str,
        enable_at: bool,
    ):
        self.platform_name = platform_name
        self.bot_platform_id = bot_platform_id
        self.chat_preset = chat_preset
        self.plugins_prompt = plugins_prompt
        self.plugins_runtime_prompt = plugins_runtime_prompt
        self.plugin_activation_rules = plugin_activation_rules
        self.enable_cot = enable_cot
        self.chat_key_rules = chat_key_rules
        self.enable_at = enable_at

    def compile_segments(self) -> PromptSegments:
        return PromptSegments(
            stable_static=PolicyKernelPrompt().render(default_env),
            channel_static=PersonaPrompt(chat_preset=self.chat_preset).render(default_env),
            runtime_dynamic=RuntimeContractPrompt(
                platform_name=self.platform_name,
                bot_platform_id=self.bot_platform_id,
                enable_cot=self.enable_cot,
                chat_key_rules=self.chat_key_rules,
                enable_at=self.enable_at,
                plugin_activation_rules=self.plugin_activation_rules,
            ).render(default_env),
        )

    def render_system_message(self) -> OpenAIChatMessage:
        segments = self.compile_segments()
        return OpenAIChatMessage.from_template(
            "system",
            SystemPrompt(
                stable_static=segments.stable_static,
                channel_static=segments.channel_static,
                runtime_dynamic=segments.runtime_dynamic,
                plugins_prompt=self.plugins_prompt,
            ),
            default_env,
        )

    def render_practice_messages(
        self,
        adapter_dialog_examples: Optional[List[object]],
        adapter_jinja_env: Optional[Environment],
    ) -> List[OpenAIChatMessage]:
        messages: List[OpenAIChatMessage] = []

        if adapter_dialog_examples and adapter_jinja_env:
            for prompt_template in adapter_dialog_examples:
                role = None
                if isinstance(prompt_template, BasePracticePrompt_question):
                    role = "user"
                    prompt_template.one_time_code = EXAMPLE_SESSION_TOKEN
                elif isinstance(prompt_template, BasePracticePrompt_response):
                    role = "assistant"
                    prompt_template.one_time_code = EXAMPLE_SESSION_TOKEN
                    prompt_template.enable_cot = self.enable_cot
                    prompt_template.enable_at = self.enable_at
                else:
                    raise TypeError(f"未知消息类型模板: {prompt_template}")
                messages.append(OpenAIChatMessage.from_template(role, prompt_template, adapter_jinja_env))
            return messages

        return [
            OpenAIChatMessage.from_template("user", PracticePrompt_question_1(one_time_code=EXAMPLE_SESSION_TOKEN), default_env),
            OpenAIChatMessage.from_template(
                "assistant",
                PracticePrompt_response_1(
                    one_time_code=EXAMPLE_SESSION_TOKEN,
                    enable_cot=self.enable_cot,
                    enable_at=self.enable_at,
                ),
                default_env,
            ),
            OpenAIChatMessage.from_template("user", PracticePrompt_question_2(one_time_code=EXAMPLE_SESSION_TOKEN), default_env),
            OpenAIChatMessage.from_template(
                "assistant",
                PracticePrompt_response_2(
                    one_time_code=EXAMPLE_SESSION_TOKEN,
                    enable_cot=self.enable_cot,
                    enable_at=self.enable_at,
                ),
                default_env,
            ),
        ]

    async def render_history_message(
        self,
        *,
        chat_key: str,
        db_chat_channel: DBChatChannel,
        one_time_code: str,
        config: CoreConfig,
        model_group: ModelConfigGroup,
    ) -> OpenAIChatMessage:
        return OpenAIChatMessage.from_template("user", HistoryFirstStart(enable_cot=self.enable_cot), default_env).extend(
            await render_history_data(
                chat_key=chat_key,
                db_chat_channel=db_chat_channel,
                one_time_code=one_time_code,
                plugin_injected_prompt=self.plugins_runtime_prompt,
                model_group=model_group,
                config=config,
            ),
        )
