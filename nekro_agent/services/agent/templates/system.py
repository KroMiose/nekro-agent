from .base import PromptTemplate, register_template


@register_template("policy_kernel.j2", "policy_kernel_prompt")
class PolicyKernelPrompt(PromptTemplate):
    pass


@register_template("runtime_contract.j2", "runtime_contract_prompt")
class RuntimeContractPrompt(PromptTemplate):
    platform_name: str
    bot_platform_id: str
    enable_cot: bool
    chat_key_rules: str
    enable_at: bool
    plugin_activation_rules: str


@register_template("persona.j2", "persona_prompt")
class PersonaPrompt(PromptTemplate):
    chat_preset: str


@register_template("system.j2", "system_prompt")
class SystemPrompt(PromptTemplate):
    stable_static: str
    channel_static: str
    runtime_dynamic: str
    plugins_prompt: str
