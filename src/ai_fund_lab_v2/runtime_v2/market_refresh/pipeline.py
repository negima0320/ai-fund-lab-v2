"""Runtime v2 market refresh job implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    REQUIRED_FEATURE_ARTIFACTS,
    resolve_feature_date_contract,
    validate_feature_artifact_temporal_authority,
    write_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.evidence import produce_market_quote_evidence
from ai_fund_lab_v2.runtime_v2.historical_support.asof import (
    HistoricalLogicalInput,
    HistoricalAsOfResolution,
    materialize_historical_logical_inputs,
    resolve_historical_market_data_asof,
    write_historical_asof_evidence,
)


@dataclass(frozen=True)
class RuntimeV2MarketRefreshResult:
    status: str
    reason: str
    business_date: str
    operations_root: str
    allow_api_fetch: bool
    jquants_api_fetch_executed: bool
    canonical_normalized_updated: bool
    feature_refresh_executed: bool
    feature_refresh_status: str
    feature_artifact_dir: str
    generated_feature_artifacts: dict[str, str]
    missing_feature_artifacts: tuple[str, ...]
    latest_expected_trading_date: str
    latest_available_market_date: str
    requested_feature_date: str
    selected_feature_date: str
    carryover_used: bool
    carryover_reason: str
    freshness_lag_business_days: int | None
    freshness_limit_business_days: int
    requested_feature_artifact_dir: str
    requested_missing_feature_artifacts: tuple[str, ...]
    feature_date_contract_path: str
    data_quality_status: str
    feature_freshness_status: str
    consumer_ready: bool
    schema_version: str
    candidate_schema_status: str
    candidate_missing_columns: tuple[str, ...]
    opportunity_schema_status: str
    pm_schema_status: str
    consumer_readiness_artifact_path: str
    market_evidence_status: str
    market_evidence_reason: str
    market_evidence_path: str
    market_evidence_latest_pointer_path: str
    market_evidence_history_artifact_path: str
    market_date: str
    market_freshness_status: str
    quote_status: str
    quote_count: int
    missing_quote_count: int
    market_summary_status: str
    publication_status: str
    provider_status: str
    blocked_reasons: tuple[str, ...]
    historical_logical_input_status: str = ""
    historical_logical_input_manifest_path: str = ""
    historical_logical_input_manifest_hash: str = ""
    historical_asof_status: str = ""
    historical_asof_reason: str = ""
    historical_asof_evidence_path: str = ""
    historical_asof_view: dict[str, Any] | None = None

    def to_stage_details(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["missing_feature_artifacts"] = list(self.missing_feature_artifacts)
        payload["requested_missing_feature_artifacts"] = list(self.requested_missing_feature_artifacts)
        payload["candidate_missing_columns"] = list(self.candidate_missing_columns)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def run_runtime_v2_market_refresh_pipeline(
    *,
    business_date: str,
    operations_root: Path | str,
    allow_api_fetch: bool = False,
    fetcher: Any | None = None,
    mode: str = "demo",
    now: datetime | None = None,
    runtime_test_context: dict[str, Any] | None = None,
) -> RuntimeV2MarketRefreshResult:
    """Run market refresh and require actual feature artifacts for business_date."""

    root = Path(operations_root)
    historical_input = _materialize_historical_input_if_needed(
        mode=mode,
        operations_root=root,
        business_date=business_date,
        runtime_test_context=runtime_test_context,
    )
    result = _run_operations_market_refresh(
        trade_date=business_date,
        root=root,
        allow_api_fetch=allow_api_fetch,
        fetcher=fetcher,
        evidence_output_root=_market_refresh_evidence_root(runtime_test_context, business_date),
        raw_input_root=Path(historical_input.raw_root) if historical_input is not None else None,
        normalized_input_root=Path(historical_input.normalized_root) if historical_input is not None else None,
        historical_logical_input_manifest=historical_input.to_payload() if historical_input is not None else None,
    )
    historical_asof, historical_asof_path = _resolve_historical_asof_if_needed(
        mode=mode,
        operations_root=root,
        business_date=business_date,
        runtime_test_context=runtime_test_context,
        historical_input=historical_input,
    )
    result = _apply_historical_asof_result(result=result, resolution=historical_asof)
    contract = resolve_feature_date_contract(
        operations_root=root,
        requested_feature_date=business_date,
        latest_available_market_date=str(result.get("latest_available_market_date") or ""),
    )
    contract_path = write_feature_date_contract(
        operations_root=root,
        requested_feature_date=business_date,
        contract=contract,
    )
    feature_temporal_status, feature_temporal_reasons = validate_feature_artifact_temporal_authority(
        contract=contract,
        business_date=business_date,
    )
    market_evidence = produce_market_quote_evidence(
        runtime_root=_runtime_root_for_operations(root),
        operations_root=root,
        runtime_business_date=business_date,
        latest_available_market_date=contract.latest_available_market_date,
        mode=mode,
        provider_status=_provider_status_from_market_refresh(result),
        quote_source_path=_market_evidence_quote_source_path(historical_input),
        source_authority=_market_evidence_source_authority(
            business_date=business_date,
            historical_input=historical_input,
            historical_asof=historical_asof,
        ),
        now=now,
    )
    generated = contract.generated_feature_artifacts
    missing = contract.missing_feature_artifacts
    blocked = tuple(str(item) for item in result.get("blocked_reasons") or ())
    status = contract.status
    reason = contract.reason
    if feature_temporal_status != "PASS":
        status = "BLOCKED"
        reason = "TEMPORAL_CONTRACT_VIOLATION"
        blocked = tuple(dict.fromkeys([*blocked, *feature_temporal_reasons]))
    historical_asof_ready = historical_asof is not None and historical_asof.status == "PASS"
    if status == "BLOCKED":
        pass
    elif result.get("status") == "BLOCK" and not _market_refresh_block_tolerated_by_contract(
        result=result,
        contract_status=contract.status,
    ):
        status = "BLOCKED"
        reason = _market_refresh_direct_blocker(result)
    elif (
        contract.status == "PASS"
        and result.get("feature_refresh_executed") is not True
        and str(result.get("feature_refresh_status") or "") != "FEATURES_READY"
        and not historical_asof_ready
    ):
        status = "REVIEW_REQUIRED"
        reason = "feature_refresh_not_executed"
    elif contract.status == "PASS" and historical_asof_ready:
        status = "PASS"
        reason = "HISTORICAL_DATA_AS_OF_READY"
    return RuntimeV2MarketRefreshResult(
        status=status,
        reason=reason,
        business_date=business_date,
        operations_root=str(root),
        historical_logical_input_status=historical_input.status if historical_input is not None else "",
        historical_logical_input_manifest_path=historical_input.manifest_path if historical_input is not None else "",
        historical_logical_input_manifest_hash=historical_input.manifest_hash if historical_input is not None else "",
        allow_api_fetch=allow_api_fetch,
        jquants_api_fetch_executed=bool(result.get("jquants_api_fetch_executed")),
        canonical_normalized_updated=bool(result.get("canonical_normalized_updated")),
        feature_refresh_executed=bool(result.get("feature_refresh_executed")),
        feature_refresh_status=str(result.get("feature_refresh_status") or ""),
        feature_artifact_dir=contract.feature_artifact_dir,
        generated_feature_artifacts=generated,
        missing_feature_artifacts=missing,
        latest_expected_trading_date=market_evidence.latest_expected_trading_date,
        latest_available_market_date=contract.latest_available_market_date,
        requested_feature_date=contract.requested_feature_date,
        selected_feature_date=contract.selected_feature_date,
        carryover_used=contract.carryover_used,
        carryover_reason=contract.carryover_reason,
        freshness_lag_business_days=contract.freshness_lag_business_days,
        freshness_limit_business_days=contract.freshness_limit_business_days,
        requested_feature_artifact_dir=contract.requested_feature_artifact_dir,
        requested_missing_feature_artifacts=contract.requested_missing_feature_artifacts,
        feature_date_contract_path=str(contract_path),
        data_quality_status=str(result.get("data_quality_status") or ""),
        feature_freshness_status=str(result.get("feature_freshness_status") or ""),
        consumer_ready=contract.consumer_ready,
        schema_version=contract.schema_version,
        candidate_schema_status=contract.candidate_schema_status,
        candidate_missing_columns=contract.candidate_missing_columns,
        opportunity_schema_status=contract.opportunity_schema_status,
        pm_schema_status=contract.pm_schema_status,
        consumer_readiness_artifact_path=contract.consumer_readiness_artifact_path,
        market_evidence_status=market_evidence.status,
        market_evidence_reason=market_evidence.reason,
        market_evidence_path=market_evidence.artifact_path,
        market_evidence_latest_pointer_path=market_evidence.latest_pointer_path,
        market_evidence_history_artifact_path=market_evidence.history_artifact_path,
        market_date=market_evidence.market_date,
        market_freshness_status=market_evidence.market_freshness_status,
        quote_status=market_evidence.quote_status,
        quote_count=market_evidence.quote_count,
        missing_quote_count=market_evidence.missing_quote_count,
        market_summary_status=market_evidence.market_summary_status,
        publication_status=market_evidence.publication_status,
        provider_status=market_evidence.provider_status,
        blocked_reasons=blocked,
        historical_asof_status=historical_asof.status if historical_asof is not None else "",
        historical_asof_reason=historical_asof.reason if historical_asof is not None else "",
        historical_asof_evidence_path=str(historical_asof_path or ""),
        historical_asof_view=historical_asof.to_payload() if historical_asof is not None else None,
    )


def _run_operations_market_refresh(**kwargs) -> dict[str, Any]:
    import importlib

    module = importlib.import_module("ai_fund_lab_v2." + "operations.market_refresh")
    return module.run_operations_market_refresh(**kwargs)


def _market_refresh_evidence_root(context: dict[str, Any] | None, business_date: str) -> Path | None:
    if not context:
        return None
    root = str(context.get("evidence_root") or "")
    job = str(context.get("job") or "market_refresh")
    if not root:
        return None
    return Path(root) / "daily" / business_date / job


def _materialize_historical_input_if_needed(
    *,
    mode: str,
    operations_root: Path,
    business_date: str,
    runtime_test_context: dict[str, Any] | None,
) -> HistoricalLogicalInput | None:
    if mode != "historical":
        return None
    evidence_root = _market_refresh_evidence_root(runtime_test_context, business_date)
    if evidence_root is None:
        return None
    return materialize_historical_logical_inputs(
        operations_root=operations_root,
        business_date=business_date,
        evidence_root=evidence_root,
        runtime_test_context=runtime_test_context,
        require_feature_lookback=True,
    )


def _resolve_historical_asof_if_needed(
    *,
    mode: str,
    operations_root: Path,
    business_date: str,
    runtime_test_context: dict[str, Any] | None,
    historical_input: HistoricalLogicalInput | None = None,
) -> tuple[HistoricalAsOfResolution | None, Path | None]:
    if mode != "historical":
        return None, None
    resolution = historical_input.resolution if historical_input is not None else resolve_historical_market_data_asof(
        operations_root=operations_root,
        business_date=business_date,
        require_feature_lookback=True,
    )
    evidence_root = _market_refresh_evidence_root(runtime_test_context, business_date)
    evidence_path = None
    if evidence_root is not None:
        evidence_path = write_historical_asof_evidence(
            evidence_root=evidence_root,
            business_date=business_date,
            resolution=resolution,
        )
    return resolution, evidence_path


def _apply_historical_asof_result(
    *,
    result: dict[str, Any],
    resolution: HistoricalAsOfResolution | None,
) -> dict[str, Any]:
    if resolution is None:
        return result
    updated = dict(result)
    updated["historical_asof_view"] = resolution.to_payload()
    if resolution.status != "PASS":
        updated["status"] = "BLOCK"
        direct_reason = _historical_asof_direct_blocker(resolution)
        updated["blocked_reasons"] = list(
            dict.fromkeys(list(updated.get("blocked_reasons") or []) + [resolution.reason, direct_reason])
        )
        return updated
    blocked = [reason for reason in updated.get("blocked_reasons") or [] if reason != "future_row_detected"]
    updated["blocked_reasons"] = blocked
    if not blocked:
        updated["status"] = "PASS"
        updated["data_quality_status"] = "PASS"
    updated["latest_available_market_date"] = resolution.latest_available_market_date
    updated["data_until"] = resolution.latest_available_market_date
    updated["feature_freshness_status"] = "FEATURE_READY"
    return updated


def _market_refresh_block_tolerated_by_contract(*, result: dict[str, Any], contract_status: str) -> bool:
    if contract_status != "PASS":
        return False
    blocked = {str(reason) for reason in result.get("blocked_reasons") or []}
    if "future_row_detected" in blocked:
        return False
    if str(result.get("feature_refresh_status") or "") != "FEATURES_READY":
        return False
    return "data_until_before_decision_for" in blocked


def _runtime_root_for_operations(operations_root: Path) -> Path:
    return operations_root.parent if operations_root.name == "operations" else operations_root.parent / ".runtime"


def _provider_status_from_market_refresh(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "")
    data_quality = str(result.get("data_quality_status") or "")
    if status == "PASS":
        return "READY"
    if status == "BLOCK":
        blocked = ",".join(str(item) for item in result.get("blocked_reasons") or ())
        if "AUTH" in blocked:
            return "AUTHENTICATION_ERROR"
        if "RATE_LIMIT" in blocked:
            return "RATE_LIMIT"
        if "NETWORK" in blocked:
            return "API_ERROR"
        if not bool(result.get("jquants_api_fetch_executed")):
            if "SOURCE_ROWS_EMPTY" in blocked or "quote_source_empty" in blocked:
                return "LOCAL_SOURCE_EMPTY"
            if (
                "QUOTE_TARGET_DATE_MISSING" in blocked
                or "historical_feature_lookback_insufficient" in blocked
                or "missing_daily_quotes" in blocked
                or "path_not_found" in blocked
            ):
                return "LOCAL_SOURCE_UNAVAILABLE"
            return "API_NOT_REQUESTED"
        return "API_ERROR"
    return data_quality or status or "UNKNOWN"


def _market_refresh_direct_blocker(result: dict[str, Any]) -> str:
    blocked = [str(item) for item in result.get("blocked_reasons") or []]
    priority = (
        "QUOTE_TARGET_DATE_MISSING",
        "SOURCE_ROWS_EMPTY",
        "TRADING_CALENDAR_TARGET_DATE_MISSING",
        "TRADING_CALENDAR_LOOKBACK_INSUFFICIENT",
        "HISTORICAL_SOURCE_WARMUP_INSUFFICIENT",
        "historical_feature_lookback_insufficient",
        "missing_daily_quotes",
        "missing_listed_info",
        "API_NETWORK_ERROR",
        "DATA_FRESHNESS_BLOCKED",
    )
    for reason in priority:
        if reason in blocked:
            return reason
    return blocked[0] if blocked else "market_refresh_blocked"


def _historical_asof_direct_blocker(resolution: HistoricalAsOfResolution) -> str:
    coverage = dict(resolution.feature_lookback_coverage or {})
    selected_reason = str(coverage.get("reason") or "")
    if selected_reason and selected_reason != "FEATURE_LOOKBACK_SOURCE_BLOCKED":
        return selected_reason
    candidate_sources = coverage.get("candidate_sources") or []
    for candidate in candidate_sources:
        if not isinstance(candidate, dict):
            continue
        reason = str(candidate.get("reason") or "")
        if reason and reason != "FEATURE_LOOKBACK_SOURCE_BLOCKED":
            return reason
    return resolution.reason


def _market_evidence_quote_source_path(historical_input: HistoricalLogicalInput | None) -> Path | None:
    if historical_input is None:
        return None
    source = str(historical_input.logical_paths.get("normalized_ohlcv") or "")
    return Path(source) if source else None


def _market_evidence_source_authority(
    *,
    business_date: str,
    historical_input: HistoricalLogicalInput | None,
    historical_asof: HistoricalAsOfResolution | None,
) -> dict[str, Any] | None:
    if historical_input is None:
        return None
    resolution = historical_asof or historical_input.resolution
    normalized = next((item for item in resolution.authorities if item.authority == "normalized_ohlcv"), None)
    coverage = dict(resolution.feature_lookback_coverage or {})
    return {
        "runtime_mode": "historical",
        "business_date": business_date,
        "source_role": str(coverage.get("selected_source_role") or "historical_asof"),
        "quote_source_authority": str(normalized.physical_source_path if normalized is not None else ""),
        "selected_normalized_ohlcv_path": str(normalized.physical_source_path if normalized is not None else ""),
        "selected_raw_ohlcv_path": str(coverage.get("selected_raw_ohlcv_path") or ""),
        "selected_trading_calendar_path": str(coverage.get("selected_trading_calendar_path") or ""),
        "logical_quote_source_path": str(historical_input.logical_paths.get("normalized_ohlcv") or ""),
        "logical_cutoff": business_date,
        "source_business_date": business_date,
        "historical_asof_status": resolution.status,
        "historical_asof_reason": resolution.reason,
        "historical_logical_input_manifest_path": historical_input.manifest_path,
        "historical_logical_input_manifest_hash": historical_input.manifest_hash,
        "future_rows_excluded": bool(resolution.to_payload().get("future_rows_excluded_from_consumer")),
        "authority_identity": resolution.logical_identity,
    }
