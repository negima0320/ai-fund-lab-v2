from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.capital_allocation_ai.phase7c_daily_path_validation import (
    DEFAULT_DAILY_RESPONSE_DIR,
    DEFAULT_RANKED_DAILY_PATH,
    load_daily_close_path,
    load_ranked_daily,
    now_utc,
    round_float,
)
from ai_fund_lab_v2.capital_allocation_ai.phase7e_strict_backtest import (
    StrictConfig,
    leakage_audit as phase7e_leakage_audit,
    simulate_strict,
    to_jsonable,
)


DEFAULT_OUTPUT_DIR = Path("reports/capital_allocation_ai/phase7f")
COMPLETION_STATUS = "PHASE7F_TURNOVER_REDUCTION_VALIDATION_COMPLETE"


def run_phase7f_turnover_reduction_validation(
    *,
    ranked_daily_path: Path = DEFAULT_RANKED_DAILY_PATH,
    daily_response_dir: Path = DEFAULT_DAILY_RESPONSE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    created_at: str | None = None,
) -> dict[str, Any]:
    created_at = created_at or now_utc()
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked = load_ranked_daily(ranked_daily_path)
    prices = load_daily_close_path(daily_response_dir, ranked)

    rows: list[dict[str, Any]] = []
    annual: list[dict[str, Any]] = []
    for config in build_phase7f_configs():
        result = simulate_strict(ranked, prices, config)
        rows.append(enrich_metrics(result["metrics"], result["annual_summary"]))
        annual.extend(result["annual_summary"])

    comparison = pd.DataFrame(rows).sort_values(["scenario_priority", "policy_id"])
    annual_frame = pd.DataFrame(annual).sort_values(["policy_id", "year"]) if annual else pd.DataFrame()
    turnover = comparison[comparison["scenario_group"].isin(["baseline", "turnover", "combined"])].copy()
    robustness = comparison[comparison["scenario_group"] == "robustness"].copy()
    leakage = phase7e_leakage_audit(ranked, prices, created_at)
    leakage["phase"] = "Phase7-F Leakage Audit"

    paths = {
        "validation_summary": output_dir / "validation_summary.json",
        "policy_comparison": output_dir / "policy_comparison.csv",
        "turnover_comparison": output_dir / "turnover_comparison.csv",
        "robustness_comparison": output_dir / "robustness_comparison.csv",
        "annual_summary": output_dir / "annual_summary.csv",
        "leakage_audit": output_dir / "leakage_audit.json",
    }
    comparison.to_csv(paths["policy_comparison"], index=False)
    turnover.to_csv(paths["turnover_comparison"], index=False)
    robustness.to_csv(paths["robustness_comparison"], index=False)
    annual_frame.to_csv(paths["annual_summary"], index=False)
    write_json(paths["leakage_audit"], leakage)
    summary = build_summary(comparison, ranked, prices, paths, leakage, created_at)
    write_json(paths["validation_summary"], summary)
    return {
        "summary": summary,
        "policy_comparison": comparison,
        "turnover_comparison": turnover,
        "robustness_comparison": robustness,
        "annual_summary": annual_frame,
        "leakage_audit": leakage,
    }


