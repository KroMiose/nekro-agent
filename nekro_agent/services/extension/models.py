"""扩展服务的数据模型"""

from typing import List, Optional

from pydantic import BaseModel


class ExtMetaData(BaseModel):
    """扩展元数据模型"""
    name: str
    version: str
    author: str
    author_email: Optional[str] = None
    description: str
    url: Optional[str] = None
    license: Optional[str] = None

    def gen_ext_info(self) -> str:
        """生成扩展信息字符串"""
        return f"+ {self.description} (v{self.version}) by {self.author}" 