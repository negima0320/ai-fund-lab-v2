#!/usr/bin/env python3
from __future__ import annotations

import hashlib
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

from ai_fund_lab_v2.data_quality.normalization import (  # noqa: E402
    NORMALIZED_SCHEMA_VERSION,
    normalize_daily_quotes,
)
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402
from scripts.audit_phase4x_real_runtime_normalized_source import (  # noqa: E402
    READY_REBUILD,
    build_real_runtime_normalized_source_summary,
)

SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4y_real_runtime_normalized_rebuild_plan_summary.json")
JSON_REPORT_PATH = Path("reports/phase_reports/phase4y_real_runtime_normalized_rebuild_plan_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4y_real_runtime_normalized_rebuild_plan_audit.md")

READY = "READY_TO_IMPLEMENT_ISOLATED_REAL_RUNTIME_NORMALIZED_REBUILD"
BLOCKED_RAW = "BLOCKED_BY_MISSING_RAW"
BLOCKED_NORMALIZER = "BLOCKED_BY_MISSING_NORMALIZER"
BLOCKED_SCHEMA = "BLOCKED_BY_SCHEMA_MAPPING"
BLOCKED_OVERWRITE = "BLOCKED_BY_OVERWRITE_RISK"
BLOCKED_PROVENANCE = "BLOCKED_BY_UNKNOWN_PROVENANCE"
SKIPPED_NO_RAW = "SKIPPED_NO_RAW"

