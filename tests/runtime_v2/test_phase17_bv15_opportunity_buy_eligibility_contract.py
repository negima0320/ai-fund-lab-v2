import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.broker_adapter.fake_demo_submit import FakeRuntimeV2DemoSubmitAdapter
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import evaluate_opportunity_buy_eligibility
from ai_fund_lab_v2.runtime_v2.buy_ai.producer import load_ai_planning_signals_from_opportunity_artifact
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import run_morning_ai_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase15i_submit_guard_buy_sell_policy_manifest import (
    _approved_pending,
    _item,
    _position,
    _runtime_root,
    _write_broker_positions_snapshot,
    _write_current_state,
    _write_policy,
)
from tests.runtime_v2.test_phase17_w_historical_morning_capability import (
    _feature_root,
    _historical_context,
    _historical_safety,
    _runtime_root as _historical_runtime_root,
)


BUSINESS_DATE = "2026-07-01"
FEATURE_DATE = "2026-06-30"


def test_phase17_bv15_resolver_blocks_36810_negative_edge_top5() -> None:
    artifact = _opportunity_payload(
        [
            _opportunity_row(
                "36810",
                expected_edge=-0.06934237,
                no_buy_reason="non_positive_expected_edge_score",
                buy_rank=2,
                reason="opportunity_top5|candidate_prior_available",
            )
        ]
    )

    result = evaluate_opportunity_buy_eligibility(
        symbol="36810",
        business_date=BUSINESS_DATE,
        feature_date=FEATURE_DATE,
        opportunity_payload=artifact,
    )

    assert result.status == "BLOCKED"
    assert result.buy_eligibility == "BUY_INELIGIBLE"
    assert result.reason_code == "non_positive_expected_edge_score"
    assert result.buy_rank == 2
    assert result.is_top5 is True


def test_phase17_bv15_loader_does_not_treat_rank_as_buy_permission(tmp_path: Path) -> None:
    path = _write_opportunity_artifact(
        tmp_path / "opportunity_rankings.json",
        [
            _opportunity_row("36810", expected_edge=-0.06934237, no_buy_reason="non_positive_expected_edge_score", buy_rank=2),
            _opportunity_row("7203", expected_edge=0.12, no_buy_reason="", buy_rank=6),
        ],
    )

    signals = load_ai_planning_signals_from_opportunity_artifact(path, selected_rank_limit=10)

    assert [signal.symbol for signal in signals] == ["7203"]
def test_phase17_bv15_submit_blocks_negative_opportunity_before_broker(tmp_path: Path) -> None:
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
            "opportunity_expected_edge_score": -0.06934237,
            "opportunity_expected_return": -0.06934237,
            "opportunity_no_buy_reason": "non_positive_expected_edge_score",
            "opportunity_buy_rank": 2,
            "opportunity_business_date": "2026-07-09",
            "opportunity_feature_date": "2026-07-09",
        },
    )
    from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan

    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", _approved_pending((item,), policy_path=policy_path))

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
    assert evidence["violated_policy"] == "opportunity_buy_eligibility"
    assert evidence["opportunity_buy_eligibility"] == "BUY_INELIGIBLE"


def test_phase17_bv15_submit_blocks_opportunity_hash_mismatch(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    _write_current_state(runtime_root, positions=[], cash=1_000_000, market_value=0)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    opportunity_path = _write_opportunity_artifact(
        tmp_path / "opportunity_rankings.json",
        [_opportunity_row("7203", expected_edge=0.10, no_buy_reason="", buy_rank=1, business_date="2026-07-09", feature_date="2026-07-09")],
    )
    item = replace(
        _item(
            pending_item_id="buy-7203",
            symbol="7203",
            side="BUY",
            quantity=100,
            estimated_price=1000,
            estimated_amount=100_000,
        ),
        listed_info={
            "code": "7203",
            "current_listed": True,
            "opportunity_expected_edge_score": 0.10,
            "opportunity_expected_return": 0.10,
            "opportunity_no_buy_reason": "",
            "opportunity_buy_rank": 1,
            "opportunity_artifact_path": str(opportunity_path),
            "opportunity_artifact_hash": "sha256:not-the-current-hash",
            "opportunity_business_date": "2026-07-09",
            "opportunity_feature_date": "2026-07-09",
        },
    )
    from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan

    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", _approved_pending((item,), policy_path=policy_path))

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
    assert evidence["violated_policy"] == "opportunity_buy_eligibility"
    assert evidence["opportunity_buy_eligibility_reason_code"] == "opportunity_artifact_hash_mismatch"


def test_phase17_bv15_sell_submit_ignores_missing_opportunity_buy_evidence(tmp_path: Path) -> None:
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
        listed_info={"code": "36810", "current_listed": True},
    )
    from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan

    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", _approved_pending((item,), policy_path=policy_path))

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
    assert evidence["violated_policy"] != "opportunity_buy_eligibility"
    assert "opportunity_buy_eligibility" not in evidence


def _opportunity_row(
    symbol: str,
    *,
    expected_edge: float,
    no_buy_reason: str,
    buy_rank: int,
    reason: str = "opportunity_ranked",
    business_date: str = BUSINESS_DATE,
    feature_date: str = FEATURE_DATE,
) -> dict:
    return {
        "schema_name": "runtime_v2_buy_opportunity_ranking",
        "artifact_role": "BUY_OPPORTUNITY_RANKING",
        "business_date": business_date,
        "target_date": feature_date,
        "feature_date": feature_date,
        "runtime_id": "runtime-v2-buy-ai-bv15-fixture",
        "model_version": "fixture",
        "code": symbol,
        "symbol": symbol,
        "expected_edge_score": expected_edge,
        "opportunity_score": expected_edge,
        "buy_rank": buy_rank,
        "rank": buy_rank,
        "expected_return": expected_edge,
        "downside_risk_score": 0.67089625,
        "no_buy_reason": no_buy_reason,
        "is_top5": buy_rank <= 5,
        "reason": reason,
    }


def _opportunity_payload(rows: list[dict], *, business_date: str = BUSINESS_DATE, feature_date: str = FEATURE_DATE) -> dict:
    return {
        "schema_name": "runtime_v2_buy_opportunity_ranking",
        "schema_version": "runtime_v2_opportunity_ranking_v1",
        "artifact_role": "BUY_OPPORTUNITY_RANKING",
        "producer": "Runtime v2 BUY AI Producer",
        "producer_version": "candidate_opportunity_ai_regular_path_v1",
        "business_date": business_date,
        "runtime_id": "runtime-v2-buy-ai-bv15-fixture",
        "model_version": "fixture",
        "feature_date": feature_date,
        "generated_at": "2026-07-01T00:00:00+00:00",
        "status": "PASS",
        "reason": "",
        "ranking_count": len(rows),
        "rankings": rows,
    }


def _write_opportunity_artifact(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _opportunity_payload(rows)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _append_price_rows(runtime_root: Path, *, symbols: tuple[str, ...]) -> None:
    price_path = runtime_root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    rows = pd.read_parquet(price_path)
    additions = pd.DataFrame(
        [{"Code": symbol, "Date": FEATURE_DATE, "Close": 1000.0, "PriceSource": "fixture"} for symbol in symbols]
    )
    pd.concat([rows, additions], ignore_index=True).to_parquet(price_path, index=False)
