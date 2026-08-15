import json
import subprocess
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalExecutionSnapshotProvider
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _write_execution_manifest_evidence
from scripts.runtime_test import collect_runtime_cli_job_evidence
from tests.runtime_v2.test_phase17_g_historical_submit_guard_and_fill import (
    BUSINESS_DATE as HISTORICAL_ORDER_DATE,
)
from tests.runtime_v2.test_phase17_g_historical_submit_guard_and_fill import (
    _historical_context,
    _runtime_fixture,
)


BUSINESS_DATE = "2026-07-07"


def test_phase17_bg_empty_no_action_execution_is_terminal_pass_without_writes(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_payload = _empty_pending_payload(BUSINESS_DATE)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending_payload)
    _write_submit_manifest(runtime_root, business_date=BUSINESS_DATE)
    before = _ledger_contents(runtime_root)

    def fail_if_called(**_kwargs):
        raise AssertionError("NO_ACTION execution must not request Broker ReadOnly snapshot")

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=fail_if_called,
    )

    assert result.status == "PASS"
    assert result.reason == "no_submitted_orders"
    assert result.execution_action == "NO_ACTION"
    assert result.orderlist_required is False
    assert result.orderlist_status == "NOT_REQUIRED"
    assert result.submitted_order_count == 0
    assert result.execution_equivalent_count == 0
    assert result.fill_count == 0
    assert result.ledger_orders_appended == 0
    assert result.ledger_executions_appended == 0
    assert result.ledger_positions_appended == 0
    assert result.ledger_cash_appended == 0
    assert result.current_apply_status == "NOT_REQUIRED"
    assert result.runtime_owned_projection_status == "NOT_REQUIRED"
    assert result.reconcile_status == "NOT_REQUIRED"
    assert result.pending_terminalization_status == "ALREADY_TERMINAL"
    assert result.pending_consumed is False
    assert result.pending_mutated is False
    assert result.submit_action == "NO_ACTION"
    assert result.submit_authority_status == "PASS"
    assert _ledger_contents(runtime_root) == before
    assert json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text()) == pending_payload


def test_phase29_l21t_ba_authorized_no_order_submit_continues_through_execution(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_payload = _empty_pending_payload(BUSINESS_DATE)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending_payload)
    _write_authorized_no_order_submit_manifest(runtime_root, business_date=BUSINESS_DATE)
    before = _ledger_contents(runtime_root)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("authorized no-order needs no snapshot")),
    )

    assert result.status == "PASS"
    assert result.reason == "no_submitted_orders"
    assert result.execution_action == "NO_ACTION"
    assert result.orderlist_required is False
    assert result.submitted_order_count == 0
    assert result.fill_count == 0
    assert result.ledger_orders_appended == 0
    assert result.ledger_executions_appended == 0
    assert result.ledger_positions_appended == 0
    assert result.ledger_cash_appended == 0
    assert result.current_apply_status == "NOT_REQUIRED"
    assert result.runtime_owned_projection_status == "NOT_REQUIRED"
    assert result.pending_terminalization_status == "ALREADY_TERMINAL"
    assert result.pending_consumed is False
    assert result.pending_mutated is False
    assert result.submit_action == "NO_SUBMISSION_REQUIRED"
    assert result.submit_authority_status == "PASS"
    assert _ledger_contents(runtime_root) == before
    assert json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text()) == pending_payload


def test_phase29_l21t_ba_buy_wait_zero_order_day_uses_authorized_no_order_without_pending(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    pending_payload = _empty_pending_payload(BUSINESS_DATE)
    pending_payload["no_action_reason"] = "BUY_WAIT:TEMPORARY_BUY_INELIGIBLE"
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending_payload)
    _write_authorized_no_order_submit_manifest(
        runtime_root,
        business_date=BUSINESS_DATE,
        no_action_reason="BUY_WAIT:TEMPORARY_BUY_INELIGIBLE",
    )

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("BUY_WAIT no-order needs no snapshot")),
    )

    assert result.status == "PASS"
    assert result.execution_action == "NO_ACTION"
    assert result.submit_action == "NO_SUBMISSION_REQUIRED"
    assert result.pending_item_count == 0
    assert result.pending_consumed is False
    assert result.pending_mutated is False
    assert result.ledger_orders_appended == 0
    assert result.current_apply_status == "NOT_REQUIRED"


