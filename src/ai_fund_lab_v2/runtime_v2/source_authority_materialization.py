from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
    rebuild_snapshot_index,
    resolve_listed_issues_snapshot,
    write_listed_issues_snapshot,
)
from ai_fund_lab_v2.runtime_v2.historical_support.trading_calendar_snapshots import (
    write_calendar_authority,
)
from ai_fund_lab_v2.runtime_v2.market_data_bootstrap import parquet_inventory

MATERIALIZATION_SCHEMA_VERSION = "phase29_l4_b_source_authority_materialization_v1"

LISTED_RELATIVE_PATH = Path("operations/jquants/raw/jquants/listed_issues/data.parquet")
LISTED_SNAPSHOT_RELATIVE_ROOT = Path("operations/jquants/historical_snapshots/listed_issues")
CALENDAR_OPERATIONS_RELATIVE_PATH = Path("operations/jquants/raw/jquants/trading_calendar/data.parquet")
CALENDAR_HISTORICAL_RELATIVE_ROOT = Path("operations/jquants/historical_snapshots/trading_calendar")
RAW_OHLCV_RELATIVE_PATH = Path("operations/jquants/raw/jquants/equities_bars_daily/data.parquet")
NORMALIZED_OHLCV_RELATIVE_PATH = Path("operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet")
REQUIRED_RAW_OHLCV_COLUMNS = ("Date", "Code", "O", "H", "L", "C", "Vo")


def materialize_raw_ohlcv_authority(
    *,
    runtime_root: Path | str,
    staging_path: Path | str,
    requested_start_date: str,
    requested_end_date: str,
    confirm: bool = False,
) -> dict[str, Any]:
    import pandas as pd

    root = Path(runtime_root)
    source = Path(staging_path)
    payload = _base_payload("raw_ohlcv", root=root, source=source, confirm=confirm)
    payload["target_path"] = str(root / RAW_OHLCV_RELATIVE_PATH)
    if not confirm:
        payload.update({"status": "DRY_RUN", "reason": "confirm_false_no_runtime_mutation"})
        return payload
    if not source.is_file():
        payload.update({"status": "HALT", "reason": "raw_ohlcv_staging_source_missing"})
        return payload

    staging_validation = _raw_ohlcv_staging_validation(source)
    if staging_validation["status"] != "PASS":
        payload.update(
            {
                "status": "HALT",
                "reason": staging_validation["reason"],
                "staging_validation": staging_validation,
                "runtime_market_data_mutated": False,
            }
        )
        return payload

    frame = pd.read_parquet(source)
    source_inventory = parquet_inventory(source)
    blockers = _raw_ohlcv_frame_blockers(
        frame,
        source_inventory=source_inventory,
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
    )
    if blockers:
        payload.update(
            {
                "status": "HALT",
                "reason": blockers[0],
                "blocked_reasons": blockers,
                "source_inventory": source_inventory,
                "staging_validation": staging_validation,
                "runtime_market_data_mutated": False,
            }
        )
        return payload

    target_path = root / RAW_OHLCV_RELATIVE_PATH
    target_before = parquet_inventory(target_path)
    _atomic_copy_file(source, target_path)
    target_after = parquet_inventory(target_path)
    verification = _raw_ohlcv_post_materialization_verification(
        source_inventory=source_inventory,
        target_inventory=target_after,
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
    )
    if verification["status"] != "PASS":
        payload.update(
            {
                "status": "HALT",
                "reason": verification["reason"],
                "source_inventory": source_inventory,
                "target_inventory_before": target_before,
                "target_inventory_after": target_after,
                "post_materialization_verification": verification,
                "staging_validation": staging_validation,
                "runtime_market_data_mutated": True,
            }
        )
        return payload
    payload.update(
        {
            "status": "PASS",
            "reason": "raw_ohlcv_authority_materialized",
            "source_inventory": source_inventory,
            "target_inventory_before": target_before,
            "target_inventory_after": target_after,
            "row_count": int(target_after.get("row_count") or 0),
            "min_date": str(target_after.get("earliest_date") or ""),
            "max_date": str(target_after.get("latest_date") or ""),
            "duplicate_key_count": int(target_after.get("duplicate_key_count") or 0),
            "content_hash": str(target_after.get("content_hash") or ""),
            "staging_validation": staging_validation,
            "post_materialization_verification": verification,
            "operation": "validated_acquisition_raw_ohlcv_to_canonical_operations_materialization",
            "runtime_market_data_mutated": True,
            "reverse_generated_from_normalized": False,
        }
    )
    return payload


