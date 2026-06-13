#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ar_candidate_output_smoke_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4ar_candidate_output_smoke_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ar_candidate_output_smoke_audit.md")
PHASE4AQ_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4aq_candidate_inference_smoke_summary.json")

READY_WITH_QUALITY_BLOCK = "TECHNICAL_PHASE4_SMOKE_COMPLETE_WITH_MODEL_QUALITY_BLOCKED"
READY_FORMAL_AUDIT = "READY_FOR_FORMAL_CANDIDATE_QUALITY_AUDIT"
BLOCKED_MISSING = "BLOCKED_BY_MISSING_CANDIDATE_ARTIFACT"
BLOCKED_SCHEMA = "BLOCKED_BY_OUTPUT_SCHEMA"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_RESPONSIBILITY = "BLOCKED_BY_RESPONSIBILITY_BOUNDARY"
BLOCKED_ALL_SAME = "BLOCKED_BY_ALL_SAME_SCORE"
BLOCKED_INEFFECTIVE = "BLOCKED_BY_INEFFECTIVE_RANKING"

FORBIDDEN_COLUMN_TERMS = (
    "future_return",
    "future_max_return",
    "future_max_drawdown",
    "top_decile",
    "downside_bad",
    "momentum_candidate_label",
    "label__",
)
TRADING_TERMS = ("backtest", "trade_result", "trading", "paper_trade")
BUY_SELL_HOLD_TERMS = ("buy", "sell", "hold", "bought", "sold")
ALLOCATION_TERMS = ("allocation", "capital_allocation", "portfolio_weight")
ORDER_TERMS = ("order", "execution")
PNL_TERMS = ("pnl", "profit", "loss")


