from typing import Optional

from nekro_agent.services.agent.templates.base import PromptTemplate, register_template


@register_template("generator.j2", "system_prompt")
class GeneratorSystemPrompt(PromptTemplate):
    """插件生成系统提示模板"""



@register_template("generator.j2", "user_prompt")
class GeneratorUserPrompt(PromptTemplate):
    """插件生成用户提示模板"""

    prompt: str
    current_code: Optional[str] = None


@register_template("generator.j2", "apply_system_prompt")
class ApplySystemPrompt(PromptTemplate):
    """代码应用系统提示模板"""



@register_template("generator.j2", "apply_user_prompt")
class ApplyUserPrompt(PromptTemplate):
    """代码应用用户提示模板"""

    current_code: str
    prompt: str
