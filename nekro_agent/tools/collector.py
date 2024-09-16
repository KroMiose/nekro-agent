from enum import Enum
from typing import Callable, Dict, List, Optional, Set, cast

from nekro_agent.core.logger import logger


class MethodType(str, Enum):
    """方法类型

    用于描述方法的类型，如工具方法, 行为方法等；方法类型区别主要在于对返回值的处理方式。

    * TOOL: 工具方法
        提供给 LLM 使用的工具，返回值可以是任意类型，LLM 可获取返回值作进一步处理

    * BEHAVIOR: 行为方法
        用于描述 LLM 的行为，其返回值必须为 str 类型，描述行为的结果，返回后会被添加到上下文中参考

    * AGENT: 代理方法
        用于提供 LLM 交互反馈，其返回值必须为 str 类型，描述 LLM 行为的结果，返回后会被添加到上下文中再次调用
    """

    TOOL = "tool"
    BEHAVIOR = "behavior"
    AGENT = "agent"


class DocCollector:
    """方法文档收集器

    用于收集面向 AI 使用的文档，并将其转化为可用提示词
    """

    def __init__(self):
        self.tag_map: Dict[str, Set[Callable]] = {}

    def mount_method(self, method_type: MethodType, method_tag: str = ""):
        """方法收集器

        Args:
            method_tag (str): 要收集的接口方法的标签

        Returns:
            Decorator: 收集装饰器
        """

        def decorator(func):
            if method_tag not in self.tag_map:
                self.tag_map[method_tag] = set()
            setattr(func, "_method_type", method_type)  # noqa: B010
            if not func.__doc__:
                logger.warning(f"注册方法 {func.__name__} 没有可用的文档注解。")
            if method_tag == "":
                if func not in self.tag_map[method_tag]:
                    self.tag_map[method_tag].add(func)
                    logger.success(f"注册方法 {func.__name__} 到默认标签。")
                else:
                    logger.error(f"[!扩展加载冲突!] 方法 {func.__name__} 已存在于默认标签中。")
            else:
                if func not in self.tag_map[method_tag]:
                    self.tag_map[method_tag].add(func)
                    logger.success(f"注册方法 {func.__name__} 到标签 {method_tag}。")
                else:
                    logger.error(f"[!扩展加载冲突!] 方法 {func.__name__} 已存在于标签 {method_tag} 中。")
            return func

        return decorator

    def get_method(self, method_name: str, in_tag: str = "") -> Optional[Callable]:
        """获取指定方法

        Args:
            method_name (str): 方法名
            in_tag (str, optional): 标签名. Defaults to "".

        Returns:
            Optional[Callable]: 方法
        """
        if in_tag not in self.tag_map:
            return None
        for method in self.tag_map[in_tag]:
            if method.__name__ == method_name:
                return method
        return None

    def get_method_type(self, method: Callable) -> MethodType:
        """获取方法类型

        Args:
            method (Callable): 方法

        Returns:
            Optional[MethodType]: 方法类型
        """
        if hasattr(method, "_method_type"):
            return cast(MethodType, method._method_type)  # type: ignore  # noqa: SLF001
        raise ValueError(f"方法 {method.__name__} 未注册。")

    def get_all_methods(self, in_tag: str = "") -> List[Callable]:
        """获取指定标签下的所有方法

        Args:
            in_tag (str, optional): 标签名. Defaults to "".

        Returns:
            List[Callable]: 方法列表
        """
        if in_tag not in self.tag_map:
            return []
        return list(self.tag_map[in_tag])

    def gen_method_prompts(self, method_tag: str = "") -> List[str]:
        """获取收集到的方法提示词

        Args:
            method_tag (Optional[str], optional): 要获取的标签，如果为 None，则获取全部标签. Defaults to None.

        Returns:
            List[str]: 方法提示词列表
        """
        prompts: List[str] = []

        if method_tag not in self.tag_map:
            return []
        for method in self.tag_map[method_tag]:
            if not method.__doc__:
                logger.warning(f"方法 {method.__name__} 没有可用的文档注解。")
                continue
            prompts.append(f"* {method.__name__} - {method.__doc__.strip()}")
        return prompts


agent_collector = DocCollector()
