#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data_quality.normalization import normalize_daily_quotes  # noqa: E402
from ai_fund_lab_v2.paper_trading.feature_refresh import run_feature_refresh  # noqa: E402


DEFAULT_RAW_ROOT = Path(".runtime/data/raw/jquants/equities_bars_daily/responses")
DEFAULT_SUPPLEMENTAL_RAW_TABLE = Path(".runtime/data/raw/jquants/equities_bars_daily/data.parquet")
DEFAULT_OUTPUT_ROOT = Path(".runtime/phase9/canonical_data/normalized_daily_quotes")
DEFAULT_CONFIG_PATH = Path("config/phase9_data_sources.yaml")
DEFAULT_MD_REPORT = Path("docs/phase_reports/phase9j3_canonical_normalized_rebuild.md")
DEFAULT_JSON_REPORT = Path("reports/phase_reports/phase9j3_canonical_normalized_rebuild.json")
DEFAULT_LISTED_INFO_PATH = Path(".runtime/data/raw/jquants/listed_issues/data.parquet")
DEFAULT_FEATURE_OUTPUT_ROOT = Path(".runtime/phase9/features")
DEFAULT_FEATURE_MANIFEST_ROOT = Path(".runtime/phase9/feature_refresh")
DEFAULT_FEATURE_MD_REPORT = Path("docs/phase_reports/phase9j_feature_refresh_report.md")
DEFAULT_FEATURE_JSON_REPORT = Path("reports/phase_reports/phase9j_feature_refresh_report.json")

REQUIRED_COLUMNS = ("date", "code", "open", "high", "low", "close", "volume")
UPPER_COLUMNS = ("Date", "Code", "Open", "High", "Low", "Close", "Volume")
OUTPUT_COLUMNS = (
    "date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "Date",
    "Code",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "PriceSource",
    "SchemaVersion",
    "source_endpoint",
    "target_date",
    "business_key",
    "endpoint",
    "source",
)


