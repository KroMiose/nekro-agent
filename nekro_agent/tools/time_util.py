from typing import List


def format_duration(seconds: int) -> str:
    """将秒数转换为易读的时间格式
    
    Args:
        seconds (int): 秒数
        
    Returns:
        str: 格式化后的时间字符串，如 "1天2小时3分钟4秒"
    """
    if seconds == 0:
        return "0秒"
        
    units = [
        (86400, "天"),
        (3600, "小时"),
        (60, "分钟"),
        (1, "秒"),
    ]
    
    parts: List[str] = []
    remaining = seconds
    
    for unit_seconds, unit_name in units:
        if remaining >= unit_seconds:
            count = remaining // unit_seconds
            remaining %= unit_seconds
            parts.append(f"{count}{unit_name}")
            
    return "".join(parts) 