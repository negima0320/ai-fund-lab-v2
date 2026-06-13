#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.candidate_ai.leakage_audit import audit_feature_table  # noqa: E402
from ai_fund_lab_v2.candidate_ai.validation import validate_feature_table  # noqa: E402
from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402
from scripts.build_phase4ak_real_runtime_features import (  # noqa: E402
    FEATURE_SET_NAME,
    FEATURE_VERSION,
    REQUIRED_AK_FEATURE_COLUMNS,
    _build_feature_row,
)

PHASE = "Phase4-AN"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4an_historical_feature_coverage_summary.json")
PHASE4AL_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4al_label_generation_summary.json")

READY_INPUT = "READY_FOR_DATASET_BUILDER"
READY = "READY_FOR_DATASET_BUILDER_RETRY"
BLOCKED_GENERATION = "BLOCKED_BY_HISTORICAL_FEATURE_GENERATION"
BLOCKED_SCHEMA = "BLOCKED_BY_SCHEMA_VALIDATION"
BLOCKED_LEAKAGE = "BLOCKED_BY_LEAKAGE_AUDIT"
BLOCKED_COVERAGE = "BLOCKED_BY_FEATURE_COVERAGE"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-AN historical Candidate feature coverage.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--phase4al-summary", default=str(PHASE4AL_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = build_phase4an_historical_feature_coverage(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        phase4al_summary_path=Path(args.phase4al_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def build_phase4an_historical_feature_coverage(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "parquet",
    phase4al_summary_path: Path = PHASE4AL_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    al_summary = _read_json_optional(phase4al_summary_path)
    normalized_path = _real_runtime_normalized_path(paths, input_format)
    features_dir = paths.runtime_dir / "candidate_ai" / "features"
    manifests_dir = paths.runtime_dir / "candidate_ai" / "manifests"
    audit_dir = paths.runtime_dir / "candidate_ai" / "audit"

    if al_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Phase4-AL summary is missing or not ready.",
            paths=paths,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not _safe_runtime_output_path(paths.runtime_dir, features_dir):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Historical feature output path is not under .runtime/candidate_ai/features.",
            paths=paths,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary
    if not normalized_path.is_file():
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="real_runtime normalized input is missing.",
            paths=paths,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    normalized_records = create_storage_backend(input_format).read_records(normalized_path)
    label_path = Path(str(al_summary.get("label_output_path") or ""))
    label_rows = _read_rows(label_path)
    label_dates = sorted({str(row.get("target_date")) for row in label_rows if row.get("target_date")})
    historical_rows = build_historical_feature_rows(
        normalized_records,
        source_snapshot_id=f"phase4an:{normalized_path}",
    )
    validation = validate_feature_table(historical_rows)
    audit = audit_feature_table(historical_rows)
    schema_validation_status = "OK" if validation.is_valid and _required_features_present(historical_rows) else "ERROR"
    leakage_audit_status = "OK" if audit.status == "OK" and not audit.forbidden_feature_detected else "ERROR"
    feature_dates = sorted({str(row.get("target_date")) for row in historical_rows if row.get("target_date")})
    overlap_dates = sorted(set(feature_dates) & set(label_dates))
    coverage_status = _coverage_status(feature_dates=feature_dates, label_dates=label_dates)
    readiness_status = _resolve_readiness(
        schema_validation_status=schema_validation_status,
        leakage_audit_status=leakage_audit_status,
        coverage_status=coverage_status,
    )

    feature_date_min = feature_dates[0] if feature_dates else None
    feature_date_max = feature_dates[-1] if feature_dates else None
    label_date_min = label_dates[0] if label_dates else None
    label_date_max = label_dates[-1] if label_dates else None
    features_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    output_path = features_dir / f"phase4an_historical_features_{feature_date_min or 'none'}_{feature_date_max or 'none'}.json"
    manifest_path = manifests_dir / f"phase4an_historical_features_manifest_{feature_date_min or 'none'}_{feature_date_max or 'none'}.json"
    audit_path = audit_dir / f"phase4an_historical_features_audit_{feature_date_min or 'none'}_{feature_date_max or 'none'}.json"

    target_distribution = Counter(str(row.get("target_date")) for row in historical_rows)
    audit_payload = {
        **audit.to_dict(),
        "schema_validation_status": schema_validation_status,
        "leakage_audit_status": leakage_audit_status,
        "feature_target_date_distribution": dict(sorted(target_distribution.items())),
        "feature_target_date_count": len(feature_dates),
        "label_target_date_count": len(label_dates),
        "overlap_target_date_count": len(overlap_dates),
        "coverage_status": coverage_status,
        "validation_messages": list(validation.messages),
    }
    manifest_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "feature_version": FEATURE_VERSION,
        "feature_set_name": FEATURE_SET_NAME,
        "data_source_type": "real_runtime",
        "normalized_input_path": str(normalized_path),
        "label_table_path_reference": str(label_path),
        "output_path": str(output_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "feature_row_count": len(historical_rows),
        "feature_target_date_count": len(feature_dates),
        "feature_target_date_min": feature_date_min,
        "feature_target_date_max": feature_date_max,
        "label_target_date_count": len(label_dates),
        "label_target_date_min": label_date_min,
        "label_target_date_max": label_date_max,
        "overlap_target_date_count": len(overlap_dates),
        "schema_validation_status": schema_validation_status,
        "leakage_audit_status": leakage_audit_status,
        "label_generation_executed": False,
        "dataset_builder_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
    }
    _write_json(output_path, {"rows": historical_rows})
    _write_json(audit_path, audit_payload)
    _write_json(manifest_path, manifest_payload)

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "historical_feature_generation_executed": True,
        "feature_target_date_count": len(feature_dates),
        "label_target_date_count": len(label_dates),
        "overlap_target_date_count": len(overlap_dates),
        "expected_feature_target_date_min": label_date_min,
        "expected_feature_target_date_max": label_date_max,
        "actual_feature_target_date_min": feature_date_min,
        "actual_feature_target_date_max": feature_date_max,
        "label_target_date_min": label_date_min,
        "label_target_date_max": label_date_max,
        "generated_historical_feature_row_count": len(historical_rows),
        "generated_historical_feature_date_count": len(feature_dates),
        "eligible_count": audit.eligible_count,
        "excluded_count": audit.excluded_count,
        "schema_validation_status": schema_validation_status,
        "leakage_audit_status": leakage_audit_status,
        "coverage_status": coverage_status,
        "join_coverage_readiness": readiness_status == READY,
        "historical_feature_output_path": str(output_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "label_generation_executed": False,
        "dataset_builder_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "recommended_next_action": "Phase4-AO Dataset Builder Retry using the historical feature table.",
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_historical_feature_rows(
    normalized_records: list[dict[str, Any]],
    *,
    source_snapshot_id: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in normalized_records:
        date_value = str(record.get("Date") or record.get("target_date") or "")
        code = str(record.get("Code") or record.get("code") or "").strip()
        if not date_value or not code:
            continue
        grouped.setdefault(code, []).append(dict(record))
    created_at = _now()
    rows: list[dict[str, Any]] = []
    for code, code_rows in sorted(grouped.items()):
        ordered = sorted(code_rows, key=lambda row: str(row.get("Date") or row.get("target_date")))
        for index, row in enumerate(ordered):
            target_date = str(row.get("Date") or row.get("target_date"))
            visible_rows = ordered[: index + 1]
            rows.append(
                _build_feature_row(
                    code=code,
                    rows=visible_rows,
                    as_of_date=target_date,
                    source_snapshot_id=source_snapshot_id,
                    created_at=created_at,
                )
            )
    return rows


def _coverage_status(*, feature_dates: list[str], label_dates: list[str]) -> str:
    if not feature_dates or not label_dates:
        return "ERROR"
    feature_set = set(feature_dates)
    return "OK" if all(date in feature_set for date in label_dates) else "ERROR"


def _resolve_readiness(*, schema_validation_status: str, leakage_audit_status: str, coverage_status: str) -> str:
    if schema_validation_status != "OK":
        return BLOCKED_SCHEMA
    if leakage_audit_status != "OK":
        return BLOCKED_LEAKAGE
    if coverage_status != "OK":
        return BLOCKED_COVERAGE
    return READY


def _required_features_present(rows: list[dict[str, Any]]) -> bool:
    if not rows:
        return False
    columns = set(rows[0].keys())
    return all(column in columns for column in REQUIRED_AK_FEATURE_COLUMNS)


def _real_runtime_normalized_path(paths: RuntimePaths, input_format: str) -> Path:
    return create_storage_backend(input_format).path_for(
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data"
    )


def _safe_runtime_output_path(runtime_dir: Path, features_dir: Path) -> bool:
    try:
        features_dir.resolve().relative_to((runtime_dir.resolve() / "candidate_ai" / "features").resolve())
        return True
    except ValueError:
        return False


def _blocked_summary(*, readiness_status: str, reason: str, paths: RuntimePaths, summary_path: Path) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "historical_feature_generation_executed": False,
        "feature_target_date_count": 0,
        "label_target_date_count": 0,
        "overlap_target_date_count": 0,
        "generated_historical_feature_row_count": 0,
        "generated_historical_feature_date_count": 0,
        "schema_validation_status": "SKIPPED",
        "leakage_audit_status": "SKIPPED",
        "join_coverage_readiness": False,
        "label_generation_executed": False,
        "dataset_builder_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "runtime_dir": str(paths.runtime_dir),
        "recommended_next_action": "Fix the historical feature coverage blocker, then rerun Phase4-AN.",
        "summary_path": str(summary_path),
    }


def _read_rows(path: Path) -> list[dict[str, Any]]:
    payload = _read_json_optional(path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    return [dict(row) for row in rows]


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