@dataclass(frozen=True)
class CanonicalRebuildResult:
    status: str
    run_id: str
    dry_run: bool
    execute: bool
    raw_root: str
    supplemental_raw_table: str
    target_data_until: str
    normalized_output_path: str
    manifest_path: str
    markdown_report_path: str
    json_report_path: str
    row_count: int = 0
    min_date: str = ""
    max_date: str = ""
    code_count: int = 0
    raw_response_file_count: int = 0
    raw_response_min_date: str = ""
    raw_response_max_date: str = ""
    supplemental_row_count: int = 0
    supplemental_min_date: str = ""
    supplemental_max_date: str = ""
    duplicate_date_code_count: int = 0
    duplicate_rows_skipped: int = 0
    future_rows_excluded: int = 0
    abnormal_rows_excluded: int = 0
    normalization_errors: int = 0
    required_columns_status: str = "UNKNOWN"
    duplicate_check_status: str = "UNKNOWN"
    abnormal_price_check_status: str = "UNKNOWN"
    future_row_check_status: str = "UNKNOWN"
    readiness_status: str = "UNKNOWN"
    readiness_decision_for: str = ""
    lookback_ready: bool = False
    lookback_business_day_count: int = 0
    config_updated: bool = False
    config_before: str | None = None
    config_after: str | None = None
    feature_refresh_status: str = "NOT_RUN"
    candidate_eligible_rows: int = 0
    opportunity_non_null_feature_rows: int = 0
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    jquants_only_source_used: bool = True
    model_retraining_executed: bool = False
    inference_executed: bool = False
    order_plan_generation_executed: bool = False
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    paper_ledger_fill_executed: bool = False
    virtual_fill_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def rebuild_canonical_normalized_daily_quotes(
    *,
    raw_root: Path | str = DEFAULT_RAW_ROOT,
    target_data_until: str,
    dry_run: bool = True,
    execute: bool = False,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    supplemental_raw_table: Path | str | None = DEFAULT_SUPPLEMENTAL_RAW_TABLE,
    listed_info_path: Path | str = DEFAULT_LISTED_INFO_PATH,
    markdown_report_path: Path | str = DEFAULT_MD_REPORT,
    json_report_path: Path | str = DEFAULT_JSON_REPORT,
    feature_output_root: Path | str = DEFAULT_FEATURE_OUTPUT_ROOT,
    feature_manifest_root: Path | str = DEFAULT_FEATURE_MANIFEST_ROOT,
    feature_markdown_report_path: Path | str = DEFAULT_FEATURE_MD_REPORT,
    feature_json_report_path: Path | str = DEFAULT_FEATURE_JSON_REPORT,
    run_feature_refresh_after: bool = True,
    created_at: str | None = None,
) -> CanonicalRebuildResult:
    if dry_run and execute:
        raise ValueError("dry_run and execute cannot both be true.")
    created_at = created_at or _now()
    run_id = f"phase9j3_canonical_rebuild_{created_at.replace(':', '').replace('+', 'Z')}"
    raw_root = Path(raw_root)
    output_root = Path(output_root)
    output_path = output_root / "data.parquet"
    manifest_path = output_root / "normalize_manifest.json"
    config_path = Path(config_path)
    supplemental_path = Path(supplemental_raw_table) if supplemental_raw_table else None
    listed_path = Path(listed_info_path)
    md_path = Path(markdown_report_path)
    json_path = Path(json_report_path)

    warnings: list[str] = []
    blocked: list[str] = []
    raw_stats = _inspect_raw_responses(raw_root=raw_root, target_data_until=target_data_until)
    supplemental_stats = _inspect_supplemental_raw_table(supplemental_path, target_data_until=target_data_until)
    if not raw_root.exists():
        blocked.append("raw_root_missing")
    if "jquants" not in str(raw_root).lower():
        blocked.append("raw_root_not_jquants_derived")
    if supplemental_path and supplemental_path.exists() and "jquants" not in str(supplemental_path).lower():
        blocked.append("supplemental_raw_table_not_jquants_derived")
    if raw_stats["file_count"] == 0 and supplemental_stats["row_count"] == 0:
        blocked.append("no_jquants_raw_daily_quotes_found")

    config_before = _read_config_value(config_path, "normalized_daily_quotes")
    if dry_run or blocked:
        status = "CANONICAL_NORMALIZED_REBUILD_DRY_RUN" if not blocked else "CANONICAL_NORMALIZED_REBUILD_FAILED"
        result = CanonicalRebuildResult(
            status=status,
            run_id=run_id,
            dry_run=dry_run,
            execute=execute,
            raw_root=str(raw_root),
            supplemental_raw_table=str(supplemental_path or ""),
            target_data_until=target_data_until,
            normalized_output_path=str(output_path),
            manifest_path=str(manifest_path),
            markdown_report_path=str(md_path),
            json_report_path=str(json_path),
            raw_response_file_count=int(raw_stats["file_count"]),
            raw_response_min_date=str(raw_stats["min_date"]),
            raw_response_max_date=str(raw_stats["max_date"]),
            supplemental_row_count=int(supplemental_stats["row_count"]),
            supplemental_min_date=str(supplemental_stats["min_date"]),
            supplemental_max_date=str(supplemental_stats["max_date"]),
            config_before=config_before,
            warnings=tuple(warnings),
            blocked_reasons=tuple(blocked),
        )
        _write_reports(result=result, markdown_path=md_path, json_path=json_path, created_at=created_at)
        return result

    output_root.mkdir(parents=True, exist_ok=True)
    rebuild_stats = _write_normalized_parquet(
        raw_root=raw_root,
        supplemental_raw_table=supplemental_path,
        target_data_until=target_data_until,
        output_path=output_path,
    )
    warnings.extend(rebuild_stats["warnings"])
    blocked.extend(rebuild_stats["blocked_reasons"])
    required_status = "OK" if set(REQUIRED_COLUMNS).issubset(set(rebuild_stats["columns"])) else "MISSING"
    duplicate_status = "OK" if rebuild_stats["duplicate_date_code_count"] == 0 else "FAILED"
    abnormal_status = "OK" if rebuild_stats["abnormal_rows_excluded"] == 0 else "EXCLUDED"
    future_status = "OK" if rebuild_stats["future_rows_excluded"] == 0 else "EXCLUDED"
    readiness_status = "READY" if (
        rebuild_stats["max_date"] >= target_data_until
        and rebuild_stats["row_count"] > 0
        and required_status == "OK"
        and duplicate_status == "OK"
    ) else "NOT_READY"
    lookback_days = _business_day_count(
        dates=rebuild_stats["available_dates"],
        end_date=target_data_until,
        limit=25,
    )
    lookback_ready = lookback_days >= 21
    if readiness_status != "READY":
        blocked.append("canonical_normalized_readiness_not_ready")
    if not lookback_ready:
        blocked.append("lookback_21_business_days_not_ready")

    config_updated = False
    config_after = config_before
    feature_refresh_status = "NOT_RUN"
    candidate_eligible_rows = 0
    opportunity_non_null_rows = 0
    if not blocked:
        _update_config_value(config_path, "normalized_daily_quotes", str(output_path))
        config_updated = True
        config_after = _read_config_value(config_path, "normalized_daily_quotes")
        if run_feature_refresh_after:
            feature_result = run_feature_refresh(
                target_data_until=target_data_until,
                dry_run=False,
                execute=True,
                config_path=config_path,
                daily_quotes_path=output_path,
                listed_info_path=listed_path,
                feature_output_root=feature_output_root,
                manifest_root=feature_manifest_root,
                markdown_report_path=feature_markdown_report_path,
                json_report_path=feature_json_report_path,
            )
            feature_refresh_status = feature_result.status
            candidate_eligible_rows = _artifact_metric(feature_result, "candidate", "eligible_rows")
            opportunity_non_null_rows = _artifact_metric(feature_result, "opportunity", "non_null_feature_rows")
            if candidate_eligible_rows <= 0:
                blocked.append("candidate_eligible_rows_zero_after_feature_refresh")
            if opportunity_non_null_rows <= 0:
                blocked.append("opportunity_non_null_feature_rows_zero_after_feature_refresh")
            warnings.extend(feature_result.warnings)
            blocked.extend(feature_result.blocked_reasons)

    status = "CANONICAL_NORMALIZED_READY" if not blocked else "CANONICAL_NORMALIZED_REBUILD_FAILED"
    result = CanonicalRebuildResult(
        status=status,
        run_id=run_id,
        dry_run=dry_run,
        execute=execute,
        raw_root=str(raw_root),
        supplemental_raw_table=str(supplemental_path or ""),
        target_data_until=target_data_until,
        normalized_output_path=str(output_path),
        manifest_path=str(manifest_path),
        markdown_report_path=str(md_path),
        json_report_path=str(json_path),
        row_count=int(rebuild_stats["row_count"]),
        min_date=str(rebuild_stats["min_date"]),
        max_date=str(rebuild_stats["max_date"]),
        code_count=int(rebuild_stats["code_count"]),
        raw_response_file_count=int(raw_stats["file_count"]),
        raw_response_min_date=str(raw_stats["min_date"]),
        raw_response_max_date=str(raw_stats["max_date"]),
        supplemental_row_count=int(supplemental_stats["row_count"]),
        supplemental_min_date=str(supplemental_stats["min_date"]),
        supplemental_max_date=str(supplemental_stats["max_date"]),
        duplicate_date_code_count=int(rebuild_stats["duplicate_date_code_count"]),
        duplicate_rows_skipped=int(rebuild_stats["duplicate_rows_skipped"]),
        future_rows_excluded=int(rebuild_stats["future_rows_excluded"]),
        abnormal_rows_excluded=int(rebuild_stats["abnormal_rows_excluded"]),
        normalization_errors=int(rebuild_stats["normalization_errors"]),
        required_columns_status=required_status,
        duplicate_check_status=duplicate_status,
        abnormal_price_check_status=abnormal_status,
        future_row_check_status=future_status,
        readiness_status=readiness_status,
        readiness_decision_for=target_data_until,
        lookback_ready=lookback_ready,
        lookback_business_day_count=lookback_days,
        config_updated=config_updated,
        config_before=config_before,
        config_after=config_after,
        feature_refresh_status=feature_refresh_status,
        candidate_eligible_rows=candidate_eligible_rows,
        opportunity_non_null_feature_rows=opportunity_non_null_rows,
        warnings=tuple(dict.fromkeys(warnings)),
        blocked_reasons=tuple(dict.fromkeys(blocked)),
    )
    _write_manifest(result=result, manifest_path=manifest_path, created_at=created_at)
    _write_reports(result=result, markdown_path=md_path, json_path=json_path, created_at=created_at)
    return result


