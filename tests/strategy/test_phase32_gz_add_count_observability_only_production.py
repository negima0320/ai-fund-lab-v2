from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy import portfolio_construction, position_management
from ai_fund_lab_v2.strategy.position_management import build_position_management_payload

from tests.strategy.test_phase22_d_position_management import (
    _generation,
    _summary as _pm_summary,
    _write_corporate_event as _write_pm_corporate_event,
    _write_market_context as _write_pm_market_context,
    _write_portfolio_policy as _write_pm_portfolio_policy,
)
from tests.strategy.test_phase22_e_portfolio_construction import (
    _build_d28_payload,
    _opportunity_row,
    _pm_row,
    _write_json,
)
from tests.strategy.test_phase30_p_strategy_intelligence_production_migration import (
    BUSINESS_DATE,
    _write_strategy_intelligence_with_campaign,
)


def test_phase32_gz_pm_count_over_five_is_observability_not_add_to_hold() -> None:
    evidence = position_management._structured_add_worthiness_evidence(
        lifecycle={
            "campaign_identity_authority_status": "COMPLETE",
            "add_history_summary": {"event_count": 8},
            "reduce_history_summary": {"event_count": 0},
        },
        cq={"status": "PASS"},
        risk={"status": "PASS"},
        profit={"status": "OBSERVED"},
    )

    assert evidence["status"] == "PASS"
    assert evidence["reason_codes"] == []
    assert evidence["current_campaign_add_count"] == 8
    assert evidence["add_count_limit_reached_observed"] is True
    assert evidence["add_count_excess_observed"] == 3
    assert evidence["add_count_observability_only"] is True
    assert evidence["add_count_standalone_decision_authority"] is False


def test_phase32_gz_pm_payload_preserves_add_action_when_only_count_exceeds_five(tmp_path: Path) -> None:
    si_path = _strategy_intelligence_with_add_count(tmp_path, add_count=5)

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
    evidence = position["strategy_intelligence_add_worthiness_evidence"]

    assert position["action"] == "ADD"
    assert "structured_add_worthiness_no_add" not in position["reason_codes"]
    assert evidence["status"] == "PASS"
    assert evidence["current_campaign_add_count"] == 5
    assert evidence["add_count_limit_reached_observed"] is True


def test_phase32_gz_current_safety_still_blocks_even_when_count_has_room() -> None:
    evidence = position_management._structured_add_worthiness_evidence(
        lifecycle={
            "campaign_identity_authority_status": "COMPLETE",
            "add_history_summary": {"event_count": 2},
            "reduce_history_summary": {"event_count": 0},
        },
        cq={"status": "FAIL"},
        risk={"status": "PASS"},
        profit={"status": "OBSERVED"},
    )

    assert evidence["status"] == "NO_ADD"
    assert evidence["reason_codes"] == ["incremental_continuation_quality_not_pass"]


def test_phase32_gz_reduce_history_still_blocks_count_over_five() -> None:
    evidence = position_management._structured_add_worthiness_evidence(
        lifecycle={
            "campaign_identity_authority_status": "COMPLETE",
            "add_history_summary": {"event_count": 12},
            "reduce_history_summary": {"event_count": 1},
        },
        cq={"status": "PASS"},
        risk={"status": "PASS"},
        profit={"status": "OBSERVED"},
    )

    assert evidence["status"] == "NO_ADD"
    assert evidence["reason_codes"] == ["prior_reduce_history_requires_add_review"]
    assert evidence["add_count_limit_reached_observed"] is True


