from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalExecutionSnapshotProvider
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from tests.runtime_v2.test_phase17_g_historical_submit_guard_and_fill import (
    BUSINESS_DATE,
    SYMBOL,
    _historical_context,
    _pending,
    _runtime_fixture,
    _write_current,
    _write_market_data,
    _write_policy,
    _write_safety,
)


def test_phase17_bv10_historical_full_sell_execution_projects_position_and_cash(tmp_path: Path) -> None:
    runtime_root, policy_path = _sell_fixture(tmp_path, owned_quantity=100.0, sell_quantity=100.0)

    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=_adapter(tmp_path, runtime_root),
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )
    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        snapshot_provider=HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=BUSINESS_DATE),
    )

    state = json.loads((runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8"))
    assert submit.status == "PASS"
    assert result.status == "PASS"
    assert result.fill_count == 1
    assert result.ledger_orders_appended == 1
    assert result.ledger_executions_appended == 1
    assert result.ledger_positions_appended == 1
    assert result.ledger_cash_appended == 1
    assert result.projected_position_count == 0
    assert state["positions"] == []
    assert state["cash"] == 1_300_000.0
    assert state["buying_power"] == 1_300_000.0
    assert result.reconcile_status == "PASS"
def test_phase17_bv10_historical_buy_execution_regression(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY")
    _attach_positive_opportunity_evidence(runtime_root)
    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )
    result = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        snapshot_provider=HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=BUSINESS_DATE),
    )

    assert submit.status == "PASS"
    assert result.status == "PASS"
    assert result.fill_count == 1
    assert result.projected_position_count == 1
    assert result.reconcile_status == "PASS"


def _attach_positive_opportunity_evidence(runtime_root: Path) -> None:
    path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for item in payload.get("items") or []:
        if str(item.get("side") or "").upper() != "BUY":
            continue
        listed_info = dict(item.get("listed_info") or {})
        listed_info.update(
            {
                "opportunity_buy_eligibility_status": "PASS",
                "opportunity_buy_eligibility": "BUY_ELIGIBLE",
                "opportunity_expected_edge_score": 0.10,
                "opportunity_expected_return": 0.10,
                "opportunity_no_buy_reason": "",
                "opportunity_buy_rank": 1,
                "opportunity_business_date": BUSINESS_DATE,
                "opportunity_feature_date": BUSINESS_DATE,
                "opportunity_eligibility_policy_version": "runtime_v2_opportunity_buy_eligibility_v1",
                "opportunity_eligibility_reason": "opportunity_positive_expected_edge",
            }
        )
        item["listed_info"] = listed_info
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _sell_fixture(tmp_path: Path, *, owned_quantity: float, sell_quantity: float) -> tuple[Path, Path]:
    runtime_root = tmp_path / ".runtime"
    runtime_root.mkdir()
    _write_market_data(tmp_path)
    policy_path = runtime_root / "runtime_state" / "policy" / "capital_deployment.json"
    _write_policy(policy_path)
    _write_safety(runtime_root, decision="ALLOW")
    _write_current(runtime_root, side="SELL")
    state_path = runtime_root / "persistent_ledger" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["positions"][0]["quantity"] = owned_quantity
    state["positions"][0]["average_price"] = 2500.0
    state["positions"][0]["market_value"] = owned_quantity * 3000.0
    state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")

    pending = _pending("historical", side="SELL", policy_path=policy_path)
    item = replace(
        pending.items[0],
        quantity=float(sell_quantity),
        estimated_amount=float(sell_quantity) * 3000.0,
        capital_allocation_amount=float(sell_quantity) * 3000.0,
        listed_info={
            "code": SYMBOL,
            "market": "東証",
            "product_category": "011",
            "security_type": "011",
            "current_listed": True,
            "trading_unit": 100,
        },
    )
    approval = replace(
        pending.approval,
        approved_order_conditions={
            "item-1": {
                **pending.approval.approved_order_conditions["item-1"],
                "quantity": float(sell_quantity),
            }
        },
    )
    pending = replace(pending, items=(item,), approval=approval)
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)
    return runtime_root, policy_path


def _adapter(tmp_path: Path, runtime_root: Path):
    from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalSubmitAdapter
    from tests.runtime_v2.test_phase17_g_historical_submit_guard_and_fill import EVALUATION_TIME

    return HistoricalSubmitAdapter(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
        pit_manifest_path=tmp_path / "pit_manifest.json",
        ohlcv_path=tmp_path / "ohlcv.parquet",
        listed_issues_path=tmp_path / "listed.parquet",
        raw_ohlcv_path=tmp_path / "raw_ohlcv.parquet",
    )