def _write_normalized_parquet(
    *,
    raw_root: Path,
    supplemental_raw_table: Path | None,
    target_data_until: str,
    output_path: Path,
) -> dict[str, Any]:
    supplemental_dates = _supplemental_dates(supplemental_raw_table, target_data_until=target_data_until)
    writer: pq.ParquetWriter | None = None
    seen_keys: set[tuple[str, str]] = set()
    dates: set[str] = set()
    codes: set[str] = set()
    columns = set(OUTPUT_COLUMNS)
    stats = {
        "row_count": 0,
        "min_date": "",
        "max_date": "",
        "code_count": 0,
        "duplicate_date_code_count": 0,
        "duplicate_rows_skipped": 0,
        "future_rows_excluded": 0,
        "abnormal_rows_excluded": 0,
        "normalization_errors": 0,
        "columns": list(OUTPUT_COLUMNS),
        "available_dates": [],
        "warnings": [],
        "blocked_reasons": [],
    }

    def write_rows(rows: list[dict[str, Any]]) -> None:
        nonlocal writer
        if not rows:
            return
        frame = pd.DataFrame(rows, columns=list(OUTPUT_COLUMNS))
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(output_path, table.schema)
        writer.write_table(table)

    try:
        for path in sorted(raw_root.glob("*.json")):
            batch_records = []
            for record in _read_response_records(path):
                date = str(record.get("Date") or record.get("target_date") or "")
                if not date:
                    continue
                if date > target_data_until:
                    stats["future_rows_excluded"] += 1
                    continue
                if date in supplemental_dates:
                    continue
                batch_records.append(record)
            written, batch_stats = _normalize_batch(batch_records, seen_keys=seen_keys, target_data_until=target_data_until)
            write_rows(written)
            _merge_write_stats(stats, batch_stats, dates=dates, codes=codes)

        if supplemental_raw_table and supplemental_raw_table.exists():
            supplement = pd.read_parquet(supplemental_raw_table)
            supplement_records = supplement.to_dict("records")
            written, batch_stats = _normalize_batch(supplement_records, seen_keys=seen_keys, target_data_until=target_data_until)
            write_rows(written)
            _merge_write_stats(stats, batch_stats, dates=dates, codes=codes)
    finally:
        if writer is not None:
            writer.close()

    if stats["row_count"] == 0:
        stats["blocked_reasons"].append("normalized_output_row_count_zero")
    stats["min_date"] = min(dates) if dates else ""
    stats["max_date"] = max(dates) if dates else ""
    stats["code_count"] = len(codes)
    stats["columns"] = sorted(columns)
    stats["available_dates"] = sorted(dates)
    return stats


