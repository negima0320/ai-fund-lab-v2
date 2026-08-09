from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.pending.models import PendingOrderItem, PendingPlanState
from ai_fund_lab_v2.runtime_v2.pending.promotion import attach_approval_link, promote_order_plan_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import (
    SellExitDecision,
    _strategy_source_authority_context_for_sell_candidate,
    run_sell_planning_pending_pipeline,
)


BUSINESS_DATE = "2023-01-18"


def test_phase28_d3_76470_same_day_strategy_sell_and_pm_reduce_reconciles(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="76470", quantity=4100, price=26.0)
    existing = _write_existing_pending(
        runtime_root,
        items=(
            _pending_item("opi-buy-93180", "93180", "BUY", 100),
            _pending_item("opi-strategy-sell-76470", "76470", "SELL", 1300, source_decision_type="SELL"),
        ),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="76470",
                quantity=0,
                reason="peak_drawdown_warning",
                source_decision="REDUCE",
                reduce_intensity="MEDIUM",
                source_decision_id="pm-2023-01-18-76470-reduce",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    evidence = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_sell_reconciliation_evidence.json")

    assert result.status == "PASS"
    assert pending["pending_plan_id"] != existing.pending_plan_id
    assert sorted(item["side"] for item in pending["items"]) == ["BUY", "SELL"]
    sell_items = [item for item in pending["items"] if item["side"] == "SELL" and item["symbol"] == "76470"]
    assert len(sell_items) == 1
    assert sell_items[0]["pending_item_id"] == "opi-strategy-sell-76470"
    assert evidence["reason_codes"] == ["PENDING_SELL_COMPATIBLE_UPDATE_MERGED"]
    assert evidence["review_required"] is False
    assert evidence["opposite_side_preserved"] is True


def test_phase28_d3_same_lineage_reduce_duplicate_preserves_existing(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="76470", quantity=4100, price=26.0)
    _write_existing_pending(
        runtime_root,
        items=(
            _pending_item(
                "opi-existing-reduce-76470",
                "76470",
                "SELL",
                1300,
                source_decision_type="REDUCE",
                source_pm_decision_id="pm-2023-01-18-76470-reduce",
            ),
        ),
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="76470",
                quantity=0,
                reason="peak_drawdown_warning",
                source_decision="REDUCE",
                reduce_intensity="MEDIUM",
                source_decision_id="pm-2023-01-18-76470-reduce",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    evidence = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_sell_reconciliation_evidence.json")

    assert result.status == "PASS"
    assert [item["pending_item_id"] for item in pending["items"] if item["side"] == "SELL"] == ["opi-existing-reduce-76470"]
    assert evidence["reason_codes"] == ["PENDING_SELL_IDEMPOTENT_DUPLICATE_PRESERVED"]


def test_phase28_d3_quantity_conflict_reviews_and_preserves_original_pending(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="76470", quantity=4100, price=26.0)
    existing = _write_existing_pending(
        runtime_root,
        items=(
            _pending_item("opi-existing-sell-76470", "76470", "SELL", 100, source_decision_type="REDUCE"),
        ),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="76470",
                quantity=0,
                reason="peak_drawdown_warning",
                source_decision="REDUCE",
                reduce_intensity="MEDIUM",
                source_decision_id="pm-2023-01-18-76470-reduce",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )
    after = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")
    evidence = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_sell_reconciliation_evidence.json")

    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_plan_id == existing.pending_plan_id
    assert after == before
    assert "PENDING_SELL_CONFLICTING_QUANTITY_REVIEW" in evidence["reason_codes"]
    assert "PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED" in evidence["reason_codes"]
    assert evidence["no_signal_overwrite_prevented"] is True


def test_phase28_d3_submitted_pending_reviews_without_replacement(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="76470", quantity=4100, price=26.0)
    existing = _write_existing_pending(
        runtime_root,
        items=(_pending_item("opi-submitted-sell-76470", "76470", "SELL", 1300, source_decision_type="REDUCE"),),
        state=PendingPlanState.SUBMITTED,
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="76470",
                quantity=0,
                reason="peak_drawdown_warning",
                source_decision="REDUCE",
                reduce_intensity="MEDIUM",
                source_decision_id="pm-2023-01-18-76470-reduce",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_plan_id == existing.pending_plan_id
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before


def test_phase28_d3_review_no_signal_does_not_overwrite_active_pending(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="76470", quantity=4100, price=26.0)
    existing = _write_existing_pending(
        runtime_root,
        items=(_pending_item("opi-existing-sell-76470", "76470", "SELL", 1300, source_decision_type="REDUCE"),),
    )
    before = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="76470",
                quantity=0,
                reason="missing reduce intensity",
                source_decision="REDUCE",
                reduce_intensity="",
                source_decision_id="pm-2023-01-18-76470-reduce",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )
    preservation = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "no_signal_preservation_evidence.json")

    assert result.status == "REVIEW_REQUIRED"
    assert result.pending_plan_id == existing.pending_plan_id
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before
    assert "PENDING_PLAN_NO_SIGNAL_DID_NOT_OVERWRITE_ACTIVE" in preservation["reason_codes"]


def test_phase28_d44_93990_sell_candidate_uses_canonical_listed_info_before_reconciliation(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93990", quantity=600, price=90.0)
    canonical_listed_info = _canonical_listed_info("93990", market="スタンダード", product_category="021")
    existing = _write_existing_pending(
        runtime_root,
        items=(
            _pending_item(
                "strategy-fd750c0ea2bcc16bd06a",
                "93990",
                "SELL",
                600,
                listed_info=canonical_listed_info,
                source_decision_type="SELL_EXIT",
                source_pm_decision_id="strategy-sell-exit-93990",
            ),
        ),
    )
    context = _historical_context(tmp_path)
    context["strategy_source_authority"] = _write_strategy_source_authority(
        tmp_path=tmp_path,
        business_date=BUSINESS_DATE,
        listed_info=canonical_listed_info,
    )

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="93990",
                quantity=600,
                reason="trend_and_opportunity_broken",
                source_decision="EXIT",
                source_decision_id="pm-2023-06-02-93990-exit",
            ),
        ),
        environment_capability_context=context,
    )

    order_plan = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "order_plan.json")
    generated_sell = next(item for item in order_plan["items"] if item["symbol"] == "93990" and item["side"] == "SELL")
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    evidence = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_sell_reconciliation_evidence.json")

    assert result.status == "PASS"
    assert result.pending_plan_id != existing.pending_plan_id
    assert generated_sell["listed_info"]["market"] == "スタンダード"
    assert generated_sell["listed_info"]["product_category"] == "021"
    assert generated_sell["listed_info"]["security_type"] == "021"
    assert generated_sell["listed_info"]["listed_info_authority"] == "canonical_pit_listed_issues"
    assert [item["pending_item_id"] for item in pending["items"] if item["side"] == "SELL"] == ["strategy-fd750c0ea2bcc16bd06a"]
    assert "PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT" not in evidence["reason_codes"]


