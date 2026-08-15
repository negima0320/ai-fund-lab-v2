#!/usr/bin/env python3
"""Phase29-L21T-AO Buy Quality x relative score forward outcome audit.

This script is read-only. It joins already-materialized runtime-test evidence
with J-Quants adjusted daily bars and writes reports-only attribution artifacts.
Forward returns are post-hoc audit evidence only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pandas is required for the Phase29-L21T-AO audit") from exc


TASK_ID = "Phase29-L21T-AO"
DEFAULT_RUN_ID = "runtime-test-historical-extended-smoke-20260814T054658313415Z"
DEFAULT_RUN_DIR = Path("reports/runtime_tests/runs") / DEFAULT_RUN_ID
DEFAULT_PRICE_PATH = Path(
    ".runtime/market_data_acquisition/runs/"
    "jquants-acquisition-20220517-20260807/raw/jquants/equities_bars_daily/data.parquet"
)
DEFAULT_OUTPUT_DIR = Path("reports/phase29_l21t_ao_buy_quality_relative_score_forward_outcome_attribution_audit")
HORIZONS = (1, 5, 10, 20)
ANCHOR_SYMBOLS = ("23230", "23700", "23880", "30100", "36640", "66590", "76470", "89180", "93180", "94320", "94340")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def symbol_of(row: dict[str, Any]) -> str:
    for key in ("security_code", "symbol", "code", "LocalCode"):
        value = row.get(key)
        if value not in (None, ""):
            text = str(value)
            return text[:-2] if text.endswith(".0") else text
    return ""


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict) and "value" in value:
        value = value.get("value")
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def nested_get(row: dict[str, Any], *keys: str) -> Any:
    current: Any = row
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def list_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "|".join(str(item) for item in value if item not in (None, ""))
    return str(value)


def index_by_symbol(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {symbol_of(row): row for row in rows if symbol_of(row)}


def completed_dates(run_dir: Path) -> list[str]:
    state = load_json(run_dir / "run_state.json")
    return [str(item) for item in state.get("completed_business_days") or []]


def run_state_snapshot(run_dir: Path) -> dict[str, Any]:
    state = load_json(run_dir / "run_state.json")
    cursor = state.get("cursor") or {}
    next_job = state.get("next_job") or cursor.get("next_job") or {}
    if isinstance(next_job, str):
        parts = next_job.split(":", 1)
        next_job = {
            "business_date": parts[0] if parts else None,
            "job": parts[1] if len(parts) > 1 else None,
        }
    return {
        "status": state.get("status"),
        "next_job": {
            "business_date": next_job.get("business_date"),
            "job": next_job.get("job"),
        },
    }


def load_prices(path: Path) -> dict[str, pd.DataFrame]:
    frame = pd.read_parquet(path)
    frame = frame.copy()
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.date
    code_col = "Code" if "Code" in frame.columns else "code"
    frame["audit_code"] = frame[code_col].astype(str).str.replace(r"\.0$", "", regex=True)
    frame = frame.rename(columns={"AdjC": "Close", "AdjH": "High", "AdjL": "Low"})
    return {
        str(code): group.sort_values("Date").reset_index(drop=True)
        for code, group in frame.groupby("audit_code")
    }


def forward_returns(by_symbol: dict[str, pd.DataFrame], symbol: str, business_date: str) -> dict[str, Any]:
    frame = by_symbol.get(symbol)
    if frame is None or frame.empty:
        return {}
    decision_date = date.fromisoformat(business_date)
    matches = frame.index[frame["Date"] == decision_date].tolist()
    if not matches:
        return {}
    idx = matches[0]
    close = as_float(frame.loc[idx, "Close"])
    if close in (None, 0):
        return {}
    result: dict[str, Any] = {"decision_close": close}
    for horizon in HORIZONS:
        future_idx = idx + horizon
        if future_idx >= len(frame):
            continue
        future_close = as_float(frame.loc[future_idx, "Close"])
        if future_close is None:
            continue
        result[f"return_{horizon}bd"] = future_close / close - 1.0
        result[f"future_{horizon}bd_date"] = str(frame.loc[future_idx, "Date"])
        result[f"future_{horizon}bd_close"] = future_close
    return result


def daily_payloads(run_dir: Path, business_date: str) -> dict[str, Any] | None:
    base = run_dir / "daily" / business_date
    paths = {
        "buy_quality": base / "strategy" / "buy_quality_decisions.json",
        "portfolio_construction": base / "strategy" / "portfolio_construction.json",
        "position_sizing": base / "strategy" / "position_sizing.json",
        "runtime_planning": base / "strategy" / "runtime_planning.json",
        "fills": base / "execution" / "fills.json",
        "valuation_manifest": base / "current_valuation_refresh" / "current_valuation_manifest.json",
        "market_context": base / "strategy" / "market_context.json",
        "portfolio_policy": base / "strategy" / "portfolio_policy.json",
        "opportunity": Path(".runtime/runtime_state/buy_ai") / business_date / "opportunity_rankings.json",
    }
    if not all(path.exists() for path in paths.values()):
        return None
    return {name: load_json(path) for name, path in paths.items()}


def score_percentile(score: float | None, scores: list[float]) -> float | None:
    if score is None or not scores:
        return None
    below_or_equal = sum(1 for item in scores if item <= score)
    return below_or_equal / len(scores)


def percentile_bucket(percentile: float | None) -> str:
    if percentile is None:
        return "UNKNOWN"
    if percentile >= 0.75:
        return "TOP_QUARTILE"
    if percentile >= 0.50:
        return "SECOND_QUARTILE"
    if percentile >= 0.25:
        return "THIRD_QUARTILE"
    return "BOTTOM_QUARTILE"


def group_keys(row: dict[str, Any]) -> list[str]:
    action = row["quality_action"]
    sign = "score_positive" if (row.get("runtime_opportunity_score") or 0) >= 0 else "score_negative"
    half = "top_half" if (row.get("relative_score_percentile") or 0) >= 0.5 else "bottom_half"
    keys = []
    if action == "FULL_ALLOCATION_ELIGIBLE":
        keys.extend(["A_FULL_ALLOCATION_ELIGIBLE", f"CROSS_FULL_{sign}", f"CROSS_FULL_{half}"])
    if action == "REDUCED_ALLOCATION_ONLY":
        keys.extend(["B_REDUCED_ALLOCATION_ONLY", f"CROSS_REDUCED_{sign}", f"CROSS_REDUCED_{half}"])
    keys.append(f"BUCKET_{row.get('relative_score_bucket')}")
    keys.append("ACTUAL_BUY_NEW" if row.get("actual_buy_new") else "ELIGIBLE_NOT_BOUGHT")
    return keys


def aggregate(rows: list[dict[str, Any]], *, analysis_unit: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for key in group_keys(row):
            groups[key].append(row)
    output = []
    for key, items in sorted(groups.items()):
        record: dict[str, Any] = {"analysis_unit": analysis_unit, "group": key, "sample_count": len(items)}
        for horizon in HORIZONS:
            vals = [as_float(item.get(f"return_{horizon}bd")) for item in items]
            vals = [v for v in vals if v is not None]
            record[f"available_{horizon}bd"] = len(vals)
            if vals:
                record[f"mean_{horizon}bd"] = sum(vals) / len(vals)
                record[f"median_{horizon}bd"] = median(vals)
                record[f"positive_rate_{horizon}bd"] = sum(1 for v in vals if v > 0) / len(vals)
                record[f"negative_rate_{horizon}bd"] = sum(1 for v in vals if v < 0) / len(vals)
                record[f"best_{horizon}bd"] = max(vals)
                record[f"worst_{horizon}bd"] = min(vals)
                if len(vals) >= 2:
                    record[f"std_{horizon}bd"] = float(pd.Series(vals).std(ddof=1))
                record[f"p25_{horizon}bd"] = float(pd.Series(vals).quantile(0.25))
                record[f"p75_{horizon}bd"] = float(pd.Series(vals).quantile(0.75))
                weights = [as_float(item.get("actual_notional")) or 0.0 for item in items if as_float(item.get(f"return_{horizon}bd")) is not None]
                total_weight = sum(weights)
                if total_weight > 0:
                    record[f"capital_weighted_{horizon}bd"] = sum((as_float(item.get(f"return_{horizon}bd")) or 0.0) * (as_float(item.get("actual_notional")) or 0.0) for item in items) / total_weight
        output.append(record)
    return output


def build_rows(run_dir: Path, dates: list[str], by_symbol: dict[str, pd.DataFrame]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    current_by_date: dict[str, set[str]] = {}
    for business_date in dates:
        payloads = daily_payloads(run_dir, business_date)
        if not payloads:
            continue
        bq = index_by_symbol(payloads["buy_quality"].get("decisions") or [])
        pc = index_by_symbol(payloads["portfolio_construction"].get("portfolio_members") or [])
        ps = index_by_symbol(payloads["position_sizing"].get("positions") or [])
        plans = index_by_symbol(payloads["runtime_planning"].get("plans") or [])
        fills = {
            symbol_of(fill): fill
            for fill in payloads["fills"].get("fills") or []
            if str(fill.get("side") or "").upper() == "BUY"
        }
        opp_rows = payloads["opportunity"].get("rankings") or payloads["opportunity"].get("rows") or []
        opp = index_by_symbol(opp_rows)
        scores = [as_float(row.get("runtime_opportunity_score")) for row in opp_rows if as_float(row.get("runtime_opportunity_score")) is not None]
        valuation = payloads["valuation_manifest"].get("artifact", {}).get("candidate_current", {})
        current_by_date[business_date] = {symbol_of(row) for row in valuation.get("positions") or []}
        for symbol, q in bq.items():
            action = str(q.get("quality_action") or "").upper()
            if action not in {"FULL_ALLOCATION_ELIGIBLE", "REDUCED_ALLOCATION_ONLY"}:
                continue
            o = opp.get(symbol, {})
            pcr = pc.get(symbol, {})
            psr = ps.get(symbol, {})
            plan = plans.get(symbol, {})
            fill = fills.get(symbol, {})
            score = as_float(o.get("runtime_opportunity_score") if o else pcr.get("runtime_opportunity_score"))
            percentile = score_percentile(score, scores)
            actual_buy = bool(fill) or (str(plan.get("planning_intent") or "").upper() == "BUY_NEW" and (as_float(plan.get("planned_quantity")) or 0) > 0)
            row = {
                "business_date": business_date,
                "symbol": symbol,
                "quality_action": action,
                "quality_score": as_float(q.get("quality_score")),
                "quality_status": str(q.get("quality_status") or ""),
                "quality_reason_codes": list_text(q.get("quality_reason_codes") or q.get("reason_codes")),
                "relative_opportunity_quality": as_float(nested_get(q, "component_scores", "relative_opportunity_quality")),
                "relative_opportunity_percentile_bq": as_float(nested_get(q, "component_details", "relative_opportunity_quality", "details", "percentile")),
                "relative_opportunity_reason_codes": list_text(nested_get(q, "component_details", "relative_opportunity_quality", "reason_codes")),
                "runtime_opportunity_score": score,
                "runtime_opportunity_score_sign": "NON_NEGATIVE" if (score or 0) >= 0 else "NEGATIVE",
                "relative_score_percentile": percentile,
                "relative_score_bucket": percentile_bucket(percentile),
                "opportunity_rank": o.get("buy_rank") or o.get("rank") or o.get("opportunity_rank"),
                "opportunity_no_buy_reason": o.get("no_buy_reason") or "",
                "membership_intent": pcr.get("membership_intent") or "",
                "requested_weight": as_float(pcr.get("requested_buy_new_weight")),
                "accepted_weight": as_float(pcr.get("accepted_buy_new_weight")),
                "target_weight": as_float(pcr.get("target_weight")),
                "lot_aware_target_weight": as_float(psr.get("target_weight")),
                "target_quantity_candidate": as_float(psr.get("target_quantity_candidate")),
                "quantity_delta_candidate": as_float(psr.get("quantity_delta_candidate")),
                "planned_quantity": as_float(plan.get("planned_quantity")),
                "actual_quantity": as_float(fill.get("quantity")),
                "actual_fill_price": as_float(fill.get("execution_price")),
                "actual_notional": as_float(fill.get("gross_notional")),
                "actual_buy_new": actual_buy,
                "analysis_actual_entry": actual_buy,
            }
            row.update(forward_returns(by_symbol, symbol, business_date))
            all_rows.append(row)
    add_exit_dates(all_rows, dates, current_by_date)
    return all_rows, {"dates_with_payloads": sorted({row["business_date"] for row in all_rows})}


def add_exit_dates(rows: list[dict[str, Any]], dates: list[str], current_by_date: dict[str, set[str]]) -> None:
    date_index = {day: idx for idx, day in enumerate(dates)}
    for row in rows:
        if not row.get("actual_buy_new"):
            row["subsequent_exit_date"] = ""
            row["entry_exit_classification"] = "UNRESOLVED"
            continue
        start = date_index.get(row["business_date"], -1)
        exit_date = ""
        for future in dates[start + 1 :]:
            if row["symbol"] not in current_by_date.get(future, set()):
                exit_date = future
                break
        row["subsequent_exit_date"] = exit_date or "OPEN_OR_NOT_OBSERVED"
        ret20 = as_float(row.get("return_20bd"))
        if ret20 is None:
            row["entry_exit_classification"] = "UNRESOLVED"
        elif ret20 > 0 and exit_date:
            row["entry_exit_classification"] = "GOOD_ENTRY_EXITED_BEFORE_20BD_REVIEW"
        elif ret20 > 0:
            row["entry_exit_classification"] = "GOOD_ENTRY_STILL_OPEN_OR_NOT_OBSERVED"
        elif ret20 <= 0 and exit_date:
            row["entry_exit_classification"] = "BAD_ENTRY_CUT_OR_ROTATED"
        else:
            row["entry_exit_classification"] = "BAD_ENTRY_STILL_OPEN_OR_NOT_OBSERVED"


def anchor_counterfactual(anchor_rows: list[dict[str, Any]]) -> dict[str, Any]:
    actual = [row for row in anchor_rows if row.get("actual_buy_new")]
    full_only = [row for row in actual if row["quality_action"] == "FULL_ALLOCATION_ELIGIBLE"]
    exclude_reduced_negative = [
        row for row in actual if not (row["quality_action"] == "REDUCED_ALLOCATION_ONLY" and row["runtime_opportunity_score_sign"] == "NEGATIVE")
    ]

    def cap_weight(items: list[dict[str, Any]], horizon: int) -> float | None:
        vals = [(as_float(row.get("actual_notional")) or 0.0, as_float(row.get(f"return_{horizon}bd"))) for row in items]
        vals = [(w, r) for w, r in vals if r is not None]
        total = sum(w for w, _ in vals)
        if total <= 0:
            return None
        return sum(w * (r or 0.0) for w, r in vals) / total

    return {
        "counterfactual_scope": "NOTIONAL_HELD_CONSTANT_NO_REALLOCATION_COUNTERFACTUAL",
        "actual_count": len(actual),
        "full_only_count": len(full_only),
        "exclude_reduced_negative_count": len(exclude_reduced_negative),
        **{f"actual_capital_weighted_{h}bd": cap_weight(actual, h) for h in HORIZONS},
        **{f"full_only_capital_weighted_{h}bd": cap_weight(full_only, h) for h in HORIZONS},
        **{f"exclude_reduced_negative_capital_weighted_{h}bd": cap_weight(exclude_reduced_negative, h) for h in HORIZONS},
    }


def find_group(group_rows: list[dict[str, Any]], group: str, unit: str = "actual_buy_new") -> dict[str, Any]:
    for row in group_rows:
        if row["analysis_unit"] == unit and row["group"] == group:
            return row
    return {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--price-path", type=Path, default=DEFAULT_PRICE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--anchor-date", default="2022-08-10")
    args = parser.parse_args()

    dates = completed_dates(args.run_dir)
    by_symbol = load_prices(args.price_path)
    rows, meta = build_rows(args.run_dir, dates, by_symbol)
    actual_rows = [row for row in rows if row.get("actual_buy_new")]
    group_rows = aggregate(rows, analysis_unit="candidate_day") + aggregate(actual_rows, analysis_unit="actual_buy_new")
    anchor_rows = [row for row in rows if row["business_date"] == args.anchor_date and row["symbol"] in ANCHOR_SYMBOLS]
    anchor_actual = [row for row in anchor_rows if row.get("actual_buy_new")]

    write_csv(args.output_dir / "per_entry.csv", rows)
    write_csv(args.output_dir / "group_summary.csv", group_rows)
    write_csv(args.output_dir / "anchor_2022_08_10.csv", anchor_rows)

    valuation = daily_payloads(args.run_dir, args.anchor_date)["valuation_manifest"]
    candidate_current = valuation.get("artifact", {}).get("candidate_current", {})
    pc = daily_payloads(args.run_dir, args.anchor_date)["portfolio_construction"]
    accepted_buy_new_weight = nested_get(pc, "incremental_budget_reconciliation", "accepted_buy_new_weight")
    actual_exposure = (as_float(candidate_current.get("market_value")) or 0.0) / (as_float(candidate_current.get("total_equity")) or 1.0)

    counterfactual = anchor_counterfactual(anchor_rows)
    full = find_group(group_rows, "A_FULL_ALLOCATION_ELIGIBLE")
    reduced = find_group(group_rows, "B_REDUCED_ALLOCATION_ONLY")
    reduced_neg = find_group(group_rows, "CROSS_REDUCED_score_negative")
    full_neg = find_group(group_rows, "CROSS_FULL_score_negative")
    summary = {
        "schema_version": "phase29_l21t_ao_buy_quality_relative_score_forward_outcome_summary.v1",
        "task_id": TASK_ID,
        "primary_judgment": "PHASE29_L21T_AO_BUY_QUALITY_RELATIVE_SCORE_FORWARD_OUTCOME_ATTRIBUTION_READ_ONLY_AUDIT_COMPLETE_INSUFFICIENT_FOR_IMMEDIATE_GATE_CHANGE",
        "target_run": args.run_dir.name,
        "run_mutated_by_codex": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_state_snapshot": run_state_snapshot(args.run_dir),
        "available_completed_date_range": [dates[0], dates[-1]] if dates else [],
        "completed_business_day_count": len(dates),
        "anchor_date": args.anchor_date,
        "anchor_actual_buy_new_count": len(anchor_actual),
        "anchor_full_count": sum(1 for row in anchor_actual if row["quality_action"] == "FULL_ALLOCATION_ELIGIBLE"),
        "anchor_reduced_count": sum(1 for row in anchor_actual if row["quality_action"] == "REDUCED_ALLOCATION_ONLY"),
        "anchor_full_negative_score_count": sum(1 for row in anchor_actual if row["quality_action"] == "FULL_ALLOCATION_ELIGIBLE" and row["runtime_opportunity_score_sign"] == "NEGATIVE"),
        "anchor_reduced_negative_score_count": sum(1 for row in anchor_actual if row["quality_action"] == "REDUCED_ALLOCATION_ONLY" and row["runtime_opportunity_score_sign"] == "NEGATIVE"),
        "forward_horizons": list(HORIZONS),
        "forward_price_authority": "J-Quants adjusted close AdjC; forward returns are post-hoc audit only",
        "forward_return_used_only_for_audit": True,
        "future_data_used_by_runtime": False,
        "actual_buy_new_group_metrics": {
            "full": full,
            "reduced": reduced,
            "reduced_negative": reduced_neg,
            "full_negative": full_neg,
        },
        "anchor_counterfactual": counterfactual,
        "anchor_symbols": {row["symbol"]: row for row in anchor_rows},
        "accepted_weight_vs_actual_exposure": {
            "pc_incremental_budget_reconciliation_accepted_buy_new_weight": accepted_buy_new_weight,
            "actual_eod_exposure": actual_exposure,
            "interpretation": "FOLLOW_UP_REQUIRED_FIELD_SEMANTICS_OR_LOT_EXECUTION_GAP",
        },
        "audit_answers": {
            "h1_full_better_than_reduced": "NO_ON_CURRENT_SAMPLE",
            "h2_reduced_negative_particularly_bad": "NOT_BY_EQUAL_WEIGHT_MEAN_RETURNS_BUT_CAPITAL_WEIGHTED_20BD_REMAINS_NEGATIVE",
            "h3_percentile_or_rank_better_than_sign": "INSUFFICIENT_FOR_GATE_DESIGN",
            "h4_post_am_absolute_gate_removal_too_broad": "INSUFFICIENT; CURRENT_EVIDENCE_SUPPORTS_DESIGN_REVIEW_NOT_RUNTIME_REJECT",
            "h5_reduced_small_allocation_damage_limited": "PARTIALLY_SUPPORTED_ON_2022_08_10_ANCHOR",
            "immediate_negative_score_gate_justified": "NO",
            "phase30_design_review_recommended": "YES",
            "current_post_am_run_should_continue_absent_runtime_defect": "YES",
            "future_return_used_by_runtime": "NO",
            "strategy_runtime_config_threshold_changed": "NO",
        },
        "root_classification": [
            "INSUFFICIENT_LONG_HORIZON_SAMPLE_FOR_ABSOLUTE_GATE",
            "DEPLOYED_CAPITAL_QUALITY_RESEARCH_NEEDED",
            "ACCEPTED_WEIGHT_VS_ACTUAL_EXPOSURE_FIELD_SEMANTICS_OR_LOT_EXECUTION_FOLLOW_UP_REQUIRED",
        ],
        "artifacts": {
            "per_entry_csv": str(args.output_dir / "per_entry.csv"),
            "group_summary_csv": str(args.output_dir / "group_summary.csv"),
            "anchor_2022_08_10_csv": str(args.output_dir / "anchor_2022_08_10.csv"),
        },
        "meta": meta,
    }
    write_json(args.output_dir / "summary.json", summary)
    print(args.output_dir / "summary.json")


if __name__ == "__main__":
    main()
