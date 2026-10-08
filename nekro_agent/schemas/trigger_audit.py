"""Immutable metadata describing what caused an Agent run."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from nekro_agent.schemas.chat_message import ChatMessage


class TriggerAuditSource(StrEnum):
    """Known sources that can start an Agent run."""

    DIRECT_USER = "direct_user"
    DEBOUNCE_RELEASE = "debounce_release"
    SYSTEM_MESSAGE = "system_message"
    SCHEDULED_JOB = "scheduled_job"
    CC_WORKSPACE = "cc_workspace"


class TriggerAuditContext(BaseModel):
    """Frozen trigger metadata used for execution auditing only.

    This model deliberately does not carry a ``ChatMessage``. It must not change
    history rendering, trigger checks, or the message persisted by the caller.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: TriggerAuditSource = Field(description="Agent run source")
    message_id: str | None = Field(default=None, description="Source message ID")
    sender_id: str | None = Field(default=None, description="Source sender ID")
    sender_name: str | None = Field(default=None, description="Source sender name")
    generation: int | None = Field(default=None, description="Debounce generation")

    @classmethod
    def from_chat_message(
        cls,
        message: ChatMessage,
        source: TriggerAuditSource = TriggerAuditSource.DIRECT_USER,
        generation: int | None = None,
    ) -> "TriggerAuditContext":
        """Create an audit snapshot without retaining the runtime message object."""

        return cls(
            source=source,
            message_id=str(message.message_id or "") or None,
            sender_id=str(message.sender_id or "") or None,
            sender_name=str(message.sender_name or "") or None,
            generation=generation,
        )

    @property
    def is_user_trigger(self) -> bool:
        """Whether this context identifies a user-originated trigger."""

        return self.source in {
            TriggerAuditSource.DIRECT_USER,
            TriggerAuditSource.DEBOUNCE_RELEASE,
        }
