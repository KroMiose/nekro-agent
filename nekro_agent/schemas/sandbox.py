import json
from typing import Optional

from pydantic import BaseModel

from nekro_agent.services.agent.openai import OpenAIResponse


class SandboxCodeExtData(BaseModel):
    message_cnt: int
    token_consumption: int
    token_input: int
    token_output: int
    chars_count_input: int
    chars_count_output: int
    chars_count_total: int
    use_model: str
    speed_tokens_per_second: float
    speed_chars_per_second: float
    first_token_cost_ms: int
    generation_time_ms: int
    stream_mode: bool
    log_path: str = ""

    @classmethod
    def create_from_llm_response(
        cls,
        llm_response: OpenAIResponse,
    ) -> "SandboxCodeExtData":
        speed_chars_per_second = (
            len(llm_response.response_content) / (llm_response.generation_time_ms / 1000)
            if llm_response.generation_time_ms > 0
            else 0
        )
        speed_chars_per_second = round(speed_chars_per_second, 1)

        prompt_str = ""
        if llm_response.messages:
            for message in llm_response.messages:
                if isinstance(message, dict):
                    content = message.get("content", "")
                    if isinstance(content, str):
                        prompt_str += content
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                prompt_str += item.get("text", "")

        chars_count_input = len(prompt_str)
        chars_count_output = len(llm_response.response_content)
        chars_count_total = chars_count_input + chars_count_output

        return cls(
            message_cnt=llm_response.message_cnt,
            token_consumption=llm_response.token_consumption,
            token_input=llm_response.token_input,
            token_output=llm_response.token_output,
            chars_count_input=chars_count_input,
            chars_count_output=chars_count_output,
            chars_count_total=chars_count_total,
            use_model=llm_response.use_model,
            speed_tokens_per_second=llm_response.speed_tokens_per_second,
            speed_chars_per_second=speed_chars_per_second,
            first_token_cost_ms=llm_response.first_token_cost_ms,
            generation_time_ms=llm_response.generation_time_ms,
            stream_mode=llm_response.stream_mode,
            log_path=str(llm_response.log_path) if llm_response.log_path else "",
        )

    def model_dump_json(self) -> str:
        return json.dumps(self.model_dump(), ensure_ascii=False)