def test_phase17_bg_empty_pending_without_submit_no_action_authority_is_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", _empty_pending_payload(BUSINESS_DATE))

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("snapshot not required before authority")),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "submit NO_ACTION authority missing"
    assert result.orderlist_required is True
    assert result.orderlist_status == "NOT_EVALUATED"


def test_phase29_l21t_ba_malformed_authorized_no_order_authority_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", _empty_pending_payload(BUSINESS_DATE))
    _write_authorized_no_order_submit_manifest(
        runtime_root,
        business_date=BUSINESS_DATE,
        authority_type="MALFORMED_AUTHORITY",
    )

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("snapshot not required before authority")),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "submit NO_ACTION authority inconsistent"
    assert result.orderlist_required is True


def test_phase29_l21t_ba_pending_item_with_no_submission_required_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    payload = _empty_pending_payload(BUSINESS_DATE)
    payload["items"] = [{"pending_item_id": "unexpected"}]
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", payload)
    _write_authorized_no_order_submit_manifest(runtime_root, business_date=BUSINESS_DATE, pending_item_count=1)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("snapshot not required for invalid EMPTY")),
    )

    assert result.status == "BLOCKED"
    assert result.reason == "pending EMPTY classification requires empty items"


def test_phase29_l21t_ba_submitted_order_with_no_action_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", _empty_pending_payload(BUSINESS_DATE))
    _write_authorized_no_order_submit_manifest(runtime_root, business_date=BUSINESS_DATE, submitted_count=1)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("snapshot not required before authority")),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "submit NO_ACTION authority inconsistent"
    assert result.orderlist_required is True


def test_phase17_bg_empty_pending_target_date_metadata_is_not_order_authority(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    payload = _empty_pending_payload(BUSINESS_DATE)
    payload["target_session_date"] = "2026-07-08"
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", payload)
    _write_submit_manifest(runtime_root, business_date=BUSINESS_DATE)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("snapshot not required for invalid EMPTY")),
    )

    assert result.status == "PASS"
    assert result.reason == "no_submitted_orders"
    assert result.execution_action == "NO_ACTION"
    assert result.orderlist_required is False


def test_phase17_bg_empty_pending_with_items_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    payload = _empty_pending_payload(BUSINESS_DATE)
    payload["items"] = [{"pending_item_id": "unexpected"}]
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", payload)
    _write_submit_manifest(runtime_root, business_date=BUSINESS_DATE)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=lambda **_: (_ for _ in ()).throw(AssertionError("snapshot not required for invalid EMPTY")),
    )

    assert result.status == "BLOCKED"
    assert result.reason == "pending EMPTY classification requires empty items"


def test_phase17_bg_active_pending_with_missing_orderlist_stays_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", _approved_pending_payload(BUSINESS_DATE))

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=_empty_orderlist_snapshot,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "orderlist evidence missing"
    assert result.orderlist_required is True
    assert result.orderlist_status == "MISSING"


def test_phase17_bg_real_order_with_missing_orderlist_stays_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    _write_json(runtime_root / "pending_order_plan" / "pending_order_plan.json", _consumed_pending_payload(BUSINESS_DATE))

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        snapshot_provider=_empty_orderlist_snapshot,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "orderlist evidence missing"
    assert result.orderlist_required is True
    assert result.orderlist_status == "MISSING"


def test_phase17_bg_real_order_execution_path_still_passes(tmp_path):
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY")
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=HISTORICAL_ORDER_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )
    provider = HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=HISTORICAL_ORDER_DATE)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=HISTORICAL_ORDER_DATE,
        mode="historical",
        snapshot_provider=provider,
    )

    assert submit.status == "PASS"
    assert result.status == "PASS"
    assert result.execution_action == "EXECUTE"
    assert result.orderlist_required is True
    assert result.orderlist_status == "READY"
    assert result.submitted_order_count == 1
    assert result.ledger_orders_appended == 1
    assert result.ledger_executions_appended >= 1


