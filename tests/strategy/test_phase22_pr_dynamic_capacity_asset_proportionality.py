from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.strategy import dynamic_cash_exposure as dce
from ai_fund_lab_v2.strategy import dynamic_position_count as dpc
from ai_fund_lab_v2.strategy import position_sizing as ps


def test_phase22_pr_asset_proportional_exposure_has_no_850000_cap(tmp_path: Path) -> None:
    one_million = _cash_payload(tmp_path / "one", cash=1_000_000, market_value=0)
    two_million = _cash_payload(tmp_path / "two", cash=2_000_000, market_value=0)
    seven_hundred = _cash_payload(tmp_path / "seven", cash=700_000, market_value=0)

    assert one_million["target_invested_notional"] == 800_000
    assert two_million["target_invested_notional"] == 1_600_000
    assert seven_hundred["target_invested_notional"] == 560_000
    assert two_million["target_invested_notional"] != 850_000
    assert two_million["strategy_fixed_jpy_exposure_cap_used"] is False
    assert two_million["legacy_max_exposure_authority_used"] is False


def test_phase22_pr_dynamic_capacity_does_not_truncate_at_fixed_eight(tmp_path: Path) -> None:
    payload = _count_payload(tmp_path, candidates=10, opportunities=10)

    assert payload["target_position_count"] == 10
    assert payload["actual_target_position_count"] == 10
    assert payload["strategy_maximum_position_count"] is None
    assert payload["strategy_fixed_position_cap_used"] is False
    assert payload["safety_hard_maximum_used_for_target_calculation"] is False


def test_phase22_pr_meaningful_allocation_capacity_can_naturally_limit_count(tmp_path: Path) -> None:
    payload = _count_payload(tmp_path, candidates=20, opportunities=20, meaningful=6)

    assert payload["meaningful_allocation_position_count"] == 6
    assert payload["target_position_count"] == 6
    assert payload["strategy_fixed_position_cap_used"] is False


def test_phase22_pr_current_holdings_delta_sizing(tmp_path: Path) -> None:
    payload = _sizing_payload(
        tmp_path,
        rows=[
            _row("1001", current_weight=0.16),
            _row("1002", current_weight=0.02),
        ],
    )
    by_code = {row["security_code"]: row for row in payload["positions"]}

    assert by_code["1001"]["incremental_buy_notional"] == 0
    assert by_code["1002"]["incremental_buy_notional"] > 0
    assert by_code["1002"]["target_notional"] == round(payload["portfolio_total_equity"] * by_code["1002"]["target_weight"], 2)


def test_phase22_pr_legacy_isolation_for_count_and_exposure(tmp_path: Path) -> None:
    base_count = _count_payload(tmp_path / "base", candidates=10, opportunities=10, legacy_max=5)
    changed_legacy_count = _count_payload(tmp_path / "changed", candidates=10, opportunities=10, legacy_max=3)
    assert base_count["target_position_count"] == changed_legacy_count["target_position_count"]

    base_cash = _cash_payload(tmp_path / "cash_base", cash=2_000_000, market_value=0)
    changed_cash = _cash_payload(tmp_path / "cash_changed", cash=2_000_000, market_value=0)
    assert base_cash["target_invested_notional"] == changed_cash["target_invested_notional"] == 1_600_000


def _count_payload(tmp_path: Path, *, candidates: int, opportunities: int, meaningful: int | None = None, legacy_max: int = 5) -> dict[str, object]:
    config = dpc.load_dynamic_position_count_config("configs/strategy/dynamic_position_count.json")
    payload, _ = dpc.build_dynamic_position_count_payload(
        business_date="2026-07-15",
        market_context_summary=_dpc_summary(tmp_path, "market", {"trend_regime": "BULL", "market_breadth": "STRONG", "volatility_regime": "LOW", "confidence": 0.9, "uncertainty": "LOW"}),
        portfolio_policy_summary=_dpc_summary(tmp_path, "policy", {"risk_posture": "RISK_ON", "entry_posture": "EXPAND", "confidence": 0.9, "uncertainty": "LOW"}),
        candidate_summary=_dpc_summary(tmp_path, "candidate", {"available_candidate_count": candidates}),
        opportunity_summary=_dpc_summary(tmp_path, "opportunity", {"available_opportunity_count": opportunities, **({"meaningful_allocation_position_count": meaningful} if meaningful is not None else {})}),
        current_portfolio_summary=_dpc_summary(tmp_path, "current", {"current_position_count": 0}),
        safety_hard_maximum=None,
        existing_active_max_positions=legacy_max,
        config=config,
    )
    return payload


def _cash_payload(tmp_path: Path, *, cash: float, market_value: float) -> dict[str, object]:
    payload, _ = dce.build_dynamic_cash_exposure_payload(
        business_date="2026-07-15",
        market_context_summary=_dce_summary(tmp_path, "market", {"trend_regime": "RANGE", "market_breadth": "NEUTRAL", "volatility_regime": "NORMAL", "confidence": 0.9, "uncertainty": "LOW"}),
        portfolio_policy_summary=_dce_summary(tmp_path, "policy", {"risk_posture": "BALANCED", "confidence": 0.9, "uncertainty": "LOW"}),
        dynamic_position_count_summary=_dce_summary(tmp_path, "count", {"target_position_count": 10, "confidence": 0.9}),
        candidate_summary=_dce_summary(tmp_path, "candidate", {"available_candidate_count": 10}),
        opportunity_summary=_dce_summary(tmp_path, "opportunity", {"available_opportunity_count": 10}),
        current_cash_summary=_dce_summary(tmp_path, "cash", {"current_cash": cash}),
        current_exposure_summary=_dce_summary(tmp_path, "exposure", {"current_market_value": market_value}),
        pending_reservation_summary=_dce_summary(tmp_path, "pending", {"pending_reserved_cash": 0, "pending_reserved_exposure": 0}),
        safety_limit_summary=_dce_summary(tmp_path, "safety", {"minimum_cash_ratio": 0.1, "maximum_gross_exposure_ratio": 0.9}),
        config=dce.load_dynamic_cash_exposure_config("configs/strategy/dynamic_cash_exposure.json"),
    )
    return payload


