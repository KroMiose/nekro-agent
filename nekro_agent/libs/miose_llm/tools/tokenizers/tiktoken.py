from typing import Dict

from tiktoken import Encoding, encoding_for_model

from .base import BaseTokenizer

enc_cache: Dict[str, Encoding] = {}


class TikTokenizer(BaseTokenizer):

    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model

    def count_tokens(self, text: str) -> int:

        if self.model in enc_cache:
            enc = enc_cache[self.model]
        else:
            enc = encoding_for_model(self.model)
            enc_cache[self.model] = enc

        return len(enc.encode(text))
