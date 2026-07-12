from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from ai_fund_lab_v2.runtime_v2.submit.pipeline import _approval_from_pending, run_submit_pipeline
from tests.runtime_v2.phase15bn_isolated_submit_fixture import (
    BUSINESS_DATE,
    PENDING_ITEM_ID,
    build_isolated_submit_fixture,
)
from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings


def test_phase15bn_isolated_root_has_no_existing_runtime_fallback(tmp_path):
    before_hashes = _existing_runtime_hashes()
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    manifest = build_isolated_submit_fixture(root)
    pending_path = root / "pending_order_plan" / "pending_order_plan.json"
    pending = _pending(root)
    pending = replace(
        pending,
        items=(replace(pending.items[0], order_type="REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY"),),
    )
    write_pending_order_plan(pending_path, pending)

    result = run_submit_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=root / "runtime_state" / "policy" / "capital_deployment.json",
    )

    assert manifest["existing_runtime_referenced"] is False
    assert result.pending_path == str(pending_path)
    assert result.status == "BLOCKED"
    assert result.submitted_count == 0
    assert result.pending_consumed is False
    assert _existing_runtime_hashes() == before_hashes


def test_phase15bn_all_conditions_ready_for_no_send_preflight(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)

    preflight = _preflight(root)

    assert preflight.allowed is True
    assert preflight.blocked is False
    assert preflight.command is not None
    assert preflight.command.symbol == "6522"
    assert preflight.command.side == "SELL"
    assert preflight.command.order_type == "MARKET"
    assert preflight.command.price_type == "MARKET"
    assert preflight.command.live_order_allowed is True


def test_phase15bn_safety_artifact_missing_fails_closed(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    (root / "runtime_state" / "safety" / "latest_safety_decision.json").unlink()

    result = run_submit_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=_BrokerShouldNotBeCalled(),
        capital_deployment_policy_path=root / "runtime_state" / "policy" / "capital_deployment.json",
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert result.pending_consumed is False
    assert result.submit_guard_item_evidence[0]["violated_policy"] == "safety_operation_guard"


def test_phase15bn_order_condition_missing_or_unapproved_blocks_preflight(tmp_path):
    for case in ("missing", "unapproved"):
        root = tmp_path / case / ".runtime_acceptance_phase15_submit"
        build_isolated_submit_fixture(root)
        pending = _pending(root)
        item = pending.items[0]
        if case == "missing":
            next_item = replace(item, order_type="REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY")
            pending = replace(pending, items=(next_item,))
            expected = "order condition authority review required"
        else:
            approval = replace(pending.approval, approved_order_conditions={})
            pending = replace(pending, approval=approval)
            expected = "order condition not approved"
        write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)

        preflight = _preflight(root)

        assert preflight.allowed is False
        assert preflight.reason == expected


def test_phase15bn_broker_capability_mismatch_blocks_preflight(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    pending = _pending(root)
    item = replace(pending.items[0], symbol="9984")
    conditions = dict(pending.approval.approved_order_conditions)
    item_conditions = dict(conditions[PENDING_ITEM_ID])
    item_conditions["issue_code"] = "9984"
    item_conditions["broker_issue_code"] = "9984"
    conditions[PENDING_ITEM_ID] = item_conditions
    pending = replace(pending, items=(item,), approval=replace(pending.approval, approved_order_conditions=conditions))
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)

    preflight = _preflight(root)

    assert preflight.allowed is False
    assert preflight.reason == "symbol not supported by broker capability"


def test_phase15bn_pending_non_approved_and_approval_expired_block_preflight(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)
    pending = replace(_pending(root), state=PendingPlanState.PENDING_APPROVAL)
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    assert _preflight(root).reason == "pending state is not APPROVED"

    build_isolated_submit_fixture(root)
    pending = _pending(root)
    pending = replace(pending, approval=replace(pending.approval, approval_expires_at="2026-07-08T15:00:00+09:00"))
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    assert _preflight(root).reason == "approval expired"


def test_phase15bn_broker_quantity_insufficient_blocks_preflight(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_submit"
    build_isolated_submit_fixture(root)

    preflight = _preflight(root, broker_position_quantity=100.0, broker_available_quantity=50.0)

    assert preflight.allowed is False
    assert preflight.reason == "sell quantity exceeds available quantity"


def _preflight(
    root: Path,
    *,
    broker_position_quantity: float = 100.0,
    broker_available_quantity: float = 100.0,
):
    pending = _pending(root)
    approval = _approval_from_pending(pending)
    return run_submit_preflight(
        pending_plan=pending,
        approval_artifact=approval,
        approved_item_id=PENDING_ITEM_ID,
        existing_order_dedup_keys=set(),
        environment="demo",
        base_url_is_demo=True,
        base_url_is_production=False,
        live_order_allowed=True,
        broker_position_quantity=broker_position_quantity,
        broker_available_quantity=broker_available_quantity,
        broker_capability=get_broker_capability("demo"),
    )


def _pending(root: Path):
    read = read_pending_order_plan_path(
        path=root / "pending_order_plan" / "pending_order_plan.json",
        environment="demo",
    )
    assert read.valid
    assert read.plan is not None
    return read.plan


class _BrokerShouldNotBeCalled:
    def preflight(self, command):
        raise AssertionError("broker preflight must not be called in Phase15-BN")

    def submit(self, command):
        raise AssertionError("broker submit must not be called in Phase15-BN")


def _existing_runtime_hashes() -> dict[str, str]:
    paths = {
        "pending": Path(".runtime/pending_order_plan/pending_order_plan.json"),
        "safety": Path(".runtime/runtime_state/safety/latest_safety_decision.json"),
        "current": Path(".runtime/persistent_ledger/state.json"),
    }
    return {key: _sha256(path) for key, path in paths.items() if path.is_file()}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
