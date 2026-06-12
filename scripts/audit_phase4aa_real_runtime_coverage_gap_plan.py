#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PHASE4Z_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4z_real_runtime_normalized_isolated_summary.json")
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4aa_real_runtime_coverage_gap_plan_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4aa_real_runtime_coverage_gap_plan_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4aa_real_runtime_coverage_gap_plan_audit.md")

READY = "READY_FOR_REAL_RUNTIME_HISTORY_FETCH_PLAN"
BLOCKED_MISSING = "BLOCKED_BY_MISSING_ISOLATED_NORMALIZED"
BLOCKED_PROVENANCE = "BLOCKED_BY_UNKNOWN_PROVENANCE"
MINIMUM_REQUIRED_BUSINESS_DAYS = 60
PREFERRED_TRAINING_START_DATE = "2021-06-01"


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    phase4z_summary_path: Path = PHASE4Z_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_coverage_gap_summary(phase4z_summary_path=phase4z_summary_path, summary_path=summary_path)
    checks = {
        "coverage_gap_summary_exists": summary_path.is_file(),
        "api_call_not_performed": summary.get("api_call_performed") is False,
        "isolated_real_runtime_normalized_detected": summary.get("isolated_real_runtime_detected") is True,
        "coverage_stats_produced": all(
            key in summary
            for key in (
                "row_count",
                "code_count",
                "date_min",
                "date_max",
                "business_day_count",
                "normalization_error_count",
            )
        ),
        "required_coverage_defined": summary.get("required_business_day_count") == MINIMUM_REQUIRED_BUSINESS_DAYS,
        "missing_coverage_calculated": summary.get("missing_business_day_count") == max(
            0, MINIMUM_REQUIRED_BUSINESS_DAYS - int(summary.get("business_day_count") or 0)
        ),
        "fetch_range_plan_defined": bool(summary.get("fetch_range_start")) and bool(summary.get("fetch_range_end")),
        "mock_path_unchanged_rule_defined": summary.get("mock_path_will_be_unchanged") is True,
        "manifest_provenance_rule_defined": summary.get("manifest_provenance_rule_defined") is True,
        "api_safety_rule_defined": summary.get("api_safety_rule_defined") is True,
        "promotion_gate_defined": summary.get("promotion_gate_defined") is True,
        "rollback_plan_defined": summary.get("rollback_plan_defined") is True,
        "readiness_status_produced": summary.get("readiness_status")
        in {
            READY,
            BLOCKED_MISSING,
            BLOCKED_PROVENANCE,
            "BLOCKED_BY_COVERAGE_AUDIT",
            "BLOCKED_BY_API_SAFETY_RULE",
            "SKIPPED_NO_REAL_RUNTIME_NORMALIZED",
        },
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "secret_terms_not_emitted": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-AA",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4aa_real_runtime_coverage_gap_plan.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_coverage_gap_summary(
    *,
    phase4z_summary_path: Path = PHASE4Z_SUMMARY_PATH,
    summary_path: Path = SUMMARY_PATH,
) -> dict[str, Any]:
    phase4z_summary = _read_json_optional(phase4z_summary_path)
    isolated_path = str(phase4z_summary.get("isolated_output_path") or "")
    manifest = phase4z_summary.get("manifest") if isinstance(phase4z_summary.get("manifest"), dict) else {}
    isolated_detected = (
        phase4z_summary.get("data_source_type") == "real_runtime"
        and bool(isolated_path)
        and Path(isolated_path).is_file()
    )
    provenance_known = (
        manifest.get("data_source_type") == "real_runtime"
        and manifest.get("source_provider") == "jquants"
        and manifest.get("promotion_status") == "not_promoted"
    )
    business_day_count = int(phase4z_summary.get("business_day_count") or 0)
    missing_business_day_count = max(0, MINIMUM_REQUIRED_BUSINESS_DAYS - business_day_count)
    coverage_sufficient_for_features = business_day_count >= MINIMUM_REQUIRED_BUSINESS_DAYS
    readiness_status = _readiness_status(isolated_detected=isolated_detected, provenance_known=provenance_known)
    fetch_range = _build_fetch_range_plan(str(phase4z_summary.get("date_max") or ""))
    summary = {
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "isolated_real_runtime_detected": isolated_detected,
        "isolated_path": isolated_path or None,
        "row_count": int(phase4z_summary.get("row_count") or 0),
        "code_count": int(phase4z_summary.get("code_count") or 0),
        "date_min": phase4z_summary.get("date_min"),
        "date_max": phase4z_summary.get("date_max"),
        "business_day_count": business_day_count,
        "per_code_row_count_min": phase4z_summary.get("per_code_row_count_min"),
        "per_code_row_count_max": phase4z_summary.get("per_code_row_count_max"),
        "per_code_row_count_mean": phase4z_summary.get("per_code_row_count_mean"),
        "required_business_day_count": MINIMUM_REQUIRED_BUSINESS_DAYS,
        "missing_business_day_count": missing_business_day_count,
        "coverage_sufficient_for_features": coverage_sufficient_for_features,
        "coverage_sufficient_for_training": False,
        "normalization_error_count": int(phase4z_summary.get("normalization_error_count") or 0),
        "fetch_plan_required": not coverage_sufficient_for_features,
        "fetch_range_start": fetch_range["fetch_range_start"],
        "fetch_range_end": fetch_range["fetch_range_end"],
        "target_end_date": fetch_range["fetch_range_end"],
        "target_start_date_rule": "at least 90 calendar days before target_end_date for initial 60-business-day coverage",
        "preferred_training_start_date": PREFERRED_TRAINING_START_DATE,
        "isolated_output_path": ".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/",
        "raw_output_path": ".runtime/data/raw/jquants/equities_bars_daily/",
        "default_mock_path": ".runtime/data/raw_normalized/jquants/equities_bars_daily/",
        "mock_path_will_be_unchanged": True,
        "manifest_provenance_rule_defined": True,
        "manifest_required_fields": (
            "data_source_type",
            "source_provider",
            "api_call_performed",
            "source_raw_path",
            "source_raw_manifest_path",
            "fetch_range_start",
            "fetch_range_end",
            "normalizer_version",
            "schema_version",
            "row_count",
            "code_count",
            "date_min",
            "date_max",
            "input_hash_optional",
            "output_hash_optional",
            "promotion_status",
        ),
        "api_safety_rule_defined": True,
        "api_safety_rule": "No API call in Phase4-AA; future fetch must use non-committed credentials, sanitized logs, dry-run plan, provenance audit, and no mock-path overwrite.",
        "promotion_gate_defined": True,
        "promotion_gate": (
            "Require coverage audit OK, business_day_count >= 60, schema validation OK, provenance manifest OK, "
            "non-mock source path, and approved promotion_status before any reader switch."
        ),
        "rollback_plan_defined": True,
        "rollback_plan": "Before reader switch, remove isolated real_runtime output only; mock normalized path remains authoritative.",
        "post_fetch_coverage_audit_required": True,
        "recommended_next_action": (
            "Prepare a no-live dry-run fetch plan for at least 60 business days, then fetch and normalize into the "
            "isolated real_runtime path only after explicit approval."
        ),
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
    }
    _write_json(summary_path, summary)
    return summary


