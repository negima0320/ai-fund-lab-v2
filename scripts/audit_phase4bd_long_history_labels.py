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

from scripts.build_phase4bd_long_history_labels import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    build_phase4bd_long_history_labels,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4bd_long_history_label_regeneration_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4bd_long_history_label_regeneration_audit.md")


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
    if not summary or not Path(str(summary.get("label_output_path") or "")).is_file():
        summary = build_phase4bd_long_history_labels(runtime_dir=runtime_dir, report_dir=report_dir)
    label_path = Path(str(summary.get("label_output_path") or ""))
    manifest_path = Path(str(summary.get("manifest_path") or ""))
    audit_path = Path(str(summary.get("audit_path") or ""))
    manifest = _read_json_optional(manifest_path)
    audit = _read_json_optional(audit_path)
    checks = {
        "summary_exists": summary_path.is_file(),
        "label_output_exists": label_path.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "audit_exists": audit_path.is_file(),
        "readiness_ready": summary.get("readiness_status") == READY,
        "label_generation_executed": summary.get("label_generation_executed") is True,
        "label_rows_positive": int(summary.get("label_row_count") or 0) > 0,
        "label_output_under_runtime_labels": "/candidate_ai/labels/" in str(label_path).replace("\\", "/"),
        "manifest_counts_match": int(manifest.get("label_row_count") or -1) == int(summary.get("label_row_count") or -2),
        "all_numeric_label_counts_positive": all(
            int(summary.get(f"{column}_count") or 0) > 0
            for column in (
                "future_return_5d",
                "future_return_10d",
                "future_return_20d",
                "future_max_return_20d",
                "future_max_drawdown_20d",
            )
        ),
        "boolean_label_counts_positive": int(summary.get("top_decile_20d_count") or 0) > 0
        and int(summary.get("momentum_candidate_label_count") or 0) > 0,
        "split_coverage_positive": all(
            int(summary.get(key) or 0) > 0
            for key in (
                "train_label_row_count_estimate",
                "validation_label_row_count_estimate",
                "test_label_row_count_estimate",
            )
        ),
        "split_positive_rate_positive": all(
            float(summary.get(key) or 0) > 0
            for key in ("train_positive_rate", "validation_positive_rate", "test_positive_rate")
        ),
        "feature_table_not_modified": summary.get("feature_table_modified") is False
        and audit.get("feature_table_modified") is False,
        "feature_table_not_joined": summary.get("feature_table_joined") is False
        and audit.get("feature_table_joined") is False,
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK"
        and audit.get("leakage_audit_status") == "OK",
        "no_downstream_execution": all(
            summary.get(key) is False
            for key in (
                "dataset_rebuild_executed",
                "training_executed",
                "inference_executed",
                "backtest_executed",
                "trading_executed",
                "promotion_performed",
                "reader_switch_performed",
            )
        ),
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(manifest) and _no_secret_terms(audit),
    }
    result = {
        "phase": "Phase4-BD",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4bd_long_history_label_regeneration.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "label_row_count",
        "label_column_count",
        "label_target_date_min",
        "label_target_date_max",
        "label_target_date_count",
        "code_count",
        "future_return_5d_count",
        "future_return_10d_count",
        "future_return_20d_count",
        "future_max_return_20d_count",
        "future_max_drawdown_20d_count",
        "top_decile_20d_count",
        "downside_bad_20d_count",
        "momentum_candidate_label_count",
        "momentum_candidate_label_positive_rate",
        "train_label_row_count_estimate",
        "validation_label_row_count_estimate",
        "test_label_row_count_estimate",
        "train_positive_rate",
        "validation_positive_rate",
        "test_positive_rate",
        "label_unavailable_tail_target_date_count",
        "label_unavailable_tail_row_count",
        "feature_table_modified",
        "feature_table_joined",
        "leakage_audit_status",
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
        "# Phase4-BD Long History Label Regeneration Audit",
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
        lines.append(f"- {name}: `{value}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- Label regeneration and label audit only.",
            "- Label columns are stored separately under `.runtime/candidate_ai/labels/`.",
            "- No dataset rebuild, training, inference, backtest, trading, promotion, reader switch, broker API, or order placement.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True).lower()
    terms = ("sauthid", "authorization", "x-api-key", "jquants_api_key", "tachibana", "password", "cookie", "refresh_token", "id_token")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