SCHEMA_MAPPING = {
    "Date": "Date",
    "Code": "Code",
    "AdjO or O": "Open",
    "AdjH or H": "High",
    "AdjL or L": "Low",
    "AdjC or C": "Close",
    "AdjVo or Vo": "Volume",
}


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def run_audit(
    *,
    runtime_dir: Path | str = ".runtime",
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = build_real_runtime_normalized_rebuild_plan_summary(runtime_dir=runtime_dir)
    _write_json(summary_path, summary)
    checks = {
        "rebuild_plan_summary_exists": summary_path.is_file(),
        "api_call_not_performed": summary.get("api_call_performed") is False,
        "raw_daily_quotes_detected": summary.get("raw_daily_quotes_detected") is True,
        "isolated_output_path_defined": bool(summary.get("isolated_output_path"))
        and "raw_normalized_real_runtime" in str(summary.get("isolated_output_path")),
        "mock_overwrite_prevented_by_design": summary.get("would_overwrite_mock_history") is True
        and summary.get("isolated_output_overwrites_mock") is False,
        "schema_mapping_defined": summary.get("schema_mapping_defined") is True,
        "provenance_manifest_defined": summary.get("provenance_manifest_defined") is True,
        "promotion_condition_defined": summary.get("promotion_condition_defined") is True,
        "rollback_plan_defined": summary.get("rollback_plan_defined") is True,
        "readiness_status_produced": summary.get("readiness_status")
        in {
            READY,
            BLOCKED_RAW,
            BLOCKED_NORMALIZER,
            BLOCKED_SCHEMA,
            BLOCKED_OVERWRITE,
            BLOCKED_PROVENANCE,
            SKIPPED_NO_RAW,
        },
        "ready_or_clear_blocked_or_skipped_status_produced": summary.get("status") in {"READY", "BLOCKED", "SKIPPED"},
        "normalized_rebuild_not_executed": summary.get("normalized_rebuild_executed") is False,
        "mock_history_not_overwritten": summary.get("mock_history_overwritten") is False,
        "label_generation_not_implemented": summary.get("label_generation_executed") is False,
        "training_inference_backtest_trading_not_implemented": summary.get("training_executed") is False
        and summary.get("inference_executed") is False
        and summary.get("backtest_executed") is False
        and summary.get("trading_executed") is False,
        "secret_terms_not_emitted": _no_secret_terms(summary),
    }
    result = {
        "phase": "Phase4-Y",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4y_real_runtime_normalized_rebuild_plan.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def build_real_runtime_normalized_rebuild_plan_summary(*, runtime_dir: Path | str = ".runtime") -> dict[str, Any]:
    runtime = Path(runtime_dir)
    paths = RuntimePaths(runtime_dir=runtime)
    phase4x = build_real_runtime_normalized_source_summary(runtime_dir=runtime)
    raw_input_path = phase4x.get("selected_input_path") if phase4x.get("selected_data_source_type") == "real_raw_jquants" else phase4x.get("inventory", {}).get("raw_daily_quotes_path")
    raw_records = _read_records(Path(str(raw_input_path))) if raw_input_path else []
    expected_records, normalization_status = _expected_normalized_records(raw_records)
    isolated_output_path = _isolated_output_path(paths, "parquet")
    isolated_manifest_path = isolated_output_path.parent / "manifest.json"
    existing_path = phase4x.get("inventory", {}).get("normalized_daily_quotes_path")
    would_overwrite_mock = bool(phase4x.get("would_overwrite_mock_history"))
    isolated_overwrites_mock = bool(existing_path and Path(str(existing_path)) == isolated_output_path)
    schema_mapping_defined = set(SCHEMA_MAPPING.values()) >= {"Date", "Code", "Open", "High", "Low", "Close", "Volume"}
    provenance_manifest = _provenance_manifest_design(
        source_raw_path=str(raw_input_path) if raw_input_path else None,
        source_raw_manifest_path=phase4x.get("inventory", {}).get("manifest_path"),
        row_count=len(expected_records),
        code_count=_code_count(expected_records),
        date_min=_date_min(expected_records),
        date_max=_date_max(expected_records),
        input_hash_optional=_hash_records(raw_records),
    )
    promotion_conditions = _promotion_conditions()
    rollback_plan = _rollback_plan()
    status, readiness_status = _readiness_status(
        phase4x=phase4x,
        raw_records=raw_records,
        normalizer_available=callable(normalize_daily_quotes),
        schema_mapping_defined=schema_mapping_defined,
        isolated_output_path_defined=bool(isolated_output_path),
        isolated_overwrites_mock=isolated_overwrites_mock,
        provenance_manifest_defined=bool(provenance_manifest),
        promotion_condition_defined=bool(promotion_conditions),
        rollback_plan_defined=bool(rollback_plan),
    )
    summary = {
        "status": status,
        "readiness_status": readiness_status,
        "api_call_performed": False,
        "raw_daily_quotes_detected": bool(phase4x.get("raw_daily_quotes_detected")),
        "raw_input_path": str(raw_input_path) if raw_input_path else None,
        "raw_row_count": phase4x.get("raw_row_count", 0),
        "raw_code_count": phase4x.get("raw_code_count", 0),
        "raw_date_min": phase4x.get("raw_date_min"),
        "raw_date_max": phase4x.get("raw_date_max"),
        "existing_normalized_data_source_type": phase4x.get("provenance", {}).get("normalized_daily_quotes"),
        "existing_normalized_path": existing_path,
        "existing_normalized_row_count": phase4x.get("normalized_row_count", 0),
        "existing_normalized_date_min": phase4x.get("normalized_date_min"),
        "existing_normalized_date_max": phase4x.get("normalized_date_max"),
        "expected_normalized_row_count": len(expected_records),
        "expected_normalized_code_count": _code_count(expected_records),
        "expected_normalized_date_min": _date_min(expected_records),
        "expected_normalized_date_max": _date_max(expected_records),
        "normalization_dry_run_status": normalization_status,
        "would_overwrite_mock_history": would_overwrite_mock,
        "isolated_output_path": str(isolated_output_path),
        "isolated_manifest_path": str(isolated_manifest_path),
        "isolated_output_overwrites_mock": isolated_overwrites_mock,
        "schema_mapping_defined": schema_mapping_defined,
        "schema_mapping": SCHEMA_MAPPING,
        "provenance_manifest_defined": bool(provenance_manifest),
        "provenance_manifest_design": provenance_manifest,
        "promotion_condition_defined": bool(promotion_conditions),
        "promotion_conditions": promotion_conditions,
        "rollback_plan_defined": bool(rollback_plan),
        "rollback_plan": rollback_plan,
        "safe_rebuild_possible": bool(phase4x.get("safe_rebuild_possible")),
        "normalized_rebuild_executed": False,
        "mock_history_overwritten": False,
        "recommended_next_action": _recommended_action(readiness_status, would_overwrite_mock=would_overwrite_mock),
        "label_generation_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "summary_path": str(SUMMARY_PATH),
    }
    return summary


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    suffix = path.suffix.lstrip(".")
    if suffix not in {"parquet", "jsonl"}:
        return []
    return create_storage_backend(suffix).read_records(path)


def _expected_normalized_records(raw_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    if not raw_records:
        return [], "SKIPPED"
    records, report = normalize_daily_quotes(raw_records)
    return records, report.status


def _isolated_output_path(paths: RuntimePaths, output_format: str) -> Path:
    return create_storage_backend(output_format).path_for(
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data"
    )


def _provenance_manifest_design(
    *,
    source_raw_path: str | None,
    source_raw_manifest_path: str | None,
    row_count: int,
    code_count: int,
    date_min: str | None,
    date_max: str | None,
    input_hash_optional: str | None,
) -> dict[str, Any]:
    return {
        "data_source_type": "real_runtime",
        "source_provider": "jquants",
        "api_call_performed": False,
        "source_raw_path": source_raw_path,
        "source_raw_manifest_path": source_raw_manifest_path,
        "created_at": "<runtime generated at execution>",
        "normalizer_version": "normalize_daily_quotes_v1",
        "schema_version": NORMALIZED_SCHEMA_VERSION,
        "row_count": row_count,
        "code_count": code_count,
        "date_min": date_min,
        "date_max": date_max,
        "input_hash_optional": input_hash_optional,
        "output_hash_optional": "<computed after isolated output write>",
    }


def _promotion_conditions() -> list[str]:
    return [
        "provenance manifest exists for isolated real_runtime output",
        "data_source_type is real_runtime",
        "source_provider is jquants",
        "mock manifest is absent for the selected path",
        "api_call_performed is explicitly recorded",
        "schema validation is OK",
        "coverage audit is OK",
        "reader switch is gated by manifest provenance, not by path alone",
    ]


def _rollback_plan() -> list[str]:
    return [
        "delete isolated real_runtime output directory to rollback",
        "do not modify the default mock normalized path during rebuild",
        "keep reader selection behind a manifest gate",
        "run coverage audit before any promotion",
    ]


def _readiness_status(
    *,
    phase4x: dict[str, Any],
    raw_records: list[dict[str, Any]],
    normalizer_available: bool,
    schema_mapping_defined: bool,
    isolated_output_path_defined: bool,
    isolated_overwrites_mock: bool,
    provenance_manifest_defined: bool,
    promotion_condition_defined: bool,
    rollback_plan_defined: bool,
) -> tuple[str, str]:
    if not phase4x.get("raw_daily_quotes_detected"):
        return ("SKIPPED", SKIPPED_NO_RAW)
    if not raw_records:
        return ("BLOCKED", BLOCKED_RAW)
    if not phase4x.get("safe_rebuild_possible"):
        return ("BLOCKED", BLOCKED_PROVENANCE)
    if not normalizer_available:
        return ("BLOCKED", BLOCKED_NORMALIZER)
    if not schema_mapping_defined:
        return ("BLOCKED", BLOCKED_SCHEMA)
    if not isolated_output_path_defined or isolated_overwrites_mock:
        return ("BLOCKED", BLOCKED_OVERWRITE)
    if not (provenance_manifest_defined and promotion_condition_defined and rollback_plan_defined):
        return ("BLOCKED", BLOCKED_PROVENANCE)
    return ("READY", READY)


def _recommended_action(readiness_status: str, *, would_overwrite_mock: bool) -> str:
    if readiness_status == READY and would_overwrite_mock:
        return "implement isolated real_runtime normalized rebuild; do not promote until coverage audit passes"
    if readiness_status == READY:
        return "implement isolated real_runtime normalized rebuild with provenance manifest"
    if readiness_status == SKIPPED_NO_RAW:
        return "prepare raw J-Quants daily quotes before rebuild planning"
    if readiness_status == BLOCKED_RAW:
        return "fix raw input discovery before rebuild planning"
    if readiness_status == BLOCKED_NORMALIZER:
        return "provide normalizer before rebuild implementation"
    if readiness_status == BLOCKED_SCHEMA:
        return "fix raw-to-normalized schema mapping before rebuild implementation"
    if readiness_status == BLOCKED_OVERWRITE:
        return "define an isolated output path that cannot overwrite mock normalized history"
    return "fix provenance, promotion, or rollback design before implementation"


def _date_min(records: list[dict[str, Any]]) -> str | None:
    values = sorted(str(record.get("Date") or "") for record in records if record.get("Date"))
    return values[0] if values else None


def _date_max(records: list[dict[str, Any]]) -> str | None:
    values = sorted(str(record.get("Date") or "") for record in records if record.get("Date"))
    return values[-1] if values else None


def _code_count(records: list[dict[str, Any]]) -> int:
    return len({str(record.get("Code") or "") for record in records if record.get("Code")})


def _hash_records(records: list[dict[str, Any]]) -> str | None:
    if not records:
        return None
    payload = json.dumps(records, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "raw_daily_quotes_detected",
        "raw_input_path",
        "raw_row_count",
        "raw_code_count",
        "raw_date_min",
        "raw_date_max",
        "existing_normalized_data_source_type",
        "existing_normalized_row_count",
        "would_overwrite_mock_history",
        "isolated_output_path",
        "schema_mapping_defined",
        "provenance_manifest_defined",
        "promotion_condition_defined",
        "rollback_plan_defined",
        "safe_rebuild_possible",
    )
    return {key: summary.get(key) for key in keys}


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-Y Real Runtime Normalized Rebuild Plan Audit",
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
            "- This audit produces a rebuild plan only.",
            "- It does not execute normalization writes or overwrite mock history.",
            "- It performs no J-Quants API call and does not request credentials.",
            "- It does not generate labels, build datasets, train, infer, backtest, trade, call broker APIs, place orders, or update Portfolio state.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True)
    terms = ("sAuthId", "Authorization", "x-api-key", "password", "cookie", "token", "http://", "https://")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
