"""
插件路由功能示例

本示例展示了如何在 Nekro 插件中使用新的路由功能来创建自定义 Web API。
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from nekro_agent.services.plugin.base import NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="路由示例插件",
    module_name="router_example",
    description="展示插件路由功能的示例插件",
    version="1.0.0",
    author="nekro",
    url="https://github.com/nekro-agent/nekro-agent",
)


# 数据模型定义
class TaskModel(BaseModel):
    id: int
    title: str
    description: str
    completed: bool = False


class CreateTaskRequest(BaseModel):
    title: str
    description: str


# 模拟数据存储
tasks_db: Dict[int, TaskModel] = {}
next_id = 1


@plugin.mount_router()
def create_router() -> APIRouter:
    """创建并配置插件路由"""
    router = APIRouter()

    @router.get("/", summary="插件首页")
    async def plugin_home():
        """插件首页，返回插件基本信息"""
        return {
            "plugin_name": plugin.name,
            "version": plugin.version,
            "description": plugin.description,
            "available_endpoints": [
                "GET / - 插件首页",
                "GET /tasks - 获取任务列表",
                "POST /tasks - 创建新任务",
                "GET /tasks/{task_id} - 获取指定任务",
                "PUT /tasks/{task_id} - 更新任务",
                "DELETE /tasks/{task_id} - 删除任务",
                "GET /health - 健康检查",
            ],
        }

    @router.get("/health", summary="健康检查")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "plugin": plugin.name,
            "tasks_count": len(tasks_db),
        }

    @router.get("/tasks", response_model=List[TaskModel], summary="获取任务列表")
    async def get_tasks(
        completed: Optional[bool] = Query(None, description="过滤已完成/未完成的任务"),
        limit: int = Query(10, ge=1, le=100, description="返回任务数量限制"),
    ):
        """获取任务列表，支持过滤和分页"""
        tasks = list(tasks_db.values())

        if completed is not None:
            tasks = [task for task in tasks if task.completed == completed]

        return tasks[:limit]

    @router.post("/tasks", response_model=TaskModel, summary="创建新任务")
    async def create_task(task_data: CreateTaskRequest):
        """创建新任务"""
        global next_id

        new_task = TaskModel(
            id=next_id,
            title=task_data.title,
            description=task_data.description,
        )

        tasks_db[next_id] = new_task
        next_id += 1

        return new_task

    @router.get("/tasks/{task_id}", response_model=TaskModel, summary="获取指定任务")
    async def get_task(task_id: int):
        """根据ID获取指定任务"""
        if task_id not in tasks_db:
            raise HTTPException(status_code=404, detail="任务不存在")

        return tasks_db[task_id]

    @router.put("/tasks/{task_id}", response_model=TaskModel, summary="更新任务")
    async def update_task(task_id: int, task_data: CreateTaskRequest, completed: bool = False):
        """更新指定任务"""
        if task_id not in tasks_db:
            raise HTTPException(status_code=404, detail="任务不存在")

        task = tasks_db[task_id]
        task.title = task_data.title
        task.description = task_data.description
        task.completed = completed

        return task

    @router.delete("/tasks/{task_id}", summary="删除任务")
    async def delete_task(task_id: int):
        """删除指定任务"""
        if task_id not in tasks_db:
            raise HTTPException(status_code=404, detail="任务不存在")

        deleted_task = tasks_db.pop(task_id)
        return {"message": f"任务 '{deleted_task.title}' 已删除"}

    # 统计端点
    @router.get("/statistics", summary="获取任务统计信息")
    async def get_statistics():
        """获取任务统计信息"""
        total_tasks = len(tasks_db)
        completed_tasks = sum(1 for task in tasks_db.values() if task.completed)
        pending_tasks = total_tasks - completed_tasks

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
        }

    return router


@plugin.mount_init_method()
async def init():
    """插件初始化"""
    global tasks_db, next_id

    # 添加一些示例数据
    sample_tasks = [
        TaskModel(id=1, title="学习 FastAPI", description="深入学习 FastAPI 框架的使用"),
        TaskModel(id=2, title="开发插件路由功能", description="为 Nekro 插件系统开发路由功能", completed=True),
        TaskModel(id=3, title="编写文档", description="为新功能编写详细的使用文档"),
    ]

    for task in sample_tasks:
        tasks_db[task.id] = task

    next_id = len(sample_tasks) + 1
    print(f"插件 {plugin.name} 初始化完成，加载了 {len(sample_tasks)} 个示例任务")


@plugin.mount_cleanup_method()
async def cleanup():
    """插件清理"""
    global tasks_db, next_id

    tasks_db.clear()
    next_id = 1
    print(f"插件 {plugin.name} 清理完成")


# 使用说明:
"""
将此文件放置在插件目录中，重启服务后，插件路由将可以通过以下路径访问：

基础路径: /plugins/nekro.router_example

可用端点:
- GET  /plugins/nekro.router_example/           - 插件首页
- GET  /plugins/nekro.router_example/health     - 健康检查  
- GET  /plugins/nekro.router_example/tasks      - 获取任务列表
- POST /plugins/nekro.router_example/tasks      - 创建新任务
- GET  /plugins/nekro.router_example/tasks/{id} - 获取指定任务
- PUT  /plugins/nekro.router_example/tasks/{id} - 更新任务
- DELETE /plugins/nekro.router_example/tasks/{id} - 删除任务
- GET  /plugins/nekro.router_example/statistics - 获取统计信息

示例请求:
1. 获取任务列表: GET /plugins/nekro.router_example/tasks
2. 创建新任务: POST /plugins/nekro.router_example/tasks
   Body: {"title": "新任务", "description": "任务描述"}
3. 更新任务: PUT /plugins/nekro.router_example/tasks/1?completed=true
   Body: {"title": "更新的任务", "description": "更新的描述"}

这个示例展示了:
- 如何使用 @plugin.mount_router() 装饰器
- 如何创建 RESTful API 端点
- 如何使用 Pydantic 模型进行请求/响应验证
- 如何处理路径参数和查询参数
- 如何返回适当的HTTP状态码和错误信息
- 如何在插件中管理数据
"""