def test_phase28_d46_93990_real_runtime_context_resolves_manifest_listed_info(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93990", quantity=600, price=90.0)
    canonical_listed_info = _canonical_listed_info("93990", market="スタンダード", product_category="021")
    existing = _write_existing_pending(
        runtime_root,
        items=(
            _pending_item(
                "strategy-a554f4e0fb84b6736786",
                "93990",
                "SELL",
                600,
                listed_info=canonical_listed_info,
                source_decision_type="SELL_EXIT",
                source_pm_decision_id="strategy-sell-exit-93990",
            ),
        ),
    )
    context = _historical_context(tmp_path)
    _write_strategy_input_manifest(tmp_path=tmp_path, business_date=BUSINESS_DATE, listed_infos=(canonical_listed_info,))

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="93990",
                quantity=600,
                reason="trend_and_opportunity_broken",
                source_decision="EXIT",
                source_decision_id="pm-2023-06-02-93990-exit",
            ),
        ),
        environment_capability_context=context,
    )

    order_plan = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "order_plan.json")
    generated_sell = next(item for item in order_plan["items"] if item["symbol"] == "93990" and item["side"] == "SELL")
    evidence = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "pending_sell_reconciliation_evidence.json")

    assert result.status == "PASS"
    assert result.pending_plan_id != existing.pending_plan_id
    assert "strategy_source_authority" not in context
    assert "strategy_input_manifest_path" not in context
    assert generated_sell["listed_info"]["market"] == "スタンダード"
    assert generated_sell["listed_info"]["product_category"] == "021"
    assert generated_sell["listed_info"]["security_type"] == "021"
    assert generated_sell["listed_info"]["listed_info_authority"] == "canonical_pit_listed_issues"
    assert generated_sell["listed_info"]["listed_info_row_id"] == "canonical_listed_issues:2023-01-18:93990"
    assert "PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT" not in evidence["reason_codes"]


