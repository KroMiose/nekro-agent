from pathlib import Path

from nekro_agent.api.schemas import AgentCtx
from nekro_agent.tools.common_util import (
    download_file,
)
from nekro_agent.tools.path_convertor import convert_filename_to_sandbox_upload_path


async def get_avatar(user_qq: str, ctx: AgentCtx) -> str:
    """获取用户头像

    Args:
        user_qq (str): 用户QQ号
        ctx (AgentCtx): 上下文对象

    Returns:
        str: 头像文件路径

    Example:
        ```python
        from nekro_agent.api.user import get_avatar

        # 获取用户头像
        avatar_path = get_avatar("123456789", ctx)
        ```
    """
    try:
        file_path, file_name = await download_file(
            f"https://q1.qlogo.cn/g?b=qq&nk={user_qq}&s=640",
            from_chat_key=ctx.chat_key,
            use_suffix=".png",
        )
        return str(convert_filename_to_sandbox_upload_path(Path(file_path)))
    except Exception as e:
        raise Exception(f"获取用户头像失败: {e}") from e
