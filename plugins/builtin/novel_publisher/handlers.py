"""小说自动发布插件 - 核心处理逻辑

支持 AI 生成原创小说、保存历史、定时发布到指定群聊。
"""

import asyncio
import hashlib
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from nekro_agent.api.message import push_system
from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import config as core_config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.services.agent.creator import OpenAIChatMessage
from nekro_agent.services.agent.openai import gen_openai_chat_response
from nekro_agent.services.command.base import CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse
from nekro_agent.services.timer.timer_service import timer_service

from .plugin import NovelPublishConfig, config, plugin

logger = get_sub_logger("api_bridge")
NOVEL_CHAT_KEY = "system_novel"

# 存储当前定时器任务 ID
_current_timer_task_id: Optional[str] = None


def _get_novels_meta_path() -> Path:
    """获取小说元数据存储路径"""
    data_dir = plugin.get_plugin_data_dir()
    return data_dir / "novels_meta.json"


def _get_novels_dir() -> Path:
    """获取小说内容存储目录"""
    data_dir = plugin.get_plugin_data_dir()
    novels_dir = data_dir / "novels"
    novels_dir.mkdir(parents=True, exist_ok=True)
    return novels_dir


def _load_novels_meta() -> List[Dict[str, Any]]:
    """加载已保存的小说元数据"""
    path = _get_novels_meta_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("加载小说元数据失败")
        return []


def _save_novels_meta(meta: List[Dict[str, Any]]) -> None:
    """保存小说元数据"""
    path = _get_novels_meta_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("保存小说元数据失败")


def _generate_novel_id(theme: str, style: str, word_count: int) -> str:
    """根据参数生成小说唯一标识（按天去重）"""
    content = f"{theme}:{style}:{word_count}:{datetime.now().strftime('%Y%m%d')}"
    return hashlib.md5(content.encode()).hexdigest()[:8]


async def _call_llm_generate(theme: str, style: str, word_count: int) -> str:
    """调用 LLM 生成小说内容"""
    model_group = config.MODEL_GROUP or "default"
    try:
        model_config = core_config.config.MODEL_GROUPS.get(model_group)
        if not model_config:
            model_config = core_config.config.MODEL_GROUPS.get("default")
            if not model_config:
                raise ValueError(f"模型组 '{model_group}' 不存在且没有默认模型组")  # noqa: TRY003
    except Exception as e:
        logger.error(f"获取模型配置失败: {e}")
        raise

    system_prompt = (
        "你是一位才华横溢的小说作家。请根据用户要求创作一篇原创短篇小说。\n"
        "要求：\n"
        "- 内容必须是原创的，不要复制已有作品\n"
        "- 故事情节完整，有开头、发展和结尾\n"
        "- 语言流畅，描写生动\n"
        "- 不要使用任何 Markdown 格式标记\n"
        "- 直接输出小说正文，不要添加前言或后记"
    )

    user_prompt = (
        f"请创作一篇{style}风格的{theme}短篇小说，"
        f"目标字数约{word_count}字。"
    )

    messages = [
        OpenAIChatMessage(role="system", content=system_prompt),
        OpenAIChatMessage(role="user", content=user_prompt),
    ]

    try:
        response = await gen_openai_chat_response(
            model=model_config.CHAT_MODEL,
            messages=messages,
            temperature=0.8,
            api_key=model_config.API_KEY,
            base_url=model_config.BASE_URL,
            max_tokens=min(word_count * 3, 4096),
        )
        return response.response_content.strip()
    except Exception as e:
        logger.exception(f"LLM 生成小说失败: {e}")
        raise