def _normalize_batch(
    records: list[dict[str, Any]],
    *,
    seen_keys: set[tuple[str, str]],
    target_data_until: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized, report = normalize_daily_quotes(records)
    output: list[dict[str, Any]] = []
    stats = {
        "row_count": 0,
        "duplicate_date_code_count": 0,
        "duplicate_rows_skipped": 0,
        "future_rows_excluded": 0,
        "abnormal_rows_excluded": 0,
        "normalization_errors": report.error_count,
        "dates": set(),
        "codes": set(),
        "warnings": [],
        "blocked_reasons": [],
    }
    for row in normalized:
        phase9_row = _phase9_row(row)
        date = str(phase9_row["date"])
        code = str(phase9_row["code"])
        if date > target_data_until:
            stats["future_rows_excluded"] += 1
            continue
        key = (date, code)
        if key in seen_keys:
            stats["duplicate_rows_skipped"] += 1
            continue
        if _is_abnormal_price_row(phase9_row):
            stats["abnormal_rows_excluded"] += 1
            continue
        seen_keys.add(key)
        output.append(phase9_row)
        stats["row_count"] += 1
        stats["dates"].add(date)
        stats["codes"].add(code)
    return output, stats


def _phase9_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": row.get("Date"),
        "code": row.get("Code") or row.get("code"),
        "open": row.get("Open"),
        "high": row.get("High"),
        "low": row.get("Low"),
        "close": row.get("Close"),
        "volume": row.get("Volume"),
        "Date": row.get("Date"),
        "Code": row.get("Code") or row.get("code"),
        "Open": row.get("Open"),
        "High": row.get("High"),
        "Low": row.get("Low"),
        "Close": row.get("Close"),
        "Volume": row.get("Volume"),
        "PriceSource": row.get("PriceSource"),
        "SchemaVersion": row.get("SchemaVersion"),
        "source_endpoint": row.get("source_endpoint"),
        "target_date": row.get("target_date") or row.get("Date"),
        "business_key": row.get("business_key") or row.get("Code") or row.get("code"),
        "endpoint": row.get("endpoint"),
        "source": "jquants",
    }


