from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping


INVENTORY_SCHEMA_VERSION = "phase22_pt_source_coverage_inventory.v1"
PREFLIGHT_SCHEMA_VERSION = "phase22_pt_historical_strategy_source_preflight.v1"
MATERIALIZATION_SCHEMA_VERSION = "phase22_pt_materialization_manifest.v1"


@dataclass(frozen=True)
class SourceSpec:
    name: str
    authority_owner: str
    path: Path
    file_format: str
    date_columns: tuple[str, ...]
    symbol_columns: tuple[str, ...] = ()
    required: bool = True
    required_lookback: int = 0
    consumer_components: tuple[str, ...] = ()


def default_source_specs(runtime_root: Path) -> tuple[SourceSpec, ...]:
    operations = runtime_root / "operations"
    return (
        SourceSpec(
            name="trading_calendar",
            authority_owner="J-Quants canonical operations",
            path=operations / "jquants" / "raw" / "jquants" / "trading_calendar" / "data.parquet",
            file_format="parquet",
            date_columns=("target_date", "Date", "date"),
            symbol_columns=("code", "Code"),
            required=True,
            consumer_components=("runtime_plan", "market_context", "preflight"),
        ),
        SourceSpec(
            name="daily_quotes",
            authority_owner="J-Quants canonical normalized daily quotes",
            path=operations / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet",
            file_format="parquet",
            date_columns=("target_date", "Date", "date"),
            symbol_columns=("code", "Code", "LocalCode", "symbol"),
            required=True,
            required_lookback=21,
            consumer_components=("market_context", "benchmark_proxy_inputs", "breadth_universe", "volatility_inputs"),
        ),
        SourceSpec(
            name="listed_information",
            authority_owner="J-Quants canonical listed issues",
            path=operations / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
            file_format="parquet",
            date_columns=("target_date", "Date", "date", "provider_effective_date"),
            symbol_columns=("code", "Code", "LocalCode", "symbol"),
            required=True,
            consumer_components=("listed_universe", "sector_classification", "corporate_event_listed_status"),
        ),
        SourceSpec(
            name="corporate_actions",
            authority_owner="J-Quants canonical corporate actions",
            path=operations / "jquants" / "raw" / "jquants" / "corporate_actions" / "data.parquet",
            file_format="parquet",
            date_columns=("target_date", "Date", "date", "effective_date"),
            symbol_columns=("code", "Code", "LocalCode", "symbol"),
            required=False,
            consumer_components=("corporate_event", "position_management"),
        ),
        SourceSpec(
            name="earnings_schedule",
            authority_owner="J-Quants canonical earnings schedule",
            path=operations / "jquants" / "raw" / "jquants" / "earnings_schedule" / "data.parquet",
            file_format="parquet",
            date_columns=("target_date", "Date", "date", "announcement_date"),
            symbol_columns=("code", "Code", "LocalCode", "symbol"),
            required=False,
            consumer_components=("corporate_event", "position_management"),
        ),
        SourceSpec(
            name="financial_statements",
            authority_owner="J-Quants canonical financial statements",
            path=operations / "jquants" / "raw" / "jquants" / "financial_statements" / "data.parquet",
            file_format="parquet",
            date_columns=("target_date", "Date", "date", "announcement_date"),
            symbol_columns=("code", "Code", "LocalCode", "symbol"),
            required=False,
            consumer_components=("corporate_event", "position_management"),
        ),
    )


def build_source_coverage_inventory(*, runtime_root: Path) -> dict[str, Any]:
    sources = [_inventory_for_spec(spec, runtime_root=runtime_root) for spec in default_source_specs(runtime_root)]
    buy_ai = _buy_ai_coverage(runtime_root / "runtime_state" / "buy_ai")
    state = _json_state_coverage(runtime_root=runtime_root)
    accepted = _accepted_generation_coverage(runtime_root / "runtime_state" / "accepted_buy_ai_bundle.json")
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "runtime_root": str(runtime_root),
        "sources": sources,
        "candidate_output": buy_ai["candidate"],
        "opportunity_output": buy_ai["opportunity"],
        "portfolio_state": state["portfolio_state"],
        "pending_state": state["pending_state"],
        "accepted_generation": accepted,
        "canonical_source_authority": {
            "market_listed_sector_corporate_event_authority": "J_QUANTS_ONLY",
            "candidate_opportunity_authority": "COMMITTED_ACCEPTED_GENERATION_OUTPUTS",
            "runtime_state_authority": "RUN_SCOPED_ISOLATED_RUNTIME_ROOT",
            "forbidden_inputs": [
                "backtest_result",
                "paper_ledger_pnl",
                "selected_or_bought_outcome",
                "strategy_outcome",
                "broker_execution_outcome",
                "future_information",
                "audit_or_test_result",
            ],
        },
    }