def test_phase28_d46_59550_76470_real_runtime_context_consumes_canonical_authority(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(
        runtime_root,
        positions=(
            {"symbol": "59550", "quantity": 700, "price": 111.0},
            {"symbol": "76470", "quantity": 4100, "price": 26.0},
        ),
    )
    listed_59550 = _canonical_listed_info("59550", market="スタンダード", product_category="011")
    listed_76470 = _canonical_listed_info("76470", market="スタンダード", product_category="011")
    _write_existing_pending(
        runtime_root,
        items=(
            _pending_item("strategy-59550", "59550", "SELL", 700, listed_info=listed_59550, source_decision_type="SELL_EXIT"),
            _pending_item("strategy-76470", "76470", "SELL", 1300, listed_info=listed_76470, source_decision_type="SELL_REDUCE"),
        ),
    )
    context = _historical_context(tmp_path)
    _write_strategy_input_manifest(tmp_path=tmp_path, business_date=BUSINESS_DATE, listed_infos=(listed_59550, listed_76470))

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="59550",
                quantity=700,
                reason="hard_stop_current_return",
                source_decision="EXIT",
                source_decision_id="pm-2023-06-02-59550-exit",
            ),
            SellExitDecision(
                symbol="76470",
                quantity=0,
                reason="peak_drawdown_warning",
                source_decision="REDUCE",
                reduce_intensity="MEDIUM",
                source_decision_id="pm-2023-06-02-76470-reduce",
            ),
        ),
        environment_capability_context=context,
    )

    order_plan = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "order_plan.json")
    by_symbol = {item["symbol"]: item for item in order_plan["items"] if item["side"] == "SELL"}

    assert result.status == "PASS"
    assert by_symbol["59550"]["listed_info"]["listed_info_authority"] == "canonical_pit_listed_issues"
    assert by_symbol["59550"]["listed_info"]["market"] == "スタンダード"
    assert by_symbol["76470"]["listed_info"]["listed_info_authority"] == "canonical_pit_listed_issues"
    assert by_symbol["76470"]["listed_info"]["market"] == "スタンダード"


def test_phase28_d46_canonical_unavailable_preserves_pm_basic_fallback(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, symbol="93990", quantity=600, price=90.0)

    result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=(
            SellExitDecision(
                symbol="93990",
                quantity=600,
                reason="trend_and_opportunity_broken",
                source_decision="EXIT",
                source_decision_id="pm-2023-06-02-93990-exit",
            ),
        ),
        environment_capability_context=_historical_context(tmp_path),
    )

    order_plan = _load_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "order_plan.json")
    generated_sell = next(item for item in order_plan["items"] if item["symbol"] == "93990" and item["side"] == "SELL")

    assert result.status == "PASS"
    assert generated_sell["listed_info"] == {
        "code": "93990",
        "market": "東証",
        "product_category": "011",
        "security_type": "011",
        "current_listed": True,
    }


