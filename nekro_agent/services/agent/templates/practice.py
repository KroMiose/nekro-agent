from .base import PromptTemplate, register_template


class BasePracticePrompt_question(PromptTemplate):
    """对话示例问题基类"""
    one_time_code: str


class BasePracticePrompt_response(PromptTemplate):
    """对话示例回答基类"""
    one_time_code: str
    enable_cot: bool
    enable_at: bool


@register_template("practice.j2", "practice_question_1")
class PracticePrompt_question_1(BasePracticePrompt_question):
    pass


@register_template("practice.j2", "practice_response_1")
class PracticePrompt_response_1(BasePracticePrompt_response):
    pass


@register_template("practice.j2", "practice_question_2")
class PracticePrompt_question_2(BasePracticePrompt_question):
    pass


@register_template("practice.j2", "practice_response_2")
class PracticePrompt_response_2(BasePracticePrompt_response):
    pass