def build_historical_strategy_preflight(
    *,
    runtime_root: Path,
    requested_start_date: str,
    requested_business_days: int,
    requested_dates: list[str] | None = None,
) -> dict[str, Any]:
    inventory = build_source_coverage_inventory(runtime_root=runtime_root)
    calendar_dates = _source_dates(inventory, "trading_calendar")
    resolved_dates = list(requested_dates) if requested_dates is not None else _business_dates_from_calendar(calendar_dates, requested_start_date, requested_business_days)
    evaluation_end = resolved_dates[-1] if resolved_dates else requested_start_date
    required_warmup_start = _warmup_start(calendar_dates, requested_start_date, 21)
    root_blockers: list[str] = []
    missing_sources: list[str] = []

    market = _coverage_check(inventory, "daily_quotes", requested_start_date, evaluation_end, warmup_start=required_warmup_start)
    if not _has_warmup(calendar_dates, requested_start_date, 21):
        market["status"] = "BOOTSTRAP_REQUIRED"
        market.setdefault("reason_codes", []).append("daily_quotes_required_warmup_insufficient")
    listed = _coverage_check(inventory, "listed_information", requested_start_date, evaluation_end)
    sector = _sector_readiness(inventory, requested_start_date, evaluation_end)
    corporate = _corporate_event_readiness(inventory, requested_start_date, evaluation_end)
    candidate = _daily_runtime_generation_readiness(inventory["candidate_output"], resolved_dates, "candidate")
    opportunity = _daily_runtime_generation_readiness(inventory["opportunity_output"], resolved_dates, "opportunity")
    portfolio = _state_readiness(inventory["portfolio_state"], requested_start_date, role="portfolio_state")
    pending = _state_readiness(inventory["pending_state"], requested_start_date, role="pending_state")
    accepted = inventory["accepted_generation"]
    accepted_ready = {"status": "PASS" if accepted.get("exists") else "BLOCK", "reason_codes": [] if accepted.get("exists") else ["accepted_generation_pointer_missing"]}

    checks = {
        "market_coverage": market,
        "listed_coverage": listed,
        "sector_coverage": sector,
        "corporate_event_coverage": corporate,
        "candidate_generation_readiness": candidate,
        "opportunity_generation_readiness": opportunity,
        "portfolio_state_readiness": portfolio,
        "pending_state_readiness": pending,
        "accepted_generation_readiness": accepted_ready,
    }
    for name, check in checks.items():
        status = str(check.get("status") or "")
        if status in {"BLOCK", "NOT_ELIGIBLE_SOURCE_COVERAGE", "SOURCE_UNAVAILABLE", "BOOTSTRAP_REQUIRED"}:
            root_blockers.append(name)
            missing_sources.extend(str(code) for code in check.get("reason_codes", []) if code)
    first_eligible = first_eligible_start_date(inventory=inventory, requested_business_days=requested_business_days)
    operator_ready = bool(resolved_dates) and not root_blockers
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "runtime_root": str(runtime_root),
        "requested_start_date": requested_start_date,
        "requested_business_days": requested_business_days,
        "required_warmup_start": required_warmup_start,
        "evaluation_end_date": evaluation_end,
        "source_coverage_start": _max_date([market.get("coverage_start"), listed.get("coverage_start"), sector.get("coverage_start")]),
        "source_coverage_end": _min_date([market.get("coverage_end"), listed.get("coverage_end"), sector.get("coverage_end")]),
        "candidate_coverage": candidate,
        "opportunity_coverage": opportunity,
        "portfolio_state_coverage": portfolio,
        "eligible_dates": resolved_dates if operator_ready else [],
        "blocked_dates": [] if operator_ready else resolved_dates,
        "first_eligible_start_date": first_eligible,
        "missing_sources": sorted(set(missing_sources)),
        "root_blockers": sorted(set(root_blockers)),
        "operator_ready": operator_ready,
        "judgment": "ELIGIBLE" if operator_ready else "NOT_ELIGIBLE_SOURCE_COVERAGE",
        **checks,
    }