def _sizing_payload(tmp_path: Path, *, rows: list[dict[str, object]]) -> dict[str, object]:
    payload, _ = ps.build_position_sizing_payload(
        business_date="2026-07-15",
        portfolio_construction_summary=_ps_summary(tmp_path, "pc", rows=rows),
        capital_deployment_summary=_ps_summary(tmp_path, "cd"),
        dynamic_position_count_summary=_ps_summary(tmp_path, "dpc", summary={"target_position_count": 5}),
        dynamic_cash_exposure_summary=_ps_summary(tmp_path, "dce", summary={"target_gross_exposure_ratio": 0.8}),
        position_management_summary=_ps_summary(tmp_path, "pm"),
        opportunity_summary=_ps_summary(tmp_path, "opp"),
        current_position_summary=_ps_summary(tmp_path, "cur", summary={"portfolio_total_equity": 1_000_000}),
        price_volatility_summary=_ps_summary(tmp_path, "pv"),
        safety_limit_summary=_ps_summary(tmp_path, "safety", summary={"maximum_position_weight": 0.25}),
        config=ps.load_position_sizing_config("configs/strategy/position_sizing.json"),
    )
    return payload


def _row(code: str, *, current_weight: float) -> dict[str, object]:
    target_weight = 0.16
    return {
        "security_code": code,
        "membership_intent": "ADD_CANDIDATE",
        "pm_action": "NEW",
        "current_weight": current_weight,
        "target_weight": target_weight,
        "target_weight_authority": {
            "authority_type": "TARGET_WEIGHT_AUTHORITY",
            "method_id": "test_production_v1_equal_weight_target_allocation",
            "method_version": "phase23_ao_test_v1",
            "business_date": "2026-07-15",
            "target_gross_exposure": 0.8,
            "resolved_target_member_count": 5,
            "single_name_weight_cap": 0.25,
            "portfolio_policy_reference": "policy-test",
            "dynamic_position_count_reference": "dynamic-position-count-test",
            "opportunity_reference": f"opportunity-{code}",
            "existing_position_reference": f"current-{code}" if current_weight else "",
            "position_management_reference": f"pm-{code}",
            "source_artifact_paths": [],
            "source_artifact_hashes": [],
            "PIT_status": "PASS",
        },
        "target_weight_resolution": {
            "status": "PASS",
            "reason": "target_weight_resolved",
            "resolved_weight": target_weight,
            "base_weight": target_weight,
            "adjustments": [],
            "cap_applied": False,
            "normalization_applied": False,
            "zero_weight_reason": "",
            "review_reason": "",
        },
        "runtime_opportunity_score": 0.5,
        "runtime_opportunity_score_authority": {
            "authority": "OPPORTUNITY_RANKING_AUTHORITY",
            "canonical_field": "runtime_opportunity_score",
            "source_decision_id": f"opportunity-{code}",
            "source_artifact_class": "opportunity",
            "source_field": "runtime_opportunity_score",
            "prediction_semantics": "runtime_opportunity_score",
        },
        "allocation_quality_score": 0.5,
        "allocation_quality_authority": {
            "authority": "ALLOCATION_QUALITY_AUTHORITY",
            "canonical_field": "allocation_quality_score",
            "source_decision_id": f"allocation-quality-{code}",
            "source_artifact_class": "portfolio_construction",
            "source_field": "allocation_quality_score",
            "output_semantics": "allocation_quality_score",
        },
        "volatility": 0.03,
        "reference_price": 500,
    }


def _dpc_summary(tmp_path: Path, kind: str, summary: dict[str, object]) -> dpc.DynamicPositionCountSourceSummary:
    path = _source(tmp_path, kind, summary)
    return dpc.DynamicPositionCountSourceSummary("PASS", "2026-07-15", "2026-07-15", str(path), dpc.sha256_file(path), summary)


def _dce_summary(tmp_path: Path, kind: str, summary: dict[str, object]) -> dce.CashExposureSourceSummary:
    path = _source(tmp_path, kind, summary)
    return dce.CashExposureSourceSummary("PASS", "2026-07-15", "2026-07-15", str(path), dce.sha256_file(path), summary)


def _ps_summary(tmp_path: Path, kind: str, *, rows: list[dict[str, object]] | None = None, summary: dict[str, object] | None = None) -> ps.PositionSizingSourceSummary:
    path = _source(tmp_path, kind, summary or {}, rows=rows or [])
    return ps.PositionSizingSourceSummary("PASS", "2026-07-15", "2026-07-15", str(path), ps.sha256_file(path), tuple(rows or ()), summary or {})


def _source(tmp_path: Path, kind: str, summary: dict[str, object], *, rows: list[dict[str, object]] | None = None) -> Path:
    path = tmp_path / f"{kind}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"kind": kind, "summary": summary, "rows": rows or []}, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    return path