def main() -> int:
    summary = audit_phase4ar_candidate_output_smoke()
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def audit_phase4ar_candidate_output_smoke(
    *,
    phase4aq_summary_path: Path = PHASE4AQ_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    aq_summary = _read_json_optional(phase4aq_summary_path)
    candidate_path = Path(str(aq_summary.get("top50_json_path") or ""))
    inference_path = Path(str(aq_summary.get("inference_output_path") or ""))
    candidate_payload = _read_json_optional(candidate_path)
    inference_payload = _read_json_optional(inference_path)
    candidates = _rows(candidate_payload)
    scored_rows = _rows(inference_payload)

    if not candidate_path.is_file() or not inference_path.is_file():
        summary = _base_summary(
            readiness_status=BLOCKED_MISSING,
            aq_summary=aq_summary,
            candidate_path=candidate_path,
            inference_path=inference_path,
        )
        _write_reports(summary, summary_path, json_report_path, markdown_report_path)
        return summary

    schema = audit_candidate_schema(candidates, expected_count=50)
    score_stats = calculate_score_stats(candidates)
    scanned_payload = {"candidates": candidates, "scored_sample": scored_rows[:100]}
    leakage = audit_forbidden_terms(scanned_payload)
    responsibility_status = "OK" if not any(
        leakage[key]
        for key in (
            "trading_column_detected",
            "buy_sell_hold_detected",
            "allocation_detected",
            "order_detected",
            "pnl_detected",
        )
    ) else "ERROR"
    all_same_score = bool(score_stats["unique_candidate_score_count"] == 1 and candidates)
    ranking_effective = bool(score_stats["unique_candidate_score_count"] > 1 and schema["candidate_rank_valid"])
    readiness_status = resolve_readiness(
        schema_ok=schema["status"] == "OK",
        leakage_ok=leakage["status"] == "OK",
        responsibility_status=responsibility_status,
        all_same_score=all_same_score,
        ranking_effective=ranking_effective,
    )
    status = "OK" if readiness_status in {READY_WITH_QUALITY_BLOCK, READY_FORMAL_AUDIT} else "BLOCKED"
    candidate_reason_coverage = _coverage(candidates, "candidate_reason")
    excluded_reason_available = all("excluded_reason" in row for row in candidates)
    feature_snapshot_id_present = all(bool(row.get("feature_snapshot_id")) for row in candidates)
    model_version_present = all(bool(row.get("model_version")) for row in candidates)
    audit_flags_present = all(bool(row.get("audit_flags")) for row in candidates)

    summary = {
        "phase": "Phase4-AR",
        "status": status,
        "readiness_status": readiness_status,
        "output_audit_executed": True,
        "target_date": aq_summary.get("target_date") or candidate_payload.get("target_date"),
        "candidate_artifact_detected": candidate_path.is_file(),
        "inference_scores_artifact_detected": inference_path.is_file(),
        "candidate_count": len(candidates),
        "scored_count": int(aq_summary.get("scored_count") or len(scored_rows)),
        "eligible_input_count": int(aq_summary.get("eligible_input_count") or 0),
        "candidate_rank_valid": schema["candidate_rank_valid"],
        "candidate_rank_unique": schema["candidate_rank_unique"],
        "candidate_score_min": score_stats["candidate_score_min"],
        "candidate_score_max": score_stats["candidate_score_max"],
        "candidate_score_mean": score_stats["candidate_score_mean"],
        "candidate_score_std": score_stats["candidate_score_std"],
        "unique_candidate_score_count": score_stats["unique_candidate_score_count"],
        "all_same_score": all_same_score,
        "ranking_effective": ranking_effective,
        "candidate_reason_coverage": candidate_reason_coverage,
        "excluded_reason_available": excluded_reason_available,
        "feature_snapshot_id_present": feature_snapshot_id_present,
        "model_version_present": model_version_present,
        "audit_flags_present": audit_flags_present,
        "forbidden_column_detected": leakage["forbidden_column_detected"],
        "future_column_detected": leakage["future_column_detected"],
        "label_column_detected": leakage["label_column_detected"],
        "trading_column_detected": leakage["trading_column_detected"],
        "buy_sell_hold_detected": leakage["buy_sell_hold_detected"],
        "allocation_detected": leakage["allocation_detected"],
        "order_detected": leakage["order_detected"],
        "pnl_detected": leakage["pnl_detected"],
        "production_model_promoted": bool(aq_summary.get("production_model_promoted")),
        "backtest_executed": bool(aq_summary.get("backtest_executed")),
        "trading_executed": bool(aq_summary.get("trading_executed")),
        "paper_trading_executed": bool(aq_summary.get("paper_trading_executed")),
        "broker_api_called": bool(aq_summary.get("broker_api_called")),
        "order_executed": bool(aq_summary.get("order_executed")),
        "responsibility_boundary_status": responsibility_status,
        "schema_status": schema["status"],
        "leakage_audit_status": leakage["status"],
        "candidate_artifact_path": str(candidate_path),
        "inference_scores_artifact_path": str(inference_path),
        "recommended_next_action": recommended_next_action(readiness_status),
        "summary_path": str(summary_path),
    }
    _write_reports(summary, summary_path, json_report_path, markdown_report_path)
    return summary


def audit_candidate_schema(rows: list[dict[str, Any]], *, expected_count: int = 50) -> dict[str, Any]:
    required = {
        "target_date",
        "code",
        "candidate_score",
        "candidate_rank",
        "candidate_reason",
        "excluded_reason",
        "feature_snapshot_id",
        "model_version",
        "audit_flags",
    }
    ranks = [row.get("candidate_rank") for row in rows]
    scores = [row.get("candidate_score") for row in rows]
    rank_valid = ranks == list(range(1, len(rows) + 1))
    rank_unique = len(ranks) == len(set(ranks))
    score_numeric = all(_is_number(score) for score in scores)
    score_not_null = all(score is not None for score in scores)
    schema_ok = (
        len(rows) == expected_count
        and all(required.issubset(row.keys()) for row in rows)
        and rank_valid
        and rank_unique
        and score_numeric
        and score_not_null
    )
    return {
        "status": "OK" if schema_ok else "ERROR",
        "candidate_rank_valid": rank_valid,
        "candidate_rank_unique": rank_unique,
        "candidate_score_numeric": score_numeric,
        "candidate_score_not_null": score_not_null,
    }


def calculate_score_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(row["candidate_score"]) for row in rows if _is_number(row.get("candidate_score"))]
    if not scores:
        return {
            "candidate_score_min": None,
            "candidate_score_max": None,
            "candidate_score_mean": None,
            "candidate_score_std": None,
            "unique_candidate_score_count": 0,
        }
    return {
        "candidate_score_min": round(min(scores), 6),
        "candidate_score_max": round(max(scores), 6),
        "candidate_score_mean": round(statistics.fmean(scores), 6),
        "candidate_score_std": round(statistics.pstdev(scores), 6),
        "unique_candidate_score_count": len({round(score, 12) for score in scores}),
    }


def audit_forbidden_terms(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=True).lower()
    # Audit flags intentionally include "not_buy_decision"; those are allowed guard phrases.
    normalized = text.replace("not_buy_decision", "").replace("not_production_model", "")
    future_detected = any(term in normalized for term in FORBIDDEN_COLUMN_TERMS if term != "label__")
    label_detected = "label__" in normalized
    trading_detected = any(term in normalized for term in TRADING_TERMS)
    buy_sell_hold_detected = any(term in normalized for term in BUY_SELL_HOLD_TERMS)
    allocation_detected = any(term in normalized for term in ALLOCATION_TERMS)
    order_detected = any(term in normalized for term in ORDER_TERMS)
    pnl_detected = any(term in normalized for term in PNL_TERMS)
    forbidden = future_detected or label_detected
    status = "OK" if not (forbidden or trading_detected or buy_sell_hold_detected or allocation_detected or order_detected or pnl_detected) else "ERROR"
    return {
        "status": status,
        "forbidden_column_detected": forbidden,
        "future_column_detected": future_detected,
        "label_column_detected": label_detected,
        "trading_column_detected": trading_detected,
        "buy_sell_hold_detected": buy_sell_hold_detected,
        "allocation_detected": allocation_detected,
        "order_detected": order_detected,
        "pnl_detected": pnl_detected,
    }


