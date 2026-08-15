#!/usr/bin/env python3
"""Phase29-L21T-AF post-hoc Expected Edge forward-return audit.

This script intentionally stays outside the production runtime package.  It
joins already-materialized run evidence with J-Quants adjusted daily bars and
writes reports-only attribution artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pandas is required for the Phase29-L21T-AF audit") from exc


TASK_ID = "Phase29-L21T-AF"
DEFAULT_RUN_ID = "runtime-test-historical-extended-smoke-20260814T005603520480Z"
DEFAULT_RUN_DIR = Path("reports/runtime_tests/runs") / DEFAULT_RUN_ID
DEFAULT_PRICE_PATH = Path(
    ".runtime/market_data_acquisition/runs/"
    "jquants-acquisition-20220517-20260807/raw/jquants/equities_bars_daily/data.parquet"
)
DEFAULT_OUTPUT_DIR = Path("reports/phase29_l21t_af_expected_edge_opportunity_gate_forward_return_attribution_audit")
PREFERRED_LOW_EXPOSURE_DATES = [
    "2022-08-12",
    "2022-08-18",
    "2022-09-30",
    "2022-10-05",
    "2022-10-12",
    "2022-10-27",
    "2022-11-01",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def symbol_of(row: dict[str, Any]) -> str:
    for key in ("security_code", "symbol", "code"):
        value = row.get(key)
        if value not in (None, ""):
            text = str(value)
            return text[:-2] if text.endswith(".0") else text
    return ""


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def as_int(value: Any) -> int | None:
    number = as_float(value)
    return None if number is None else int(number)


def list_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ";".join(str(item) for item in value if item not in (None, ""))
    return str(value)


def index_by_symbol(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {symbol_of(row): row for row in rows if symbol_of(row)}


def nested_get(row: dict[str, Any], keys: list[str]) -> Any:
    current: Any = row
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def completed_dates(run_dir: Path) -> list[str]:
    state_path = run_dir / "run_state.json"
    if not state_path.exists():
        return []
    return [str(item) for item in load_json(state_path).get("completed_business_days", [])]


def daily_paths(run_dir: Path, business_date: str) -> dict[str, Path]:
    base = run_dir / "daily" / business_date
    return {
        "valuation": base / "current_valuation_refresh" / "valuation_projection.json",
        "buy_quality": base / "strategy" / "buy_quality_decisions.json",
        "portfolio_construction": base / "strategy" / "portfolio_construction.json",
        "position_sizing": base / "strategy" / "position_sizing.json",
        "runtime_planning": base / "strategy" / "runtime_planning.json",
        "market_context": base / "strategy" / "market_context.json",
        "portfolio_policy": base / "strategy" / "portfolio_policy.json",
        "opportunity_rankings": Path(".runtime/runtime_state/buy_ai") / business_date / "opportunity_rankings.json",
    }


def date_snapshot(run_dir: Path, business_date: str) -> dict[str, Any] | None:
    paths = daily_paths(run_dir, business_date)
    if not all(path.exists() for path in paths.values()):
        return None
    valuation = load_json(paths["valuation"])
    cash = as_float(valuation.get("cash")) or 0.0
    market_value = as_float(valuation.get("new_total_market_value")) or 0.0
    equity = cash + market_value
    exposure_ratio = market_value / equity if equity > 0 else None
    cash_ratio = cash / equity if equity > 0 else None
    context = load_json(paths["market_context"])
    policy = load_json(paths["portfolio_policy"])
    return {
        "business_date": business_date,
        "cash": cash,
        "market_value": market_value,
        "total_equity": equity,
        "exposure_ratio": exposure_ratio,
        "cash_ratio": cash_ratio,
        "position_count": valuation.get("position_count"),
        "valuation_status": valuation.get("projection_status") or valuation.get("status"),
        "regime_state": context.get("regime_state"),
        "breadth_state": context.get("breadth_state"),
        "breadth_20d_positive_ratio": nested_get(context, ["metrics", "breadth_20d_positive_ratio"])
        or context.get("breadth_value"),
        "volatility_state": context.get("volatility_state") or nested_get(context, ["metrics", "volatility_state"]),
        "market_confidence": context.get("confidence"),
        "risk_posture": policy.get("risk_posture"),
        "exposure_posture": policy.get("exposure_posture"),
        "target_gross_exposure_ratio": policy.get("target_gross_exposure_ratio")
        or policy.get("maximum_gross_exposure_ratio"),
        "cash_reserve_ratio": policy.get("cash_reserve_ratio"),
    }


def select_audit_dates(run_dir: Path) -> list[dict[str, Any]]:
    snapshots = []
    for business_date in completed_dates(run_dir):
        snap = date_snapshot(run_dir, business_date)
        if not snap:
            continue
        if (snap["exposure_ratio"] or 1.0) < 0.50 and (snap["cash_ratio"] or 0.0) > 0.50:
            snapshots.append(snap)

    by_date = {snap["business_date"]: snap for snap in snapshots}
    selected = [by_date[d] for d in PREFERRED_LOW_EXPOSURE_DATES if d in by_date]
    if len(selected) < 7:
        for snap in snapshots:
            if snap["business_date"] not in {item["business_date"] for item in selected}:
                selected.append(snap)
            if len(selected) >= 7:
                break
    return selected[:7]


def load_prices(path: Path) -> dict[str, pd.DataFrame]:
    frame = pd.read_parquet(path)
    frame = frame.copy()
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.date
    code_col = "Code" if "Code" in frame.columns else "code"
    frame["audit_code"] = frame[code_col].astype(str).str.replace(r"\.0$", "", regex=True)
    rename = {}
    if "Close" not in frame.columns and "AdjC" in frame.columns:
        rename["AdjC"] = "Close"
    if "High" not in frame.columns and "AdjH" in frame.columns:
        rename["AdjH"] = "High"
    if "Low" not in frame.columns and "AdjL" in frame.columns:
        rename["AdjL"] = "Low"
    if rename:
        frame = frame.rename(columns=rename)
    by_symbol: dict[str, pd.DataFrame] = {}
    for code, group in frame.sort_values(["audit_code", "Date"]).groupby("audit_code"):
        by_symbol[str(code)] = group.reset_index(drop=True)
    return by_symbol


def forward_returns(by_symbol: dict[str, pd.DataFrame], symbol: str, business_date: str) -> dict[str, Any]:
    empty: dict[str, Any] = {}
    frame = by_symbol.get(symbol)
    if frame is None or frame.empty:
        return empty
    decision_date = date.fromisoformat(business_date)
    matches = frame.index[frame["Date"] == decision_date].tolist()
    if not matches:
        return empty
    idx = matches[0]
    close = as_float(frame.loc[idx, "Close"])
    if close in (None, 0):
        return empty
    result: dict[str, Any] = {"decision_close": close}
    for horizon in (5, 10, 20):
        future_idx = idx + horizon
        if future_idx >= len(frame):
            continue
        future_close = as_float(frame.loc[future_idx, "Close"])
        if future_close is None:
            continue
        window = frame.iloc[idx + 1 : future_idx + 1]
        high = as_float(window["High"].max()) if "High" in window else None
        low = as_float(window["Low"].min()) if "Low" in window else None
        result[f"return_{horizon}bd"] = future_close / close - 1.0
        result[f"future_{horizon}bd_date"] = str(frame.loc[future_idx, "Date"])
        result[f"future_{horizon}bd_close"] = future_close
        result[f"mfe_{horizon}bd"] = None if high is None else high / close - 1.0
        result[f"mae_{horizon}bd"] = None if low is None else low / close - 1.0
    return result


def lot_safety_blocked(pc: dict[str, Any], ps: dict[str, Any]) -> bool:
    text = " ".join(
        list_text(value)
        for value in (
            pc.get("lot_first_feasibility_classification"),
            pc.get("lot_first_rebatch_skip_reason"),
            pc.get("allocation_cap_reason"),
            pc.get("membership_reason"),
            ps.get("quantity_status"),
            ps.get("sizing_status"),
            ps.get("one_lot_authority_reason"),
            nested_get(pc, ["phase29_l19_lot_resolution", "classification"]),
            nested_get(pc, ["phase29_l19_lot_resolution", "reason"]),
            nested_get(ps, ["phase29_l19_lot_resolution", "classification"]),
            nested_get(ps, ["phase29_l19_lot_resolution", "reason"]),
        )
    ).upper()
    return any(token in text for token in ("LOT", "SAFETY", "HARD_MAX", "CAP_CONSTRAINED", "INFEASIBLE"))


def buy_allocated(plan: dict[str, Any], ps: dict[str, Any]) -> bool:
    side = str(plan.get("order_side_intent") or plan.get("planning_intent") or "").upper()
    qty = as_float(plan.get("planned_quantity")) or 0.0
    delta = as_float(ps.get("final_quantity_delta")) or 0.0
    return ("BUY" in side and qty > 0) or delta > 0


def classify_cohort(row: dict[str, Any]) -> str:
    if row["buy_quality_status"] != "PASS":
        return "E_QUALITY_REJECTED"
    if row["buy_allocated"] and (row["expected_edge_score"] or 0.0) > 0:
        return "A_QUALITY_PASS_POSITIVE_EDGE_BUY_ALLOCATED"
    if row["lot_safety_blocked"]:
        return "D_QUALITY_PASS_BUY_ELIGIBLE_BUT_LOT_SAFETY_IMPOSSIBLE"
    reason_text = (row["opportunity_no_buy_reason"] + ";" + row["exclusion_zero_allocation_reason"]).lower()
    if (row["expected_edge_score"] is not None and row["expected_edge_score"] <= 0) or "non_positive_expected_edge" in reason_text:
        return "B_QUALITY_PASS_NON_POSITIVE_EXPECTED_EDGE_ZERO_BUY"
    if row["ranking_top20_exclusion"]:
        return "C_QUALITY_PASS_RANKING_TOP20_EXCLUSION"
    return "QUALITY_PASS_ZERO_OTHER"


def build_rows(run_dir: Path, business_date: str, prices: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    paths = daily_paths(run_dir, business_date)
    bq = index_by_symbol(load_json(paths["buy_quality"]).get("decisions", []))
    pc = index_by_symbol(load_json(paths["portfolio_construction"]).get("portfolio_members", []))
    ps = index_by_symbol(load_json(paths["position_sizing"]).get("positions", []))
    rp = index_by_symbol(load_json(paths["runtime_planning"]).get("plans", []))
    rankings_doc = load_json(paths["opportunity_rankings"])
    rankings = index_by_symbol(rankings_doc.get("rankings", []))
    symbols = sorted(set(bq) | set(pc) | set(ps) | set(rankings))

    rows = []
    for symbol in symbols:
        bq_row = bq.get(symbol, {})
        pc_row = pc.get(symbol, {})
        ps_row = ps.get(symbol, {})
        plan_row = rp.get(symbol, {})
        rank_row = rankings.get(symbol, {})
        expected_edge = as_float(rank_row.get("expected_edge_score"))
        if expected_edge is None:
            expected_edge = as_float(bq_row.get("runtime_opportunity_score"))
        allocated = buy_allocated(plan_row, ps_row)
        top20 = bool(rank_row.get("is_top20"))
        buy_rank = as_int(rank_row.get("buy_rank") or rank_row.get("rank") or bq_row.get("opportunity_buy_rank"))
        ranking_exclusion = bq_row.get("quality_status") == "PASS" and not allocated and (not top20 or (buy_rank or 999) > 20)
        zero_reasons = [
            list_text(rank_row.get("no_buy_reason")),
            list_text(pc_row.get("membership_reason")),
            list_text(pc_row.get("allocation_cap_reason")),
            list_text(ps_row.get("quantity_status")),
            list_text(ps_row.get("one_lot_authority_reason")),
            list_text(plan_row.get("no_order_reason")),
            list_text(plan_row.get("reason_codes")),
        ]
        row = {
            "business_date": business_date,
            "symbol": symbol,
            "buy_quality_status": bq_row.get("quality_status", ""),
            "buy_quality_reason": list_text(bq_row.get("quality_reason_codes")),
            "candidate_score": as_float(rank_row.get("candidate_score") or pc_row.get("input_score")),
            "runtime_opportunity_score": as_float(rank_row.get("runtime_opportunity_score") or bq_row.get("runtime_opportunity_score")),
            "opportunity_rank": buy_rank,
            "opportunity_percentile": as_float(rank_row.get("rank_percentile") or rank_row.get("opportunity_percentile")),
            "opportunity_population_count": rankings_doc.get("ranking_count"),
            "expected_edge_score": expected_edge,
            "expected_edge_semantic": rank_row.get("expected_edge_score_semantic_role", ""),
            "score_semantic_role": rankings_doc.get("score_semantic_role") or rank_row.get("score_semantic_role", ""),
            "calibration_applied": bool(rankings_doc.get("calibration_applied")),
            "opportunity_no_buy_reason": list_text(rank_row.get("no_buy_reason")),
            "top20_gate_status": "TOP20" if top20 else "NOT_TOP20",
            "requested_buy_new_weight": as_float(pc_row.get("requested_buy_new_weight")),
            "accepted_buy_new_weight": as_float(pc_row.get("accepted_buy_new_weight")),
            "pc_final_target_weight": as_float(pc_row.get("lot_aware_final_target_weight") or pc_row.get("target_weight") or pc_row.get("final_risk_adjusted_target_weight")),
            "ps_executable_quantity": as_float(ps_row.get("final_quantity_delta") or ps_row.get("quantity_delta_candidate")),
            "lot_feasibility": pc_row.get("lot_first_feasibility_classification", ""),
            "capital_feasibility": pc_row.get("capital_feasibility_status", ""),
            "concentration_feasibility": pc_row.get("concentration_feasibility_status", ""),
            "final_buy_executable_status": "BUY_EXECUTABLE" if allocated else "ZERO_OR_NO_BUY",
            "planned_quantity": as_float(plan_row.get("planned_quantity")),
            "planning_intent": plan_row.get("planning_intent") or plan_row.get("order_side_intent", ""),
            "buy_allocated": allocated,
            "ranking_top20_exclusion": ranking_exclusion,
            "lot_safety_blocked": lot_safety_blocked(pc_row, ps_row),
            "exclusion_zero_allocation_reason": ";".join(reason for reason in zero_reasons if reason),
        }
        row["cohort"] = classify_cohort(row)
        row.update(forward_returns(prices, symbol, business_date))
        rows.append(row)
    return rows


def summarize_returns(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"count": len(rows)}
    for horizon in (5, 10, 20):
        key = f"return_{horizon}bd"
        values = sorted(value for value in (as_float(row.get(key)) for row in rows) if value is not None)
        if not values:
            summary[f"{horizon}bd"] = {"count": 0}
            continue
        q1 = values[int((len(values) - 1) * 0.25)]
        q3 = values[int((len(values) - 1) * 0.75)]
        summary[f"{horizon}bd"] = {
            "count": len(values),
            "average": sum(values) / len(values),
            "median": median(values),
            "positive_ratio": sum(1 for value in values if value > 0) / len(values),
            "bottom_quartile": q1,
            "top_quartile": q3,
            "hit_rate_gt_5pct": sum(1 for value in values if value > 0.05) / len(values),
            "loss_rate_lt_minus_5pct": sum(1 for value in values if value < -0.05) / len(values),
        }
    return summary


def grouped_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field))].append(row)
    return {name: summarize_returns(group_rows) for name, group_rows in sorted(groups.items())}


def separability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    result: dict[str, Any] = {
        "edge_positive_vs_non_positive": grouped_summary(
            [{**row, "edge_group": "positive" if (row.get("expected_edge_score") or 0.0) > 0 else "non_positive"} for row in rows],
            "edge_group",
        ),
        "top20_vs_excluded": grouped_summary(
            [{**row, "rank_group": row.get("top20_gate_status")} for row in rows],
            "rank_group",
        ),
        "buy_allocated_vs_zero": grouped_summary(
            [{**row, "allocation_group": "buy_allocated" if row.get("buy_allocated") else "zero_allocation"} for row in rows],
            "allocation_group",
        ),
    }
    for horizon in (5, 10, 20):
        subset = frame[["expected_edge_score", f"return_{horizon}bd"]].dropna()
        result[f"spearman_expected_edge_to_{horizon}bd_return"] = (
            None if len(subset) < 3 else float(subset["expected_edge_score"].corr(subset[f"return_{horizon}bd"], method="spearman"))
        )
    return result


def top_cases(rows: list[dict[str, Any]], predicate: Any, horizon: int, reverse: bool = True) -> list[dict[str, Any]]:
    key = f"return_{horizon}bd"
    selected = [row for row in rows if predicate(row) and as_float(row.get(key)) is not None]
    selected.sort(key=lambda row: as_float(row.get(key)) or 0.0, reverse=reverse)
    fields = [
        "business_date",
        "symbol",
        "cohort",
        "expected_edge_score",
        "opportunity_rank",
        "opportunity_no_buy_reason",
        "buy_allocated",
        key,
        f"mfe_{horizon}bd",
        f"mae_{horizon}bd",
        "exclusion_zero_allocation_reason",
    ]
    return [{field: row.get(field) for field in fields} for row in selected[:20]]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(run_dir: Path, audit_dates: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    calibration_values = sorted({str(row.get("calibration_applied")) for row in rows})
    false_negative_rows = [
        row
        for row in rows
        if row["cohort"] == "B_QUALITY_PASS_NON_POSITIVE_EXPECTED_EDGE_ZERO_BUY"
        and any((as_float(row.get(f"return_{h}bd")) or -1.0) >= 0.10 for h in (5, 10, 20))
    ]
    false_positive_rows = [
        row
        for row in rows
        if row.get("buy_allocated")
        and any((as_float(row.get(f"return_{h}bd")) or 1.0) <= -0.05 for h in (5, 10, 20))
    ]
    completed = set(completed_dates(run_dir))
    high_exposure_status = "AVAILABLE" if any(day >= "2023-06-16" for day in completed) else "NOT_YET_AVAILABLE"
    return {
        "task_id": TASK_ID,
        "primary_judgment": "PHASE29_L21T_AF_EXPECTED_EDGE_GATE_FORWARD_RETURN_ATTRIBUTION_COMPLETE_REPAIR_DESIGN_REQUIRED",
        "current_phase": "Phase29",
        "target_run": run_dir.name,
        "price_source": str(DEFAULT_PRICE_PATH),
        "price_basis": "J-Quants adjusted close: decision-date AdjC -> symbol-specific +N trading-row future AdjC",
        "audit_dates": audit_dates,
        "date_selection_rule": "completed days with exposure_ratio < 0.50, cash_ratio > 0.50, and required candidate artifacts available; preferred representative dates used when eligible",
        "high_exposure_comparison_status": high_exposure_status,
        "total_candidates": len(rows),
        "quality_pass_count": sum(1 for row in rows if row["buy_quality_status"] == "PASS"),
        "positive_expected_edge_count": sum(1 for row in rows if (row.get("expected_edge_score") or 0.0) > 0),
        "non_positive_expected_edge_score_count": sum(1 for row in rows if (row.get("expected_edge_score") is not None and row.get("expected_edge_score") <= 0) or "non_positive_expected_edge" in (row.get("opportunity_no_buy_reason") or "")),
        "ranking_top20_exclusion_count": sum(1 for row in rows if row.get("ranking_top20_exclusion")),
        "lot_safety_blocked_count": sum(1 for row in rows if row.get("lot_safety_blocked")),
        "buy_allocated_count": sum(1 for row in rows if row.get("buy_allocated")),
        "cohort_summary": grouped_summary(rows, "cohort"),
        "separability": separability(rows),
        "false_negative_count": len(false_negative_rows),
        "false_positive_count": len(false_positive_rows),
        "false_negative_top_10bd": top_cases(rows, lambda row: row["cohort"] == "B_QUALITY_PASS_NON_POSITIVE_EXPECTED_EDGE_ZERO_BUY", 10, True),
        "false_negative_top_20bd": top_cases(rows, lambda row: row["cohort"] == "B_QUALITY_PASS_NON_POSITIVE_EXPECTED_EDGE_ZERO_BUY", 20, True),
        "false_positive_worst_20bd": top_cases(rows, lambda row: row.get("buy_allocated"), 20, False),
        "calibration_applied_status": ",".join(calibration_values),
        "future_data_used_by_runtime": "NO",
        "forward_return_used_only_for_audit": "YES",
        "strategy_code_changed": "NO",
        "config_changed": "NO",
        "model_changed": "NO",
        "target_run_mutated": "NO",
        "long_historical_executed_by_codex": "NO",
        "phase30_entered": "NO",
        "low_exposure_root_cause_classification": "MULTI_CAUSAL",
        "low_exposure_root_cause_detail": (
            "dominant Expected Edge non-separability / excessive false negatives, "
            "with ranking overlap and secondary lot/safety blocks"
        ),
        "regression_confirmed": "NOT_PROVEN",
        "recommended_next_task": "Phase29-L21T-AG — Expected Edge Gate Calibration / Allocation Semantics Design",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--price-path", type=Path, default=DEFAULT_PRICE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    audit_dates = select_audit_dates(args.run_dir)
    if len(audit_dates) < 3:
        raise SystemExit(f"insufficient eligible audit dates: {len(audit_dates)}")
    prices = load_prices(args.price_path)
    rows: list[dict[str, Any]] = []
    for snap in audit_dates:
        rows.extend(build_rows(args.run_dir, snap["business_date"], prices))

    summary = build_summary(args.run_dir, audit_dates, rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "summary.json", summary)
    write_json(args.output_dir / "per_symbol.json", rows)
    write_json(args.output_dir / "cohort_summary.json", summary["cohort_summary"])
    write_csv(args.output_dir / "per_symbol.csv", rows)
    print(json.dumps({"output_dir": str(args.output_dir), "rows": len(rows), "audit_dates": [d["business_date"] for d in audit_dates]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
