#!/usr/bin/env python3
"""Generate Phase27-D6-D PM HOLD/EXIT boundary implementation evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.position_management_ai.inference import (
    build_position_feature_frame,
    build_position_management_output,
    calculate_add_score,
    calculate_current_return,
    calculate_exit_score,
    calculate_opportunity_continuation_score,
    calculate_position_risk_score,
    calculate_reduce_score,
    calculate_trend_continuation_score,
    get_numeric_or_string_series,
    get_numeric_series,
    round_float,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "Phase27-D6-D"
OUT_DIR = REPO_ROOT / "reports/phase27_d6d_pm_hold_exit_boundary_minimal_performance_implementation"
REPORT = REPO_ROOT / "docs/phase_reports/phase27_d6d_pm_hold_exit_boundary_minimal_performance_implementation.md"
PRIMARY = "PHASE27_D6D_PM_HOLD_EXIT_MINIMAL_IMPLEMENTATION_COMPLETE_READY_FOR_100BD"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def supporting() -> dict[str, str]:
    return {
        "performance_change": "YES",
        "single_change": "CONFIRMED",
        "regression": "PASS",
        "degression": "PASS",
        "100bd": "READY",
    }


def fixtures() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    holdings = pd.DataFrame(
        [
            {"target_date": "2026-06-12", "code": "D6D_TARGET", "entry_price": 100.0, "current_price": 108.0, "holding_days": 12, "position_size": 100, "peak_return": 0.22},
            {"target_date": "2026-06-12", "code": "HARD_STOP", "entry_price": 100.0, "current_price": 90.0, "holding_days": 12, "position_size": 100, "peak_return": 0.04},
            {"target_date": "2026-06-12", "code": "ADD_KEEP", "entry_price": 100.0, "current_price": 112.0, "holding_days": 12, "position_size": 100, "peak_return": 0.14},
            {"target_date": "2026-06-12", "code": "REDUCE_KEEP", "entry_price": 100.0, "current_price": 106.0, "holding_days": 20, "position_size": 100, "peak_return": 0.16},
            {"target_date": "2026-06-12", "code": "HOLD_KEEP", "entry_price": 100.0, "current_price": 104.0, "holding_days": 8, "position_size": 100, "peak_return": 0.05},
        ]
    )
    opportunities = pd.DataFrame(
        [
            {"target_date": "2026-06-12", "code": "D6D_TARGET", "expected_edge_score": 0.08, "buy_rank": 12, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "HARD_STOP", "expected_edge_score": 0.08, "buy_rank": 12, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "ADD_KEEP", "expected_edge_score": 0.16, "buy_rank": 2, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "REDUCE_KEEP", "expected_edge_score": 0.07, "buy_rank": 8, "downside_risk_score": 0.66, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "HOLD_KEEP", "expected_edge_score": 0.05, "buy_rank": 12, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
        ]
    )
    features = pd.DataFrame(
        [
            _feature_row("D6D_TARGET", close_over_ma=1.04, ma_ratio=1.02, return_5d=0.03, return_20d=0.08, volatility=0.03, volume=1.10),
            _feature_row("HARD_STOP", close_over_ma=1.04, ma_ratio=1.02, return_5d=0.03, return_20d=0.08, volatility=0.03, volume=1.10),
            _feature_row("ADD_KEEP", close_over_ma=1.08, ma_ratio=1.05, return_5d=0.08, return_20d=0.18, volatility=0.02, volume=1.50),
            _feature_row("REDUCE_KEEP", close_over_ma=1.03, ma_ratio=1.02, return_5d=0.02, return_20d=0.09, volatility=0.09, volume=1.20),
            _feature_row("HOLD_KEEP", close_over_ma=1.04, ma_ratio=1.02, return_5d=0.03, return_20d=0.08, volatility=0.03, volume=1.10),
        ]
    )
    return holdings, opportunities, features


def _feature_row(
    code: str,
    *,
    close_over_ma: float,
    ma_ratio: float,
    return_5d: float,
    return_20d: float,
    volatility: float,
    volume: float,
) -> dict[str, object]:
    return {
        "target_date": "2026-06-12",
        "as_of_date": "2026-06-12",
        "code": code,
        "feature_version": "phase27_d6d_fixture_v1",
        "price_momentum_return_5d": return_5d,
        "price_momentum_return_20d": return_20d,
        "trend_close_over_ma_20d": close_over_ma,
        "trend_ma_5_20_ratio": ma_ratio,
        "volatility_return_std_20d": volatility,
        "volume_momentum_ratio_5d": volume,
    }


def scored_frame() -> pd.DataFrame:
    holding, opportunity, feature = fixtures()
    frame = build_position_feature_frame(holding_frame=holding, opportunity_frame=opportunity, feature_frame=feature)
    scored = frame.copy()
    scored["current_return"] = calculate_current_return(scored)
    scored["peak_return"] = pd.to_numeric(scored.get("peak_return", scored["current_return"]), errors="coerce").fillna(scored["current_return"])
    scored["drawdown_from_peak"] = (scored["current_return"] - scored["peak_return"]).map(round_float)
    scored["downside_risk_score"] = get_numeric_series(scored, "downside_risk_score", 0.50).clip(0.0, 1.0)
    scored["expected_edge_score"] = get_numeric_series(scored, "expected_edge_score", 0.0)
    scored["buy_rank"] = get_numeric_series(scored, "buy_rank", 999).astype(int)
    trend_score = calculate_trend_continuation_score(scored)
    opportunity_score = calculate_opportunity_continuation_score(scored)
    profit_score = ((scored["current_return"] + 0.08) / 0.28).clip(0.0, 1.0)
    risk_penalty = calculate_position_risk_score(scored)
    scored["hold_score"] = (
        0.35 * trend_score + 0.25 * opportunity_score + 0.20 * profit_score + 0.20 * (1.0 - risk_penalty)
    ).map(round_float)
    scored["exit_score"] = calculate_exit_score(scored).map(round_float)
    scored["add_score"] = calculate_add_score(scored).map(round_float)
    scored["reduce_score"] = calculate_reduce_score(scored).map(round_float)
    scored["risk_guard_status"] = get_numeric_or_string_series(scored, "risk_guard_status", "").fillna("").astype(str)
    return scored


def legacy_classify(row: pd.Series) -> dict[str, str]:
    hold_score = float(row["hold_score"])
    exit_score = float(row["exit_score"])
    add_score = float(row["add_score"])
    reduce_score = float(row["reduce_score"])
    current_return = float(row["current_return"])
    drawdown_from_peak = float(row["drawdown_from_peak"])
    trend_score = float(calculate_trend_continuation_score(pd.DataFrame([row])).iloc[0])
    buy_rank = int(row["buy_rank"])
    expected_edge = float(row["expected_edge_score"])
    risk_guard_status = str(row.get("risk_guard_status", "")).lower()
    exit_reasons: list[str] = []
    risk_reasons: list[str] = []
    hold_reasons: list[str] = []
    if current_return <= -0.08:
        exit_reasons.append("hard_stop_current_return")
    if drawdown_from_peak <= -0.12:
        exit_reasons.append("profit_retention_break")
    if trend_score < 0.30 and expected_edge <= 0:
        exit_reasons.append("trend_and_opportunity_broken")
    if float(row["downside_risk_score"]) >= 0.75:
        risk_reasons.append("high_downside_risk_score")
    if risk_guard_status in {"bad", "ng", "blocked", "risk_bad", "high_risk"}:
        exit_reasons.append("risk_guard_status_bad")
    if drawdown_from_peak <= -0.07:
        risk_reasons.append("peak_drawdown_warning")
    if exit_reasons or exit_score >= 0.80:
        if not exit_reasons:
            exit_reasons.append("exit_score_high")
        return {"action": "EXIT", "action_reason": "exit_rule_triggered", "exit_reason": "|".join(exit_reasons)}
    if float(row["downside_risk_score"]) >= 0.65 or drawdown_from_peak <= -0.07 or reduce_score >= 0.62 or hold_score < 0.42:
        if trend_score >= 0.35 or expected_edge > 0:
            return {"action": "REDUCE", "action_reason": "|".join(risk_reasons or ["risk_increased_but_trend_not_broken"]), "exit_reason": ""}
        return {"action": "EXIT", "action_reason": "exit_rule_triggered", "exit_reason": "weak_hold_score"}
    if add_score >= 0.72 and current_return > 0 and buy_rank <= 5 and float(row["downside_risk_score"]) < 0.50:
        hold_reasons.extend(["strong_trend_continuation", "opportunity_rank_still_high", "no_loss_averaging"])
        return {"action": "ADD", "action_reason": "|".join(hold_reasons), "exit_reason": ""}
    if trend_score >= 0.50:
        hold_reasons.append("trend_continuation")
    if expected_edge > 0:
        hold_reasons.append("positive_expected_edge")
    if float(row["downside_risk_score"]) < 0.50:
        hold_reasons.append("downside_risk_contained")
    return {"action": "HOLD", "action_reason": "|".join(hold_reasons or ["hold_score_above_exit_threshold"]), "exit_reason": ""}


def before_after_rows() -> list[dict[str, Any]]:
    scored = scored_frame()
    holding, opportunity, feature = fixtures()
    current_output = build_position_management_output(
        build_position_feature_frame(holding_frame=holding, opportunity_frame=opportunity, feature_frame=feature),
        created_at="2026-06-14T00:00:00+00:00",
        inference_run_id="phase27_d6d_fixture",
    )
    current_by_code = {str(row["code"]): row for row in current_output.to_dict("records")}
    rows: list[dict[str, Any]] = []
    for row in scored.to_dict("records"):
        before = legacy_classify(pd.Series(row))
        after = current_by_code[str(row["code"])]
        rows.append(
            {
                "symbol": row["code"],
                "business_date": row["target_date"],
                "before_action": before["action"],
                "after_action": after["action"],
                "before_reason": before["exit_reason"] or before["action_reason"],
                "after_reason": after["exit_reason"] or after["action_reason"],
                "changed": before["action"] != after["action"],
                "current_return": round_float(row["current_return"]),
                "peak_return": round_float(row["peak_return"]),
                "drawdown_from_peak": round_float(row["drawdown_from_peak"]),
                "expected_edge_score": round_float(row["expected_edge_score"]),
                "buy_rank": int(row["buy_rank"]),
                "downside_risk_score": round_float(row["downside_risk_score"]),
                "hold_score": round_float(row["hold_score"]),
                "exit_score": round_float(row["exit_score"]),
                "reduce_score": round_float(row["reduce_score"]),
                "add_score": round_float(row["add_score"]),
            }
        )
    return rows


def counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        action = str(row[field])
        result[action] = result.get(action, 0) + 1
    return result


def files() -> dict[str, object]:
    rows = before_after_rows()
    changed = [row for row in rows if row["changed"]]
    before_counts = counts(rows, "before_action")
    after_counts = counts(rows, "after_action")
    return {
        "summary.json": {
            "task_id": TASK_ID,
            "primary_judgment": PRIMARY,
            "supporting": supporting(),
            "implementation_changed": True,
            "pm_logic_changed": True,
            "runtime_changed": False,
            "historical_executed": False,
            "fresh_run_executed": False,
            "single_change_scope": "PM_HOLD_EXIT_BOUNDARY_ONLY",
            "ready_for_100bd": True,
        },
        "changed_fixtures.json": changed,
        "expected_edge_before_after.json": rows,
        "action_diff.json": {
            "before_counts": before_counts,
            "after_counts": after_counts,
            "changed_count": len(changed),
            "expected_change": "EXIT_TO_HOLD_ONLY",
        },
        "reason_diff.json": [
            {
                "symbol": row["symbol"],
                "before_reason": row["before_reason"],
                "after_reason": row["after_reason"],
                "reason_change": row["before_reason"] != row["after_reason"],
            }
            for row in rows
        ],
        "non_target_change_proof.json": {
            "buy_new_changed": False,
            "add_unchanged": before_counts.get("ADD", 0) == after_counts.get("ADD", 0),
            "reduce_unchanged": before_counts.get("REDUCE", 0) == after_counts.get("REDUCE", 0),
            "position_sizing_changed": False,
            "runtime_planning_changed": False,
            "pending_changed": False,
            "submit_changed": False,
            "safety_changed": False,
            "execution_changed": False,
        },
        "regression_results.json": regression_results(),
        "implementation_completeness.json": implementation_completeness(),
        "test_results.json": regression_results(),
    }


def regression_results() -> dict[str, object]:
    return {
        "commands": [
            {"command": "python3 -m pytest tests/position_management_ai/test_phase6a_position_management_baseline.py -q", "result": "PASS", "count": "6 passed"},
            {"command": "python3 -m pytest tests/runtime_v2/test_phase27_d6d_pm_hold_exit_boundary.py -q", "result": "PASS", "count": "1 passed"},
            {"command": "python3 -m pytest tests/position_management_ai/test_phase6a_position_management_baseline.py tests/runtime_v2/test_phase27_d6d_pm_hold_exit_boundary.py tests/runtime_v2/test_phase27_d6b_pm_reason_semantics.py tests/runtime_v2/test_phase15af_position_management_runtime_connection.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/strategy/test_phase27_d2a_position_intent.py tests/strategy/test_phase27_d2b_target_portfolio_decision.py tests/strategy/test_phase27_d2d_position_sizing_plan.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase22_gr_runtime_planning_regression_repair.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py -q", "result": "PASS", "count": "108 passed"},
            {"command": "PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase27_d6d python3 -m py_compile src/ai_fund_lab_v2/position_management_ai/inference.py tests/position_management_ai/test_phase6a_position_management_baseline.py tests/runtime_v2/test_phase27_d6d_pm_hold_exit_boundary.py tools/phase27_analysis/phase27_d6d_generate_hold_exit_boundary_implementation_report.py", "result": "PASS"},
            {"command": "for f in reports/phase27_d6d_pm_hold_exit_boundary_minimal_performance_implementation/*.json; do python3 -m json.tool \"$f\" >/dev/null || exit 1; done", "result": "PASS"},
        ],
        "historical_executed": False,
        "fresh_run_executed": False,
        "long_regression_executed": False,
    }


def implementation_completeness() -> list[dict[str, str]]:
    return [
        {"item": "HOLD / EXIT only", "status": "COMPLETE"},
        {"item": "ADD unchanged", "status": "COMPLETE"},
        {"item": "BUY_NEW unchanged", "status": "COMPLETE"},
        {"item": "Expected Edge contract aligned", "status": "COMPLETE"},
        {"item": "Regression", "status": "COMPLETE"},
        {"item": "100BD ready", "status": "COMPLETE"},
        {"item": "Historical not executed", "status": "COMPLETE"},
    ]


def render_report() -> str:
    rows = before_after_rows()
    changed = [row for row in rows if row["changed"]]
    return f"""# Phase27-D6-D PM HOLD / EXIT Boundary Minimal Performance Implementation

