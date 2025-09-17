"""
Telegram 适配器工具函数
"""

from typing import List, Union, Optional
import re


class SegAt:
    """AT 消息段"""
    
    def __init__(self, platform_user_id: str, nickname: Optional[str] = None):
        self.platform_user_id = platform_user_id
        self.nickname = nickname

    def __str__(self):
        return f"@{self.platform_user_id}"


def parse_at_from_text(text: str) -> List[Union[str, SegAt]]:
    """
    从文本中解析出 @ 用户信息
    
    Telegram中的@格式为 @username 或 [用户](tg://user?id=123456789)
    
    Args:
        text: 要解析的文本
        
    Returns:
        解析后的文本段和@对象列表
    """
    result = []
    current_pos = 0
    
    # 匹配 [用户](tg://user?id=123456789) 格式
    for match in re.finditer(r'\[(.*?)\]\(tg://user\?id=(\d+)\)', text):
        # 添加匹配前的文本
        if match.start() > current_pos:
            result.append(text[current_pos:match.start()])
            
        # 创建 SegAt 对象
        nickname = match.group(1)
        user_id = match.group(2)
        result.append(SegAt(platform_user_id=user_id, nickname=nickname))
        
        current_pos = match.end()
    
    # 匹配 @username 格式
    remaining_text = text[current_pos:]
    if remaining_text:
        # 处理普通的@用户名格式
        parts = re.split(r'(\@\w+)', remaining_text)
        for part in parts:
            if part and part.startswith('@'):
                # 提取用户名（去掉@符号）
                username = part[1:]
                # 在Telegram中，我们无法直接通过用户名获取用户ID
                # 这里简化处理，将用户名作为平台用户ID
                result.append(SegAt(platform_user_id=username, nickname=username))
            elif part:
                result.append(part)
    
    return result


def format_telegram_message(text: str, max_length: int = 4096) -> List[str]:
    """
    将长文本格式化为符合 Telegram 消息长度限制的消息列表
    
    Args:
        text: 要格式化的文本
        max_length: 最大消息长度，默认4096
        
    Returns:
        格式化后的消息列表
    """
    messages = []
    
    if len(text) <= max_length:
        return [text]
    
    # 尝试按段落分割
    paragraphs = text.split('\n\n')
    current_message = ""
    
    for para in paragraphs:
        # 如果段落本身超过最大长度，需要进一步分割
        if len(para) > max_length:
            # 如果当前消息不为空，先保存
            if current_message:
                messages.append(current_message)
                current_message = ""
            
            # 按句子分割长段落
            sentences = re.split(r'(\. |\? |\! )', para)
            current_para = ""
            
            for i in range(0, len(sentences), 2):
                sentence = sentences[i]
                punctuation = sentences[i+1] if i+1 < len(sentences) else ""
                full_sentence = sentence + punctuation
                
                if len(current_para) + len(full_sentence) > max_length:
                    if current_para:
                        messages.append(current_para)
                    current_para = full_sentence
                else:
                    current_para += full_sentence
            
            if current_para:
                messages.append(current_para)
        else:
            # 检查添加当前段落是否会超过长度限制
            if current_message and len(current_message) + len('\n\n') + len(para) > max_length:
                messages.append(current_message)
                current_message = para
            else:
                if current_message:
                    current_message += '\n\n' + para
                else:
                    current_message = para
    
    if current_message:
        messages.append(current_message)
    
    return messages


def escape_markdown(text: str) -> str:
    """
    转义 Telegram Markdown 特殊字符
    
    Args:
        text: 要转义的文本
        
    Returns:
        转义后的文本
    """
    # Telegram Markdown V2 特殊字符
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    result = []
    for char in text:
        if char in special_chars:
            result.append('\\' + char)
        else:
            result.append(char)
    
    return ''.join(result)


def extract_telegram_chat_id(update_data: dict) -> Optional[str]:
    """
    从 Telegram 更新数据中提取聊天 ID
    
    Args:
        update_data: Telegram Webhook 更新数据
        
    Returns:
        聊天 ID 字符串，如果无法提取则返回 None
    """
    if 'message' in update_data:
        return str(update_data['message'].get('chat', {}).get('id'))
    elif 'edited_message' in update_data:
        return str(update_data['edited_message'].get('chat', {}).get('id'))
    elif 'callback_query' in update_data:
        return str(update_data['callback_query'].get('message', {}).get('chat', {}).get('id'))
    elif 'channel_post' in update_data:
        return str(update_data['channel_post'].get('chat', {}).get('id'))
    elif 'edited_channel_post' in update_data:
        return str(update_data['edited_channel_post'].get('chat', {}).get('id'))
    
    return None


def escape_html(text: str) -> str:
    """最小化转义 HTML 特殊字符，供 Telegram parse_mode=HTML 使用"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_mention_html(user_id: str, nickname: Optional[str] = None) -> str:
    """构建 Telegram 的用户超链接 mention 片段 (HTML)

    Args:
        user_id: Telegram 数值用户ID或用户名
        nickname: 显示文本，缺省则用 user_id
    """
    display = escape_html(nickname or user_id)
    # 使用 tg://user?id=<id> 的形式可在群内正确 @ 到用户
    return f'<a href="tg://user?id={user_id}">{display}</a>'