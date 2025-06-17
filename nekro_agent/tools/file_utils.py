import shutil
from pathlib import Path
from typing import Type, Union

from nekro_agent.core.os_env import SANDBOX_SHARED_HOST_DIR, USER_UPLOAD_DIR
from nekro_agent.tools.common_util import (
    download_file,
    download_file_from_base64,
    download_file_from_bytes,
)

from .path_convertor import (
    convert_filepath_to_sandbox_shared_path,
    convert_filepath_to_sandbox_upload_path,
    convert_to_host_path,
    get_upload_file_path,
)


class FileUtils:

    @classmethod
    def sandbox2host(cls, sandbox_path: str | Path, chat_key: str, container_key: str) -> Path:
        """将沙盒内互通路径转换为宿主机路径

        用来转换 AI 提供的沙盒内互通路径为插件可访问的宿主机路径

        Args:
            sandbox_path: 沙盒内互通路径
            chat_key: 聊天会话ID
            container_key: 容器ID

        Returns:
            Path: 宿主机路径
        """
        return convert_to_host_path(Path(sandbox_path), chat_key, container_key)

    @classmethod
    def host_shared2sandbox(cls, host_filepath: str | Path) -> Path:
        """将宿主机沙盒共享目录文件路径转换为沙盒内路径

        Args:
            host_filepath: 宿主机上传路径

        Returns:
            Path: 沙盒内路径
        """
        return convert_filepath_to_sandbox_shared_path(Path(host_filepath))

    @classmethod
    def host_upload2sandbox(cls, host_filepath: str | Path) -> Path:
        """将宿主机上传目录文件路径转换为沙盒内路径"""
        return convert_filepath_to_sandbox_upload_path(Path(host_filepath))

    @classmethod
    def get_sandbox_shared_host_path(cls, container_key: str) -> Path:
        """获取沙盒共享目录的宿主机路径

        Args:
            chat_key: 聊天会话ID
            container_key: 容器ID
        """
        path = cls.to_absolute_path(SANDBOX_SHARED_HOST_DIR) / container_key
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_upload_file_path(cls, from_chat_key: str, file_name: str = "", use_suffix: str = "", seed: str = "") -> str:
        """获取或生成一个可用的上传文件路径

        Args:
            from_chat_key: 聊天会话ID
            file_name: 文件名
            use_suffix: 指定文件后缀
            seed: 种子
        """
        return get_upload_file_path(from_chat_key, file_name, use_suffix, seed)

    @classmethod
    def to_absolute_path(cls, path: str | Path) -> Path:
        """将相对路径转换为绝对路径

        Args:
            path: 路径
        """
        return Path(path) if str(path).startswith("/") else Path(path).resolve()


class FileSystem:
    """文件系统工具类，提供插件应用与沙盒内文件系统互通的工具"""

    def __init__(self, chat_key: str, container_key: str):
        self._chat_key = chat_key
        self._container_key = container_key

    @property
    def chat_key(self) -> str:
        return self._chat_key

    @property
    def container_key(self) -> str:
        return self._container_key

    @property
    def file_utils(self) -> Type[FileUtils]:
        return FileUtils

    @property
    def shared_path(self) -> Path:
        """获取当前会话的文件共享目录"""
        return FileUtils.get_sandbox_shared_host_path(self.container_key)

    @property
    def upload_path(self) -> Path:
        """获取当前会话的文件上传目录"""
        return Path(USER_UPLOAD_DIR) / self.chat_key

    def get_file(self, file_path: Path | str) -> Path:
        """从 AI 提供的沙盒内互通路径获取可访问的文件对象

        Args:
            file_path: 文件路径

        Returns:
            Path: 文件对象
        """
        path = Path(file_path)
        if path.is_relative_to(Path("/app/shared")):
            return self.shared_path / path.relative_to(Path("/app/shared"))
        if path.is_relative_to(Path("/app/uploads")):
            return self.upload_path / path.relative_to(Path("/app/uploads"))
        raise ValueError(f'文件 "{path}" 不在合法的沙盒内容共享目录或上传目录下，无法映射到应用路径')

    def forward_file(self, file_path: Path | str) -> str:
        """通过文件路径向 AI 提供一个可访问的沙盒内互通文件路径

        注意: 需要先把文件放到 shared_path 或 upload_path 下

        Args:
            file_path: 文件路径

        Returns:
            str: 可访问的文件路径
        """
        path = Path(file_path)
        # 检查文件是否在共享目录下
        if path.is_relative_to(self.shared_path):
            rel_path = path.relative_to(self.shared_path)
            return str(self.file_utils.host_shared2sandbox(rel_path))
        if path.is_relative_to(self.upload_path):
            rel_path = path.relative_to(self.upload_path)
            return str(self.file_utils.host_upload2sandbox(rel_path))
        raise ValueError(f'文件 "{path}" 不在合法的应用共享目录或上传目录下，无法映射到沙盒路径')

    async def mixed_forward_file(self, file: Union[str, bytes, Path], file_name: str = "") -> str:
        """通过 url/base64/bytes/path 向 AI 提供一个可访问的沙盒内互通文件路径

        Args:
            file: 文件 URL/base64/bytes/path

        Returns:
            str: 可访问的文件路径
        """
        if isinstance(file, str):
            if file.startswith(("http", "https")):
                file_path, file_name = await download_file(file, from_chat_key=self.chat_key, file_name=file_name)
            elif file.startswith("data:"):
                file_path, file_name = await download_file_from_base64(file, from_chat_key=self.chat_key, file_name=file_name)
        elif isinstance(file, bytes):
            file_path, file_name = await download_file_from_bytes(file, from_chat_key=self.chat_key, file_name=file_name)
        elif isinstance(file, Path):
            if file.is_relative_to(self.shared_path):
                file_path = self.shared_path / file.relative_to(self.shared_path)
            elif file.is_relative_to(self.upload_path):
                file_path = self.upload_path / file.relative_to(self.upload_path)
            else:
                shutil.copy(file, self.shared_path / file.name)
                file_path = self.shared_path / file.name
        else:
            raise TypeError(f"不支持的文件类型: {type(file)}")
        return self.forward_file(file_path)