def materialize_listed_issues_authority(
    *,
    runtime_root: Path | str,
    staging_path: Path | str,
    requested_start_date: str,
    requested_end_date: str,
    confirm: bool = False,
) -> dict[str, Any]:
    import pandas as pd

    root = Path(runtime_root)
    source = Path(staging_path)
    payload = _base_payload("listed_issues", root=root, source=source, confirm=confirm)
    if not confirm:
        payload.update({"status": "DRY_RUN", "reason": "confirm_false_no_runtime_mutation"})
        return payload
    if not source.is_file():
        payload.update({"status": "HALT", "reason": "listed_staging_source_missing"})
        return payload
    frame = pd.read_parquet(source)
    blocked = _listed_frame_blockers(frame, requested_start_date=requested_start_date, requested_end_date=requested_end_date)
    if blocked:
        payload.update({"status": "HALT", "reason": blocked[0], "blocked_reasons": blocked})
        return payload

    source_frame = frame.copy()
    source_frame["Date"] = source_frame["Date"].astype(str)
    source_frame["Code"] = source_frame["Code"].astype(str)
    canonical = source_frame.drop_duplicates(["Date", "Code"], keep="last").sort_values(["Date", "Code"]).reset_index(drop=True)
    target_path = root / LISTED_RELATIVE_PATH
    _atomic_write_parquet(canonical, target_path)

    snapshot_root = root / LISTED_SNAPSHOT_RELATIVE_ROOT
    write_results = []
    for snapshot_date, group in canonical.groupby("Date", sort=True):
        result = write_listed_issues_snapshot(
            snapshot_root=snapshot_root,
            requested_date=str(snapshot_date),
            records=group.to_dict(orient="records"),
            fetched_at=_now_utc(),
            pagination_metadata={
                "materialization_source": str(source),
                "materialization_schema_version": MATERIALIZATION_SCHEMA_VERSION,
                "source_materialization": True,
            },
            overwrite=True,
        )
        write_results.append(result.to_payload())
        if result.status != "PASS":
            payload.update({"status": "HALT", "reason": result.reason, "failed_snapshot": result.to_payload()})
            return payload
    index = rebuild_snapshot_index(snapshot_root)
    validation_dates = _listed_validation_dates(canonical, requested_start_date=requested_start_date, requested_end_date=requested_end_date)
    resolutions = [
        resolve_listed_issues_snapshot(snapshot_root=snapshot_root, business_date=day).to_payload()
        for day in validation_dates
    ]
    payload.update(
        {
            "status": "PASS" if index.get("status") == "PASS" and all(item["status"] == "PASS" for item in resolutions) else "REVIEW_REQUIRED",
            "reason": "listed_issues_authority_materialized" if index.get("status") == "PASS" else "listed_snapshot_index_not_ready",
            "target_path": str(target_path),
            "snapshot_root": str(snapshot_root),
            "row_count": int(len(canonical)),
            "unique_snapshot_dates": int(canonical["Date"].nunique()),
            "min_date": str(canonical["Date"].min()),
            "max_date": str(canonical["Date"].max()),
            "duplicate_key_count": int(canonical.duplicated(["Date", "Code"]).sum()),
            "content_hash": _sha256_file(target_path),
            "snapshot_write_count": len(write_results),
            "snapshot_index": index,
            "pit_validation": {
                "selection_policy": "latest_snapshot_not_after_business_date",
                "validation_dates": validation_dates,
                "results": resolutions,
                "future_snapshot_used": any(bool(item.get("future_snapshot_used")) for item in resolutions),
            },
            "latest_current_backfill_prohibited": True,
            "operation": "canonical_operations_materialization_and_pit_snapshot_index_rebuild",
        }
    )
    return payload


