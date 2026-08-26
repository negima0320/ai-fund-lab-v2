from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.safety.portfolio_limits import load_portfolio_safety_limits
from ai_fund_lab_v2.strategy import portfolio_construction, portfolio_policy, position_management, runtime_planning
from ai_fund_lab_v2.strategy.portfolio_construction import portfolio_construction_hash
from ai_fund_lab_v2.strategy.position_sizing import (
    PositionSizingSourceSummary,
    build_position_sizing_payload,
    load_position_sizing_config,
    position_sizing_hash,
    sha256_file,
)
from ai_fund_lab_v2.strategy.runtime_planning import (
    RuntimePlanningSourceSummary,
    build_runtime_planning_payload,
    runtime_planning_hash,
)
from ai_fund_lab_v2.strategy.shadow_runtime import _produce_lot_aware_final_portfolio_construction


BUSINESS_DATE = "2022-10-03"
REAL_PIT_STRATEGY_DIR = Path(
    "reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T135454942984Z"
) / "daily" / BUSINESS_DATE / "strategy"


def test_phase31_g66_actual_pit_publication_path_materializes_buy_plans(tmp_path: Path) -> None:
    pc_actual = _read_json(REAL_PIT_STRATEGY_DIR / "portfolio_construction.json")
    ps_actual = _read_json(REAL_PIT_STRATEGY_DIR / "position_sizing.json")

    assert ps_actual["producer_result_status"] == "BLOCK"
    assert "G61_COMPATIBILITY_DATE_MISMATCH" in ps_actual["reason_codes"]
    assert _lot_executable_count(pc_actual.get("capital_competition")) == 0

    draft_path = tmp_path / "portfolio_construction_draft.json"
    preflight_path = tmp_path / "position_sizing_preflight.json"
    pc_path = tmp_path / "portfolio_construction.json"
    _write_json(draft_path, _read_json(REAL_PIT_STRATEGY_DIR / "portfolio_construction_draft.json"))
    _write_json(preflight_path, _read_json(REAL_PIT_STRATEGY_DIR / "position_sizing_preflight.json"))

    _produce_lot_aware_final_portfolio_construction(
        business_date=BUSINESS_DATE,
        draft_path=draft_path,
        preflight_path=preflight_path,
        output_path=pc_path,
    )

    pc_promoted = _read_json(pc_path)
    multi = pc_promoted["capital_competition"]["canonical_multi_allocation_deployment_set"]
    compatibility = multi["lot_aware_allocation_to_sizing_compatibility"]

    assert pc_promoted["pre_lot_capital_competition"]["canonical_multi_allocation_deployment_set"][
        "lot_aware_allocation_to_sizing_compatibility"
    ]["lot_executable_count"] == 0
    assert pc_promoted["business_date"] == BUSINESS_DATE
    assert multi["business_date"] == BUSINESS_DATE
    assert compatibility["business_date"] == BUSINESS_DATE
    assert multi["budget_envelope"]["schema_version"] == "incremental_capital_budget_envelope.v1"
    assert multi["budget_envelope"]["bootstrap_or_residual_cash_state"] == "EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP"
    assert "CAPITAL_BUDGET_ENVELOPE_MISSING" not in multi["reason_codes"]
    assert len(multi["security_allocations"]) > 0
    assert multi["bootstrap_cash_preferred_participation_allowed"] is True
    assert multi["bootstrap_cash_preferred_participation_count"] > 0
    assert all(
        item["interaction_result"] == "CASH_PREFERRED"
        for item in multi["security_allocations"]
        if item.get("bootstrap_reduced_risk_participation")
    )
    assert multi["cash_preferred_security_deferral_count"] == 0
    assert multi["authorized_cash_allocation"]["authorized_allocation_weight"] > 0
    assert _lot_executable_count(pc_promoted["capital_competition"]) > 0
    assert "G66_LOT_AWARE_MULTI_ALLOCATION_PUBLISHED_TOP_LEVEL" in pc_promoted["reason_codes"]
    assert pc_promoted["capital_competition"] != pc_promoted["pre_lot_capital_competition"]

    pc_path = _write_artifact(pc_path, pc_promoted, portfolio_construction_hash)
    ps_payload, _ = build_position_sizing_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_summary=PositionSizingSourceSummary(
            "PASS",
            BUSINESS_DATE,
            BUSINESS_DATE,
            str(pc_path),
            sha256_file(pc_path),
            tuple(pc_promoted["portfolio_members"]),
            pc_promoted,
        ),
        capital_deployment_summary=_ps_summary(tmp_path, "capital_deployment"),
        dynamic_position_count_summary=_ps_summary(
            tmp_path,
            "dynamic_position_count",
            summary={"target_position_count": pc_actual["resolved_target_member_count"]},
        ),
        dynamic_cash_exposure_summary=_ps_summary(
            tmp_path,
            "dynamic_cash_exposure",
            summary={
                "target_gross_exposure_ratio": pc_actual["target_gross_exposure"],
                "market_context_risk_state": "NORMAL",
            },
        ),
        position_management_summary=_ps_summary(
            tmp_path,
            "position_management",
            rows=_rows_from_artifact("positions", REAL_PIT_STRATEGY_DIR / "position_management.json"),
            summary=_read_json(REAL_PIT_STRATEGY_DIR / "position_management.json"),
        ),
        opportunity_summary=_ps_summary(tmp_path, "opportunity"),
        current_position_summary=_ps_summary(
            tmp_path,
            "current_position",
            summary={"portfolio_total_equity": 1_000_000.0, "portfolio_value": 1_000_000.0},
        ),
        price_volatility_summary=_ps_summary(
            tmp_path,
            "price_volatility",
            rows=_rows_from_artifact("rows", REAL_PIT_STRATEGY_DIR / "price_volatility.json"),
            summary=_read_json(REAL_PIT_STRATEGY_DIR / "price_volatility.json"),
        ),
        safety_limit_summary=_ps_summary(
            tmp_path,
            "safety_limit",
            summary=load_portfolio_safety_limits("configs/safety/portfolio_limits.json").to_contract_payload(),
        ),
        config=load_position_sizing_config("configs/strategy/position_sizing.json"),
        production_consumer_connected=True,
    )

    consumption = ps_payload["g61_lot_aware_compatibility_consumption"]
    assert ps_payload["producer_result_status"] == "PASS"
    assert consumption["status"] == "PASS"
    assert consumption["lot_executable_count"] > 0
    assert consumption["lower_priority_implicit_promotion"] is False
    assert consumption["position_sizing_quantity_owner"] == "POSITION_SIZING"
    assert consumption["pc_discrete_quantity_authority"] is False
    assert consumption["market_quality_semantics_changed"] is False
    assert sum(1 for row in ps_payload["positions"] if int(row.get("quantity_delta_candidate") or 0) > 0) > 0

    ps_path = _write_artifact(tmp_path / "position_sizing.json", ps_payload, position_sizing_hash)
    policy_path = _write_artifact(
        tmp_path / "portfolio_policy.json",
        _read_json(REAL_PIT_STRATEGY_DIR / "portfolio_policy.json"),
        portfolio_policy.portfolio_policy_hash,
    )
    pm_path = _write_artifact(
        tmp_path / "position_management.json",
        _read_json(REAL_PIT_STRATEGY_DIR / "position_management.json"),
        position_management.position_management_hash,
    )

    rp_payload, _ = build_runtime_planning_payload(
        business_date=BUSINESS_DATE,
        portfolio_construction_artifact_path=pc_path,
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=policy_path,
        position_management_artifact_path=pm_path,
        current_portfolio_summary=_rp_summary(tmp_path, "current_portfolio", summary={"portfolio_total_equity": 1_000_000.0}),
        current_cash_summary=_rp_summary(tmp_path, "current_cash", summary={"cash_available": 1_000_000.0}),
        current_position_summary=_rp_summary(tmp_path, "current_position"),
        pending_summary=_rp_summary(tmp_path, "pending"),
        planning_config_summary=_rp_summary(tmp_path, "planning_config"),
        position_sizing_artifact_path=ps_path,
        opportunity_artifact_path=REAL_PIT_STRATEGY_DIR / "buy_quality_decisions.json",
    )
    rp_payload["artifact_hash"] = runtime_planning_hash(rp_payload)

    plans = rp_payload["plans"]
    assert rp_payload["producer_result_status"] == "PASS"
    assert sum(
        1
        for plan in plans
        if plan["planning_intent"] in {"BUY_NEW", "BUY_ADD"} and int(plan.get("planned_quantity") or 0) > 0
    ) > 0
    binding = rp_payload["g63_pc_ps_runtime_executable_binding"]
    assert binding["status"] == "PASS"
    assert binding["runtime_capital_priority_redecision"] is False


