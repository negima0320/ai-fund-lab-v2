from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy.portfolio_construction import (
    PortfolioConstructionSourceSummary,
    build_portfolio_construction_payload,
)
from ai_fund_lab_v2.strategy.position_management import build_position_management_payload
from ai_fund_lab_v2.strategy.strategy_intelligence import produce_strategy_intelligence_artifact

from tests.strategy.test_phase22_d_position_management import (
    _generation,
    _summary as _pm_summary,
    _write_corporate_event as _write_pm_corporate_event,
    _write_market_context as _write_pm_market_context,
    _write_portfolio_policy as _write_pm_portfolio_policy,
)
from tests.strategy.test_phase22_e_portfolio_construction import (
    _source_summary as _pc_source_summary,
    _write_corporate_event,
    _write_json,
    _write_market_context,
    _write_portfolio_policy,
    _write_position_management,
)


BUSINESS_DATE = "2026-07-15"


def test_phase30_p_strategy_intelligence_production_artifact_is_consumer_eligible(tmp_path: Path) -> None:
    path = _write_strategy_intelligence(tmp_path, cq_complete=True)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["runtime_consumer_eligibility"] == "ELIGIBLE"
    assert payload["production_consumer_connected"] is True
    assert payload["production_authority"] is False
    assert payload["shadow_only"] is False
    assert "proposed_decision_if_authorized" not in payload["symbol_intelligence"]["11110"]
    assert payload["symbol_intelligence"]["11110"]["expected_edge"]["calibration_status"] == "UNCALIBRATED"
    assert payload["symbol_intelligence"]["11110"]["expected_edge"]["economic_units_available"] is False
    assert payload["symbol_intelligence"]["11110"]["expected_edge"]["shadow_only"] is False
    assert payload["symbol_intelligence"]["11110"]["strategy_intelligence_interpretation"]["shadow_only"] is False
    assert payload["future_information_used"] is False
    assert payload["historical_outcome_used_for_production_parameter_selection"] is False


def test_phase30_p_portfolio_construction_uses_si_cq_for_buy_wait(tmp_path: Path) -> None:
    si_path = _write_strategy_intelligence(tmp_path, cq_complete=False)
    buy_quality = _pc_source_summary(
        tmp_path,
        "buy_quality",
        rows=[
            {
                "security_code": "11110",
                "quality_action": "FULL_ALLOCATION_ELIGIBLE",
                "quality_score": 0.90,
                "quality_status": "PASS",
            }
        ],
    )

    payload, _ = build_portfolio_construction_payload(
        business_date=BUSINESS_DATE,
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, rows=[], producer_status="PASS"),
        candidate_summary=_pc_summary(tmp_path, "candidate", [{"security_code": "11110", "candidate_id": "candidate-11110"}]),
        opportunity_summary=_pc_summary(
            tmp_path,
            "opportunity",
            [{"security_code": "11110", "opportunity_id": "opportunity-11110", "rank": 1, "runtime_opportunity_score": 0.82}],
        ),
        current_portfolio_summary=_pc_summary(tmp_path, "current", []),
        pending_summary=_pc_summary(tmp_path, "pending", []),
        policy_config_summary=_pc_summary(tmp_path, "policy_config", []),
        buy_quality_summary=buy_quality,
        strategy_intelligence_artifact_path=si_path,
    )

    member = payload["portfolio_members"][0]
    assert member["strategy_intelligence_consumer_status"] == "CONNECTED"
    assert member["legacy_buy_quality_action"] == "FULL_ALLOCATION_ELIGIBLE"
    assert member["quality_action"] == "BUY_REVIEW_REQUIRED"
    assert member["membership_intent"] == "UNRESOLVED"
    assert "strategy_intelligence_eligibility_not_pass" in member["reason_codes"]
    assert payload["upstream_artifacts"]["strategy_intelligence"]["production_evidence_allowed"] is True


