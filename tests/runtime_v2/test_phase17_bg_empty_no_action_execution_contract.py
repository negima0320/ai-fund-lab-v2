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


def test_phase17_bg_empty_pending_target_date_mismatch_fails_closed(tmp_path):
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

    assert result.status == "BLOCKED"
    assert result.reason == "pending EMPTY classification target_session_date mismatch"


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


def _approved_pending_payload(business_date: str) -> dict:
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
                    "symbol": "7203",
                    "side": "BUY",
                    "quantity": 100,
                    "order_type": "MARKET",
                    "estimated_price": 1000,
                    "estimated_amount": 100000,
                    "approved": True,
                    "state": "APPROVED",
                }
            ],
        }
    )
    payload.pop("no_action_reason", None)
    return payload


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


def _ledger_contents(runtime_root: Path) -> dict[str, str]:
    ledger = runtime_root / "persistent_ledger"
    return {name: (ledger / f"{name}.jsonl").read_text(encoding="utf-8") for name in ("orders", "executions", "positions", "cash", "events")}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
