import httpx
from typing import Any, Dict, Optional, List

from nekro_agent.core import logger
from .config import WeChatPadConfig


class WeChatPadClient:
    """用于与 WeChatPadPro API 交互的客户端"""

    def __init__(self, config: WeChatPadConfig):
        self._config = config
        self._http_client = httpx.AsyncClient(
            base_url=self._config.WECHATPAD_API_URL,
            timeout=90.0,  # 增加超时时间到90秒，因为API响应较慢
        )

    async def _request(self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行 API 请求的通用方法"""
        # 使用正确的认证方式：query parameter
        params = {"key": self._config.WECHATPAD_AUTH_KEY}
        
        try:
            response = await self._http_client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
            )
            response.raise_for_status()  # 如果状态码是 4xx 或 5xx，则引发异常
            result = response.json()
            
            # 根据实际 API 响应格式解析
            code = result.get("Code")
            if code == 200:
                # 成功，返回 Data 部分
                return result.get("Data", {})
            elif code == 300:
                # 业务错误（如未登录）
                error_msg = result.get("Text", "Unknown business error")
                logger.warning(f"WeChatPad API 业务错误: {error_msg}")
                raise ValueError(f"WeChatPad API 业务错误: {error_msg}")
            else:
                # 其他错误
                error_msg = result.get("Text", "Unknown error")
                logger.error(f"WeChatPad API 错误: Code={code}, Text={error_msg}")
                raise ValueError(f"WeChatPad API 错误: {error_msg}")
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e!s} | Response: {e.response.text} | Request: {e.request.method} {e.request.url}")
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {type(e).__name__}: {e} | Request: {method} {endpoint}")
            import traceback
            logger.error(f"堆栈跟踪: {traceback.format_exc()}")
            raise

    async def set_callback_url(self) -> None:
        """设置事件回调地址"""
        if not self._config.WECHATPAD_CALLBACK_URL:
            logger.warning("回调地址未配置 (WECHATPAD_CALLBACK_URL)，将无法接收微信事件")
            return

        logger.info(f"正在设置微信回调地址: {self._config.WECHATPAD_CALLBACK_URL}")
        # TODO: 需要找到正确的设置回调地址的 API 端点
        # 目前暂时跳过设置回调地址
        logger.warning("回调地址设置功能暂未实现，请手动在 WeChatPadPro 中配置")

    # --- 消息发送相关 API ---
    
    async def send_text_message(self, to_wxid: str, content: str) -> Dict[str, Any]:
        """发送文本消息"""
        return await self._request(
            method="POST",
            endpoint="/message/SendTextMessage",
            json_data={
                "MsgItem": [
                    {
                        "MsgType": 1,  # 1 = Text
                        "TextContent": content,
                        "ToUserName": to_wxid,
                    }
                ]
            },
        )
    
    async def send_image_message(self, to_wxid: str, image_base64: str) -> Dict[str, Any]:
        """发送图片消息（使用SendTextMessage API，MsgType=3）"""
        return await self._request(
            method="POST",
            endpoint="/message/SendTextMessage",
            json_data={
                "MsgItem": [
                    {
                        "MsgType": 3,  # 3 = Image
                        "ImageContent": image_base64,
                        "ToUserName": to_wxid,
                    }
                ]
            },
        )
    
    async def send_image_new_message(self, to_wxid: str, image_file_data: bytes) -> Dict[str, Any]:
        """发送图片消息（New版本，使用MsgItem格式）"""
        # 先压缩图片，然后转换为base64
        compressed_image_data = self._compress_image(image_file_data)
        
        return await self._request(
            method="POST",
            endpoint="/message/SendImageNewMessage",
            json_data={
                "MsgItem": [
                    {
                        "MsgType": 3,  # 3 = Image
                        "ImageContent": compressed_image_data,
                        "ToUserName": to_wxid
                    }
                ]
            },
        )
    
    def _compress_image(self, image_data: bytes) -> str:
        """压缩图片并转换为base64"""
        import base64
        import io
        from PIL import Image
        
        try:
            img = Image.open(io.BytesIO(image_data))
            buf = io.BytesIO()
            if img.format == "JPEG":
                img.save(buf, "JPEG", quality=80)
            else:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(buf, "JPEG", quality=80)
            return base64.b64encode(buf.getvalue()).decode()
        except Exception as e:
            logger.error(f"图片压缩失败，使用原始数据: {e}")
            return base64.b64encode(image_data).decode('utf-8')
    
    async def send_voice_message(self, to_wxid: str, voice_file_data: bytes, duration: int = 0) -> Dict[str, Any]:
        """发送语音消息"""
        import base64
        
        # 将语音数据转换为base64
        voice_base64 = base64.b64encode(voice_file_data).decode('utf-8')
        
        return await self._request(
            method="POST",
            endpoint="/message/SendVoice",
            json_data={
                "ToUserName": to_wxid,
                "VoiceData": voice_base64,
                "VoiceFormat": 4,  # 4 = silk格式
                "VoiceSecond": duration,
            },
        )
    
    async def send_emoji_message(self, to_wxid: str, emoji_md5: str, emoji_size: int) -> Dict[str, Any]:
        """发送表情消息"""
        return await self._request(
            method="POST",
            endpoint="/message/SendEmojiMessage",
            json_data={
                "EmojiList": [{
                    "ToUserName": to_wxid,
                    "EmojiMd5": emoji_md5,
                    "EmojiSize": emoji_size
                }]
            },
        )
    
    async def get_msg_big_img(self, msg_id: int, from_user: str, to_user: str, 
                             total_len: int = 0, compress_type: int = 0) -> Dict[str, Any]:
        """获取高清图片"""
        return await self._request(
            method="POST",
            endpoint="/message/GetMsgBigImg",
            json_data={
                "CompressType": compress_type,
                "FromUserName": from_user,
                "MsgId": msg_id,
                "Section": {"DataLen": 61440, "StartPos": 0},
                "ToUserName": to_user,
                "TotalLen": total_len,
            },
        )
    
    async def get_msg_voice(self, new_msg_id: str, to_user: str, bufid: str, length: int) -> Dict[str, Any]:
        """下载语音消息"""
        return await self._request(
            method="POST",
            endpoint="/message/GetMsgVoice",
            json_data={
                "Bufid": bufid,
                "ToUserName": to_user,
                "NewMsgId": new_msg_id,
                "Length": length,
            },
        )
    

    # --- 信息获取相关 API ---
    
    async def check_login_status(self) -> Dict[str, Any]:
        """检查登录状态"""
        return await self._request(
            method="GET",
            endpoint="/login/GetLoginStatus",
        )
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """获取个人资料"""
        return await self._request(
            method="GET",
            endpoint="/user/GetProfile",
        )
    
    async def get_contact_list(self) -> Dict[str, Any]:
        """获取联系人列表（包括微信官方号、服务号等）"""
        return await self._request("POST", "/friend/GetContactList", {})
    
    async def get_friend_list(self) -> Dict[str, Any]:
        """获取好友列表（不包括微信官方号等）"""
        return await self._request("GET", "/friend/GetFriendList")
    
    async def get_contact_details(self, user_id: str) -> Dict[str, Any]:
        """获取单个联系人详情"""
        return await self._request("POST", "/friend/GetContactDetailsList", {
            "UserName": user_id
        })
    
    async def get_group_list(self) -> Dict[str, Any]:
        """获取所有群列表（包括未保存到通讯录的群）"""
        return await self._request("GET", "/group/GetAllGroupList")
    
    async def get_chatroom_info(self, chatroom_id: str) -> Dict[str, Any]:
        """获取群聊信息"""
        return await self._request(
            method="POST",
            endpoint="/group/GetChatRoomInfo",
            json_data={"ChatRoomWxIdList": [chatroom_id]},  # 根据API文档使用数组格式
        )
    
    # 兼容性方法
    async def get_self_info(self) -> Dict[str, Any]:
        """获取自身信息（兼容性方法）"""
        return await self.get_user_profile()
    
    async def get_contact(self, wxid: str) -> Dict[str, Any]:
        """获取联系人信息（兼容性方法）"""
        # TODO: 需要实现单个联系人信息获取
        logger.warning(f"单个联系人信息获取功能暂未实现: {wxid}")
        return {"UserName": wxid, "NickName": wxid}
