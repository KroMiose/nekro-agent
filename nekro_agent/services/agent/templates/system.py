from .base import PromptTemplate, register_template


@register_template("system.j2", "system_prompt")
class SystemPrompt(PromptTemplate):
    one_time_code: str
    bot_qq: str
    chat_preset: str
    chat_key: str
    plugins_prompt: str
    admin_chat_key: str
    enable_cot: bool
