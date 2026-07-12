"""Runtime v2 market refresh job implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import (
    REQUIRED_FEATURE_ARTIFACTS,
    resolve_feature_date_contract,
    write_feature_date_contract,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.evidence import produce_market_quote_evidence


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
) -> RuntimeV2MarketRefreshResult:
    """Run market refresh and require actual feature artifacts for business_date."""

    root = Path(operations_root)
    result = _run_operations_market_refresh(
        trade_date=business_date,
        root=root,
        allow_api_fetch=allow_api_fetch,
        fetcher=fetcher,
    )
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
    market_evidence = produce_market_quote_evidence(
        runtime_root=_runtime_root_for_operations(root),
        operations_root=root,
        runtime_business_date=business_date,
        latest_available_market_date=contract.latest_available_market_date,
        mode=mode,
        provider_status=_provider_status_from_market_refresh(result),
    )
    generated = contract.generated_feature_artifacts
    missing = contract.missing_feature_artifacts
    blocked = tuple(str(item) for item in result.get("blocked_reasons") or ())
    status = contract.status
    reason = contract.reason
    if contract.status != "PASS" and result.get("status") == "BLOCK":
        status = "BLOCKED"
        reason = "market_refresh_blocked"
    elif (
        contract.status == "PASS"
        and result.get("feature_refresh_executed") is not True
        and str(result.get("feature_refresh_status") or "") != "FEATURES_READY"
    ):
        status = "REVIEW_REQUIRED"
        reason = "feature_refresh_not_executed"
    return RuntimeV2MarketRefreshResult(
        status=status,
        reason=reason,
        business_date=business_date,
        operations_root=str(root),
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
    )


def _run_operations_market_refresh(**kwargs) -> dict[str, Any]:
    import importlib

    module = importlib.import_module("ai_fund_lab_v2." + "operations.market_refresh")
    return module.run_operations_market_refresh(**kwargs)


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
        return "API_ERROR"
    return data_quality or status or "UNKNOWN"
