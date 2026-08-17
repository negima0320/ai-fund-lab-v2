from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.strategy.strategy_intelligence import build_strategy_intelligence_payload

from tests.strategy.test_phase30_j_strategy_intelligence import (
    _candidate_summary,
    _current_summary,
    _opportunity_summary,
    _price_volatility_summary,
    _technical_summary,
    _write_json,
)


def test_phase30_l_buy_wait_is_not_shadow_reinterpreted_as_buy_new(tmp_path: Path) -> None:
    payload = _payload_for_action(tmp_path, action="BUY_WAIT", held=False)

    row = payload["symbol_intelligence"]["11110"]
    interpretation = row["strategy_intelligence_interpretation"]
    assert interpretation["state"] == "BUY_WAIT_CONTEXT_SHADOW"
    assert interpretation["not_action_authority"] is True
    assert interpretation["state"] != "BUY_NEW_CANDIDATE_EVIDENCE_SHADOW"
    assert interpretation["current_action_preserved"] is True
    assert interpretation["actual_behavior_changed"] is False


def test_phase30_l_add_worthiness_is_separate_from_hold_worthiness(tmp_path: Path) -> None:
    payload = _payload_for_action(tmp_path, action="ADD", held=True)

    row = payload["symbol_intelligence"]["11110"]
    interpretation = row["strategy_intelligence_interpretation"]
    assert interpretation["state"] == "ADD_WORTHINESS_EVIDENCE_SHADOW"
    assert interpretation["state"] != "HOLD_WORTHINESS_OBSERVED_SHADOW"
    assert interpretation["interpretation_summary"]["add_vs_hold_separation"] is True
    assert row["expected_edge"]["incremental_edge_for_add"]["not_action_authority"] is True


def test_phase30_l_reduce_and_exit_preserve_current_pm_authority(tmp_path: Path) -> None:
    for action, expected in (("REDUCE", "PM_REDUCE_EVIDENCE_OBSERVED_SHADOW"), ("EXIT", "PM_EXIT_EVIDENCE_OBSERVED_SHADOW")):
        payload = _payload_for_action(tmp_path / action, action=action, held=True)

        row = payload["symbol_intelligence"]["11110"]
        interpretation = row["strategy_intelligence_interpretation"]
        assert interpretation["state"] == expected
        assert interpretation["state"] != "HOLD_WORTHINESS_OBSERVED_SHADOW"
        assert interpretation["interpretation_summary"]["reduce_exit_authority_preservation"] is True
        assert row["current_decision"]["pm_action"] == action
        assert interpretation["shadow_output_connected_to_production_action_authority"] is False


def test_phase30_l_profit_protection_uses_observed_past_current_state_only(tmp_path: Path) -> None:
    payload = _payload_for_action(
        tmp_path,
        action="REDUCE",
        held=True,
        current_overrides={"market_value": 112000, "observed_campaign_mfe": 0.22, "observed_giveback": 0.08},
    )

    evidence = payload["symbol_intelligence"]["11110"]["profit_protection_evidence"]
    assert evidence["status"] == "OBSERVED"
    assert round(evidence["embedded_return_observed"], 6) == 0.12
    assert evidence["observed_campaign_mfe"] == 0.22
    assert evidence["observed_giveback"] == 0.08
    assert evidence["future_mfe_used"] is False
    assert evidence["future_peak_used"] is False
    assert evidence["not_action_authority"] is True


def test_phase30_l_relative_strength_connects_stock_vs_market_only(tmp_path: Path) -> None:
    payload = _payload_for_action(tmp_path, action="BUY_NEW", held=False, market_returns=True)

    rs = payload["symbol_intelligence"]["11110"]["continuation_quality"]["relative_strength"]
    assert rs["authority_connection_status"] == "PARTIALLY_CONNECTED"
    assert rs["state"] == "SUPPORTIVE"
    assert rs["rank_or_opportunity_score_used"] is False
    assert round(rs["values"]["stock_vs_market_return_20d"], 6) == 0.04
    assert "stock_vs_sector_relative_strength_authority" in rs["missing_inputs"]
    assert "sector_vs_market_symbol_join_authority" in rs["missing_inputs"]


def test_phase30_l_sell_exit_takes_precedence_over_buy_wait_shadow_context(tmp_path: Path) -> None:
    payload = _payload_for_action(tmp_path, action="SELL_EXIT", held=True, buy_quality_action="BUY_WAIT")

    row = payload["symbol_intelligence"]["11110"]
    assert row["current_decision"]["buy_quality_action"] == "BUY_WAIT"
    assert row["current_decision"]["pm_action"] == "SELL_EXIT"
    assert row["strategy_intelligence_interpretation"]["state"] == "PM_EXIT_EVIDENCE_OBSERVED_SHADOW"
    assert row["strategy_intelligence_interpretation"]["interpretation_summary"]["reduce_exit_authority_preservation"] is True


def _payload_for_action(
    tmp_path: Path,
    *,
    action: str,
    held: bool,
    buy_quality_action: str | None = None,
    current_overrides: dict | None = None,
    market_returns: bool = False,
) -> dict:
    business_date = "2026-07-15"
    paths = _write_source_artifacts_l(
        tmp_path,
        business_date=business_date,
        action=action,
        buy_quality_action=buy_quality_action or action,
        market_returns=market_returns,
    )
    current = _current_summary(business_date, held=held)
    if current_overrides:
        current["rows"][0].update(current_overrides)
    payload, _ = build_strategy_intelligence_payload(
        business_date=business_date,
        candidate_summary=_candidate_summary(business_date),
        opportunity_summary=_opportunity_summary(business_date),
        current_summary=current,
        technical_feature_summary=_technical_summary(business_date),
        price_volatility_summary=_price_volatility_summary(business_date),
        position_campaigns_artifact_path=_campaigns_l(tmp_path, business_date=business_date) if held else None,
        as_of=f"{business_date}T00:00:00+00:00",
        **paths,
    )
    return payload


def _campaigns_l(tmp_path: Path, *, business_date: str) -> Path:
    return _write_json(
        tmp_path / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "business_date": business_date,
            "position_campaigns": [
                {
                    "position_campaign_id": "pc-11110-0001",
                    "symbol": "11110",
                    "campaign_status": "OPEN",
                    "opened_business_date": "2026-07-10",
                    "current_quantity": 100,
                    "current_campaign_relative_return": 0.12,
                    "observed_campaign_mfe": 0.22,
                    "observed_giveback": 0.08,
                    "events": [{"business_date": "2026-07-10", "side": "BUY", "stage": "BUY"}],
                }
            ],
        },
    )


def _write_source_artifacts_l(
    tmp_path: Path,
    *,
    business_date: str,
    action: str,
    buy_quality_action: str,
    market_returns: bool,
) -> dict[str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    market_payload = {
        "schema_version": "market_context.v1",
        "business_date": business_date,
        "market_regime": "BULL",
        "artifact_hash": "market-hash",
    }
    if market_returns:
        market_payload["metrics"] = {"return_5d_equal_weight": 0.01, "return_20d_equal_weight": 0.05}
    market_context = _write_json(tmp_path / "market_context.json", market_payload)
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
            "decisions": [{"security_code": "11110", "quality_action": buy_quality_action, "quality_band": "OBSERVED"}],
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
                    "semantic_buy_type": "REENTRY" if action == "REENTRY" else action,
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