def test_phase29_l20b_quarantine_only_buy_execution_is_no_action_without_orderlist(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    business_date = HISTORICAL_ORDER_DATE
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        _approved_pending_payload(business_date, symbol="76920", side="BUY", quantity=2000),
    )
    _write_quarantine_submit_authority(
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports" / "runtime_tests" / "runs" / "run-l20b-buy",
        business_date=business_date,
        symbol="76920",
        side="BUY",
        quantity=2000,
    )
    before = _ledger_contents(runtime_root)

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="historical",
        snapshot_provider=HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=business_date),
    )

    assert result.status == "PASS"
    assert result.reason == "no_submitted_orders"
    assert result.execution_action == "NO_ACTION"
    assert result.orderlist_required is False
    assert result.submitted_order_count == 0
    assert result.fill_count == 0
    assert result.ledger_orders_appended == 0
    assert result.ledger_executions_appended == 0
    assert result.current_apply_status == "NOT_REQUIRED"
    assert result.submit_authority_status == "PASS"
    assert result.submit_authority_reason == "historical_corporate_action_quarantine_no_submitted_orders"
    assert _ledger_contents(runtime_root) == before


def test_phase29_l20b_quarantine_only_sell_execution_is_no_action_without_orderlist(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    business_date = HISTORICAL_ORDER_DATE
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        _approved_pending_payload(business_date, symbol="76920", side="SELL", quantity=700),
    )
    _write_quarantine_submit_authority(
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports" / "runtime_tests" / "runs" / "run-l20b-sell",
        business_date=business_date,
        symbol="76920",
        side="SELL",
        quantity=700,
    )

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="historical",
        snapshot_provider=HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=business_date),
    )

    assert result.status == "PASS"
    assert result.execution_action == "NO_ACTION"
    assert result.orderlist_required is False
    assert result.fill_count == 0
    assert result.pending_terminalization_status == "PENDING_LIFECYCLE_REQUIRED"
    assert result.submit_authority_reason == "historical_corporate_action_quarantine_no_submitted_orders"


def test_phase29_l20b_mixed_quarantine_and_submitted_order_still_requires_orderlist(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    business_date = HISTORICAL_ORDER_DATE
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        _approved_pending_payload(business_date, symbol="76920", side="BUY", quantity=2000),
    )
    _write_quarantine_submit_authority(
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports" / "runtime_tests" / "runs" / "run-l20b-mixed",
        business_date=business_date,
        symbol="76920",
        side="BUY",
        quantity=2000,
        submitted_count=1,
        pass_item=True,
    )

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="historical",
        snapshot_provider=HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=business_date),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "orderlist evidence missing"
    assert result.execution_action == "EXECUTE"
    assert result.orderlist_required is True


def test_phase29_l20h_mixed_quarantine_and_filled_order_requires_pending_lifecycle(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    business_date = HISTORICAL_ORDER_DATE
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        _mixed_pending_payload(business_date),
    )
    _write_quarantine_submit_authority(
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports" / "runtime_tests" / "runs" / "run-l20h-mixed",
        business_date=business_date,
        symbol="76920",
        side="BUY",
        quantity=1400,
        submitted_count=1,
        pass_item=True,
    )

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="historical",
        snapshot_provider=_MixedHistoricalSnapshotProvider(runtime_root=runtime_root, business_date=business_date),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == (
        "runtime owned current projection failed before transaction commit: "
        "runtime owned accepted submit evidence missing"
    )
    assert result.execution_action == "EXECUTE"
    assert result.orderlist_required is True
    assert result.submitted_order_count == 1
    assert result.ledger_orders_appended == 0
    assert result.ledger_executions_appended == 0
    assert result.pending_terminalization_status == "NOT_EXECUTED"
    assert result.transaction_consistency_status == "NOT_EXECUTED"


