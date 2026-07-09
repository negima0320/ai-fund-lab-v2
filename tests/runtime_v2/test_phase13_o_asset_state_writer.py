from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.asset.builder import build_current_asset_state
from ai_fund_lab_v2.runtime_v2.asset.writer import (
    asset_state_to_payload,
    write_current_asset_state,
)
from ai_fund_lab_v2.runtime_v2.current_state.reader import read_current_state
from ai_fund_lab_v2.runtime_v2.ledger.models import LedgerCashRecord


def test_asset_state_payload_can_be_written_to_state_json(tmp_path):
    state = _confirmed_empty_state()
    path = tmp_path / ".runtime/persistent_ledger/state.json"

    written = write_current_asset_state(path, state)

    assert written == path
    assert path.exists()
    assert '"asset_state_id"' in path.read_text(encoding="utf-8")


def test_writer_requires_explicit_path():
    with pytest.raises(ValueError, match="path is required"):
        write_current_asset_state(None, _confirmed_empty_state())


def test_writer_rejects_mode_rooted_runtime_path(tmp_path):
    path = tmp_path / ".runtime/production/persistent_ledger/state.json"

    with pytest.raises(ValueError, match="mode-rooted runtime paths"):
        write_current_asset_state(path, _confirmed_empty_state())


def test_asset_state_payload_matches_current_state_contract():
    payload = asset_state_to_payload(_confirmed_empty_state())

    assert payload["schema_version"] == "1"
    assert payload["positions"] == []
    assert payload["cash"] == 100000
    assert payload["buying_power"] == 50000
    assert payload["review_required"] is False
    assert payload["current_state_confirmed_empty"] is True


def test_current_state_reader_can_read_written_asset_state(tmp_path):
    state = _confirmed_empty_state()
    path = tmp_path / ".runtime/persistent_ledger/state.json"
    write_current_asset_state(path, state)

    result = read_current_state(
        mode="demo",
        environment="demo",
        object_type="persistent_ledger_state",
        base_dir=tmp_path,
    )

    assert result.classification == "CONFIRMED_EMPTY"
    assert result.exists is True
    assert result.current_state_confirmed_empty is True


def test_asset_writer_is_the_state_json_writer_skeleton():
    source = Path("src/ai_fund_lab_v2/runtime_v2/ledger").rglob("*.py")
    for path in source:
        text = path.read_text(encoding="utf-8")
        assert "state.json" not in text
        assert "write_current_asset_state" not in text


def _confirmed_empty_state():
    return build_current_asset_state(
        environment="demo",
        positions=(),
        cash_records=(
            LedgerCashRecord(
                record_id="cash-1",
                record_type="cash",
                schema_version="1",
                environment="demo",
                source="broker_cash",
                created_at="2026-07-07T00:00:00Z",
                dedup_key="cash-1",
                cash_key="cash-1",
                cash=100000,
                buying_power=50000,
                currency="JPY",
                as_of="2026-07-07T00:00:00Z",
            ),
        ),
        source="broker_cash",
        as_of="2026-07-07T00:00:00Z",
    )
