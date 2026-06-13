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

from scripts.rebuild_phase4bb_long_history_normalized import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    rebuild_phase4bb_long_history_normalized,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4bb_long_history_normalized_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4bb_long_history_normalized_audit.md")


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
    if not summary or not Path(str(summary.get("isolated_output_path") or "")).is_file():
        summary = rebuild_phase4bb_long_history_normalized(runtime_dir=runtime_dir, report_dir=report_dir)

    isolated_output = Path(str(summary.get("isolated_output_path") or ""))
    manifest_path = Path(str(summary.get("manifest_path") or ""))
    manifest = _read_json_optional(manifest_path)
    if summary and not _manifest_matches_summary(manifest, summary):
        summary = rebuild_phase4bb_long_history_normalized(runtime_dir=runtime_dir, report_dir=report_dir)
        isolated_output = Path(str(summary.get("isolated_output_path") or ""))
        manifest_path = Path(str(summary.get("manifest_path") or ""))
        manifest = _read_json_optional(manifest_path)
    checks = {
        "summary_exists": summary_path.is_file(),
        "isolated_output_exists": isolated_output.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "readiness_ready": summary.get("readiness_status") == READY,
        "normalized_rebuild_executed": summary.get("normalized_rebuild_executed") is True,
        "raw_row_count_positive": int(summary.get("raw_row_count") or 0) > 0,
        "normalized_row_count_positive": int(summary.get("normalized_row_count") or 0) > 0,
        "raw_to_normalized_accounted_for": int(summary.get("normalized_row_count") or 0)
        + int(summary.get("price_missing_excluded_count") or 0)
        == int(summary.get("raw_row_count") or -1),
        "normalization_error_count_zero": int(summary.get("normalization_error_count") or 0) == 0,
        "schema_mapping_ok": summary.get("schema_mapping_status") == "OK",
        "duplicate_date_code_zero": _as_int(summary.get("duplicate_date_code_count"), default=-1) == 0,
        "business_day_count_positive": _as_int(summary.get("business_day_count"), default=0) > 0,
        "manifest_row_count_matches_summary": int(manifest.get("normalized_row_count") or -1)
        == int(summary.get("normalized_row_count") or -2),
        "manifest_data_source_real_runtime": manifest.get("data_source_type") == "real_runtime",
        "manifest_phase_ok": manifest.get("phase") == "Phase4-BB",
        "formal_training_coverage_sufficient": summary.get("formal_training_coverage_sufficient_after_normalization") is True
        and manifest.get("formal_training_coverage_sufficient_after_normalization") is True,
        "mock_path_unchanged": summary.get("mock_path_unchanged") is True and manifest.get("mock_path_unchanged") is True,
        "promotion_not_performed": summary.get("promotion_performed") is False
        and manifest.get("promotion_performed") is False,
        "reader_switch_not_performed": summary.get("reader_switch_performed") is False
        and manifest.get("reader_switch_performed") is False,
        "no_downstream_execution": summary.get("feature_generation_executed") is False
        and summary.get("label_generation_executed") is False
        and summary.get("dataset_rebuild_executed") is False
        and summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(manifest),
    }
    result = {
        "phase": "Phase4-BB",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4bb_long_history_normalized.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "raw_row_count",
        "normalized_row_count",
        "price_missing_excluded_count",
        "normalization_error_count",
        "date_min",
        "date_max",
        "business_day_count",
        "code_count",
        "duplicate_date_code_count",
        "schema_mapping_status",
        "mock_path_unchanged",
        "promotion_status",
        "promotion_performed",
        "reader_switch_performed",
        "formal_training_coverage_sufficient_after_normalization",
        "isolated_output_path",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _as_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _manifest_matches_summary(manifest: dict[str, Any], summary: dict[str, Any]) -> bool:
    return (
        manifest.get("phase") == "Phase4-BB"
        and manifest.get("data_source_type") == "real_runtime"
        and _as_int(manifest.get("normalized_row_count"), default=-1)
        == _as_int(summary.get("normalized_row_count"), default=-2)
        and manifest.get("mock_path_unchanged") is True
        and manifest.get("promotion_performed") is False
        and manifest.get("reader_switch_performed") is False
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-BB Long History Normalized Audit",
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
            "- Normalized rebuild only.",
            "- No promotion, reader switch, feature generation, label generation, dataset rebuild, training, inference, backtest, trading, Paper Trading, broker API, or order placement.",
            "- Mock normalized path remains unchanged.",
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