def _merge_write_stats(target: dict[str, Any], batch: dict[str, Any], *, dates: set[str], codes: set[str]) -> None:
    for key in (
        "row_count",
        "duplicate_date_code_count",
        "duplicate_rows_skipped",
        "future_rows_excluded",
        "abnormal_rows_excluded",
        "normalization_errors",
    ):
        target[key] += int(batch[key])
    dates.update(batch["dates"])
    codes.update(batch["codes"])
    target["warnings"].extend(batch["warnings"])
    target["blocked_reasons"].extend(batch["blocked_reasons"])


def _read_response_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        nested = payload.get("payload")
        if isinstance(nested, dict) and isinstance(nested.get("data"), list):
            return [record for record in nested["data"] if isinstance(record, dict)]
        if isinstance(payload.get("data"), list):
            return [record for record in payload["data"] if isinstance(record, dict)]
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    return []


def _inspect_raw_responses(*, raw_root: Path, target_data_until: str) -> dict[str, Any]:
    dates: list[str] = []
    files = sorted(raw_root.glob("*.json")) if raw_root.exists() else []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            date = str(payload.get("date") or payload.get("target_date") or "")
            if date and date <= target_data_until:
                dates.append(date)
    return {
        "file_count": len(files),
        "min_date": min(dates) if dates else "",
        "max_date": max(dates) if dates else "",
    }


def _inspect_supplemental_raw_table(path: Path | None, *, target_data_until: str) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"row_count": 0, "min_date": "", "max_date": ""}
    frame = pd.read_parquet(path, columns=None)
    if frame.empty:
        return {"row_count": 0, "min_date": "", "max_date": ""}
    date_column = "Date" if "Date" in frame.columns else "target_date"
    dates = frame[date_column].astype(str)
    dates = dates[dates <= target_data_until]
    return {
        "row_count": int(len(frame)),
        "min_date": str(dates.min()) if not dates.empty else "",
        "max_date": str(dates.max()) if not dates.empty else "",
    }