def test_phase29_l20b_generic_review_required_does_not_become_no_action(tmp_path):
    runtime_root = _runtime_root(tmp_path)
    business_date = HISTORICAL_ORDER_DATE
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        _approved_pending_payload(business_date, symbol="76920", side="BUY", quantity=2000),
    )
    _write_quarantine_submit_authority(
        runtime_root=runtime_root,
        evidence_root=tmp_path / "reports" / "runtime_tests" / "runs" / "run-l20b-generic",
        business_date=business_date,
        symbol="76920",
        side="BUY",
        quantity=2000,
        guard_reason="aggregate_submit_feasibility_failed",
        violated_policy="submit_guard_canonical_evidence_revalidation",
    )

    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=business_date,
        mode="historical",
        snapshot_provider=HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=business_date),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "orderlist evidence missing"
    assert result.execution_action == "EXECUTE"
    assert result.orderlist_required is True


def test_phase17_bg_runtime_test_collects_execution_evidence_for_nonzero_and_zero(tmp_path):
    runtime_root = tmp_path / ".runtime"
    run_dir = tmp_path / "reports" / "runtime_tests" / "runs" / "run-bg"
    for code in (20, 0):
        manifest_path = (
            runtime_root
            / "runtime_state"
            / "run_manifest"
            / BUSINESS_DATE
            / f"runtime-v2-execution-bg-{code}.json"
        )
        log_path = runtime_root / "runtime_state" / "logs" / BUSINESS_DATE / f"runtime-v2-execution-bg-{code}.log"
        _write_json(manifest_path, {"run_id": f"runtime-v2-execution-bg-{code}", "job": "execution", "exit_code": code})
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"exit_code={code}\n", encoding="utf-8")
        completed = subprocess.CompletedProcess(
            args=["runtime"],
            returncode=code,
            stdout=json.dumps({"exit_code": code, "manifest": str(manifest_path)}) + "\n",
            stderr="",
        )

        collect_runtime_cli_job_evidence(
            completed=completed,
            run_dir=run_dir / f"case-{code}",
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            job="execution",
        )

        job_dir = run_dir / f"case-{code}" / "daily" / BUSINESS_DATE / "execution"
        result = json.loads((job_dir / "cli_result.json").read_text(encoding="utf-8"))
        assert result["exit_code"] == code
        assert result["runtime_manifest_copied"] is True
        assert result["runtime_log_copied"] is True
        assert (job_dir / "runtime_manifest.json").is_file()
        assert (job_dir / "runtime_log.log").is_file()


