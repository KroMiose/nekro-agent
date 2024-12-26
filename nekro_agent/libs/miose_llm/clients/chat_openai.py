import warnings
from typing import Any, Dict, List, Optional, Tuple

import httpx
import openai
import pkg_resources

from ..creators.base import BasePromptCreator
from ..creators.openai import OpenAIPromptCreator
from ..exceptions import (
    InvalidCredentialException,
    QuotaLimitException,
    RequestTimeoutException,
)
from .base import BaseClient, ClientResponse

_OPENAI_PROXY: Optional[str] = None
_OPENAI_BASE_URL = "https://api.openai.com/v1"

__openai_version = pkg_resources.get_distribution("openai").version

if __openai_version < "0.27.0":
    raise ImportError("openai 版本过低，请升级至 0.27.0 或以上版本")
if __openai_version > "0.28.0":  # 低版本 openai 兼容
    from openai import AsyncOpenAI  # type: ignore
    from openai.types.chat.chat_completion import ChatCompletion

    openai.api_base = _OPENAI_BASE_URL  # type: ignore
else:
    warnings.warn(
        "openai 版本过低，请注意升级至 1.0.0 或以上版本，以避免兼容性问题",
        stacklevel=2,
    )


def set_openai_proxy(proxy: Optional[str]) -> None:
    global _OPENAI_PROXY
    if proxy:
        if not proxy.startswith("http"):
            proxy = f"http://{proxy}"
        _OPENAI_PROXY = proxy
    else:
        _OPENAI_PROXY = None


def set_openai_base_url(base_url: str) -> None:
    global _OPENAI_BASE_URL
    _OPENAI_BASE_URL = base_url

    if __openai_version <= "0.28.0":
        openai.api_base = _OPENAI_BASE_URL  # type: ignore
    else:
        openai.base_url = _OPENAI_BASE_URL  # type: ignore


set_openai_base_url(_OPENAI_BASE_URL)


async def gen_openai_chat_response(
    model: str,
    messages: List[Dict],
    temperature: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    top_p: Optional[float] = None,
    stop_words: Optional[List[str]] = None,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
) -> Tuple[str, int]:
    """生成聊天回复内容"""

    try:
        if __openai_version <= "0.28.0":
            openai.api_key = api_key
            openai.proxy = _OPENAI_PROXY  # type: ignore

            res = openai.ChatCompletion.create(  # type: ignore
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                max_tokens=max_tokens,
                stop=stop_words,
            )

            output = res.choices[0].message.content  # type: ignore
            token_consumption = res.usage.total_tokens  # type: ignore
            assert output, "Chat response is empty"
            return output, token_consumption

        client: AsyncOpenAI = AsyncOpenAI(  # type: ignore
            api_key=api_key,
            base_url=_OPENAI_BASE_URL,
            http_client=(
                httpx.AsyncClient(
                    proxy=_OPENAI_PROXY,
                )
                if _OPENAI_PROXY
                else None
            ),
        )

        res: ChatCompletion = await client.chat.completions.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop_words,
        )

        output = res.choices[0].message.content
        token_consumption: int = res.usage.total_tokens if res.usage else -1
        assert output, "Chat response is empty"
        return output, token_consumption  # noqa: TRY300

    except httpx.TimeoutException:
        raise RequestTimeoutException from None
    except Exception as e:
        if "You exceeded your current quota" in str(e):
            raise InvalidCredentialException from e  # 只有抛出该异常才会触发更换 API key 重试
        if "You have exceeded your API usage limit" in str(e):
            raise QuotaLimitException from e
        raise


class OpenAIChatClient(BaseClient):
    """OpenAI 聊天客户端"""

    supported_creator = OpenAIPromptCreator

    def __init__(
        self,
        model: str,
        temperature: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_words: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        proxy: Optional[str] = None,
    ):
        self.model = model
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.top_p = top_p
        self.stop_words = stop_words
        self.max_tokens = max_tokens
        self.api_key = api_key
        if base_url is not None:
            set_openai_base_url(base_url)
        if proxy is not None:
            set_openai_proxy(proxy)

    async def call(self, creator: BasePromptCreator, cr: ClientResponse):
        """调用聊天 API"""

        if not isinstance(creator, self.supported_creator):
            raise TypeError("Creator not supported by this client")

        messages: List[Dict[str, Any]] = await creator.render()

        if cr.test_output:
            cr.update_token_info(total_tokens=25565)
            cr.finish(
                prompt_text=creator.transform_prompt(messages),
                response_text=cr.test_output,
            )
            return cr

        output_str, token_consumption = await gen_openai_chat_response(
            model=self.model,
            messages=messages,
            temperature=(self.temperature if creator.temperature is None else creator.temperature),
            frequency_penalty=(self.frequency_penalty if creator.frequency_penalty is None else creator.frequency_penalty),
            presence_penalty=(self.presence_penalty if creator.presence_penalty is None else creator.presence_penalty),
            top_p=self.top_p if creator.top_p is None else creator.top_p,
            stop_words=(self.stop_words if creator.stop_words is None else creator.stop_words),
            max_tokens=(self.max_tokens if creator.max_tokens is None else creator.max_tokens),
            api_key=self.api_key,
        )

        cr.update_token_info(total_tokens=token_consumption)
        cr.finish(
            prompt_text=creator.transform_prompt(messages),
            response_text=output_str,
        )
        return cr