async def _generate_and_save_novel(theme: str, style: str, word_count: int) -> Optional[Dict[str, Any]]:
    """生成小说并保存，如果当天已存在则返回已有记录"""
    novel_id = _generate_novel_id(theme, style, word_count)
    meta_list = _load_novels_meta()

    # 检查是否已存在
    for item in meta_list:
        if item.get("novel_id") == novel_id:
            logger.info(f"小说已存在，跳过生成: {novel_id}")
            return item

    # 生成小说内容
    content = await _call_llm_generate(theme, style, word_count)

    # 保存到文件
    file_name = f"{novel_id}_{int(time.time())}.txt"
    file_path = _get_novels_dir() / file_name
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        logger.exception("保存小说文件失败")
        raise

    # 更新元数据
    meta = {
        "novel_id": novel_id,
        "theme": theme,
        "style": style,
        "word_count": word_count,
        "actual_word_count": len(content),
        "file_name": file_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    meta_list.append(meta)
    _save_novels_meta(meta_list)

    logger.info(f"小说生成并保存成功: {novel_id}")
    return meta


async def _publish_novel_to_chats(novel_id: str, chat_keys: List[str]) -> int:
    """将指定小说发布到目标群聊"""
    meta_list = _load_novels_meta()
    meta = None
    for item in meta_list:
        if item.get("novel_id") == novel_id:
            meta = item
            break

    if not meta:
        logger.error(f"小说不存在: {novel_id}")
        return 0

    # 读取小说内容
    file_path = _get_novels_dir() / meta["file_name"]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        logger.exception(f"读取小说文件失败: {file_path}")
        return 0

    # 构建发布消息
    header = f"📖 【{meta['theme']}】{meta['style']}风格短篇\n\n"
    footer = f"\n\n— 字数约{meta['actual_word_count']}字 | {meta['created_at']} —"
    full_message = header + content + footer

    sent_count = 0
    for chat_key in chat_keys:
        try:
            await push_system(chat_key, full_message, trigger_agent=False)
            sent_count += 1
            if config.RANDOM_DELAY_MAX > 0:
                await asyncio.sleep(random.randint(1, config.RANDOM_DELAY_MAX))
        except Exception as e:
            logger.error(f"向群聊 {chat_key} 发布小说失败: {e}")

    logger.info(f"小说发布完成: {novel_id}, 成功 {sent_count}/{len(chat_keys)} 个群聊")
    return sent_count


async def _auto_publish_callback():
    """自动发布回调函数"""
    current_config: NovelPublishConfig = plugin.get_config(NovelPublishConfig)
    if not current_config.ENABLE_AUTO_PUBLISH or not current_config.TARGET_CHAT_KEYS:
        return

    try:
        # 生成小说
        meta = await _generate_and_save_novel(
            theme=current_config.DEFAULT_THEME,
            style=current_config.DEFAULT_STYLE,
            word_count=current_config.DEFAULT_WORD_COUNT,
        )
        if not meta:
            logger.error("自动生成小说失败")
            return

        # 发布
        await _publish_novel_to_chats(meta["novel_id"], current_config.TARGET_CHAT_KEYS)
    except Exception:
        logger.exception("自动发布小说失败")

    # 重新设置下次定时器
    await _schedule_next_publish()


async def _schedule_next_publish():
    """计算并设置下次发布时间"""
    current_config: NovelPublishConfig = plugin.get_config(NovelPublishConfig)
    if not current_config.ENABLE_AUTO_PUBLISH or not current_config.TARGET_CHAT_KEYS:
        return

    try:
        from croniter import croniter

        itr = croniter(current_config.PUBLISH_CRON, datetime.now())
        next_dt = itr.get_next(datetime)
        trigger_time = int(next_dt.timestamp())
    except Exception:
        logger.exception("计算下次发布时间失败")
        return

    global _current_timer_task_id
    await timer_service.set_timer(
        chat_key=NOVEL_CHAT_KEY,
        trigger_time=trigger_time,
        event_desc="小说自动发布",
        silent=True,
        callback=_auto_publish_callback,
    )
    logger.info(f"下次小说发布时间: {next_dt.strftime('%Y-%m-%d %H:%M:%S')}")


# ==================== 沙盒方法 ====================

@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "生成原创小说")
async def generate_novel(
    _ctx: AgentCtx,
    theme: str,
    style: str,
    word_count: int,
) -> str:
    """调用 AI 生成一篇原创短篇小说并保存。

    会根据主题、风格和字数要求生成小说内容，自动保存到插件数据目录。
    如果相同参数的小说今天已存在，则返回已有内容。

    Args:
        theme (str): 小说主题，如"奇幻冒险"、"都市爱情"
        style (str): 写作风格，如"轻松幽默"、"悬疑紧张"
        word_count (int): 目标字数，建议 200-2000 字

    Returns:
        str: 生成结果说明，包含小说ID和摘要
    """
    try:
        meta = await _generate_and_save_novel(theme, style, word_count)
        if not meta:
            return "小说生成失败，请检查日志"

        return (
            f"✅ 小说生成成功！\n"
            f"- 主题：{meta['theme']}\n"
            f"- 风格：{meta['style']}\n"
            f"- 目标字数：{meta['word_count']}\n"
            f"- 实际字数：{meta['actual_word_count']}\n"
            f"- 小说ID：{meta['novel_id']}\n"
            f"- 生成时间：{meta['created_at']}"
        )
    except Exception as e:
        logger.exception("生成小说失败")
        return f"小说生成失败: {e}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "发布小说")
async def publish_novel(
    _ctx: AgentCtx,
    novel_id: str,
    chat_keys: List[str],
) -> str:
    """将已保存的小说发布到指定群聊。

    Args:
        novel_id (str): 小说ID
        chat_keys (List[str]): 目标群聊列表，如 ["group_123456"]

    Returns:
        str: 发布结果
    """
    if not chat_keys:
        return "目标群聊列表为空"

    sent = await _publish_novel_to_chats(novel_id, chat_keys)
    return f"小说发布完成，成功发送到 {sent} 个群聊"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "获取小说列表")
