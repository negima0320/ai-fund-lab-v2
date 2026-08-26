from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import activate_strategy_planning_authority
from ai_fund_lab_v2.strategy.shadow_runtime import generate_strategy_shadow_for_day


TARGET_RUN = "runtime-test-historical-extended-smoke-20260825T072702567342Z"
BUSINESS_DATE = "2022-11-28"
ANCHOR_SYMBOL = "93180"


def test_phase31_g110_actual_path_campaign_identity_reaches_runtime_planning(tmp_path: Path) -> None:
    source_run = Path("reports/runtime_tests/runs") / TARGET_RUN
    runtime_root = Path(".runtime")
    if not source_run.is_dir() or not runtime_root.is_dir():
        pytest.skip("G110 actual-path artifacts are not available in this checkout")
    if not (runtime_root / "persistent_ledger" / "state.json").is_file():
        pytest.skip("G110 runtime ledger state is not available in this checkout")

    run_dir = tmp_path / TARGET_RUN
    shutil.copytree(source_run, run_dir, ignore=shutil.ignore_patterns("*.parquet"))

    generate_strategy_shadow_for_day(
        run_dir=run_dir,
        runtime_root=runtime_root,
        run_id=TARGET_RUN,
        profile_id="historical-extended-smoke",
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        historical_evaluation_authority_path=str(source_run / "historical_evaluation_authority.json"),
        artifact_subdir="strategy_g110_actual_path",
        decision_timing="PRE_ACTION",
        authority_role="FORMAL_PLANNING_AUTHORITY_INPUT",
        materialization_role="G110_ACTUAL_PATH_REGRESSION",
    )

    strategy_dir = run_dir / "daily" / BUSINESS_DATE / "strategy_g110_actual_path"
    campaign_payload = _read_json(run_dir / "daily" / BUSINESS_DATE / "positions" / "position_campaigns.json")
    strategy_intelligence = _read_json(strategy_dir / "strategy_intelligence.json")
    position_management = _read_json(strategy_dir / "position_management.json")
    portfolio_construction = _read_json(strategy_dir / "portfolio_construction.json")
    position_sizing = _read_json(strategy_dir / "position_sizing.json")
    runtime_planning = _read_json(strategy_dir / "runtime_planning.json")

    campaigns = [
        row
        for row in campaign_payload.get("position_campaigns", [])
        if _symbol(row) == ANCHOR_SYMBOL and str(row.get("campaign_status") or "").upper() == "OPEN"
    ]
    assert len(campaigns) == 1
    assert campaigns[0]["opened_business_date"] == "2022-11-25"
    assert campaigns[0]["current_quantity"] == 700.0

    lifecycle = strategy_intelligence["symbol_intelligence"][ANCHOR_SYMBOL]["lifecycle_context"]
    assert strategy_intelligence["producer_identity"]["module"] == "ai_fund_lab_v2.strategy.strategy_intelligence"
    assert strategy_intelligence["producer_identity"]["artifact_function"] == "produce_strategy_intelligence_artifact"
    assert lifecycle["position_campaign_id"] == campaigns[0]["position_campaign_id"]
    assert lifecycle["campaign_opened_date"] == "2022-11-25"
    assert lifecycle["campaign_status"] == "OPEN"
    assert lifecycle["campaign_identity_authority_status"] == "COMPLETE"
    assert lifecycle["missing_campaign_authority_fields"] == []

    pm_row = _row_by_symbol(position_management.get("positions", []), ANCHOR_SYMBOL)
    hold = pm_row["strategy_intelligence_hold_worthiness_evidence"]
    assert pm_row["action"] == "HOLD"
    assert hold["campaign_identity_authority_status"] == "COMPLETE"
    assert "canonical_campaign_identity_missing" not in hold["reason_codes"]

    pc_row = _row_by_symbol(portfolio_construction.get("portfolio_members", []), ANCHOR_SYMBOL)
    assert pc_row["membership_intent"] == "RETAIN"
    assert pc_row["strategy_intelligence_campaign_identity_authority_status"] == "COMPLETE"

    ps_row = _row_by_symbol(position_sizing.get("positions", []), ANCHOR_SYMBOL)
    assert ps_row["sizing_status"] == "SIZED"

    plan = _row_by_symbol(runtime_planning.get("plans", []), ANCHOR_SYMBOL)
    assert plan["planning_intent"] == "NO_ACTION"
    assert plan["order_side_intent"] == "NONE"
    assert "strategy_plan_order_side_unresolved" not in json.dumps(plan)

    tmp_runtime = tmp_path / "runtime_root"
    (tmp_runtime / "persistent_ledger").mkdir(parents=True)
    shutil.copy2(runtime_root / "persistent_ledger" / "state.json", tmp_runtime / "persistent_ledger" / "state.json")
    result = activate_strategy_planning_authority(
        runtime_root=tmp_runtime,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        target_session_date=BUSINESS_DATE,
    )
    details = result.to_stage_details()
    assert details["status"] == "PASS"
    assert "strategy_plan_order_side_unresolved" not in details["reason_codes"]
    anchor_items = [
        item
        for item in details["lineage"].get("items", [])
        if _symbol(item) == ANCHOR_SYMBOL
    ]
    assert anchor_items
    assert all(item.get("planning_intent") == "NO_ACTION" for item in anchor_items)
    assert all(item.get("order_side_intent") == "NONE" for item in anchor_items)
    assert "strategy_plan_order_side_unresolved" not in json.dumps(anchor_items)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _row_by_symbol(rows: list[dict], symbol: str) -> dict:
    for row in rows:
        if _symbol(row) == symbol:
            return row
    raise AssertionError(f"symbol not found: {symbol}")


def _symbol(row: dict) -> str:
    return str(row.get("security_code") or row.get("symbol") or row.get("code") or "").strip()
