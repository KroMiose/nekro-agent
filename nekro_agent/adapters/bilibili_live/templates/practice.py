from jinja2 import Environment, FileSystemLoader

from nekro_agent.services.agent.templates.base import register_template
from nekro_agent.services.agent.templates.practice import (
    BasePracticePrompt_question,
    BasePracticePrompt_response,
)


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