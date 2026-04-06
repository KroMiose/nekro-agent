import re
from typing import List, Union

from pydantic import BaseModel


AT_PATTERN = re.compile(r"\[@id:(\S+?)(?:;nickname:(.*?))?@\]")


class SegAt(BaseModel):
    platform_user_id: str
    nickname: str = ""


def parse_at_from_text(text: str) -> List[Union[str, SegAt]]:
    result: List[Union[str, SegAt]] = []
    start = 0

    while True:
        match = AT_PATTERN.search(text, start)
        if not match:
            if start < len(text):
                result.append(text[start:])
            break

        if match.start() > start:
            result.append(text[start : match.start()])

        platform_user_id = match.group(1).strip()
        nickname = (match.group(2) or "").strip()
        if platform_user_id:
            result.append(SegAt(platform_user_id=platform_user_id, nickname=nickname))
        else:
            result.append(match.group(0))

        start = match.end()

    return [item for item in result if item]
