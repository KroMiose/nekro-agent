import pytest
from pydantic import ValidationError

from nekro_agent.schemas.trigger_audit import TriggerAuditContext, TriggerAuditSource


def test_trigger_audit_context_is_immutable_and_excludes_message_content() -> None:
    context = TriggerAuditContext(
        source=TriggerAuditSource.DEBOUNCE_RELEASE,
        message_id="message-1",
        sender_id="3265694993",
        sender_name="Healock",
        generation=7,
    )

    assert context.is_user_trigger
    assert context.model_dump() == {
        "source": "debounce_release",
        "message_id": "message-1",
        "sender_id": "3265694993",
        "sender_name": "Healock",
        "generation": 7,
    }
    with pytest.raises(ValidationError):
        context.sender_id = "other-user"  # type: ignore[misc]


def test_system_trigger_is_not_misidentified_as_a_user() -> None:
    context = TriggerAuditContext(source=TriggerAuditSource.SYSTEM_MESSAGE)

    assert not context.is_user_trigger
    assert context.sender_id is None
    assert context.sender_name is None


def test_trigger_audit_source_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError):
        TriggerAuditContext(source="guessed_from_recent_history")
