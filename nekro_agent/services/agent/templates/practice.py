from .base import PromptTemplate, register_template


@register_template("practice.j2", "practice_question_1")
class PracticePrompt_question_1(PromptTemplate):
    one_time_code: str


@register_template("practice.j2", "practice_response_1")
class PracticePrompt_response_1(PromptTemplate):
    one_time_code: str
    enable_cot: bool


@register_template("practice.j2", "practice_question_2")
class PracticePrompt_question_2(PromptTemplate):
    one_time_code: str


@register_template("practice.j2", "practice_response_2")
class PracticePrompt_response_2(PromptTemplate):
    one_time_code: str
    enable_cot: bool