def resolve_readiness(
    *,
    schema_ok: bool,
    leakage_ok: bool,
    responsibility_status: str,
    all_same_score: bool,
    ranking_effective: bool,
) -> str:
    if not schema_ok:
        return BLOCKED_SCHEMA
    if not leakage_ok:
        return BLOCKED_LEAKAGE
    if responsibility_status != "OK":
        return BLOCKED_RESPONSIBILITY
    if all_same_score:
        return READY_WITH_QUALITY_BLOCK
    if not ranking_effective:
        return BLOCKED_INEFFECTIVE
    return READY_FORMAL_AUDIT


def recommended_next_action(readiness_status: str) -> str:
    if readiness_status == READY_WITH_QUALITY_BLOCK:
        return "Phase4-AS Candidate Model Quality Root Cause Analysis before formal quality audit."
    if readiness_status == READY_FORMAL_AUDIT:
        return "Proceed to formal Candidate Quality Audit when sufficient historical data is available."
    return "Fix the blocking Candidate output audit issue, then rerun Phase4-AR."


def _base_summary(
    *,
    readiness_status: str,
    aq_summary: dict[str, Any],
    candidate_path: Path,
    inference_path: Path,
) -> dict[str, Any]:
    return {
        "phase": "Phase4-AR",
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "output_audit_executed": False,
        "target_date": aq_summary.get("target_date"),
        "candidate_artifact_detected": candidate_path.is_file(),
        "inference_scores_artifact_detected": inference_path.is_file(),
        "candidate_count": 0,
        "scored_count": int(aq_summary.get("scored_count") or 0),
        "eligible_input_count": int(aq_summary.get("eligible_input_count") or 0),
        "candidate_rank_valid": False,
        "candidate_rank_unique": False,
        "candidate_score_min": None,
        "candidate_score_max": None,
        "candidate_score_mean": None,
        "candidate_score_std": None,
        "unique_candidate_score_count": 0,
        "all_same_score": False,
        "ranking_effective": False,
        "candidate_reason_coverage": 0.0,
        "excluded_reason_available": False,
        "feature_snapshot_id_present": False,
        "model_version_present": False,
        "audit_flags_present": False,
        "forbidden_column_detected": False,
        "future_column_detected": False,
        "label_column_detected": False,
        "trading_column_detected": False,
        "buy_sell_hold_detected": False,
        "allocation_detected": False,
        "order_detected": False,
        "pnl_detected": False,
        "production_model_promoted": bool(aq_summary.get("production_model_promoted")),
        "backtest_executed": bool(aq_summary.get("backtest_executed")),
        "trading_executed": bool(aq_summary.get("trading_executed")),
        "paper_trading_executed": bool(aq_summary.get("paper_trading_executed")),
        "broker_api_called": bool(aq_summary.get("broker_api_called")),
        "order_executed": bool(aq_summary.get("order_executed")),
        "responsibility_boundary_status": "UNKNOWN",
        "recommended_next_action": recommended_next_action(readiness_status),
        "summary_path": str(SUMMARY_PATH),
    }


def _write_reports(summary: dict[str, Any], summary_path: Path, json_report_path: Path, markdown_report_path: Path) -> None:
    _write_json(summary_path, summary)
    result = {
        "phase": "Phase4-AR",
        "status": "complete" if summary.get("readiness_status") in {READY_WITH_QUALITY_BLOCK, READY_FORMAL_AUDIT} else "incomplete",
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ar_candidate_output_smoke.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "candidate_count",
        "scored_count",
        "candidate_score_min",
        "candidate_score_max",
        "candidate_score_mean",
        "candidate_score_std",
        "unique_candidate_score_count",
        "all_same_score",
        "ranking_effective",
        "responsibility_boundary_status",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AR Candidate Output Audit Smoke",
        "",
        f"- status: {result['status']}",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `TECHNICAL_PHASE4_SMOKE_COMPLETE_WITH_MODEL_QUALITY_BLOCKED` means the output pipeline is technically sound but model quality is blocked.",
            "- All-same candidate scores indicate the current smoke model does not provide useful ranking information.",
            "- This audit does not improve the model, change labels, run backtests, or perform trading.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _coverage(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if row.get(key) not in (None, "")) / len(rows), 6)


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    return [dict(row) for row in rows]


def _is_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
