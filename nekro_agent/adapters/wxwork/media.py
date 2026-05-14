import hashlib
import io
from pathlib import Path

from PIL import Image

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatMessageSegmentType


logger = get_sub_logger("adapter.wxwork.media")


class WxWorkImageNormalizeOptions:
    def __init__(
        self,
        *,
        target_max_kb: int = 180,
        min_quality: int = 45,
        initial_quality: int = 85,
        min_edge: int = 320,
    ):
        self.target_max_bytes = max(1, int(target_max_kb)) * 1024
        self.min_quality = max(1, min(100, int(min_quality)))
        self.initial_quality = max(self.min_quality, min(100, int(initial_quality)))
        self.min_edge = max(1, int(min_edge))


def build_attachment_filename(
    *,
    segment_type: ChatMessageSegmentType,
    raw_bytes: bytes,
    original_file_name: str,
    fallback_index: int,
) -> str:
    original_name = original_file_name.strip()
    suffix = Path(original_name).suffix.lower() if original_name else ""
    if original_name and suffix:
        return original_name

    digest = hashlib.sha1(raw_bytes).hexdigest()[:12]
    default_suffix = ".jpg" if segment_type == ChatMessageSegmentType.IMAGE else ""
    return f"wxwork_{segment_type.value}_{fallback_index}_{digest}{suffix or default_suffix}"


def normalize_incoming_image(
    raw_bytes: bytes,
    file_name: str,
    *,
    options: WxWorkImageNormalizeOptions | None = None,
) -> tuple[bytes, str]:
    resolved_options = options or WxWorkImageNormalizeOptions()
    try:
        image = Image.open(io.BytesIO(raw_bytes))
    except Exception:
        logger.warning("WeCom 入站图片无法被 Pillow 识别，保留原始字节")
        return raw_bytes, file_name

    if len(raw_bytes) <= resolved_options.target_max_bytes:
        return raw_bytes, file_name

    working = image.convert("RGB")
    width, height = working.size
    normalized_file_name = f"{Path(file_name).stem}.jpg"

    best_bytes, candidate, quality = _try_compress_with_qualities(
        working,
        resolved_options,
    )
    if candidate is not None:
        _log_image_compression(
            raw_bytes=raw_bytes,
            compressed_bytes=candidate,
            quality=quality,
            scale=1.0,
        )
        return candidate, normalized_file_name

    scale = 1.0
    while True:
        scale *= 0.85
        resized = working.resize(
            (
                max(int(width * scale), resolved_options.min_edge),
                max(int(height * scale), resolved_options.min_edge),
            ),
            Image.Resampling.LANCZOS,
        )
        best_bytes, candidate, quality = _try_compress_with_qualities(
            resized,
            resolved_options,
        )
        if candidate is not None:
            _log_image_compression(
                raw_bytes=raw_bytes,
                compressed_bytes=candidate,
                quality=quality,
                scale=scale,
            )
            return candidate, normalized_file_name

        if min(resized.size) <= resolved_options.min_edge:
            logger.info(
                "WeCom 入站图片压缩达到下限，使用当前最优结果: "
                f"original={len(raw_bytes)}B compressed={len(best_bytes)}B"
            )
            return best_bytes, normalized_file_name


def _try_compress_with_qualities(
    image: Image.Image,
    options: WxWorkImageNormalizeOptions,
) -> tuple[bytes, bytes | None, int]:
    best_bytes = b""
    for quality in range(
        options.initial_quality,
        options.min_quality - 1,
        -10,
    ):
        candidate = _encode_jpeg(image, quality)
        best_bytes = candidate
        if len(candidate) <= options.target_max_bytes:
            return best_bytes, candidate, quality
    return best_bytes, None, options.min_quality


def _encode_jpeg(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def _log_image_compression(
    *,
    raw_bytes: bytes,
    compressed_bytes: bytes,
    quality: int,
    scale: float,
) -> None:
    logger.info(
        "WeCom 入站图片已压缩用于视觉请求: "
        f"original={len(raw_bytes)}B compressed={len(compressed_bytes)}B quality={quality} scale={scale:.2f}"
    )
