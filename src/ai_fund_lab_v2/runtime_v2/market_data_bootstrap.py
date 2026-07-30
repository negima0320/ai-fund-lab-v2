from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BOOTSTRAP_SCHEMA_VERSION = "phase20_bb_runtime_market_data_bootstrap.v1"
WARMUP_SCHEMA_VERSION = "phase20_bb_runtime_market_data_warmup_sufficiency.v1"
DEFAULT_SOURCE_PATH = Path(".runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet")
NORMALIZED_RELATIVE_PATH = Path("operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet")
RAW_RELATIVE_PATH = Path("operations/jquants/raw/jquants/equities_bars_daily/data.parquet")
LISTED_RELATIVE_PATH = Path("operations/jquants/raw/jquants/listed_issues/data.parquet")
REQUIRED_NORMALIZED_COLUMNS = (
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
    "code",
    "business_key",
    "endpoint",
    "source",
)
REQUIRED_LOOKBACK_BUSINESS_DAYS = 61


@dataclass(frozen=True)
class BootstrapPaths:
    runtime_root: Path
    source_path: Path
    evidence_root: Path

    @property
    def target_path(self) -> Path:
        return self.runtime_root / NORMALIZED_RELATIVE_PATH

    @property
    def raw_path(self) -> Path:
        return self.runtime_root / RAW_RELATIVE_PATH

    @property
    def listed_path(self) -> Path:
        return self.runtime_root / LISTED_RELATIVE_PATH


def build_market_data_bootstrap_plan(
    *,
    runtime_root: Path | str,
    source_path: Path | str = DEFAULT_SOURCE_PATH,
    evidence_root: Path | str = "reports/phase20_bb_runtime_market_data_bootstrap",
    years: int = 5,
    target_start_date: str | None = None,
    target_end_date: str | None = None,
    write_evidence: bool = False,
    created_at: str | None = None,
) -> dict[str, Any]:
    paths = BootstrapPaths(Path(runtime_root), Path(source_path), Path(evidence_root))
    created_at = created_at or _utc_now()
    current = parquet_inventory(paths.target_path)
    raw = parquet_inventory(paths.raw_path)
    listed = parquet_inventory(paths.listed_path)
    source = parquet_inventory(paths.source_path)
    schema = compare_normalized_schemas(current=current, source=source)
    today = date.today().isoformat()
    target_end = target_end_date or str(current.get("latest_date") or today)
    target_start = target_start_date or _calendar_years_before(target_end, years)
    warmup = build_market_data_warmup_sufficiency(
        runtime_root=paths.runtime_root,
        target_start_date=target_start,
        target_end_date=target_end,
        maximum_required_warmup_business_days=REQUIRED_LOOKBACK_BUSINESS_DAYS,
    )
    reuse_status = _source_reuse_status(source=source, schema=schema, target_start_date=target_start, target_end_date=target_end)
    current_latest = str(current.get("latest_date") or "")
    source_latest = str(source.get("latest_date") or "")
    source_earliest = str(source.get("earliest_date") or "")
    missing_periods = _missing_periods(
        required_start=str(warmup.get("required_source_start_date") or target_start),
        target_end=target_end,
        current_earliest=str(current.get("earliest_date") or ""),
        current_latest=current_latest,
        source_earliest=source_earliest,
        source_latest=source_latest,
    )
    status = "PASS" if reuse_status == "REUSABLE" else "BLOCK"
    final_judgment = "BOOTSTRAP_PLAN_READY" if status == "PASS" else "BOOTSTRAP_SOURCE_REVIEW_REQUIRED"
    plan = {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "operation": "plan",
        "status": status,
        "final_judgment": final_judgment,
        "created_at": created_at,
        "read_only": True,
        "runtime_root": str(paths.runtime_root),
        "source_path": str(paths.source_path),
        "target_path": str(paths.target_path),
        "years": int(years),
        "target_start_date": target_start,
        "target_end_date": target_end,
        "maximum_required_warmup_business_days": REQUIRED_LOOKBACK_BUSINESS_DAYS,
        "current_runtime_ohlcv_inventory": current,
        "current_runtime_raw_ohlcv_inventory": raw,
        "current_runtime_listed_issues_inventory": listed,
        "existing_five_year_source_inventory": source,
        "schema_comparison": schema,
        "source_reuse_status": reuse_status,
        "missing_periods": missing_periods,
        "warmup_sufficiency": warmup,
        "merge_contract": bootstrap_contract(paths=paths),
        "blocked_reasons": _plan_blocked_reasons(reuse_status=reuse_status, source=source, schema=schema, warmup=warmup),
        "warnings": _plan_warnings(source=source, current=current),
        "jquants_api_fetch_executed": False,
        "runtime_market_data_mutated": False,
        "broker_access": "NOT_PERFORMED",
    }
    if write_evidence:
        write_bootstrap_evidence(plan, paths=paths)
    return plan


