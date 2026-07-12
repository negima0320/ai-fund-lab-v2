from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.data_readiness import evaluate_runtime_data_readiness
from ai_fund_lab_v2.runtime_v2.runtime_state import (
    produce_runtime_operation_state,
    validate_runtime_operation_state,
)
from ai_fund_lab_v2.runtime_v2.safety.evaluation import run_runtime_safety_evaluation


BUSINESS_DATE = "2026-07-10"


def test_phase15ba_runtime_state_producer_writes_authoritative_contract(tmp_path):
    root = tmp_path / ".runtime"

    result = produce_runtime_operation_state(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )
    payload = _load_json(root / "runtime_state" / "current_state.json")

    assert result.status == "READY"
    assert payload["schema_version"] == "runtime_v2_operation_state_v1"
    assert payload["role"] == "authoritative_runtime_operation_state"
    assert payload["asset_state_is_authoritative_here"] is False
    assert payload["pending_state_is_authoritative_here"] is False


def test_phase15ba_runtime_state_validator_rejects_stale_legacy_role(tmp_path):
    root = tmp_path / ".runtime"
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "business_date": "2026-07-09",
            "generated_at": "2026-07-09T00:00:00Z",
            "environment": "demo",
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "source": "legacy_fixture",
        },
    )

    result = validate_runtime_operation_state(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "runtime_state_contract_missing_fields"
    assert "schema_version" in result.missing_fields


def test_phase15ba_data_readiness_requires_runtime_state_contract(tmp_path):
    root = _runtime_root(tmp_path)
    (root / "runtime_state" / "current_state.json").unlink()

    result = evaluate_runtime_data_readiness(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        readiness_scope="execution",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["runtime_state_status"] == "REVIEW_REQUIRED"
    assert "runtime_state_missing" in result.payload["review_reasons"]
    assert result.payload["components"]["runtime_state"]["contract_role"] == ""


def test_phase15ba_safety_uses_runtime_state_contract_validator(tmp_path):
    root = _runtime_root(tmp_path)
    runtime_state = _load_json(root / "runtime_state" / "current_state.json")
    runtime_state["role"] = "legacy_advisory"
    _write_json(root / "runtime_state" / "current_state.json", runtime_state)

    result = run_runtime_safety_evaluation(
        runtime_root=root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "runtime_state" in result.manifest_fields["stale_evidence"]


def test_phase15ba_cli_runtime_state_refresh_job(tmp_path):
    root = _runtime_root(tmp_path, write_runtime_state=False)

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "runtime_state_refresh",
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
    manifest = _latest_manifest(root)

    assert exit_code == 0
    assert manifest["runtime_state_status"] == "READY"
    assert (root / "runtime_state" / "current_state.json").is_file()


def _runtime_root(tmp_path: Path, *, write_runtime_state: bool = True) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "runtime_v2_current_temporal_v1",
            "business_date": BUSINESS_DATE,
            "as_of": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "updated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "environment": "demo",
            "source": "fixture",
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "position_state_as_of": BUSINESS_DATE,
            "valuation_as_of": BUSINESS_DATE,
            "source_market_date": BUSINESS_DATE,
            "last_execution_date": BUSINESS_DATE,
            "last_reconciled_at": BUSINESS_DATE + "T09:00:00+00:00",
            "current_position_status": "READY",
            "current_valuation_status": "READY",
            "temporal_schema_version": "runtime_v2_current_temporal_v1",
            "review_required": False,
        },
    )
    for name in ("orders", "executions", "positions", "cash", "events"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "EMPTY", "active_pending": False, "items": []})
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": BUSINESS_DATE,
            "runtime_business_date": BUSINESS_DATE,
            "market_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"source": "fixture"},
            "quotes": {},
            "candidate_universe_market_summary": {"market_crash": False, "daily_loss_pct": "0"},
        },
    )
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "snapshot_at": BUSINESS_DATE + "T09:00:00+00:00",
            "environment": "demo",
            "broker_mode": "demo",
            "positions": [],
            "orders": [],
            "executions": [],
        },
    )
    _write_json(
        root / "safety" / "locks" / "manual_emergency_state.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "is_locked": False,
            "status": "CLEAR",
        },
    )
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_policy_version": "safety_operation_guard_v1",
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "expires_at": BUSINESS_DATE + "T23:59:59+00:00",
        },
    )
    if write_runtime_state:
        produce_runtime_operation_state(runtime_root=root, business_date=BUSINESS_DATE, mode="demo", now=_now())
    return root


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_manifest(root: Path) -> dict:
    manifests = sorted((root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return _load_json(manifests[-1])


def _now() -> datetime:
    return datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