def test_phase30_p_pm_uses_si_to_separate_hold_worthy_from_add_worthy(tmp_path: Path) -> None:
    si_path = _write_strategy_intelligence(tmp_path, cq_complete=False, held=True)

    payload, _ = build_position_management_payload(
        business_date=BUSINESS_DATE,
        market_context_artifact_path=_write_pm_market_context(tmp_path),
        corporate_event_artifact_path=_write_pm_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_pm_portfolio_policy(tmp_path),
        existing_pm_decisions=[
            {
                "security_code": "11110",
                "action": "ADD",
                "intensity": "MEDIUM",
                "confidence": 0.8,
                "reason_codes": ["legacy_add_candidate"],
            }
        ],
        runtime_current_positions=[{"security_code": "11110", "quantity": 100, "position_id": "pos-11110"}],
        position_lifecycle_summary=_pm_summary(tmp_path, "lifecycle"),
        technical_feature_summary=_pm_summary(tmp_path, "features"),
        opportunity_summary=_pm_summary(tmp_path, "opportunity"),
        accepted_generation_reference=_generation(tmp_path),
        strategy_intelligence_artifact_path=si_path,
    )

    position = payload["positions"][0]
    assert position["strategy_intelligence_consumer_status"] == "CONNECTED"
    assert position["action"] == "HOLD"
    assert "structured_add_worthiness_no_add" in position["reason_codes"]
    assert position["strategy_intelligence_add_worthiness_evidence"]["status"] == "NO_ADD"
    assert payload["upstream_artifacts"]["strategy_intelligence"]["production_evidence_allowed"] is True


def test_phase30_ae1_pm_exposes_canonical_position_campaign_id_from_si(tmp_path: Path) -> None:
    si_path = _write_strategy_intelligence_with_campaign(tmp_path)

    payload, _ = build_position_management_payload(
        business_date=BUSINESS_DATE,
        market_context_artifact_path=_write_pm_market_context(tmp_path),
        corporate_event_artifact_path=_write_pm_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_pm_portfolio_policy(tmp_path),
        existing_pm_decisions=[
            {
                "security_code": "11110",
                "action": "ADD",
                "intensity": "MEDIUM",
                "confidence": 0.8,
                "lifecycle_reference": "runtime-current-11110",
                "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
            }
        ],
        runtime_current_positions=[{"security_code": "11110", "quantity": 100, "position_id": "pos-11110"}],
        position_lifecycle_summary=_pm_summary(tmp_path, "lifecycle"),
        technical_feature_summary=_pm_summary(tmp_path, "features"),
        opportunity_summary=_pm_summary(tmp_path, "opportunity"),
        accepted_generation_reference=_generation(tmp_path),
        strategy_intelligence_artifact_path=si_path,
    )

    position = payload["positions"][0]
    assert position["strategy_intelligence_consumer_status"] == "CONNECTED"
    assert position["position_campaign_id"] == "pc-11110-0001"
    assert position["strategy_intelligence_campaign_id"] == "pc-11110-0001"
    assert position["position_campaign_id"] != "runtime-current-11110"


def test_phase31_g108_pm_hold_not_unresolved_when_runtime_fill_campaign_identity_complete(tmp_path: Path) -> None:
    si_path = _write_strategy_intelligence_with_campaign(tmp_path, action="HOLD")

    payload, _ = build_position_management_payload(
        business_date=BUSINESS_DATE,
        market_context_artifact_path=_write_pm_market_context(tmp_path),
        corporate_event_artifact_path=_write_pm_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_pm_portfolio_policy(tmp_path),
        existing_pm_decisions=[
            {
                "security_code": "11110",
                "action": "HOLD",
                "intensity": "NONE",
                "confidence": 0.8,
                "lifecycle_reference": "runtime-current-11110",
                "reason_codes": ["trend_continuation"],
            }
        ],
        runtime_current_positions=[{"security_code": "11110", "quantity": 100, "position_id": "pos-11110"}],
        position_lifecycle_summary=_pm_summary(tmp_path, "lifecycle"),
        technical_feature_summary=_pm_summary(tmp_path, "features"),
        opportunity_summary=_pm_summary(tmp_path, "opportunity"),
        accepted_generation_reference=_generation(tmp_path),
        strategy_intelligence_artifact_path=si_path,
    )

    position = payload["positions"][0]
    assert position["strategy_intelligence_consumer_status"] == "CONNECTED"
    assert position["action"] == "HOLD"
    assert position["position_campaign_id"] == "pc-11110-0001"
    assert "structured_hold_worthiness_review_required" not in position["reason_codes"]
    assert position["strategy_intelligence_hold_worthiness_evidence"]["campaign_identity_authority_status"] == "COMPLETE"
    assert "canonical_campaign_identity_missing" not in position["strategy_intelligence_hold_worthiness_evidence"]["reason_codes"]


