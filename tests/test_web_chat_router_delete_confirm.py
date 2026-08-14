import pytest

from nekro_agent.adapters.web.routers import DELETE_SESSION_CONFIRM_MESSAGE, _ensure_delete_session_confirmed
from nekro_agent.schemas.errors import ValidationError


def test_delete_web_session_requires_explicit_confirmation() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _ensure_delete_session_confirmed(False)

    assert exc_info.value.params["reason"] == DELETE_SESSION_CONFIRM_MESSAGE


def test_delete_web_session_accepts_explicit_confirmation() -> None:
    _ensure_delete_session_confirmed(True)
