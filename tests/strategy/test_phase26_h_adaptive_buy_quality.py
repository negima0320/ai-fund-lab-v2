from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy import buy_quality
from ai_fund_lab_v2.strategy import portfolio_construction
from ai_fund_lab_v2.strategy.shadow_runtime import _pc_summary
from ai_fund_lab_v2.strategy.position_sizing import (
    PositionSizingConfig,
    _raw_position,
    resolve_adaptive_buy_quality,
    resolve_allocation_quality_score,
)


BUSINESS_DATE = "2026-07-21"


def test_strong_market_strong_population_high_quality_is_full_allocation(tmp_path: Path) -> None:
    payload = _quality_payload(tmp_path, scores=[0.90, 0.24, 0.18, 0.10, -0.04], market="BULL", calibration_applied=True)
    top = _decision(payload, "1000")

    assert top["quality_action"] == "FULL_ALLOCATION_ELIGIBLE"
    assert top["quality_score"] >= 0.72
    assert top["fixed_rank_n_limit_used"] is False
    assert top["target_position_count_decision_consumer"] is False


def test_weak_market_weak_population_rank1_is_not_full_allocation(tmp_path: Path) -> None:
    payload = _quality_payload(tmp_path, scores=[0.03, 0.02, 0.01], market="BEAR", calibration_applied=True)
    top = _decision(payload, "1000")

    assert top["opportunity_buy_rank"] == 1
    assert top["quality_action"] != "FULL_ALLOCATION_ELIGIBLE"
    assert "rank1_weak_population_not_full" in top["quality_reason_codes"]


def test_weak_market_outlier_can_still_be_reduced_or_full_without_rank_gate(tmp_path: Path) -> None:
    payload = _quality_payload(tmp_path, scores=[1.8, 0.04, 0.01, -0.05, -0.12], market="BEAR", calibration_applied=True)
    top = _decision(payload, "1000")

    assert top["quality_action"] in {"REDUCED_ALLOCATION_ONLY", "FULL_ALLOCATION_ELIGIBLE"}
    assert "rank_not_used_as_fixed_n_gate" in top["quality_reason_codes"]


def test_strong_market_low_relative_quality_is_not_promoted_to_full(tmp_path: Path) -> None:
    payload = _quality_payload(tmp_path, scores=[0.90, 0.75, 0.63, 0.44, 0.03], market="BULL", calibration_applied=True)
    low = _decision(payload, "1004")

    assert low["quality_action"] != "FULL_ALLOCATION_ELIGIBLE"
    assert low["component_scores"]["relative_opportunity_quality"] < 0.55


def test_critical_evidence_missing_is_review_or_reject_not_default_full(tmp_path: Path) -> None:
    payload = _quality_payload(tmp_path, scores=[0.50, 0.20, 0.10], market="BULL", calibration_applied=True, binding_status="UNBOUND")
    top = _decision(payload, "1000")

    assert top["quality_action"] in {"REVIEW_REQUIRED", "REJECT"}
    assert top["quality_allocation_adjustment"] == 0.0
    assert top["component_statuses"]["signal_reliability"] == "REVIEW_REQUIRED"


def test_low_positive_raw_score_does_not_receive_normal_allocation(tmp_path: Path) -> None:
    payload = _quality_payload(tmp_path, scores=[0.02, 0.01, 0.005], market="BULL", calibration_applied=True)
    top = _decision(payload, "1000")

    assert top["runtime_opportunity_score"] > 0
    assert top["quality_action"] != "FULL_ALLOCATION_ELIGIBLE"


def test_position_sizing_consumes_adaptive_quality_without_fixed_notional_or_alias_conflict() -> None:
    full = _sized_row("2000", adjustment=1.0, score=0.82, action="FULL_ALLOCATION_ELIGIBLE")
    reduced = _sized_row("2001", adjustment=0.50, score=0.58, action="REDUCED_ALLOCATION_ONLY")
    full_position = _raw_position(full, config=_config(), base=0.10, max_weight=0.25, portfolio_value=1_000_000)
    reduced_position = _raw_position(reduced, config=_config(), base=0.10, max_weight=0.25, portfolio_value=1_000_000)

    assert full_position["target_notional"] == 100_000
    assert reduced_position["target_notional"] == 50_000
    assert full_position["legacy_allocation_quality_resolution"]["review_reason"] == "allocation_quality_score_missing"
    assert resolve_allocation_quality_score(full).source_field == ""


def test_missing_adaptive_quality_fails_closed_not_one_point_zero() -> None:
    result = resolve_adaptive_buy_quality({"security_code": "2002", "membership_intent": "ADD_CANDIDATE"})

    assert result["quality_action"] == "REVIEW_REQUIRED"
    assert result["quality_allocation_adjustment"] == 0.0
    assert result["review_reason"] == "adaptive_buy_quality_decision_missing"


