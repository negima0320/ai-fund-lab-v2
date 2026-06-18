from __future__ import annotations

import pandas as pd

from ai_fund_lab_v2.paper_trading.daily_inference_runner import _build_candidate_rows, _build_opportunity_rows, prohibited_flags


def test_candidate_rank_uses_raw_rank_score_when_clipped_scores_tie() -> None:
    frame = pd.DataFrame(
        [
            _candidate_feature_row("30000", ret20=0.20, liquidity=1000),
            _candidate_feature_row("10000", ret20=0.60, liquidity=1000),
            _candidate_feature_row("20000", ret20=0.40, liquidity=1000),
        ]
    )

    rows = _build_candidate_rows(
        frame,
        decision_for="2026-06-16",
        data_until="2026-06-16",
        feature_schema_hash="test",
        source_data_refs={},
        limit=3,
    )

    assert [row["code"] for row in rows] == ["10000", "20000", "30000"]
    assert all(row["score_clipped"] == 100 for row in rows)
    assert len({row["rank_score"] for row in rows}) == 3
    assert rows[0]["rank_score"] > rows[1]["rank_score"] > rows[2]["rank_score"]
    assert all(row["score_saturation_flag"] for row in rows)


def test_candidate_tiebreak_uses_liquidity_then_code_only_when_rank_score_ties() -> None:
    frame = pd.DataFrame(
        [
            _candidate_feature_row("20000", ret20=0.30, liquidity=1000),
            _candidate_feature_row("10000", ret20=0.30, liquidity=5000),
            _candidate_feature_row("30000", ret20=0.30, liquidity=1000),
        ]
    )

    rows = _build_candidate_rows(
        frame,
        decision_for="2026-06-16",
        data_until="2026-06-16",
        feature_schema_hash="test",
        source_data_refs={},
        limit=3,
    )

    assert [row["code"] for row in rows] == ["10000", "20000", "30000"]
    assert rows[0]["rank_liquidity"] > rows[1]["rank_liquidity"]
    assert rows[1]["rank_score"] == rows[2]["rank_score"]


def test_opportunity_uses_candidate_rank_score_and_expected_edge_varies() -> None:
    candidate_rows = [
        {"code": "10000", "rank_score": 180.0, "score_clipped": 100, "is_current_listed": True, "has_current_name": True, "is_fresh_price": True, "is_allowed_product": True},
        {"code": "20000", "rank_score": 130.0, "score_clipped": 100, "is_current_listed": True, "has_current_name": True, "is_fresh_price": True, "is_allowed_product": True},
        {"code": "30000", "rank_score": 110.0, "score_clipped": 100, "is_current_listed": True, "has_current_name": True, "is_fresh_price": True, "is_allowed_product": True},
    ]
    frame = pd.DataFrame(
        [
            _opportunity_feature_row("10000", ret20=0.10),
            _opportunity_feature_row("20000", ret20=0.10),
            _opportunity_feature_row("30000", ret20=0.10),
        ]
    )

    rows = _build_opportunity_rows(
        frame,
        candidate_rows=candidate_rows,
        decision_for="2026-06-16",
        data_until="2026-06-16",
        feature_schema_hash="test",
        source_data_refs={},
        limit=3,
    )

    assert [row["code"] for row in rows] == ["10000", "20000", "30000"]
    assert [row["candidate_rank_score"] for row in rows] == [180.0, 130.0, 110.0]
    assert all(row["score_clipped"] == 100 for row in rows)
    assert len({row["rank_score"] for row in rows}) == 3
    assert len({row["expected_edge_score"] for row in rows}) == 3
    assert len({row["public_confidence_score"] for row in rows}) == 3


def test_prohibited_flags_remain_false() -> None:
    assert all(value is False for value in prohibited_flags().values())


def _candidate_feature_row(code: str, *, ret20: float, liquidity: float) -> dict[str, object]:
    return {
        "code": code,
        "universe_eligible": True,
        "price_momentum_return_5d": 0.10,
        "price_momentum_return_20d": ret20,
        "volume_momentum_ratio_5d": 1.0,
        "volatility_return_std_20d": 0.01,
        "trend_close_over_ma_20d": 0.20,
        "liquidity_avg_volume_20d": liquidity,
    }


def _opportunity_feature_row(code: str, *, ret20: float) -> dict[str, object]:
    return {
        "code": code,
        "feature__price_momentum_return_20d": ret20,
        "feature__volume_momentum_ratio_5d": 1.0,
        "feature__volatility_return_std_20d": 0.01,
        "feature__trend_close_over_ma_20d": 0.20,
        "feature__liquidity_avg_volume_20d": 1000,
    }