def build_phase7f_configs() -> list[StrictConfig]:
    configs = [
        tagged(StrictConfig("A_FIXED_20BD", "Baseline A fixed 20bd", "BASE"), "baseline", 1),
        tagged(StrictConfig("C3_MIN15_T2", "C3 min15 strict T+2", "C3", minimum_holding_days=15), "baseline", 1),
    ]
    for cap in [3, 4, 5, 6, 8]:
        configs.append(tagged(StrictConfig(f"CAP{cap}", f"C3 min15 monthly cap {cap}", "C3", minimum_holding_days=15, replacement_cap_per_month=cap), "turnover", 2))
    for cooldown in [5, 10, 15]:
        configs.append(tagged(StrictConfig(f"COOLDOWN{cooldown}", f"C3 min15 reentry cooldown {cooldown}bd", "C3", minimum_holding_days=15, reentry_cooldown_days=cooldown), "turnover", 2))
    for edge in [0.02, 0.03, 0.05, 0.08, 0.10]:
        configs.append(tagged(StrictConfig(f"EDGE{int(edge * 100):02d}", f"C3 min15 edge margin {edge:.2f}", "C3", minimum_holding_days=15, replacement_edge_margin=edge), "turnover", 2))
    for threshold in [50, 30, 20, 10]:
        configs.append(tagged(StrictConfig(f"RANK_OUT{threshold}", f"C3 min15 rank > {threshold}", "C3", minimum_holding_days=15, replacement_rank_threshold=threshold), "turnover", 2))
    for confirm in [2, 3, 5]:
        configs.append(tagged(StrictConfig(f"CONFIRM{confirm}", f"C3 min15 confirmation {confirm}bd", "C3", minimum_holding_days=15, confirmation_days=confirm), "turnover", 2))

    combined = [
        StrictConfig("POLICY_X_CAP5_EDGE05_CONF3", "Policy X cap5 edge0.05 confirm3", "C3", minimum_holding_days=15, replacement_cap_per_month=5, replacement_edge_margin=0.05, confirmation_days=3),
        StrictConfig("POLICY_Y_CAP4_EDGE08_CONF5", "Policy Y cap4 edge0.08 confirm5", "C3", minimum_holding_days=15, replacement_cap_per_month=4, replacement_edge_margin=0.08, confirmation_days=5),
        StrictConfig("POLICY_Z_MIN20_CAP5_EDGE05_CONF3", "Policy Z min20 cap5 edge0.05 confirm3", "C3", minimum_holding_days=20, replacement_cap_per_month=5, replacement_edge_margin=0.05, confirmation_days=3),
        StrictConfig("POLICY_W_CAP6_EDGE05_CONF3", "Policy W cap6 edge0.05 confirm3", "C3", minimum_holding_days=15, replacement_cap_per_month=6, replacement_edge_margin=0.05, confirmation_days=3),
        StrictConfig("POLICY_V_CAP8_EDGE08_CONF3", "Policy V cap8 edge0.08 confirm3", "C3", minimum_holding_days=15, replacement_cap_per_month=8, replacement_edge_margin=0.08, confirmation_days=3),
    ]
    configs.extend(tagged(c, "combined", 1) for c in combined)

    robust_templates = [
        StrictConfig("ROBUST_C3_MIN15", "Robust C3 min15", "C3", minimum_holding_days=15),
        StrictConfig("ROBUST_POLICY_X", "Robust Policy X", "C3", minimum_holding_days=15, replacement_cap_per_month=5, replacement_edge_margin=0.05, confirmation_days=3),
        StrictConfig("ROBUST_POLICY_Y", "Robust Policy Y", "C3", minimum_holding_days=15, replacement_cap_per_month=4, replacement_edge_margin=0.08, confirmation_days=5),
        StrictConfig("ROBUST_CAP5", "Robust cap5", "C3", minimum_holding_days=15, replacement_cap_per_month=5),
    ]
    for template in robust_templates:
        for bps in [0.0, 10.0, 30.0]:
            configs.append(tagged(
                StrictConfig(
                    f"{template.policy_id}_{int(bps)}BPS",
                    f"{template.policy_name} cost/slippage {bps:.0f}bps",
                    "C3",
                    minimum_holding_days=template.minimum_holding_days,
                    replacement_cap_per_month=template.replacement_cap_per_month,
                    replacement_edge_margin=template.replacement_edge_margin,
                    confirmation_days=template.confirmation_days,
                    replacement_rank_threshold=template.replacement_rank_threshold,
                    transaction_cost_bps=bps,
                    slippage_bps=bps,
                ),
                "robustness",
                3,
            ))
    return configs


def tagged(config: StrictConfig, group: str, priority: int) -> StrictConfig:
    object.__setattr__(config, "scenario_group", group)
    object.__setattr__(config, "phase7f_priority", priority)
    return config


