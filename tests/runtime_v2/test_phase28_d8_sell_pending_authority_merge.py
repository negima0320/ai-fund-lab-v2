from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.pending.composition import reconcile_with_existing_sell_pending
from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import attach_approval_link, promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan


BUSINESS_DATE = "2023-04-10"


def test_phase28_d8_43880_existing_null_new_valid_listed_info_is_filled(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    existing_item = _sell_item(
        "strategy-d3ca3c09c7e90609497b",
        "43880",
        listed_info=None,
        source_decision_type="SELL_EXIT",
        source_pm_decision_id="strategy-sell-exit-43880",
    )
    _write_existing_pending(runtime_root, items=(existing_item,))
    new_item = _sell_item(
        "opi-sell-exit-pm-43880-001",
        "43880",
        listed_info=_listed_info("43880"),
        source_decision_type="SELL_EXIT",
        source_pm_decision_id="pm-2023-04-10-43880-exit",
        planning_authority_source="sell_planning_pm_fixture",
    )
    pending = _new_pending(items=(new_item,))

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "PASS"
    assert result.pending.items[0].pending_item_id == existing_item.pending_item_id
    assert result.pending.items[0].listed_info == _listed_info("43880")
    merge = result.evidence["authority_merge_events"][0]
    assert merge["merge_action"] == "FILL_MISSING_FROM_NEW"
    assert merge["validation_status"] == "PASS"
    assert merge["listed_info_source_item_id"] == "opi-sell-exit-pm-43880-001"


def test_phase28_d8_existing_valid_new_null_preserves_existing(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    existing_item = _sell_item("opi-existing-43880", "43880", listed_info=_listed_info("43880"))
    _write_existing_pending(runtime_root, items=(existing_item,))
    pending = _new_pending(items=(_sell_item("opi-new-43880", "43880", listed_info=None),))

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "PASS"
    assert result.pending.items[0].listed_info == _listed_info("43880")
    assert result.evidence["authority_merge_events"][0]["merge_action"] == "PRESERVE_EXISTING"


def test_phase28_d8_both_valid_equivalent_preserves_existing(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    existing_item = _sell_item("opi-existing-43880", "43880", listed_info=_listed_info("43880"))
    _write_existing_pending(runtime_root, items=(existing_item,))
    pending = _new_pending(items=(_sell_item("opi-new-43880", "43880", listed_info=_listed_info("43880")),))

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "PASS"
    assert result.pending.items[0].pending_item_id == "opi-existing-43880"
    assert result.evidence["authority_merge_events"][0]["conflict_status"] == "NO_CONFLICT_EQUIVALENT"


def test_phase28_d16_43880_existing_canonical_preserved_over_pm_basic_market_metadata(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    existing_item = _sell_item(
        "strategy-48c2f0737936a341d096",
        "43880",
        listed_info=_listed_info("43880", market="グロース", authority="canonical_pit_listed_issues"),
        source_decision_type="SELL_EXIT",
        source_pm_decision_id="strategy-sell-exit-43880",
    )
    _write_existing_pending(runtime_root, items=(existing_item,))
    pending = _new_pending(
        items=(
            _sell_item(
                "opi-sell-exit-pm-43880-001",
                "43880",
                listed_info=_listed_info("43880", market="東証"),
                source_decision_type="SELL_EXIT",
                source_pm_decision_id="pm-2023-04-10-43880-exit",
            ),
        )
    )

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "PASS"
    assert result.pending.items[0].pending_item_id == existing_item.pending_item_id
    assert result.pending.items[0].listed_info == existing_item.listed_info
    merge = result.evidence["authority_merge_events"][0]
    assert merge["merge_action"] == "PRESERVE_EXISTING_CANONICAL"
    assert merge["conflict_status"] == "NO_CONFLICT_AUTHORITY_PRECEDENCE"
    assert merge["reason_code"] == "PENDING_SELL_CANONICAL_LISTED_INFO_PRESERVED_OVER_BASIC_MARKET_METADATA"
    assert merge["existing_authority_type"] == "CANONICAL_PIT_LISTED_ISSUE_AUTHORITY"
    assert merge["new_authority_type"] == "PM_BASIC_EXECUTION_METADATA"
    assert merge["market_existing_value"] == "グロース"
    assert merge["market_new_value"] == "東証"
    assert merge["secondary_market_value"] == "東証"
    assert merge["canonical_authority_preserved"] is True


def test_phase28_d16_canonical_vs_canonical_market_mismatch_reviews(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    existing_item = _sell_item(
        "opi-existing-43880",
        "43880",
        listed_info=_listed_info("43880", market="グロース", authority="canonical_pit_listed_issues"),
    )
    existing = _write_existing_pending(runtime_root, items=(existing_item,))
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")
    pending = _new_pending(
        items=(
            _sell_item(
                "opi-new-43880",
                "43880",
                listed_info=_listed_info("43880", market="スタンダード", authority="canonical_pit_listed_issues"),
            ),
        )
    )

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.existing_pending is not None
    assert result.existing_pending.pending_plan_id == existing.pending_plan_id
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before
    merge = result.evidence["authority_merge_events"][0]
    assert merge["existing_authority_type"] == "CANONICAL_PIT_LISTED_ISSUE_AUTHORITY"
    assert merge["new_authority_type"] == "CANONICAL_PIT_LISTED_ISSUE_AUTHORITY"
    assert merge["conflict_status"] == "CONFLICTING_LISTED_INFO"
    assert "PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT" in result.evidence["reason_codes"]


def test_phase28_d8_conflicting_listed_info_reviews_and_preserves_original(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    existing_item = _sell_item("opi-existing-43880", "43880", listed_info=_listed_info("43880", market="東証"))
    existing = _write_existing_pending(runtime_root, items=(existing_item,))
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")
    pending = _new_pending(items=(_sell_item("opi-new-43880", "43880", listed_info=_listed_info("43880", market="名証")),))

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.existing_pending is not None
    assert result.existing_pending.pending_plan_id == existing.pending_plan_id
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before
    assert "PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT" in result.evidence["reason_codes"]


def test_phase28_d8_both_null_reviews_before_approval(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    _write_existing_pending(runtime_root, items=(_sell_item("opi-existing-43880", "43880", listed_info=None),))
    pending = _new_pending(items=(_sell_item("opi-new-43880", "43880", listed_info=None),))

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "PENDING_SELL_REQUIRED_AUTHORITY_LISTED_INFO_MISSING" in result.evidence["reason_codes"]


def test_phase28_d8_committed_existing_sell_does_not_merge(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    _write_existing_pending(
        runtime_root,
        items=(_sell_item("opi-existing-43880", "43880", listed_info=None),),
        state=PendingPlanState.SUBMITTING,
    )
    pending = _new_pending(items=(_sell_item("opi-new-43880", "43880", listed_info=_listed_info("43880")),))

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert "PENDING_SELL_ALREADY_SUBMITTED_REVIEW" in result.evidence["reason_codes"]
    assert result.evidence["authority_merge_events"] == []


def test_phase28_d8_buy_items_are_not_authority_merged(tmp_path: Path) -> None:
    runtime_root, artifact_dir = _runtime_root(tmp_path)
    _write_existing_pending(
        runtime_root,
        items=(
            _sell_item("opi-existing-43880", "43880", listed_info=None),
            _buy_item("opi-buy-83060", "83060"),
        ),
    )
    pending = _new_pending(
        items=(
            _sell_item("opi-new-43880", "43880", listed_info=_listed_info("43880")),
            _buy_item("opi-new-buy-94320", "94320"),
        )
    )

    result = reconcile_with_existing_sell_pending(
        runtime_root=runtime_root,
        pending=pending,
        business_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        environment="historical",
        artifact_dir=artifact_dir,
    )

    assert result.status == "PASS"
    assert [event["existing_pending_item_id"] for event in result.evidence["authority_merge_events"]] == ["opi-existing-43880"]
    assert any(item.pending_item_id == "opi-new-buy-94320" for item in result.pending.items)


def _runtime_root(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    artifact_dir = root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE
    artifact_dir.mkdir(parents=True)
    return root, artifact_dir


def _sell_item(
    pending_item_id: str,
    symbol: str,
    *,
    listed_info: dict | None,
    source_decision_type: str = "SELL_EXIT",
    source_pm_decision_id: str = "pm-2023-04-10-sell-exit",
    planning_authority_source: str = "fixture_sell_planning",
) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side="SELL",
        quantity=100,
        order_type="MARKET",
        estimated_price=100,
        estimated_amount=10_000,
        approved=True,
        state="READY",
        listed_info=listed_info,
        source_decision_type=source_decision_type,
        source_pm_decision_id=source_pm_decision_id,
        source_pm_business_date=BUSINESS_DATE,
        source_position_symbol=symbol,
        quantity_contract={"source_decision": source_decision_type, "position_campaign_id": "campaign-43880"},
    )


def _buy_item(pending_item_id: str, symbol: str) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side="BUY",
        quantity=100,
        order_type="MARKET",
        estimated_price=100,
        estimated_amount=10_000,
        approved=True,
        state="READY",
    )


def _listed_info(code: str, *, market: str = "東証", authority: str = "") -> dict:
    listed_info = {
        "code": code,
        "market": market,
        "product_category": "011",
        "security_type": "011",
        "current_listed": True,
    }
    if authority:
        listed_info["listed_info_authority"] = authority
        listed_info["listed_info_source_hash"] = "sha256:canonical-listed-info-fixture"
        listed_info["listed_info_source_artifact"] = "fixtures/listed_issues.parquet"
    return listed_info


def _new_pending(*, items: tuple[PendingOrderItem, ...]):
    return _pending_plan("order-plan-new", items=items)


def _write_existing_pending(
    root: Path,
    *,
    items: tuple[PendingOrderItem, ...],
    state: PendingPlanState = PendingPlanState.APPROVED,
):
    pending = replace(_pending_plan("order-plan-existing", items=items), state=state)
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _pending_plan(order_plan_id: str, *, items: tuple[PendingOrderItem, ...]):
    source_path = f"fixtures/{order_plan_id}.json"
    pending = promote_order_plan_to_pending(
        order_plan_id=order_plan_id,
        source_order_plan_path=source_path,
        source_order_plan_hash="sha256:fixture",
        environment="historical",
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=items,
    )
    return attach_approval_link(
        pending,
        approval_path=f"fixtures/{order_plan_id}-approval.json",
        approval_hash="sha256:approval",
        approval_status="APPROVED",
        approved_item_ids=tuple(item.pending_item_id for item in items),
        approval_expires_at=f"{BUSINESS_DATE}T15:00:00+09:00",
    )


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