def build_materialization_manifest(*, runtime_root: Path) -> dict[str, Any]:
    inventory = build_source_coverage_inventory(runtime_root=runtime_root)
    outputs: list[dict[str, Any]] = []
    for source in inventory["sources"]:
        outputs.append(
            {
                "source_name": source["name"],
                "materialization_strategy": "REUSE_EXISTING_CANONICAL_SOURCE" if source["exists"] else "SOURCE_UNAVAILABLE",
                "output_reference": source["canonical_path"],
                "output_hash": source.get("sha256", ""),
                "min_business_date": source.get("min_business_date", ""),
                "max_business_date": source.get("max_business_date", ""),
                "row_count": source.get("row_count", 0),
                "symbol_count": source.get("symbol_count", 0),
            }
        )
    payload = {
        "schema_version": MATERIALIZATION_SCHEMA_VERSION,
        "materialization_id": "phase22_pt_reuse_existing_canonical_jquants_sources",
        "source_authority": "J_QUANTS_CANONICAL_DATA",
        "runtime_root": str(runtime_root),
        "outputs": outputs,
        "pit_contract": {
            "future_rows_allowed_in_file": True,
            "future_rows_allowed_in_selection": False,
            "latest_fallback_allowed": False,
            "date_rewrite_allowed": False,
            "run_scoped_mutable_state_required": True,
        },
    }
    payload["manifest_hash"] = _hash_mapping(payload)
    return payload


def first_eligible_start_date(*, inventory: Mapping[str, Any], requested_business_days: int) -> str:
    calendar_dates = _source_dates(inventory, "trading_calendar")
    if not calendar_dates:
        return ""
    candidates = sorted(set(calendar_dates))
    for candidate in candidates:
        dates = _business_dates_from_calendar(calendar_dates, candidate, requested_business_days)
        if len(dates) != requested_business_days:
            continue
        preflight = _preflight_from_inventory(inventory=inventory, requested_start_date=candidate, requested_dates=dates)
        if preflight:
            return candidate
    return ""


def _preflight_from_inventory(*, inventory: Mapping[str, Any], requested_start_date: str, requested_dates: list[str]) -> bool:
    calendar_dates = _source_dates(inventory, "trading_calendar")
    warmup_start = _warmup_start(calendar_dates, requested_start_date, 21)
    end = requested_dates[-1]
    checks = [
        _market_check_with_warmup(inventory, calendar_dates, requested_start_date, end, warmup_start),
        _coverage_check(inventory, "listed_information", requested_start_date, end),
    ]
    return all(check.get("status") == "PASS" for check in checks)


def _market_check_with_warmup(inventory: Mapping[str, Any], calendar_dates: list[str], start: str, end: str, warmup_start: str) -> dict[str, Any]:
    check = _coverage_check(inventory, "daily_quotes", start, end, warmup_start=warmup_start)
    if not _has_warmup(calendar_dates, start, 21):
        check["status"] = "BOOTSTRAP_REQUIRED"
        check.setdefault("reason_codes", []).append("daily_quotes_required_warmup_insufficient")
    return check


