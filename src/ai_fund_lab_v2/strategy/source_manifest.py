from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


SOURCE_MANIFEST_SCHEMA_VERSION = "strategy_source_manifest.v1"

COMPONENT_NAMES = (
    "market_context",
    "corporate_event",
    "portfolio_policy",
    "portfolio_construction",
    "position_sizing",
    "position_management",
    "runtime_planning",
    "strategy_decision_trace",
    "strategy_shadow_summary",
)

DIRECT_BLOCKER_CLASSES = {
    "DIRECT_SOURCE_PIT_VIOLATION",
    "DIRECT_SOURCE_MISSING",
    "ARTIFACT_ACCEPTANCE_NOT_ELIGIBLE",
    "SOURCE_COVERAGE_INCOMPLETE",
    "CONFIG_SAFETY_CONTRACT_VIOLATION",
    "DOWNSTREAM_COMPONENT_REVIEW_REQUIRED",
    "TEMPORAL_AUTHORITY_MISMATCH",
    "SCHEMA_INCOMPATIBILITY",
    "LINEAGE_MISMATCH",
    "BUSINESS_DATE_MISMATCH",
    "CURRENT_STATE_LEAKAGE",
    "LATEST_ARTIFACT_FALLBACK",
    "BOOTSTRAP_CONTRACT_GAP",
    "RESOLVER_BUG",
    "TEST_ROOT_CONTAMINATION",
    "OTHER",
}


