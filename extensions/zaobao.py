from typing import List, Dict
import httpx
from pydantic import BaseModel, ValidationError, Field

from nekro_agent.api import core, message
from nekro_agent.api.schemas import AgentCtx

# 扩展元数据
__meta__ = core.ExtMetaData(
    name="zaobao",
    version="0.1.0",
    author="XGGM",
    description="提供每日早报信息，包括新闻头条和微语。使用 Alapi.cn 的早报接口获取数据。",
)

class ZaobaoResponse(BaseModel):
    """早报接口响应模型"""
    code: int = Field(..., description="API 返回的状态码")
    msg: str = Field(default="", description="API 返回的消息")
    data: Dict[str, str | List[str]] = Field(..., description="早报数据")

@core.agent_collector.mount_method(core.MethodType.BEHAVIOR)
async def get_daily_zaobao(chat_key: str, _ctx: AgentCtx) -> str:
    """获取并发送每日早报信息
    
    Args:
        chat_key (str): 聊天标识符，用于指定发送消息的聊天
    
    Returns:
        str: 早报信息字符串，包含日期、新闻头条和微语
    
    Raises:
        ValueError: 如果 API 请求失败或数据处理出错，抛出该异常
        
    Example:
        get_daily_zaobao("chat_key")
    """
    api_token = config.ZB_API_TOKEN
    url = config.ZB_URL
    payload = {"token": api_token, "format": "json"}
    headers = {"Content-Type": "application/json"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            try:
                zaobao_data = ZaobaoResponse(**response.json())
            except ValidationError as e:
                core.logger.error(f"API 响应数据格式错误: {str(e)}")
                raise ValueError("API 响应数据格式不正确，请稍后重试。")
            
            if zaobao_data.code != 200:
                core.logger.error(f"API 返回错误: {zaobao_data.msg}")
                raise ValueError(f"API 返回错误: {zaobao_data.msg}")
            
            if not isinstance(zaobao_data.data, dict):
                core.logger.error("API 返回数据格式不正确")
                raise ValueError("API 返回数据格式不正确，请稍后重试。")
            
            required_fields = ['date', 'news', 'weiyu']
            for field in required_fields:
                if field not in zaobao_data.data:
                    core.logger.error(f"早报数据缺失关键字段: {field}")
                    raise ValueError(f"早报数据缺失关键字段 {field}，请稍后重试。")
            
            try:
                news = "\n".join(zaobao_data.data['news'])
                zaobao_message = (
                    f"今天是{zaobao_data.data['date']}\n{news}\n{zaobao_data.data['weiyu']}"
                )
                
                # 发送消息并返回成功提示
                await message.send_text(chat_key, zaobao_message, ctx=_ctx)
                return "今日早报已送达"
            except Exception as e:
                core.logger.error(f"早报信息拼接失败: {str(e)}")
                raise ValueError("早报信息处理失败，请稍后重试。")
    except httpx.RequestError as e:
        core.logger.error(f"HTTP 请求失败: {str(e)}")
        raise ValueError("无法获取早报信息，请稍后重试。")
    except Exception as e:
        core.logger.error(f"处理早报信息时出错: {str(e)}")
        raise ValueError("处理早报信息时出错，请稍后重试。")

def clean_up():
    """清理扩展资源"""
    # 如有必要，在此实现清理资源的逻辑