def test_phase17_bg_execution_run_scoped_evidence_marks_no_action_not_required(tmp_path):
    evidence_root = tmp_path / "run"
    manifest_path = tmp_path / "runtime-v2-execution.json"
    manifest = {
        "business_date": BUSINESS_DATE,
        "mode": "demo",
        "runtime_test_run_id": "runtime-test-bg",
        "runtime_test_profile_id": "historical-smoke",
        "warnings": [],
        "errors": [],
        "prohibited_actions": {
            "demo_submit_executed": False,
            "production_order_executed": False,
            "notification_sent": False,
            "phase9_runtime_called": False,
            "phase9_writer_called": False,
            "mode_rooted_current_used": False,
        },
        "stages": [
            {
                "name": "environment_composition",
                "status": "PASS",
                "details": {"broker_write": False, "external_delivery": False},
            },
            {
                "name": "runtime_v2_execution_readonly_pipeline",
                "status": "PASS",
                "details": {
                    "execution_acceptance_status": "PASS",
                    "execution_acceptance_reason": "no_submitted_orders",
                    "execution_action": "NO_ACTION",
                    "orderlist_required": False,
                    "orderlist_status": "NOT_REQUIRED",
                    "orders_count": 0,
                    "submitted_order_count": 0,
                    "executions_count": 0,
                    "fill_count": 0,
                    "ledger_connected": True,
                    "ledger_orders_appended": 0,
                    "ledger_executions_appended": 0,
                    "ledger_positions_appended": 0,
                    "ledger_cash_appended": 0,
                    "ledger_events_appended": 0,
                    "current_apply_status": "NOT_REQUIRED",
                    "runtime_owned_projection_status": "NOT_REQUIRED",
                    "pending_terminalization_status": "ALREADY_TERMINAL",
                    "pending_consumed": False,
                    "pending_mutated": False,
                    "pending_read_valid": True,
                    "pending_classification": "EMPTY",
                    "pending_active": False,
                    "pending_plan_present": False,
                    "pending_item_count": 0,
                    "no_action_reason": "NO_SIGNAL:phase17_bg_fixture",
                    "submit_action": "NO_ACTION",
                    "submit_authority_status": "PASS",
                },
            },
        ],
    }

    _write_execution_manifest_evidence(
        evidence_root=evidence_root,
        business_date=BUSINESS_DATE,
        manifest_path=manifest_path,
        manifest=manifest,
    )

    execution_dir = evidence_root / "daily" / BUSINESS_DATE / "execution"
    submitted = json.loads((execution_dir / "submitted_order_authority.json").read_text(encoding="utf-8"))
    fill = json.loads((execution_dir / "historical_fill_authority.json").read_text(encoding="utf-8"))
    pending = json.loads((execution_dir / "pending_terminalization_evidence.json").read_text(encoding="utf-8"))
    current = json.loads((execution_dir / "current_apply_evidence.json").read_text(encoding="utf-8"))
    assert submitted["orderlist_required"] is False
    assert submitted["orderlist_status"] == "NOT_REQUIRED"
    assert submitted["execution_action"] == "NO_ACTION"
    assert fill["fill_count"] == 0
    assert fill["orderlist_status"] == "NOT_REQUIRED"
    assert pending["status"] == "ALREADY_TERMINAL"
    assert pending["pending_consumed"] is False
    assert pending["pending_mutated"] is False
    assert current["status"] == "NOT_REQUIRED"


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_json(
        ledger / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-bg",
            "environment": "demo",
            "source": "fixture",
            "as_of": BUSINESS_DATE,
            "positions": [],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 0,
            "total_equity": 1_000_000,
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "generated_from": [],
            "created_at": BUSINESS_DATE,
        },
    )
    return root


