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

from scripts.build_phase4bc_long_history_features import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    build_phase4bc_long_history_features,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4bc_long_history_feature_regeneration_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4bc_long_history_feature_regeneration_audit.md")


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
    if not summary or not Path(str(summary.get("feature_output_path") or "")).is_file():
        summary = build_phase4bc_long_history_features(runtime_dir=runtime_dir, report_dir=report_dir)
    feature_path = Path(str(summary.get("feature_output_path") or ""))
    manifest_path = Path(str(summary.get("manifest_path") or ""))
    audit_path = Path(str(summary.get("audit_path") or ""))
    manifest = _read_json_optional(manifest_path)
    audit = _read_json_optional(audit_path)
    quality = audit.get("feature_quality_gate") if isinstance(audit.get("feature_quality_gate"), dict) else {}
    train = quality.get("splits", {}).get("train", {}) if isinstance(quality.get("splits"), dict) else {}
    checks = {
        "summary_exists": summary_path.is_file(),
        "feature_output_exists": feature_path.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "audit_exists": audit_path.is_file(),
        "readiness_ready": summary.get("readiness_status") == READY,
        "feature_generation_executed": summary.get("feature_generation_executed") is True,
        "feature_rows_positive": int(summary.get("feature_row_count") or 0) > 0,
        "schema_validation_ok": summary.get("schema_validation_status") == "OK"
        and manifest.get("schema_validation_status") == "OK",
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK"
        and manifest.get("leakage_audit_status") == "OK",
        "no_forbidden_future_label_columns": summary.get("forbidden_feature_detected") is False
        and summary.get("future_column_detected") is False
        and summary.get("label_column_detected") is False,
        "train_all_null_resolved": _as_int(summary.get("all_null_feature_count_train"), default=-1) == 0,
        "train_variance_available": summary.get("feature_variance_available_train") is True,
        "at_problem_resolved": summary.get("at_null_constant_problem_resolved") is True,
        "manifest_counts_match": int(manifest.get("row_count") or -1) == int(summary.get("feature_row_count") or -2),
        "no_downstream_execution": all(
            summary.get(key) is False
            for key in (
                "label_generation_executed",
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
        "train_quality_payload_present": bool(train),
    }
    result = {
        "phase": "Phase4-BC",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4bc_long_history_feature_regeneration.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "feature_row_count",
        "eligible_count",
        "excluded_count",
        "target_date_min",
        "target_date_max",
        "target_date_count",
        "feature_column_count",
        "schema_validation_status",
        "leakage_audit_status",
        "all_null_feature_count_train",
        "constant_feature_count_train",
        "near_constant_feature_count_train",
        "high_null_feature_count_train",
        "all_null_feature_count_validation",
        "constant_feature_count_validation",
        "high_null_feature_count_validation",
        "all_null_feature_count_test",
        "constant_feature_count_test",
        "high_null_feature_count_test",
        "at_null_constant_problem_resolved",
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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-BC Long History Feature Regeneration Audit",
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
            "- Feature regeneration and feature quality audit only.",
            "- No label generation, dataset rebuild, training, inference, backtest, trading, promotion, reader switch, broker API, or order placement.",
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
