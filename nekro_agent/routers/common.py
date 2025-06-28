import os
import shutil
from hashlib import md5
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import WALLPAPER_DIR
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user

router = APIRouter(prefix="/common", tags=["Common"])

# 确保壁纸目录存在
WALLPAPER_PATH = Path(WALLPAPER_DIR)
WALLPAPER_PATH.mkdir(parents=True, exist_ok=True)

# 支持的图片类型
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.post("/wallpaper/upload", response_model=Ret)
async def upload_wallpaper(
    file: UploadFile = File(...),
    current_user: DBUser = Depends(get_current_active_user),
):
    """上传壁纸"""
    try:
        # 检查文件扩展名
        filename = file.filename or "unknown.jpg"
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return Ret.fail(msg=f"不支持的文件类型，允许的类型: {', '.join(ALLOWED_EXTENSIONS)}")

        # 读取文件内容
        content = await file.read()

        # 计算MD5
        file_md5 = md5(content).hexdigest()

        # 完整文件路径 (保留原始扩展名以便正确识别文件类型)
        filepath = WALLPAPER_PATH / f"{file_md5}{file_ext}"

        # 写入文件
        with filepath.open("wb") as f:
            f.write(content)

        logger.info(f"用户 {current_user.username} 上传壁纸: {filepath}")

        return Ret.success(
            msg="壁纸上传成功",
            data={"id": file_md5, "filename": filename, "url": f"/api/common/wallpaper/{file_md5}{file_ext}"},
        )
    except Exception as e:
        logger.exception(f"壁纸上传失败: {e}")
        return Ret.error(msg=f"壁纸上传失败: {e}")


@router.get("/wallpaper/list", response_model=Ret)
async def list_wallpapers(_current_user: DBUser = Depends(get_current_active_user)):
    """获取所有壁纸列表"""
    try:
        wallpapers = []

        for file in WALLPAPER_PATH.iterdir():
            if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
                file_id = file.stem  # 文件名是MD5值
                wallpapers.append({"id": file_id, "url": f"/api/common/wallpaper/{file.name}", "filename": file.name})

        return Ret.success(msg="获取壁纸列表成功", data=wallpapers)
    except Exception as e:
        logger.exception(f"获取壁纸列表失败: {e}")
        return Ret.error(msg=f"获取壁纸列表失败: {e}")


@router.delete("/wallpaper/{wallpaper_id}", response_model=Ret)
async def delete_wallpaper(
    wallpaper_id: str,
    current_user: DBUser = Depends(get_current_active_user),
):
    """删除壁纸"""
    try:
        # 查找匹配的壁纸文件
        found = False
        for file in WALLPAPER_PATH.iterdir():
            if file.is_file() and file.stem == wallpaper_id:
                file.unlink()
                found = True
                logger.info(f"用户 {current_user.username} 删除壁纸: {file}")
                break

        if not found:
            return Ret.fail(msg="未找到指定的壁纸")

        return Ret.success(msg="壁纸删除成功")
    except Exception as e:
        logger.exception(f"删除壁纸失败: {e}")
        return Ret.error(msg=f"删除壁纸失败: {e}")


@router.get("/wallpaper/{filename}")
async def get_wallpaper(filename: str):
    """获取壁纸文件 (无需鉴权)"""
    filepath = WALLPAPER_PATH / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="壁纸不存在")

    # 设置缓存头以提高性能
    headers = {"Cache-Control": "public, max-age=604800", "ETag": f'"{filename}"'}  # 缓存一周

    return FileResponse(filepath, headers=headers, media_type=f"image/{filepath.suffix.lstrip('.')}")