def _empty_pending_payload(business_date: str) -> dict:
    return {
        "schema_version": "1",
        "pending_plan_id": f"pending-empty-{business_date}",
        "state": "EMPTY",
        "status": "EMPTY",
        "environment": "demo",
        "created_at": business_date,
        "updated_at": business_date,
        "plan_created_date": business_date,
        "intended_submit_date": business_date,
        "target_session_date": business_date,
        "source_order_plan": {"order_plan_id": "order-empty", "path": "x", "artifact_hash": "sha256:x"},
        "approval": None,
        "approved_item_ids": [],
        "items": [],
        "submit_constraints": {"expires_at": "", "allow_post_send_unknown_resubmit": False},
        "consume": {"consumed": False, "submitted_order_ids": [], "ledger_order_record_ids": []},
        "active_pending": False,
        "no_action_reason": "NO_SIGNAL:phase17_bg_fixture",
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _approved_pending_payload(
    business_date: str,
    *,
    symbol: str = "7203",
    side: str = "BUY",
    quantity: int = 100,
) -> dict:
    payload = _empty_pending_payload(business_date)
    payload.update(
        {
            "pending_plan_id": f"pending-active-{business_date}",
            "state": "APPROVED",
            "status": "APPROVED",
            "active_pending": True,
            "approval": {
                "approval_path": "approval.json",
                "approval_hash": "sha256:approval",
                "approval_status": "APPROVED",
                "approved_item_ids": ["item-1"],
                "approval_expires_at": business_date + "T15:00:00+09:00",
            },
            "approved_item_ids": ["item-1"],
            "items": [
                {
                    "pending_item_id": "item-1",
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "order_type": "MARKET",
                    "estimated_price": 1000,
                    "estimated_amount": quantity * 1000,
                    "approved": True,
                    "state": "APPROVED",
                }
            ],
        }
    )
    payload.pop("no_action_reason", None)
    return payload


def _mixed_pending_payload(business_date: str) -> dict:
    payload = _approved_pending_payload(business_date, symbol="76920", side="BUY", quantity=1400)
    payload["state"] = "REVIEW_REQUIRED"
    payload["status"] = "REVIEW_REQUIRED"
    payload["approved_item_ids"] = ["item-1", "item-pass"]
    payload["approval"]["approved_item_ids"] = ["item-1", "item-pass"]
    payload["items"] = [
        {
            "pending_item_id": "item-1",
            "symbol": "76920",
            "side": "BUY",
            "quantity": 1400,
            "order_type": "MARKET",
            "estimated_price": 100,
            "estimated_amount": 140000,
            "approved": True,
            "state": "APPROVED",
        },
        {
            "pending_item_id": "item-pass",
            "symbol": "7203",
            "side": "BUY",
            "quantity": 100,
            "order_type": "MARKET",
            "estimated_price": 1000,
            "estimated_amount": 100000,
            "approved": True,
            "state": "APPROVED",
        },
    ]
    return payload


def _write_quarantine_submit_authority(
    *,
    runtime_root: Path,
    evidence_root: Path,
    business_date: str,
    symbol: str,
    side: str,
    quantity: int,
    submitted_count: int = 0,
    pass_item: bool = False,
    guard_reason: str = "corporate_action_event_not_resolved",
    violated_policy: str = "historical_corporate_action_symbol_quarantine",
) -> None:
    manifest_path = runtime_root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-submit-l20b.json"
    guard_items = []
    if pass_item:
        guard_items.append(
            {
                "pending_item_id": "item-pass",
                "symbol": "7203",
                "side": "BUY",
                "quantity": 100,
                "submit_item_status": "PASS",
                "guard_decision": "PASS",
                "guard_reason": "approved_by_submit_guard_policy",
            }
        )
    guard_items.append(
        {
            "pending_item_id": "item-1",
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "submit_item_status": "REVIEW_REQUIRED",
            "guard_decision": "BLOCKED",
            "guard_reason": guard_reason,
            "blocked_at_submit_reason": guard_reason,
            "violated_policy": violated_policy,
            "corporate_action_event_status": "IMPACT_DETECTED",
            "corporate_action_adjustment_authority_status": "REVIEW_REQUIRED",
            "corporate_action_adjustment_authority_reason": "corporate_action_event_not_resolved",
            "corporate_action_split_inference_used": False,
            "corporate_action_quantity_adjustment_performed": False,
        }
    )
    blocked_count = 1
    pending_item_count = len(guard_items)
    _write_json(
        manifest_path,
        {
            "run_id": "runtime-v2-submit-l20b",
            "job": "submit",
            "business_date": business_date,
            "run_type": "HISTORICAL",
            "runtime_mode": "historical",
            "broker_environment": "historical_simulated",
            "historical_replay": True,
            "runtime_test_run_id": evidence_root.name,
            "runtime_test_evidence_root": str(evidence_root),
            "exit_code": 20,
            "final_state": "REVIEW_REQUIRED",
            "pending_read_valid": True,
            "pending_classification": "VALID",
            "pending_active": True,
            "pending_plan_present": True,
            "pending_item_count": pending_item_count,
            "submit_action": "SUBMIT" if submitted_count else "NO_SUBMIT_ATTEMPTED",
            "submitted_count": submitted_count,
            "blocked_count": blocked_count,
            "review_required": True,
            "halt_required": False,
            "broker_write": False,
            "external_delivery": False,
            "prohibited_actions": {
                "demo_submit_executed": False,
                "production_order_executed": False,
                "broker_write": False,
                "external_delivery": False,
            },
            "stages": [
                {
                    "name": "environment_composition",
                    "status": "PASS",
                    "details": {
                        "run_type": "HISTORICAL",
                        "broker_environment": "historical_simulated",
                        "historical_replay": True,
                        "broker_write": False,
                        "external_delivery": False,
                    },
                }
            ],
            "submit_guard_item_evidence": guard_items,
        },
    )
    continuation_path = evidence_root / "daily" / business_date / "submit" / "corporate_action_symbol_quarantine_continuation.json"
    _write_json(
        continuation_path,
        {
            "schema_version": "runtime_test_historical_corporate_action_symbol_quarantine_continuation_v1",
            "status": "COMPLETED_WITH_SYMBOL_QUARANTINE",
            "scope": "CORPORATE_ACTION_SYMBOL_ONLY",
            "business_date": business_date,
            "job": "submit",
            "runtime_cli_exit_code": 20,
            "runtime_manifest_path": str(evidence_root / "daily" / business_date / "submit" / "runtime_manifest.json"),
            "checks": {
                "runtime_cli_nonzero": True,
                "submit_job": True,
                "historical_replay": True,
                "broker_environment_historical_simulated": True,
                "no_actual_broker_write": True,
                "runtime_submit_review_required": True,
                "blocked_item_count_positive": True,
                "pending_count_matches_guard_evidence": True,
                "submitted_count_matches_pass_items": submitted_count == int(pass_item),
                "blocked_count_matches_ca_items": guard_reason == "corporate_action_event_not_resolved",
                "other_item_results_independently_inspectable": True,
                "has_eligible_corporate_action_item": True,
                "generic_review_required_not_continued": guard_reason == "corporate_action_event_not_resolved",
            },
            "affected_symbols": [symbol],
            "quarantined_symbols": [symbol],
            "corporate_action_quarantine_status": "QUARANTINED",
            "corporate_action_quarantine_scope": "SYMBOL_ONLY",
            "corporate_action_run_continuation_eligibility": "ALLOWED_FOR_HISTORICAL_REPLAY_ONLY",
            "production_applicability": "NEVER",
            "reason": "historical_symbol_scoped_corporate_action_quarantine_continuation",
        },
    )


def _consumed_pending_payload(business_date: str) -> dict:
    payload = _approved_pending_payload(business_date)
    payload["state"] = "CONSUMED"
    payload["status"] = "CONSUMED"
    payload["active_pending"] = False
    payload["consume"] = {
        "consumed": True,
        "consume_reason": "submitted",
        "submitted_order_ids": ["sha256:order-bg"],
        "ledger_order_record_ids": ["ledger-order-bg"],
    }
    return payload


def _write_submit_manifest(runtime_root: Path, *, business_date: str) -> None:
    _write_json(
        runtime_root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-submit-bg.json",
        {
            "run_id": "runtime-v2-submit-bg",
            "job": "submit",
            "business_date": business_date,
            "exit_code": 0,
            "final_state": "CURRENT_STATE_LOADED",
            "pending_read_valid": True,
            "pending_classification": "EMPTY",
            "pending_active": False,
            "pending_plan_present": False,
            "pending_item_count": 0,
            "no_action_reason": "NO_SIGNAL:phase17_bg_fixture",
            "submit_action": "NO_ACTION",
            "submitted_count": 0,
            "blocked_count": 0,
            "review_required": False,
            "halt_required": False,
            "prohibited_actions": {"demo_submit_executed": False, "production_order_executed": False},
        },
    )


def _write_authorized_no_order_submit_manifest(
    runtime_root: Path,
    *,
    business_date: str,
    authority_type: str = "AUTHORIZED_NO_ORDER",
    pending_item_count: int = 0,
    submitted_count: int = 0,
    no_action_reason: str = "NO_SIGNAL:phase29_l21t_ba_fixture",
) -> None:
    _write_json(
        runtime_root / "runtime_state" / "run_manifest" / business_date / "runtime-v2-submit-ba.json",
        {
            "run_id": "runtime-v2-submit-ba",
            "job": "submit",
            "business_date": business_date,
            "exit_code": 0,
            "final_state": "CURRENT_STATE_LOADED",
            "pending_read_valid": True,
            "pending_classification": "VALID",
            "pending_active": False,
            "pending_plan_present": True,
            "pending_item_count": pending_item_count,
            "no_action_reason": no_action_reason,
            "no_order_authority_status": "PASS",
            "no_order_authority_evidence": {
                "status": "PASS",
                "authority_type": authority_type,
                "approval_status": "NO_ORDER_AUTHORIZED",
                "order_plan_status": "NO_ORDER_AUTHORIZED",
                "planning_consumer_eligibility": "NO_ORDER_AUTHORIZED",
                "pending_state": "EMPTY",
                "pending_item_count": pending_item_count,
                "pending_approved_item_count": 0,
                "runtime_planning_status": "PASS",
                "runtime_planning_quantity_unresolved_count": 0,
                "runtime_planning_review_required_quantity_count": 0,
            },
            "submit_action": "NO_SUBMISSION_REQUIRED",
            "submitted_count": submitted_count,
            "blocked_count": 0,
            "review_required": False,
            "halt_required": False,
            "prohibited_actions": {"demo_submit_executed": False, "production_order_executed": False},
        },
    )


def _empty_orderlist_snapshot(**kwargs):
    snapshot_path = Path(kwargs["snapshot_path"])
    _write_json(
        snapshot_path,
        {
            "generated_at": BUSINESS_DATE + "T15:30:00+09:00",
            "orders": [],
            "executions": [],
            "positions": [],
            "buying_power": {"cash_available": "1000000", "buying_power": "1000000", "currency": "JPY"},
        },
    )
    _write_json(Path(kwargs["report_path"]), {"status": "PASS"})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _filled_order_snapshot(**kwargs):
    snapshot_path = Path(kwargs["snapshot_path"])
    _write_json(
        snapshot_path,
        {
            "generated_at": BUSINESS_DATE + "T15:30:00+09:00",
            "orders": [
                {
                    "order_id_hash": "sha256:order-bg",
                    "issue_code": "7203",
                    "side": "buy",
                    "quantity": "100",
                    "executed_quantity": "100",
                    "remaining_quantity": "0",
                    "status": "全部約定",
                    "as_of": BUSINESS_DATE + "T15:30:00+09:00",
                }
            ],
            "executions": [],
            "positions": [{"issue_code": "7203", "quantity": "100", "average_price": "1000", "market_value": "100000"}],
            "buying_power": {"cash_available": "900000", "buying_power": "900000", "currency": "JPY"},
        },
    )
    _write_json(Path(kwargs["report_path"]), {"status": "PASS"})
    return type("SnapshotResult", (), {"status": "PASS"})()


class _MixedHistoricalSnapshotProvider(HistoricalExecutionSnapshotProvider):
    def __call__(self, *, mode: str, snapshot_path, report_path):
        return _mixed_filled_order_snapshot(snapshot_path=snapshot_path, report_path=report_path)


def _mixed_filled_order_snapshot(**kwargs):
    snapshot_path = Path(kwargs["snapshot_path"])
    _write_json(
        snapshot_path,
        {
            "generated_at": HISTORICAL_ORDER_DATE + "T15:30:00+09:00",
            "orders": [
                {
                    "order_id_hash": "sha256:order-l20h",
                    "pending_item_id": "item-pass",
                    "pending_plan_id": f"pending-active-{HISTORICAL_ORDER_DATE}",
                    "issue_code": "7203",
                    "side": "buy",
                    "quantity": "100",
                    "executed_quantity": "100",
                    "remaining_quantity": "0",
                    "status": "全部約定",
                    "as_of": HISTORICAL_ORDER_DATE + "T15:30:00+09:00",
                }
            ],
            "executions": [],
            "positions": [{"issue_code": "7203", "quantity": "100", "average_price": "1000", "market_value": "100000"}],
            "buying_power": {"cash_available": "900000", "buying_power": "900000", "currency": "JPY"},
        },
    )
    _write_json(Path(kwargs["report_path"]), {"status": "PASS"})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _ledger_contents(runtime_root: Path) -> dict[str, str]:
    ledger = runtime_root / "persistent_ledger"
    return {name: (ledger / f"{name}.jsonl").read_text(encoding="utf-8") for name in ("orders", "executions", "positions", "cash", "events")}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
