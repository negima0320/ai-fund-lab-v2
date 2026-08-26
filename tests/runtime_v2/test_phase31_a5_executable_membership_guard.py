import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.historical_support.corporate_action_quarantine import (
    upsert_quarantine,
)
from ai_fund_lab_v2.runtime_v2.pending.models import PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import (
    attach_approval_link,
    promote_order_plan_to_pending,
)
from ai_fund_lab_v2.runtime_v2.pending.review_scope_authority import (
    build_pending_review_scope_authority,
)
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import (
    load_runtime_current_exposure,
)
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import (
    ManualReviewThreshold,
    CapitalDeploymentPolicy,
    capital_deployment_policy_hash,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import _blocked_guard_evidence
from tests.runtime_v2.pending_fixtures import make_pending_item


def test_phase31_a5_historical_ca_quarantined_buy_is_removed_from_executable_membership(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, business_date="2022-09-26", cash=1_000_000.0, positions=[])
    upsert_quarantine(
        runtime_root=root,
        business_date="2022-09-26",
        symbol="76920",
        reason="corporate_action_event_not_resolved",
        event_status="IMPACT_DETECTED",
    )
    policy = _policy(tmp_path)
    pass_buy = _buy_item("buy-pass", symbol="72030")
    ca_buy = _buy_item("buy-ca", symbol="76920")
    pending = _pending(
        (pass_buy, ca_buy),
        policy=policy,
        environment="historical",
        business_date="2022-09-26",
    )

    linked = attach_approval_link(
        pending,
        approval_path="approval_artifact/2022-09-26/approval.json",
        approval_hash="approval-hash",
        approval_status="APPROVED",
        approved_item_ids=("buy-pass", "buy-ca"),
        approval_expires_at="2022-09-26T15:00:00+09:00",
        planning_submit_feasibility_current=load_runtime_current_exposure(
            root / "persistent_ledger" / "state.json",
            business_date="2022-09-26",
        ),
        planning_submit_feasibility_policy=policy,
    )

    authority = build_pending_review_scope_authority(linked)
    ca_evidence = _item_evidence(linked, "buy-ca")

    assert linked.state == PendingPlanState.REVIEW_REQUIRED
    assert linked.review_scope == "BUY_ITEM_SCOPED_REVIEW"
    assert linked.approved_buy_item_ids == ("buy-pass",)
    assert linked.review_required_buy_item_ids == ("buy-ca",)
    assert authority.executable_item_ids == ("buy-pass",)
    assert "buy-ca" not in authority.executable_item_ids
    assert ca_evidence["violated_policy"] == "historical_corporate_action_symbol_quarantine"
    assert ca_evidence["guard_class"] == "DATA_INTEGRITY_SAFETY"
    assert ca_evidence["guard_code"] == "CORPORATE_ACTION_UNRESOLVED"
    assert ca_evidence["scope"] == "ITEM"
    assert ca_evidence["affected_side"] == "BUY"
    assert ca_evidence["batch_blocking"] is False


def test_phase31_a5_historical_ca_quarantined_buy_preserves_sell_continuation(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(
        root,
        business_date="2022-09-26",
        cash=1_000_000.0,
        positions=[{"symbol": "72030", "quantity": 100, "market_value": 100_000.0}],
    )
    upsert_quarantine(
        runtime_root=root,
        business_date="2022-09-26",
        symbol="76920",
        reason="corporate_action_event_not_resolved",
        event_status="IMPACT_DETECTED",
    )
    policy = _policy(tmp_path)
    sell = _sell_item("sell-pass", symbol="72030")
    ca_buy = _buy_item("buy-ca", symbol="76920")
    pending = _pending(
        (sell, ca_buy),
        policy=policy,
        environment="historical",
        business_date="2022-09-26",
    )

    linked = attach_approval_link(
        pending,
        approval_path="approval_artifact/2022-09-26/approval.json",
        approval_hash="approval-hash",
        approval_status="APPROVED",
        approved_item_ids=("sell-pass", "buy-ca"),
        approval_expires_at="2022-09-26T15:00:00+09:00",
        planning_submit_feasibility_current=load_runtime_current_exposure(
            root / "persistent_ledger" / "state.json",
            business_date="2022-09-26",
        ),
        planning_submit_feasibility_policy=policy,
    )

    authority = build_pending_review_scope_authority(linked)

    assert linked.review_scope == "BUY_ITEM_SCOPED_REVIEW"
    assert linked.sell_continuation_allowed is True
    assert linked.approved_sell_item_ids == ("sell-pass",)
    assert linked.review_required_buy_item_ids == ("buy-ca",)
    assert authority.executable_sell_item_ids == ("sell-pass",)
    assert authority.reviewed_buy_item_ids == ("buy-ca",)


def test_phase31_a5_common_ca_adjustment_authority_is_consumed_before_pending_membership(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    _write_current(root, business_date="2026-07-09", cash=1_000_000.0, positions=[])
    policy = _policy(tmp_path)
    pass_buy = _buy_item("buy-pass", symbol="72030")
    ca_buy = replace(
        _buy_item("buy-ca", symbol="99840"),
        quantity_contract=_quantity_contract("99840")
        | {
            "corporate_action_adjustment_authority": {
                "corporate_action_adjustment_authority_status": "REVIEW_REQUIRED",
                "corporate_action_adjustment_authority_reason": "corporate_action_adjustment_authority_unresolved",
                "corporate_action_adjustment_authority_path": "runtime_state/corporate_action_adjustment/99840.json",
            },
        },
    )
    pending = _pending((pass_buy, ca_buy), policy=policy, environment="demo", business_date="2026-07-09")

    linked = attach_approval_link(
        pending,
        approval_path="approval_artifact/2026-07-09/approval.json",
        approval_hash="approval-hash",
        approval_status="APPROVED",
        approved_item_ids=("buy-pass", "buy-ca"),
        approval_expires_at="2026-07-09T15:00:00+09:00",
        planning_submit_feasibility_current=load_runtime_current_exposure(
            root / "persistent_ledger" / "state.json",
            business_date="2026-07-09",
        ),
        planning_submit_feasibility_policy=policy,
    )

    ca_evidence = _item_evidence(linked, "buy-ca")
    authority = build_pending_review_scope_authority(linked)

    assert linked.review_required_buy_item_ids == ("buy-ca",)
    assert authority.executable_item_ids == ("buy-pass",)
    assert ca_evidence["violated_policy"] == "corporate_action_adjustment_authority"
    assert ca_evidence["guard_code"] == "CORPORATE_ACTION_UNRESOLVED"
    assert ca_evidence["typed_guard"]["consumer_action"] == "FAIL_CLOSED_REVIEW_ITEM_ALLOW_UNAFFECTED_ITEMS"


def test_phase31_a5_submit_blocked_evidence_materializes_typed_guard_fields() -> None:
    cases = (
        ("aggregate_submit_feasibility", "aggregate_submit_feasibility_review_required", "BUY"),
        ("accepted_generation_binding", "accepted_generation_binding_mismatch", "BUY"),
        ("historical_corporate_action_symbol_quarantine", "corporate_action_event_not_resolved", "BUY"),
        ("corporate_action_adjustment_authority", "corporate_action_adjustment_authority_unresolved", "BUY"),
        ("safety_operation_guard", "safety_operation_guard_block_submit", "BUY"),
        ("buy_market_status_eligibility", "buy market closed", "BUY"),
        ("opportunity_buy_eligibility", "opportunity buy eligibility rejected", "BUY"),
        ("supported_side", "supported side missing", "BUY"),
        ("sell_current_position_quantity", "sell quantity exceeds current position quantity", "SELL"),
        ("broker_available_quantity", "broker sell available quantity missing", "SELL"),
        ("max_sell_liquidation_amount", "estimated amount exceeds max_sell_liquidation_amount", "SELL"),
    )

    for policy, reason, side in cases:
        evidence = _blocked_guard_evidence(
            evidence={"pending_item_id": f"{side.lower()}-1", "side": side},
            reason=reason,
            violated_policy=policy,
            violated_policy_source=f"{policy}:source",
        )

        assert evidence["guard_decision"] == "BLOCKED"
        assert evidence["violated_policy"] == policy
        assert evidence["typed_guard"]["status"] == "REVIEW_REQUIRED"
        assert evidence["guard_class"]
        assert evidence["guard_code"]
        assert evidence["scope"]
        assert evidence["affected_side"] in {"BUY", "SELL", "BOTH", "NONE"}
        assert evidence["affected_item_ids"] == [f"{side.lower()}-1"]
        assert "batch_blocking" in evidence
        assert evidence["recoverability"]
        assert evidence["canonical_owner"]
        assert evidence["consumer_action"]


def _runtime_root(tmp_path: Path) -> Path:
    return tmp_path / ".runtime"


def _policy(tmp_path: Path) -> CapitalDeploymentPolicy:
    return CapitalDeploymentPolicy(
        policy_version="capital_deployment_v1",
        policy_source=str(tmp_path / "capital_deployment_policy.json"),
        evaluation_capital=1_000_000.0,
        max_positions=8,
        min_order_amount=0.0,
        max_buy_order_amount=None,
        max_sell_liquidation_amount=None,
        buy_notional_policy="derived_from_capital_allocation_and_constraints",
        sell_liquidation_policy="current_owned_available_quantity_policy",
        manual_review_threshold=ManualReviewThreshold(buy_amount=None, sell_liquidation_amount=None),
        loaded_from=str(tmp_path / "capital_deployment_policy.json"),
    )


def _buy_item(pending_item_id: str, *, symbol: str) -> object:
    return replace(
        make_pending_item(pending_item_id),
        symbol=symbol,
        side="BUY",
        quantity=100.0,
        estimated_price=1_000.0,
        estimated_amount=100_000.0,
        reserved_notional=100_000.0,
        reservation_price=1_000.0,
        quantity_contract=_quantity_contract(symbol),
    )


def _sell_item(pending_item_id: str, *, symbol: str) -> object:
    return replace(
        make_pending_item(pending_item_id),
        symbol=symbol,
        side="SELL",
        quantity=100.0,
        estimated_price=1_000.0,
        estimated_amount=100_000.0,
        quantity_contract=_quantity_contract(symbol),
    )


def _pending(
    items: tuple[object, ...],
    *,
    policy: CapitalDeploymentPolicy,
    environment: str,
    business_date: str,
) -> object:
    prepared_items = tuple(
        replace(
            item,
            policy_version=policy.policy_version,
            policy_source=policy.policy_source,
            submit_policy_version=policy.policy_version,
            submit_policy_source=policy.policy_source,
            submit_policy_hash=capital_deployment_policy_hash(policy),
            evaluation_capital=policy.evaluation_capital,
            max_positions=policy.max_positions,
            min_order_amount=policy.min_order_amount,
            max_buy_order_amount=policy.max_buy_order_amount,
            max_sell_liquidation_amount=policy.max_sell_liquidation_amount,
            buy_notional_policy=policy.buy_notional_policy,
            sell_liquidation_policy=policy.sell_liquidation_policy,
            manual_review_threshold={
                "buy_amount": policy.manual_review_threshold.buy_amount,
                "sell_liquidation_amount": policy.manual_review_threshold.sell_liquidation_amount,
            },
        )
        for item in items
    )
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-phase31-a5",
        source_order_plan_path=f"order_plan/{business_date}/order_plan.json",
        source_order_plan_hash="sha256:phase31-a5-order-plan",
        environment=environment,
        plan_created_date=business_date,
        intended_submit_date=business_date,
        target_session_date=business_date,
        items=prepared_items,
    )
    return replace(pending, policy_context=_policy_context(policy))


def _policy_context(policy: CapitalDeploymentPolicy) -> dict:
    return {
        "policy_version": policy.policy_version,
        "policy_source": policy.policy_source,
        "target_position_count": 8,
        "selected_dynamic_position_count": 8,
        "safety_hard_maximum": None,
        "target_cash_ratio": 0.10,
        "target_gross_exposure_ratio": 0.85,
        "maximum_gross_exposure_ratio": 0.90,
        "legacy_position_count_config_used": False,
        "position_count_fallback_used": False,
        "legacy_cash_config_used": False,
        "legacy_exposure_config_used": False,
        "cash_exposure_fallback_used": False,
    }


def _quantity_contract(symbol: str) -> dict:
    return {
        **_policy_context(_policy(Path("/tmp"))),
        "position_sizing_authority": {
            "symbol": symbol,
            "selected_position_amount": 100_000.0,
            "remaining_add_capacity": 100_000.0,
            "selected_position_weight": 0.10,
            "target_weight": 0.10,
            "target_notional": 100_000.0,
            "incremental_buy_notional": 100_000.0,
            "maximum_position_weight": 0.20,
            "portfolio_policy_source": "phase31_a5_fixture_portfolio_policy",
        },
    }


def _write_current(root: Path, *, business_date: str, cash: float, positions: list[dict]) -> None:
    market_value = sum(float(position["market_value"]) for position in positions)
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase31-a5",
            "environment": "test",
            "as_of": business_date,
            "positions": positions,
            "cash": cash,
            "buying_power": cash,
            "market_value": market_value,
            "total_equity": cash + market_value,
        },
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _item_evidence(pending, pending_item_id: str) -> dict:
    items = pending.planning_submit_feasibility["items"]
    return next(item for item in items if item["pending_item_id"] == pending_item_id)