def execute_market_data_bootstrap(
    *,
    runtime_root: Path | str,
    source_path: Path | str = DEFAULT_SOURCE_PATH,
    evidence_root: Path | str = "reports/phase20_bb_runtime_market_data_bootstrap",
    years: int = 5,
    target_start_date: str | None = None,
    target_end_date: str | None = None,
    confirm: bool = False,
    explicit_mutation_confirm: bool = False,
    write_evidence: bool = False,
    created_at: str | None = None,
) -> dict[str, Any]:
    plan = build_market_data_bootstrap_plan(
        runtime_root=runtime_root,
        source_path=source_path,
        evidence_root=evidence_root,
        years=years,
        target_start_date=target_start_date,
        target_end_date=target_end_date,
        write_evidence=False,
        created_at=created_at,
    )
    if not (confirm and explicit_mutation_confirm):
        result = {
            **plan,
            "operation": "run",
            "status": "BLOCK",
            "final_judgment": "BOOTSTRAP_CONFIRMATION_REQUIRED",
            "blocked_reasons": list(dict.fromkeys([*plan.get("blocked_reasons", []), "confirm_and_explicit_market_data_mutation_flag_required"])),
            "runtime_market_data_mutated": False,
        }
        if write_evidence:
            write_bootstrap_evidence(result, paths=BootstrapPaths(Path(runtime_root), Path(source_path), Path(evidence_root)))
        return result
    if plan["status"] != "PASS":
        result = {
            **plan,
            "operation": "run",
            "status": "BLOCK",
            "final_judgment": "BOOTSTRAP_SOURCE_NOT_ACCEPTED",
            "runtime_market_data_mutated": False,
        }
        if write_evidence:
            write_bootstrap_evidence(result, paths=BootstrapPaths(Path(runtime_root), Path(source_path), Path(evidence_root)))
        return result
    paths = BootstrapPaths(Path(runtime_root), Path(source_path), Path(evidence_root))
    result = _commit_bootstrap_merge(paths=paths, plan=plan)
    if write_evidence:
        write_bootstrap_evidence(result, paths=paths)
    return result


