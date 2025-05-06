from typing import Optional

from fastapi import APIRouter, Depends, Query

from nekro_agent.core.logger import logger
from nekro_agent.models.db_preset import DBPreset
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.systems.cloud.api.preset import get_preset, list_presets
from nekro_agent.systems.cloud.exceptions import NekroCloudDisabled

router = APIRouter(prefix="/cloud/presets-market", tags=["Cloud Presets Market"])


@router.get("/list", summary="获取云端人设列表")
@require_role(Role.Admin)
async def get_cloud_presets_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取云端人设列表"""
    try:
        # 查询云端人设列表
        response = await list_presets(page=page, page_size=page_size, keyword=keyword, tag=tag)

        if not response.success:
            return Ret.fail(msg=f"获取失败: {response.error}")

        if not response.data or not response.data.items:
            return Ret.success(msg="暂无数据", data={"total": 0, "items": []})

        # 获取所有云端人设的ID
        remote_ids = [item.id for item in response.data.items]

        # 查询已存在于本地的远程人设ID
        local_presets = await DBPreset.filter(remote_id__in=remote_ids).values("remote_id")
        local_preset_remote_ids = {preset["remote_id"] for preset in local_presets}

        # 构建返回结果，添加是否已在本地的标记
        result = []
        for item in response.data.items:
            result.append(
                {
                    "remote_id": item.id,
                    "is_local": item.id in local_preset_remote_ids,
                    "name": item.name,
                    "title": item.title,
                    "avatar": item.avatar,
                    "content": item.content,
                    "description": item.description,
                    "tags": item.tags,
                    "author": item.author,
                    "create_time": item.created_at,
                    "update_time": item.updated_at,
                },
            )

        return Ret.success(
            msg="获取成功",
            data={
                "total": response.data.total,
                "items": result,
                "page": page,
                "page_size": page_size,
                "total_pages": (response.data.total + page_size - 1) // page_size,  # 计算总页数
            },
        )

    except NekroCloudDisabled:
        return Ret.fail(msg="Nekro Cloud 未启用")
    except Exception as e:
        logger.error(f"获取云端人设列表失败: {e}")
        return Ret.fail(msg=f"获取失败: {e}")


@router.post("/download/{remote_id}", summary="下载云端人设到本地")
@require_role(Role.Admin)
async def download_preset(
    remote_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """下载云端人设到本地"""
    try:
        # 检查是否已下载
        exists = await DBPreset.exists(remote_id=remote_id)
        if exists:
            return Ret.fail(msg="此人设已存在于本地库")

        # 获取远程人设详情
        response = await get_preset(remote_id)
        if not response.success or not response.data:
            return Ret.fail(msg=f"获取失败: {response.error}")

        # 创建本地人设记录
        preset_data = response.data
        ext_data = preset_data.ext_data if preset_data.ext_data not in [None, "", "''", '""'] else {}
        await DBPreset.create(
            remote_id=preset_data.id,
            on_shared=preset_data.is_owner or False,  # 下载的人设是否为自己共享的
            name=preset_data.name,
            title=preset_data.title,
            avatar=preset_data.avatar,
            content=preset_data.content,
            description=preset_data.description,
            tags=preset_data.tags,
            author=preset_data.author,
            ext_data=ext_data,
        )

        return Ret.success(msg="下载成功")

    except NekroCloudDisabled:
        return Ret.fail(msg="Nekro Cloud 未启用")
    except Exception as e:
        logger.exception(f"下载云端人设失败: {e}")
        return Ret.fail(msg=f"下载失败: {e}")
