import json
import re
from typing import Any, Dict, Type, TypeVar, Union

from ..exceptions import ComponentRuntimeError
from ..scene import BaseScene, ModelResponse
from .base import BaseComponent

JsonResolverComponentType = TypeVar(
    "JsonResolverComponentType",
    bound="JsonResolverComponent",
)


class JsonResolverComponent(BaseComponent):

    def setup(self, indent: int = 4):
        self._indent = indent
        return self

    @classmethod
    async def render(cls, indent: int = 4) -> str:
        return json.dumps(cls.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    async def example(cls, indent: int = 4) -> str:
        """生成响应格式示例 Prompt"""
        ret: str = f"```json\n{await cls.render(indent)}\n```"
        return ret

    @classmethod
    def to_dict(cls) -> Dict:
        """将组件类的字段转化为字典格式"""
        ret = {}
        for attr in dir(cls):
            if (
                not attr.startswith("p_")
                and not attr.startswith("_")
                and not callable(getattr(cls, attr))
                and (attr not in ["scene", "Params", "params"])
            ):
                attr_value = getattr(cls, attr)
                if isinstance(attr_value, JsonResolverComponent) and hasattr(
                    attr_value,
                    "to_dict",
                ):
                    ret[attr] = attr_value.to_dict()  # type: ignore
                elif (  # 基本类型
                    isinstance(attr_value, (str, int, float, bool))
                    or attr_value is None
                ):
                    ret[attr] = attr_value
        return ret

    def resolve_from_text(
        self: JsonResolverComponentType,
        response_text: str,
    ) -> JsonResolverComponentType:
        """解析模型响应"""

        data = withdraw_json(response_text)
        return self.resolve_from_data(data)

    def resolve_from_data(
        self: JsonResolverComponentType,
        data: Any,
    ) -> JsonResolverComponentType:
        """从字典数据中初始化组件"""

        obj = self.__class__(self.scene)
        if isinstance(data, dict):
            for key, value in data.items():
                annotation_type = self.__annotations__.get(key)
                if isinstance(annotation_type, Type):
                    if issubclass(
                        annotation_type,
                        JsonResolverComponent,
                    ):
                        sub_obj = annotation_type(self.scene)
                        setattr(obj, key, sub_obj.resolve_from_data(value))
                    else:
                        setattr(obj, key, value)
                else:
                    raise ComponentRuntimeError(
                        f"Invalid annotation type: {annotation_type}",
                    )
        else:
            raise ComponentRuntimeError(f"Invalid data type: {type(data)}")
        return obj


def withdraw_json(s: str) -> Any:
    """提取返回文本中的 JSON 内容"""

    s = s.strip()

    try:
        s = json.loads(s)
    except json.JSONDecodeError:
        pass
    else:
        return s

    if re.match(r"^```json\n(.*?)\n```$", s, re.DOTALL):
        s = re.match(r"^```json\n(.*?)\n```$", s, re.DOTALL).group(1)  # type: ignore
    elif re.match(r"^```JSON\n(.*?)\n```$", s, re.DOTALL):
        s = re.match(r"^```JSON\n(.*?)\n```$", s, re.DOTALL).group(1)  # type: ignore
    else:
        raise ComponentRuntimeError("Cannot find JSON content in the response.")

    try:
        s = json.loads(s)
    except json.JSONDecodeError as e:
        raise ComponentRuntimeError(f"Invalid JSON format: {e}") from e
    else:
        return s