def build_market_data_warmup_sufficiency(
    *,
    runtime_root: Path | str,
    target_start_date: str,
    target_end_date: str | None = None,
    maximum_required_warmup_business_days: int = REQUIRED_LOOKBACK_BUSINESS_DAYS,
    source_path: Path | str | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root)
    path = Path(source_path) if source_path is not None else root / NORMALIZED_RELATIVE_PATH
    inventory = parquet_inventory(path)
    source_dates = [str(item) for item in inventory.get("unique_dates", [])]
    source_date_set = set(source_dates)
    required_start = required_source_start_date(
        target_start_date=target_start_date,
        available_dates=source_dates,
        maximum_required_warmup_business_days=_positive_warmup_days(maximum_required_warmup_business_days),
    )
    actual_earliest = str(inventory.get("earliest_date") or "")
    actual_latest = str(inventory.get("latest_date") or "")
    required_business_dates = []
    available_business_dates = []
    if required_start and actual_earliest:
        required_business_dates = _required_business_date_window(
            target_start_date=target_start_date,
            available_dates=source_dates,
            maximum_required_warmup_business_days=_positive_warmup_days(maximum_required_warmup_business_days),
        )
        available_business_dates = [day for day in required_business_dates if day in source_date_set]
        expected_count = int(maximum_required_warmup_business_days)
        missing_count = max(0, expected_count - len(available_business_dates))
    else:
        missing_count = int(maximum_required_warmup_business_days)
    target_date_available = target_start_date in source_date_set
    sufficient = bool(
        actual_earliest
        and actual_latest
        and required_start
        and missing_count == 0
        and target_date_available
    )
    if sufficient:
        reason = "HISTORICAL_SOURCE_WARMUP_SUFFICIENT"
    elif not source_dates:
        reason = "SOURCE_ROWS_EMPTY"
    elif not target_date_available:
        reason = "QUOTE_TARGET_DATE_MISSING"
    else:
        reason = "HISTORICAL_SOURCE_WARMUP_INSUFFICIENT"
    return {
        "schema_version": WARMUP_SCHEMA_VERSION,
        "component_id": "runtime_market_data_warmup_sufficiency",
        "target_start_date": target_start_date,
        "target_end_date": target_end_date or target_start_date,
        "maximum_required_warmup_business_days": int(maximum_required_warmup_business_days),
        "required_source_start_date": required_start,
        "actual_source_earliest_date": actual_earliest,
        "actual_source_latest_date": actual_latest,
        "source_path": str(path),
        "missing_warmup_business_days": int(missing_count),
        "required_business_dates_count": len(required_business_dates),
        "available_business_dates_count": len(available_business_dates),
        "target_date_available": target_date_available,
        "target_date_missing": not target_date_available,
        "warmup_sufficiency_judgment": "PASS" if sufficient else "BLOCK",
        "reason": reason,
        "affected_components": [
            "Candidate Feature",
            "Opportunity Feature",
            "Position Management technical features",
            "Safety lookback-dependent checks",
        ],
        "lookback_evidence": {
            "candidate_feature_builder": "src/ai_fund_lab_v2/paper_trading/feature_refresh.py:_build_formal_candidate_rows uses len(visible) < 61 and close[-61]",
            "opportunity_feature_builder": "src/ai_fund_lab_v2/paper_trading/feature_refresh.py:_build_opportunity_feature_input consumes candidate 60d features and market/sector 20d features",
            "pm_features": "src/ai_fund_lab_v2/paper_trading/feature_refresh.py position features consume candidate technical columns up to 20d",
        },
    }


def _positive_warmup_days(value: int) -> int:
    return max(1, int(value))


def _required_business_date_window(
    *,
    target_start_date: str,
    available_dates: list[str],
    maximum_required_warmup_business_days: int,
) -> list[str]:
    target = str(target_start_date)
    dates = sorted(day for day in available_dates if day <= target)
    if len(dates) >= maximum_required_warmup_business_days:
        return dates[-maximum_required_warmup_business_days:]
    fallback_start = required_source_start_date(
        target_start_date=target,
        available_dates=available_dates,
        maximum_required_warmup_business_days=maximum_required_warmup_business_days,
    )
    start = date.fromisoformat(fallback_start)
    end = date.fromisoformat(target)
    days: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days[-maximum_required_warmup_business_days:]


def required_source_start_date(
    *,
    target_start_date: str,
    available_dates: list[str],
    maximum_required_warmup_business_days: int = REQUIRED_LOOKBACK_BUSINESS_DAYS,
) -> str:
    target = str(target_start_date)
    dates = sorted(day for day in available_dates if day <= target)
    if len(dates) >= maximum_required_warmup_business_days:
        return dates[-maximum_required_warmup_business_days]
    fallback = date.fromisoformat(target)
    days_needed = int(maximum_required_warmup_business_days)
    current = fallback
    seen = 0
    while seen < days_needed:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            seen += 1
    return current.isoformat()


