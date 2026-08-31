from __future__ import annotations

import pytest

from ai_fund_lab_v2.runtime_v2.historical_support.safety_temporal_authority import (
    CONTRACT_ID,
    evaluate_historical_daily_neutral_safety_authority,
    evaluate_historical_pending_safety_authority,
    pending_scope_current_valuation_adapter_ready,
    pending_scope_sell_continuation_adapter_ready,
)


BUSINESS_DATE = "2026-07-08"
PREVIOUS_DATE = "2026-07-07"
RUN_ID = "runtime-test-phase30-ak9r28"
PROFILE_ID = "historical-smoke"
EVIDENCE_ROOT = "/tmp/runtime-test-phase30-ak9r28"


@pytest.mark.parametrize(
    ("case_name", "pending", "scope", "expected_status", "expected_reason"),
    [
        (
            "normal_approved_pending",
            lambda: _approved_pending(),
            "submit",
            "READY",
            "historical_pending_safety_authority_ready",
        ),
        (
            "buy_item_scoped_review_sell_planning",
            lambda: _buy_item_scoped_review_pending(approved_state="APPROVED"),
            "sell_planning",
            "READY",
            "historical_pending_safety_authority_ready",
        ),
        (
            "buy_item_scoped_review_submit",
            lambda: _buy_item_scoped_review_pending(approved_state="APPROVED"),
            "submit",
            "READY",
            "historical_pending_safety_authority_ready",
        ),
        (
            "reviewed_sell",
            lambda: _buy_item_scoped_review_pending(include_reviewed_sell=True),
            "sell_planning",
            "REVIEW_REQUIRED",
            "historical_pending_safety_authority_mismatch",
        ),
        (
            "mixed_sell_item_scoped_review",
            lambda: _mixed_sell_item_scoped_review_pending(),
            "sell_planning",
            "READY",
            "historical_pending_safety_authority_ready",
        ),
        (
            "stale_prior_day_pending",
            lambda: _approved_pending(target_date=PREVIOUS_DATE),
            "submit",
            "REVIEW_REQUIRED",
            "historical_pending_safety_authority_mismatch",
        ),
        (
            "next_day_residual_reviewed_buy",
            lambda: _buy_item_scoped_review_pending(approved_state="CONSUMED", reviewed_batch_status="ITEM_REVIEW_REQUIRED"),
            "current_valuation",
            "READY",
            "historical_post_submit_residual_buy_review_current_valuation_ready",
        ),
        (
            "no_pending",
            lambda: _empty_pending(),
            "morning",
            "READY",
            "historical_no_action_pending_safety_authority_ready",
        ),
        (
            "malformed_pending",
            lambda: _buy_item_scoped_review_pending(malformed=True),
            "submit",
            "REVIEW_REQUIRED",
            "historical_pending_safety_authority_mismatch",
        ),
        (
            "current_valuation_same_day_continuation",
            lambda: _buy_item_scoped_review_pending(approved_state="CONSUMED", reviewed_batch_status="ITEM_REVIEW_REQUIRED"),
            "current_valuation",
            "READY",
            "historical_post_submit_residual_buy_review_current_valuation_ready",
        ),
        (
            "genuine_safety_business_date_mismatch",
            lambda: _approved_pending(safety_business_date=PREVIOUS_DATE),
            "submit",
            "REVIEW_REQUIRED",
            "historical_pending_safety_authority_mismatch",
        ),
    ],
)
def test_phase30_ak9r28_shadow_cases_classified_without_unexplained_mismatch(
    case_name: str,
    pending,
    scope: str,
    expected_status: str,
    expected_reason: str,
) -> None:
    result = _pending_authority(pending(), scope=scope)

    assert result["status"] == expected_status, case_name
    assert result["reason"] == expected_reason, case_name
    assert result["contract_id"] == CONTRACT_ID
    assert result["pending_review_scope_contract_id"] == "pending_review_scope_authority"
    assert result["authority_provenance"]["producer"] == CONTRACT_ID


