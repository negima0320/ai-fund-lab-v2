from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.broker_readonly import refresh as broker_readonly_refresh
from ai_fund_lab_v2.runtime_v2.broker_readonly.refresh import run_broker_readonly_refresh
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main


BUSINESS_DATE = "2026-07-10"
EVALUATION_TIME = "2026-07-10T09:10:00+00:00"


def test_phase15bd_broker_readonly_refresh_cli_snapshot_only_no_mutations(tmp_path, monkeypatch):
    monkeypatch.setattr(broker_readonly_refresh, "_default_snapshot_provider", lambda: _fake_snapshot_provider)
    runtime_root = _runtime_root(tmp_path)
    before_current = (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")
    before_pending = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "broker_readonly_refresh",
            "--business-date",
            BUSINESS_DATE,
            "--evaluation-time",
            EVALUATION_TIME,
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
        ]
    )

    manifest = _latest_manifest(tmp_path, BUSINESS_DATE)
    snapshot = _load_json(runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "tachibana_snapshot.json")
    latest = _load_json(runtime_root / "runtime_state" / "broker_readonly" / "latest.json")

    assert exit_code == 0
    assert manifest["broker_readonly_refresh_status"] == "READY"
    assert manifest["broker_snapshot_freshness_status"] == "READY"
    assert snapshot["runtime_schema_version"] == "runtime_v2_broker_readonly_snapshot_v1"
    assert snapshot["runtime_business_date"] == BUSINESS_DATE
    assert snapshot["read_only"] is True
    assert snapshot["ledger_appended"] is False
    assert snapshot["current_position_apply_executed"] is False
    assert snapshot["pending_mutation_executed"] is False
    assert snapshot["broker_write_executed"] is False
    assert snapshot["account_id_redacted"] == "REDACTED"
    assert latest["snapshot_path"].endswith("tachibana_snapshot.json")
    assert not (runtime_root / "persistent_ledger" / "orders.jsonl").exists()
    assert not (runtime_root / "persistent_ledger" / "executions.jsonl").exists()
    assert (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8") == before_current
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before_pending
    assert "PASSWORD_VALUE" not in json.dumps(snapshot)


def test_phase15bd_broker_readonly_refresh_stale_and_missing_require_review(tmp_path):
    stale_root = _runtime_root(tmp_path / "stale")
    stale = run_broker_readonly_refresh(
        runtime_root=stale_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=_dt(EVALUATION_TIME),
        snapshot_provider=lambda **kwargs: _fake_snapshot_provider(**kwargs, generated_at="2026-07-10T08:00:00+00:00"),
    )
    missing_root = _runtime_root(tmp_path / "missing")
    missing = run_broker_readonly_refresh(
        runtime_root=missing_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=_dt(EVALUATION_TIME),
        snapshot_provider=lambda **kwargs: type("SnapshotResult", (), {"status": "PASS"})(),
    )

    assert stale.status == "REVIEW_REQUIRED"
    assert stale.freshness_status == "STALE"
    assert missing.status == "REVIEW_REQUIRED"
    assert missing.reason == "broker readonly snapshot was not created"


def test_phase15bd_broker_readonly_refresh_idempotent_paths_with_fixed_time(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    kwargs = {
        "runtime_root": runtime_root,
        "business_date": BUSINESS_DATE,
        "mode": "demo",
        "evaluation_time": _dt(EVALUATION_TIME),
        "snapshot_provider": _fake_snapshot_provider,
    }

    first = run_broker_readonly_refresh(**kwargs)
    second = run_broker_readonly_refresh(**kwargs)

    assert first.status == "READY"
    assert second.status == "READY"
    assert first.snapshot_path == second.snapshot_path
    assert first.latest_pointer_path == second.latest_pointer_path
    assert not (runtime_root / "persistent_ledger" / "orders.jsonl").exists()


def _runtime_root(tmp_path: Path) -> Path:
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "environment": "demo",
            "business_date": BUSINESS_DATE,
            "as_of": "2026-07-09",
            "positions": [],
            "cash": 1000000,
            "buying_power": 1000000,
            "market_value": 0,
            "total_equity": 1000000,
        },
    )
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "state": "EMPTY",
            "status": "EMPTY",
            "active_pending": False,
        },
    )
    return runtime_root


def _fake_snapshot_provider(**kwargs):
    return _write_snapshot(
        kwargs["snapshot_path"],
        kwargs["report_path"],
        kwargs.get("source") or "test",
        generated_at=kwargs.get("generated_at", "2026-07-10T09:05:00+00:00"),
    )


def _write_snapshot(snapshot_path: Path | str, report_path: Path | str, source: str, generated_at: str = "2026-07-10T09:05:00+00:00"):
    snapshot_path = Path(snapshot_path)
    report_path = Path(report_path)
    _write_json(
        snapshot_path,
        {
            "schema_version": "tachibana_broker_snapshot_v1",
            "broker": "tachibana",
            "environment": "demo",
            "generated_at": generated_at,
            "session_status": "PASS",
            "source": source,
            "provider": "tachibana",
            "adapter": "tachibana_broker_snapshot",
            "transport": "HTTP_POST",
            "raw_response_origin": "TACHIBANA_API_RESPONSE",
            "data_origin": "BROKER_API",
            "fixture_used": False,
            "mock_used": False,
            "read_only": True,
            "account_identity_hash": "sha256:test-account",
            "account_identity_status": "REFERENCE_HASHED",
            "credential_reference_id": "sha256:test-credential",
            "account_summary": {"data_origin": "BROKER_API", "cash_available": "1000000", "buying_power": "1000000"},
            "buying_power": {"data_origin": "BROKER_API", "buying_power": "1000000"},
            "positions": [{"data_origin": "BROKER_API", "symbol": "7203", "quantity": "100", "available_quantity": "100"}],
            "orders": [],
            "executions": [],
            "redaction_status": {
                "auth_identifier_saved": False,
                "private_secret_saved": False,
                "account_customer_id_saved": False,
            },
        },
    )
    _write_json(report_path, {"status": "PASS", "source": source})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_manifest(tmp_path: Path, business_date: str) -> dict:
    path = next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return _load_json(path)


def _dt(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))
