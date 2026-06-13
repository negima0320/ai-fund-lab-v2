#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
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

from ai_fund_lab_v2.data_store import create_storage_backend  # noqa: E402
from ai_fund_lab_v2.runtime import RuntimePaths  # noqa: E402

PHASE = "Phase4-AL"
SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4al_label_generation_summary.json")
PHASE4AK_SUMMARY_PATH = Path("reports/candidate_ai/full_range/phase4ak_real_runtime_feature_generation_summary.json")

READY_INPUT = "READY_FOR_LABEL_GENERATION"
READY = "READY_FOR_DATASET_BUILDER"
BLOCKED_GENERATION = "BLOCKED_BY_LABEL_GENERATION"
BLOCKED_LEAKAGE = "BLOCKED_BY_LABEL_LEAKAGE"
BLOCKED_PATH = "BLOCKED_BY_OUTPUT_PATH_SAFETY"

LABEL_VERSION = "candidate_labels_real_runtime_v1"
DOWNSIDE_BAD_THRESHOLD_20D = -0.10
LABEL_COLUMNS = (
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_max_return_20d",
    "future_max_drawdown_20d",
    "top_decile_20d",
    "downside_bad_20d",
    "momentum_candidate_label",
)
FORBIDDEN_NON_LABEL_TERMS = (
    "backtest",
    "trade",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
    "paper_trade",
    "position",
    "allocation",
    "order",
    "execution",
    "profit",
    "loss",
    "pnl",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Phase4-AL Candidate label table from real_runtime normalized data.")
    parser.add_argument("--runtime-dir", default=".runtime")
    parser.add_argument("--report-dir", default="reports/candidate_ai/full_range")
    parser.add_argument("--input-format", choices=("parquet", "jsonl"), default="parquet")
    parser.add_argument("--phase4ak-summary", default=str(PHASE4AK_SUMMARY_PATH))
    args = parser.parse_args(argv)
    summary = build_phase4al_labels(
        runtime_dir=args.runtime_dir,
        report_dir=args.report_dir,
        input_format=args.input_format,
        phase4ak_summary_path=Path(args.phase4ak_summary),
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary.get("status") in {"OK", "BLOCKED"} else 1


def build_phase4al_labels(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    input_format: str = "parquet",
    phase4ak_summary_path: Path = PHASE4AK_SUMMARY_PATH,
) -> dict[str, Any]:
    paths = RuntimePaths(runtime_dir=Path(runtime_dir))
    report_dir = Path(report_dir)
    summary_path = report_dir / SUMMARY_PATH.name
    phase4ak_summary = _read_json_optional(phase4ak_summary_path)
    normalized_path = _real_runtime_normalized_path(paths, input_format)
    labels_dir = paths.runtime_dir / "candidate_ai" / "labels"
    manifests_dir = paths.runtime_dir / "candidate_ai" / "manifests"
    audit_dir = paths.runtime_dir / "candidate_ai" / "audit"

    if phase4ak_summary.get("readiness_status") != READY_INPUT:
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Phase4-AK summary is missing or not ready for label generation.",
            paths=paths,
            normalized_path=normalized_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    if not _safe_runtime_output_path(paths.runtime_dir, labels_dir):
        summary = _blocked_summary(
            readiness_status=BLOCKED_PATH,
            reason="Label output path is not under .runtime/candidate_ai/labels.",
            paths=paths,
            normalized_path=normalized_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    feature_table_path = Path(str(phase4ak_summary.get("feature_output_path") or ""))
    feature_hash_before = _file_hash(feature_table_path)
    if not normalized_path.is_file() or not feature_table_path.is_file():
        summary = _blocked_summary(
            readiness_status=BLOCKED_GENERATION,
            reason="Required normalized input or Phase4-AK feature table is missing.",
            paths=paths,
            normalized_path=normalized_path,
            summary_path=summary_path,
        )
        _write_json(summary_path, summary)
        return summary

    normalized_records = create_storage_backend(input_format).read_records(normalized_path)
    label_rows = build_label_rows(
        normalized_records,
        source_snapshot_id=f"phase4ak:{phase4ak_summary.get('manifest_path') or feature_table_path}",
    )
    leakage = audit_label_table_isolation(label_rows=label_rows, feature_table_path=feature_table_path)
    feature_hash_after = _file_hash(feature_table_path)
    feature_table_modified = feature_hash_before != feature_hash_after
    feature_table_joined = _feature_table_contains_label_columns(feature_table_path)
    leakage_audit_status = (
        "OK"
        if leakage["status"] == "OK" and not feature_table_modified and not feature_table_joined
        else "ERROR"
    )
    readiness_status = _resolve_readiness(
        label_rows=label_rows,
        leakage_audit_status=leakage_audit_status,
        feature_table_modified=feature_table_modified,
        feature_table_joined=feature_table_joined,
    )

    date_min, date_max = _label_date_range(label_rows)
    labels_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    label_path = labels_dir / f"phase4al_labels_{date_min or 'none'}_{date_max or 'none'}.json"
    manifest_path = manifests_dir / f"phase4al_labels_manifest_{date_min or 'none'}_{date_max or 'none'}.json"
    audit_path = audit_dir / f"phase4al_labels_audit_{date_min or 'none'}_{date_max or 'none'}.json"

    counts = _label_counts(label_rows)
    audit_payload = {
        **leakage,
        "leakage_audit_status": leakage_audit_status,
        "feature_table_modified": feature_table_modified,
        "feature_table_joined": feature_table_joined,
        "label_row_count": len(label_rows),
        "label_columns": list(LABEL_COLUMNS),
        "label_counts": counts,
    }
    manifest_payload = {
        "phase": PHASE,
        "created_at": _now(),
        "label_version": LABEL_VERSION,
        "data_source_type": "real_runtime",
        "input_sources": ["daily_quotes_normalized_real_runtime", "phase4ak_feature_table_reference"],
        "normalized_input_path": str(normalized_path),
        "feature_table_path_reference": str(feature_table_path),
        "feature_table_joined": False,
        "label_output_path": str(label_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "target_date_min": date_min,
        "target_date_max": date_max,
        "label_row_count": len(label_rows),
        "label_column_count": len(LABEL_COLUMNS),
        "source_snapshot_id": label_rows[0].get("source_snapshot_id") if label_rows else None,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "dataset_builder_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
    }
    _write_json(label_path, {"rows": label_rows})
    _write_json(audit_path, audit_payload)
    _write_json(manifest_path, manifest_payload)

    summary = {
        "phase": PHASE,
        "status": "OK" if readiness_status == READY else "BLOCKED",
        "readiness_status": readiness_status,
        "label_generation_executed": True,
        "label_row_count": len(label_rows),
        "label_column_count": len(LABEL_COLUMNS),
        "future_return_5d_count": counts["future_return_5d_count"],
        "future_return_10d_count": counts["future_return_10d_count"],
        "future_return_20d_count": counts["future_return_20d_count"],
        "future_max_return_20d_count": counts["future_max_return_20d_count"],
        "future_max_drawdown_20d_count": counts["future_max_drawdown_20d_count"],
        "top_decile_20d_count": counts["top_decile_20d_count"],
        "downside_bad_20d_count": counts["downside_bad_20d_count"],
        "momentum_candidate_label_count": counts["momentum_candidate_label_count"],
        "feature_table_modified": feature_table_modified,
        "feature_table_joined": feature_table_joined,
        "leakage_audit_status": leakage_audit_status,
        "label_output_path": str(label_path),
        "manifest_path": str(manifest_path),
        "audit_path": str(audit_path),
        "feature_table_path_reference": str(feature_table_path),
        "normalized_input_path": str(normalized_path),
        "dataset_builder_executed": False,
        "training_executed": False,
        "inference_executed": False,
        "backtest_executed": False,
        "trading_executed": False,
        "paper_trading_executed": False,
        "broker_api_executed": False,
        "order_executed": False,
        "promotion_performed": False,
        "reader_switch_performed": False,
        "recommended_next_action": "Phase4-AM Dataset Builder: join feature and label tables only for training dataset; inference dataset must not include labels.",
        "summary_path": str(summary_path),
    }
    _write_json(summary_path, summary)
    return summary


def build_label_rows(normalized_records: list[dict[str, Any]], *, source_snapshot_id: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in normalized_records:
        date_value = str(record.get("Date") or record.get("target_date") or "")
        code = str(record.get("Code") or record.get("code") or "").strip()
        if not date_value or not code or not _is_number(record.get("Close")):
            continue
        grouped.setdefault(code, []).append({"Date": date_value, "Code": code, "Close": float(record["Close"])})
    created_at = _now()
    rows: list[dict[str, Any]] = []
    for code, records in sorted(grouped.items()):
        ordered = sorted(records, key=lambda item: item["Date"])
        for index in range(0, len(ordered) - 20):
            current = ordered[index]
            future = ordered[index + 1 : index + 21]
            close = float(current["Close"])
            future_closes = [float(item["Close"]) for item in future]
            rows.append(
                {
                    "target_date": current["Date"],
                    "code": code,
                    "label_version": LABEL_VERSION,
                    "label_horizon": "20d",
                    "future_start_date": future[0]["Date"],
                    "future_end_date": future[-1]["Date"],
                    "created_at": created_at,
                    "source_snapshot_id": source_snapshot_id,
                    "future_return_5d": _round(_safe_ratio(float(ordered[index + 5]["Close"]), close)),
                    "future_return_10d": _round(_safe_ratio(float(ordered[index + 10]["Close"]), close)),
                    "future_return_20d": _round(_safe_ratio(float(ordered[index + 20]["Close"]), close)),
                    "future_max_return_20d": _round(_safe_ratio(max(future_closes), close)),
                    "future_max_drawdown_20d": _round(_safe_ratio(min(future_closes), close)),
                }
            )
    _assign_cross_sectional_labels(rows)
    return rows


def audit_label_table_isolation(*, label_rows: list[dict[str, Any]], feature_table_path: Path) -> dict[str, Any]:
    label_columns = {column for row in label_rows for column in row.keys()}
    unexpected_columns = sorted(
        column
        for column in label_columns
        if _contains_forbidden_non_label_term(column) and column not in LABEL_COLUMNS
    )
    feature_has_label_columns = _feature_table_contains_label_columns(feature_table_path)
    status = "OK" if label_rows and not unexpected_columns and not feature_has_label_columns else "ERROR"
    return {
        "status": status,
        "unexpected_forbidden_columns": unexpected_columns,
        "feature_table_contains_label_columns": feature_has_label_columns,
        "label_table_physically_separate": "/candidate_ai/labels/" not in str(feature_table_path).replace("\\", "/"),
        "messages": [] if status == "OK" else ["label isolation audit failed"],
    }


def _assign_cross_sectional_labels(rows: list[dict[str, Any]]) -> None:
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_date.setdefault(str(row["target_date"]), []).append(row)
    for date_rows in by_date.values():
        ranked = sorted(date_rows, key=lambda row: float(row["future_return_20d"]), reverse=True)
        top_count = max(1, math.ceil(len(ranked) * 0.1))
        top_keys = {(row["target_date"], row["code"]) for row in ranked[:top_count]}
        for row in date_rows:
            row["top_decile_20d"] = (row["target_date"], row["code"]) in top_keys
            row["downside_bad_20d"] = float(row["future_max_drawdown_20d"]) <= DOWNSIDE_BAD_THRESHOLD_20D
            row["momentum_candidate_label"] = bool(row["top_decile_20d"] and not row["downside_bad_20d"])


def _label_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for column in LABEL_COLUMNS:
        if column in {"top_decile_20d", "downside_bad_20d", "momentum_candidate_label"}:
            counts[f"{column}_count"] = sum(1 for row in rows if row.get(column) is True)
        else:
            counts[f"{column}_count"] = sum(1 for row in rows if row.get(column) is not None)
    return counts


def _resolve_readiness(
    *,
    label_rows: list[dict[str, Any]],
    leakage_audit_status: str,
    feature_table_modified: bool,
    feature_table_joined: bool,
) -> str:
    if not label_rows:
        return BLOCKED_GENERATION
    if leakage_audit_status != "OK" or feature_table_modified or feature_table_joined:
        return BLOCKED_LEAKAGE
    return READY


def _feature_table_contains_label_columns(path: Path) -> bool:
    if not path.is_file():
        return False
    payload = _read_json_optional(path)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    if not rows:
        return False
    columns = {column for row in rows for column in row.keys()}
    return any(column in LABEL_COLUMNS or column.startswith(("future_return_", "future_max_return_", "future_max_drawdown_", "top_decile_", "downside_bad_")) or "label" in column for column in columns)


def _label_date_range(rows: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    dates = sorted({str(row.get("target_date") or "") for row in rows if row.get("target_date")})
    return (dates[0] if dates else None, dates[-1] if dates else None)


def _real_runtime_normalized_path(paths: RuntimePaths, input_format: str) -> Path:
    return create_storage_backend(input_format).path_for(
        paths.runtime_dir / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily" / "data"
    )


def _safe_runtime_output_path(runtime_dir: Path, labels_dir: Path) -> bool:
    try:
        labels_dir.resolve().relative_to((runtime_dir.resolve() / "candidate_ai" / "labels").resolve())
        return True
    except ValueError:
        return False


def _blocked_summary(
    *,
    readiness_status: str,
    reason: str,
    paths: RuntimePaths,
    normalized_path: Path,
    summary_path: Path,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "BLOCKED",
        "readiness_status": readiness_status,
        "block_reason": reason,
        "label_generation_executed": False,
        "label_row_count": 0,
        "label_column_count": len(LABEL_COLUMNS),
        "future_return_5d_count": 0,
        "future_return_10d_count": 0,
        "future_return_20d_count": 0,
        "future_max_return_20d_count": 0,
        "future_max_drawdown_20d_count": 0,
        "top_decile_20d_count": 0,
        "downside_bad_20d_count": 0,
        "momentum_candidate_label_count": 0,
        "feature_table_modified": False,
        "feature_table_joined": False,
        "leakage_audit_status": "SKIPPED",
        "normalized_input_path": str(normalized_path),
        "runtime_dir": str(paths.runtime_dir),
        "recommended_next_action": "Fix the blocking condition, then rerun Phase4-AL.",
        "summary_path": str(summary_path),
    }


def _contains_forbidden_non_label_term(column: str) -> bool:
    normalized = column.lower()
    tokens = [token for token in normalized.replace("-", "_").split("_") if token]
    return any(term in normalized or term in tokens for term in FORBIDDEN_NON_LABEL_TERMS)


def _is_number(value: Any) -> bool:
    if value is None or value == "":
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return not math.isnan(number)


def _safe_ratio(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return current / previous - 1.0


def _round(value: float) -> float:
    return round(value, 6)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
