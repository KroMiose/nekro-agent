"""CC Prompt 元信息封装（转发导入）

实际定义位于 nekro_agent.services.workspace.prompt_envelope，
此处保留以维持插件内部导入路径的兼容性。
"""

from nekro_agent.services.workspace.prompt_envelope import CcPromptEnvelope, CcPromptMeta

__all__ = ["CcPromptEnvelope", "CcPromptMeta"]