def _supplemental_dates(path: Path | None, *, target_data_until: str) -> set[str]:
    if path is None or not path.exists():
        return set()
    frame = pd.read_parquet(path, columns=None)
    if frame.empty:
        return set()
    date_column = "Date" if "Date" in frame.columns else "target_date"
    return set(frame.loc[frame[date_column].astype(str) <= target_data_until, date_column].astype(str).tolist())


def _is_abnormal_price_row(row: dict[str, Any]) -> bool:
    try:
        prices = [float(row[column]) for column in ("open", "high", "low", "close")]
        volume = float(row["volume"])
    except (TypeError, ValueError):
        return True
    return any(price <= 0 for price in prices) or volume < 0


def _business_day_count(*, dates: Iterable[str], end_date: str, limit: int) -> int:
    visible = sorted({date for date in dates if date <= end_date})
    return len(visible[-limit:])


def _artifact_metric(feature_result: Any, ai_name: str, metric: str) -> int:
    path = ""
    for artifact in feature_result.artifacts:
        if artifact.ai_name == ai_name:
            path = artifact.artifact_path
            break
    if not path or not Path(path).is_file():
        return 0
    frame = pd.read_parquet(path)
    if metric == "eligible_rows" and "universe_eligible" in frame.columns:
        return int(frame["universe_eligible"].fillna(False).astype(bool).sum())
    if metric == "non_null_feature_rows":
        feature_columns = [column for column in frame.columns if column.startswith("feature__")]
        if not feature_columns:
            return 0
        return int(frame[feature_columns].notna().any(axis=1).sum())
    return 0


def _read_config_value(config_path: Path, key: str) -> str | None:
    if not config_path.exists():
        return None
    in_section = False
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            in_section = stripped[:-1] == "phase9_data_sources"
            continue
        if in_section and stripped.startswith(f"{key}:"):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return None if value.lower() in {"", "null", "none", "~"} else value
    return None