def test_compound_sizing_scales_with_current_equity() -> None:
    row = _sized_row("2003", adjustment=0.75, score=0.66, action="REDUCED_ALLOCATION_ONLY")
    down = _raw_position(row, config=_config(), base=0.10, max_weight=0.25, portfolio_value=800_000)
    up = _raw_position(row, config=_config(), base=0.10, max_weight=0.25, portfolio_value=1_200_000)

    assert down["target_weight"] == up["target_weight"] == 0.075
    assert down["target_notional"] == 60_000
    assert up["target_notional"] == 90_000


def test_same_inputs_are_mode_parity_stable(tmp_path: Path) -> None:
    payloads = [
        _quality_payload(tmp_path / mode, scores=[0.70, 0.20, 0.10, -0.10, -0.20], market="NEUTRAL", calibration_applied=True)
        for mode in ("production", "demo", "historical")
    ]
    decision_tuples = [
        [
            (
                row["symbol"],
                row["quality_action"],
                row["quality_score"],
                row["quality_allocation_adjustment"],
                row["component_scores"],
            )
            for row in payload["decisions"]
        ]
        for payload in payloads
    ]

    assert decision_tuples[0] == decision_tuples[1] == decision_tuples[2]


def test_shadow_runtime_passes_buy_quality_decisions_to_portfolio_construction(tmp_path: Path) -> None:
    quality_payload = _quality_payload(tmp_path, scores=[0.90, 0.24, 0.18, 0.10, -0.04], market="BULL", calibration_applied=True)
    artifact_path = _write_json(tmp_path / "buy_quality_decisions.json", quality_payload)
    summary = _pc_summary(
        {
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "artifact_path": str(artifact_path),
            "artifact_hash": buy_quality.buy_quality_hash(quality_payload),
        },
        BUSINESS_DATE,
    )

    assert len(summary.rows) == quality_payload["decision_count"]

    member = {
        "security_code": "1000",
        "membership_intent": "ADD_CANDIDATE",
        "target_membership": True,
        "weight_intent": "INCREASE",
        "current_position": False,
        "reason_codes": ["candidate_eligible"],
    }
    [attached] = portfolio_construction._attach_buy_quality([member], summary)

    assert attached["quality_decision_id"]
    assert attached["quality_action"] == "FULL_ALLOCATION_ELIGIBLE"
    assert attached["membership_intent"] == "ADD_CANDIDATE"
    assert attached["target_membership"] is True
    assert attached["buy_quality_authority"]["authority_type"] == "ADAPTIVE_BUY_QUALITY_AUTHORITY"


def test_phase28_d51_buy_quality_preserves_listed_info_from_opportunity_and_candidate(tmp_path: Path) -> None:
    payload = _quality_payload(
        tmp_path,
        scores=[0.90, 0.24, 0.18, 0.10, -0.04],
        market="BULL",
        calibration_applied=True,
        listed_info_by_symbol={
            "1000": {
                "code": "1000",
                "market": "スタンダード",
                "product_category": "021",
                "security_type": "021",
                "current_listed": True,
            }
        },
    )
    decision = _decision(payload, "1000")

    assert decision["product_category"] == "021"
    assert decision["security_type"] == "021"
    assert decision["market_name"] == "スタンダード"
    assert decision["listed_info"] == {
        "code": "1000",
        "current_listed": True,
        "market": "スタンダード",
        "product_category": "021",
        "security_type": "021",
    }
    assert decision["quality_score"] > 0


