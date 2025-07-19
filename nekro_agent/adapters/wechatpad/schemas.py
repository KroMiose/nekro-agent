from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class WeChatPadEvent(BaseModel):
    """WeChatPad 事件基础模型"""
    type: Optional[str] = Field(None, description="事件类型")
    type_name: Optional[str] = Field(None, description="事件类型名称")
    data: Optional[Dict[str, Any]] = Field(None, description="事件数据")


class WeChatPadMessageEvent(BaseModel):
    """WeChatPad 消息事件模型 - 基于 API 文档的实际结构"""
    # 基础消息字段
    FromUserName: Optional[str] = Field(None, description="发送者微信ID")
    ToUserName: Optional[str] = Field(None, description="接收者微信ID")
    MsgType: Optional[int] = Field(None, description="消息类型")
    Content: Optional[str] = Field(None, description="消息内容")
    CreateTime: Optional[int] = Field(None, description="创建时间戳")
    MsgId: Optional[int] = Field(None, description="消息ID")
    NewMsgId: Optional[str] = Field(None, description="新消息ID")
    ClientMsgId: Optional[int] = Field(None, description="客户端消息ID")
    
    # 消息内容相关
    TextContent: Optional[str] = Field(None, description="文本内容")
    ImageContent: Optional[str] = Field(None, description="图片内容(base64)")
    
    # 群聊相关字段
    ChatroomId: Optional[str] = Field(None, description="群聊ID")
    AtWxIDList: Optional[List[str]] = Field(None, description="@用户列表")
    

class WeChatPadContact(BaseModel):
    """WeChatPad 联系人模型"""
    Wxid: Optional[str] = Field(None, description="微信ID")
    NickName: Optional[str] = Field(None, description="昵称")
    Remark: Optional[str] = Field(None, description="备注")
    HeadImgUrl: Optional[str] = Field(None, description="头像URL")
    

class WeChatPadChatroom(BaseModel):
    """WeChatPad 群聊模型"""
    ChatroomId: Optional[str] = Field(None, description="群聊ID")
    ChatroomName: Optional[str] = Field(None, description="群聊名称")
    MemberCount: Optional[int] = Field(None, description="成员数量")
    

# 消息类型常量（根据实际测试结果和微信协议）
class MessageType:
    """微信消息类型常量 - 基于实际测试结果"""
    # 基础消息类型
    TEXT = 1  # 文本消息
    IMAGE = 3  # 图片消息（实际测试结果）
    FILE = 6  # 文件消息
    
    # 扩展消息类型（基于微信协议和实际测试）
    VOICE = 34  # 语音消息
    VIDEO = 43  # 视频消息
    EMOJI = 47  # 表情消息
    LOCATION = 48  # 位置消息
    LINK = 49  # 链接消息
    SYSTEM = 10000  # 系统消息
    
    # 发送消息时使用的类型（API文档中的MessageItem）
    class SendType:
        """发送消息时使用的消息类型"""
        TEXT = 1  # 文本消息
        IMAGE = 2  # 图片消息


class MessageItem(BaseModel):
    """消息项模型 - 用于发送消息"""
    AtWxIDList: Optional[List[str]] = Field(None, description="发送艾特消息时的 wxid 列表")
    ImageContent: Optional[str] = Field(None, description="图片类型消息时图片的 base64 编码")
    MsgType: Optional[int] = Field(None, description="消息类型: 1 Text 2 Image")
    TextContent: Optional[str] = Field(None, description="文本类型消息时内容")
    ToUserName: Optional[str] = Field(None, description="接收者 wxid")


class SendMessageModel(BaseModel):
    """发送消息模型"""
    MsgItem: Optional[List[MessageItem]] = Field(None, description="消息体数组")
