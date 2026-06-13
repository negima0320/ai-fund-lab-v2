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

from scripts.build_phase4an_historical_feature_coverage import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    build_phase4an_historical_feature_coverage,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4an_historical_feature_coverage_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4an_historical_feature_coverage_audit.md")


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
    if not summary or not Path(str(summary.get("historical_feature_output_path") or "")).is_file():
        summary = build_phase4an_historical_feature_coverage(runtime_dir=runtime_dir, report_dir=report_dir)
    output_path = Path(str(summary.get("historical_feature_output_path") or ""))
    manifest_path = Path(str(summary.get("manifest_path") or ""))
    audit_path = Path(str(summary.get("audit_path") or ""))
    payload = _read_json_optional(output_path)
    manifest = _read_json_optional(manifest_path)
    audit = _read_json_optional(audit_path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    checks = {
        "summary_exists": summary_path.is_file(),
        "historical_feature_output_exists": output_path.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "audit_exists": audit_path.is_file(),
        "readiness_ready_for_dataset_builder_retry": summary.get("readiness_status") == READY,
        "historical_feature_generation_executed": summary.get("historical_feature_generation_executed") is True,
        "feature_rows_positive": int(summary.get("generated_historical_feature_row_count") or 0) > 0 and bool(rows),
        "feature_target_dates_cover_labels": summary.get("coverage_status") == "OK"
        and summary.get("expected_feature_target_date_min") >= summary.get("actual_feature_target_date_min")
        and summary.get("expected_feature_target_date_max") <= summary.get("actual_feature_target_date_max"),
        "overlap_target_dates_positive": int(summary.get("overlap_target_date_count") or 0) > 0,
        "schema_validation_ok": summary.get("schema_validation_status") == "OK"
        and audit.get("schema_validation_status") == "OK",
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK"
        and audit.get("leakage_audit_status") == "OK",
        "manifest_counts_match": int(manifest.get("feature_row_count") or -1)
        == int(summary.get("generated_historical_feature_row_count") or -2),
        "no_forbidden_future_label_columns": _no_forbidden_future_label_columns(rows),
        "label_dataset_training_inference_not_executed": all(
            summary.get(key) is False
            for key in ("label_generation_executed", "dataset_builder_executed", "training_executed", "inference_executed", "backtest_executed", "trading_executed")
        ),
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(manifest) and _no_secret_terms(audit),
    }
    result = {
        "phase": "Phase4-AN",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4an_historical_feature_coverage.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _no_forbidden_future_label_columns(rows: list[Any]) -> bool:
    if not rows:
        return False
    forbidden_prefixes = ("future_return_", "future_max_return_", "future_max_drawdown_", "top_decile_", "downside_bad_")
    for row in rows[:100]:
        for column in row:
            if column.startswith(forbidden_prefixes) or "label" in column:
                return False
    return True


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "feature_target_date_count",
        "label_target_date_count",
        "overlap_target_date_count",
        "expected_feature_target_date_min",
        "expected_feature_target_date_max",
        "actual_feature_target_date_min",
        "actual_feature_target_date_max",
        "generated_historical_feature_row_count",
        "generated_historical_feature_date_count",
        "eligible_count",
        "excluded_count",
        "schema_validation_status",
        "leakage_audit_status",
        "join_coverage_readiness",
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
        "# Phase4-AN Historical Feature Coverage Audit",
        "",
        "## Audit Result",
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
    lines.extend(["", "## Checks", ""])
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- This audit checks historical feature coverage only.",
            "- It confirms label generation, dataset builder, training, inference, backtest, and trading are not executed.",
            "- Phase4-AO may retry Dataset Builder using the historical feature table.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "JQUANTS_API_KEY", "TACHIBANA", "password", "cookie", "token")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