def _inventory_for_spec(spec: SourceSpec, *, runtime_root: Path) -> dict[str, Any]:
    overlay_paths = _validated_acquisition_overlay_paths(runtime_root=runtime_root, source_name=spec.name)
    source_paths = [spec.path, *overlay_paths]
    base: dict[str, Any] = {
        "name": spec.name,
        "authority_owner": spec.authority_owner,
        "canonical_path": str(spec.path),
        "authority_paths": [str(path) for path in source_paths],
        "overlay_paths": [str(path) for path in overlay_paths],
        "overlay_count": len(overlay_paths),
        "selected_source_role": "canonical_plus_validated_acquisition_overlay" if overlay_paths else "operations_canonical",
        "canonical_mutated": False,
        "fallback_path": "",
        "legacy_path": "",
        "file_format": spec.file_format,
        "required": spec.required,
        "required_lookback": spec.required_lookback,
        "consumer_components": list(spec.consumer_components),
        "exists": any(path.is_file() for path in source_paths),
        "sha256": _file_hash(spec.path),
        "date_column": "",
        "publication_effective_date_fields": list(spec.date_columns),
        "pit_usability": "SOURCE_UNAVAILABLE",
        "materialization_command": (
            "reuse operations canonical source plus validated acquisition staging overlay; no runtime mutation"
            if overlay_paths
            else "reuse canonical source; no per-run rewrite"
        ),
        "missing_periods": [],
        "row_count": 0,
        "symbol_count": 0,
        "min_business_date": "",
        "max_business_date": "",
        "dates": [],
    }
    readable_paths = [path for path in source_paths if path.is_file()]
    if not readable_paths:
        return base
    try:
        import pandas as pd

        frames = [pd.read_parquet(path) for path in readable_paths]
        frame = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    except Exception as exc:
        base.update({"pit_usability": "READ_ERROR", "read_error": type(exc).__name__})
        return base
    base["row_count"] = int(len(frame))
    date_col = _best_populated_column(frame, spec.date_columns)
    symbol_col = _best_populated_column(frame, spec.symbol_columns)
    base["date_column"] = date_col
    if symbol_col:
        symbols: set[str] = set()
        for col in spec.symbol_columns:
            if col in frame.columns:
                symbols.update(str(value) for value in frame[col].dropna().astype(str))
        base["symbol_count"] = len(symbols)
    if date_col and not frame.empty:
        dates: list[str] = sorted(
            {
                str(value)
                for col in spec.date_columns
                if col in frame.columns
                for value in frame[col].dropna().astype(str)
            }
        )
        base["dates"] = dates
        base["min_business_date"] = dates[0] if dates else ""
        base["max_business_date"] = dates[-1] if dates else ""
        base["pit_usability"] = "PIT_USABLE" if dates else "SOURCE_UNAVAILABLE"
    return base


def _best_populated_column(frame: Any, columns: tuple[str, ...]) -> str:
    present = [column for column in columns if column in frame.columns]
    if not present:
        return ""
    return max(present, key=lambda column: int(frame[column].notna().sum()))


def _validated_acquisition_overlay_paths(*, runtime_root: Path, source_name: str) -> list[Path]:
    relative_by_source = {
        "trading_calendar": Path("raw/jquants/trading_calendar/data.parquet"),
        "daily_quotes": Path("raw_normalized/jquants/equities_bars_daily/data.parquet"),
        "listed_information": Path("raw/jquants/listed_issues/data.parquet"),
    }
    relative = relative_by_source.get(source_name)
    if relative is None:
        return []
    run_root = runtime_root / "market_data_acquisition" / "runs"
    if not run_root.is_dir():
        return []
    paths: list[Path] = []
    for state_path in sorted(run_root.glob("*/state.json")):
        run_dir = state_path.parent
        plan_path = run_dir / "plan.json"
        source_path = run_dir / relative
        if not plan_path.is_file() or not source_path.is_file():
            continue
        state = _read_json(state_path)
        plan = _read_json(plan_path)
        final = dict(state.get("final_validation") or {})
        if state.get("status") != "PASS" or plan.get("status") != "PASS" or final.get("status") != "PASS":
            continue
        if state.get("acquisition_run_id") != run_dir.name or plan.get("acquisition_run_id") != run_dir.name:
            continue
        if int(final.get("future_date_count") or 0) != 0:
            continue
        paths.append(source_path)
    return paths


def _buy_ai_coverage(root: Path) -> dict[str, Any]:
    result = {
        "candidate": _daily_json_coverage(root, "candidate_decisions.json", "candidate"),
        "opportunity": _daily_json_coverage(root, "opportunity_rankings.json", "opportunity"),
    }
    return result


def _daily_json_coverage(root: Path, filename: str, role: str) -> dict[str, Any]:
    dates: list[str] = []
    hashes: dict[str, str] = {}
    if root.is_dir():
        for path in sorted(root.glob(f"*/{filename}")):
            day = path.parent.name
            payload = _read_json(path)
            payload_date = str(payload.get("business_date") or payload.get("target_date") or payload.get("date") or day)
            if payload_date == day:
                dates.append(day)
                hashes[day] = _file_hash(path)
    return {
        "role": role,
        "authority_owner": "COMMITTED_ACCEPTED_GENERATION_DAILY_OUTPUT",
        "root": str(root),
        "file_name": filename,
        "dates": dates,
        "min_business_date": min(dates) if dates else "",
        "max_business_date": max(dates) if dates else "",
        "date_count": len(dates),
        "hashes": hashes,
        "pit_usability": "PIT_USABLE" if dates else "SOURCE_UNAVAILABLE",
        "latest_fallback_allowed": False,
    }


def _json_state_coverage(*, runtime_root: Path) -> dict[str, Any]:
    return {
        "portfolio_state": _state_file(runtime_root / "persistent_ledger" / "state.json", "portfolio_state"),
        "pending_state": _state_file(runtime_root / "pending_order_plan" / "pending_order_plan.json", "pending_state"),
    }


