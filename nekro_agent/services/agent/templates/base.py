from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, PrivateAttr

env = Environment(loader=FileSystemLoader("nekro_agent/services/agent/templates/j2"), auto_reload=False)

T = TypeVar("T", bound="PromptTemplate")


def register_template(template_name: str, macro_name: Optional[str] = None) -> Callable[[Type[T]], Type[T]]:
    """注册模板装饰器

    Args:
        template_name: 模板文件路径
        macro_name: 宏名称，可选
    """

    def decorator(cls: Type[T]) -> Type[T]:
        # 使用 PrivateAttr 设置私有属性
        cls._template_name = PrivateAttr(default=template_name)
        cls._macro_name = PrivateAttr(default=macro_name)
        # 同时存储原始值为类属性，便于访问
        cls._template_name_str = template_name  # type: ignore
        cls._macro_name_str = macro_name  # type: ignore
        return cls

    return decorator


class PromptTemplate(BaseModel):
    """提示模板基类"""

    _template_name: str = PrivateAttr()
    _macro_name: Optional[str] = PrivateAttr()

    def render(self) -> str:
        """渲染模板"""
        # 使用类属性访问模板名和宏名
        template = env.get_template(self.__class__._template_name_str)  # type: ignore # noqa: SLF001
        data = {k: v for k, v in self.model_dump().items() if not k.startswith("_")}

        macro_name = self.__class__._macro_name_str  # type: ignore  # noqa: SLF001
        if macro_name:
            # 如果指定了宏，调用对应的宏
            macro = getattr(template.module, macro_name)
            return macro(**data)

        # 否则直接渲染模板
        return template.render(**data)
