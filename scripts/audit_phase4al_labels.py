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

from scripts.build_phase4al_labels import (  # noqa: E402
    LABEL_COLUMNS,
    READY,
    SUMMARY_PATH,
    build_phase4al_labels,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4al_label_generation_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4al_label_generation_audit.md")


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
        summary = build_phase4al_labels(runtime_dir=runtime_dir, report_dir=report_dir)

    label_output = Path(str(summary.get("label_output_path") or ""))
    manifest_path = Path(str(summary.get("manifest_path") or ""))
    audit_path = Path(str(summary.get("audit_path") or ""))
    label_payload = _read_json_optional(label_output)
    manifest = _read_json_optional(manifest_path)
    audit = _read_json_optional(audit_path)
    rows = label_payload.get("rows") if isinstance(label_payload.get("rows"), list) else []

    checks = {
        "summary_exists": summary_path.is_file(),
        "label_output_exists": label_output.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "audit_exists": audit_path.is_file(),
        "readiness_ready_for_dataset_builder": summary.get("readiness_status") == READY,
        "label_generation_executed": summary.get("label_generation_executed") is True,
        "label_rows_positive": int(summary.get("label_row_count") or 0) > 0 and bool(rows),
        "label_columns_present": _label_columns_present(rows),
        "label_output_under_runtime_labels": "/candidate_ai/labels/" in str(label_output).replace("\\", "/"),
        "manifest_real_runtime": manifest.get("data_source_type") == "real_runtime",
        "feature_table_not_modified": summary.get("feature_table_modified") is False
        and audit.get("feature_table_modified") is False,
        "feature_table_not_joined": summary.get("feature_table_joined") is False
        and audit.get("feature_table_joined") is False,
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK"
        and audit.get("leakage_audit_status") == "OK",
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
        "boolean_label_counts_recorded": all(
            f"{column}_count" in summary
            for column in ("top_decile_20d", "downside_bad_20d", "momentum_candidate_label")
        ),
        "dataset_training_inference_backtest_trading_not_executed": all(
            summary.get(key) is False
            for key in (
                "dataset_builder_executed",
                "training_executed",
                "inference_executed",
                "backtest_executed",
                "trading_executed",
            )
        ),
        "broker_order_paper_not_executed": all(
            summary.get(key) is False
            for key in ("paper_trading_executed", "broker_api_executed", "order_executed")
        ),
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(manifest) and _no_secret_terms(audit),
    }
    result = {
        "phase": "Phase4-AL",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4al_label_generation.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _label_columns_present(rows: list[Any]) -> bool:
    if not rows:
        return False
    columns = set(rows[0].keys())
    return all(column in columns for column in LABEL_COLUMNS) and all(
        column in columns
        for column in (
            "target_date",
            "code",
            "label_version",
            "label_horizon",
            "future_start_date",
            "future_end_date",
            "source_snapshot_id",
        )
    )


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "label_generation_executed",
        "label_row_count",
        "label_column_count",
        "future_return_5d_count",
        "future_return_10d_count",
        "future_return_20d_count",
        "future_max_return_20d_count",
        "future_max_drawdown_20d_count",
        "top_decile_20d_count",
        "downside_bad_20d_count",
        "momentum_candidate_label_count",
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
        "# Phase4-AL Label Generation Audit",
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
            "- This audit checks label generation only.",
            "- It confirms labels are stored separately under `.runtime/candidate_ai/labels/`.",
            "- It confirms the Phase4-AK feature table is not modified or joined.",
            "- Phase4-AM may join features and labels only for a training dataset; inference datasets must not include labels.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = (
        "sAuthId",
        "Authorization",
        "x-api-key",
        "JQUANTS_API_KEY",
        "TACHIBANA",
        "password",
        "cookie",
        "refresh_token",
        "id_token",
    )
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
