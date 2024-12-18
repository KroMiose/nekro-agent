from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel


class BaseStore(BaseModel):
    """场景数据源基类"""

    def __getitem__(self, key: str) -> Any:
        """获取场景数据"""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """设置场景数据"""
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """获取场景数据"""
        return getattr(self, key, default)

    def set(self, key: str, value: Any) -> None:
        """设置场景数据"""
        setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