def _lot_executable_count(competition: Mapping[str, Any] | None) -> int:
    if not isinstance(competition, Mapping):
        return 0
    multi = competition.get("canonical_multi_allocation_deployment_set")
    if not isinstance(multi, Mapping):
        return 0
    compatibility = multi.get("lot_aware_allocation_to_sizing_compatibility")
    if not isinstance(compatibility, Mapping):
        return 0
    return int(compatibility.get("lot_executable_count") or 0)


def _rows_from_artifact(key: str, path: Path) -> tuple[Mapping[str, Any], ...]:
    payload = _read_json(path)
    return tuple(payload.get(key) or ())


def _ps_summary(
    tmp_path: Path,
    name: str,
    *,
    rows: tuple[Mapping[str, Any], ...] = (),
    summary: Mapping[str, Any] | None = None,
) -> PositionSizingSourceSummary:
    path = tmp_path / f"{name}_source.json"
    payload = {
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "status": "PASS",
        "summary": dict(summary or {}),
        "rows": list(rows),
    }
    _write_json(path, payload)
    return PositionSizingSourceSummary("PASS", BUSINESS_DATE, BUSINESS_DATE, str(path), sha256_file(path), rows, summary or {})


def _rp_summary(
    tmp_path: Path,
    name: str,
    *,
    rows: tuple[Mapping[str, Any], ...] = (),
    summary: Mapping[str, Any] | None = None,
) -> RuntimePlanningSourceSummary:
    path = tmp_path / f"{name}_source.json"
    payload = {
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "status": "PASS",
        "summary": dict(summary or {}),
        "rows": list(rows),
    }
    _write_json(path, payload)
    return RuntimePlanningSourceSummary("PASS", BUSINESS_DATE, BUSINESS_DATE, str(path), sha256_file(path), rows, summary or {})


def _write_artifact(path: Path, payload: Mapping[str, Any], hash_fn: Any) -> Path:
    updated = dict(payload)
    updated.pop("artifact_hash", None)
    updated["artifact_hash"] = hash_fn(updated)
    _write_json(path, updated)
    return path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
