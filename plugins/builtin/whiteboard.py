"""
# 直播白板演示 (Whiteboard)

为直播场景提供一个专业的演示白板，允许 AI 将生成的图片、视频、HTML 代码等资源实时展示到白板上。

## 设计理念：实时演示白板

这个插件充当了 AI 与直播观众之间的可视化桥梁。AI 可以将任何需要展示的内容（图片、视频、代码、文本等）
发送到白板上，白板会通过 SSE 长连接实时更新显示内容。白板页面可以直接在 OBS 等直播软件中作为浏览器源使用。

## 主要功能

- **实时内容展示**: 支持图片、视频、HTML、文本等多种内容类型的实时展示
- **多种布局模式**: 提供单屏、分屏、网格等多种布局选择
- **断线重连机制**: 自动检测连接状态并重连，确保直播稳定性
- **动画过渡效果**: 平滑的内容切换动画，提升观看体验
- **OBS 集成友好**: 专门为直播软件优化的页面设计

## 使用方法

### 在 OBS 中使用
1. 添加浏览器源
2. URL 设置为: `http://localhost:8021/plugins/nekro.whiteboard/` -> [跳转](/plugins/nekro.whiteboard/)
3. 设置合适的分辨率（推荐 1920x1080）

### AI 调用示例
AI 可以通过以下方法操作白板：
- `display_image()`: 展示图片
- `display_video()`: 播放视频
- `display_html()`: 展示 HTML 渲染内容
- `display_text()`: 显示文本信息
- `clear_whiteboard()`: 清空白板
- `set_layout()`: 设置布局模式
"""

import asyncio
import base64
import contextlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import magic
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger
from nekro_agent.tools.path_convertor import is_url_path

plugin = NekroPlugin(
    name="直播白板演示插件",
    module_name="whiteboard",
    description="为直播场景提供专业的演示白板，支持实时展示图片、视频、HTML等内容",
    version="1.0.0",
    author="nekro",
    url="https://github.com/nekro-agent/nekro-agent",
    support_adapter=["bilibili_live"],
)


@plugin.mount_config()
class WhiteboardConfig(ConfigBase):
    """白板配置"""

    DEFAULT_LAYOUT: str = Field(default="single", title="默认布局模式", description="single(单屏)/split(分屏)/grid(网格)")
    AUTO_CLEAR_TIMEOUT: int = Field(default=300, title="自动清理超时", description="内容展示超时时间(秒)，0表示不自动清理")
    MAX_CONTENT_SIZE: int = Field(default=10, title="最大内容数量", description="白板最多同时展示的内容数量")
    ENABLE_ANIMATIONS: bool = Field(default=True, title="启用动画效果", description="是否启用内容切换的动画效果")
    MAX_FILE_SIZE_MB: float = Field(
        default=10.0,
        title="最大文件大小(MB)",
        description="支持转换为base64的最大文件大小，超过此大小的文件将被拒绝",
    )


# 获取配置
config = plugin.get_config(WhiteboardConfig)


# 全局状态管理
class ContentItem(BaseModel):
    """白板内容项"""

    id: str
    type: str  # image, video, html, text, webpage
    content: str  # 文件路径或HTML内容
    title: Optional[str] = None
    position: Dict[str, Any] = Field(default_factory=lambda: {"x": 0, "y": 0, "width": "100%", "height": "100%"})
    style: Dict[str, str] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class WhiteboardState(BaseModel):
    """白板状态"""

    layout: str = "single"
    contents: List[ContentItem] = Field(default_factory=list)
    background_color: str = "#000000"
    last_update: float = Field(default_factory=time.time)


# 白板客户端类
class WhiteboardClient:
    """白板SSE客户端"""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.is_alive = True
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=50)
        self.last_heartbeat = time.time()

    async def send_event(self, data: Dict[str, Any]) -> None:
        """发送事件到客户端"""
        if not self.is_alive:
            return
        try:
            await asyncio.wait_for(self.event_queue.put(data), timeout=0.1)
            self.last_heartbeat = time.time()
        except (asyncio.TimeoutError, asyncio.QueueFull):
            # 客户端可能卡住，标记为失活
            self.is_alive = False

    def is_expired(self, timeout_seconds: int = 60) -> bool:
        """检查客户端是否过期"""
        return time.time() - self.last_heartbeat > timeout_seconds

    def update_heartbeat(self) -> None:
        """更新心跳时间"""
        self.last_heartbeat = time.time()