def parquet_inventory(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    item: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "row_count": 0,
        "column_count": 0,
        "columns": [],
        "date_column": "",
        "code_column": "",
        "earliest_date": "",
        "latest_date": "",
        "unique_business_days": 0,
        "symbol_count": 0,
        "duplicate_key_count": 0,
        "schema_hash": "",
        "content_hash": _sha256_file(path),
        "jquants_lineage_status": "MISSING",
        "price_source_values": [],
        "future_or_training_columns_detected": [],
        "status": "MISSING",
    }
    if not path.is_file():
        return item
    try:
        import pandas as pd

        frame = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        item.update({"status": "UNREADABLE", "error": type(exc).__name__})
        return item
    columns = [str(column) for column in frame.columns]
    date_column = next((column for column in ("Date", "target_date", "date", "business_date", "as_of_date") if column in frame.columns), "")
    code_column = next((column for column in ("Code", "code", "LocalCode", "symbol") if column in frame.columns), "")
    dates = sorted({_extract_date(value) for value in frame[date_column].dropna().astype(str)}) if date_column else []
    duplicate_count = int(frame.duplicated([date_column, code_column]).sum()) if date_column and code_column else 0
    lineage_status = "PASS" if _jquants_lineage_pass(frame) else "REVIEW_REQUIRED"
    suspicious = [
        column
        for column in columns
        if column.lower() in {"label", "target", "future_return", "forward_return"} or column.lower().startswith(("label_", "future_", "target_return"))
    ]
    item.update(
        {
            "row_count": int(len(frame)),
            "column_count": len(columns),
            "columns": columns,
            "date_column": date_column,
            "code_column": code_column,
            "earliest_date": dates[0] if dates else "",
            "latest_date": dates[-1] if dates else "",
            "unique_dates": dates,
            "unique_business_days": len(dates),
            "symbol_count": int(frame[code_column].astype(str).nunique()) if code_column else 0,
            "duplicate_key_count": duplicate_count,
            "schema_hash": hashlib.sha256(json.dumps(columns, ensure_ascii=True).encode("utf-8")).hexdigest(),
            "jquants_lineage_status": lineage_status,
            "price_source_values": sorted(str(value) for value in frame["PriceSource"].dropna().astype(str).unique()) if "PriceSource" in frame.columns else [],
            "future_or_training_columns_detected": suspicious,
            "status": "PASS" if duplicate_count == 0 and date_column and code_column else "REVIEW_REQUIRED",
        }
    )
    return item


def compare_normalized_schemas(*, current: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    current_cols = [str(column) for column in current.get("columns", [])]
    source_cols = [str(column) for column in source.get("columns", [])]
    missing = [column for column in REQUIRED_NORMALIZED_COLUMNS if column not in source_cols]
    extra = [column for column in source_cols if column not in REQUIRED_NORMALIZED_COLUMNS]
    return {
        "required_columns": list(REQUIRED_NORMALIZED_COLUMNS),
        "current_columns": current_cols,
        "source_columns": source_cols,
        "missing_required_source_columns": missing,
        "extra_source_columns": extra,
        "current_schema_hash": current.get("schema_hash", ""),
        "source_schema_hash": source.get("schema_hash", ""),
        "schema_match": current_cols == source_cols if current_cols and source_cols else False,
        "runtime_merge_compatible": not missing,
        "status": "PASS" if not missing else "BLOCK",
    }


def bootstrap_contract(*, paths: BootstrapPaths) -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "authority": "COMMON_RUNTIME_MARKET_DATA_SOT",
        "target_root": str(paths.runtime_root / "operations/jquants"),
        "target_normalized_ohlcv": str(paths.target_path),
        "source_requirement": "J-Quants-derived normalized OHLCV with runtime schema, no training labels, duplicate-free Date/Code keys",
        "daily_refresh_relationship": "bootstrap is explicit initial/history construction; daily market_refresh remains incremental merge",
        "merge_key": ["Date", "Code"],
        "duplicate_policy": "source rows first, existing runtime rows last; existing runtime value wins on duplicate Date/Code",
        "atomicity": "write merged parquet to temporary path, validate schema/coverage/duplicates, then os.replace target",
        "idempotency": "same source and target produce no duplicate rows and stable Date/Code content",
        "fail_closed_conditions": [
            "source_missing",
            "source_schema_incompatible",
            "source_jquants_lineage_not_confirmed",
            "source_duplicate_keys",
            "source_coverage_insufficient",
            "warmup_insufficient",
            "existing_latest_date_would_be_lost",
            "merged_duplicate_keys",
            "merged_schema_invalid",
        ],
        "forbidden": [
            "training_dataset_direct_runtime_input",
            "benchmark_fetch",
            "broker_access",
            "runtime_state_mutation",
            "historical_smoke_execution",
        ],
    }


