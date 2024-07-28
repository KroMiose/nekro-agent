from typing import Callable, Dict, List, Optional, Set

from nekro_agent.core.logger import logger


class DocCollector:
    """方法文档收集器

    用于收集面向 AI 使用的文档，并将其转化为可用提示词
    """

    def __init__(self):
        self.tag_map: Dict[str, Set[Callable]] = {}

    def fastapi_interface(self, method_tag: str = ""):
        """FastAPI 接口文档收集器

        Args:
            method_tag (str): 要收集的接口方法的标签

        Returns:
            Decorator: 收集装饰器
        """

        def decorator(func):
            if method_tag not in self.tag_map:
                self.tag_map[method_tag] = set()
            if not func.__doc__:
                logger.warning(f"Method {func.__name__} has no docstring.")
            self.tag_map[method_tag].add(func)
            logger.info(f"Add method {func.__name__} to collector.")
            return func

        return decorator

    def method_interface(self, method_tag: str = ""):
        """普通方法文档收集器

        Args:
            method_tag (str): 要收集的接口方法的标签

        Returns:
            Decorator: 收集装饰器
        """

        def decorator(func):
            if method_tag not in self.tag_map:
                self.tag_map[method_tag] = set()
            if not func.__doc__:
                logger.warning(f"Method {func.__name__} has no docstring.")
            self.tag_map[method_tag].add(func)
            logger.info(f"Add method {func.__name__} to collector.")
            return func

        return decorator

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
                logger.warning(f"Method {method.__name__} has no docstring.")
                continue
            prompts.append(f"{method.__name__} - {method.__doc__.strip()}")
        return prompts


agent_method_collector = DocCollector()
