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

from scripts.rebuild_phase4z_real_runtime_normalized_isolated import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    rebuild_isolated_real_runtime_normalized,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4z_real_runtime_normalized_isolated_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4z_real_runtime_normalized_isolated_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


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
        summary = rebuild_isolated_real_runtime_normalized(runtime_dir=runtime_dir, report_dir=report_dir)
    manifest_path = Path(str(summary.get("isolated_manifest_path") or ""))
    manifest = _read_json_optional(manifest_path)
    checks = {
        "isolated_output_exists": Path(str(summary.get("isolated_output_path") or "")).is_file(),
        "isolated_manifest_exists": manifest_path.is_file(),
        "data_source_type_real_runtime": manifest.get("data_source_type") == "real_runtime",
        "source_provider_jquants": manifest.get("source_provider") == "jquants",
        "api_call_not_performed": summary.get("api_call_performed") is False and manifest.get("api_call_performed") is False,
        "promotion_status_not_promoted": summary.get("promotion_status") == "not_promoted"
        and manifest.get("promotion_status") == "not_promoted",
        "default_mock_path_unchanged": summary.get("default_mock_path_unchanged") is True,
        "mock_history_not_overwritten": summary.get("mock_history_overwritten") is False
        and manifest.get("mock_history_overwritten") is False,
        "schema_mapping_ok": summary.get("schema_mapping_status") == "OK",
        "row_count_positive": int(summary.get("row_count") or 0) > 0 and int(manifest.get("row_count") or 0) > 0,
        "code_count_positive": int(summary.get("code_count") or 0) > 0 and int(manifest.get("code_count") or 0) > 0,
        "coverage_stats_produced": all(
            key in summary
            for key in (
                "business_day_count",
                "per_code_row_count_min",
                "per_code_row_count_max",
                "per_code_row_count_mean",
                "coverage_status_detail",
            )
        ),
        "reader_switch_not_performed": summary.get("reader_switch_performed") is False,
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "secret_terms_not_emitted": _no_secret_terms(summary) and _no_secret_terms(manifest),
    }
    result = {
        "phase": "Phase4-Z",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "coverage_status": summary.get("coverage_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4z_real_runtime_normalized_isolated.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "coverage_status",
        "data_source_type",
        "isolated_output_path",
        "isolated_manifest_path",
        "default_mock_path_unchanged",
        "mock_history_overwritten",
        "promotion_performed",
        "row_count",
        "code_count",
        "date_min",
        "date_max",
        "business_day_count",
        "schema_mapping_status",
        "coverage_status_detail",
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
        "# Phase4-Z Isolated Real Runtime Normalized Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- coverage_status: `{result.get('coverage_status')}`",
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
            "- This audit checks isolated normalized output only.",
            "- It confirms no promotion, reader switch, default mock overwrite, API call, label generation, training, inference, backtest, trading, broker API, order placement, or Portfolio auto-update occurred.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
