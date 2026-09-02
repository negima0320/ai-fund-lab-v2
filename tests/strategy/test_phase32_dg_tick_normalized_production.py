from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ai_fund_lab_v2.runtime_v2.buy_ai.producer import _apply_candidate_pit_quality_surface
from ai_fund_lab_v2.strategy import buy_quality, input_materialization
from ai_fund_lab_v2.strategy.shadow_runtime import _supply_reentry_source_evidence
from ai_fund_lab_v2.strategy.strategy_intelligence import _entry_admission


BUSINESS_DATE = "2023-03-15"


def test_phase32_dg_93180_quantized_trend_materializes_caution(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", symbol="93180", closes=[2.0, 3.0] * 35)
    listed = _write_listed(tmp_path / "listed.parquet", symbol="93180", market="スタンダード", scale="-")

    result = input_materialization.produce_pm_technical_feature_artifact(
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_path=quotes,
        output_path=tmp_path / "technical.json",
        symbols=("93180",),
        listed_issues_path=listed,
        runtime_run_id="run-dg",
        as_of=f"{BUSINESS_DATE}T00:00:00+00:00",
    )
    row = result.payload["rows"][0]

    assert result.status == "PASS"
    assert row["single_tick_pct"] >= 0.30
    assert row["close_level_count_20d"] == 2
    assert row["tick_normalized_trend_state"] == "QUANTIZED_CAUTION"
    assert row["momentum_confidence_state"] == "LOW_CONFIDENCE_QUANTIZED"
    assert row["candidate_rank_tick_reliability"] == "LOW_CONFIDENCE"
    assert row["trend_robustness_authority"]["authority_type"] == "TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY"
    assert row["momentum_confidence_authority"]["authority_type"] == "QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY"
    assert row["hard_min_price_filter_used"] is False
    assert row["low_price_blacklist_used"] is False


def test_phase32_dg_candidate_rank_is_not_independent_confirmation_under_tick_caution() -> None:
    row = {
        **_surface_row("93180", score=0.99, rank=1),
        "tick_quantization_status": "PASS",
        "tick_normalized_trend_state": "QUANTIZED_CAUTION",
        "momentum_confidence_state": "LOW_CONFIDENCE_QUANTIZED",
        "close_level_diversity_state": "LOW_DIVERSITY",
        "candidate_rank_tick_reliability": "LOW_CONFIDENCE",
    }

    [candidate], evidence = _apply_candidate_pit_quality_surface([row], top_n=1)

    assert candidate["candidate_rank"] == 1
    assert candidate["candidate_pit_surface_state"] == "CAUTION_MOMENTUM_SURFACE"
    assert candidate["candidate_rank_tick_reliability"] == "LOW_CONFIDENCE"
    assert "candidate_rank_score_not_independent_confirmation_under_tick_caution" in candidate["candidate_pit_surface_reason_codes"]
    assert evidence["candidate_score_role"] == "CO_EQUAL_HYBRID_EVIDENCE"


def test_phase32_dg_buy_quality_caps_full_to_reduced_for_quantized_caution(tmp_path: Path) -> None:
    payload = _quality_payload(
        tmp_path,
        tick_fields={
            "tick_quantization_status": "PASS",
            "tick_normalized_trend_state": "QUANTIZED_CAUTION",
            "momentum_confidence_state": "LOW_CONFIDENCE_QUANTIZED",
            "close_level_diversity_state": "LOW_DIVERSITY",
            "candidate_rank_tick_reliability": "LOW_CONFIDENCE",
            "single_tick_pct": 0.33333333,
        },
    )
    decision = payload["decisions"][0]

    assert decision["quality_action"] == "REDUCED_ALLOCATION_ONLY"
    assert decision["quality_status"] == "PASS"
    assert decision["tick_normalized_trend_state"] == "QUANTIZED_CAUTION"
    assert decision["tick_quantization_validation"]["candidate_rank_confirmation_role"] == "SUPPORTING_ONLY_NOT_INDEPENDENT_CONFIRMATION"
    assert any(reason.startswith("tick_quantization_") for reason in decision["quality_reason_codes"])
    assert decision["quality_allocation_adjustment"] > 0


def test_phase32_dg_low_price_with_acceptable_tick_persistence_remains_eligible(tmp_path: Path) -> None:
    payload = _quality_payload(
        tmp_path,
        tick_fields={
            "tick_quantization_status": "PASS",
            "tick_normalized_trend_state": "ACCEPTABLE",
            "momentum_confidence_state": "MODERATE_CONFIDENCE",
            "close_level_diversity_state": "ADEQUATE_DIVERSITY",
            "candidate_rank_tick_reliability": "QUALIFIED",
            "single_tick_pct": 0.02857143,
            "tick_quantization_reason_codes": ["low_price_but_tick_persistent_trend"],
        },
    )
    decision = payload["decisions"][0]

    assert decision["quality_action"] in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY"}
    assert decision["quality_status"] == "PASS"
    assert decision["tick_normalized_trend_state"] == "ACCEPTABLE"
    assert "tick_quantization_prevents_full_allocation" not in decision["quality_reason_codes"]
    assert decision["tick_quantization_validation"]["hard_min_price_filter_used"] is False


def test_phase32_di_candidate_empty_tick_placeholders_do_not_shadow_valid_opportunity_tick_evidence(tmp_path: Path) -> None:
    tick_fields = {
        "tick_quantization_status": "PASS",
        "tick_normalized_trend_state": "ACCEPTABLE",
        "momentum_confidence_state": "MODERATE_CONFIDENCE",
        "close_level_diversity_state": "ADEQUATE_DIVERSITY",
        "candidate_rank_tick_reliability": "QUALIFIED",
        "single_tick_pct": 0.002,
        "minimum_tick_authority_status": "KNOWN",
        "minimum_tick_authority_hash": "sha256:" + "1" * 64,
        "trend_robustness_authority": {"authority_type": "TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY", "state": "ACCEPTABLE"},
        "momentum_confidence_authority": {"authority_type": "QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY", "state": "MODERATE_CONFIDENCE"},
        "tick_quantization_reason_codes": ["tick_normalized_trend_acceptable"],
    }
    payload = _quality_payload_custom(
        tmp_path,
        opportunity_rows=[_opportunity_row("94320", rank=1, score=0.99, tick_fields=tick_fields)],
        candidate_rows=[{**_candidate_row("94320"), **_empty_tick_placeholders()}],
    )
    decision = payload["decisions"][0]

    assert decision["tick_quantization_status"] == "PASS"
    assert decision["tick_normalized_trend_state"] == "ACCEPTABLE"
    assert decision["tick_quantization_validation"]["minimum_tick_authority_hash"] == "sha256:" + "1" * 64
    assert "tick_normalized_evidence_missing" not in decision["quality_reason_codes"]
    assert decision["quality_action"] != "REVIEW_REQUIRED"


def test_phase32_di_shadow_runtime_enriches_opportunity_with_full_tick_contract(tmp_path: Path) -> None:
    corporate_path = _write_json(
        tmp_path / "corporate.json",
        {
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "producer_result_status": "PASS",
            "known_no_event_symbols": ["94320"],
        },
    )
    technical_row = {
        "symbol": "94320",
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "minimum_tick": 1.0,
        "single_tick_pct": 0.002,
        "minimum_tick_authority_status": "KNOWN",
        "minimum_tick_authority_hash": "sha256:" + "2" * 64,
        "tick_quantization_status": "PASS",
        "tick_normalized_trend_state": "ROBUST",
        "momentum_confidence_state": "HIGH_CONFIDENCE",
        "close_level_diversity_state": "HIGH_DIVERSITY",
        "candidate_rank_tick_reliability": "RELIABLE",
        "trend_robustness_authority": {"authority_type": "TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY", "state": "ROBUST"},
        "momentum_confidence_authority": {"authority_type": "QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY", "state": "HIGH_CONFIDENCE"},
        "tick_quantization_reason_codes": ["tick_normalized_trend_robust"],
        "close_level_count_20d": 12,
        "ticks_traversed_20d": 8.0,
        "net_tick_move_20d": 7.0,
        "directional_tick_persistence_20d": 0.8,
    }

    supplied = _supply_reentry_source_evidence(
        business_date=BUSINESS_DATE,
        opportunity={"payload": {"rankings": [_opportunity_row("94320", rank=1, score=0.99)]}},
        technical_features={
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "source_ref": "technical_features.json",
            "source_hash": "sha256:" + "3" * 64,
            "rows": [technical_row],
        },
        corporate_event_path=corporate_path,
    )
    [row] = supplied["opportunity"]["rows"]

    assert supplied["evidence"]["technical_supplied_count"] == 1
    assert row["tick_quantization_status"] == "PASS"
    assert row["tick_normalized_trend_state"] == "ROBUST"
    assert row["momentum_confidence_state"] == "HIGH_CONFIDENCE"
    assert row["candidate_rank_tick_reliability"] == "RELIABLE"
    assert row["minimum_tick_authority_hash"] == "sha256:" + "2" * 64
    assert row["tick_quantization_reason_codes"] == ["tick_normalized_trend_robust"]


def test_phase32_di_first_day_fresh_run_shape_consumes_technical_tick_evidence(tmp_path: Path) -> None:
    technical_rows = []
    opportunity_rows = []
    candidate_rows = []
    for idx in range(50):
        symbol = f"{10000 + idx * 10}"
        trend = "QUANTIZED_CAUTION" if idx == 0 else "ACCEPTABLE"
        momentum = "LOW_CONFIDENCE_QUANTIZED" if idx == 0 else "MODERATE_CONFIDENCE"
        reliability = "LOW_CONFIDENCE" if idx == 0 else "QUALIFIED"
        technical_rows.append(
            {
                "symbol": symbol,
                "business_date": BUSINESS_DATE,
                "feature_date": BUSINESS_DATE,
                "minimum_tick": 1.0,
                "single_tick_pct": 0.03 if idx == 0 else 0.002,
                "minimum_tick_authority_status": "KNOWN",
                "minimum_tick_authority_hash": "sha256:" + f"{idx:064x}"[-64:],
                "tick_quantization_status": "PASS",
                "tick_normalized_trend_state": trend,
                "momentum_confidence_state": momentum,
                "close_level_diversity_state": "LOW_DIVERSITY" if idx == 0 else "ADEQUATE_DIVERSITY",
                "candidate_rank_tick_reliability": reliability,
                "trend_robustness_authority": {"authority_type": "TICK_NORMALIZED_TREND_ROBUSTNESS_AUTHORITY", "state": trend},
                "momentum_confidence_authority": {"authority_type": "QUANTIZATION_AWARE_MOMENTUM_CONFIDENCE_AUTHORITY", "state": momentum},
                "tick_quantization_reason_codes": ["tick_normalized_trend_quantized_caution" if idx == 0 else "tick_normalized_trend_acceptable"],
            }
        )
        opportunity_rows.append(_opportunity_row(symbol, rank=idx + 1, score=max(0.10, 0.95 - idx * 0.01)))
        candidate_rows.append({**_candidate_row(symbol), **_empty_tick_placeholders()})
    corporate_path = _write_json(tmp_path / "corporate.json", {"business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "producer_result_status": "PASS"})
    supplied = _supply_reentry_source_evidence(
        business_date=BUSINESS_DATE,
        opportunity={"payload": {"rankings": opportunity_rows}},
        technical_features={
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "source_ref": "technical_features.json",
            "source_hash": "sha256:" + "4" * 64,
            "rows": technical_rows,
        },
        corporate_event_path=corporate_path,
    )
    payload = _quality_payload_custom(
        tmp_path,
        opportunity_rows=list(supplied["opportunity"]["rows"]),
        candidate_rows=candidate_rows,
    )

    missing = [
        decision
        for decision in payload["decisions"]
        if "tick_normalized_evidence_missing" in decision["tick_quantization_validation"]["reason_codes"]
    ]
    assert len(payload["decisions"]) == 50
    assert missing == []
    assert {decision["tick_quantization_status"] for decision in payload["decisions"]} == {"PASS"}
    assert payload["decisions"][0]["tick_normalized_trend_state"] == "QUANTIZED_CAUTION"
    assert payload["decisions"][0]["quality_action"] == "REDUCED_ALLOCATION_ONLY"


def test_phase32_di_genuine_missing_tick_evidence_still_requires_review(tmp_path: Path) -> None:
    payload = _quality_payload_custom(
        tmp_path,
        opportunity_rows=[_opportunity_row("94320", rank=1, score=0.99)],
        candidate_rows=[{**_candidate_row("94320"), **_empty_tick_placeholders()}],
    )
    decision = payload["decisions"][0]

    assert decision["tick_quantization_status"] == "INSUFFICIENT_EVIDENCE"
    assert decision["quality_action"] == "REVIEW_REQUIRED"
    assert "tick_normalized_evidence_placeholder_without_authority" in decision["quality_reason_codes"]


@pytest.mark.parametrize("symbol", ["33500", "76470", "17570", "67400"])
def test_phase32_di_low_price_positive_controls_consume_valid_tick_evidence(tmp_path: Path, symbol: str) -> None:
    payload = _quality_payload_custom(
        tmp_path,
        opportunity_rows=[
            _opportunity_row(
                symbol,
                rank=1,
                score=0.99,
                tick_fields={
                    "tick_quantization_status": "PASS",
                    "tick_normalized_trend_state": "ACCEPTABLE",
                    "momentum_confidence_state": "MODERATE_CONFIDENCE",
                    "close_level_diversity_state": "ADEQUATE_DIVERSITY",
                    "candidate_rank_tick_reliability": "QUALIFIED",
                    "single_tick_pct": 0.025,
                    "minimum_tick_authority_status": "KNOWN",
                    "minimum_tick_authority_hash": "sha256:" + symbol.zfill(64)[-64:],
                    "tick_quantization_reason_codes": ["low_price_but_tick_persistent_trend"],
                },
            )
        ],
        candidate_rows=[{**_candidate_row(symbol), **_empty_tick_placeholders()}],
    )
    decision = payload["decisions"][0]

    assert decision["tick_quantization_status"] == "PASS"
    assert decision["tick_normalized_trend_state"] == "ACCEPTABLE"
    assert "tick_normalized_evidence_missing" not in decision["quality_reason_codes"]
    assert decision["quality_action"] in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY", "BUY_WAIT"}


@pytest.mark.parametrize("symbol", ["76920", "94320", "83060"])
def test_phase32_di_normal_price_controls_consume_valid_tick_evidence(tmp_path: Path, symbol: str) -> None:
    payload = _quality_payload_custom(
        tmp_path,
        opportunity_rows=[
            _opportunity_row(
                symbol,
                rank=1,
                score=0.99,
                tick_fields={
                    "tick_quantization_status": "PASS",
                    "tick_normalized_trend_state": "ROBUST",
                    "momentum_confidence_state": "HIGH_CONFIDENCE",
                    "close_level_diversity_state": "HIGH_DIVERSITY",
                    "candidate_rank_tick_reliability": "RELIABLE",
                    "single_tick_pct": 0.001,
                    "minimum_tick_authority_status": "KNOWN",
                    "minimum_tick_authority_hash": "sha256:" + symbol.zfill(64)[-64:],
                    "tick_quantization_reason_codes": ["tick_normalized_trend_robust"],
                },
            )
        ],
        candidate_rows=[{**_candidate_row(symbol), **_empty_tick_placeholders()}],
    )
    decision = payload["decisions"][0]

    assert decision["tick_quantization_status"] == "PASS"
    assert decision["tick_normalized_trend_state"] == "ROBUST"
    assert "tick_normalized_evidence_missing" not in decision["quality_reason_codes"]
    assert decision["quality_action"] in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY", "BUY_WAIT"}


def test_phase32_dg_entry_admission_reduces_quantized_caution_without_rejecting() -> None:
    entry = _entry_admission(
        symbol="93180",
        business_date=BUSINESS_DATE,
        eligibility={"status": "PASS"},
        continuation_quality={
            "status": "PASS",
            "evidence_sufficiency": "SUFFICIENT",
            "trend_health": {"state": "SUPPORTIVE"},
            "tick_normalized_trend_robustness": {"state": "QUANTIZED_CAUTION"},
            "quantization_aware_momentum_confidence": {"state": "LOW_CONFIDENCE_QUANTIZED"},
            "persistence": {"state": "SUPPORTIVE"},
            "acceleration_state": {"state": "ACCELERATING"},
            "exhaustion_risk": {"state": "MANAGEABLE"},
            "participation_quality": {"state": "SUPPORTIVE"},
            "relative_strength": {"state": "SUPPORTIVE"},
            "regime_compatibility": {"state": "OBSERVED"},
        },
        downside_risk={
            "evidence_sufficiency": "SUFFICIENT",
            "reversal_risk": {"state": "MANAGEABLE"},
            "volatility_risk": {"state": "OBSERVED"},
            "participation_risk": {"state": "MANAGEABLE"},
            "regime_risk": {"state": "OBSERVED"},
        },
        expected_edge={"calibration_status": "UNCALIBRATED"},
        lifecycle_context={"current_position_state": "NONE"},
        current_decision={"buy_quality_action": "FULL_ALLOCATION_ELIGIBLE"},
    )

    assert entry["admission_action"] == "BUY_NEW_REDUCED_ONLY"
    assert entry["entry_state"] == "CONTINUATION_WITH_CAUTION"
    assert "tick_quantization_caution_entry_reduced" in entry["reason_codes"]


def _quality_payload(tmp_path: Path, *, tick_fields: dict[str, object]) -> dict[str, object]:
    market_path = _write_json(
        tmp_path / "market.json",
        {
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "producer_result_status": "PASS",
            "confidence": 0.98,
            "breadth_value": 0.95,
            "trend_state": "BULL",
            "metrics": {"volatility_score": 0.05},
        },
    )
    policy_path = _write_json(
        tmp_path / "policy.json",
        {"business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "single_name_weight_cap": 0.20, "target_gross_exposure_ratio": 0.85},
    )
    corporate_path = _write_json(
        tmp_path / "corporate.json",
        {"business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "producer_result_status": "PASS"},
    )
    opportunity_rows = [
        {
            "symbol": "93180",
            "buy_rank": 1,
            "runtime_opportunity_score": 0.99,
            "expected_edge_score": 0.99,
            "confidence": 0.99,
            "downside_risk_score": 0.05,
            "opportunity_id": "opp-93180",
            "price_momentum_return_1d": 0.02,
            "price_momentum_return_3d": 0.04,
            "price_momentum_return_5d": 0.08,
            "price_momentum_return_20d": 0.24,
            "price_momentum_return_60d": 0.30,
            "volatility_return_std_20d": 0.02,
            "trend_close_over_ma_20d": 1.10,
            **tick_fields,
        },
        {"symbol": "11110", "buy_rank": 2, "runtime_opportunity_score": 0.40, "expected_edge_score": 0.40, "confidence": 0.80},
        {"symbol": "22220", "buy_rank": 3, "runtime_opportunity_score": 0.30, "expected_edge_score": 0.30, "confidence": 0.80},
    ]
    candidate_rows = [
        {
            "symbol": "93180",
            "candidate_id": "candidate-93180",
            "confidence": 0.99,
            "price_momentum_return_1d": 0.02,
            "price_momentum_return_3d": 0.04,
            "price_momentum_return_5d": 0.08,
            "price_momentum_return_20d": 0.24,
            "price_momentum_return_60d": 0.30,
            "volatility_return_std_20d": 0.02,
            "trend_close_over_ma_20d": 1.10,
            **tick_fields,
        }
    ]
    payload, _ = buy_quality.build_buy_quality_payload(
        business_date=BUSINESS_DATE,
        candidate_summary=_summary(tmp_path, "candidate", rows=candidate_rows),
        opportunity_summary=_summary(
            tmp_path,
            "opportunity",
            rows=opportunity_rows,
            summary={"accepted_generation_binding": {"status": "PASS"}, "calibration_applied": False},
        ),
        market_context_artifact_path=market_path,
        portfolio_policy_artifact_path=policy_path,
        current_portfolio_summary=_summary(tmp_path, "current", rows=[]),
        pending_summary=_summary(tmp_path, "pending", rows=[]),
        price_volatility_summary=_summary(tmp_path, "volatility", rows=[{"symbol": "93180", "liquidity_score": 0.98}]),
        corporate_event_artifact_path=corporate_path,
    )
    buy_quality.validate_buy_quality_artifact(payload)
    return payload


def _quality_payload_custom(
    tmp_path: Path,
    *,
    opportunity_rows: list[dict[str, object]],
    candidate_rows: list[dict[str, object]],
) -> dict[str, object]:
    market_path = _write_json(
        tmp_path / "market.json",
        {
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "producer_result_status": "PASS",
            "confidence": 0.98,
            "breadth_value": 0.95,
            "trend_state": "BULL",
            "metrics": {"volatility_score": 0.05},
        },
    )
    policy_path = _write_json(
        tmp_path / "policy.json",
        {"business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "single_name_weight_cap": 0.20, "target_gross_exposure_ratio": 0.85},
    )
    corporate_path = _write_json(
        tmp_path / "corporate.json",
        {"business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "producer_result_status": "PASS"},
    )
    payload, _ = buy_quality.build_buy_quality_payload(
        business_date=BUSINESS_DATE,
        candidate_summary=_summary(tmp_path, "candidate", rows=candidate_rows),
        opportunity_summary=_summary(
            tmp_path,
            "opportunity",
            rows=opportunity_rows,
            summary={"accepted_generation_binding": {"status": "PASS"}, "calibration_applied": False},
        ),
        market_context_artifact_path=market_path,
        portfolio_policy_artifact_path=policy_path,
        current_portfolio_summary=_summary(tmp_path, "current", rows=[]),
        pending_summary=_summary(tmp_path, "pending", rows=[]),
        price_volatility_summary=_summary(tmp_path, "volatility", rows=[{"symbol": row["symbol"], "liquidity_score": 0.98} for row in opportunity_rows]),
        corporate_event_artifact_path=corporate_path,
    )
    buy_quality.validate_buy_quality_artifact(payload)
    return payload


def _opportunity_row(symbol: str, *, rank: int, score: float, tick_fields: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "symbol": symbol,
        "buy_rank": rank,
        "runtime_opportunity_score": score,
        "expected_edge_score": score,
        "confidence": 0.99,
        "downside_risk_score": 0.05,
        "opportunity_id": f"opp-{symbol}",
        "price_momentum_return_1d": 0.02,
        "price_momentum_return_3d": 0.04,
        "price_momentum_return_5d": 0.08,
        "price_momentum_return_20d": 0.24,
        "price_momentum_return_60d": 0.30,
        "volatility_return_std_20d": 0.02,
        "trend_close_over_ma_20d": 1.10,
        **(tick_fields or {}),
    }


def _candidate_row(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "candidate_id": f"candidate-{symbol}",
        "confidence": 0.99,
        "price_momentum_return_1d": 0.02,
        "price_momentum_return_3d": 0.04,
        "price_momentum_return_5d": 0.08,
        "price_momentum_return_20d": 0.24,
        "price_momentum_return_60d": 0.30,
        "volatility_return_std_20d": 0.02,
        "trend_close_over_ma_20d": 1.10,
    }


def _empty_tick_placeholders() -> dict[str, object]:
    return {
        "tick_quantization_status": "",
        "tick_normalized_trend_state": "",
        "momentum_confidence_state": "",
        "candidate_rank_tick_reliability": "",
    }


def _surface_row(code: str, *, score: float, rank: int) -> dict[str, object]:
    return {
        "code": code,
        "candidate_score": score,
        "candidate_rank": rank,
        "candidate_reason": "high_candidate_score",
        "price_momentum_return_5d": 0.08,
        "price_momentum_return_20d": 0.15,
        "price_momentum_return_60d": 0.22,
        "trend_close_over_ma_20d": 1.03,
        "trend_ma_5_20_ratio": 1.02,
        "trend_ma_20_60_ratio": 1.01,
        "momentum_5d_vs_20d_delta": 0.02,
        "volume_momentum_ratio_5d": 1.4,
        "volatility_return_std_20d": 0.02,
        "liquidity_avg_volume_20d": 1_000_000,
    }


def _summary(tmp_path: Path, name: str, *, rows: list[dict[str, object]], summary: dict[str, object] | None = None) -> buy_quality.BuyQualitySourceSummary:
    path = _write_json(tmp_path / f"{name}.json", {"business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "rows": rows})
    return buy_quality.BuyQualitySourceSummary(
        status="PASS",
        business_date=BUSINESS_DATE,
        feature_date=BUSINESS_DATE,
        source_ref=str(path),
        source_hash="sha256:" + "a" * 64,
        rows=tuple(rows),
        summary=summary or {},
    )


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_quotes(path: Path, *, symbol: str, closes: list[float]) -> Path:
    dates = pd.bdate_range(end=BUSINESS_DATE, periods=len(closes))
    rows = [
        {"target_date": day.date().isoformat(), "code": symbol, "Close": close, "Volume": 1_000_000 + idx}
        for idx, (day, close) in enumerate(zip(dates, closes))
    ]
    pd.DataFrame(rows).to_parquet(path)
    return path


def _write_listed(path: Path, *, symbol: str, market: str, scale: str) -> Path:
    pd.DataFrame(
        [
            {
                "Date": BUSINESS_DATE,
                "Code": symbol,
                "ProdCat": "011",
                "MktNm": market,
                "ScaleCat": scale,
            }
        ]
    ).to_parquet(path)
    return path
