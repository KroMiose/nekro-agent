from typing import Callable, Dict, List, Optional, Set

from nekro_agent.core.logger import logger


class DocCollector:
    """方法文档收集器

    用于收集面向 AI 使用的文档，并将其转化为可用提示词
    """

    def __init__(self):
        self.tag_map: Dict[str, Set[Callable]] = {}

    def mount_method(self, method_tag: str = ""):
        """方法收集器

        Args:
            method_tag (str): 要收集的接口方法的标签

        Returns:
            Decorator: 收集装饰器
        """

        def decorator(func):
            if method_tag not in self.tag_map:
                self.tag_map[method_tag] = set()
            if not func.__doc__:
                logger.warning(f"注册方法 {func.__name__} 没有可用的文档注解。")
            if method_tag == "":
                if func not in self.tag_map[""]:
                    self.tag_map[""].add(func)
                    logger.success(f"注册方法 {func.__name__} 到默认标签 {method_tag}。")
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
            prompts.append(f"{method.__name__} - {method.__doc__.strip()}")
        return prompts


agent_collector = DocCollector()
