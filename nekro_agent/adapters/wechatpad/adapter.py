import time
import asyncio
import os
from typing import Type, Optional, List
from fastapi import APIRouter

from nekro_agent.core import logger
from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    ChatType,
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)

from .config import WeChatPadConfig
from .http_client import WeChatPadClient
from .routers import router
from .realtime_processor import WeChatRealtimeProcessor, MessageHandler, TextMessageHandler


class WeChatPadAdapter(BaseAdapter[WeChatPadConfig]):
    """WeChatPad 适配器"""

    def __init__(self, config_cls: Type[WeChatPadConfig] = WeChatPadConfig):
        """初始化 WeChatPad 适配器"""
        super().__init__(config_cls)
        self.http_client = WeChatPadClient(self.config)
        self.realtime_processor: Optional[WeChatRealtimeProcessor] = None
        self._realtime_task: Optional[asyncio.Task] = None

    @property
    def key(self) -> str:
        return "wechatpad"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="WeChatPad Pro",
            description="基于 WeChatPadPro 和 nekro_agent 项目的微信适配器，允许 Agent 通过 HTTP API 与微信进行交互。",
            version="0.1.0",
            author="Dirac",
            homepage="https://github.com/1A7432/nekro-agent/tree/main/nekro_agent/adapters/wechatpad",
            tags=["wechat", "wechatpad", "http", "chat"],
        )
    
    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "群聊: `wechatpad-群聊ID@chatroom` (例如: wechatpad-12345678@chatroom)",
            "私聊: `wechatpad-用户微信ID` (例如: wechatpad-wxid_abc123def456)",
        ]

    def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        return router

    async def init(self) -> None:
        """初始化适配器，设置回调地址"""
        logger.info("正在初始化 WeChatPad 适配器...")
        try:
            await self.http_client.set_callback_url()
        except Exception as e:
            logger.error(f"WeChatPad 适配器初始化失败: {e!s}")
            # 即使回调设置失败，也允许程序继续运行，可能用户只想用它来发消息
        
        # 初始化实时消息处理器（传递适配器引用）
        self.realtime_processor = WeChatRealtimeProcessor(self.config, adapter=self)
        logger.info("WeChatPad 实时消息处理器已初始化")
        
        # 启动实时消息处理
        await self.start_realtime_processing()

    async def cleanup(self) -> None:
        """清理适配器"""
        # 停止实时消息处理
        await self.stop_realtime_processing()
        logger.info("WeChatPad 适配器已卸载")
        return

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到微信协议端"""
        logger.info(f"开始发送消息: chat_key={request.chat_key}, segments_count={len(request.segments)}")
        try:
            message_ids = []
            
            # 从 chat_key 中解析 channel_id
            channel_id = self.parse_channel_id(request.chat_key)
            logger.info(f"解析得到 channel_id: {channel_id}")
            
            # 检查是否有有效的消息段
            has_valid_content = False
            for segment in request.segments:
                if segment.type == PlatformSendSegmentType.TEXT and segment.content and segment.content.strip():
                    has_valid_content = True
                    break
                elif segment.type == PlatformSendSegmentType.AT and segment.at_info:
                    has_valid_content = True
                    break
                elif segment.type in [PlatformSendSegmentType.IMAGE, PlatformSendSegmentType.FILE] and segment.file_path:
                    has_valid_content = True
                    break
            
            if not has_valid_content:
                logger.info("空消息，跳过发送")
                return PlatformSendResponse(success=True, message_id="")
            
            # 遍历消息段并发送
            for segment in request.segments:
                if segment.type == PlatformSendSegmentType.TEXT:
                    # 发送文本消息
                    text_content = segment.content
                    if text_content and text_content.strip():
                        result = await self.http_client.send_text_message(
                            to_wxid=channel_id,
                            content=text_content
                        )
                        # 根据实际 API 响应解析 message_id
                        if isinstance(result, dict) and result.get("Code") == 200:
                            # API 返回的是字典格式，包含 Data 字段
                            data_list = result.get("Data", [])
                            if data_list and len(data_list) > 0:
                                first_msg = data_list[0]
                                if first_msg.get("isSendSuccess"):
                                    resp = first_msg.get("resp", {})
                                    chat_send_ret_list = resp.get("chat_send_ret_list", [])
                                    if chat_send_ret_list:
                                        msg_id = str(chat_send_ret_list[0].get("newMsgId", int(time.time() * 1000)))
                                    else:
                                        msg_id = f"wechat_{int(time.time() * 1000)}"
                                else:
                                    msg_id = f"wechat_{int(time.time() * 1000)}"
                            else:
                                msg_id = f"wechat_{int(time.time() * 1000)}"
                        else:
                            msg_id = f"wechat_{int(time.time() * 1000)}"
                        message_ids.append(msg_id)
                        logger.info(f"发送文本消息成功: {text_content[:50]}...")
                
                elif segment.type == PlatformSendSegmentType.AT:
                    # 处理@消息段，在微信中作为文本发送
                    if segment.at_info:
                        at_text = f"@{segment.at_info.nickname or segment.at_info.platform_user_id}"
                        result = await self.http_client.send_text_message(
                            to_wxid=channel_id,
                            content=at_text
                        )
                        msg_id = f"wechat_{int(time.time() * 1000)}"
                        message_ids.append(msg_id)
                        logger.info(f"发送@消息成功: {at_text}")
                
                elif segment.type == PlatformSendSegmentType.IMAGE:
                    # 发送图片消息，优先使用新版API
                    file_path = segment.file_path
                    image_data = segment.content  # base64数据在content中
                    
                    msg_id = f"wechat_{int(time.time() * 1000)}"
                    
                    # 优先使用文件路径发送（新版API）
                    if file_path and os.path.exists(file_path):
                        try:
                            with open(file_path, 'rb') as f:
                                image_bytes = f.read()
                            
                            result = await self.http_client.send_image_new_message(image_bytes)
                            logger.info(f"使用新版API发送图片成功: {file_path}")
                            message_ids.append(msg_id)
                            continue
                        except Exception as e:
                            logger.warning(f"新版API发送图片失败，回退到旧版API: {e}")
                    
                    # 回退到旧版API（base64模式）
                    if image_data:
                        try:
                            # 如果是文件路径，需要转换为 base64
                            if image_data.startswith("data:image/"):
                                # 已经是 base64 格式
                                image_base64 = image_data.split(",")[1] if "," in image_data else image_data
                            else:
                                # 假设是 base64 编码的图片数据
                                image_base64 = image_data
                            
                            result = await self.http_client.send_image_message(
                                to_wxid=channel_id,
                                image_base64=image_base64
                            )
                            logger.info(f"使用旧版API发送图片成功")
                            message_ids.append(msg_id)
                        except Exception as e:
                            logger.error(f"发送图片消息失败: {e}")
                
                elif segment.type == PlatformSendSegmentType.FILE:
                    # 发送文件消息（语音文件等）
                    file_path = segment.file_path
                    file_data = segment.content  # base64数据在content中
                    # 从文件路径中提取文件名
                    file_name = os.path.basename(file_path) if file_path else "unknown"
                    
                    msg_id = f"wechat_{int(time.time() * 1000)}"
                    
                    # 判断是否为语音文件
                    is_voice = (
                        file_name.lower().endswith(('.wav', '.mp3', '.amr', '.silk'))
                        # 暂时去掉mime_type检查，因为PlatformSendSegment没有这个字段
                    )
                    
                    if is_voice:
                        # 发送语音消息
                        if file_path and os.path.exists(file_path):
                            try:
                                with open(file_path, 'rb') as f:
                                    voice_bytes = f.read()
                                
                                result = await self.http_client.send_voice_message(voice_bytes)
                                logger.info(f"发送语音消息成功: {file_path}")
                                message_ids.append(msg_id)
                            except Exception as e:
                                logger.error(f"发送语音消息失败: {e}")
                        elif file_data:
                            try:
                                # 假设 file_data 是 base64编码的数据
                                import base64
                                voice_bytes = base64.b64decode(file_data)
                                
                                result = await self.http_client.send_voice_message(voice_bytes)
                                logger.info(f"发送语音消息成功")
                                message_ids.append(msg_id)
                            except Exception as e:
                                logger.error(f"发送语音消息失败: {e}")
                    else:
                        # 其他文件类型暂不支持
                        logger.warning(f"暂不支持的文件类型: {file_name}")
                
                else:
                    logger.warning(f"不支持的消息段类型: {segment.type}")
            
            # 返回发送结果
            return PlatformSendResponse(
                message_id=",".join(message_ids) if message_ids else "",
                success=len(message_ids) > 0
            )
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"错误详情: {e}")
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            return PlatformSendResponse(
                message_id="",
                success=False,
                error_message=str(e)
            )

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        try:
            result = await self.http_client.get_user_profile()
            
            # 根据实际 API 响应解析数据
            user_info = result.get("userInfo", {})
            
            # 解析嵌套的数据结构
            wxid = ""
            nickname = ""
            
            if "userName" in user_info:
                user_name_data = user_info["userName"]
                if isinstance(user_name_data, dict) and "str" in user_name_data:
                    wxid = user_name_data["str"]
                else:
                    wxid = str(user_name_data)
            
            if "nickName" in user_info:
                nick_name_data = user_info["nickName"]
                if isinstance(nick_name_data, dict) and "str" in nick_name_data:
                    nickname = nick_name_data["str"]
                else:
                    nickname = str(nick_name_data)
            
            # 如果没有昵称，使用微信号
            if not nickname:
                nickname = wxid
            
            return PlatformUser(
                user_id=wxid,
                user_name=nickname,
                platform_name="微信",
                avatar_url="",  # 头像 URL 需要另外处理
            )
            
        except Exception as e:
            logger.error(f"获取自身信息失败: {e}")
            # 返回默认值
            return PlatformUser(
                user_id="unknown",
                user_name="未知用户",
                platform_name="微信",
                avatar_url="",
            )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户信息"""
        try:
            # 优先尝试获取单个联系人详情
            try:
                contact_details = await self.http_client.get_contact_details(user_id)
                # TODO: 根据实际API响应解析联系人详情
                # 这里需要根据实际响应格式进行解析
                if contact_details:
                    return PlatformUser(
                        user_id=user_id,
                        user_name=user_id,  # 暂时使用 user_id，待实际测试后修正
                        platform_name="微信",
                        avatar_url="",
                    )
            except Exception as detail_error:
                logger.warning(f"获取联系人详情失败: {detail_error}")
            
            # 如果单个联系人详情获取失败，尝试从好友列表中查找
            try:
                friend_list_result = await self.http_client.get_friend_list()
                # 根据测试结果，好友列表API已正常工作
                # 这里需要根据实际响应格式进行解析
                logger.info(f"好友列表响应: {friend_list_result}")
                
                # 暂时返回默认信息，待实际测试后修正
                return PlatformUser(
                    user_id=user_id,
                    user_name=user_id,
                    platform_name="微信",
                    avatar_url="",
                )
            except Exception as friend_error:
                logger.warning(f"获取好友列表失败: {friend_error}")
            
            # 如果所有方法都失败，返回默认信息
            return PlatformUser(
                user_id=user_id,
                user_name=user_id,
                platform_name="微信",
                avatar_url="",
            )
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            # 返回默认值
            return PlatformUser(
                user_id=user_id,
                user_name=user_id,
                platform_name="微信",
                avatar_url="",
            )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道(群聊/私聊)信息"""
        try:
            # 判断是群聊还是私聊（群聊 ID 通常以 @chatroom 结尾）
            is_group = channel_id.endswith("@chatroom")
            
            if is_group:
                # 群聊
                try:
                    result = await self.http_client.get_chatroom_info(channel_id)
                    # TODO: 需要根据实际 API 响应解析群名
                    channel_name = result.get("ChatroomName", channel_id)
                    chat_type = ChatType.GROUP
                except Exception:
                    # 如果获取群信息失败，使用默认值
                    channel_name = channel_id
                    chat_type = ChatType.GROUP
            else:
                # 私聊 - 使用简化处理
                channel_name = channel_id  # 暂时使用 channel_id 作为显示名
                chat_type = ChatType.PRIVATE
            
            return PlatformChannel(
                channel_id=channel_id,
                channel_name=channel_name,
                channel_type=chat_type,
            )
            
        except Exception as e:
            logger.error(f"获取频道信息失败: {e}")
            # 返回默认值
            return PlatformChannel(
                channel_id=channel_id,
                channel_name=channel_id,
                channel_type=ChatType.PRIVATE,  # 默认为私聊
            )
    
    # ==================== 实时消息处理方法 ====================
    
    async def start_realtime_processing(self) -> bool:
        """启动实时消息处理"""
        if not self.realtime_processor:
            logger.error("实时消息处理器未初始化")
            return False
        
        if self._realtime_task and not self._realtime_task.done():
            logger.warning("实时消息处理已在运行")
            return True
        
        try:
            # 创建异步任务并添加错误处理
            async def _start_with_error_handling():
                try:
                    await self.realtime_processor.start()
                except Exception as e:
                    logger.error(f"实时消息处理器运行失败: {e}")
                    logger.error(f"错误类型: {type(e).__name__}")
                    import traceback
                    logger.error(f"堆栈跟踪: {traceback.format_exc()}")
                    
            self._realtime_task = asyncio.create_task(_start_with_error_handling())
            logger.info("实时消息处理已启动")
            
            # 等待一小段时间检查是否成功启动
            await asyncio.sleep(1.0)
            if self._realtime_task.done():
                # 如果任务已经结束，可能是出错了
                try:
                    await self._realtime_task  # 获取异常
                except Exception as e:
                    logger.error(f"实时消息处理器启动失败: {e}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"启动实时消息处理失败: {e}")
            return False
    
    async def stop_realtime_processing(self) -> bool:
        """停止实时消息处理"""
        if self.realtime_processor:
            await self.realtime_processor.stop()
        
        if self._realtime_task and not self._realtime_task.done():
            self._realtime_task.cancel()
            try:
                await self._realtime_task
            except asyncio.CancelledError:
                pass
        
        logger.info("实时消息处理已停止")
        return True
    
    def add_message_handler(self, handler: MessageHandler) -> bool:
        """添加消息处理器"""
        if not self.realtime_processor:
            logger.error("实时消息处理器未初始化")
            return False
        
        self.realtime_processor.add_handler(handler)
        return True
    
    def remove_message_handler(self, handler: MessageHandler) -> bool:
        """移除消息处理器"""
        if not self.realtime_processor:
            logger.error("实时消息处理器未初始化")
            return False
        
        self.realtime_processor.remove_handler(handler)
        return True
    
    def get_realtime_stats(self) -> dict:
        """获取实时消息处理统计信息"""
        if not self.realtime_processor:
            return {"error": "实时消息处理器未初始化"}
        
        return self.realtime_processor.get_stats()
    
    def is_realtime_processing(self) -> bool:
        """检查实时消息处理是否正在运行"""
        if not self.realtime_processor:
            return False
        
        return self.realtime_processor.is_running
