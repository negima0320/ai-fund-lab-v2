from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.safety.evaluation import run_runtime_safety_evaluation
from ai_fund_lab_v2.runtime_v2.safety.producer import produce_runtime_safety_decision
from ai_fund_lab_v2.runtime_v2.safety_decision import load_runtime_safety_decision


BUSINESS_DATE = "2026-07-10"


def test_phase15ad_runtime_evidence_maps_to_valid_phase11_safety_report(tmp_path):
    runtime_root = _runtime_root(tmp_path)

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )
    report = json.loads(Path(result.safety_report_path).read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert report["schema_version"] == "phase11_safety_report_v2"
    assert report["business_date"] == BUSINESS_DATE
    assert report["environment"] == "demo"
    assert report["expires_at"]
    assert report["overall_decision"] == "ALLOW"
    assert report["input_evidence_sources"]["current"].endswith("persistent_ledger/state.json")
    assert report["input_freshness_status"] == "PASS"
    assert result.manifest_fields["safety_evaluation_status"] == "PASS"
    assert result.manifest_fields["current_source"].endswith("persistent_ledger/state.json")
    assert result.manifest_fields["safety_report_path"] == str(result.safety_report_path)


def test_phase15ad_missing_current_is_review_required_not_allow(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    (runtime_root / "persistent_ledger" / "state.json").unlink()

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )
    report = json.loads(Path(result.safety_report_path).read_text(encoding="utf-8"))

    assert result.status == "REVIEW_REQUIRED"
    assert report["overall_decision"] == "REVIEW_REQUIRED"
    assert "current" in report["missing_evidence"]
    assert "RUNTIME_EVIDENCE_MISSING" in {item["reason_code"] for item in report["review_required_items"]}


def test_phase15ad_stale_current_is_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    current_path = runtime_root / "persistent_ledger" / "state.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["business_date"] = "2026-07-09"
    current["generated_at"] = "2026-07-09T09:00:00+00:00"
    _write_json(current_path, current)

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "current" in result.manifest_fields["stale_evidence"]


def test_phase15ad_missing_broker_snapshot_is_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    for path in (runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE).glob("*.json"):
        path.unlink()

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "broker_snapshot" in result.manifest_fields["missing_evidence"]
    assert result.manifest_fields["input_freshness_status"] == "MISSING_EVIDENCE"


def test_phase15ad_missing_market_evidence_is_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    (runtime_root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json").unlink()

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "market" in result.manifest_fields["missing_evidence"]


def test_phase15ad_manual_emergency_lock_maps_to_halt(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_json(
        runtime_root / "safety" / "locks" / "manual_emergency_state.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "is_locked": True,
            "status": "HALT",
            "reason": "operator emergency stop",
        },
    )

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )
    report = json.loads(Path(result.safety_report_path).read_text(encoding="utf-8"))

    assert result.status == "HALT"
    assert report["overall_decision"] == "EMERGENCY_STOP"
    assert "all_order_submission" in report["blocked_actions"]


def test_phase15ad_buy_sell_review_scope_is_preserved(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    market_path = runtime_root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json"
    market = json.loads(market_path.read_text(encoding="utf-8"))
    market["buy_review_required"] = True
    market["buy_review_reason"] = "new buys require human review"
    market["sell_review_required"] = False
    _write_json(market_path, market)

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )
    report = json.loads(Path(result.safety_report_path).read_text(encoding="utf-8"))

    assert result.status == "REVIEW_REQUIRED"
    assert report["buy_review_required"] == ["BUY_REVIEW_REQUIRED"]
    assert report["sell_review_required"] == []
    assert "new_buy_without_human_review" in report["blocked_actions"]


def test_phase15ad_cli_safety_evaluation_then_safety_refresh_regular_path(tmp_path):
    runtime_root = _runtime_root(tmp_path)

    evaluation_exit = main(
        [
            "--mode",
            "demo",
            "--job",
            "safety_evaluation",
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
            "--safety-reports-root",
            str(tmp_path / "reports"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--evaluation-time",
            _now().isoformat(),
        ]
    )
    evaluation_manifest = _latest_manifest(runtime_root)
    safety_report = Path(evaluation_manifest["safety_report_path"])

    refresh_exit = main(
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
            str(safety_report),
            "--evaluation-time",
            _now().isoformat(),
        ]
    )
    decision = load_runtime_safety_decision(runtime_root=runtime_root, business_date=BUSINESS_DATE, mode="demo")

    assert evaluation_exit == 0
    assert evaluation_manifest["job"] == "safety_evaluation"
    assert evaluation_manifest["safety_evaluation_status"] == "PASS"
    assert safety_report.exists()
    assert refresh_exit == 0
    assert decision.decision == "ALLOW"


def test_phase15ad_runtime_safety_evaluation_has_no_scenario_dry_run_dependency():
    text = Path("src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py").read_text(encoding="utf-8")

    forbidden = [
        "integration_dry_run",
        "PHASE11G_SCENARIOS",
        "build_phase11g_scenarios",
        "_base_monitor_input",
        "_quote(",
        "_order(",
        "_broker_snapshot(",
    ]
    for token in forbidden:
        assert token not in text


def test_phase15ad_phase11_report_can_feed_runtime_safety_decision_producer(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    evaluation = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    produced = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        source_artifact_path=evaluation.safety_report_path,
        now=_now(),
    )

    assert produced.status == "PASS"
    assert produced.decision.safety_policy_version == "phase11_safety_report_v2"
    assert produced.decision.safety_source == evaluation.safety_report_path


def test_phase15ax_fixed_evaluation_time_fresh_broker_snapshot_is_pass(tmp_path):
    runtime_root = _runtime_root(tmp_path, broker_snapshot_at="2026-07-10T08:59:00+00:00")

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert result.status == "PASS"
    assert result.manifest_fields["broker_snapshot_at"] == "2026-07-10T08:59:00+00:00"


def test_phase15ax_fixed_evaluation_time_stale_broker_snapshot_requires_review(tmp_path):
    runtime_root = _runtime_root(tmp_path, broker_snapshot_at="2026-07-10T08:00:00+00:00")

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    report = json.loads(Path(result.safety_report_path).read_text(encoding="utf-8"))
    assert "BROKER_SNAPSHOT_STALE" in {item["reason_code"] for item in report["review_required_items"]}


def test_phase15ax_utc_snapshot_jst_evaluation_age_is_calculated(tmp_path):
    runtime_root = _runtime_root(tmp_path, broker_snapshot_at="2026-07-10T08:59:00+00:00")

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=datetime(2026, 7, 10, 18, 0, tzinfo=timezone(timedelta(hours=9))),
    )

    assert result.status == "PASS"


