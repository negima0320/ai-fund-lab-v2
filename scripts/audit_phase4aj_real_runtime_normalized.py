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

from scripts.rebuild_phase4aj_real_runtime_normalized import (  # noqa: E402
    READY,
    REQUIRED_BUSINESS_DAY_COUNT,
    SUMMARY_PATH,
    rebuild_phase4aj_real_runtime_normalized,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4aj_real_runtime_normalized_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4aj_real_runtime_normalized_audit.md")


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
        summary = rebuild_phase4aj_real_runtime_normalized(runtime_dir=runtime_dir, report_dir=report_dir)

    isolated_output = Path(str(summary.get("isolated_output_path") or ""))
    isolated_manifest = Path(str(summary.get("isolated_manifest_path") or ""))
    manifest = _read_json_optional(isolated_manifest)

    checks = {
        "summary_exists": summary_path.is_file(),
        "isolated_output_exists": isolated_output.is_file(),
        "isolated_manifest_exists": isolated_manifest.is_file(),
        "readiness_ready_for_real_runtime_feature_generation": summary.get("readiness_status") == READY,
        "raw_row_count_positive": int(summary.get("raw_row_count") or 0) > 0,
        "normalized_row_count_positive": int(summary.get("normalized_row_count") or 0) > 0,
        "raw_to_normalized_accounted_for": int(summary.get("normalized_row_count") or 0)
        + int(summary.get("price_missing_excluded_count") or 0)
        == int(summary.get("raw_row_count") or -1),
        "business_day_count_sufficient": int(summary.get("business_day_count") or 0) >= REQUIRED_BUSINESS_DAY_COUNT,
        "code_count_positive": int(summary.get("code_count") or 0) > 0,
        "date_range_present": bool(summary.get("date_min")) and bool(summary.get("date_max")),
        "normalization_error_count_zero": int(summary.get("normalization_error_count") or 0) == 0,
        "schema_mapping_ok": summary.get("schema_mapping_status") == "OK",
        "manifest_row_count_matches_summary": int(manifest.get("normalized_row_count") or -1)
        == int(summary.get("normalized_row_count") or -2),
        "manifest_data_source_real_runtime": manifest.get("data_source_type") == "real_runtime",
        "manifest_schema_version_ok": int(manifest.get("schema_version") or 0) == 2,
        "promotion_status_not_promoted": summary.get("promotion_status") == "not_promoted"
        and manifest.get("promotion_status") == "not_promoted",
        "promotion_not_performed": summary.get("promotion_performed") is False
        and manifest.get("promotion_performed") is False,
        "reader_switch_not_performed": summary.get("reader_switch_performed") is False
        and manifest.get("reader_switch_performed") is False,
        "mock_path_unchanged": summary.get("mock_path_unchanged") is True and manifest.get("mock_path_unchanged") is True,
        "feature_label_training_backtest_trading_not_executed": all(
            summary.get(key) is False
            for key in (
                "feature_generation_executed",
                "label_generation_executed",
                "training_executed",
                "backtest_executed",
                "trading_executed",
            )
        ),
        "broker_order_paper_trading_not_executed": all(
            summary.get(key) is False
            for key in (
                "paper_trading_executed",
                "broker_api_executed",
                "order_executed",
                "portfolio_auto_update_executed",
            )
        ),
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(manifest),
    }

    result = {
        "phase": "Phase4-AJ",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4aj_real_runtime_normalized.py && python3 -m pytest -q",
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
        "code_count",
        "date_min",
        "date_max",
        "business_day_count",
        "normalization_error_count",
        "price_missing_excluded_count",
        "schema_mapping_status",
        "promotion_status",
        "promotion_performed",
        "reader_switch_performed",
        "mock_path_unchanged",
        "isolated_output_path",
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
        "# Phase4-AJ Real Runtime Normalized Audit",
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
            "- This audit checks isolated real_runtime normalized rebuild only.",
            "- It confirms no promotion, reader switch, feature generation, label generation, dataset builder, training, inference, backtest, trading, Paper Trading, broker API, order placement, or Portfolio auto-update occurred.",
            "- The mock normalized path under `.runtime/data/raw_normalized/jquants/equities_bars_daily/` must remain unchanged.",
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