def materialize_trading_calendar_authority(
    *,
    runtime_root: Path | str,
    staging_path: Path | str,
    requested_start_date: str,
    requested_end_date: str,
    confirm: bool = False,
) -> dict[str, Any]:
    import pandas as pd

    root = Path(runtime_root)
    source = Path(staging_path)
    payload = _base_payload("trading_calendar", root=root, source=source, confirm=confirm)
    if not confirm:
        payload.update({"status": "DRY_RUN", "reason": "confirm_false_no_runtime_mutation"})
        return payload
    if not source.is_file():
        payload.update({"status": "HALT", "reason": "calendar_staging_source_missing"})
        return payload
    staging = _canonical_calendar_frame(pd.read_parquet(source), source_label="validated_acquisition_staging")
    historical_path = root / CALENDAR_HISTORICAL_RELATIVE_ROOT / "data.parquet"
    operations_path = root / CALENDAR_OPERATIONS_RELATIVE_PATH
    historical = _read_optional_calendar_frame(historical_path, source_label="historical_snapshot_base")
    operations = _read_optional_calendar_frame(operations_path, source_label="operations_current")
    merged = _merge_calendar_frames([historical, operations, staging])
    blockers = _calendar_frame_blockers(merged, requested_start_date=requested_start_date, requested_end_date=requested_end_date)
    if blockers:
        payload.update({"status": "HALT", "reason": blockers[0], "blocked_reasons": blockers})
        return payload

    records = merged.to_dict(orient="records")
    write_result = write_calendar_authority(
        calendar_root=root / CALENDAR_HISTORICAL_RELATIVE_ROOT,
        requested_from_date=requested_start_date,
        requested_to_date=requested_end_date,
        records=records,
        fetched_at=_now_utc(),
        pagination_metadata={
            "materialization_source": str(source),
            "materialization_schema_version": MATERIALIZATION_SCHEMA_VERSION,
            "source_materialization": True,
        },
        skip_verified_existing=False,
    )
    _atomic_write_parquet(merged, operations_path)
    reconciliation = reconcile_calendar_with_quotes(
        calendar_frame=merged,
        quote_path=root / NORMALIZED_OHLCV_RELATIVE_PATH,
        start_date=requested_start_date,
        end_date=requested_end_date,
    )
    business_days = sorted(
        str(value)
        for value in merged.loc[
            (merged["Date"].astype(str) >= requested_start_date)
            & (merged["Date"].astype(str) <= requested_end_date)
            & (merged["HolDiv"].astype(str).isin({"1", "1.0"})),
            "Date",
        ].dropna().unique()
    )
    status = "PASS" if write_result.get("status") == "PASS" and reconciliation["status"] == "PASS" else "REVIEW_REQUIRED"
    payload.update(
        {
            "status": status,
            "reason": "trading_calendar_authority_materialized" if status == "PASS" else "calendar_quote_reconciliation_review_required",
            "historical_calendar_root": str(root / CALENDAR_HISTORICAL_RELATIVE_ROOT),
            "operations_calendar_path": str(operations_path),
            "row_count": int(len(merged)),
            "min_date": str(merged["Date"].min()),
            "max_date": str(merged["Date"].max()),
            "business_day_count": len(business_days),
            "business_days_in_requested_window": business_days,
            "historical_write_result": write_result,
            "quote_calendar_reconciliation": reconciliation,
            "content_hash": _sha256_file(operations_path),
            "source_precedence": [
                "historical_snapshot_base",
                "operations_current",
                "validated_acquisition_staging",
            ],
            "legacy_raw_cache_authority": "NON_AUTHORITATIVE",
        }
    )
    return payload


