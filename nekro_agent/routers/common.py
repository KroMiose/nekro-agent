from hashlib import md5
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import USER_UPLOAD_DIR, WALLPAPER_DIR
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import AppFileNotFoundError, InvalidFileTypeError
from nekro_agent.services.user.deps import get_current_active_user

logger = get_sub_logger("common_api")
router = APIRouter(prefix="/common", tags=["Common"])

# 确保壁纸目录存在
WALLPAPER_PATH = Path(WALLPAPER_DIR)
WALLPAPER_PATH.mkdir(parents=True, exist_ok=True)

# 支持的图片类型
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class WallpaperInfo(BaseModel):
    id: str
    filename: str
    url: str


class ActionResponse(BaseModel):
    ok: bool = True


@router.post("/wallpaper/upload", response_model=WallpaperInfo)
async def upload_wallpaper(
    file: UploadFile = File(...),
    current_user: DBUser = Depends(get_current_active_user),
) -> WallpaperInfo:
    """上传壁纸"""
    filename = file.filename or "unknown.jpg"
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeError(file_type=file_ext or "unknown")

    content = await file.read()

    file_md5 = md5(content).hexdigest()

    filepath = WALLPAPER_PATH / f"{file_md5}{file_ext}"

    with filepath.open("wb") as f:
        f.write(content)

    logger.info(f"用户 {current_user.username} 上传壁纸: {filepath}")

    return WallpaperInfo(
        id=file_md5,
        filename=filename,
        url=f"/api/common/wallpaper/{file_md5}{file_ext}",
    )


@router.get("/wallpaper/list", response_model=List[WallpaperInfo])
async def list_wallpapers(_current_user: DBUser = Depends(get_current_active_user)) -> List[WallpaperInfo]:
    """获取所有壁纸列表"""
    wallpapers: List[WallpaperInfo] = []

    for file in WALLPAPER_PATH.iterdir():
        if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
            file_id = file.stem
            wallpapers.append(
                WallpaperInfo(
                    id=file_id,
                    filename=file.name,
                    url=f"/api/common/wallpaper/{file.name}",
                )
            )

    return wallpapers


@router.delete("/wallpaper/{wallpaper_id}", response_model=ActionResponse)
async def delete_wallpaper(
    wallpaper_id: str,
    current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """删除壁纸"""
    found = False
    for file in WALLPAPER_PATH.iterdir():
        if file.is_file() and file.stem == wallpaper_id:
            file.unlink()
            found = True
            logger.info(f"用户 {current_user.username} 删除壁纸: {file}")
            break

    if not found:
        raise AppFileNotFoundError(filename=wallpaper_id)

    return ActionResponse(ok=True)


@router.get("/wallpaper/{filename}")
async def get_wallpaper(filename: str):
    """获取壁纸文件 (无需鉴权)"""
    filepath = WALLPAPER_PATH / filename
    if not filepath.exists():
        raise AppFileNotFoundError(filename=filename)

    headers = {"Cache-Control": "public, max-age=604800", "ETag": f'"{filename}"'}

    return FileResponse(filepath, headers=headers, media_type=f"image/{filepath.suffix.lstrip('.')}" )


UPLOAD_PATH = Path(USER_UPLOAD_DIR)


@router.get("/uploads/{chat_key}/{filename}")
async def get_upload_file(
    chat_key: str,
    filename: str,
):
    """获取聊天上传文件（无需鉴权，供 img 标签等直接访问）"""
    # 防止路径穿越
    safe_chat_key = Path(chat_key).name
    safe_filename = Path(filename).name
    filepath = UPLOAD_PATH / safe_chat_key / safe_filename

    if not filepath.exists() or not filepath.is_file():
        raise AppFileNotFoundError(filename=filename)

    # 根据后缀推断 media type
    suffix = filepath.suffix.lower().lstrip(".")
    media_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "mp4": "video/mp4",
        "pdf": "application/pdf",
    }
    media_type = media_map.get(suffix, "application/octet-stream")

    headers = {"Cache-Control": "public, max-age=86400", "ETag": f'"{safe_filename}"'}
    # 非已知媒体类型强制下载，防止浏览器执行未知内容
    if media_type == "application/octet-stream":
        headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
    return FileResponse(filepath, headers=headers, media_type=media_type)