def test_phase15ax_timezone_missing_snapshot_stops_as_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, broker_snapshot_at="2026-07-10T09:00:00")

    result = run_runtime_safety_evaluation(
        runtime_root=runtime_root,
        reports_root=tmp_path / "reports",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert result.status == "REVIEW_REQUIRED"
    report = json.loads(Path(result.safety_report_path).read_text(encoding="utf-8"))
    assert "BROKER_SNAPSHOT_STALE" in {item["reason_code"] for item in report["review_required_items"]}


def test_phase15ax_same_fixture_same_evaluation_time_repeats_same_result(tmp_path):
    first = run_runtime_safety_evaluation(
        runtime_root=_runtime_root(tmp_path / "first", broker_snapshot_at="2026-07-10T08:59:00+00:00"),
        reports_root=tmp_path / "reports_first",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )
    second = run_runtime_safety_evaluation(
        runtime_root=_runtime_root(tmp_path / "second", broker_snapshot_at="2026-07-10T08:59:00+00:00"),
        reports_root=tmp_path / "reports_second",
        business_date=BUSINESS_DATE,
        mode="demo",
        now=_now(),
    )

    assert first.status == second.status == "PASS"
    assert first.reason == second.reason


def test_phase15ax_production_default_clock_remains_runtime_now():
    text = Path("src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py").read_text(encoding="utf-8")

    assert "now or datetime.now(timezone.utc)" in text


def _runtime_root(tmp_path: Path, *, broker_snapshot_at: str | None = None) -> Path:
    root = tmp_path / ".runtime"
    snapshot_at = broker_snapshot_at or BUSINESS_DATE + "T09:00:00+00:00"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "environment": "demo",
            "source": "runtime_v2_current_projection",
            "positions": [{"symbol": "7203", "quantity": 100, "price": 1000, "market_value": 100000}],
            "cash": 900000,
            "buying_power": 900000,
            "market_value": 100000,
            "total_equity": 1000000,
            "previous_total_equity": 1000000,
            "review_required": False,
        },
    )
    _write_jsonl(root / "persistent_ledger" / "orders.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "executions.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "positions.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "cash.jsonl", [])
    _write_jsonl(root / "persistent_ledger" / "events.jsonl", [])
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_operation_state_v1",
            "role": "authoritative_runtime_operation_state",
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "updated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "environment": "demo",
            "runtime_mode": "demo",
            "state": "CURRENT_STATE_LOADED",
            "safety_state": "NORMAL",
            "current_safety_state": "NORMAL",
            "source": "runtime_v2_runtime_state_producer",
            "asset_state_is_authoritative_here": False,
            "pending_state_is_authoritative_here": False,
        },
    )
    _write_json(
        root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "tachibana_snapshot.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": snapshot_at,
            "snapshot_at": snapshot_at,
            "environment": "demo",
            "broker_mode": "demo",
            "production_equivalent": False,
            "buying_power": 900000,
            "cash_available": 900000,
            "total_equity": 1000000,
            "positions": [{"symbol": "7203", "issue_code": "7203", "quantity": 100, "market_value": 100000}],
            "orders": [],
            "divergence_status": "NONE",
        },
    )
    _write_json(
        root / "runtime_state" / "market" / BUSINESS_DATE / "market_evidence.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "environment": "demo",
            "quotes": {"7203": {"price": 1000, "age_seconds": 0, "stale": False}},
            "candidate_universe_market_summary": {"market_crash": False, "daily_loss_pct": "0"},
            "safety_config": {
                "max_broker_snapshot_age_seconds": 900,
                "max_quote_age_seconds": 300,
            },
        },
    )
    _write_json(
        root / "safety" / "locks" / "manual_emergency_state.json",
        {
            "business_date": BUSINESS_DATE,
            "generated_at": BUSINESS_DATE + "T09:00:00+00:00",
            "is_locked": False,
            "status": "CLEAR",
            "reason": "no manual emergency stop",
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-phase15ad",
            "state": "CONSUMED",
            "environment": "demo",
            "items": [],
        },
    )
    return root


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
