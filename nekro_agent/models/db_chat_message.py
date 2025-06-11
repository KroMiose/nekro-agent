import datetime
from typing import Any, Dict, List, cast

import json5
from tortoise import fields
from tortoise.models import Model

from nekro_agent.core.config import config
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentAt,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    segments_from_list,
)
from nekro_agent.tools.path_convertor import convert_filename_to_sandbox_upload_path


class DBChatMessage(Model):
    """数据库聊天消息模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    sender_id = fields.CharField(max_length=128, index=True, description="发送者 ID")
    sender_name = fields.CharField(max_length=128, index=True, description="发送者真实昵称")
    sender_nickname = fields.CharField(max_length=128, index=True, description="发送者显示昵称")
    is_tome = fields.IntField(description="是否与 Bot 相关")
    is_recalled = fields.BooleanField(description="是否为撤回消息")

    adapter_key = fields.CharField(max_length=64, index=True, description="适配器标识")
    message_id = fields.CharField(max_length=64, index=True, description="消息平台 ID")
    chat_key = fields.CharField(max_length=64, index=True, description="会话唯一标识")
    chat_type = fields.CharField(max_length=32, index=True, description="会话类型")
    platform_userid = fields.CharField(max_length=128, index=True, description="平台用户 ID")

    content_text = fields.TextField(description="消息内容文本")
    content_data = fields.TextField(description="消息内容数据 JSON")

    raw_cq_code = fields.TextField(description="原始 CQ 码")
    ext_data = fields.TextField(description="扩展数据")

    send_timestamp = fields.IntField(index=True, description="发送时间戳")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "chat_message"

    def parse_chat_history_prompt(self, one_time_code: str, travel_mode: bool = False) -> str:
        """解析聊天历史记录生成提示词"""
        content = convert_raw_msg_data_json_to_msg_prompt(self.content_data, one_time_code, travel_mode)
        if len(content) > config.AI_CONTEXT_LENGTH_PER_MESSAGE:  # 截断消息内容
            content = (
                content[: config.AI_CONTEXT_LENGTH_PER_MESSAGE // 4 - 3]
                + "..."
                + content[-config.AI_CONTEXT_LENGTH_PER_MESSAGE // 4 + 3 :]
                + "(content too long, omitted)"
            )
        time_str = datetime.datetime.fromtimestamp(self.send_timestamp).strftime("%m-%d %H:%M:%S")
        additional_info = f" (message_id: {self.id})" if travel_mode else ""
        return f'[{time_str} id:{self.platform_userid}] "{self.sender_nickname}" 说: {content or self.content_text}{additional_info}'

    def parse_content_data(self) -> List[ChatMessageSegment]:
        """解析内容数据"""
        return segments_from_list(cast(List[Dict], json5.loads(self.content_data)))


def convert_raw_msg_data_json_to_msg_prompt(json_data: str, one_time_code: str, travel_mode: bool = False) -> str:
    """将数据库保存的原始消息数据 JSON 转换为提示词字符串

    Args:
        json_data (str): 数据库保存的原始消息数据 JSON

    Returns:
        str: 提示词字符串
    """

    prompt_str = ""

    for seg in segments_from_list(cast(List[Dict[str, Any]], json5.loads(json_data))):
        if isinstance(seg, ChatMessageSegmentImage):
            prompt_str += (
                f"<Image:{convert_filename_to_sandbox_upload_path(seg.file_name)}>"
                if travel_mode
                else f"<{one_time_code} | Image:{convert_filename_to_sandbox_upload_path(seg.file_name)}>"
            )
        elif isinstance(seg, ChatMessageSegmentFile):
            prompt_str += (
                f"<File:{convert_filename_to_sandbox_upload_path(seg.file_name)}>"
                if travel_mode
                else f"<{one_time_code} | File:{convert_filename_to_sandbox_upload_path(seg.file_name)}>"
            )
        elif isinstance(seg, ChatMessageSegmentAt):
            prompt_str += (
                f"<At:[@id:{seg.target_platform_userid};nickname:{seg.target_nickname}@]>"
                if travel_mode
                else f"<{one_time_code} | At:[@id:{seg.target_platform_userid};nickname:{seg.target_nickname}@]>"
            )
        elif isinstance(seg, ChatMessageSegment):
            prompt_str += seg.text

    return prompt_str