def build_strategy_source_manifest(
    *,
    run_dir: Path,
    runtime_root: Path,
    run_id: str,
    profile_id: str,
    business_date: str,
    strategy_dir: Path,
    decision_timing: str = "EOD",
    input_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    input_manifest = input_manifest or {}
    operations_root = runtime_root / "operations"
    strategy_source_authority = _strategy_source_authority(input_manifest)
    artifacts = _component_artifacts(strategy_dir)
    blockers = classify_component_blockers(artifacts=artifacts, business_date=business_date)
    manifest: dict[str, Any] = {
        "schema_version": SOURCE_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_id": profile_id,
        "business_date": business_date,
        "decision_timing": decision_timing,
        "runtime_root": str(runtime_root),
        "run_dir": str(run_dir),
        "source_policy": {
            "point_in_time": True,
            "latest_fallback_allowed": False,
            "current_state_for_past_date_allowed": False,
            "future_rows_may_exist_but_must_not_be_selected": True,
            "missing_source_status": "SOURCE_UNAVAILABLE",
        },
        "input_manifest": _source_ref(strategy_dir / "input_manifest.json"),
        "portfolio_state": _json_state_ref(runtime_root / "persistent_ledger" / "state.json", business_date=business_date, role="portfolio_state"),
        "pending_state": _json_state_ref(runtime_root / "pending_order_plan" / "pending_order_plan.json", business_date=business_date, role="pending_state"),
        "market_quotes": _parquet_date_ref(
            _authority_path(
                strategy_source_authority,
                "normalized_ohlcv",
                default=operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet",
            ),
            business_date=business_date,
            date_candidates=("target_date", "Date", "date"),
            role="market_quotes",
            required_lookback=21,
        ),
        "benchmark": _benchmark_ref(artifacts.get("market_context", {}), business_date=business_date),
        "sector": _sector_ref(
            _authority_path(
                strategy_source_authority,
                "listed_issues",
                default=operations_root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
            ),
            market_context=artifacts.get("market_context", {}),
            business_date=business_date,
        ),
        "corporate_event": _corporate_event_ref(
            operations_root=operations_root,
            listed_issues_path=_authority_path(
                strategy_source_authority,
                "listed_issues",
                default=operations_root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
            ),
            artifact=artifacts.get("corporate_event", {}),
            business_date=business_date,
        ),
        "candidate": _ai_ref(
            runtime_root / "runtime_state" / "buy_ai" / business_date / "candidate_decisions.json",
            business_date=business_date,
            role="candidate",
        ),
        "opportunity": _ai_ref(
            runtime_root / "runtime_state" / "buy_ai" / business_date / "opportunity_rankings.json",
            business_date=business_date,
            role="opportunity",
        ),
        "price_volatility": _strategy_input_source_ref(
            input_manifest=input_manifest,
            name="price_volatility",
            business_date=business_date,
        ),
        "technical_features": _strategy_input_source_ref(
            input_manifest=input_manifest,
            name="technical_features",
            business_date=business_date,
        ),
        "portfolio_policy_config": _strategy_input_source_ref(
            input_manifest=input_manifest,
            name="portfolio_policy_config",
            business_date=business_date,
        ),
        "bootstrap": {},
        "artifact_locator": {name: _source_ref(path) for name, path in _component_paths(strategy_dir).items()},
        "components": blockers["components"],
        "direct_blockers": blockers["direct_blockers"],
        "propagated_blockers": blockers["propagated_blockers"],
        "root_blocker_components": blockers["root_blocker_components"],
        "root_reason_codes": blockers["root_reason_codes"],
        "hashes": {},
    }
    manifest["bootstrap"] = _bootstrap_ref(manifest["market_quotes"], business_date=business_date)
    manifest["pit_validation"] = _pit_validation(manifest=manifest, input_manifest=input_manifest)
    _attach_pit_status_to_blockers(manifest)
    manifest["hashes"] = _manifest_hashes(manifest)
    return manifest


def manifest_hash(manifest: Mapping[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("hashes", None)
    return _hash_bytes(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def classify_component_blockers(*, artifacts: Mapping[str, Mapping[str, Any]], business_date: str) -> dict[str, Any]:
    components: dict[str, dict[str, Any]] = {}
    direct: dict[str, dict[str, Any]] = {}
    propagated: dict[str, dict[str, Any]] = {}
    root_reason_codes: list[str] = []
    for name in COMPONENT_NAMES:
        payload = artifacts.get(name, {})
        status = str(payload.get("producer_result_status") or payload.get("status") or "")
        reason_codes = [str(code) for code in payload.get("reason_codes", []) if code]
        classes = sorted({_classify_reason(code) for code in reason_codes})
        temporal = payload.get("temporal_safety") if isinstance(payload.get("temporal_safety"), dict) else {}
        if temporal.get("future_leakage_used") is True or temporal.get("feature_date_lte_business_date") is False:
            classes.append("DIRECT_SOURCE_PIT_VIOLATION")
        feature_date = str(payload.get("feature_date") or business_date)
        if feature_date > business_date:
            classes.append("BUSINESS_DATE_MISMATCH")
        is_propagated = any(cls == "UPSTREAM_BLOCK_PROPAGATION" for cls in classes)
        direct_classes = sorted({cls for cls in classes if cls in DIRECT_BLOCKER_CLASSES})
        primary_class = _primary_blocker_class(reason_codes=reason_codes, direct_classes=direct_classes, status=status)
        primary_reason = _primary_reason_code(reason_codes=reason_codes, primary_class=primary_class)
        secondary = [
            {"blocker_class": cls, "reason_codes": sorted(code for code in reason_codes if _classify_reason(code) == cls)}
            for cls in direct_classes
            if cls != primary_class
        ]
        component = {
            "status": status or "MISSING",
            "business_date": str(payload.get("business_date") or ""),
            "feature_date": feature_date,
            "reason_codes": sorted(set(reason_codes)),
            "blocker_classes": sorted(set(classes)),
            "direct_blocker_classes": direct_classes,
            "primary_blocker_class": primary_class,
            "primary_reason_code": primary_reason,
            "secondary_blockers": secondary,
            "pit_validation_status": "PASS",
            "propagated": is_propagated,
        }
        components[name] = component
        if status == "BLOCK":
            if is_propagated and not direct_classes:
                propagated[name] = component
            else:
                direct[name] = component
                root_reason_codes.extend(reason_codes or direct_classes or ["OTHER"])
    return {
        "components": components,
        "direct_blockers": direct,
        "propagated_blockers": propagated,
        "root_blocker_components": sorted(direct),
        "root_reason_codes": sorted(set(root_reason_codes)),
    }


def _component_paths(strategy_dir: Path) -> dict[str, Path]:
    return {
        "market_context": strategy_dir / "market_context.json",
        "corporate_event": strategy_dir / "corporate_event.json",
        "portfolio_policy": strategy_dir / "portfolio_policy.json",
        "portfolio_construction": strategy_dir / "portfolio_construction.json",
        "position_sizing": strategy_dir / "position_sizing.json",
        "position_management": strategy_dir / "position_management.json",
        "runtime_planning": strategy_dir / "runtime_planning.json",
        "strategy_decision_trace": strategy_dir / "strategy_decision_trace.json",
        "strategy_shadow_summary": strategy_dir / "strategy_shadow_summary.json",
    }


def _component_artifacts(strategy_dir: Path) -> dict[str, dict[str, Any]]:
    return {name: _read_json(path) for name, path in _component_paths(strategy_dir).items() if path.is_file()}


def _pit_validation(*, manifest: Mapping[str, Any], input_manifest: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    status = "PASS"
    latest_fallback_used = False
    current_state_leakage = False
    source_block = False
    future_row_rejection_count = 0
    for role in ("market_quotes", "sector", "corporate_event"):
        ref = manifest.get(role)
        if not isinstance(ref, Mapping):
            continue
        future_row_rejection_count += int(ref.get("future_row_rejection_count") or 0)
        latest_fallback_used = latest_fallback_used or bool(ref.get("latest_fallback_used"))
        current_state_leakage = current_state_leakage or bool(ref.get("current_state_leakage_detected"))
        source_block = source_block or ref.get("status") == "BLOCK"
        if ref.get("status") in {"BLOCK", "SOURCE_UNAVAILABLE", "BOOTSTRAP_REQUIRED"}:
            reasons.extend(str(code) for code in ref.get("reason_codes", []) if code)
    for role in ("candidate", "opportunity", "portfolio_state", "pending_state", "price_volatility", "technical_features", "portfolio_policy_config"):
        ref = manifest.get(role)
        if not isinstance(ref, Mapping):
            continue
        if ref.get("status") == "NOT_DECLARED":
            continue
        latest_fallback_used = latest_fallback_used or bool(ref.get("latest_fallback_used"))
        current_state_leakage = current_state_leakage or bool(ref.get("current_state_leakage_detected"))
        source_block = source_block or ref.get("status") == "BLOCK"
        if ref.get("business_date_valid") is False:
            reasons.append(f"{role}_business_date_mismatch")
        if ref.get("status") in {"SOURCE_UNAVAILABLE", "BLOCK"}:
            reasons.extend(str(code) for code in ref.get("reason_codes", []) if code)
    bootstrap = manifest.get("bootstrap") if isinstance(manifest.get("bootstrap"), Mapping) else {}
    if bootstrap.get("status") == "BOOTSTRAP_REQUIRED":
        reasons.extend(str(code) for code in bootstrap.get("reason_codes", []) if code)
    if input_manifest.get("latest_fallback_used") is True:
        latest_fallback_used = True
        reasons.append("input_manifest_latest_fallback_used")
    if latest_fallback_used or current_state_leakage or source_block:
        status = "BLOCK"
    elif reasons:
        status = "REVIEW_REQUIRED"
    return {
        "status": status,
        "reason_codes": sorted(set(reasons)),
        "latest_fallback_used": latest_fallback_used,
        "current_state_leakage_detected": current_state_leakage,
        "future_row_rejection_count": future_row_rejection_count,
        "pit_valid": status == "PASS",
        "source_unavailable": any("missing" in code or "source_unavailable" in code for code in reasons),
        "bootstrap_required": bootstrap.get("status") == "BOOTSTRAP_REQUIRED",
    }


def _strategy_source_authority(input_manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = input_manifest.get("strategy_source_authority")
    if isinstance(direct, Mapping):
        return direct
    sources = input_manifest.get("strategy_input_sources")
    if isinstance(sources, Mapping):
        nested = sources.get("strategy_source_authority")
        if isinstance(nested, Mapping):
            return nested
    return {}


def _authority_path(authority: Mapping[str, Any], key: str, *, default: Path) -> Path:
    paths = authority.get("paths") if isinstance(authority.get("paths"), Mapping) else {}
    value = str(paths.get(key) or "")
    if value:
        return Path(value)
    return default


def _attach_pit_status_to_blockers(manifest: dict[str, Any]) -> None:
    pit_status = str((manifest.get("pit_validation") or {}).get("status") if isinstance(manifest.get("pit_validation"), Mapping) else "")
    for section in ("components", "direct_blockers", "propagated_blockers"):
        items = manifest.get(section)
        if not isinstance(items, dict):
            continue
        for component in items.values():
            if isinstance(component, dict):
                component["pit_validation_status"] = pit_status
                if pit_status == "PASS":
                    component["blocker_classes"] = [
                        cls for cls in component.get("blocker_classes", []) if cls != "DIRECT_SOURCE_PIT_VIOLATION"
                    ]
                    component["direct_blocker_classes"] = [
                        cls for cls in component.get("direct_blocker_classes", []) if cls != "DIRECT_SOURCE_PIT_VIOLATION"
                    ]
                    if component.get("primary_blocker_class") == "DIRECT_SOURCE_PIT_VIOLATION":
                        reason_codes = [str(code) for code in component.get("reason_codes", []) if code]
                        direct_classes = [str(cls) for cls in component.get("direct_blocker_classes", []) if cls]
                        component["primary_blocker_class"] = _primary_blocker_class(
                            reason_codes=reason_codes,
                            direct_classes=direct_classes,
                            status=str(component.get("status") or ""),
                        )
                        component["primary_reason_code"] = _primary_reason_code(
                            reason_codes=reason_codes,
                            primary_class=str(component.get("primary_blocker_class") or ""),
                        )


def _parquet_date_ref(path: Path, *, business_date: str, date_candidates: tuple[str, ...], role: str, required_lookback: int = 0) -> dict[str, Any]:
    ref = _source_ref(path)
    ref.update({"role": role, "selected_as_of": "", "future_row_rejection_count": 0, "latest_fallback_used": False, "reason_codes": []})
    if not path.is_file():
        ref.update({"status": "SOURCE_UNAVAILABLE", "reason_codes": [f"{role}_missing"]})
        return ref
    try:
        import pandas as pd

        frame = pd.read_parquet(path)
    except Exception as exc:
        ref.update({"status": "REVIEW_REQUIRED", "reason_codes": [f"{role}_read_error:{type(exc).__name__}"]})
        return ref
    if frame.empty:
        ref.update({"status": "SOURCE_UNAVAILABLE", "reason_codes": [f"{role}_empty"]})
        return ref
    date_col = next((name for name in date_candidates if name in frame.columns), "")
    if not date_col:
        ref.update({"status": "REVIEW_REQUIRED", "reason_codes": [f"{role}_date_column_missing"]})
        return ref
    dates = frame[date_col].astype(str)
    future_count = int((dates > business_date).sum())
    pit_dates = sorted(set(str(value) for value in dates[dates <= business_date].dropna()))
    ref["future_row_rejection_count"] = future_count
    ref["max_source_date"] = str(dates.max())
    ref["min_source_date"] = str(dates.min())
    if not pit_dates:
        ref.update({"status": "BLOCK", "reason_codes": [f"{role}_future_source_rows_rejected", f"{role}_no_pit_rows"]})
        return ref
    ref["selected_as_of"] = pit_dates[-1]
    ref["available_pit_business_days"] = len(pit_dates)
    if required_lookback and len(pit_dates) < required_lookback:
        ref.update({"status": "BOOTSTRAP_REQUIRED", "reason_codes": [f"{role}_insufficient_history_{required_lookback}d"]})
    else:
        ref.update({"status": "PASS", "reason_codes": []})
    return ref


def _json_state_ref(path: Path, *, business_date: str, role: str) -> dict[str, Any]:
    payload = _read_json(path) if path.is_file() else {}
    ref = _source_ref(path)
    ref.update({"role": role, "selected_as_of": business_date, "latest_fallback_used": False, "current_state_leakage_detected": False})
    if not path.is_file():
        ref.update({"status": "SOURCE_UNAVAILABLE", "reason_codes": [f"{role}_missing"]})
        return ref
    payload_date = str(payload.get("business_date") or payload.get("as_of_date") or payload.get("date") or business_date)
    ref["payload_business_date"] = payload_date
    ref["business_date_valid"] = payload_date <= business_date
    ref["status"] = "PASS" if ref["business_date_valid"] else "BLOCK"
    ref["reason_codes"] = [] if ref["business_date_valid"] else [f"{role}_business_date_mismatch"]
    return ref


def _ai_ref(path: Path, *, business_date: str, role: str) -> dict[str, Any]:
    payload = _read_json(path) if path.is_file() else {}
    ref = _source_ref(path)
    ref.update({"role": role, "latest_fallback_used": False, "current_state_leakage_detected": False})
    if not path.is_file():
        ref.update({"status": "SOURCE_UNAVAILABLE", "reason_codes": [f"{role}_artifact_missing"], "business_date_valid": False})
        return ref
    payload_date = str(payload.get("business_date") or payload.get("target_date") or payload.get("date") or business_date)
    ref["payload_business_date"] = payload_date
    ref["business_date_valid"] = payload_date == business_date
    ref["status"] = "PASS" if ref["business_date_valid"] else "BLOCK"
    ref["reason_codes"] = [] if ref["business_date_valid"] else [f"{role}_business_date_mismatch"]
    return ref


def _benchmark_ref(market_context: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    status = str(market_context.get("producer_result_status") or "SOURCE_UNAVAILABLE")
    metrics = market_context.get("metrics") if isinstance(market_context.get("metrics"), Mapping) else {}
    return {
        "role": "benchmark",
        "status": "PASS" if status == "PASS" else "REVIEW_REQUIRED" if status == "REVIEW_REQUIRED" else "SOURCE_UNAVAILABLE",
        "business_date": business_date,
        "selected_as_of": str(metrics.get("feature_date") or market_context.get("feature_date") or ""),
        "benchmark_id": str(market_context.get("benchmark_id") or ""),
        "coverage_status": str(market_context.get("benchmark_coverage") or ""),
        "reason_codes": [code for code in market_context.get("reason_codes", []) if "benchmark" in str(code)],
    }


def _sector_ref(path: Path, *, market_context: Mapping[str, Any], business_date: str) -> dict[str, Any]:
    ref = _parquet_date_ref(path, business_date=business_date, date_candidates=("target_date", "Date", "date", "provider_effective_date"), role="sector", required_lookback=0)
    if ref.get("status") == "PASS":
        ref["pit_status"] = "PASS"
        ref["sector_pit_available"] = True
        ref["sector_effective_as_of"] = ref.get("selected_as_of", "")
        ref["sector_coverage_start"] = ref.get("min_source_date", "")
        ref["sector_coverage_end"] = ref.get("max_source_date", "")
        ref["sector_fallback_used"] = False
    else:
        ref["pit_status"] = "REVIEW_REQUIRED" if ref.get("status") != "BLOCK" else "BLOCK"
        ref["sector_pit_available"] = False
        ref["sector_effective_as_of"] = ""
        ref["sector_coverage_start"] = ref.get("min_source_date", "")
        ref["sector_coverage_end"] = ref.get("max_source_date", "")
        ref["sector_fallback_used"] = False
        ref["reason_codes"] = sorted(set([*ref.get("reason_codes", []), "sector_historical_pit_source_not_confirmed"]))
    ref["sector_source_status"] = str(market_context.get("authority_policy", {}).get("sector_source_status") if isinstance(market_context.get("authority_policy"), Mapping) else "")
    return ref


def _corporate_event_ref(*, operations_root: Path, listed_issues_path: Path | None = None, artifact: Mapping[str, Any], business_date: str) -> dict[str, Any]:
    listed_ref = _parquet_date_ref(
        listed_issues_path or operations_root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
        business_date=business_date,
        date_candidates=("target_date", "Date", "date", "provider_effective_date"),
        role="corporate_event_listed_issues",
        required_lookback=0,
    )
    coverage = str(artifact.get("coverage_status") or "SOURCE_UNAVAILABLE")
    event_count = int(artifact.get("event_count") or 0)
    status = "PASS" if listed_ref.get("status") == "PASS" else "REVIEW_REQUIRED"
    if listed_ref.get("status") in {"SOURCE_UNAVAILABLE", "BLOCK"}:
        status = str(listed_ref.get("status"))
    return {
        **listed_ref,
        "role": "corporate_event",
        "status": status,
        "coverage_status": coverage,
        "event_semantics": "EVENT_PRESENT" if event_count else "NO_EVENT_CONFIRMED" if status == "PASS" and coverage == "AVAILABLE" else "SOURCE_PARTIAL" if coverage != "AVAILABLE" else "REVIEW_REQUIRED",
        "event_count": event_count,
        "reason_codes": sorted(set([*listed_ref.get("reason_codes", []), *[str(code) for code in artifact.get("reason_codes", []) if code]])),
    }


def _bootstrap_ref(market_quotes: Mapping[str, Any], *, business_date: str) -> dict[str, Any]:
    available = int(market_quotes.get("available_pit_business_days") or 0)
    required = 21
    status = "PASS" if available >= required else "BOOTSTRAP_REQUIRED"
    return {
        "status": status,
        "business_date": business_date,
        "required_lookback_business_days": required,
        "available_pit_business_days": available,
        "reason_codes": [] if status == "PASS" else ["insufficient_history_for_strategy_shadow_bootstrap"],
        "run_mutation_allowed": False,
        "artifact_generation_allowed": True,
    }


def _manifest_hashes(manifest: Mapping[str, Any]) -> dict[str, Any]:
    source_hashes = {}
    for role in ("portfolio_state", "pending_state", "market_quotes", "sector", "candidate", "opportunity", "price_volatility", "technical_features", "portfolio_policy_config"):
        ref = manifest.get(role)
        if isinstance(ref, Mapping):
            source_hashes[role] = str(ref.get("sha256") or "")
    return {"source_hashes": source_hashes, "manifest_sha256": manifest_hash(manifest)}


def _strategy_input_source_ref(*, input_manifest: Mapping[str, Any], name: str, business_date: str) -> dict[str, Any]:
    sources = input_manifest.get("strategy_input_sources") if isinstance(input_manifest.get("strategy_input_sources"), Mapping) else {}
    source = sources.get(name) if isinstance(sources.get(name), Mapping) else {}
    if not source:
        return {
            "path": "",
            "exists": False,
            "sha256": "",
            "role": name,
            "logical_source_identity": name,
            "status": "NOT_DECLARED",
            "business_date": business_date,
            "feature_date": "",
            "business_date_valid": True,
            "latest_fallback_used": False,
            "current_state_leakage_detected": False,
            "pit_status": "NOT_RUN",
            "coverage_status": "NOT_DECLARED",
            "reason_codes": [],
        }
    path = Path(str(source.get("physical_path") or ""))
    ref = _source_ref(path)
    status = str(source.get("status") or ("PASS" if ref["exists"] else "SOURCE_UNAVAILABLE"))
    if status == "REVIEW_REQUIRED":
        manifest_status = "REVIEW_REQUIRED"
    elif status == "PASS":
        manifest_status = "PASS"
    else:
        manifest_status = "SOURCE_UNAVAILABLE" if not ref["exists"] else status
    payload_date = str(source.get("business_date") or business_date)
    feature_date = str(source.get("feature_date") or "")
    reason_codes = [str(code) for code in source.get("reason_codes", []) if code] if isinstance(source.get("reason_codes"), list) else []
    if not ref["exists"] and not reason_codes:
        reason_codes.append(f"{name}_missing")
    business_date_valid = payload_date == business_date
    if not business_date_valid:
        reason_codes.append(f"{name}_business_date_mismatch")
    if feature_date and feature_date > business_date:
        reason_codes.append(f"{name}_future_feature_date")
        manifest_status = "BLOCK"
    return {
        **ref,
        "role": name,
        "logical_source_identity": str(source.get("logical_source_identity") or name),
        "status": manifest_status,
        "business_date": payload_date,
        "feature_date": feature_date,
        "business_date_valid": business_date_valid,
        "latest_fallback_used": False,
        "current_state_leakage_detected": False,
        "pit_status": str(source.get("pit_status") or ""),
        "coverage_status": str(source.get("coverage_status") or ""),
        "reason_codes": sorted(set(reason_codes)),
    }


def _classify_reason(reason: str) -> str:
    lowered = reason.lower()
    if "_block:" in lowered or "source_blocked" in lowered or "block:" in lowered:
        return "UPSTREAM_BLOCK_PROPAGATION"
    if "future" in lowered or "after_business_date" in lowered or "future_source_date_detected" in lowered:
        return "DIRECT_SOURCE_PIT_VIOLATION"
    if "feature_date" in lowered and ("mismatch" in lowered or "authority" in lowered):
        return "TEMPORAL_AUTHORITY_MISMATCH"
    if "configured_max_position_weight_above_safety_cap" in lowered or "legacy_0_20" in lowered or "safety_contract" in lowered:
        return "CONFIG_SAFETY_CONTRACT_VIOLATION"
    if "coverage" in lowered or "source_partial" in lowered or "not_implemented_or_missing" in lowered:
        return "SOURCE_COVERAGE_INCOMPLETE"
    if "review_required" in lowered or "not_eligible" in lowered or "runtime_consumer" in lowered or "draft" in lowered:
        return "DOWNSTREAM_COMPONENT_REVIEW_REQUIRED"
    if "missing" in lowered or "source_unavailable" in lowered or "no_source" in lowered:
        return "DIRECT_SOURCE_MISSING"
    if "schema" in lowered or "required_column" in lowered:
        return "SCHEMA_INCOMPATIBILITY"
    if "lineage" in lowered or "hash_mismatch" in lowered:
        return "LINEAGE_MISMATCH"
    if "business_date" in lowered or "incompatible_date" in lowered:
        return "BUSINESS_DATE_MISMATCH"
    if "latest" in lowered or "fallback" in lowered:
        return "LATEST_ARTIFACT_FALLBACK"
    if "bootstrap" in lowered or "insufficient_history" in lowered or "insufficient_lookback" in lowered:
        return "BOOTSTRAP_CONTRACT_GAP"
    return "OTHER"


def _primary_blocker_class(*, reason_codes: list[str], direct_classes: list[str], status: str) -> str:
    if not direct_classes:
        return "OTHER" if status == "BLOCK" else ""
    priority = [
        "DIRECT_SOURCE_PIT_VIOLATION",
        "TEMPORAL_AUTHORITY_MISMATCH",
        "CONFIG_SAFETY_CONTRACT_VIOLATION",
        "SCHEMA_INCOMPATIBILITY",
        "LINEAGE_MISMATCH",
        "DIRECT_SOURCE_MISSING",
        "SOURCE_COVERAGE_INCOMPLETE",
        "ARTIFACT_ACCEPTANCE_NOT_ELIGIBLE",
        "DOWNSTREAM_COMPONENT_REVIEW_REQUIRED",
        "BUSINESS_DATE_MISMATCH",
        "CURRENT_STATE_LEAKAGE",
        "LATEST_ARTIFACT_FALLBACK",
        "BOOTSTRAP_CONTRACT_GAP",
        "RESOLVER_BUG",
        "TEST_ROOT_CONTAMINATION",
        "OTHER",
    ]
    for item in priority:
        if item in direct_classes:
            return item
    return direct_classes[0]


def _primary_reason_code(*, reason_codes: list[str], primary_class: str) -> str:
    if not reason_codes:
        return primary_class
    for code in sorted(reason_codes):
        if _classify_reason(code) == primary_class:
            return code
    return sorted(reason_codes)[0]


def root_blocker_counts(summary: Mapping[str, Any]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    daily = summary.get("daily_summaries") if isinstance(summary.get("daily_summaries"), list) else []
    for item in daily:
        if not isinstance(item, Mapping):
            continue
        for component in item.get("root_blocker_components", []) or []:
            counter[str(component)] += 1
    return dict(sorted(counter.items()))


def _source_ref(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": _file_hash(path),
    }


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


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
