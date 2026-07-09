import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.current_state.reader import read_current_state


def test_missing_current_file_returns_missing(tmp_path):
    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="runtime_state",
        base_dir=tmp_path,
    )

    assert result.classification == "MISSING"
    assert result.exists is False
    assert result.state_missing is True
    assert result.review_required is True


def test_missing_persistent_ledger_state_is_not_confirmed_empty(tmp_path):
    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="persistent_ledger_state",
        base_dir=tmp_path,
    )

    assert result.classification == "MISSING"
    assert result.current_state_confirmed_empty is False
    assert result.current_positions_unknown is True
    assert result.cash_unknown is True
    assert result.buying_power_unknown is True


def test_json_current_file_can_be_read(tmp_path):
    path = tmp_path / ".runtime/runtime_state/current_state.json"
    _write_json(
        path,
        {
            "schema_version": "1",
            "runtime_id": "runtime-demo",
            "run_id": "run-1",
            "state": "IDLE",
            "environment": "demo",
            "updated_at": "2026-07-07T00:00:00Z",
        },
    )

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="runtime_state",
        base_dir=tmp_path,
    )

    assert result.classification == "VALID"
    assert result.exists is True
    assert result.valid is True
    assert result.payload["state"] == "IDLE"


def test_jsonl_current_file_can_be_read(tmp_path):
    path = tmp_path / ".runtime/persistent_ledger/orders.jsonl"
    _write_text(
        path,
        json.dumps(
            {
                "schema_version": "1",
                "ledger_record_id": "order-1",
                "recorded_at": "2026-07-07T00:00:00Z",
                "environment": "demo",
                "source": "submit_runtime",
                "review_required": False,
            }
        )
        + "\n",
    )

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="persistent_ledger_orders",
        base_dir=tmp_path,
    )

    assert result.classification == "VALID"
    assert result.valid is True
    assert len(result.payload) == 1


def test_invalid_json_returns_invalid(tmp_path):
    path = tmp_path / ".runtime/runtime_state/current_state.json"
    _write_text(path, "{ invalid json")

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="runtime_state",
        base_dir=tmp_path,
    )

    assert result.classification == "INVALID"
    assert result.valid is False
    assert result.review_required is True


def test_invalid_jsonl_returns_invalid(tmp_path):
    path = tmp_path / ".runtime/persistent_ledger/orders.jsonl"
    _write_text(path, "{ invalid jsonl\n")

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="persistent_ledger_orders",
        base_dir=tmp_path,
    )

    assert result.classification == "INVALID"
    assert result.valid is False
    assert result.review_required is True


def test_mode_and_environment_are_required(tmp_path):
    with pytest.raises(ValueError, match="mode is required"):
        read_current_state(
            mode="",
            environment="demo",
            object_type="runtime_state",
            base_dir=tmp_path,
        )

    with pytest.raises(ValueError, match="environment is required"):
        read_current_state(
            mode="demo",
            environment="",
            object_type="runtime_state",
            base_dir=tmp_path,
        )


def test_default_production_fallback_does_not_exist(tmp_path):
    with pytest.raises(TypeError):
        read_current_state(
            environment="demo",
            object_type="runtime_state",
            base_dir=tmp_path,
        )


def _write_json(path: Path, payload):
    _write_text(path, json.dumps(payload))


def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