# 客户端管理器
class WhiteboardClientManager:
    """白板客户端管理器"""

    def __init__(self):
        self.clients: Dict[str, WhiteboardClient] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_shutting_down = False

    async def start(self) -> None:
        """启动客户端管理器"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """停止客户端管理器"""
        self.is_shutting_down = True

        # 标记所有客户端为非活跃
        for client in self.clients.values():
            client.is_alive = False

        # 取消清理任务
        if self.cleanup_task:
            self.cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.cleanup_task
            self.cleanup_task = None

        # 清空客户端列表
        self.clients.clear()

    async def _cleanup_loop(self) -> None:
        """定期清理过期客户端"""
        try:
            while not self.is_shutting_down:
                await asyncio.sleep(30)  # 每30秒检查一次

                expired_clients = []
                for client_id, client in self.clients.items():
                    if client.is_expired():
                        expired_clients.append(client_id)

                for client_id in expired_clients:
                    client = self.clients.pop(client_id, None)
                    if client:
                        client.is_alive = False
                        logger.info(f"清理过期的白板 SSE 客户端: {client_id}")

        except asyncio.CancelledError:
            pass

    def register_client(self, client_id: str) -> WhiteboardClient:
        """注册新客户端"""
        client = WhiteboardClient(client_id)
        self.clients[client_id] = client
        return client

    def unregister_client(self, client_id: str) -> None:
        """注销客户端"""
        client = self.clients.pop(client_id, None)
        if client:
            client.is_alive = False

    async def broadcast(self, data: Dict[str, Any]) -> None:
        """广播消息到所有客户端"""
        if self.is_shutting_down:
            return

        dead_clients = []
        for client_id, client in self.clients.items():
            if not client.is_alive or client.is_expired():
                dead_clients.append(client_id)
                continue

            await client.send_event(data)

        # 清理失效客户端
        for client_id in dead_clients:
            self.unregister_client(client_id)

    def get_client_count(self) -> int:
        """获取当前客户端数量"""
        return len(self.clients)


# 全局管理器和状态
client_manager = WhiteboardClientManager()
whiteboard_state = WhiteboardState()


async def broadcast_to_sse(data: Dict[str, Any]) -> None:
    """向所有 SSE 连接广播数据"""
    await client_manager.broadcast(data)


async def close_all_sse_connections() -> None:
    """关闭所有SSE连接"""
    logger.info(f"开始关闭 {client_manager.get_client_count()} 个SSE连接")

    # 向所有客户端发送关闭信号
    if client_manager.clients:
        try:
            await asyncio.wait_for(
                client_manager.broadcast({"type": "server_shutdown"}),
                timeout=0.5,
            )
        except asyncio.TimeoutError:
            logger.warning("发送关闭信号超时")

    # 等待连接自然关闭
    for _ in range(5):  # 最多等待0.5秒
        if not client_manager.clients:
            break
        await asyncio.sleep(0.1)

    # 强制关闭所有剩余连接
    await client_manager.stop()
    logger.info("所有SSE连接已关闭")


@plugin.mount_router()
def create_router() -> APIRouter:
    """创建白板路由"""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, summary="白板演示页面")
    async def whiteboard_page():
        """返回白板 HTML 页面"""
        html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>直播白板演示</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Arial', sans-serif;
            background: #000;
            color: #fff;
            overflow: hidden;
            width: 100vw;
            height: 100vh;
        }
        
        .whiteboard {
            width: 100%;
            height: 100%;
            position: relative;
            transition: all 0.3s ease;
        }
        
        .content-item {
            position: absolute;
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 
                0 8px 32px rgba(0, 0, 0, 0.4),
                0 0 0 2px rgba(255, 255, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.15);
        }
        
        .content-item.fade-in {
            animation: fadeIn 0.5s ease-in-out;
        }
        
        .content-item.fade-out {
            animation: fadeOut 0.5s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.8); }
            to { opacity: 1; transform: scale(1); }
        }
        
        @keyframes fadeOut {
            from { opacity: 1; transform: scale(1); }
            to { opacity: 0; transform: scale(0.8); }
        }
        
        .content-image {
            width: 100%;
            height: 100%;
            object-fit: contain;
            position: relative;
            z-index: 2;
        }
        
        .image-container {
            width: 100%;
            height: 100%;
            position: relative;
            overflow: hidden;
        }
        
        .image-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: inherit;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            filter: blur(20px) brightness(0.3) saturate(1.2);
            transform: scale(1.1);
            z-index: 1;
        }
        
        .content-video {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        .content-html {
            width: 100%;
            height: 100%;
            border: none;
            background: #fff;
        }
        
        .content-text {
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .content-iframe {
            width: 100%;
            height: 100%;
            border: none;
            background: #fff;
        }
        
        .content-title {
            position: absolute;
            top: 15px;
            left: 15px;
            background: linear-gradient(135deg, rgba(0, 0, 0, 0.8), rgba(50, 50, 50, 0.6));
            color: #fff;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            z-index: 10;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        
        .status-indicator {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 1000;
        }
        
        .status-connected {
            background: #4CAF50;
            color: white;
        }
        
        .status-disconnected {
            background: #f44336;
            color: white;
        }
        
        .status-reconnecting {
            background: #ff9800;
            color: white;
        }
        
        /* 布局样式 */
        .layout-single .content-item {
            width: 100% !important;
            height: 100% !important;
            top: 0 !important;
            left: 0 !important;
        }
        
        .layout-split .content-item:nth-child(1) {
            width: 50% !important;
            height: 100% !important;
            top: 0 !important;
            left: 0 !important;
        }
        
        .layout-split .content-item:nth-child(2) {
            width: 50% !important;
            height: 100% !important;
            top: 0 !important;
            left: 50% !important;
        }
        
        .layout-grid .content-item:nth-child(1) {
            width: 50% !important;
            height: 50% !important;
            top: 0 !important;
            left: 0 !important;
        }
        
        .layout-grid .content-item:nth-child(2) {
            width: 50% !important;
            height: 50% !important;
            top: 0 !important;
            left: 50% !important;
        }
        
        .layout-grid .content-item:nth-child(3) {
            width: 50% !important;
            height: 50% !important;
            top: 50% !important;
            left: 0 !important;
        }
        
        .layout-grid .content-item:nth-child(4) {
            width: 50% !important;
            height: 50% !important;
            top: 50% !important;
            left: 50% !important;
        }
    </style>
</head>
<body>
    <div class="whiteboard" id="whiteboard">
        <div class="status-indicator status-disconnected" id="status">
            未连接
        </div>
    </div>

    <script>
        class WhiteboardClient {
            constructor() {
                this.eventSource = null;
                this.reconnectDelay = 1000;
                this.maxReconnectDelay = 30000;
                this.reconnectAttempts = 0;
                this.maxReconnectAttempts = 50;
                
                this.whiteboard = document.getElementById('whiteboard');
                this.statusIndicator = document.getElementById('status');
                
                this.connect();
            }
            
            connect() {
                this.updateStatus('reconnecting', '连接中...');
                
                try {
                    this.eventSource = new EventSource('/plugins/nekro.whiteboard/events');
                    
                    this.eventSource.onopen = () => {
                        this.updateStatus('connected', '已连接');
                        this.reconnectDelay = 1000;
                        this.reconnectAttempts = 0;
                    };
                    
                    this.eventSource.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            this.handleMessage(data);
                        } catch (error) {
                            console.error('解析消息失败:', error);
                        }
                    };
                    
                    this.eventSource.onerror = () => {
                        this.updateStatus('disconnected', '连接断开');
                        this.eventSource.close();
                        this.scheduleReconnect();
                    };
                    
                } catch (error) {
                    console.error('连接失败:', error);
                    this.scheduleReconnect();
                }
            }
            
            scheduleReconnect() {
                if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    this.updateStatus('disconnected', '连接失败');
                    return;
                }
                
                this.reconnectAttempts++;
                this.updateStatus('reconnecting', `重连中... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                
                // 关闭现有连接（如果存在）
                if (this.eventSource) {
                    this.eventSource.close();
                    this.eventSource = null;
                }
                
                setTimeout(() => {
                    this.connect();
                }, this.reconnectDelay);
                
                this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
            }
            
            updateStatus(type, message) {
                this.statusIndicator.className = `status-indicator status-${type}`;
                this.statusIndicator.textContent = message;
            }
            
            handleMessage(data) {
                switch (data.type) {
                    case 'update_state':
                        this.updateWhiteboard(data.state);
                        break;
                    case 'clear':
                        this.clearWhiteboard();
                        break;
                    case 'server_shutdown':
                        this.updateStatus('reconnecting', '服务器重启中...');
                        this.eventSource.close();
                        this.scheduleReconnect();
                        break;
                    case 'heartbeat':
                        // 心跳消息，保持连接活跃
                        break;
                    default:
                        console.log('未知消息类型:', data.type);
                }
            }
            
            updateWhiteboard(state) {
                // 更新背景色
                this.whiteboard.style.backgroundColor = state.background_color;
                
                // 更新布局类
                this.whiteboard.className = `whiteboard layout-${state.layout}`;
                
                // 清除现有内容
                const existingItems = this.whiteboard.querySelectorAll('.content-item');
                existingItems.forEach(item => {
                    if (item.classList.contains('fade-in')) {
                        item.classList.add('fade-out');
                        setTimeout(() => item.remove(), 500);
                    } else {
                        item.remove();
                    }
                });
                
                // 添加新内容
                state.contents.forEach((content, index) => {
                    setTimeout(() => {
                        this.addContentItem(content, index);
                    }, index * 100);
                });
            }
            
            addContentItem(content, index) {
                const item = document.createElement('div');
                item.className = 'content-item fade-in';
                item.style.position = 'absolute';
                
                // 应用自定义样式
                Object.entries(content.style || {}).forEach(([key, value]) => {
                    item.style[key] = value;
                });
                
                // 添加标题
                if (content.title) {
                    const title = document.createElement('div');
                    title.className = 'content-title';
                    title.textContent = content.title;
                    item.appendChild(title);
                }
                
                // 根据类型创建内容
                let contentElement;
                switch (content.type) {
                    case 'image':
                        contentElement = document.createElement('div');
                        contentElement.className = 'image-container';
                        
                        // 设置背景图片供伪元素继承（模糊效果）
                        contentElement.style.backgroundImage = `url(${content.content})`;
                        
                        // 创建前景图片
                        const imgElement = document.createElement('img');
                        imgElement.className = 'content-image';
                        imgElement.src = content.content;
                        imgElement.alt = content.title || '图片';
                        
                        contentElement.appendChild(imgElement);
                        break;
                        
                    case 'video':
                        contentElement = document.createElement('video');
                        contentElement.className = 'content-video';
                        contentElement.src = content.content;
                        contentElement.controls = true;
                        contentElement.autoplay = true;
                        contentElement.muted = true;
                        contentElement.loop = true;
                        break;
                        
                    case 'html':
                        contentElement = document.createElement('iframe');
                        contentElement.className = 'content-html';
                        contentElement.srcdoc = content.content;
                        contentElement.sandbox = 'allow-scripts allow-same-origin';
                        break;
                        
                    case 'text':
                        contentElement = document.createElement('div');
                        contentElement.className = 'content-text';
                        contentElement.innerHTML = content.content;
                        break;
                        
                    case 'webpage':
                        contentElement = document.createElement('iframe');
                        contentElement.className = 'content-iframe';
                        contentElement.src = content.content;
                        contentElement.sandbox = 'allow-scripts allow-same-origin allow-forms allow-popups allow-pointer-lock';
                        contentElement.loading = 'lazy';
                        break;
                        
                    default:
                        contentElement = document.createElement('div');
                        contentElement.className = 'content-text';
                        contentElement.textContent = '不支持的内容类型: ' + content.type;
                }
                
                item.appendChild(contentElement);
                this.whiteboard.appendChild(item);
            }
            
            clearWhiteboard() {
                const items = this.whiteboard.querySelectorAll('.content-item');
                items.forEach((item, index) => {
                    setTimeout(() => {
                        item.classList.add('fade-out');
                        setTimeout(() => item.remove(), 500);
                    }, index * 50);
                });
            }
        }
        
        // 初始化白板客户端
        let whiteboardClient;
        
        document.addEventListener('DOMContentLoaded', () => {
            whiteboardClient = new WhiteboardClient();
        });
        
        // 页面卸载时关闭连接
        window.addEventListener('beforeunload', () => {
            if (whiteboardClient && whiteboardClient.eventSource) {
                whiteboardClient.eventSource.close();
            }
        });
        
        // 处理页面可见性变化
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // 页面不可见，可以选择暂停重连
            } else {
                // 页面可见，确保连接正常
                if (whiteboardClient && (!whiteboardClient.eventSource || whiteboardClient.eventSource.readyState === EventSource.CLOSED)) {
                    whiteboardClient.connect();
                }
            }
        });
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)

    @router.get("/events", summary="SSE 事件流")
    async def events_stream(request: Request):
        """SSE 长连接端点"""

        async def event_generator():
            client_id = f"whiteboard-{int(time.time() * 1000)}"
            client = client_manager.register_client(client_id)
            logger.info(f"新的SSE连接建立，客户端ID: {client_id}, 当前连接数: {client_manager.get_client_count()}")

            try:
                # 发送初始连接事件
                yield f'data: {json.dumps({"type": "connected", "client_id": client_id}, ensure_ascii=False)}\n\n'

                # 发送初始状态
                try:
                    initial_data = {"type": "update_state", "state": whiteboard_state.model_dump()}
                    yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.warning(f"发送初始状态失败: {e}")

                # 心跳计时器
                heartbeat_timer = 0

                # 持续发送事件
                while client.is_alive and not client_manager.is_shutting_down:
                    try:
                        # 检查请求是否断开
                        if await request.is_disconnected():
                            logger.info(f"客户端 {client_id} 断开连接")
                            break

                        # 发送心跳
                        if time.time() - heartbeat_timer >= 5:
                            try:
                                yield 'data: {"type": "heartbeat"}\n\n'
                                heartbeat_timer = time.time()
                                client.update_heartbeat()
                            except Exception:
                                break

                        # 等待事件，使用较短超时
                        try:
                            data = await asyncio.wait_for(client.event_queue.get(), timeout=1.0)
                            message = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                            yield message
                        except asyncio.TimeoutError:
                            # 超时继续循环
                            pass

                    except asyncio.CancelledError:
                        logger.info(f"SSE连接 {client_id} 被取消")
                        break
                    except Exception as e:
                        logger.warning(f"SSE事件处理错误: {e}")
                        break

                # 如果是因为关闭事件退出，尝试发送关闭信号
                if client_manager.is_shutting_down:
                    with contextlib.suppress(Exception):
                        yield 'data: {"type": "server_shutdown"}\n\n'

            except asyncio.CancelledError:
                logger.info(f"SSE连接生成器 {client_id} 被取消")
            except Exception as e:
                logger.warning(f"SSE 连接错误: {e}")
            finally:
                client_manager.unregister_client(client_id)
                logger.info(f"SSE连接断开，客户端ID: {client_id}, 当前连接数: {client_manager.get_client_count()}")

        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "X-Accel-Buffering": "no",  # 禁用缓冲
            },
        )

    @router.get("/status", summary="获取白板状态")
    async def get_status():
        """获取当前白板状态"""
        return {
            "success": True,
            "data": {
                "state": whiteboard_state.model_dump(),
                "connections": client_manager.get_client_count(),
                "last_update": datetime.fromtimestamp(whiteboard_state.last_update).isoformat(),
            },
        }

    @router.post("/clear", summary="清空白板")
    async def clear_whiteboard_api():
        """清空白板内容"""
        global whiteboard_state
        whiteboard_state.contents.clear()
        whiteboard_state.last_update = time.time()

        await broadcast_to_sse({"type": "clear"})

        return {"success": True, "message": "白板已清空"}

    return router


@plugin.mount_prompt_inject_method(name="whiteboard_prompt")
async def whiteboard_prompt(_ctx: AgentCtx) -> str:
    """白板提示词注入"""

    # 构建当前内容摘要
    content_summary = []
    for idx, content in enumerate(whiteboard_state.contents):
        if content.type == "image":
            summary = f"图片 #{idx+1}: {content.title or '无标题'}"
        elif content.type == "video":
            summary = f"视频 #{idx+1}: {content.title or '无标题'}"
        elif content.type == "html":
            summary = f"HTML渲染内容 #{idx+1}: {content.title or '无标题'}"
        elif content.type == "text":
            text_preview = content.content[:50] + "..." if len(content.content) > 50 else content.content
            summary = f"文本 #{idx+1}: {content.title or text_preview}"
        elif content.type == "webpage":
            summary = f"网页 #{idx+1}: {content.title or content.content}"
        else:
            summary = f"未知类型 #{idx+1}: {content.type}"
        content_summary.append(summary)

    content_info = "\n".join(content_summary) if content_summary else "- 白板当前为空"

    layout_desc = {
        "single": "单屏模式 - 内容占满整个屏幕",
        "split": "分屏模式 - 左右分屏展示两个内容",
        "grid": "网格模式 - 四宫格展示多个内容",
    }

    return f"""
