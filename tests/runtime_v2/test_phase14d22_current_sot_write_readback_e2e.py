from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.asset.models import CurrentAssetState
from ai_fund_lab_v2.runtime_v2.asset.writer import write_current_asset_state
from ai_fund_lab_v2.runtime_v2.current_sot_write_readback import (
    run_current_sot_write_readback_e2e,
)
from ai_fund_lab_v2.runtime_v2.current_state.reader import read_current_state
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerCashRecord
from ai_fund_lab_v2.runtime_v2.ledger.writer import write_ledger_records
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import resolve_current_path


def test_phase14d22_current_sot_write_readback_e2e(tmp_path):
    result = run_current_sot_write_readback_e2e(
        base_dir=tmp_path,
        evidence_root=Path(".runtime/phase14d15"),
    )

    assert result.final_decision == "PHASE14D22_CURRENT_SOT_WRITE_READBACK_PASS"
    assert result.mode_rooted_write_rejected is True
    assert result.state_readback_classification == "VALID"
    assert result.orders_readback_classification == "VALID"
    assert result.executions_readback_classification == "VALID"
    assert result.positions_readback_classification == "VALID"
    assert result.cash_readback_classification == "VALID"
    assert result.events_readback_classification == "VALID"
    assert result.pending_readback_classification == "VALID"
    assert result.runtime_state_readback_classification == "VALID"
    assert result.after_position_7203_quantity == 0.0
    assert result.cash == 19999648.0
    assert result.buying_power == 19999648.0
    assert result.reconciliation_findings == 0
    assert result.audit_findings == 0
    assert result.per_run_artifact_used_as_current is False


def test_phase14d22_fixed_current_paths_are_read_back(tmp_path):
    result = run_current_sot_write_readback_e2e(
        base_dir=tmp_path,
        evidence_root=Path(".runtime/phase14d15"),
    )

    state_path = tmp_path / ".runtime/persistent_ledger/state.json"
    mode_state_path = tmp_path / ".runtime/demo/persistent_ledger/state.json"
    cash_path = tmp_path / ".runtime/persistent_ledger/cash.jsonl"

    assert result.fixed_state_path == str(state_path)
    assert state_path.exists()
    assert cash_path.exists()
    assert not mode_state_path.exists()

    readback = read_current_state(
        mode="demo",
        environment="demo",
        object_type="persistent_ledger_state",
        base_dir=tmp_path,
    )
    assert readback.path == state_path
    assert readback.classification == "VALID"


def test_phase14d22_writers_reject_mode_rooted_current_paths(tmp_path):
    state = _current_asset_state()
    with pytest.raises(ValueError, match="mode-rooted runtime paths"):
        write_current_asset_state(
            tmp_path / ".runtime/demo/persistent_ledger/state.json",
            state,
        )

    with pytest.raises(ValueError, match="mode-rooted runtime paths"):
        write_ledger_records(
            tmp_path / ".runtime/demo/persistent_ledger/cash.jsonl",
            (_cash_record(),),
        )


def test_phase14d22_resolver_returns_fixed_current_paths():
    assert resolve_current_path("demo", "demo", "persistent_ledger_state") == Path(
        ".runtime/persistent_ledger/state.json"
    )
    assert resolve_current_path("production", "production", "persistent_ledger_state") == Path(
        ".runtime/persistent_ledger/state.json"
    )
    assert resolve_current_path("demo", "demo", "persistent_ledger_cash") == Path(
        ".runtime/persistent_ledger/cash.jsonl"
    )


def _current_asset_state():
    from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state

    return build_current_asset_state(
        environment="demo",
        positions=(),
        cash_records=(_cash_record(),),
        source="phase14d22_fixture",
        as_of="2026-07-07",
    )


def _cash_record():
    return LedgerCashRecord(
        record_id="cash-1",
        record_type="cash",
        schema_version="1",
        environment="demo",
        source="phase14d22_fixture",
        created_at="2026-07-07T00:00:00Z",
        dedup_key="cash-1",
        cash_key="cash-1",
        cash=100000.0,
        buying_power=100000.0,
        currency="JPY",
        as_of="2026-07-07T00:00:00Z",
    )
