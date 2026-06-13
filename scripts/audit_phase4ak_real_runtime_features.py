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

from scripts.build_phase4ak_real_runtime_features import (  # noqa: E402
    READY,
    REQUIRED_AK_FEATURE_COLUMNS,
    SUMMARY_PATH,
    build_phase4ak_real_runtime_features,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4ak_real_runtime_feature_generation_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ak_real_runtime_feature_generation_audit.md")


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
        summary = build_phase4ak_real_runtime_features(runtime_dir=runtime_dir, report_dir=report_dir)

    feature_output = Path(str(summary.get("feature_output_path") or ""))
    manifest_path = Path(str(summary.get("manifest_path") or ""))
    audit_path = Path(str(summary.get("audit_path") or ""))
    features_payload = _read_json_optional(feature_output)
    manifest = _read_json_optional(manifest_path)
    audit = _read_json_optional(audit_path)
    rows = features_payload.get("rows") if isinstance(features_payload.get("rows"), list) else []

    checks = {
        "summary_exists": summary_path.is_file(),
        "feature_output_exists": feature_output.is_file(),
        "manifest_exists": manifest_path.is_file(),
        "audit_exists": audit_path.is_file(),
        "readiness_ready_for_label_generation": summary.get("readiness_status") == READY,
        "feature_generation_executed": summary.get("feature_generation_executed") is True,
        "schema_validation_ok": summary.get("schema_validation_status") == "OK"
        and audit.get("schema_validation_status") == "OK",
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK" and audit.get("leakage_audit_status") == "OK",
        "feature_rows_positive": int(summary.get("feature_row_count") or 0) > 0 and bool(rows),
        "eligible_count_positive": int(summary.get("eligible_count") or 0) > 0,
        "required_features_present": _required_features_present(rows),
        "forbidden_feature_not_detected": summary.get("forbidden_feature_detected") is False
        and audit.get("forbidden_feature_detected") is False,
        "future_column_not_detected": summary.get("future_column_detected") is False
        and audit.get("future_column_detected") is False,
        "label_column_not_detected": summary.get("label_column_detected") is False
        and audit.get("label_column_detected") is False,
        "manifest_real_runtime": manifest.get("data_source_type") == "real_runtime",
        "runtime_candidate_ai_paths": _paths_under_candidate_runtime(summary, manifest),
        "promotion_not_performed": summary.get("promotion_performed") is False
        and manifest.get("promotion_performed") is False,
        "reader_switch_not_performed": summary.get("reader_switch_performed") is False
        and manifest.get("reader_switch_performed") is False,
        "label_training_inference_backtest_trading_not_executed": all(
            summary.get(key) is False
            for key in (
                "label_generation_executed",
                "training_executed",
                "inference_executed",
                "backtest_executed",
                "trading_executed",
            )
        ),
        "broker_order_paper_portfolio_not_executed": all(
            summary.get(key) is False
            for key in (
                "paper_trading_executed",
                "broker_api_executed",
                "order_executed",
            )
        ),
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(manifest) and _no_secret_terms(audit),
    }
    result = {
        "phase": "Phase4-AK",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ak_real_runtime_feature_generation.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _required_features_present(rows: list[Any]) -> bool:
    if not rows:
        return False
    columns = set(rows[0].keys())
    return all(column in columns for column in REQUIRED_AK_FEATURE_COLUMNS) and "universe_eligible" in columns and "excluded_reason" in columns


def _paths_under_candidate_runtime(summary: dict[str, Any], manifest: dict[str, Any]) -> bool:
    for value in (
        summary.get("feature_output_path"),
        summary.get("manifest_path"),
        summary.get("audit_path"),
        manifest.get("output_path"),
        manifest.get("manifest_path"),
        manifest.get("audit_path"),
    ):
        normalized = str(value).replace("\\", "/")
        if not value or "/candidate_ai/" not in normalized:
            return False
    return True


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "schema_validation_status",
        "leakage_audit_status",
        "raw_row_count",
        "normalized_row_count",
        "feature_row_count",
        "eligible_count",
        "excluded_count",
        "business_day_count",
        "code_count",
        "date_min",
        "date_max",
        "feature_column_count",
        "null_count",
        "forbidden_feature_detected",
        "future_column_detected",
        "label_column_detected",
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
        "# Phase4-AK Real Runtime Feature Generation Audit",
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
            "- This audit checks Candidate feature generation only.",
            "- It confirms no label generation, dataset builder, training, inference, backtest, trading, Paper Trading, promotion, reader switch, Broker API, or order placement occurred.",
            "- Phase4-AL may generate future labels in a physically separate label table.",
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