def test_phase32_gz_pc_count_over_five_reaches_add_capital_competition(tmp_path: Path) -> None:
    payload = _build_d28_payload(
        tmp_path,
        current_rows=[{"position_id": "current-11110", "security_code": "11110", "current_weight": 0.05, "position_campaign_id": "pc-11110-0001"}],
        pm_rows=[
            {
                **_pm_row("11110", "ADD"),
                "position_campaign_id": "pc-11110-0001",
                "strategy_intelligence_campaign_id": "pc-11110-0001",
                "strategy_intelligence_add_history_count": 5,
                "strategy_intelligence_add_count_observability_only": True,
                "strategy_intelligence_add_count_standalone_decision_authority": False,
                "strategy_intelligence_add_worthiness_state": "ADD_ALLOWED",
                "entry_admission_action": "ADD_ALLOWED",
                "reason_codes": ["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"],
            }
        ],
        opportunity_rows=[
            _opportunity_row(
                "11110",
                1,
                0.82,
                position_campaign_id="pc-11110-0001",
                expected_edge_baseline_score=0.70,
                expected_edge_baseline_business_date="2026-07-14",
                expected_edge_baseline_campaign_id="pc-11110-0001",
                incremental_investment_value_state="POSITIVE",
                opportunity_cost_status="PASS",
            ),
        ],
        exposure=0.4,
        cap=0.4,
    )

    member = next(row for row in payload["portfolio_members"] if row["security_code"] == "11110")
    competitor = next(
        row
        for row in payload["capital_competition"]["competitors"]
        if row["competitor_type"] == "ADD" and row["symbol"] == "11110"
    )

    assert member["membership_intent"] == "RETAIN"
    assert member["weight_intent"] == "INCREASE"
    assert member["add_allocation_eligibility_status"] == "PASS"
    assert competitor["canonical_add_competitor"]["eligibility_state"] == "PASS"
    assert competitor["canonical_add_competitor"]["proposed_incremental_target_weight"] > 0.0


def test_phase32_gz_pc_si_mirror_keeps_count_observable_without_no_add() -> None:
    fields = portfolio_construction._strategy_intelligence_member_fields(
        {
            "continuation_quality": {"status": "PASS"},
            "downside_risk": {"status": "PASS"},
            "profit_protection_evidence": {"status": "OBSERVED"},
            "entry_admission": {},
            "lifecycle_context": {
                "current_position_state": "HELD",
                "campaign_identity_authority_status": "COMPLETE",
                "position_campaign_id": "pc-11110-0001",
                "add_history_summary": {"event_count": 8},
                "reduce_history_summary": {"event_count": 0},
            },
        },
        {"artifact_hash": "hash", "business_date": BUSINESS_DATE},
        "strategy_intelligence.json",
    )

    assert fields["strategy_intelligence_add_history_count"] == 8
    assert fields["strategy_intelligence_add_count_observability_only"] is True
    assert fields["strategy_intelligence_add_count_limit_reached_observed"] is True
    assert fields["strategy_intelligence_add_count_excess_observed"] == 3
    assert fields["strategy_intelligence_add_count_standalone_decision_authority"] is False
    assert fields["strategy_intelligence_add_worthiness_state"] == "ADD_ALLOWED"


def test_phase32_gz_runaway_pyramiding_counts_recheck_current_safety() -> None:
    for add_count in (6, 8, 12):
        strong = position_management._structured_add_worthiness_evidence(
            lifecycle={
                "campaign_identity_authority_status": "COMPLETE",
                "add_history_summary": {"event_count": add_count},
                "reduce_history_summary": {"event_count": 0},
            },
            cq={"status": "PASS"},
            risk={"status": "PASS"},
            profit={"status": "OBSERVED"},
        )
        unsafe = position_management._structured_add_worthiness_evidence(
            lifecycle={
                "campaign_identity_authority_status": "COMPLETE",
                "add_history_summary": {"event_count": add_count},
                "reduce_history_summary": {"event_count": 0},
            },
            cq={"status": "PASS"},
            risk={"status": "BLOCK"},
            profit={"status": "OBSERVED"},
        )

        assert strong["status"] == "PASS"
        assert unsafe["status"] == "NO_ADD"
        assert unsafe["reason_codes"] == ["downside_risk_blocks_add"]


def _strategy_intelligence_with_add_count(tmp_path: Path, *, add_count: int) -> Path:
    path = _write_strategy_intelligence_with_campaign(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    row = payload["symbol_intelligence"]["11110"]
    row["lifecycle_context"]["add_history_summary"] = {"event_count": add_count}
    row["lifecycle_context"]["reduce_history_summary"] = {"event_count": 0}
    row["lifecycle_context"]["current_position_state"] = "HELD"
    row["profit_protection_evidence"]["status"] = "OBSERVED"
    _write_json(path, payload)
    return path