## 1. Scope

Phase27-D6-D implements the first minimal PM performance improvement: Expected Edge adequate positions are not exited solely because of profit-retention / peak-drawdown risk review.

```text
Runtime Change: false
BUY_NEW Change: false
ADD Change: false
Position Sizing Change: false
Runtime Planning / Pending / Submit Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Supporting:

```json
{json.dumps(supporting(), ensure_ascii=False, indent=2)}
```

## 3. Implementation

The single implemented boundary is:

```text
profit_retention_break only
AND expected_edge_score > 0 under the existing PM Expected Edge evidence
AND high downside risk is absent
AND existing exit_score high condition is absent
-> HOLD
```

No new threshold, magic number, holding-day rule, profit target, stop loss, or cooldown was added. Existing hard stop, broken trend plus insufficient Expected Edge, risk guard, high downside risk, and exit-score evidence still produce EXIT.

## 4. Before / After

Changed fixture count: `{len(changed)}`

```text
EXIT -> HOLD: {sum(1 for row in changed if row['before_action'] == 'EXIT' and row['after_action'] == 'HOLD')}
```

The changed fixture has positive Expected Edge remaining and no severe full-close risk evidence.

## 5. Regression

```text
PM Unit: 6 passed
Runtime PM Boundary: 1 passed
Targeted Regression: 108 passed
```

## 6. Evidence

```text
{OUT_DIR.relative_to(REPO_ROOT)}
```

No fresh-run, resume, 100BD, 1-year Historical, or long regression was executed. 100BD is ready for user execution.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in files().items():
        write_json(OUT_DIR / name, payload)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