def _quality_payload(
    tmp_path: Path,
    *,
    scores: list[float],
    market: str,
    calibration_applied: bool,
    binding_status: str = "PASS",
    listed_info_by_symbol: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    market_path = _write_json(
        tmp_path / "market_context.json",
        {
            "schema_version": "strategy_market_context.v1",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "producer_result_status": "PASS",
            "confidence": 0.95 if market == "BULL" else 0.55,
            "breadth_value": 0.90 if market == "BULL" else 0.35,
            "trend_state": market,
            "metrics": {"volatility_score": 0.12 if market == "BULL" else 0.68},
        },
    )
    policy_path = _write_json(
        tmp_path / "portfolio_policy.json",
        {
            "schema_version": "portfolio_policy.v1",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "producer_result_status": "PASS",
            "single_name_weight_cap": 0.20,
            "target_gross_exposure_ratio": 0.80,
        },
    )
    corporate_path = _write_json(
        tmp_path / "corporate_event.json",
        {"schema_version": "corporate_event.v1", "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "producer_result_status": "PASS"},
    )
    listed_info_by_symbol = listed_info_by_symbol or {}
    opportunity_rows = []
    for index, score in enumerate(scores):
        symbol = f"{1000 + index}"
        row = {
            "symbol": symbol,
            "buy_rank": index + 1,
            "expected_edge_score": score,
            "confidence": 0.96,
            "downside_risk_score": 0.18,
            "opportunity_id": f"opp-{index}",
        }
        if symbol in listed_info_by_symbol:
            row["listed_info"] = listed_info_by_symbol[symbol]
        opportunity_rows.append(row)
    candidate_rows = []
    for row in opportunity_rows:
        candidate = {"symbol": row["symbol"], "candidate_id": f"candidate-{row['symbol']}", "confidence": 0.95}
        if row["symbol"] in listed_info_by_symbol:
            candidate["listed_info"] = listed_info_by_symbol[row["symbol"]]
        candidate_rows.append(candidate)
    payload, _ = buy_quality.build_buy_quality_payload(
        business_date=BUSINESS_DATE,
        candidate_summary=_summary(tmp_path, "candidate", rows=candidate_rows),
        opportunity_summary=_summary(
            tmp_path,
            "opportunity",
            rows=opportunity_rows,
            summary={"accepted_generation_binding": {"status": binding_status}, "calibration_applied": calibration_applied},
        ),
        market_context_artifact_path=market_path,
        portfolio_policy_artifact_path=policy_path,
        current_portfolio_summary=_summary(tmp_path, "current", rows=[]),
        pending_summary=_summary(tmp_path, "pending", rows=[]),
        price_volatility_summary=_summary(
            tmp_path,
            "price_volatility",
            rows=[{"symbol": row["symbol"], "liquidity_score": 0.92} for row in opportunity_rows],
        ),
        corporate_event_artifact_path=corporate_path,
    )
    buy_quality.validate_buy_quality_artifact(payload)
    return payload


def _decision(payload: dict[str, object], symbol: str) -> dict[str, object]:
    return buy_quality.decision_by_symbol(payload)[symbol]


def _summary(tmp_path: Path, kind: str, *, rows: list[dict[str, object]], summary: dict[str, object] | None = None) -> buy_quality.BuyQualitySourceSummary:
    path = _write_json(tmp_path / f"{kind}.json", {"kind": kind, "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE, "rows": rows, "summary": summary or {}})
    return buy_quality.BuyQualitySourceSummary("PASS", BUSINESS_DATE, BUSINESS_DATE, str(path), buy_quality.stable_payload_hash({"kind": kind, "rows": rows}), tuple(rows), summary or {})


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sized_row(code: str, *, adjustment: float, score: float, action: str) -> dict[str, object]:
    return {
        "security_code": code,
        "position_reference": f"pc-{code}",
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "current_weight": 0.0,
        "confidence": 0.9,
        "opportunity_confidence": 0.9,
        "target_weight": 0.10,
        "target_weight_authority": {"authority_type": "TARGET_WEIGHT_AUTHORITY", "PIT_status": "PASS"},
        "target_weight_resolution": {"status": "PASS", "resolved_weight": 0.10, "review_reason": ""},
        "runtime_opportunity_score": 0.5,
        "runtime_opportunity_score_authority": {"prediction_semantics": "runtime_opportunity_score"},
        "quality_decision_id": f"bq-{code}",
        "quality_score": score,
        "quality_action": action,
        "quality_status": "PASS",
        "quality_band": "HIGH",
        "quality_reason_codes": [],
        "quality_policy_version": buy_quality.POLICY_VERSION,
        "quality_allocation_adjustment": adjustment,
        "component_scores": {},
        "component_statuses": {},
        "buy_quality_authority": {"authority_type": "ADAPTIVE_BUY_QUALITY_AUTHORITY", "producer": buy_quality.PRODUCER},
        "reference_price": 500.0,
        "reference_price_type": "planning_reference_close",
        "reference_price_date": BUSINESS_DATE,
        "reference_price_authority": {"PIT_status": "PASS"},
        "reference_price_resolution": {"status": "PASS", "resolved_price": 500.0, "review_reason": ""},
        "trading_unit": 100,
    }


def _config() -> PositionSizingConfig:
    return PositionSizingConfig(
        config_version="phase26_h_test",
        config_source="tests/strategy/test_phase26_h_adaptive_buy_quality.py",
        sizing_method="asset_proportional",
        opportunity_adjustment={"enabled": 0.0},
        volatility_adjustment={"enabled": False},
        pm_intent_adjustment={"NEW": 1.0, "HOLD": 1.0, "ADD": 1.0, "REDUCE": 1.0, "EXIT": 1.0, "UNRESOLVED": 0.0},
        minimum_meaningful_notional={"amount_jpy": 0.0, "tradable_unit": 100},
        strategy_maximum_position_weight=0.25,
        safety_concentration_reference="test_safety_cap",
    )
