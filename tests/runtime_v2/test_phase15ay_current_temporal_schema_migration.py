from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.current_state.temporal import (
    CURRENT_TEMPORAL_SCHEMA_VERSION,
    build_current_temporal_candidate,
    read_current_temporal,
    run_current_temporal_migration,
)


BUSINESS_DATE = "2026-07-10"


def test_phase15ay_legacy_reader_marks_legacy_as_of_and_not_production_equivalent(tmp_path):
    root = _runtime_root(tmp_path)
    _write_legacy_current(root, as_of="2026-07-09", positions=[_position("7203")])

    candidate, metadata = read_current_temporal(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert candidate["legacy_as_of_used"] is True
    assert candidate["legacy_migration_status"] == "LEGACY_DERIVED"
    assert candidate["production_equivalent"] is False
    assert metadata.review_required is True
    assert metadata.production_equivalent is False


def test_phase15ay_legacy_without_evidence_is_review_required_not_ready(tmp_path):
    root = _runtime_root(tmp_path)
    _write_legacy_current(root, as_of="2026-07-09", positions=[_position("7203")])

    result = run_current_temporal_migration(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.legacy_as_of_used is True
    assert "runtime_owned_execution_ledger" in result.missing_evidence
    assert "market_evidence" in result.missing_evidence


def test_phase15ay_new_schema_preserves_separate_position_and_valuation_dates(tmp_path):
    root = _runtime_root(tmp_path)
    _write_new_current(root)

    candidate, metadata = read_current_temporal(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert metadata.review_required is False
    assert candidate["position_state_as_of"] == "2026-07-09"
    assert candidate["valuation_as_of"] == BUSINESS_DATE
    assert candidate["source_market_date"] == BUSINESS_DATE
    assert candidate["no_fill"] is True
    assert candidate["positions"][0]["quantity"] == 100
    assert candidate["positions"][0]["average_price"] == 900


def test_phase15ay_position_previous_day_valuation_today_is_contract_ready(tmp_path):
    root = _runtime_root(tmp_path)
    _write_new_current(root)

    candidate, _ = read_current_temporal(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert candidate["current_position_status"] == "READY"
    assert candidate["current_valuation_status"] == "READY"


def test_phase15ay_non_trading_day_valid_carryover(tmp_path):
    root = _runtime_root(tmp_path)
    _write_new_current(root, business_date="2026-07-11", valuation_as_of=BUSINESS_DATE, source_market_date=BUSINESS_DATE)

    candidate, _ = read_current_temporal(runtime_root=root, business_date="2026-07-11", now=datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc))

    assert candidate["current_valuation_status"] == "VALID_CARRYOVER"


def test_phase15ay_ledger_and_market_evidence_derive_candidate_dates(tmp_path):
    root = _runtime_root(tmp_path)
    _write_legacy_current(root, as_of="2026-07-08", positions=[_position("7203")])
    _write_execution(root, business_date="2026-07-09", symbol="7203")
    _write_market_evidence(root, market_date=BUSINESS_DATE)

    result = run_current_temporal_migration(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.candidate_current["position_state_as_of"] == "2026-07-09"
    assert result.candidate_current["last_execution_date"] == "2026-07-09"
    assert result.candidate_current["valuation_as_of"] == BUSINESS_DATE
    assert result.candidate_current["source_market_date"] == BUSINESS_DATE


def test_phase15ay_broker_only_position_is_not_added(tmp_path):
    root = _runtime_root(tmp_path)
    _write_legacy_current(root, as_of=BUSINESS_DATE, positions=[])
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {"positions": [_position("9999")]},
    )

    result = run_current_temporal_migration(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.candidate_current.get("positions") == []


def test_phase15ay_dry_run_does_not_modify_current(tmp_path):
    root = _runtime_root(tmp_path)
    _write_new_current(root)
    before = (root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")

    result = run_current_temporal_migration(runtime_root=root, business_date=BUSINESS_DATE, now=_now())
    after = (root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")

    assert result.apply_requested is False
    assert result.apply_executed is False
    assert before == after


def test_phase15ay_apply_requires_explicit_option_and_writes_backup(tmp_path):
    root = _runtime_root(tmp_path)
    _write_new_current(root)

    result = run_current_temporal_migration(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_migration=True,
        now=_now(),
    )
    current = _load_json(root / "persistent_ledger" / "state.json")

    assert result.status == "READY"
    assert result.apply_requested is True
    assert result.apply_executed is True
    assert Path(result.backup_path).is_file()
    assert current["temporal_schema_version"] == CURRENT_TEMPORAL_SCHEMA_VERSION


def test_phase15bd_safe_legacy_temporal_metadata_apply_preserves_position_and_cash(tmp_path):
    root = _runtime_root(tmp_path)
    _write_legacy_current(root, as_of="2026-07-09", positions=[_position("7203")])
    _write_execution(root, business_date="2026-07-09", symbol="7203")
    _write_market_evidence(root, market_date=BUSINESS_DATE)
    before = _load_json(root / "persistent_ledger" / "state.json")

    result = run_current_temporal_migration(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_migration=True,
        now=_now(),
    )
    current = _load_json(root / "persistent_ledger" / "state.json")

    assert result.status == "READY"
    assert result.apply_executed is True
    assert Path(result.backup_path).is_file()
    assert current["temporal_schema_version"] == CURRENT_TEMPORAL_SCHEMA_VERSION
    assert current["position_state_as_of"] == "2026-07-09"
    assert current["valuation_as_of"] == BUSINESS_DATE
    assert current["positions"][0]["quantity"] == before["positions"][0]["quantity"]
    assert current["positions"][0]["average_price"] == before["positions"][0]["average_price"]
    assert current["cash"] == before["cash"]
    assert current["buying_power"] == before["buying_power"]


def test_phase15ay_migration_idempotent_for_same_input(tmp_path):
    root = _runtime_root(tmp_path)
    _write_new_current(root)

    first = run_current_temporal_migration(runtime_root=root, business_date=BUSINESS_DATE, now=_now())
    second = run_current_temporal_migration(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert first.candidate_current == second.candidate_current


def test_phase15ay_corrupt_current_is_halt_artifact(tmp_path):
    root = _runtime_root(tmp_path)
    path = root / "persistent_ledger" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad json", encoding="utf-8")

    result = run_current_temporal_migration(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "HALT"
    assert Path(result.artifact_path).is_file()


def test_phase15ay_cli_job_writes_dry_run_artifact_without_apply(tmp_path):
    root = _runtime_root(tmp_path)
    _write_new_current(root)

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "current_temporal_migration",
            "--business-date",
            BUSINESS_DATE,
            "--runtime-root",
            str(root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(root / "runtime_state" / "logs"),
            "--evaluation-time",
            _now().isoformat(),
        ]
    )
    artifact = root / "runtime_state" / "current_migration" / BUSINESS_DATE / "current_temporal_migration.json"
    payload = _load_json(artifact)

    assert exit_code == 0
    assert payload["apply_requested"] is False
    assert payload["apply_executed"] is False
    assert payload["candidate_current"]["temporal_schema_version"] == CURRENT_TEMPORAL_SCHEMA_VERSION


def test_phase15ay_candidate_builder_does_not_default_to_today(tmp_path):
    root = _runtime_root(tmp_path)
    current = {
        "schema_version": "1",
        "as_of": "2026-07-08",
        "updated_at": "2026-07-08T00:00:00+00:00",
        "positions": [],
    }

    candidate, _, _, _ = build_current_temporal_candidate(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        current_payload=current,
        now=_now(),
    )

    assert candidate["position_state_as_of"] == "2026-07-08"
    assert candidate["valuation_as_of"] == "2026-07-08"


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_legacy_current(root: Path, *, as_of: str, positions: list[dict]) -> None:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "as_of": as_of,
            "updated_at": as_of + "T00:00:00+00:00",
            "positions": positions,
            "cash": 1000000,
            "buying_power": 1000000,
            "market_value": sum(float(position.get("market_value") or 0) for position in positions),
        },
    )


def _write_new_current(
    root: Path,
    *,
    business_date: str = BUSINESS_DATE,
    valuation_as_of: str = BUSINESS_DATE,
    source_market_date: str = BUSINESS_DATE,
) -> None:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "temporal_schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "position_state_as_of": "2026-07-09",
            "valuation_as_of": valuation_as_of,
            "source_market_date": source_market_date,
            "last_execution_date": "2026-07-09",
            "last_reconciled_at": business_date + "T08:00:00+00:00",
            "updated_at": business_date + "T09:00:00+00:00",
            "positions": [_position("7203")],
            "cash": 1000000,
            "buying_power": 1000000,
            "market_value": 100000,
            "production_equivalent": True,
        },
    )


def _write_execution(root: Path, *, business_date: str, symbol: str) -> None:
    path = root / "persistent_ledger" / "executions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"business_date": business_date, "symbol": symbol, "runtime_owned": True, "quantity": 100}
    path.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")


def _write_market_evidence(root: Path, *, market_date: str) -> None:
    artifact = root / "runtime_state" / "market" / market_date / "market_evidence.json"
    _write_json(
        artifact,
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "market_date": market_date,
            "latest_available_market_date": market_date,
        },
    )
    _write_json(
        root / "runtime_state" / "market" / "latest.json",
        {"artifact_path": str(artifact), "market_date": market_date},
    )


def _position(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "quantity": 100,
        "average_price": 900,
        "current_price": 1000,
        "market_value": 100000,
        "ownership": "runtime_owned",
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
