"""
SSE 客户端分块接收器
====================

负责处理从服务端通过SSE推送的大文件分块数据。
"""

import asyncio
import base64
import contextlib
import time
from typing import Any, Callable, Coroutine, Dict, Optional, Union

from loguru import logger

from .models import ChunkComplete, ChunkData, FileChunkResponse


class ChunkReceiver:
    """分块接收处理器

    负责接收、缓冲、合并从服务端推送的文件分块。
    """

    def __init__(self, file_received_callback: Callable[[str, bytes, str, str], Coroutine[Any, Any, None]]):
        """初始化分块接收器

        Args:
            file_received_callback: 文件接收完成时的回调函数
        """
        self.chunk_buffers: Dict[str, Any] = {}
        self.chunk_timeouts: Dict[str, float] = {}
        self.chunk_timeout_duration = 300  # 5分钟超时
        self.running = True
        self._cleanup_task: Optional[asyncio.Task] = None
        self._file_received_callback = file_received_callback

    async def start(self) -> None:
        """启动分块接收器后台任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._chunk_cleanup_loop())

    async def stop(self) -> None:
        """停止分块接收器后台任务"""
        self.running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def handle_file_chunk(
        self,
        data: Union[ChunkData, Dict[str, Any]],
    ) -> Optional[FileChunkResponse]:
        """处理文件分块数据

        Args:
            data: 分块数据

        Returns:
            Optional[FileChunkResponse]: 响应数据，如果是中间分块则返回None
        """
        try:
            chunk_data = ChunkData(**data) if isinstance(data, dict) else data

            if not all(
                [
                    chunk_data.chunk_id,
                    chunk_data.chunk_index is not None,
                    chunk_data.total_chunks,
                    chunk_data.chunk_data,
                ],
            ):
                logger.error(f"分块数据不完整: {chunk_data}")
                return FileChunkResponse(success=False, error="分块数据不完整", message=None)

            logger.debug(f"接收分块: {chunk_data.filename} [{chunk_data.chunk_index + 1}/{chunk_data.total_chunks}]")

            if chunk_data.chunk_id not in self.chunk_buffers:
                self.chunk_buffers[chunk_data.chunk_id] = {
                    "chunks": [None] * chunk_data.total_chunks,
                    "total_chunks": chunk_data.total_chunks,
                    "received_chunks": 0,
                    "filename": chunk_data.filename,
                    "mime_type": chunk_data.mime_type,
                    "file_type": chunk_data.file_type,
                }
                self.chunk_timeouts[chunk_data.chunk_id] = time.time() + self.chunk_timeout_duration

            buffer_info = self.chunk_buffers[chunk_data.chunk_id]

            if buffer_info["chunks"][chunk_data.chunk_index] is not None:
                logger.warning(
                    f"重复接收分块: {chunk_data.filename} [{chunk_data.chunk_index + 1}/{chunk_data.total_chunks}]",
                )
                return None

            buffer_info["chunks"][chunk_data.chunk_index] = chunk_data.chunk_data
            buffer_info["received_chunks"] += 1

            if buffer_info["received_chunks"] == chunk_data.total_chunks:
                complete_data = "".join(filter(None, buffer_info["chunks"]))
                try:
                    file_bytes = base64.b64decode(complete_data)
                    await self._file_received_callback(
                        buffer_info["filename"] or f"file_{chunk_data.chunk_id[:8]}",
                        file_bytes,
                        buffer_info["mime_type"] or "application/octet-stream",
                        buffer_info["file_type"] or "file",
                    )
                except Exception as e:
                    logger.exception(f"文件解码或处理失败: {buffer_info['filename']}")
                    return FileChunkResponse(success=False, error=f"文件解码或处理失败: {e!s}", message=None)
                finally:
                    self._cleanup_buffer(chunk_data.chunk_id)
                return FileChunkResponse(success=True, error=None, message=f"文件 {buffer_info['filename']} 接收完成")

        except Exception as e:
            logger.exception("处理文件分块异常")
            return FileChunkResponse(success=False, error=str(e), message=None)
        return None

    def handle_file_chunk_complete(self, data: Union[ChunkComplete, Dict[str, Any]]) -> None:
        """处理文件分块传输完成事件"""
        chunk_complete = ChunkComplete(**data) if isinstance(data, dict) else data
        if not chunk_complete.success:
            logger.error(f"服务端传输失败: {chunk_complete.message}")
            self._cleanup_buffer(chunk_complete.chunk_id)

    def _cleanup_buffer(self, chunk_id: str) -> None:
        """清理指定ID的缓冲区"""
        if chunk_id in self.chunk_buffers:
            del self.chunk_buffers[chunk_id]
        if chunk_id in self.chunk_timeouts:
            del self.chunk_timeouts[chunk_id]

    async def _chunk_cleanup_loop(self) -> None:
        """分块清理循环任务"""
        while self.running:
            await asyncio.sleep(60)
            try:
                self._cleanup_expired_chunks()
            except Exception:
                logger.exception("分块清理任务异常")

    def _cleanup_expired_chunks(self) -> None:
        """清理过期的分块缓冲区"""
        current_time = time.time()
        expired_chunk_ids = [chunk_id for chunk_id, timeout_time in self.chunk_timeouts.items() if current_time > timeout_time]

        for chunk_id in expired_chunk_ids:
            buffer_info = self.chunk_buffers.get(chunk_id, {})
            filename = buffer_info.get("filename", "unknown")
            logger.warning(f"清理过期分块缓冲区: {filename} (chunk_id: {chunk_id})")
            self._cleanup_buffer(chunk_id)
