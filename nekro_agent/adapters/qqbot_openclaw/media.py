from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from nekro_agent.adapters.interface.schemas.platform import PlatformSendSegmentType

from .config import QQBOT_MEDIA_SIZE_LIMIT_MB, QQBotOpenClawConfig

QQBotMediaKind = Literal["image", "voice", "video", "file"]

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".amr", ".silk", ".ogg", ".m4a", ".aac", ".flac"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
FILE_TYPE_CODE: dict[QQBotMediaKind, int] = {"image": 1, "video": 2, "voice": 3, "file": 4}
QQBOT_MD5_10M_WINDOW = 10002432


@dataclass(slots=True)
class MediaFile:
    path: Path
    kind: QQBotMediaKind
    file_type: int
    file_name: str
    size: int
    md5: str
    sha1: str
    md5_10m: str


def infer_media_kind(path: str | Path, segment_type: PlatformSendSegmentType) -> QQBotMediaKind:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    mime_type, _ = mimetypes.guess_type(str(file_path))

    if segment_type == PlatformSendSegmentType.IMAGE:
        return "image"
    if mime_type:
        if mime_type.startswith("image/"):
            return "image"
        if mime_type.startswith("audio/"):
            return "voice"
        if mime_type.startswith("video/"):
            return "video"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in AUDIO_SUFFIXES:
        return "voice"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return "file"


def validate_media_file(path: str | Path, segment_type: PlatformSendSegmentType, config: QQBotOpenClawConfig) -> MediaFile:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    kind = infer_media_kind(file_path, segment_type)
    size = file_path.stat().st_size
    limit_mb = QQBOT_MEDIA_SIZE_LIMIT_MB[kind]
    limit_bytes = limit_mb * 1024 * 1024
    if size > limit_bytes:
        raise ValueError(f"{kind} 文件超过 OpenClaw 默认限制: {size / 1024 / 1024:.1f}MB > {limit_mb}MB")

    data = file_path.read_bytes()
    first_10m = data[:QQBOT_MD5_10M_WINDOW]
    return MediaFile(
        path=file_path,
        kind=kind,
        file_type=FILE_TYPE_CODE[kind],
        file_name=file_path.name,
        size=size,
        md5=hashlib.md5(data).hexdigest(),  # noqa: S324 - OpenClaw 上传协议要求 MD5。
        sha1=hashlib.sha1(data).hexdigest(),  # noqa: S324 - OpenClaw 上传协议要求 SHA1。
        md5_10m=hashlib.md5(first_10m).hexdigest(),  # noqa: S324 - OpenClaw 上传协议要求 MD5。
    )