def _update_config_value(config_path: Path, key: str, value: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text("phase9_data_sources:\n", encoding="utf-8")
    lines = config_path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    in_section = False
    updated = False
    section_seen = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if not raw_line.startswith(" ") and stripped.endswith(":"):
            if in_section and not updated:
                output.append(f"  {key}: {value}")
                updated = True
            in_section = stripped[:-1] == "phase9_data_sources"
            section_seen = section_seen or in_section
            output.append(raw_line)
            continue
        if in_section and stripped.startswith(f"{key}:"):
            output.append(f"  {key}: {value}")
            updated = True
        else:
            output.append(raw_line)
    if not section_seen:
        output.extend(["phase9_data_sources:", f"  {key}: {value}"])
    elif in_section and not updated:
        output.append(f"  {key}: {value}")
    config_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def _write_manifest(*, result: CanonicalRebuildResult, manifest_path: Path, created_at: str) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    payload["created_at"] = created_at
    payload["source_constraints"] = {
        "allowed": ["J-Quants raw daily_quotes", "J-Quants listed_info", "J-Quants trading_calendar"],
        "prohibited_used": [],
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_reports(
    *,
    result: CanonicalRebuildResult,
    markdown_path: Path,
    json_path: Path,
    created_at: str,
) -> None:
    payload = result.to_dict()
    payload["created_at"] = created_at
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")


def _render_markdown(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Phase9-J3 Canonical Normalized Rebuild",
            "",
            f"- status: {payload['status']}",
            f"- target_data_until: {payload['target_data_until']}",
            f"- raw_source_path: `{payload['raw_root']}`",
            f"- supplemental_raw_table: `{payload['supplemental_raw_table']}`",
            f"- raw_coverage: {payload['raw_response_min_date']} to {payload['raw_response_max_date']}",
            f"- supplemental_coverage: {payload['supplemental_min_date']} to {payload['supplemental_max_date']}",
            f"- normalized_output_path: `{payload['normalized_output_path']}`",
            f"- row_count: {payload['row_count']}",
            f"- min_date: {payload['min_date']}",
            f"- max_date: {payload['max_date']}",
            f"- code_count: {payload['code_count']}",
            f"- duplicate_check_status: {payload['duplicate_check_status']}",
            f"- abnormal_price_check_status: {payload['abnormal_price_check_status']}",
            f"- future_row_check_status: {payload['future_row_check_status']}",
            f"- readiness_status: {payload['readiness_status']}",
            f"- lookback_ready: {payload['lookback_ready']}",
            f"- config_before: {payload['config_before']}",
            f"- config_after: {payload['config_after']}",
            f"- config_updated: {payload['config_updated']}",
            f"- feature_refresh_status: {payload['feature_refresh_status']}",
            f"- candidate_eligible_rows: {payload['candidate_eligible_rows']}",
            f"- opportunity_non_null_feature_rows: {payload['opportunity_non_null_feature_rows']}",
            "",
            "## Blocked Reasons",
            "",
            *([f"- {reason}" for reason in payload["blocked_reasons"]] or ["- none"]),
            "",
            "## Warnings",
            "",
            *([f"- {warning}" for warning in payload["warnings"]] or ["- none"]),
            "",
            "## Safety",
            "",
            f"- jquants_only_source_used: {payload['jquants_only_source_used']}",
            f"- model_retraining_executed: {payload['model_retraining_executed']}",
            f"- inference_executed: {payload['inference_executed']}",
            f"- order_plan_generation_executed: {payload['order_plan_generation_executed']}",
            f"- broker_order_api_called: {payload['broker_order_api_called']}",
            f"- open_d_started: {payload['open_d_started']}",
            f"- unlock_trade_called: {payload['unlock_trade_called']}",
            f"- paper_ledger_fill_executed: {payload['paper_ledger_fill_executed']}",
            f"- virtual_fill_executed: {payload['virtual_fill_executed']}",
            "",
            "## Next Action",
            "",
            "- Phase9-K model manifest / retrain eligibility review.",
            "",
        ]
    )


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild Phase9 canonical normalized daily_quotes from J-Quants raw data.")
    parser.add_argument("--raw-root", default=str(DEFAULT_RAW_ROOT))
    parser.add_argument("--target-data-until", required=True)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--config-path", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--supplemental-raw-table", default=str(DEFAULT_SUPPLEMENTAL_RAW_TABLE))
    parser.add_argument("--listed-info-path", default=str(DEFAULT_LISTED_INFO_PATH))
    parser.add_argument("--markdown-report-path", default=str(DEFAULT_MD_REPORT))
    parser.add_argument("--json-report-path", default=str(DEFAULT_JSON_REPORT))
    parser.add_argument("--feature-output-root", default=str(DEFAULT_FEATURE_OUTPUT_ROOT))
    parser.add_argument("--feature-manifest-root", default=str(DEFAULT_FEATURE_MANIFEST_ROOT))
    parser.add_argument("--feature-markdown-report-path", default=str(DEFAULT_FEATURE_MD_REPORT))
    parser.add_argument("--feature-json-report-path", default=str(DEFAULT_FEATURE_JSON_REPORT))
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true", default=False)
    parser.add_argument("--skip-feature-refresh", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    execute = bool(args.execute)
    dry_run = not execute
    result = rebuild_canonical_normalized_daily_quotes(
        raw_root=args.raw_root,
        target_data_until=args.target_data_until,
        dry_run=dry_run,
        execute=execute,
        output_root=args.output_root,
        config_path=args.config_path,
        supplemental_raw_table=args.supplemental_raw_table,
        listed_info_path=args.listed_info_path,
        markdown_report_path=args.markdown_report_path,
        json_report_path=args.json_report_path,
        feature_output_root=args.feature_output_root,
        feature_manifest_root=args.feature_manifest_root,
        feature_markdown_report_path=args.feature_markdown_report_path,
        feature_json_report_path=args.feature_json_report_path,
        run_feature_refresh_after=not args.skip_feature_refresh,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if result.status in {"CANONICAL_NORMALIZED_READY", "CANONICAL_NORMALIZED_REBUILD_DRY_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