def test_phase28_d46_malformed_manifest_is_not_silently_treated_as_unavailable(tmp_path: Path) -> None:
    manifest_path = tmp_path / "reports" / "daily" / BUSINESS_DATE / "strategy" / "input_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{malformed", encoding="utf-8")

    try:
        _strategy_source_authority_context_for_sell_candidate(
            business_date=BUSINESS_DATE,
            environment_capability_context={"runtime_test_evidence_root": str(tmp_path / "reports")},
        )
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("malformed manifest must not be silently converted to empty authority")


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    ledger = root / "persistent_ledger"
    ledger.mkdir(parents=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (ledger / f"{name}.jsonl").write_text("", encoding="utf-8")
    _write_safety_decision(root)
    return root


def _write_current_state(
    root: Path,
    *,
    symbol: str = "",
    quantity: float = 0.0,
    price: float = 0.0,
    positions: tuple[dict, ...] | None = None,
) -> None:
    position_rows = positions or ({"symbol": symbol, "quantity": quantity, "price": price},)
    payload = {
        "schema_version": "1",
        "asset_state_id": "asset-phase28d3",
        "environment": "historical",
        "source": "fixture",
        "as_of": BUSINESS_DATE,
        "positions": [
            {
                "symbol": str(row["symbol"]),
                "quantity": float(row["quantity"]),
                "average_price": float(row["price"]),
                "market_value": float(row["quantity"]) * float(row["price"]),
                "source": "fixture",
                "as_of": BUSINESS_DATE,
            }
            for row in position_rows
        ],
        "cash": 1_000_000,
        "buying_power": 1_000_000,
        "market_value": sum(float(row["quantity"]) * float(row["price"]) for row in position_rows),
        "total_equity": 1_000_000 + sum(float(row["quantity"]) * float(row["price"]) for row in position_rows),
        "review_required": False,
        "production_equivalent": True,
        "current_state_confirmed_empty": False,
        "current_positions_unknown": False,
        "cash_unknown": False,
        "buying_power_unknown": False,
        "generated_from": ["fixture"],
        "created_at": BUSINESS_DATE,
        "updated_at": BUSINESS_DATE,
    }
    _write_json(root / "persistent_ledger" / "state.json", payload)


def _pending_item(
    pending_item_id: str,
    symbol: str,
    side: str,
    quantity: float,
    *,
    source_decision_type: str = "",
    source_pm_decision_id: str = "",
    listed_info: dict | None = None,
) -> PendingOrderItem:
    return PendingOrderItem(
        pending_item_id=pending_item_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type="MARKET",
        estimated_price=100,
        estimated_amount=quantity * 100,
        approved=True,
        state="READY",
        listed_info=listed_info,
        quantity_contract={"source_decision": source_decision_type} if source_decision_type else None,
        source_decision_type=source_decision_type,
        source_pm_decision_id=source_pm_decision_id,
        source_pm_business_date=BUSINESS_DATE,
        source_position_symbol=symbol,
    )


def _write_existing_pending(
    root: Path,
    *,
    items: tuple[PendingOrderItem, ...],
    state: PendingPlanState = PendingPlanState.APPROVED,
):
    order_plan_path = root / "fixtures" / "existing_order_plan.json"
    order_plan_path.parent.mkdir(parents=True, exist_ok=True)
    order_plan_path.write_text(json.dumps({"order_plan_id": "order-plan-existing"}), encoding="utf-8")
    pending = promote_order_plan_to_pending(
        order_plan_id="order-plan-existing",
        source_order_plan_path=str(order_plan_path),
        source_order_plan_hash="sha256:fixture",
        environment="historical",
        plan_created_date=BUSINESS_DATE,
        intended_submit_date=BUSINESS_DATE,
        target_session_date=BUSINESS_DATE,
        items=items,
    )
    pending = attach_approval_link(
        pending,
        approval_path=str(root / "fixtures" / "existing_approval.json"),
        approval_hash="sha256:approval",
        approval_status="APPROVED",
        approved_item_ids=tuple(item.pending_item_id for item in items),
        approval_expires_at=f"{BUSINESS_DATE}T15:00:00+09:00",
    )
    pending = replace(pending, state=state)
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    return pending


def _write_safety_decision(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "safety" / "latest_safety_decision.json",
        {
            "safety_decision_id": f"safety-{BUSINESS_DATE}",
            "business_date": BUSINESS_DATE,
            "mode": "historical",
            "status": "PASS",
            "decision": "NEUTRAL",
            "reason": "fixture",
            "review_required": False,
            "halt_runtime": False,
            "block_buy": False,
            "block_sell": False,
            "safety_policy_version": "fixture",
            "safety_source": "fixture",
            "action_permissions": {
                "sell_planning": "ALLOWED_FOR_REPLAY",
                "sell_submit": "ALLOWED_FOR_REPLAY",
            },
        },
    )


def _historical_context(tmp_path: Path) -> dict:
    return {
        "runtime_mode": "historical",
        "historical_replay": True,
        "broker_environment": "historical_simulated",
        "simulation": True,
        "broker_write": False,
        "external_delivery": False,
        "tachibana_demo_write": False,
        "tachibana_production_write": False,
        "submit_enabled": False,
        "runtime_test_run_id": "phase28-d3-focused",
        "runtime_test_profile_id": "focused",
        "runtime_test_evidence_root": str(tmp_path / "reports"),
    }


def _canonical_listed_info(symbol: str, *, market: str, product_category: str) -> dict:
    return {
        "code": symbol,
        "market": market,
        "product_category": product_category,
        "security_type": product_category,
        "current_listed": True,
        "listed_info_authority": "canonical_pit_listed_issues",
        "listed_info_source_hash": "sha256:fixture",
        "listed_info_source_artifact": "fixtures/listed_issues.parquet",
        "listed_info_business_date": BUSINESS_DATE,
        "listed_info_row_date": BUSINESS_DATE,
        "listed_info_resolution_status": "PASS",
    }


def _write_strategy_source_authority(*, tmp_path: Path, business_date: str, listed_info: dict) -> dict:
    return _write_strategy_source_authority_for_listed_infos(tmp_path=tmp_path, business_date=business_date, listed_infos=(listed_info,))


def _write_strategy_source_authority_for_listed_infos(*, tmp_path: Path, business_date: str, listed_infos: tuple[dict, ...]) -> dict:
    import hashlib

    import pandas as pd

    source_path = tmp_path / "authority" / "listed_issues.parquet"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "Date": business_date,
                "Code": listed_info["code"],
                "MktNm": listed_info["market"],
                "ProdCat": listed_info["product_category"],
            }
            for listed_info in listed_infos
        ]
    ).to_parquet(source_path, index=False)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    return {
        "authority": "historical_asof_source_authority",
        "status": "PASS",
        "business_date": business_date,
        "paths": {"listed_issues": str(source_path)},
        "source_records": {
            "listed_issues": {
                "business_date": business_date,
                "exists": True,
                "path": str(source_path),
                "pit_status": "PASS",
                "sha256": source_hash,
            }
        },
        "resolution_source": "phase28_d44_focused_fixture",
        "run_scoped_historical_authority_used": True,
    }


def _write_strategy_input_manifest(*, tmp_path: Path, business_date: str, listed_infos: tuple[dict, ...]) -> dict:
    authority = _write_strategy_source_authority_for_listed_infos(
        tmp_path=tmp_path,
        business_date=business_date,
        listed_infos=listed_infos,
    )
    manifest_path = tmp_path / "reports" / "daily" / business_date / "strategy" / "input_manifest.json"
    _write_json(
        manifest_path,
        {
            "business_date": business_date,
            "strategy_source_authority": authority,
        },
    )
    return authority


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
