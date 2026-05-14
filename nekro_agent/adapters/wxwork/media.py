import hashlib
import io
from pathlib import Path

from PIL import Image

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatMessageSegmentType


logger = get_sub_logger("adapter.wxwork.media")
WXWORK_INBOUND_IMAGE_TARGET_MAX_BYTES = 180 * 1024
WXWORK_INBOUND_IMAGE_MIN_QUALITY = 45
WXWORK_INBOUND_IMAGE_INITIAL_QUALITY = 85
WXWORK_INBOUND_IMAGE_MIN_EDGE = 320


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


def normalize_incoming_image(raw_bytes: bytes, file_name: str) -> tuple[bytes, str]:
    try:
        image = Image.open(io.BytesIO(raw_bytes))
    except Exception:
        logger.warning("WeCom 入站图片无法被 Pillow 识别，保留原始字节")
        return raw_bytes, file_name

    if len(raw_bytes) <= WXWORK_INBOUND_IMAGE_TARGET_MAX_BYTES:
        return raw_bytes, file_name

    working = image.convert("RGB")
    width, height = working.size
    normalized_file_name = f"{Path(file_name).stem}.jpg"

    best_bytes, candidate, quality = _try_compress_with_qualities(
        working,
        WXWORK_INBOUND_IMAGE_TARGET_MAX_BYTES,
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
                max(int(width * scale), WXWORK_INBOUND_IMAGE_MIN_EDGE),
                max(int(height * scale), WXWORK_INBOUND_IMAGE_MIN_EDGE),
            ),
            Image.Resampling.LANCZOS,
        )
        best_bytes, candidate, quality = _try_compress_with_qualities(
            resized,
            WXWORK_INBOUND_IMAGE_TARGET_MAX_BYTES,
        )
        if candidate is not None:
            _log_image_compression(
                raw_bytes=raw_bytes,
                compressed_bytes=candidate,
                quality=quality,
                scale=scale,
            )
            return candidate, normalized_file_name

        if min(resized.size) <= WXWORK_INBOUND_IMAGE_MIN_EDGE:
            logger.info(
                "WeCom 入站图片压缩达到下限，使用当前最优结果: "
                f"original={len(raw_bytes)}B compressed={len(best_bytes)}B"
            )
            return best_bytes, normalized_file_name


def _try_compress_with_qualities(
    image: Image.Image,
    target_bytes: int,
) -> tuple[bytes, bytes | None, int]:
    best_bytes = b""
    for quality in range(
        WXWORK_INBOUND_IMAGE_INITIAL_QUALITY,
        WXWORK_INBOUND_IMAGE_MIN_QUALITY - 1,
        -10,
    ):
        candidate = _encode_jpeg(image, quality)
        best_bytes = candidate
        if len(candidate) <= target_bytes:
            return best_bytes, candidate, quality
    return best_bytes, None, WXWORK_INBOUND_IMAGE_MIN_QUALITY


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
