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

from scripts.build_phase4ao_dataset_retry import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    build_phase4ao_dataset_retry,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4ao_dataset_retry_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ao_dataset_retry_audit.md")


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
        summary = build_phase4ao_dataset_retry(runtime_dir=runtime_dir, report_dir=report_dir)
    dataset_path = Path(str(summary.get("dataset_output_path") or ""))
    manifest_path = Path(str(summary.get("manifest_path") or ""))
    audit_path = Path(str(summary.get("audit_path") or ""))
    dataset = _read_json_optional(dataset_path)
    manifest = _read_json_optional(manifest_path)
    audit = _read_json_optional(audit_path)
    rows = dataset.get("rows") if isinstance(dataset.get("rows"), list) else []

    checks = {
        "summary_exists": summary_path.is_file(),
        "dataset_output_exists": dataset_path.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "audit_exists": audit_path.is_file(),
        "dataset_builder_executed": summary.get("dataset_builder_executed") is True,
        "readiness_ready_for_first_lightgbm_training": summary.get("readiness_status") == READY,
        "joined_rows_positive": int(summary.get("joined_row_count") or 0) > 0,
        "join_success_rate_positive": float(summary.get("join_success_rate") or 0.0) > 0.0,
        "split_counts_recorded": all(
            key in summary for key in ("train_row_count", "validation_row_count", "test_row_count")
        ),
        "test_split_has_rows_for_current_runtime": int(summary.get("test_row_count") or 0) > 0,
        "feature_label_separation_ok": summary.get("feature_label_columns_separated") is True
        and audit.get("feature_label_columns_separated") is True
        and _prefixed_columns_when_rows_exist(rows),
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK"
        and audit.get("leakage_audit_status") == "OK",
        "no_future_columns_in_features": summary.get("future_column_detected_in_features") is False,
        "no_label_columns_in_features": summary.get("label_column_detected_in_features") is False,
        "manifest_counts_match_summary": manifest.get("joined_row_count") == summary.get("joined_row_count")
        and manifest.get("feature_row_count") == summary.get("feature_row_count")
        and manifest.get("label_row_count") == summary.get("label_row_count"),
        "training_inference_backtest_trading_not_executed": all(
            summary.get(key) is False
            for key in ("training_executed", "inference_executed", "backtest_executed", "trading_executed")
        ),
        "secret_terms_not_emitted": _no_secret_terms(summary)
        and _no_secret_terms(manifest)
        and _no_secret_terms(audit)
        and _no_secret_terms({"sample_rows": rows[:10]}),
    }
    result = {
        "phase": "Phase4-AO",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ao_dataset_retry.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _prefixed_columns_when_rows_exist(rows: list[Any]) -> bool:
    if not rows:
        return False
    columns = set(rows[0].keys())
    return any(column.startswith("feature__") for column in columns) and any(column.startswith("label__") for column in columns)


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "feature_row_count",
        "label_row_count",
        "joined_row_count",
        "join_success_rate",
        "train_row_count",
        "validation_row_count",
        "test_row_count",
        "feature_column_count",
        "label_column_count",
        "leakage_audit_status",
        "future_column_detected_in_features",
        "label_column_detected_in_features",
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
        "# Phase4-AO Dataset Builder Retry Audit",
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
            "- This audit checks dataset builder retry only.",
            "- It confirms Phase4-AN historical feature rows join with Phase4-AL labels by target_date + code.",
            "- It confirms feature columns and label columns remain prefixed and separated.",
            "- It confirms training, inference, backtest, and trading are not executed.",
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