async def list_novels(_ctx: AgentCtx) -> str:
    """获取已保存的小说列表。

    Returns:
        str: 小说列表信息
    """
    meta_list = _load_novels_meta()
    if not meta_list:
        return "暂无已保存的小说"

    lines = ["📚 已保存小说列表："]
    for idx, meta in enumerate(meta_list, 1):
        lines.append(
            f"{idx}. 【{meta['theme']}】{meta['style']} | "
            f"字数:{meta['actual_word_count']} | ID:{meta['novel_id']} | {meta['created_at']}"
        )
    return "\n".join(lines)


# ==================== 命令 ====================

@plugin.mount_command(
    name="novel_publish",
    description="立即生成并发布一篇小说",
    aliases=["发布小说"],
    usage="/novel_publish [主题] [风格] [字数]",
    permission=CommandPermission.ADMIN,
)
async def novel_publish_cmd(
    context: CommandExecutionContext,
    theme: str = "",
    style: str = "",
    word_count: str = "",
) -> CommandResponse:
    """立即生成并发布小说命令"""
    current_config: NovelPublishConfig = plugin.get_config(NovelPublishConfig)
    _theme = theme or current_config.DEFAULT_THEME
    _style = style or current_config.DEFAULT_STYLE
    _word_count = int(word_count) if word_count.isdigit() else current_config.DEFAULT_WORD_COUNT

    try:
        meta = await _generate_and_save_novel(_theme, _style, _word_count)
        if not meta:
            return CmdCtl.failed("小说生成失败")

        if current_config.TARGET_CHAT_KEYS:
            sent = await _publish_novel_to_chats(meta["novel_id"], current_config.TARGET_CHAT_KEYS)
            return CmdCtl.success(
                f"小说生成并发布成功！\n"
                f"主题：{meta['theme']}\n"
                f"字数：{meta['actual_word_count']}\n"
                f"成功发布到 {sent} 个群聊"
            )
        return CmdCtl.success(
            f"小说生成成功！\n"
            f"主题：{meta['theme']}\n"
            f"字数：{meta['actual_word_count']}\n"
            f"小说ID：{meta['novel_id']}"
        )
    except Exception as e:
        logger.exception("命令发布小说失败")
        return CmdCtl.failed(f"发布失败: {e}")


@plugin.mount_command(
    name="novel_list",
    description="查看已保存的小说列表",
    aliases=["小说列表"],
    usage="/novel_list",
    permission=CommandPermission.ADMIN,
)
async def novel_list_cmd(context: CommandExecutionContext) -> CommandResponse:
    """查看小说列表命令"""
    meta_list = _load_novels_meta()
    if not meta_list:
        return CmdCtl.success("暂无已保存的小说")

    lines = ["📚 已保存小说列表："]
    for idx, meta in enumerate(meta_list, 1):
        lines.append(
            f"{idx}. 【{meta['theme']}】{meta['style']} | "
            f"字数:{meta['actual_word_count']} | ID:{meta['novel_id']} | {meta['created_at']}"
        )
    return CmdCtl.success("\n".join(lines))


@plugin.mount_command(
    name="novel_read",
    description="查看指定小说的内容",
    aliases=["阅读小说"],
    usage="/novel_read <小说ID>",
    permission=CommandPermission.ADMIN,
)
async def novel_read_cmd(
    context: CommandExecutionContext,
    novel_id: str = "",
) -> CommandResponse:
    """查看小说内容命令"""
    if not novel_id:
        return CmdCtl.failed("请提供小说ID，使用 /novel_list 查看列表")

    meta_list = _load_novels_meta()
    meta = None
    for item in meta_list:
        if item.get("novel_id") == novel_id:
            meta = item
            break

    if not meta:
        return CmdCtl.failed(f"小说不存在: {novel_id}")

    file_path = _get_novels_dir() / meta["file_name"]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return CmdCtl.failed("读取小说文件失败")

    return CmdCtl.success(
        f"📖 【{meta['theme']}】{meta['style']}风格\n"
        f"字数：{meta['actual_word_count']} | 生成于：{meta['created_at']}\n"
        f"{'=' * 20}\n"
        f"{content}"
    )


# ==================== 生命周期 ====================

@plugin.mount_init_method()
async def init():
    """插件初始化"""
    pass


@plugin.on_enabled()
async def on_enabled():
    """插件启用时设置定时器"""
    await _schedule_next_publish()


@plugin.on_disabled()
async def on_disabled():
    """插件禁用时清除定时器"""
    await timer_service.set_timer(chat_key=NOVEL_CHAT_KEY, trigger_time=-1, event_desc="")


@plugin.mount_cleanup_method()
async def cleanup():
    """插件清理"""
    await timer_service.set_timer(chat_key=NOVEL_CHAT_KEY, trigger_time=-1, event_desc="")
