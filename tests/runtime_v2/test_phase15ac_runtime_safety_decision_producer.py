from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.safety.producer import produce_runtime_safety_decision
from ai_fund_lab_v2.runtime_v2.safety_decision import load_runtime_safety_decision


BUSINESS_DATE = "2026-07-10"


def test_phase15ac_valid_authoritative_source_produces_runtime_safety_decision(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    source = _write_phase11_report(tmp_path / "reports" / "safety" / "phase11" / "safety_report.json")

    result = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        source_artifact_path=source,
        now=_now(),
    )
    decision = load_runtime_safety_decision(runtime_root=runtime_root, business_date=BUSINESS_DATE, mode="demo")

    assert result.status == "PASS"
    assert Path(result.runtime_safety_decision_path).exists()
    assert Path(result.history_path).exists()
    assert decision.safety_status == "PASS"
    assert decision.decision == "ALLOW"
    assert decision.safety_policy_version == "phase11_safety_report_v2"
    assert decision.safety_source == str(source)


def test_phase15ac_missing_source_does_not_generate_allow(tmp_path):
    runtime_root = _runtime_root(tmp_path)

    result = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        source_artifact_path=tmp_path / "missing.json",
        now=_now(),
    )
    decision = load_runtime_safety_decision(runtime_root=runtime_root, business_date=BUSINESS_DATE, mode="demo")

    assert result.status == "REVIEW_REQUIRED"
    assert decision.decision == "REVIEW_REQUIRED"
    assert decision.block_buy is True
    assert decision.block_sell is True
    assert decision.block_submit is True
    assert decision.reason == "authoritative safety source missing"


def test_phase15ac_stale_source_becomes_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    source = _write_phase11_report(
        tmp_path / "reports" / "safety" / "phase11" / "safety_report.json",
        expires_at="2026-07-09T00:00:00+00:00",
    )

    result = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        source_artifact_path=source,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.manifest_fields["source_freshness_status"].startswith("REVIEW_REQUIRED:")
    assert "source expired" in result.reason


def test_phase15ac_conflicting_trading_lock_does_not_allow(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    source = _write_phase11_report(tmp_path / "reports" / "safety" / "phase11" / "safety_report.json")
    _write_json(
        runtime_root / "safety" / "locks" / "trading_lock.json",
        {
            "is_locked": True,
            "reason": "manual trading lock active",
            "status": "HALT",
            "created_at": "2026-07-10T08:00:00+00:00",
        },
    )

    result = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        source_artifact_path=source,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.decision.decision == "REVIEW_REQUIRED"
    assert "conflicting Safety evidence" in result.reason


def test_phase15ac_emergency_stop_maps_to_halt(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    source = _write_phase11_report(
        tmp_path / "reports" / "safety" / "phase11" / "safety_report.json",
        overall_decision="EMERGENCY_STOP",
        next_state="EMERGENCY_STOP",
        emergency_candidates=["DUPLICATE_ORDER_SYSTEM_EMERGENCY"],
    )

    result = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        source_artifact_path=source,
        now=_now(),
    )

    assert result.status == "HALT"
    assert result.decision.decision == "HALT"
    assert result.decision.halt_runtime is True
    assert result.decision.emergency_stop is True


def test_phase15ac_buy_sell_block_flags_are_separated(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    source = _write_phase11_report(
        tmp_path / "reports" / "safety" / "phase11" / "safety_report.json",
        overall_decision="REVIEW_REQUIRED",
        next_state="BUY_REVIEW_REQUIRED",
        review_required_items=[{"reason_code": "BUY_REVIEW_REQUIRED", "message": "buy needs review"}],
        buy_review_required=["BUY_REVIEW_REQUIRED"],
        sell_review_required=[],
    )

    result = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        source_artifact_path=source,
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.decision.block_buy is True
    assert result.decision.block_sell is False
    assert result.decision.block_submit is True


def test_phase15ac_cli_safety_refresh_regular_path_generates_reader_artifact(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    source = _write_phase11_report(tmp_path / "reports" / "safety" / "phase11" / "safety_report.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "safety_refresh",
            "--business-date",
            BUSINESS_DATE,
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
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--safety-report-path",
            str(source),
        ]
    )
    decision = load_runtime_safety_decision(runtime_root=runtime_root, business_date=BUSINESS_DATE, mode="demo")
    manifest = _latest_manifest(runtime_root)

    assert exit_code == 0
    assert decision.decision == "ALLOW"
    assert manifest["safety_producer_status"] == "PASS"
    assert manifest["authoritative_safety_source"] == "phase11_safety_report_v2"
    assert manifest["runtime_safety_decision_path"].endswith("latest_safety_decision.json")


def test_phase15ac_runtime_mainline_has_no_fixture_safety_producer():
    for path in Path("src/ai_fund_lab_v2/runtime_v2").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "_write_safety_decision" not in text
        assert "phase15_safety_allow" not in text
        assert "demo_safety_decision.json" not in text


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15ac",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE,
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-phase15ac",
            "state": "CONSUMED",
            "environment": "demo",
            "items": [],
        },
    )
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED", "environment": "demo"})
    for name in ("orders", "executions", "positions", "cash", "events"):
        path = root / "persistent_ledger" / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return root


def _write_phase11_report(
    path: Path,
    *,
    overall_decision: str = "ALLOW",
    next_state: str = "NORMAL",
    expires_at: str = "2099-01-01T00:00:00+00:00",
    emergency_candidates: list[str] | None = None,
    review_required_items: list[dict] | None = None,
    buy_review_required: list[str] | None = None,
    sell_review_required: list[str] | None = None,
) -> Path:
    _write_json(
        path,
        {
            "schema_version": "phase11_safety_report_v2",
            "report_id": "safety-report-phase15ac",
            "business_date": BUSINESS_DATE,
            "generated_at": "2026-07-10T08:00:00+00:00",
            "expires_at": expires_at,
            "environment": "demo",
            "runtime_id": "runtime-v2-demo",
            "current_safety_state": "NORMAL",
            "overall_decision": overall_decision,
            "next_recommended_safety_state": next_state,
            "transition_reason": overall_decision,
            "blocked_actions": [] if overall_decision == "ALLOW" else ["broker_order_api"],
            "review_required_items": review_required_items or [],
            "emergency_candidates": emergency_candidates or [],
            "buy_review_required": buy_review_required or [],
            "sell_review_required": sell_review_required or [],
        },
    )
    return path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