def _state_file(path: Path, role: str) -> dict[str, Any]:
    payload = _read_json(path) if path.is_file() else {}
    state_date = str(payload.get("business_date") or payload.get("as_of_date") or payload.get("date") or "")
    return {
        "role": role,
        "authority_owner": "RUN_SCOPED_ISOLATED_RUNTIME_ROOT",
        "path": str(path),
        "exists": path.is_file(),
        "sha256": _file_hash(path),
        "state_business_date": state_date,
        "pit_usability": "PIT_USABLE" if path.is_file() else "SOURCE_UNAVAILABLE",
    }


def _accepted_generation_coverage(path: Path) -> dict[str, Any]:
    payload = _read_json(path) if path.is_file() else {}
    return {
        "authority_owner": "COMMITTED_ACCEPTED_GENERATION_RESOLVER",
        "path": str(path),
        "exists": path.is_file(),
        "sha256": _file_hash(path),
        "generation_id": str(payload.get("generation_id") or payload.get("accepted_generation_id") or ""),
        "resolution_status": str(payload.get("resolution_status") or ""),
        "pit_usability": "PIT_USABLE" if path.is_file() else "SOURCE_UNAVAILABLE",
    }


def _coverage_check(inventory: Mapping[str, Any], source_name: str, start: str, end: str, *, warmup_start: str = "") -> dict[str, Any]:
    source = _source_by_name(inventory, source_name)
    coverage_start = str(source.get("min_business_date") or "")
    coverage_end = str(source.get("max_business_date") or "")
    required_start = warmup_start or start
    reasons: list[str] = []
    if not source.get("exists"):
        reasons.append(f"{source_name}_missing")
    if coverage_start and required_start < coverage_start:
        reasons.append(f"{source_name}_coverage_starts_after_required_start")
    if coverage_end and end > coverage_end:
        reasons.append(f"{source_name}_coverage_ends_before_evaluation_end")
    status = "PASS" if not reasons else "NOT_ELIGIBLE_SOURCE_COVERAGE"
    return {
        "status": status,
        "source_name": source_name,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "required_start": required_start,
        "evaluation_end_date": end,
        "reason_codes": reasons,
        "authority_paths": list(source.get("authority_paths") or []),
        "overlay_paths": list(source.get("overlay_paths") or []),
        "selected_source_role": str(source.get("selected_source_role") or ""),
        "canonical_mutated": bool(source.get("canonical_mutated")),
        "fallback_path": str(source.get("fallback_path") or ""),
        "legacy_path": str(source.get("legacy_path") or ""),
    }


def _sector_readiness(inventory: Mapping[str, Any], start: str, end: str) -> dict[str, Any]:
    listed = _coverage_check(inventory, "listed_information", start, end)
    source = _source_by_name(inventory, "listed_information")
    status = "PASS" if listed["status"] == "PASS" else listed["status"]
    return {
        **listed,
        "status": status,
        "sector_source_status": "JQUANTS_LISTED_ISSUES_SECTOR_COLUMNS",
        "sector_pit_available": status == "PASS",
        "sector_effective_as_of": start if status == "PASS" else "",
        "sector_coverage_start": source.get("min_business_date", ""),
        "sector_coverage_end": source.get("max_business_date", ""),
        "sector_fallback_used": False,
    }


def _corporate_event_readiness(inventory: Mapping[str, Any], start: str, end: str) -> dict[str, Any]:
    listed = _coverage_check(inventory, "listed_information", start, end)
    optional = {
        name: _source_by_name(inventory, name)
        for name in ("corporate_actions", "earnings_schedule", "financial_statements")
    }
    available_optional = sorted(name for name, source in optional.items() if source.get("exists"))
    coverage = "AVAILABLE" if len(available_optional) == len(optional) and listed["status"] == "PASS" else "PARTIAL" if listed["status"] == "PASS" else "SOURCE_UNAVAILABLE"
    return {
        "status": "PASS" if listed["status"] == "PASS" else listed["status"],
        "overall_event_coverage": coverage,
        "event_states_supported": ["EVENT_PRESENT", "NO_EVENT_CONFIRMED", "SOURCE_PARTIAL", "SOURCE_UNAVAILABLE", "NOT_COVERED"],
        "listed_status_coverage": listed,
        "optional_sources_available": available_optional,
        "optional_sources_missing": sorted(set(optional) - set(available_optional)),
        "reason_codes": [] if listed["status"] == "PASS" else listed.get("reason_codes", []),
    }


