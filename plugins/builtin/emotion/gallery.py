from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from fastapi import UploadFile
from nekro_agent.api import schemas
from nekro_agent.api.core import logger
from nekro_agent.tools.path_convertor import convert_to_host_path

from .constants import DEFAULT_CATEGORY_DESCRIPTIONS, SUPPORTED_IMAGE_SUFFIXES


def safe_category_name(category: str) -> str:
    return category.strip().replace("/", "_").replace("\\", "_")


def normalize_description_map(raw_descriptions: Any) -> Dict[str, str]:
    if not isinstance(raw_descriptions, dict):
        return {}
    descriptions: Dict[str, str] = {}
    for category, description in raw_descriptions.items():
        safe_category = safe_category_name(str(category))
        if not safe_category:
            continue
        descriptions[safe_category] = str(description).strip()
    return descriptions


def is_supported_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES


class CategoryGalleryManager:
    def __init__(
        self,
        gallery_dir: Path,
        gallery_data_path: Path,
        default_gallery_dir: Path,
        config: Any,
        calculate_file_hash,
        download_image,
    ):
        self.gallery_dir = gallery_dir
        self.gallery_data_path = gallery_data_path
        self.default_gallery_dir = default_gallery_dir
        self.config = config
        self.calculate_file_hash = calculate_file_hash
        self.download_image = download_image

    def load_descriptions(self) -> Dict[str, str]:
        if not self.gallery_data_path.exists():
            return {}

        try:
            data = self.gallery_data_path.read_text(encoding="utf-8")
            import json

            parsed = json.loads(data)
        except Exception as e:
            logger.error(f"加载分类图库描述失败: {e}")
            return {}

        return normalize_description_map(parsed)

    def save_descriptions(self, descriptions: Dict[str, str]) -> None:
        import json

        self.gallery_data_path.parent.mkdir(parents=True, exist_ok=True)
        self.gallery_data_path.write_text(json.dumps(descriptions, ensure_ascii=False, indent=2), encoding="utf-8")

    def sync_descriptions_with_filesystem(self) -> Dict[str, str]:
        descriptions = self.load_descriptions()
        if "未分类" not in descriptions:
            descriptions["未分类"] = "尚未设置分类元数据的图片"
            self.save_descriptions(descriptions)
        self.gallery_dir.mkdir(parents=True, exist_ok=True)
        return descriptions

    def sync_default_descriptions_to_filesystem(self) -> Dict[str, Any]:
        descriptions = self.load_descriptions()
        default_descriptions = normalize_description_map(self.config.DEFAULT_CATEGORY_DESCRIPTIONS) or DEFAULT_CATEGORY_DESCRIPTIONS
        added_descriptions: List[str] = []
        updated_descriptions: List[str] = []
        normalized_categories: List[str] = []
        self.gallery_dir.mkdir(parents=True, exist_ok=True)

        for category, description in default_descriptions.items():
            safe_category = safe_category_name(category)
            if not safe_category:
                continue
            if safe_category != category:
                normalized_categories.append(category)
            description_text = str(description).strip()
            if descriptions.get(safe_category) != description_text:
                if safe_category in descriptions:
                    updated_descriptions.append(safe_category)
                else:
                    added_descriptions.append(safe_category)
                descriptions[safe_category] = description_text

        if "未分类" not in descriptions:
            descriptions["未分类"] = "尚未设置分类元数据的图片"
            added_descriptions.append("未分类")

        self.save_descriptions(descriptions)
        return {
            "status": "ok",
            "created_categories": added_descriptions,
            "added_descriptions": added_descriptions,
            "updated_descriptions": updated_descriptions,
            "normalized_categories": normalized_categories,
            "category_count": len(descriptions),
            "realtime": True,
            "message": "已按图库类别描述同步分类名和分类描述",
        }

    def init_gallery(self) -> None:
        if not self.config.ENABLE_CATEGORY_GALLERY:
            return
        self.gallery_dir.mkdir(parents=True, exist_ok=True)
        self.sync_descriptions_with_filesystem()

    def get_image_paths(self, category: str) -> List[Path]:
        return sorted(path for path in self.gallery_dir.iterdir() if is_supported_image_file(path))

    def get_stats(self) -> Dict[str, int]:
        descriptions = self.sync_descriptions_with_filesystem()
        return {category: 0 for category in descriptions}

    def find_duplicate_image(self, category: str, file_path: Path) -> Optional[Path]:
        target_hash = self.calculate_file_hash(file_path)
        if not target_hash:
            return None
        for image_path in self.get_image_paths(category):
            if self.calculate_file_hash(image_path) == target_hash:
                return image_path
        return None

    def copy_or_move_images(self, source_category: str, target_category: str, filenames: List[str], move: bool) -> Dict[str, Any]:
        safe_source = safe_category_name(source_category)
        safe_target = safe_category_name(target_category)
        if not safe_source or not safe_target:
            raise ValueError("来源分类和目标分类不能为空")
        if safe_source == safe_target:
            raise ValueError("来源分类和目标分类不能相同")
        if not filenames:
            raise ValueError("filenames 不能为空")

        descriptions = self.sync_descriptions_with_filesystem()
        if safe_target not in descriptions:
            descriptions[safe_target] = "请添加描述"
            self.save_descriptions(descriptions)

        processed = []
        missing = []
        invalid = []
        for filename in filenames:
            safe_filename = Path(str(filename)).name
            if not safe_filename:
                invalid.append(str(filename))
                continue
            source_path = self.gallery_dir / safe_filename
            if not source_path.exists() or not is_supported_image_file(source_path):
                missing.append(safe_filename)
                continue
            processed.append(safe_filename)
        return {
            "status": "ok",
            "source_category": safe_source,
            "target_category": safe_target,
            "moved" if move else "copied": processed,
            "missing": missing,
            "conflicts": [],
            "invalid": invalid,
            "processed_count": len(processed),
            "missing_count": len(missing),
            "conflict_count": 0,
            "invalid_count": len(invalid),
        }

    async def save_upload_file(self, upload_file: UploadFile, category: str) -> Path:
        safe_category = safe_category_name(category)
        if not safe_category:
            raise ValueError("分类不能为空")
        filename = Path(upload_file.filename or "upload.png").name
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError("仅支持 jpg、jpeg、png、gif、webp 图片")
        target_path = self.gallery_dir / filename
        index = 1
        while target_path.exists():
            target_path = self.gallery_dir / f"{Path(filename).stem}_{index}{suffix}"
            index += 1
        content = await upload_file.read()
        async with aiofiles.open(target_path, "wb") as file:
            await file.write(content)
        duplicate_path = self.find_duplicate_image(safe_category, target_path)
        if duplicate_path and duplicate_path != target_path:
            target_path.unlink(missing_ok=True)
            return duplicate_path
        return target_path

    async def add_image(self, source_path: str, category: str, ctx: schemas.AgentCtx) -> Path:
        safe_category = safe_category_name(category)
        if not safe_category:
            raise ValueError("Error: Category cannot be empty!")
        descriptions = self.sync_descriptions_with_filesystem()
        if safe_category not in descriptions:
            descriptions[safe_category] = "请添加描述"
            self.save_descriptions(descriptions)
        if source_path.startswith(("http://", "https://")):
            import hashlib
            import time

            suffix = Path(source_path.split("?")[0]).suffix.lower()
            if suffix not in SUPPORTED_IMAGE_SUFFIXES:
                suffix = ".png"
            file_name = f"{int(time.time())}_{hashlib.md5(source_path.encode()).hexdigest()[:8]}{suffix}"
            target_path = self.gallery_dir / file_name
            if not await self.download_image(source_path, target_path):
                raise ValueError(f"Error: Failed to download image from {source_path}")
        else:
            source_file = convert_to_host_path(Path(source_path), ctx.chat_key)
            if not source_file.exists():
                raise ValueError(f"Error: Source image not found: {source_path}")
            target_path = self.gallery_dir / source_file.name
            index = 1
            while target_path.exists():
                target_path = self.gallery_dir / f"{source_file.stem}_{index}{source_file.suffix}"
                index += 1
            async with aiofiles.open(source_file, "rb") as src_file:
                content = await src_file.read()
            async with aiofiles.open(target_path, "wb") as target_file:
                await target_file.write(content)
        duplicate_path = self.find_duplicate_image(safe_category, target_path)
        if duplicate_path and duplicate_path != target_path:
            target_path.unlink(missing_ok=True)
            return duplicate_path
        return target_path
