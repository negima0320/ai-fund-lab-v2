import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
    rebuild_snapshot_index,
    write_listed_issues_snapshot,
)
from ai_fund_lab_v2.runtime_v2.market_status.buy_eligibility import evaluate_buy_eligibility
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import run_morning_ai_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase15i_submit_guard_buy_sell_policy_manifest import (
    _approved_pending,
    _item,
    _position,
    _runtime_root,
    _write_broker_positions_snapshot,
    _write_current_state,
    _write_policy,
)
from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase17_w_historical_morning_capability import (
    _feature_root,
    _historical_context,
    _historical_safety,
    _runtime_root as _historical_runtime_root,
)
from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter


def test_phase17_bv14_buy_eligibility_blocks_explicit_delisting_status() -> None:
    result = evaluate_buy_eligibility(
        symbol="36810",
        business_date="2026-06-29",
        mode="historical",
        listed_info={
            "code": "36810",
            "current_listed": True,
            "market_status": "DELISTING_SCHEDULED",
            "scheduled_delisting_date": "2026-07-01",
        },
    )

    assert result.status == "BLOCKED"
    assert result.buy_eligibility == "INELIGIBLE"
    assert result.reason_code.startswith("market_status_buy_ineligible")


def test_phase17_bv14_buy_eligibility_uses_point_in_time_snapshot_without_lookahead(tmp_path: Path) -> None:
    snapshot_0630 = tmp_path / "listed_0630.parquet"
    snapshot_0701 = tmp_path / "listed_0701.parquet"
    pd.DataFrame([{"Date": "2026-06-30", "Code": "36810", "MktNm": "プライム", "ProdCat": "011"}]).to_parquet(
        snapshot_0630,
        index=False,
    )
    pd.DataFrame([{"Date": "2026-07-01", "Code": "33500", "MktNm": "プライム", "ProdCat": "011"}]).to_parquet(
        snapshot_0701,
        index=False,
    )

    before_delisting = evaluate_buy_eligibility(
        symbol="36810",
        business_date="2026-06-30",
        mode="historical",
        listed_snapshot_path=snapshot_0630,
    )
    after_delisting = evaluate_buy_eligibility(
        symbol="36810",
        business_date="2026-07-01",
        mode="historical",
        listed_snapshot_path=snapshot_0701,
    )

    assert before_delisting.status == "PASS"
    assert before_delisting.reason_code == "market_status_buy_eligible"
    assert after_delisting.status == "BLOCKED"
    assert after_delisting.reason_code == "symbol_not_listed_as_of_business_date"


def test_phase17_bv14_morning_filters_buy_candidate_not_listed_in_pit_snapshot(tmp_path: Path) -> None:
    runtime_root = _historical_runtime_root(tmp_path / ".runtime")
    feature_root = _feature_root(runtime_root, "2026-06-30")
    price_path = runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    price_rows = pd.read_parquet(price_path)
    pd.concat(
        [
            price_rows,
            pd.DataFrame([{"Code": "36810", "Date": "2026-06-30", "Close": 1000.0, "PriceSource": "fixture"}]),
        ],
        ignore_index=True,
    ).to_parquet(price_path, index=False)
    snapshot_root = runtime_root / "operations" / "jquants" / "historical_snapshots" / "listed_issues"
    write_listed_issues_snapshot(
        snapshot_root=snapshot_root,
        requested_date="2026-06-30",
        fetched_at="2026-06-30T15:30:00+09:00",
        records=[{"Date": "2026-06-30", "Code": "7203", "MktNm": "プライム", "ProdCat": "011"}],
    )
    rebuild_snapshot_index(snapshot_root)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")

    result = run_morning_ai_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-01",
        mode="historical",
        feature_root=feature_root,
        feature_date="2026-06-30",
        capital_deployment_policy_path=policy_path,
        ai_signals=(
            AIPlanningSignal("signal-36810", "36810", "BUY", 1, 0.9, "fixture", "fixture_ai"),
            AIPlanningSignal("signal-7203", "7203", "BUY", 2, 0.8, "fixture", "fixture_ai"),
        ),
        safety_decision=replace(_historical_safety(), business_date="2026-07-01"),
        environment_capability_context=_historical_context(tmp_path),
    )

    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    order_plan = json.loads(Path(result.order_plan_artifact_path).read_text(encoding="utf-8"))
    assert result.status == "PASS"
    assert result.selected_symbols == ("7203",)
    assert result.buy_eligibility_filtered_count == 1
    assert pending["items"][0]["listed_info"]["buy_eligibility"] == "ELIGIBLE"
    assert order_plan["buy_eligibility_contract"]["filtered_count"] == 1


def test_phase17_bv14_submit_blocks_buy_ineligible_market_status_before_broker(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    item = replace(
        _item(
            pending_item_id="buy-36810",
            symbol="36810",
            side="BUY",
            quantity=100,
            estimated_price=1000,
            estimated_amount=100_000,
        ),
        listed_info={
            "code": "36810",
            "current_listed": True,
            "market_status": "DELISTING_SCHEDULED",
            "scheduled_delisting_date": "2026-07-01",
        },
    )
    pending = _approved_pending((item,), policy_path=policy_path)
    from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan

    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert result.status == "REVIEW_REQUIRED"
    assert result.submitted_count == 0
    assert evidence["guard_decision"] == "BLOCKED"
    assert evidence["violated_policy"] == "buy_market_status_eligibility"
    assert evidence["should_have_been_blocked_at_planning"] is True
    assert evidence["buy_eligibility"] == "INELIGIBLE"


def test_phase17_bv14_sell_is_not_blocked_by_buy_eligibility_guard(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(
        runtime_root,
        positions=[_position("36810", quantity=100, price=1000)],
        cash=1_000_000,
        market_value=100_000,
    )
    _write_broker_positions_snapshot(runtime_root, symbol="36810", quantity=100, available_quantity=100)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    item = replace(
        _item(
            pending_item_id="sell-36810",
            symbol="36810",
            side="SELL",
            quantity=100,
            estimated_price=1000,
            estimated_amount=100_000,
        ),
        listed_info={
            "code": "36810",
            "current_listed": False,
            "market_status": "DELISTED",
        },
    )
    pending = _approved_pending((item,), policy_path=policy_path)
    from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan

    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    result = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date="2026-07-09",
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        adapter=FakeRuntimeV2DemoSubmitAdapter(),
        capital_deployment_policy_path=policy_path,
    )

    evidence = result.submit_guard_item_evidence[0]
    assert evidence["side"] == "SELL"
    assert "buy_eligibility" not in evidence
    assert evidence["violated_policy"] != "buy_market_status_eligibility"
