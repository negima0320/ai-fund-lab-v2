import json

from ai_fund_lab_v2.safety_phase11.emergency_flag import (
    clear_manual_emergency_flag_candidate,
    create_manual_emergency_flag,
    read_manual_emergency_flag,
)
from ai_fund_lab_v2.safety_phase11.models import SafetyState
from ai_fund_lab_v2.safety_phase11.state_machine import SafetyStateMachine


def test_manual_emergency_flag_create_read_and_clear_candidate(tmp_path):
    path = create_manual_emergency_flag(created_by="operator", reason="manual stop", runtime_dir=tmp_path)
    assert path.exists()
    payload = read_manual_emergency_flag(runtime_dir=tmp_path)
    assert payload["active"] is True
    assert payload["created_by"] == "operator"
    assert payload["raw_response_saved"] is False
    assert payload["auto_trade_executed"] is False

    clear_manual_emergency_flag_candidate(cleared_by="operator", reason="reviewed", runtime_dir=tmp_path)
    cleared = read_manual_emergency_flag(runtime_dir=tmp_path)
    assert cleared["active"] is False
    assert cleared["auto_recovery_executed"] is False

    machine = SafetyStateMachine(SafetyState.EMERGENCY_STOP)
    next_machine, result = machine.transition_to(SafetyState.NORMAL)
    assert result.allowed is False
    assert next_machine.current_state is SafetyState.EMERGENCY_STOP


def test_manual_emergency_flag_sanitizes_forbidden_values(tmp_path):
    path = create_manual_emergency_flag(
        created_by="auth_id=AUTH-PLAINTEXT",
        reason=(
            "raw_request=RAW-REQUEST raw_response=RAW-RESPONSE "
            "account_id=ACCOUNT order_id=ORDER execution_id=EXEC "
            "second_password=SECOND https://secret.example.test/path"
        ),
        runtime_dir=tmp_path,
    )
    text = path.read_text(encoding="utf-8")
    assert "AUTH-PLAINTEXT" not in text
    assert "RAW-REQUEST" not in text
    assert "RAW-RESPONSE" not in text
    assert "ACCOUNT" not in text
    assert "ORDER" not in text
    assert "EXEC" not in text
    assert "SECOND" not in text
    assert "secret.example.test" not in text

    payload = json.loads(text)
    assert payload["active"] is True
    assert payload["raw_response_saved"] is False