def _write_strategy_intelligence(tmp_path: Path, *, cq_complete: bool, held: bool = False) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    market = _write_json(
        tmp_path / "si_market_context.json",
        {
            "schema_version": "market_context.v1",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "market_regime": "BULL",
            "artifact_hash": "market-hash",
        },
    )
    corporate = _write_json(
        tmp_path / "si_corporate_event.json",
        {
            "schema_version": "corporate_event.v1",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "coverage_status": "PARTIAL",
            "symbol_event_facts": {"11110": {"coverage_status": "MISSING", "event_facts": []}},
            "artifact_hash": "event-hash",
        },
    )
    technical_row = {"security_code": "11110", "business_date": BUSINESS_DATE, "feature_date": BUSINESS_DATE}
    if cq_complete:
        technical_row.update(
            {
                "trend_close_over_ma_20d": 1.05,
                "trend_ma_5_20_ratio": 1.02,
                "price_momentum_return_1d": 0.01,
                "price_momentum_return_3d": 0.02,
                "price_momentum_return_5d": 0.03,
                "price_momentum_return_20d": 0.08,
                "momentum_5d_vs_20d_delta": 0.01,
                "momentum_1d_vs_5d_delta": 0.01,
                "volume_momentum_ratio_5d": 1.1,
                "reference_price": 1000,
                "volatility_return_std_20d": 0.02,
            }
        )
    result = produce_strategy_intelligence_artifact(
        business_date=BUSINESS_DATE,
        candidate_summary=_si_summary("candidate", [{"security_code": "11110"}]),
        opportunity_summary=_si_summary("opportunity", [{"security_code": "11110", "runtime_opportunity_score": 0.82}]),
        current_summary=_si_summary(
            "current",
            [
                {
                    "security_code": "11110",
                    "quantity": 100 if held else 0,
                    "average_price": 1000,
                    "current_price": 1040,
                    "market_value": 104000 if held else 0,
                }
            ],
        ),
        technical_feature_summary=_si_summary("technical", [technical_row]),
        price_volatility_summary=_si_summary("volatility", [{"security_code": "11110", "reference_price": 1000}]),
        market_context_artifact_path=market,
        corporate_event_artifact_path=corporate,
        buy_quality_artifact_path=None,
        portfolio_construction_artifact_path=None,
        position_sizing_artifact_path=None,
        position_management_artifact_path=None,
        runtime_planning_artifact_path=None,
        output_path=tmp_path / "strategy_intelligence.json",
        production_consumer_connected=True,
        consumer_stage="PRE_ACTION_PRODUCTION_EVIDENCE",
    )
    assert result.status in {"PASS", "REVIEW_REQUIRED"}
    return Path(result.artifact_path)


def _write_strategy_intelligence_with_campaign(tmp_path: Path, *, action: str = "ADD") -> Path:
    path = _write_strategy_intelligence(tmp_path, cq_complete=True, held=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    row = payload["symbol_intelligence"]["11110"]
    row["current_decision"]["pm_action"] = action
    row["lifecycle_context"].update(
        {
            "position_campaign_id": "pc-11110-0001",
            "campaign_opened_date": "2026-07-12",
            "campaign_status": "OPEN",
            "campaign_identity_authority_status": "COMPLETE",
            "campaign_age_business_days": 3,
            "missing_campaign_authority_fields": [],
            "add_history_summary": {"event_count": 0},
            "reduce_history_summary": {"event_count": 0},
        }
    )
    row["continuation_quality"]["status"] = "PASS"
    row["downside_risk"]["status"] = "PASS"
    _write_json(path, payload)
    return path


def _si_summary(kind: str, rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "status": "PASS",
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "source_ref": f"{kind}.json",
        "source_hash": f"{kind}-hash",
        "rows": rows,
    }


def _pc_summary(tmp_path: Path, kind: str, rows: list[dict[str, object]]) -> PortfolioConstructionSourceSummary:
    return _pc_source_summary(tmp_path, kind, rows=rows)
