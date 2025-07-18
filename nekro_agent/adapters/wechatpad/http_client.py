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
            timeout=30.0,
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
            logger.error(f"HTTP error occurred: {e!s} | Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e!s}")
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
                "ToUserName": to_wxid,
                "TextContent": content,
            },
        )
    
    async def send_image_message(self, to_wxid: str, image_base64: str) -> Dict[str, Any]:
        """发送图片消息"""
        return await self._request(
            method="POST",
            endpoint="/message/SendImageMessage",
            json_data={
                "ToUserName": to_wxid,
                "ImageContent": image_base64,
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
            json_data={"ChatroomId": chatroom_id},
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