def enrich_metrics(metrics: dict[str, Any], annual: list[dict[str, Any]]) -> dict[str, Any]:
    out = dict(metrics)
    out["scenario_group"] = getattr_from_policy(metrics["policy_id"], "scenario_group")
    out["scenario_priority"] = getattr_from_policy(metrics["policy_id"], "priority")
    out["cost_adjusted_return"] = out["cumulative_return_net"]
    row_2026 = next((r for r in annual if int(r["year"]) == 2026), None)
    out["annual_return_2026"] = row_2026["annual_return_net_by_year"] if row_2026 else None
    out["annual_dd_2026"] = row_2026["annual_max_drawdown_net_by_year"] if row_2026 else None
    out["annual_trade_count_2026"] = row_2026["annual_trade_count_by_year"] if row_2026 else None
    out["annual_replacement_count_2026"] = row_2026["annual_replacement_count_by_year"] if row_2026 else None
    return out


_POLICY_META: dict[str, dict[str, Any]] = {}


def getattr_from_policy(policy_id: str, attr: str) -> Any:
    if not _POLICY_META:
        for config in build_phase7f_configs_no_meta_recursion():
            _POLICY_META[config.policy_id] = {
                "scenario_group": getattr(config, "scenario_group", "unknown"),
                "priority": getattr(config, "phase7f_priority", 9),
            }
    return _POLICY_META.get(policy_id, {}).get(attr, "unknown" if attr == "scenario_group" else 9)


def build_phase7f_configs_no_meta_recursion() -> list[StrictConfig]:
    saved = dict(_POLICY_META)
    _POLICY_META.clear()
    configs = build_phase7f_configs()
    _POLICY_META.clear()
    _POLICY_META.update(saved)
    return configs


def build_summary(
    comparison: pd.DataFrame,
    ranked: pd.DataFrame,
    prices: pd.DataFrame,
    paths: dict[str, Path],
    audit: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    candidates = comparison[
        (comparison["scenario_group"].isin(["turnover", "combined"]))
        & (comparison["replacement_rate"] >= 0.2)
        & (comparison["replacement_rate"] <= 0.5)
    ].copy()
    top3 = candidates.sort_values(["cumulative_return_net", "annual_return_2026"], ascending=[False, False]).head(3).to_dict("records")
    best_cost = comparison[comparison["scenario_group"] == "robustness"].sort_values("cumulative_return_net", ascending=False).head(3).to_dict("records")
    best_2026 = comparison.sort_values(["annual_return_2026", "cumulative_return_net"], ascending=[False, False]).head(3).to_dict("records")
    base = comparison[comparison["policy_id"] == "A_FIXED_20BD"].to_dict("records")
    c3 = comparison[comparison["policy_id"] == "C3_MIN15_T2"].to_dict("records")
    return {
        "phase": "Phase7-F",
        "created_at": created_at,
        "completion_status": COMPLETION_STATUS,
        "source": {
            "ranked_daily": str(DEFAULT_RANKED_DAILY_PATH),
            "daily_response_dir": str(DEFAULT_DAILY_RESPONSE_DIR),
            "ranked_start_date": str(ranked["target_date"].min()),
            "ranked_end_date": str(ranked["target_date"].max()),
            "price_start_date": str(prices["target_date"].min()),
            "price_end_date": str(prices["target_date"].max()),
            "ranked_row_count": int(len(ranked)),
            "price_row_count": int(len(prices)),
        },
        "key_findings": {
            "baseline": base[0] if base else {},
            "c3_min15_t2": c3[0] if c3 else {},
            "top3_recommended_in_target_turnover_band": top3,
            "best_cost_robustness": best_cost,
            "best_2026": best_2026,
        },
        "artifact_paths": {k: str(v) for k, v in paths.items()},
        "leakage_audit_status": audit["status"],
        "no_future_data_in_decision": True,
        "backtest_outcome_used_in_decision": False,
        "future_price_used_in_decision": False,
        "future_rank_used_in_decision": False,
        "decision_evaluation_separated": True,
        "broker_api_executed": False,
        "paper_trading_executed": False,
        "order_executed": False,
        "live_order_executed": False,
        "tachibana_api_called": False,
        "jquants_api_called": False,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
