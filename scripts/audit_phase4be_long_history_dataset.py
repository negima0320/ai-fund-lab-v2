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

from scripts.build_phase4be_long_history_dataset import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    build_phase4be_long_history_dataset,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4be_long_history_dataset_rebuild_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4be_long_history_dataset_rebuild_audit.md")


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
    if not summary or not Path(str(summary.get("dataset_output_path") or "")).is_file():
        summary = build_phase4be_long_history_dataset(runtime_dir=runtime_dir, report_dir=report_dir)
    dataset_path = Path(str(summary.get("dataset_output_path") or ""))
    manifest_path = Path(str(summary.get("manifest_path") or ""))
    audit_path = Path(str(summary.get("audit_path") or ""))
    manifest = _read_json_optional(manifest_path)
    audit = _read_json_optional(audit_path)
    checks = {
        "summary_exists": summary_path.is_file(),
        "dataset_output_exists": dataset_path.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "audit_exists": audit_path.is_file(),
        "readiness_ready": summary.get("readiness_status") == READY,
        "dataset_rebuild_executed": summary.get("dataset_rebuild_executed") is True,
        "joined_rows_positive": int(summary.get("joined_row_count") or 0) > 0,
        "join_success_rate_positive": float(summary.get("join_success_rate") or 0) > 0,
        "split_rows_positive": all(
            int(summary.get(key) or 0) > 0
            for key in ("train_row_count", "validation_row_count", "test_row_count")
        ),
        "split_positives_positive": all(
            int(summary.get(key) or 0) > 0
            for key in ("train_positive_count", "validation_positive_count", "test_positive_count")
        ),
        "feature_label_counts_positive": int(summary.get("feature_column_count") or 0) > 0
        and int(summary.get("label_column_count") or 0) > 0,
        "no_future_or_label_in_features": summary.get("future_column_detected_in_features") is False
        and summary.get("label_column_detected_in_features") is False,
        "no_feature_in_labels": summary.get("feature_column_detected_in_labels") is False,
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK"
        and audit.get("leakage", {}).get("status") == "OK",
        "train_feature_quality_ok": _as_int(summary.get("train_all_null_feature_count"), default=-1) == 0
        and summary.get("train_feature_variance_available") is True,
        "validation_test_variance_ok": summary.get("validation_feature_variance_available") is True
        and summary.get("test_feature_variance_available") is True,
        "manifest_counts_match": int(manifest.get("joined_row_count") or -1) == int(summary.get("joined_row_count") or -2),
        "no_downstream_execution": all(
            summary.get(key) is False
            for key in (
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
        "phase": "Phase4-BE",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4be_long_history_dataset_rebuild.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "joined_row_count",
        "join_success_rate",
        "train_row_count",
        "validation_row_count",
        "test_row_count",
        "train_positive_rate",
        "validation_positive_rate",
        "test_positive_rate",
        "feature_column_count",
        "label_column_count",
        "leakage_audit_status",
        "train_all_null_feature_count",
        "train_constant_feature_count",
        "train_high_null_feature_count",
        "train_feature_variance_available",
        "validation_feature_variance_available",
        "test_feature_variance_available",
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
        "# Phase4-BE Long History Dataset Rebuild Audit",
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
            "- Dataset rebuild and dataset audit only.",
            "- Labels are joined only into the training dataset with `label__` prefixes.",
            "- Inference datasets must not include labels.",
            "- No training, inference, backtest, trading, promotion, reader switch, broker API, or order placement.",
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