def write_bootstrap_evidence(payload: dict[str, Any], *, paths: BootstrapPaths) -> None:
    root = paths.evidence_root
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / "current_runtime_ohlcv_inventory.json", payload.get("current_runtime_ohlcv_inventory", {}))
    _write_json(root / "existing_five_year_source_inventory.json", payload.get("existing_five_year_source_inventory", {}))
    _write_json(root / "schema_comparison.json", payload.get("schema_comparison", {}))
    _write_json(root / "bootstrap_plan.json", payload)
    _write_json(root / "bootstrap_contract.json", payload.get("merge_contract", bootstrap_contract(paths=paths)))
    _write_json(root / "warmup_requirement_inventory.json", payload.get("warmup_sufficiency", {}))
    _write_json(
        root / "system_status_warmup_guard_test.json",
        build_market_data_warmup_sufficiency(
            runtime_root=paths.runtime_root,
            target_start_date="2026-03-24",
            target_end_date="2026-03-24",
        ),
    )
    _write_json(root / "fresh_run_market_data_preservation_audit.json", fresh_run_market_data_preservation_audit())
    _write_json(root / "historical_asof_contract_audit.json", historical_asof_contract_audit(paths=paths))
    existing = _read_json_optional(root / "test_summary.json")
    if not existing:
        _write_json(
            root / "test_summary.json",
            {
                "schema_version": BOOTSTRAP_SCHEMA_VERSION,
                "status": "PENDING_VALIDATION",
                "tests": [],
                "long_running_historical_executed": False,
                "broker_access": "NOT_PERFORMED",
            },
        )


def fresh_run_market_data_preservation_audit() -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "status": "PASS",
        "evidence": [
            {
                "path": "src/ai_fund_lab_v2/runtime_v2/historical_support/isolated_root.py",
                "finding": "Historical isolated root symlinks shared operations/jquants instead of copying or deleting it.",
            },
            {
                "path": "src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py",
                "finding": "Resettable paths include operations/feature_refresh and operations/market_refresh, not operations/jquants raw/raw_normalized authority.",
            },
        ],
        "shared_market_data_deleted_by_fresh_run": False,
        "runtime_market_data_paths_preserved": [
            str(RAW_RELATIVE_PATH),
            str(NORMALIZED_RELATIVE_PATH),
            str(LISTED_RELATIVE_PATH),
        ],
    }


def historical_asof_contract_audit(*, paths: BootstrapPaths) -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "status": "PASS",
        "asof_authority": "src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py",
        "normalized_ohlcv_source": str(paths.target_path),
        "consumer_cutoff": "Historical as-of view resolves Date <= business_date for consumer inputs.",
        "future_leakage_policy": "Bootstrap may hold future physical rows; historical consumers must use as-of cutoff.",
        "inspection_target_date": "2026-03-24",
    }


