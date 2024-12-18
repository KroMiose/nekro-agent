from abc import ABC, abstractmethod


class BaseTokenizer(ABC):

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """计算文本的token数量

        Args:
            text (str): 待处理的文本

        Returns:
            int: token数量
        """
