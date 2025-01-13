from fastapi import APIRouter, Depends

from nekro_agent.schemas.message import Ret
from nekro_agent.services.extension import ALL_EXT_META_DATA
from nekro_agent.systems.user.deps import get_current_active_user
from nekro_agent.tools.collector import MethodType, agent_collector

router = APIRouter(prefix="/extensions", tags=["Extensions"])


@router.get("", summary="获取扩展列表")
async def get_extensions(_=Depends(get_current_active_user)) -> Ret:
    """获取所有已加载的扩展信息"""
    extensions = []

    # 获取所有方法及其所属的标签
    all_methods = {}
    for _tag, methods in agent_collector.tag_map.items():
        for method in methods:
            if method.__doc__:
                try:
                    method_type = agent_collector.get_method_type(method)
                    # 使用方法所在模块的文件名作为扩展名
                    ext_name = method.__module__.split(".")[-1]
                    if ext_name not in all_methods:
                        all_methods[ext_name] = []
                    all_methods[ext_name].append(
                        {"name": method.__name__, "type": method_type, "description": method.__doc__.strip()},
                    )
                except ValueError:
                    continue

    # 为每个扩展添加其对应的方法
    for ext in ALL_EXT_META_DATA:
        extensions.append(
            {
                "name": ext.name,
                "version": ext.version,
                "description": ext.description,
                "author": ext.author,
                "methods": all_methods.get(ext.name, []),  # 获取该扩展对应的方法列表
                "is_enabled": True,
            },
        )

    return Ret.success(msg="获取扩展列表成功", data=extensions)
