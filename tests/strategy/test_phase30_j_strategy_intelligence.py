from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.strategy_intelligence import (
    build_strategy_intelligence_payload,
    produce_strategy_intelligence_artifact,
    stable_payload_hash,
    validate_strategy_intelligence_artifact,
)


def test_phase30_j_strategy_intelligence_shadow_artifact_contract(tmp_path: Path) -> None:
    paths = _write_source_artifacts(tmp_path, business_date="2026-07-15", action="BUY_NEW")

    result = produce_strategy_intelligence_artifact(
        business_date="2026-07-15",
        candidate_summary=_candidate_summary("2026-07-15"),
        opportunity_summary=_opportunity_summary("2026-07-15"),
        current_summary=_current_summary("2026-07-15", held=False),
        technical_feature_summary=_technical_summary("2026-07-15"),
        price_volatility_summary=_price_volatility_summary("2026-07-15"),
        output_path=tmp_path / "strategy_intelligence.json",
        as_of="2026-07-15T00:00:00+00:00",
        **paths,
    )

    payload = json.loads(Path(result.artifact_path).read_text(encoding="utf-8"))
    assert result.status == "REVIEW_REQUIRED"
    assert validate_strategy_intelligence_artifact(payload)["status"] == "PASS"
    assert payload["schema_version"] == "strategy_intelligence.v1"
    assert payload["semantic_version"] == "1.4.0"
    assert payload["shadow_only"] is True
    assert payload["production_authority"] is False
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["shadow_output_connected_to_production_action_authority"] is False
    assert payload["new_ai_created"] is False
    assert payload["production_model_retrained"] is False
    assert payload["accepted_generation_changed"] is False
    assert payload["future_information_used"] is False
    assert payload["historical_outcome_used_as_runtime_input"] is False
    assert payload["test_result_used_as_strategy_input"] is False
    assert payload["historical_outcome_used_for_production_parameter_selection"] is False

    row = payload["symbol_intelligence"]["11110"]
    assert set(row) >= {
        "eligibility",
        "continuation_quality",
        "downside_risk",
        "expected_edge",
        "entry_admission",
        "selection_quality_comparator",
        "current_decision",
        "strategy_intelligence_interpretation",
        "profit_protection_evidence",
        "provenance",
    }
    assert row["expected_edge"]["edge_contract"] == "EXPECTED_EDGE_RESEARCH_CONTRACT"
    assert row["expected_edge"]["calibration_status"] == "UNCALIBRATED"
    assert row["expected_edge"]["shadow_only"] is True
    assert row["entry_admission"]["schema_version"] == "entry_admission.v1"
    assert row["entry_admission"]["future_information_used"] is False
    assert row["selection_quality_comparator"]["schema_version"] == "selection_quality_comparator.v1"
    assert row["selection_quality_comparator"]["tier"] == "REJECT"
    assert row["selection_quality_comparator"]["rank_score_role"] == "SUPPORTING_NOT_HARD_REJECTION_AUTHORITY"
    assert row["selection_quality_comparator"]["expected_edge_role"] == "UNCALIBRATED_SUPPORTING"
    assert payload["selection_quality_comparator_summary"]["candidate_quality_tier_distribution"]["REJECT"] == 1
    assert row["continuation_quality"]["relative_strength"]["state"] == "INSUFFICIENT_AUTHORITY"
    assert "explicit_relative_strength_authority" in row["continuation_quality"]["known_data_gaps"]
    assert row["downside_risk"]["event_uncertainty"]["state"] == "EVENT_COVERAGE_INCOMPLETE"
    assert row["eligibility"]["status"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["special_risk_coverage_state"] == "UNKNOWN"
    assert row["eligibility"]["special_risk_eligibility"] == "REVIEW_REQUIRED"
    assert row["eligibility"]["probabilistic_risk_not_automatic_reject"] is True
    assert row["current_decision"]["pm_action"] == "BUY_NEW"
    assert row["lifecycle_context"]["semantic_entry_type"] == "REENTRY"


def test_phase30_j_strategy_intelligence_blocks_future_feature_input(tmp_path: Path) -> None:
    paths = _write_source_artifacts(tmp_path, business_date="2026-07-15", action="BUY_NEW")

    payload, _evidence = build_strategy_intelligence_payload(
        business_date="2026-07-15",
        candidate_summary=_candidate_summary("2026-07-16"),
        opportunity_summary=_opportunity_summary("2026-07-15"),
        current_summary=_current_summary("2026-07-15", held=False),
        technical_feature_summary=_technical_summary("2026-07-15"),
        price_volatility_summary=_price_volatility_summary("2026-07-15"),
        as_of="2026-07-15T00:00:00+00:00",
        **paths,
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "candidate_future_feature_date" in payload["reason_codes"]
    assert payload["future_information_used"] is False
    assert payload["shadow_output_connected_to_production_action_authority"] is False


def test_phase30_j_strategy_intelligence_idempotent_payload_hash(tmp_path: Path) -> None:
    paths = _write_source_artifacts(tmp_path, business_date="2026-07-15", action="HOLD")
    kwargs = {
        "business_date": "2026-07-15",
        "candidate_summary": _candidate_summary("2026-07-15"),
        "opportunity_summary": _opportunity_summary("2026-07-15"),
        "current_summary": _current_summary("2026-07-15", held=True),
        "technical_feature_summary": _technical_summary("2026-07-15"),
        "price_volatility_summary": _price_volatility_summary("2026-07-15"),
        "as_of": "2026-07-15T00:00:00+00:00",
        **paths,
    }

    first, _ = build_strategy_intelligence_payload(**kwargs)
    second, _ = build_strategy_intelligence_payload(**kwargs)

    assert stable_payload_hash(first) == stable_payload_hash(second)
    assert first == second


def test_phase30_j_strategy_intelligence_multi_day_lifecycle_shadow_only(tmp_path: Path) -> None:
    actions = ("BUY_NEW", "BUY_WAIT", "ADD", "REENTRY", "HOLD", "REDUCE", "EXIT", "NO_ACTION")

    for index, action in enumerate(actions, start=1):
        business_date = f"2026-07-{index + 10:02d}"
        paths = _write_source_artifacts(tmp_path / business_date, business_date=business_date, action=action)
        payload, _ = build_strategy_intelligence_payload(
            business_date=business_date,
            candidate_summary=_candidate_summary(business_date),
            opportunity_summary=_opportunity_summary(business_date),
            current_summary=_current_summary(business_date, held=action in {"ADD", "HOLD", "REDUCE", "EXIT"}),
            technical_feature_summary=_technical_summary(business_date),
            price_volatility_summary=_price_volatility_summary(business_date),
            as_of=f"{business_date}T00:00:00+00:00",
            **paths,
        )

        row = payload["symbol_intelligence"]["11110"]
        assert payload["producer_result_status"] == "REVIEW_REQUIRED"
        assert payload["shadow_only"] is True
        assert payload["shadow_output_connected_to_production_action_authority"] is False
        assert row["current_decision"]["runtime_planning_action"] == action
        assert row["current_decision"]["current_decision_authority_unchanged"] is True
        assert row["strategy_intelligence_interpretation"]["actual_behavior_changed"] is False


def _write_source_artifacts(tmp_path: Path, *, business_date: str, action: str) -> dict[str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    market_context = _write_json(
        tmp_path / "market_context.json",
        {
            "schema_version": "market_context.v1",
            "business_date": business_date,
            "market_regime": "BULL",
            "artifact_hash": "market-hash",
        },
    )
    corporate_event = _write_json(
        tmp_path / "corporate_event.json",
        {
            "schema_version": "corporate_event.v1",
            "business_date": business_date,
            "coverage_status": "PARTIAL",
            "symbol_event_facts": {"11110": {"coverage_status": "MISSING", "event_facts": []}},
            "artifact_hash": "event-hash",
        },
    )
    buy_quality = _write_json(
        tmp_path / "buy_quality_decisions.json",
        {
            "schema_version": "buy_quality.v1",
            "business_date": business_date,
            "decisions": [{"security_code": "11110", "quality_action": action, "quality_band": "OBSERVED"}],
            "artifact_hash": "bq-hash",
        },
    )
    portfolio_construction = _write_json(
        tmp_path / "portfolio_construction.json",
        {
            "schema_version": "portfolio_construction.v1",
            "business_date": business_date,
            "portfolio_members": [
                {
                    "security_code": "11110",
                    "membership_intent": action,
                    "semantic_buy_type": "REENTRY",
                    "weight_intent": 0.1,
                    "runtime_opportunity_score": 0.72,
                }
            ],
            "artifact_hash": "pc-hash",
        },
    )
    position_sizing = _write_json(
        tmp_path / "position_sizing.json",
        {
            "schema_version": "position_sizing.v1",
            "business_date": business_date,
            "position_sizing": [{"security_code": "11110", "target_notional": 100000}],
            "artifact_hash": "ps-hash",
        },
    )
    position_management = _write_json(
        tmp_path / "position_management.json",
        {
            "schema_version": "position_management.v1",
            "business_date": business_date,
            "positions": [{"security_code": "11110", "action": action}],
            "artifact_hash": "pm-hash",
        },
    )
    runtime_planning = _write_json(
        tmp_path / "runtime_planning.json",
        {
            "schema_version": "runtime_planning.v1",
            "business_date": business_date,
            "plans": [{"security_code": "11110", "planning_intent": action, "planned_quantity": 100}],
            "artifact_hash": "rp-hash",
        },
    )
    return {
        "market_context_artifact_path": market_context,
        "corporate_event_artifact_path": corporate_event,
        "buy_quality_artifact_path": buy_quality,
        "portfolio_construction_artifact_path": portfolio_construction,
        "position_sizing_artifact_path": position_sizing,
        "position_management_artifact_path": position_management,
        "runtime_planning_artifact_path": runtime_planning,
    }


def _candidate_summary(business_date: str) -> dict:
    return {
        "status": "PASS",
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": "candidate_decisions.json",
        "source_hash": "candidate-hash",
        "rows": [{"security_code": "11110", "business_date": business_date, "feature_date": business_date}],
    }


def _opportunity_summary(business_date: str) -> dict:
    return {
        "status": "PASS",
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": "opportunity_rankings.json",
        "source_hash": "opportunity-hash",
        "rows": [{"security_code": "11110", "business_date": business_date, "runtime_opportunity_score": 0.72}],
    }


def _current_summary(business_date: str, *, held: bool) -> dict:
    return {
        "status": "PASS",
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": "Current",
        "source_hash": "current-hash",
        "rows": [
            {
                "security_code": "11110",
                "business_date": business_date,
                "quantity": 100 if held else 0,
                "average_price": 1000,
                "market_value": 100000 if held else 0,
            }
        ],
    }


def _technical_summary(business_date: str) -> dict:
    row = {
        "security_code": "11110",
        "business_date": business_date,
        "feature_date": business_date,
        "trend_close_over_ma_20d": 1.05,
        "trend_ma_5_20_ratio": 1.02,
        "price_momentum_return_1d": -0.01,
        "price_momentum_return_3d": 0.02,
        "price_momentum_return_5d": 0.03,
        "price_momentum_return_10d": 0.04,
        "price_momentum_return_20d": 0.09,
        "momentum_5d_vs_20d_delta": 0.01,
        "momentum_1d_vs_5d_delta": 0.02,
        "volume_momentum_ratio_5d": 1.2,
        "rolling_median_traded_value_20": 250000000,
        "reference_price": 1000,
        "volatility_return_std_20d": 0.02,
        "recent_move_volatility_z_1d": 0.5,
        "recent_move_volatility_z_3d": 0.8,
        "source_ref": "technical_features.json",
        "source_hash": "technical-hash",
    }
    return {
        "status": "PASS",
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": "technical_features.json",
        "source_hash": "technical-hash",
        "rows": [row],
    }


def _price_volatility_summary(business_date: str) -> dict:
    return {
        "status": "PASS",
        "business_date": business_date,
        "feature_date": business_date,
        "source_ref": "price_volatility.json",
        "source_hash": "vol-hash",
        "rows": [
            {
                "security_code": "11110",
                "business_date": business_date,
                "feature_date": business_date,
                "volatility_return_std_20d": 0.02,
                "reference_price": 1000,
                "source_ref": "price_volatility.json",
                "source_hash": "vol-hash",
            }
        ],
    }


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    return path