def _daily_output_readiness(coverage: Mapping[str, Any], dates: list[str], role: str) -> dict[str, Any]:
    available = set(str(day) for day in coverage.get("dates", []))
    missing = [day for day in dates if day not in available]
    return {
        "status": "PASS" if not missing and bool(dates) else "NOT_ELIGIBLE_SOURCE_COVERAGE",
        "role": role,
        "coverage_start": str(coverage.get("min_business_date") or ""),
        "coverage_end": str(coverage.get("max_business_date") or ""),
        "requested_dates": dates,
        "missing_dates": missing,
        "reason_codes": [] if not missing and dates else [f"{role}_daily_output_missing"],
        "latest_fallback_used": False,
    }


def _daily_runtime_generation_readiness(coverage: Mapping[str, Any], dates: list[str], role: str) -> dict[str, Any]:
    available = set(str(day) for day in coverage.get("dates", []))
    missing = [day for day in dates if day not in available]
    future_existing_dates = sorted(day for day in available if dates and day > max(dates))
    return {
        "status": "PASS" if dates else "REVIEW_REQUIRED",
        "role": role,
        "artifact_lifecycle": "DAILY_RUNTIME_GENERATED_ARTIFACT",
        "producer_job": "morning",
        "producer": "runtime_v2.buy_ai.producer.produce_buy_ai_decisions",
        "consumer": "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority",
        "preexisting_artifact_required": False,
        "runtime_generation_required": True,
        "coverage_start": str(coverage.get("min_business_date") or ""),
        "coverage_end": str(coverage.get("max_business_date") or ""),
        "requested_dates": dates,
        "preexisting_dates": sorted(available & set(dates)),
        "missing_preexisting_dates": missing,
        "missing_dates": [],
        "reason_codes": [] if dates else [f"{role}_runtime_generation_window_unresolved"],
        "latest_fallback_used": False,
        "shared_state_fallback_used": False,
        "default_generation_fallback_used": False,
        "future_artifact_selectable": False,
        "future_existing_dates_ignored": future_existing_dates,
        "failure_semantics": "runtime producer failure on a requested business date becomes REVIEW_REQUIRED/BLOCKED for that day",
    }


def _state_readiness(coverage: Mapping[str, Any], requested_start_date: str, *, role: str) -> dict[str, Any]:
    exists = bool(coverage.get("exists"))
    return {
        "status": "PASS" if exists else "SOURCE_UNAVAILABLE",
        "role": role,
        "requested_start_date": requested_start_date,
        "path": coverage.get("path", ""),
        "state_business_date": coverage.get("state_business_date", ""),
        "run_scoped_required": True,
        "current_state_leakage_detected": False,
        "reason_codes": [] if exists else [f"{role}_missing"],
    }


def _source_by_name(inventory: Mapping[str, Any], source_name: str) -> dict[str, Any]:
    for source in inventory.get("sources", []):
        if isinstance(source, Mapping) and source.get("name") == source_name:
            return dict(source)
    return {"name": source_name, "exists": False}


def _source_dates(inventory: Mapping[str, Any], source_name: str) -> list[str]:
    source = _source_by_name(inventory, source_name)
    return [str(day) for day in source.get("dates", []) if str(day)]


def _business_dates_from_calendar(calendar_dates: list[str], start: str, count: int) -> list[str]:
    dates = [day for day in sorted(calendar_dates) if day >= start]
    if not dates or dates[0] != start:
        return []
    return dates[:count]


def _warmup_start(calendar_dates: list[str], start: str, lookback: int) -> str:
    dates = sorted(calendar_dates)
    if start not in dates:
        return start
    idx = dates.index(start)
    warm_idx = idx - max(lookback - 1, 0)
    return dates[warm_idx] if warm_idx >= 0 else dates[0]


def _has_warmup(calendar_dates: list[str], start: str, lookback: int) -> bool:
    dates = sorted(calendar_dates)
    return start in dates and dates.index(start) >= max(lookback - 1, 0)


def _min_date(values: list[Any]) -> str:
    dates = [str(value) for value in values if value]
    return min(dates) if dates else ""


def _max_date(values: list[Any]) -> str:
    dates = [str(value) for value in values if value]
    return max(dates) if dates else ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_mapping(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
