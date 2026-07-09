import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.orchestrator.models import RuntimeRunRequest
from ai_fund_lab_v2.runtime_v2.orchestrator.orchestrator import RuntimeOrchestrator
from ai_fund_lab_v2.runtime_v2.state_machine.models import RuntimeState


def test_runtime_run_request_requires_mode_environment_and_business_date():
    with pytest.raises(TypeError):
        RuntimeRunRequest(environment="demo", business_date="2026-07-07")

    with pytest.raises(TypeError):
        RuntimeRunRequest(mode="demo", business_date="2026-07-07")

    with pytest.raises(TypeError):
        RuntimeRunRequest(mode="demo", environment="demo")

    with pytest.raises(ValueError, match="mode is required"):
        RuntimeRunRequest(mode="", environment="demo", business_date="2026-07-07")

    with pytest.raises(ValueError, match="environment is required"):
        RuntimeRunRequest(mode="demo", environment="", business_date="2026-07-07")


def test_run_preflight_returns_runtime_run_result_for_missing_current(tmp_path):
    request = RuntimeRunRequest(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
    )

    result = RuntimeOrchestrator(base_dir=tmp_path).run_preflight(request)

    assert result.start_state == RuntimeState.IDLE
    assert result.end_state == RuntimeState.REVIEW_REQUIRED
    assert result.review_required is True
    assert result.blocked is False
    assert result.side_effect_executed is False
    assert result.transitions
    assert all(transition.allowed for transition in result.transitions)


def test_valid_minimal_current_state_causes_current_state_loaded(tmp_path):
    _write_json(
        tmp_path / ".runtime/persistent_ledger/state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-1",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
            "positions": [{"symbol": "7203", "quantity": 100}],
            "cash": {"amount": 100000},
            "buying_power": {"amount": 50000},
            "source": "broker_positions",
            "review_required": False,
        },
    )
    request = RuntimeRunRequest(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
    )

    result = RuntimeOrchestrator(base_dir=tmp_path).run_preflight(request)

    assert result.end_state == RuntimeState.CURRENT_STATE_LOADED
    assert result.review_required is False
    assert result.blocked is False
    assert result.side_effect_executed is False
    assert [transition.to_state for transition in result.transitions] == [
        RuntimeState.MARKET_DATA_READY,
        RuntimeState.FEATURE_READY,
        RuntimeState.CURRENT_STATE_LOADED,
    ]
    assert all(transition.allowed for transition in result.transitions)


def test_unknown_current_state_causes_review_required(tmp_path):
    _write_json(
        tmp_path / ".runtime/persistent_ledger/state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-unknown",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
            "positions": None,
            "cash": None,
            "buying_power": None,
            "source": "unknown",
            "review_required": False,
        },
    )
    request = RuntimeRunRequest(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
    )

    result = RuntimeOrchestrator(base_dir=tmp_path).run_preflight(request)

    assert result.end_state == RuntimeState.REVIEW_REQUIRED
    assert result.review_required is True
    assert result.side_effect_executed is False


def test_invalid_current_state_causes_review_required(tmp_path):
    path = tmp_path / ".runtime/persistent_ledger/state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ invalid json", encoding="utf-8")
    request = RuntimeRunRequest(
        mode="demo",
        environment="demo",
        business_date="2026-07-07",
    )

    result = RuntimeOrchestrator(base_dir=tmp_path).run_preflight(request)

    assert result.end_state == RuntimeState.REVIEW_REQUIRED
    assert result.review_required is True
    assert result.side_effect_executed is False


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
