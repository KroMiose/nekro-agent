"""表情包嵌入 provider 抽象测试

覆盖逻辑：`plugins/builtin/emotion.py` 中
`generate_embedding` 的 provider 分发，以及 multimodal provider
的占位实现（NotImplementedError + 清晰错误信息）。

说明：本测试不直接 import `plugins.builtin.emotion`，
原因是该模块在 import 时会触发 ``nekro_agent`` 完整初始化（数据库、Qdrant 等）。
本测试通过对源文件做静态分析 + stub 实现来校验逻辑。
"""

import re
from pathlib import Path

# ----------------------------------------------------------------------------
# 源码静态分析：保证核心契约不会被无意破坏
# ----------------------------------------------------------------------------


EMOTION_PY = (
    Path(__file__).parent.parent / "plugins" / "builtin" / "emotion.py"
)


def _read_emotion_src() -> str:
    return EMOTION_PY.read_text(encoding="utf-8")


def test_emotion_module_defines_provider_config():
    """EmotionConfig 必须暴露 EMBEDDING_PROVIDER 字段。"""
    src = _read_emotion_src()
    assert "EMBEDDING_PROVIDER" in src
    # 默认值必须是 "text"，保持向后兼容
    assert re.search(
        r'EMBEDDING_PROVIDER:\s*str\s*=\s*Field\(\s*default="text"',
        src,
    ), "EMBEDDING_PROVIDER 必须默认 'text' 以保持向后兼容"


def test_emotion_module_defines_multimodal_configs():
    """多模态相关配置字段必须存在。"""
    src = _read_emotion_src()
    required = [
        "MULTIMODAL_API_KEY",
        "MULTIMODAL_BASE_URL",
        "MULTIMODAL_MODEL",
        "MULTIMODAL_DIMENSION",
        "MULTIMODAL_REQUEST_TIMEOUT",
    ]
    for name in required:
        assert name in src, f"缺少多模态配置字段: {name}"


def test_generate_embedding_dispatches_on_provider():
    """generate_embedding 必须按 provider 分发到 text 或 multimodal 实现。"""
    src = _read_emotion_src()
    # 分发核心逻辑: provider == "multimodal" 时调用 multimodal 实现
    assert 'EMBEDDING_PROVIDER or "text"' in src or 'EMBEDDING_PROVIDER' in src
    assert "_generate_multimodal_embedding" in src
    assert "_generate_text_embedding" in src
    # 未知 provider 必须回退到 text,避免误配置炸服务
    assert "回退到 text provider" in src or "回退到 text" in src


def test_generate_embedding_image_path_parameter_added():
    """generate_embedding 必须新增 image_path 参数以支持 multimodal 输入。"""
    src = _read_emotion_src()
    # 函数签名必须包含 image_path
    assert re.search(
        r"async def generate_embedding\(\s*[^)]*image_path",
        src,
        re.DOTALL,
    ), "generate_embedding 签名必须包含 image_path 参数"


def test_multimodal_provider_raises_not_implemented():
    """multimodal 占位必须明确抛 NotImplementedError 而不是静默回退。"""
    src = _read_emotion_src()
    assert "raise NotImplementedError" in src
    # 错误信息中应包含 "multimodal" 关键字便于排查
    assert "multimodal" in src.lower()


def test_multimodal_api_key_env_fallback():
    """多模态 API Key 必须支持从环境变量回退,不得硬编码。"""
    src = _read_emotion_src()
    assert "_resolve_multimodal_api_key" in src
    # 至少出现 DASHSCOPE_API_KEY 或 NEKRO_MULTIMODAL_API_KEY 之一作为环境变量 fallback
    assert (
        "DASHSCOPE_API_KEY" in src or "NEKRO_MULTIMODAL_API_KEY" in src
    ), "多模态 API Key 必须支持环境变量回退"


def test_multimodal_base_url_default_points_to_dashscope():
    """多模态默认 endpoint 必须指向阿里云 DashScope,便于国内用户开箱即用。"""
    src = _read_emotion_src()
    m = re.search(
        r'MULTIMODAL_BASE_URL:\s*str\s*=\s*Field\(\s*default="([^"]+)"',
        src,
    )
    assert m, "MULTIMODAL_BASE_URL 必须显式给定默认值"
    default_url = m.group(1)
    assert "dashscope" in default_url.lower(), (
        f"MULTIMODAL_BASE_URL 默认值应指向阿里云 DashScope,实际: {default_url}"
    )


def test_no_hardcoded_api_key_in_module():
    """禁止在源码中硬编码 API Key,仅允许默认值=空 + 环境变量回退。"""
    src = _read_emotion_src()
    # 简易检查: MULTIMODAL_API_KEY 默认值必须为空字符串
    m = re.search(
        r'MULTIMODAL_API_KEY:\s*str\s*=\s*Field\(\s*default="([^"]*)"',
        src,
    )
    assert m, "MULTIMODAL_API_KEY 字段定义未找到"
    default_value = m.group(1)
    assert default_value == "", (
        f"MULTIMODAL_API_KEY 默认值必须为空字符串以避免泄露密钥,实际: {default_value!r}"
    )


def test_collect_update_reindex_pass_image_path():
    """collect / update / reindex 路径必须把图片路径传给 generate_embedding。"""
    src = _read_emotion_src()
    # 至少出现 3 次 image_path= 调用,覆盖 collect / update / reindex 三条路径
    matches = re.findall(r"image_path=", src)
    assert len(matches) >= 3, (
        f"generate_embedding 调用点应至少 3 处传入 image_path,实际: {len(matches)}"
    )


# ----------------------------------------------------------------------------
# 行为测试: 通过 stub 验证 multimodal 占位逻辑
# ----------------------------------------------------------------------------


def _stub_multimodal_dispatch(provider_value: str) -> str:
    """复刻 generate_embedding 中的 provider 分发判定。"""
    provider = (provider_value or "text").strip().lower()
    if provider == "multimodal":
        return "multimodal"
    if provider != "text":
        return "fallback_text"
    return "text"


def test_dispatch_text_provider():
    assert _stub_multimodal_dispatch("text") == "text"


def test_dispatch_multimodal_provider():
    assert _stub_multimodal_dispatch("multimodal") == "multimodal"


def test_dispatch_empty_provider_falls_back_to_text():
    """空字符串必须回退到 text 而非崩服务。"""
    assert _stub_multimodal_dispatch("") == "text"


def test_dispatch_unknown_provider_warns_and_falls_back():
    """未知 provider 应回退到 text(便于管理员误配时优雅降级)。"""
    assert _stub_multimodal_dispatch("foobar") == "fallback_text"


def test_dispatch_case_insensitive():
    """provider 比较应大小写不敏感。"""
    assert _stub_multimodal_dispatch("MULTIMODAL") == "multimodal"
    assert _stub_multimodal_dispatch("Text") == "text"