🎯 直播白板演示功能状态:

📋 当前白板信息:
- 布局模式: {whiteboard_state.layout} ({layout_desc.get(whiteboard_state.layout, '未知')})
- 最后更新: {datetime.fromtimestamp(whiteboard_state.last_update).strftime('%H:%M:%S')}

📄 当前展示内容:
{content_info}

🛠️ 可用的白板操作工具:
1. display_image - 展示图片到白板 (支持本地文件和URL)
2. display_video - 播放视频到白板 (支持本地文件和URL)
3. display_html - 展示HTML渲染内容到白板
4. display_text - 显示文本信息到白板 (支持HTML格式)
5. display_link - 在白板中直接打开网页供观众查看
6. set_layout - 设置布局模式 (single/split/grid)
7. clear_whiteboard - 清空所有内容

💡 使用建议:
- 这是一个直播展示白板，观众只能观看无法交互
- 合理选择布局模式来展示多个内容
- 图片和视频文件会自动转换为base64格式在浏览器中显示
- HTML内容可以展示任意内容，将会在白板中通过浏览器引擎直接渲染
- 链接功能会在白板中直接打开网页，观众可以看到实际的网页内容
- 文本内容支持HTML格式，可添加丰富的样式和格式
- 由于你无法直接和白板交互，例如用户让你制作一个小游戏，你可以同时编写自动游玩的代码来实现
"""


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="展示图片到白板",
    description="在直播白板上展示图片资源",
)
async def display_image(
    _ctx: AgentCtx,
    image_path: str,
    title: Optional[str] = None,
    clear_before: bool = False,
) -> str:
    """在白板上展示图片

    Args:
        image_path (str): 图片文件路径或URL
        title (Optional[str]): 图片标题，显示在左上角
        clear_before (bool): 是否在展示前清空白板

    Returns:
        str: 操作结果描述

    Example:
        display_image("/shared/generated_chart.png", "数据分析图表")
    """
    global whiteboard_state

    def _validate_file_path(file_path: str) -> str:
        """验证并处理文件路径"""
        host_path = _ctx.fs.get_file(file_path)
        if not Path(host_path).exists():
            raise FileNotFoundError(f"图片文件不存在: {file_path}")
        return str(host_path)

    def _check_file_size(file_path: str) -> None:
        """检查文件大小限制"""
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        if file_size_mb > config.MAX_FILE_SIZE_MB:
            raise ValueError(f"图片文件过大 ({file_size_mb:.2f}MB)，超过限制 ({config.MAX_FILE_SIZE_MB}MB)")

    try:
        # 处理文件路径
        if is_url_path(image_path):
            # URL 直接使用
            display_url = image_path
        else:
            # 使用 ctx.fs 方法将沙盒路径转换为宿主机路径
            host_path = _validate_file_path(image_path)
            _check_file_size(host_path)

            # 读取文件并转换为base64 data URL
            async with aiofiles.open(host_path, "rb") as f:
                file_data = await f.read()
                mime_type = magic.from_buffer(file_data, mime=True)
                base64_data = base64.b64encode(file_data).decode("utf-8")
                display_url = f"data:{mime_type};base64,{base64_data}"

        if clear_before:
            whiteboard_state.contents.clear()

        # 创建内容项
        content_item = ContentItem(id=f"img_{int(time.time() * 1000)}", type="image", content=display_url, title=title)

        # 限制内容数量
        if len(whiteboard_state.contents) >= config.MAX_CONTENT_SIZE:
            whiteboard_state.contents.pop(0)

        whiteboard_state.contents.append(content_item)
        whiteboard_state.last_update = time.time()

        # 广播更新
        await broadcast_to_sse({"type": "update_state", "state": whiteboard_state.model_dump()})

        logger.info(f"白板展示图片成功: {title or image_path}, 连接数: {client_manager.get_client_count()}")

    except Exception as e:
        raise Exception(f"展示图片失败: {e}") from e
    else:
        return f"成功在白板上展示图片: {title or image_path}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="播放视频到白板",
    description="在直播白板上播放视频资源",
)
async def display_video(
    _ctx: AgentCtx,
    video_path: str,
    title: Optional[str] = None,
    clear_before: bool = False,
) -> str:
    """在白板上播放视频

    Args:
        video_path (str): 视频文件路径或URL
        title (Optional[str]): 视频标题
        clear_before (bool): 是否在播放前清空白板

    Returns:
        str: 操作结果描述
    """
    global whiteboard_state

    def _validate_video_path(file_path: str) -> str:
        """验证并处理视频文件路径"""
        host_path = _ctx.fs.get_file(file_path)
        if not Path(host_path).exists():
            raise FileNotFoundError(f"视频文件不存在: {file_path}")
        return str(host_path)

    def _check_video_size(file_path: str) -> None:
        """检查视频文件大小限制"""
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        if file_size_mb > config.MAX_FILE_SIZE_MB:
            raise ValueError(f"视频文件过大 ({file_size_mb:.2f}MB)，超过限制 ({config.MAX_FILE_SIZE_MB}MB)")

    try:
        # 处理文件路径
        if is_url_path(video_path):
            display_url = video_path
        else:
            # 使用 ctx.fs 方法将沙盒路径转换为宿主机路径
            host_path = _validate_video_path(video_path)
            _check_video_size(host_path)

            # 读取文件并转换为base64 data URL
            async with aiofiles.open(host_path, "rb") as f:
                file_data = await f.read()
                mime_type = magic.from_buffer(file_data, mime=True)
                base64_data = base64.b64encode(file_data).decode("utf-8")
                display_url = f"data:{mime_type};base64,{base64_data}"

        if clear_before:
            whiteboard_state.contents.clear()

        content_item = ContentItem(id=f"vid_{int(time.time() * 1000)}", type="video", content=display_url, title=title)

        if len(whiteboard_state.contents) >= config.MAX_CONTENT_SIZE:
            whiteboard_state.contents.pop(0)

        whiteboard_state.contents.append(content_item)
        whiteboard_state.last_update = time.time()

        await broadcast_to_sse({"type": "update_state", "state": whiteboard_state.model_dump()})

        logger.info(f"白板播放视频成功: {title or video_path}, 连接数: {client_manager.get_client_count()}")

    except Exception as e:
        raise Exception(f"播放视频失败: {e}") from e
    else:
        return f"成功在白板上播放视频: {title or video_path}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="展示HTML内容到白板",
    description="在直播白板上展示HTML代码渲染内容",
)
async def display_html(
    _ctx: AgentCtx,
    html_content: str,
    title: Optional[str] = None,
    clear_before: bool = False,
) -> str:
    """在白板上展示HTML内容

    Args:
        html_content (str): 待渲染的HTML代码内容
        title (Optional[str]): 内容标题
        clear_before (bool): 是否在展示前清空白板

    Returns:
        str: 操作结果描述

    Example:
        display_html("<h1>Hello World</h1><p>这是一个示例</p>", "示例页面")
    """
    global whiteboard_state

    try:
        if clear_before:
            whiteboard_state.contents.clear()

        content_item = ContentItem(id=f"html_{int(time.time() * 1000)}", type="html", content=html_content, title=title)

        if len(whiteboard_state.contents) >= config.MAX_CONTENT_SIZE:
            whiteboard_state.contents.pop(0)

        whiteboard_state.contents.append(content_item)
        whiteboard_state.last_update = time.time()

        await broadcast_to_sse({"type": "update_state", "state": whiteboard_state.model_dump()})

    except Exception as e:
        raise Exception(f"展示HTML内容失败: {e}") from e
    else:
        return f"成功在白板上展示HTML内容: {title or 'HTML内容'}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="显示文本到白板",
    description="在直播白板上显示文本信息",
)
async def display_text(
    _ctx: AgentCtx,
    text_content: str,
    title: Optional[str] = None,
    font_size: str = "24px",
    text_color: str = "#ffffff",
    clear_before: bool = False,
) -> str:
    """在白板上显示文本

    Args:
        text_content (str): 文本内容，支持HTML格式
        title (Optional[str]): 文本标题
        font_size (str): 字体大小，默认24px
        text_color (str): 文本颜色，默认白色
        clear_before (bool): 是否在显示前清空白板

    Returns:
        str: 操作结果描述
    """
    global whiteboard_state

    try:
        if clear_before:
            whiteboard_state.contents.clear()

        content_item = ContentItem(
            id=f"text_{int(time.time() * 1000)}",
            type="text",
            content=text_content,
            title=title,
            style={"font-size": font_size, "color": text_color},
        )

        if len(whiteboard_state.contents) >= config.MAX_CONTENT_SIZE:
            whiteboard_state.contents.pop(0)

        whiteboard_state.contents.append(content_item)
        whiteboard_state.last_update = time.time()

        await broadcast_to_sse({"type": "update_state", "state": whiteboard_state.model_dump()})

    except Exception as e:
        raise Exception(f"显示文本失败: {e}") from e
    else:
        return f"成功在白板上显示文本: {title or '文本内容'}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="打开链接到白板",
    description="在直播白板上直接打开并展示网页内容",
)
async def display_link(
    _ctx: AgentCtx,
    url: str,
    title: Optional[str] = None,
    clear_before: bool = False,
) -> str:
    """在白板上直接打开并展示网页内容

    Args:
        url (str): 要打开的网页URL地址
        title (Optional[str]): 网页标题
        clear_before (bool): 是否在展示前清空白板

    Returns:
        str: 操作结果描述

    Example:
        display_link("https://github.com", "GitHub首页")
    """
    global whiteboard_state

    try:
        if clear_before:
            whiteboard_state.contents.clear()

        content_item = ContentItem(
            id=f"webpage_{int(time.time() * 1000)}",
            type="webpage",
            content=url,
            title=title,
        )

        if len(whiteboard_state.contents) >= config.MAX_CONTENT_SIZE:
            whiteboard_state.contents.pop(0)

        whiteboard_state.contents.append(content_item)
        whiteboard_state.last_update = time.time()

        await broadcast_to_sse({"type": "update_state", "state": whiteboard_state.model_dump()})

    except Exception as e:
        raise Exception(f"打开网页失败: {e}") from e
    else:
        return f"成功在白板上打开网页: {title or url}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="设置白板布局",
    description="设置白板的布局模式",
)
async def set_layout(_ctx: AgentCtx, layout_mode: str) -> str:
    """设置白板布局模式

    Args:
        layout_mode (str): 布局模式 - single(单屏)/split(分屏)/grid(网格)

    Returns:
        str: 操作结果描述

    Example:
        set_layout("grid")  # 设置为网格布局
    """
    global whiteboard_state

    def _validate_layout(mode: str) -> None:
        """验证布局模式"""
        valid_layouts = ["single", "split", "grid"]
        if mode not in valid_layouts:
            raise ValueError(f"无效的布局模式: {mode}，支持的模式: {valid_layouts}")

    try:
        _validate_layout(layout_mode)

        whiteboard_state.layout = layout_mode
        whiteboard_state.last_update = time.time()

        await broadcast_to_sse({"type": "update_state", "state": whiteboard_state.model_dump()})

    except Exception as e:
        raise Exception(f"设置布局失败: {e}") from e
    else:
        return f"成功设置白板布局为: {layout_mode}"


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="清空白板",
    description="清空白板上的所有内容",
)
async def clear_whiteboard(_ctx: AgentCtx) -> str:
    """清空白板上的所有内容

    Returns:
        str: 操作结果描述
    """
    global whiteboard_state

    try:
        whiteboard_state.contents.clear()
        whiteboard_state.last_update = time.time()

        await broadcast_to_sse({"type": "clear"})

    except Exception as e:
        raise Exception(f"清空白板失败: {e}") from e
    else:
        return "成功清空白板内容"


@plugin.mount_cleanup_method()
async def cleanup():
    """快速清理插件资源"""
    global whiteboard_state, client_manager

    logger.info("开始快速清理白板插件资源...")

    try:
        # 快速关闭所有SSE连接
        await asyncio.wait_for(close_all_sse_connections(), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning("SSE连接关闭超时，强制继续")
        await client_manager.stop()
    except Exception as e:
        logger.warning(f"关闭SSE连接时发生错误: {e}")
        await client_manager.stop()

    # 立即重置白板状态
    whiteboard_state = WhiteboardState()

    logger.info("白板插件快速清理完成")


@plugin.mount_init_method()
async def init():
    """初始化插件"""
    global whiteboard_state, client_manager

    # 重置白板状态
    whiteboard_state = WhiteboardState(layout=config.DEFAULT_LAYOUT)

    # 启动客户端管理器
    await client_manager.start()

    logger.info(f"白板插件初始化完成，默认布局: {config.DEFAULT_LAYOUT}")