def test_phase30_ak9r28_daily_neutral_consumes_pending_scope_and_fails_closed_on_external_effects() -> None:
    ready = evaluate_historical_daily_neutral_safety_authority(
        business_date=BUSINESS_DATE,
        mode="historical",
        broker_environment="historical_simulated",
        current_payload={},
        pending_payload=_wrap(_empty_pending()),
        readiness_scope="morning",
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        runtime_test_evidence_root=EVIDENCE_ROOT,
        broker_write=False,
        external_delivery=False,
        previous_empty_pending_present=False,
    )
    blocked = {
        **ready,
        **evaluate_historical_daily_neutral_safety_authority(
            business_date=BUSINESS_DATE,
            mode="historical",
            broker_environment="historical_simulated",
            current_payload={},
            pending_payload=_wrap(_empty_pending()),
            readiness_scope="morning",
            runtime_test_run_id=RUN_ID,
            runtime_test_profile_id=PROFILE_ID,
            runtime_test_evidence_root=EVIDENCE_ROOT,
            broker_write=True,
            external_delivery=False,
            previous_empty_pending_present=False,
        ),
    }

    assert ready["status"] == "READY"
    assert ready["pending_review_scope_contract_id"] == "pending_review_scope_authority"
    assert blocked["status"] == "REVIEW_REQUIRED"
    assert "broker_write" in blocked["mismatched_fields"]


def test_phase30_ak9r28_pending_scope_adapters_delegate_to_ak9r27_authority() -> None:
    sell_plan = _buy_item_scoped_review_pending(approved_state="APPROVED")
    residual_plan = _buy_item_scoped_review_pending(
        approved_state="CONSUMED",
        reviewed_batch_status="ITEM_REVIEW_REQUIRED",
    )
    reviewed_sell = _buy_item_scoped_review_pending(include_reviewed_sell=True)
    mixed_sell = _mixed_sell_item_scoped_review_pending()

    assert pending_scope_sell_continuation_adapter_ready(
        pending_payload=_wrap(sell_plan),
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="sell_planning",
    )
    assert pending_scope_current_valuation_adapter_ready(
        pending_payload=_wrap(residual_plan),
        business_date=BUSINESS_DATE,
        mode="historical",
    )
    assert not pending_scope_sell_continuation_adapter_ready(
        pending_payload=_wrap(reviewed_sell),
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="sell_planning",
    )
    assert pending_scope_sell_continuation_adapter_ready(
        pending_payload=_wrap(mixed_sell),
        business_date=BUSINESS_DATE,
        mode="historical",
        readiness_scope="sell_planning",
    )


def _pending_authority(pending: dict, *, scope: str) -> dict:
    return evaluate_historical_pending_safety_authority(
        pending_payload=_wrap(pending),
        business_date=BUSINESS_DATE,
        readiness_scope=scope,
        runtime_test_run_id=RUN_ID,
        runtime_test_profile_id=PROFILE_ID,
        runtime_test_evidence_root=EVIDENCE_ROOT,
    )


def _wrap(pending: dict) -> dict:
    return {
        "payload": pending,
        "slot_status": str(pending.get("state") or ""),
        "active_pending": bool(pending.get("active_pending")),
        "source_paths": {"pending": "pending_order_plan.json"},
    }


def _empty_pending() -> dict:
    return {
        "pending_plan_id": "",
        "state": "EMPTY",
        "environment": "historical",
        "target_session_date": BUSINESS_DATE,
        "active_pending": False,
        "items": [],
    }


def _approved_pending(
    *,
    target_date: str = BUSINESS_DATE,
    safety_business_date: str = BUSINESS_DATE,
) -> dict:
    return {
        "pending_plan_id": "pending-approved",
        "state": "APPROVED",
        "environment": "historical",
        "target_session_date": target_date,
        "active_pending": True,
        "approved_item_ids": [],
        "approved_buy_item_ids": [],
        "approved_sell_item_ids": [],
        "review_required_buy_item_ids": [],
        "review_required_sell_item_ids": [],
        "items": [],
        "safety_context": _safety_context(safety_business_date=safety_business_date),
    }