def _readiness_status(*, isolated_detected: bool, provenance_known: bool) -> str:
    if not isolated_detected:
        return BLOCKED_MISSING
    if not provenance_known:
        return BLOCKED_PROVENANCE
    return READY


def _build_fetch_range_plan(date_max: str) -> dict[str, str | None]:
    end_date = _parse_date(date_max) or date.today()
    start_date = end_date - timedelta(days=90)
    return {
        "fetch_range_start": start_date.isoformat(),
        "fetch_range_end": end_date.isoformat(),
    }


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "api_call_performed",
        "isolated_real_runtime_detected",
        "isolated_path",
        "row_count",
        "code_count",
        "date_min",
        "date_max",
        "business_day_count",
        "required_business_day_count",
        "missing_business_day_count",
        "coverage_sufficient_for_features",
        "coverage_sufficient_for_training",
        "normalization_error_count",
        "fetch_plan_required",
        "fetch_range_start",
        "fetch_range_end",
        "preferred_training_start_date",
        "mock_path_will_be_unchanged",
        "promotion_gate_defined",
        "rollback_plan_defined",
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
        "# Phase4-AA Real Runtime Coverage Gap Plan Audit",
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
            "- Phase4-AA is a plan and audit only.",
            "- It does not call J-Quants APIs, fetch live data, promote real_runtime data, switch readers, generate features, generate labels, train, infer, backtest, trade, place orders, or update Portfolio state.",
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
