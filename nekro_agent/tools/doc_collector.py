from typing import Callable, Dict, List, Optional, Set

from nekro_agent.core import logger


class DocCollector:
    """方法文档收集器

    用于收集面向 AI 使用的文档，并将其转化为可用提示词
    """

    def __init__(self):
        self.methods: Set[Callable] = []
        self.tag_map: Dict[str, Set[Callable]] = {}

    def fastapi_interface(self, method_tag):
        """FastAPI 接口文档收集器

        Args:
            method_tag (str): 要收集的接口方法的标签

        Returns:
            Decorator: 收集装饰器
        """

        def decorator(func):
            self.methods.add(func)
            if method_tag not in self.tag_map:
                self.tag_map[method_tag] = set()
            self.tag_map[method_tag].add(func)
            return func

        return decorator

    def get_method_prompts(self, method_tag: Optional[str] = None) -> List[str]:
        """获取收集到的方法提示词

        Args:
            method_tag (Optional[str], optional): 要获取的标签，如果为 None，则获取全部标签. Defaults to None.

        Returns:
            List[str]: 方法提示词列表
        """
        if method_tag is None:
            prompts = []
            for method in self.methods:
                if method.__doc__ is None:
                    logger.warning(f"Method {method.__name__} has no docstring.")
                    continue
                prompts.append(f"{method.__name__} - {method.__doc__.strip()}")
            return prompts

        if method_tag not in self.tag_map:
            return []
        prompts = []
        for method in self.tag_map[method_tag]:
            if method.__doc__ is None:
                logger.warning(f"Method {method.__name__} has no docstring.")
                continue
            prompts.append(f"{method.__name__} - {method.__doc__.strip()}")
        return prompts