def _buy_item_scoped_review_pending(
    *,
    approved_state: str = "APPROVED",
    reviewed_batch_status: str = "ITEM_REVIEW_REQUIRED",
    include_reviewed_sell: bool = False,
    malformed: bool = False,
) -> dict:
    review_id = "sell-review" if include_reviewed_sell else "buy-review"
    review_side = "SELL" if include_reviewed_sell else "BUY"
    approved_ids = ["unknown-buy-pass"] if malformed else ["buy-pass"]
    return {
        "pending_plan_id": "pending-buy-item-scoped",
        "state": "REVIEW_REQUIRED",
        "environment": "historical",
        "target_session_date": BUSINESS_DATE,
        "active_pending": True,
        "review_scope": "BUY_ITEM_SCOPED_REVIEW",
        "review_scope_source": "planning_submit_feasibility",
        "sell_continuation_allowed": True,
        "approved_item_ids": approved_ids,
        "approved_buy_item_ids": approved_ids,
        "approved_sell_item_ids": [],
        "review_required_buy_item_ids": [] if include_reviewed_sell else [review_id],
        "review_required_sell_item_ids": [review_id] if include_reviewed_sell else [],
        "planning_submit_feasibility": {
            "status": "REVIEW_REQUIRED",
            "items": [
                {"pending_item_id": "buy-pass", "status": "PASS", "side": "BUY"},
                {
                    "pending_item_id": review_id,
                    "status": "REVIEW_REQUIRED",
                    "side": review_side,
                    "violated_policy": "reserved_cash" if not include_reviewed_sell else "sell_available_quantity",
                    "violated_policy_source": "planning_submit_feasibility",
                },
            ],
        },
        "items": [
            _item("buy-pass", side="BUY", state=approved_state, approved=True),
            _item(
                review_id,
                side=review_side,
                state="REVIEW_REQUIRED",
                approved=False,
                batch_submit_status=reviewed_batch_status,
            ),
        ],
        "safety_context": _safety_context(safety_business_date=BUSINESS_DATE),
    }


def _mixed_sell_item_scoped_review_pending() -> dict:
    return {
        "pending_plan_id": "pending-mixed-sell-item-scoped",
        "state": "REVIEW_REQUIRED",
        "environment": "historical",
        "target_session_date": BUSINESS_DATE,
        "active_pending": True,
        "review_scope": "MIXED_SELL_ITEM_SCOPED_REVIEW",
        "review_scope_source": "planning_submit_feasibility",
        "sell_continuation_allowed": True,
        "approved_item_ids": ["sell-pass"],
        "approved_buy_item_ids": [],
        "approved_sell_item_ids": ["sell-pass"],
        "review_required_buy_item_ids": ["buy-review"],
        "review_required_sell_item_ids": ["sell-review"],
        "planning_submit_feasibility": {
            "status": "REVIEW_REQUIRED",
            "items": [
                {"pending_item_id": "sell-pass", "status": "PASS", "side": "SELL"},
                {
                    "pending_item_id": "buy-review",
                    "status": "REVIEW_REQUIRED",
                    "side": "BUY",
                    "violated_policy": "reserved_cash",
                    "violated_policy_source": "planning_submit_feasibility",
                },
                {
                    "pending_item_id": "sell-review",
                    "status": "REVIEW_REQUIRED",
                    "side": "SELL",
                    "violated_policy": "corporate_action_adjustment_authority",
                    "violated_policy_source": "runtime_state/corporate_action_adjustments/2023-10-11/50280.json",
                },
            ],
        },
        "items": [
            _item("sell-pass", side="SELL", state="APPROVED", approved=True),
            _item("buy-review", side="BUY", state="REVIEW_REQUIRED", approved=False),
            _item("sell-review", side="SELL", state="REVIEW_REQUIRED", approved=False),
        ],
        "safety_context": _safety_context(safety_business_date=BUSINESS_DATE),
    }


def _item(
    item_id: str,
    *,
    side: str,
    state: str,
    approved: bool,
    batch_submit_status: str = "PASS_ITEM_SUBMITTABLE",
) -> dict:
    return {
        "pending_item_id": item_id,
        "symbol": "7203",
        "side": side,
        "state": state,
        "approved": approved,
        "batch_submit_status": batch_submit_status,
        **_safety_context(safety_business_date=BUSINESS_DATE),
        "temporal_authority_business_date": BUSINESS_DATE,
    }


def _safety_context(*, safety_business_date: str) -> dict:
    return {
        "safety_authority": "historical_initial_no_external_effect",
        "safety_decision": "NEUTRAL",
        "safety_policy_version": "historical_replay_neutral_safety_v1",
        "safety_source": "data_readiness_historical_temporal_authority",
        "safety_business_date": safety_business_date,
        "safety_decision_id": f"historical-neutral-safety:{safety_business_date}",
        "runtime_test_run_id": RUN_ID,
        "runtime_test_profile_id": PROFILE_ID,
        "runtime_test_evidence_root": EVIDENCE_ROOT,
    }