def _commit_bootstrap_merge(*, paths: BootstrapPaths, plan: dict[str, Any]) -> dict[str, Any]:
    import pandas as pd

    source = pd.read_parquet(paths.source_path)
    current = pd.read_parquet(paths.target_path) if paths.target_path.is_file() else pd.DataFrame(columns=list(REQUIRED_NORMALIZED_COLUMNS))
    merged = pd.concat([source, current], ignore_index=True)
    merged["Date"] = merged["Date"].astype(str)
    merged["Code"] = merged["Code"].astype(str)
    merged = merged.drop_duplicates(["Date", "Code"], keep="last").sort_values(["Date", "Code"]).reset_index(drop=True)
    tmp = paths.target_path.with_name(f"{paths.target_path.name}.phase20_bb_tmp")
    merged.to_parquet(tmp, index=False)
    merged_inventory = parquet_inventory(tmp)
    blocked = []
    if merged_inventory.get("duplicate_key_count"):
        blocked.append("merged_duplicate_keys")
    if compare_normalized_schemas(current=plan["current_runtime_ohlcv_inventory"], source=merged_inventory)["status"] != "PASS":
        blocked.append("merged_schema_invalid")
    if str(merged_inventory.get("latest_date") or "") < str(plan["current_runtime_ohlcv_inventory"].get("latest_date") or ""):
        blocked.append("existing_latest_date_would_be_lost")
    if blocked:
        tmp.unlink(missing_ok=True)
        return {
            **plan,
            "operation": "run",
            "status": "BLOCK",
            "final_judgment": "BOOTSTRAP_COMMIT_VALIDATION_FAILED",
            "blocked_reasons": list(dict.fromkeys([*plan.get("blocked_reasons", []), *blocked])),
            "runtime_market_data_mutated": False,
            "merged_inventory": merged_inventory,
        }
    paths.target_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = paths.target_path.with_name(f"{paths.target_path.name}.backup_phase20_bb_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    if paths.target_path.is_file():
        shutil.copy2(paths.target_path, backup_path)
    os.replace(tmp, paths.target_path)
    final_inventory = parquet_inventory(paths.target_path)
    return {
        **plan,
        "operation": "run",
        "status": "PASS",
        "final_judgment": "BOOTSTRAP_COMMIT_COMPLETE",
        "runtime_market_data_mutated": True,
        "backup_path": str(backup_path) if backup_path.exists() else "",
        "merged_inventory": final_inventory,
    }


def _source_reuse_status(*, source: dict[str, Any], schema: dict[str, Any], target_start_date: str, target_end_date: str) -> str:
    if not source.get("exists"):
        return "SOURCE_MISSING"
    if schema.get("status") != "PASS":
        return "SCHEMA_INCOMPATIBLE"
    if source.get("duplicate_key_count"):
        return "DUPLICATE_KEYS"
    if source.get("jquants_lineage_status") != "PASS":
        return "LINEAGE_REVIEW_REQUIRED"
    if source.get("future_or_training_columns_detected"):
        return "TRAINING_COLUMNS_DETECTED"
    if str(source.get("earliest_date") or "") > target_start_date or str(source.get("latest_date") or "") < target_end_date:
        return "COVERAGE_INSUFFICIENT"
    return "REUSABLE"


def _plan_blocked_reasons(*, reuse_status: str, source: dict[str, Any], schema: dict[str, Any], warmup: dict[str, Any]) -> list[str]:
    reasons = []
    if reuse_status != "REUSABLE":
        reasons.append(reuse_status.lower())
    if schema.get("status") != "PASS":
        reasons.append("source_schema_incompatible")
    if warmup.get("warmup_sufficiency_judgment") != "PASS":
        reasons.append("current_runtime_warmup_insufficient")
    if source.get("row_count", 0) and int(source.get("row_count", 0)) < 1_000_000:
        reasons.append("source_not_five_year_scale")
    return list(dict.fromkeys(reasons))


def _plan_warnings(*, source: dict[str, Any], current: dict[str, Any]) -> list[str]:
    warnings = []
    if source.get("exists") and source.get("latest_date") and current.get("latest_date") and str(source["latest_date"]) < str(current["latest_date"]):
        warnings.append("source_latest_before_current_latest_existing_runtime_rows_must_win")
    return warnings


def _missing_periods(*, required_start: str, target_end: str, current_earliest: str, current_latest: str, source_earliest: str, source_latest: str) -> dict[str, Any]:
    return {
        "required_start": required_start,
        "target_end": target_end,
        "current_runtime_gap": not (current_earliest and current_latest and current_earliest <= required_start and current_latest >= target_end),
        "source_gap": not (source_earliest and source_latest and source_earliest <= required_start and source_latest >= target_end),
        "current_runtime_earliest": current_earliest,
        "current_runtime_latest": current_latest,
        "source_earliest": source_earliest,
        "source_latest": source_latest,
    }


def _jquants_lineage_pass(frame: Any) -> bool:
    if "source" in frame.columns and set(frame["source"].dropna().astype(str).unique()) - {"jquants"}:
        return False
    if "endpoint" in frame.columns:
        endpoints = set(frame["endpoint"].dropna().astype(str).unique())
        if not endpoints.issubset({"daily_quotes_normalized", "/v2/equities/bars/daily"}):
            return False
    if "source_endpoint" in frame.columns and not set(frame["source_endpoint"].dropna().astype(str).unique()).issubset({"/v2/equities/bars/daily"}):
        return False
    return True


def _calendar_years_before(value: str, years: int) -> str:
    end = date.fromisoformat(value)
    try:
        return end.replace(year=end.year - int(years)).isoformat()
    except ValueError:
        return end.replace(month=2, day=28, year=end.year - int(years)).isoformat()


def _extract_date(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) >= 10:
        return text[:10]
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json_optional(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
