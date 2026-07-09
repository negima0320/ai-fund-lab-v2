import json
from dataclasses import replace
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.asset.capability_policy import (
    apply_broker_cash_policy,
    decide_asset_reflection_from_broker_evidence,
    should_auto_replace_positions_from_broker,
)
from ai_fund_lab_v2.runtime_v2.asset.initializer import initialize_demo_operation_current_sot
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import generate_public_report_from_current
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from tests.runtime_v2.pending_fixtures import make_approved_pending_plan


def test_mode_demo_capability_is_auto_resolved_without_config_file():
    capability = get_broker_capability("demo")

    assert capability.supports_daily_reset is True
    assert capability.cash_as_truth is False
    assert capability.buying_power_as_truth is False
    assert capability.positions_as_truth is False
    assert capability.executions_as_truth is True
    assert capability.order_status_as_truth is True
    assert capability.supports_9000_series_orders is False
    assert capability.default_evaluation_capital == 1_000_000
    assert capability.broker_cash_is_evidence_only is True
    assert capability.broker_positions_are_evidence_only_after_reset is True


def test_mode_production_capability_is_auto_resolved():
    capability = get_broker_capability("production")

    assert capability.supports_daily_reset is False
    assert capability.cash_as_truth is True
    assert capability.buying_power_as_truth is True
    assert capability.positions_as_truth is True
    assert capability.executions_as_truth is True
    assert capability.order_status_as_truth is True
    assert capability.supports_9000_series_orders is True
    assert capability.default_evaluation_capital is None
    assert capability.broker_cash_is_evidence_only is False
    assert capability.broker_positions_are_evidence_only_after_reset is False


def test_unknown_mode_fails_closed():
    with pytest.raises(ValueError, match="unsupported broker capability mode"):
        get_broker_capability("paper")


def test_demo_broker_cash_does_not_replace_runtime_evaluation_cash():
    capability = get_broker_capability("demo")

    cash, buying_power = apply_broker_cash_policy(
        capability=capability,
        runtime_cash=1_000_000,
        runtime_buying_power=1_000_000,
        broker_cash=20_000_000,
        broker_buying_power=20_000_000,
    )

    assert cash == 1_000_000
    assert buying_power == 1_000_000


def test_demo_broker_daily_reset_positions_do_not_auto_delete_runtime_positions():
    capability = get_broker_capability("demo")

    decision = decide_asset_reflection_from_broker_evidence(
        capability=capability,
        runtime_cash=1_000_000,
        runtime_buying_power=1_000_000,
        runtime_positions=({"symbol": "7203", "quantity": 100},),
        broker_cash=20_000_000,
        broker_buying_power=20_000_000,
        broker_positions=(),
        business_date="2026-07-07",
    )

    assert decision.use_broker_cash is False
    assert decision.use_broker_buying_power is False
    assert decision.use_broker_positions is False
    assert decision.review_required is True
    assert decision.event is not None
    assert decision.event.event_type == "DEMO_BROKER_DAILY_RESET_DETECTED"
    assert should_auto_replace_positions_from_broker(
        capability=capability,
        runtime_positions=({"symbol": "7203", "quantity": 100},),
        broker_positions=(),
    ) is False


def test_demo_capability_blocks_9000_series_submit_candidate():
    plan = make_approved_pending_plan()
    item = replace(plan.items[0], symbol="9432")
    plan = replace(plan, items=(item,))

    result = run_submit_preflight(
        pending_plan=plan,
        approval_artifact=_approval_for(plan),
        approved_item_id=item.pending_item_id,
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
    )

    assert result.blocked is True
    assert result.reason == "symbol not supported by broker capability"


def test_production_capability_marks_cash_and_positions_as_truth():
    capability = get_broker_capability("production")

    assert should_auto_replace_positions_from_broker(
        capability=capability,
        runtime_positions=(),
        broker_positions=({"symbol": "7203", "quantity": 100},),
    ) is True
    cash, buying_power = apply_broker_cash_policy(
        capability=capability,
        runtime_cash=1_000_000,
        runtime_buying_power=1_000_000,
        broker_cash=20_000_000,
        broker_buying_power=19_500_000,
    )
    assert cash == 20_000_000
    assert buying_power == 19_500_000


def test_demo_operation_current_initializer_backs_up_and_writes_fixed_current(tmp_path):
    runtime_root = tmp_path / ".runtime"
    state_path = runtime_root / "persistent_ledger" / "state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "asset_state_id": "polluted",
                "environment": "demo",
                "updated_at": "2026-07-07",
                "positions": [{"symbol": "9001", "quantity": 100}],
                "cash": 19999648,
                "buying_power": 19999648,
                "source": "phase14d15_orderlist_position_cash_reflection",
                "review_required": False,
            }
        ),
        encoding="utf-8",
    )

    result = initialize_demo_operation_current_sot(
        runtime_root=runtime_root,
        business_date="2026-07-07",
        backup_root=runtime_root / "backups" / "phase14e8",
    )

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert Path(result["backup_dir"], "state.json").exists()
    assert payload["cash"] == 1_000_000
    assert payload["buying_power"] == 1_000_000
    assert payload["market_value"] == 0
    assert payload["total_equity"] == 1_000_000
    assert payload["positions"] == []
    assert payload["environment"] == "demo"
    assert payload["source"] == "phase14e8_demo_operation_initial_state"
    assert payload["review_required"] is False
    assert payload["production_equivalent"] is False
    assert "phase14d15" not in json.dumps(payload)


def test_public_report_shows_demo_operation_one_million_and_zero_positions(tmp_path):
    runtime_root = tmp_path / ".runtime"
    initialize_demo_operation_current_sot(
        runtime_root=runtime_root,
        business_date="2026-07-07",
        backup_root=runtime_root / "backups" / "phase14e8",
    )
    _write_runtime_state(runtime_root)
    _write_pending(runtime_root)

    result = generate_public_report_from_current(
        runtime_root=runtime_root,
        runtime_output_dir=tmp_path / "reports" / "runtime_v2" / "2026-07-07",
        public_output_dir=tmp_path / "reports" / "public" / "runtime_v2" / "2026-07-07",
        business_date="2026-07-07",
    )

    public_report = Path(result["public_report_md"]).read_text(encoding="utf-8")
    assert "Cash: JPY 1,000,000" in public_report
    assert "Buying power: JPY 1,000,000" in public_report
    assert "Market value: JPY 0" in public_report
    assert "Total equity: JPY 1,000,000" in public_report
    assert "No active positions" in public_report
    assert "9001" not in public_report
    assert "phase14d15" not in public_report


def _approval_for(plan):
    from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus

    return ApprovalArtifact(
        approval_id="approval-1",
        approval_request_id="request-1",
        pending_plan_id=plan.pending_plan_id,
        order_plan_id=plan.source_order_plan.order_plan_id,
        status=ApprovalStatus.APPROVED,
        approved_item_ids=plan.approved_item_ids,
        rejected_item_ids=(),
        approval_hash=plan.approval.approval_hash,
        approved_at="2026-07-07T00:00:00Z",
        expires_at="2026-07-08T00:00:00Z",
        review_required=False,
        reason="approved",
    )


def _write_runtime_state(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase14e8-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": "2026-07-07",
        },
    )


def _write_pending(runtime_root: Path) -> None:
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "phase14e8-empty-pending",
            "state": "CONSUMED",
            "environment": "demo",
            "created_at": "2026-07-07",
            "updated_at": "2026-07-07",
            "items": [],
        },
    )


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