def reconcile_calendar_with_quotes(
    *,
    calendar_frame: Any,
    quote_path: Path | str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    import pandas as pd

    calendar = _canonical_calendar_frame(calendar_frame, source_label="calendar")
    quote_counts = _quote_counts_by_date(Path(quote_path))
    if quote_counts is None:
        return {
            "schema_version": MATERIALIZATION_SCHEMA_VERSION,
            "status": "SKIPPED",
            "reason": "quote_source_missing",
            "quote_path": str(quote_path),
            "ambiguous_dates": [],
            "quote_dates": [],
        }
    quote_dates = sorted(day for day in quote_counts if start_date <= day <= end_date)
    logical_start = max(start_date, quote_dates[0]) if quote_dates else start_date
    logical_end = min(end_date, quote_dates[-1]) if quote_dates else end_date
    logical = calendar[(calendar["Date"].astype(str) >= logical_start) & (calendar["Date"].astype(str) <= logical_end)].copy()
    states = {
        str(row.Date): str(row.HolDiv).strip() in {"1", "1.0"}
        for row in logical[["Date", "HolDiv"]].itertuples(index=False)
    }
    ambiguous = []
    for day, is_open in sorted(states.items()):
        count = int(quote_counts.get(day, 0))
        if is_open and count <= 0:
            ambiguous.append({"date": day, "calendar_state": "OPEN", "quote_rows": count, "reason": "calendar_open_quote_rows_zero"})
        elif not is_open and count > 0:
            ambiguous.append({"date": day, "calendar_state": "CLOSED", "quote_rows": count, "reason": "calendar_closed_quote_rows_present"})
    for day in quote_dates:
        if day not in states:
            ambiguous.append({"date": day, "calendar_state": "MISSING", "quote_rows": int(quote_counts[day]), "reason": "quote_rows_without_calendar_date"})
    return {
        "schema_version": MATERIALIZATION_SCHEMA_VERSION,
        "status": "PASS" if not ambiguous else "REVIEW_REQUIRED",
        "reason": "calendar_quote_reconciliation_pass" if not ambiguous else "calendar_quote_reconciliation_ambiguity",
        "quote_path": str(quote_path),
        "quote_date_count": len(quote_dates),
        "quote_min_date": quote_dates[0] if quote_dates else "",
        "quote_max_date": quote_dates[-1] if quote_dates else "",
        "reconciled_start_date": logical_start,
        "reconciled_end_date": logical_end,
        "ambiguous_dates": ambiguous,
    }


def _base_payload(kind: str, *, root: Path, source: Path, confirm: bool) -> dict[str, Any]:
    return {
        "schema_version": MATERIALIZATION_SCHEMA_VERSION,
        "kind": kind,
        "runtime_root": str(root),
        "source_path": str(source),
        "source_exists": source.is_file(),
        "source_hash": _sha256_file(source),
        "confirm": confirm,
        "mutates_strategy_or_pm_policy": False,
    }


def _listed_frame_blockers(frame: Any, *, requested_start_date: str, requested_end_date: str) -> list[str]:
    blockers = []
    for column in ("Date", "Code"):
        if column not in frame.columns:
            blockers.append(f"listed_required_column_missing:{column}")
    if blockers:
        return blockers
    dates = sorted(str(value) for value in frame["Date"].dropna().astype(str).unique())
    if not dates:
        blockers.append("listed_source_empty")
    elif dates[0] > requested_start_date or dates[-1] < requested_end_date:
        blockers.append("listed_source_requested_window_not_covered")
    if int(frame.duplicated(["Date", "Code"]).sum()):
        blockers.append("listed_duplicate_date_code")
    return blockers


def _calendar_frame_blockers(frame: Any, *, requested_start_date: str, requested_end_date: str) -> list[str]:
    blockers = []
    if "Date" not in frame.columns or "HolDiv" not in frame.columns:
        return ["calendar_required_columns_missing"]
    dates = sorted(str(value) for value in frame["Date"].dropna().astype(str).unique())
    if not dates:
        blockers.append("calendar_source_empty")
    elif dates[0] > requested_start_date or dates[-1] < requested_end_date:
        blockers.append("calendar_requested_window_not_covered")
    if int(frame.duplicated(["Date"]).sum()):
        blockers.append("calendar_duplicate_date")
    return blockers


def _raw_ohlcv_frame_blockers(
    frame: Any,
    *,
    source_inventory: dict[str, Any],
    requested_start_date: str,
    requested_end_date: str,
) -> list[str]:
    blockers = []
    missing = [column for column in REQUIRED_RAW_OHLCV_COLUMNS if column not in frame.columns]
    if missing:
        blockers.append("raw_ohlcv_required_columns_missing")
    if blockers:
        return blockers
    dates = sorted(str(value) for value in frame["Date"].dropna().astype(str).unique())
    if not dates:
        blockers.append("raw_ohlcv_source_empty")
    elif dates[0] > requested_start_date or dates[-1] < requested_end_date:
        blockers.append("raw_ohlcv_requested_window_not_covered")
    if int(frame.duplicated(["Date", "Code"]).sum()):
        blockers.append("raw_ohlcv_duplicate_date_code")
    if source_inventory.get("jquants_lineage_status") != "PASS":
        blockers.append("raw_ohlcv_jquants_lineage_not_pass")
    if source_inventory.get("future_or_training_columns_detected"):
        blockers.append("raw_ohlcv_training_or_future_columns_detected")
    if source_inventory.get("status") != "PASS":
        blockers.append("raw_ohlcv_inventory_not_pass")
    return blockers


def _raw_ohlcv_staging_validation(source: Path) -> dict[str, Any]:
    run_root = source.parents[3] if len(source.parents) > 3 else source.parent
    normalized_path = run_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    plan_path = run_root / "plan.json"
    state_path = run_root / "state.json"
    payload: dict[str, Any] = {
        "schema_version": MATERIALIZATION_SCHEMA_VERSION,
        "component_id": "raw_ohlcv_staging_validation",
        "run_root": str(run_root),
        "raw_path": str(source),
        "normalized_path": str(normalized_path),
        "plan_path": str(plan_path),
        "state_path": str(state_path),
        "raw_hash": _sha256_file(source),
        "normalized_hash": _sha256_file(normalized_path),
    }
    blocked = []
    if not plan_path.is_file() or not state_path.is_file():
        blocked.append("raw_ohlcv_staging_validation_artifact_missing")
    if not normalized_path.is_file():
        blocked.append("raw_ohlcv_staging_normalized_pair_missing")
    plan: dict[str, Any] = {}
    state: dict[str, Any] = {}
    if plan_path.is_file() and state_path.is_file():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - fail closed on malformed validation artifacts.
            blocked.append(f"raw_ohlcv_staging_validation_artifact_unreadable:{type(exc).__name__}")
    final = dict(state.get("final_validation") or {})
    normalized_inventory = dict(final.get("normalized_inventory") or {})
    lineage = dict(final.get("jquants_lineage") or {})
    schema = dict(final.get("schema_comparison") or {})
    if plan or state:
        if plan.get("status") != "PASS" or state.get("status") != "PASS" or final.get("status") != "PASS":
            blocked.append("raw_ohlcv_staging_final_validation_not_pass")
        if plan.get("acquisition_run_id") != run_root.name or state.get("acquisition_run_id") != run_root.name:
            blocked.append("raw_ohlcv_staging_run_id_mismatch")
        if final.get("content_hash") and final.get("content_hash") != payload["normalized_hash"]:
            blocked.append("raw_ohlcv_staging_normalized_hash_mismatch")
        if int(normalized_inventory.get("duplicate_key_count") or 0):
            blocked.append("raw_ohlcv_staging_normalized_duplicate_keys")
        if int(final.get("future_date_count") or 0):
            blocked.append("raw_ohlcv_staging_future_date_rows")
        if lineage.get("status") != "PASS":
            blocked.append("raw_ohlcv_staging_lineage_not_pass")
        if schema.get("status") != "PASS" or schema.get("runtime_merge_compatible") is not True:
            blocked.append("raw_ohlcv_staging_schema_not_runtime_compatible")
    payload.update(
        {
            "status": "PASS" if not blocked else "BLOCK",
            "reason": "validated_acquisition_raw_ohlcv_staging_ready" if not blocked else blocked[0],
            "acquisition_run_id": str(state.get("acquisition_run_id") or plan.get("acquisition_run_id") or ""),
            "coverage_start_date": str(final.get("coverage_start_date") or ""),
            "coverage_end_date": str(final.get("coverage_end_date") or ""),
            "lineage_status": str(lineage.get("status") or ""),
            "schema_status": str(schema.get("status") or ""),
            "runtime_merge_compatible": bool(schema.get("runtime_merge_compatible")),
            "blocked_reasons": list(dict.fromkeys(blocked)),
        }
    )
    return payload


def _raw_ohlcv_post_materialization_verification(
    *,
    source_inventory: dict[str, Any],
    target_inventory: dict[str, Any],
    requested_start_date: str,
    requested_end_date: str,
) -> dict[str, Any]:
    blocked = []
    for key, reason in (
        ("row_count", "raw_ohlcv_post_materialization_row_count_mismatch"),
        ("earliest_date", "raw_ohlcv_post_materialization_earliest_date_mismatch"),
        ("latest_date", "raw_ohlcv_post_materialization_latest_date_mismatch"),
        ("schema_hash", "raw_ohlcv_post_materialization_schema_hash_mismatch"),
        ("content_hash", "raw_ohlcv_post_materialization_content_hash_mismatch"),
    ):
        if str(target_inventory.get(key) or "") != str(source_inventory.get(key) or ""):
            blocked.append(reason)
    if not target_inventory.get("exists"):
        blocked.append("raw_ohlcv_post_materialization_target_missing")
    if target_inventory.get("status") != "PASS":
        blocked.append("raw_ohlcv_post_materialization_inventory_not_pass")
    if target_inventory.get("duplicate_key_count"):
        blocked.append("raw_ohlcv_post_materialization_duplicate_keys")
    if str(target_inventory.get("earliest_date") or "") > requested_start_date:
        blocked.append("raw_ohlcv_post_materialization_start_not_covered")
    if str(target_inventory.get("latest_date") or "") < requested_end_date:
        blocked.append("raw_ohlcv_post_materialization_end_not_covered")
    return {
        "schema_version": MATERIALIZATION_SCHEMA_VERSION,
        "component_id": "raw_ohlcv_post_materialization_verification",
        "status": "PASS" if not blocked else "BLOCK",
        "reason": "raw_ohlcv_post_materialization_verified" if not blocked else blocked[0],
        "source_inventory": source_inventory,
        "target_inventory": target_inventory,
        "blocked_reasons": list(dict.fromkeys(blocked)),
    }


def _listed_validation_dates(frame: Any, *, requested_start_date: str, requested_end_date: str) -> list[str]:
    dates = sorted(str(value) for value in frame["Date"].dropna().astype(str).unique())
    selected = {dates[0], dates[-1]} if dates else set()
    selected.update(day for day in (requested_start_date, requested_end_date) if day)
    selected.update(day for day in dates if requested_start_date <= day <= requested_end_date)
    return sorted(selected)[:5] + sorted(selected)[-5:] if len(selected) > 10 else sorted(selected)


def _canonical_calendar_frame(frame: Any, *, source_label: str) -> Any:
    import pandas as pd

    if frame is None:
        return pd.DataFrame(columns=["Date", "HolDiv", "source", "endpoint", "fetched_at"])
    normalized = frame.copy()
    date_column = next((column for column in ("Date", "calendar_date", "date") if column in normalized.columns), "")
    holdiv_column = next((column for column in ("HolDiv", "HolidayDivision", "holiday_division") if column in normalized.columns), "")
    if not date_column:
        return pd.DataFrame(columns=["Date", "HolDiv", "source", "endpoint", "fetched_at"])
    normalized["Date"] = normalized[date_column].astype(str)
    if holdiv_column:
        normalized["HolDiv"] = normalized[holdiv_column].astype(str)
    elif "is_trading_day" in normalized.columns:
        normalized["HolDiv"] = normalized["is_trading_day"].map(lambda value: "1" if bool(value) else "3")
    else:
        normalized["HolDiv"] = ""
    normalized["source"] = normalized.get("source", source_label)
    normalized["endpoint"] = normalized.get("endpoint", "/v2/markets/calendar")
    normalized["fetched_at"] = normalized.get("fetched_at", "")
    normalized["materialization_source"] = source_label
    normalized["calendar_date"] = normalized["Date"]
    normalized["holiday_division"] = normalized["HolDiv"]
    normalized["is_trading_day"] = normalized["HolDiv"].astype(str).isin({"1", "1.0"})
    return normalized


def _read_optional_calendar_frame(path: Path, *, source_label: str) -> Any:
    if not path.is_file():
        return None
    import pandas as pd

    return _canonical_calendar_frame(pd.read_parquet(path), source_label=source_label)


def _merge_calendar_frames(frames: list[Any]) -> Any:
    import pandas as pd

    non_empty = [frame for frame in frames if frame is not None and len(frame)]
    if not non_empty:
        return pd.DataFrame(columns=["Date", "HolDiv", "source", "endpoint", "fetched_at"])
    merged = pd.concat(non_empty, ignore_index=True, sort=False)
    merged["Date"] = merged["Date"].astype(str)
    merged = merged.drop_duplicates(["Date"], keep="last").sort_values("Date").reset_index(drop=True)
    merged["calendar_date"] = merged["Date"]
    merged["holiday_division"] = merged["HolDiv"].astype(str)
    merged["is_trading_day"] = merged["HolDiv"].astype(str).isin({"1", "1.0"})
    return merged


def _quote_counts_by_date(path: Path) -> dict[str, int] | None:
    if not path.is_file():
        return None
    import pandas as pd

    frame = pd.read_parquet(path, columns=["Date"])
    return {str(key): int(value) for key, value in frame["Date"].astype(str).value_counts().to_dict().items()}


def _atomic_write_parquet(frame: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temp_path, index=False, engine="pyarrow")
    temp_path.replace(path)


def _atomic_copy_file(source: Path, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with source.open("rb") as src, temp_path.open("wb") as dst:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            dst.write(chunk)
    temp_path.replace(path)


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
