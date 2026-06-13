#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.run_phase4bg_formal_candidate_inference import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    TOP50_CSV_PATH,
    TOP50_JSON_PATH,
    run_phase4bg_formal_candidate_inference,
    validate_candidate_output,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4bg_formal_candidate_inference_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4bg_formal_candidate_inference_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.get("status") == "complete" else 1


def run_audit(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = _read_json_optional(summary_path)
    top50_json_path = Path(report_dir) / TOP50_JSON_PATH.name
    top50_csv_path = Path(report_dir) / TOP50_CSV_PATH.name
    if not summary or not top50_json_path.is_file():
        summary = run_phase4bg_formal_candidate_inference(runtime_dir=runtime_dir, report_dir=report_dir)
    top50_json_path = Path(str(summary.get("top50_json_path") or top50_json_path))
    top50_csv_path = Path(str(summary.get("top50_csv_path") or top50_csv_path))
    candidate_path = Path(str(summary.get("candidate_output_path") or ""))
    inference_path = Path(str(summary.get("inference_output_path") or ""))
    top50 = _read_json_optional(top50_json_path)
    candidate_payload = _read_json_optional(candidate_path)
    top_rows = top50.get("rows") if isinstance(top50.get("rows"), list) else []
    candidate_rows = candidate_payload.get("rows") if isinstance(candidate_payload.get("rows"), list) else []

    checks = {
        "summary_exists": summary_path.is_file(),
        "inference_executed": summary.get("inference_executed") is True,
        "formal_inference": summary.get("formal_inference") is True,
        "readiness_ready_for_quality_audit": summary.get("readiness_status") == READY,
        "model_artifact_detected": summary.get("model_artifact_detected") is True,
        "model_manifest_detected": summary.get("model_manifest_detected") is True,
        "model_version_present": bool(summary.get("model_version")),
        "input_rows_positive": int(summary.get("input_feature_row_count") or 0) > 0,
        "eligible_rows_positive": int(summary.get("eligible_input_count") or 0) > 0,
        "scored_count_matches_eligible": summary.get("scored_count") == summary.get("eligible_input_count"),
        "candidate_count_top_n": summary.get("candidate_count") == min(int(summary.get("top_n") or 0), int(summary.get("scored_count") or 0)),
        "score_stats_recorded": all(
            summary.get(key) is not None
            for key in ("candidate_score_min", "candidate_score_max", "candidate_score_mean", "candidate_score_std")
        ),
        "score_variation_exists": summary.get("all_same_score") is False
        and int(summary.get("unique_candidate_score_count") or 0) > 1,
        "ranking_effective": summary.get("ranking_effective") is True,
        "top50_json_exists": top50_json_path.is_file(),
        "top50_csv_exists": top50_csv_path.is_file(),
        "runtime_candidate_output_exists": candidate_path.is_file(),
        "runtime_inference_output_exists": inference_path.is_file(),
        "candidate_schema_ok": validate_candidate_output(top_rows) and validate_candidate_output(candidate_rows),
        "candidate_rank_is_sequential": _rank_is_sequential(top_rows),
        "candidate_rank_unique": len({row.get("candidate_rank") for row in top_rows}) == len(top_rows),
        "candidate_score_sorted_desc": _score_sorted_desc(top_rows),
        "candidate_reason_present": all(bool(row.get("candidate_reason")) for row in top_rows),
        "feature_snapshot_present": all(bool(row.get("feature_snapshot_id")) for row in top_rows),
        "audit_flags_present": all(bool(row.get("audit_flags")) for row in top_rows),
        "no_future_column_used_as_feature": summary.get("future_column_used_as_feature") is False,
        "no_label_column_used_as_feature": summary.get("label_column_used_as_feature") is False,
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK",
        "responsibility_boundary_ok": summary.get("responsibility_boundary_status") == "OK",
        "no_production_promotion": summary.get("production_model_promoted") is False,
        "backtest_trading_broker_order_not_executed": all(
            summary.get(key) is False
            for key in (
                "backtest_executed",
                "trading_executed",
                "paper_trading_executed",
                "broker_api_called",
                "order_executed",
            )
        ),
        "secret_terms_not_emitted": _no_secret_terms(summary)
        and _no_secret_terms(top50)
        and _no_secret_terms({"candidate_rows": candidate_rows[:10]}),
    }
    result = {
        "phase": "Phase4-BG",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4bg_formal_candidate_inference.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _rank_is_sequential(rows: list[Any]) -> bool:
    return [row.get("candidate_rank") for row in rows] == list(range(1, len(rows) + 1))


def _score_sorted_desc(rows: list[Any]) -> bool:
    scores = [float(row.get("candidate_score")) for row in rows]
    return scores == sorted(scores, reverse=True)


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "model_type",
        "model_version",
        "target_date",
        "input_feature_row_count",
        "eligible_input_count",
        "excluded_input_count",
        "scored_count",
        "candidate_count",
        "top_n",
        "candidate_score_min",
        "candidate_score_max",
        "candidate_score_mean",
        "candidate_score_std",
        "unique_candidate_score_count",
        "all_same_score",
        "ranking_effective",
        "feature_column_count",
        "candidate_reason_coverage",
        "leakage_audit_status",
        "responsibility_boundary_status",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-BG Formal Candidate Inference Audit",
        "",
        "## Audit Result",
        "",
        f"- status: `{result['status']}`",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks", ""])
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- Formal Candidate inference only.",
            "- Candidate rank is an extraction rank, not a purchase rank.",
            "- No production promotion, backtest, trading, Paper Trading, broker API, or order execution is performed.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True, default=str)
    terms = ("sAuthId", "Authorization", "x-api-key", "JQUANTS_API_KEY", "TACHIBANA", "password", "cookie", "refresh_token", "id_token")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
