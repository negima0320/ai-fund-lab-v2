from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_fund_lab_v2.strategy import corporate_event, market_context
from ai_fund_lab_v2.strategy.status_contract import (
    SOURCE_LIFECYCLE_DRAFT,
    SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE,
)


SCHEMA_VERSION = "phase22_b_candidate_opportunity_compatibility.v1"

COMPATIBLE_NOT_CONNECTED = "COMPATIBLE_NOT_CONNECTED"
INCOMPATIBLE_SCHEMA = "INCOMPATIBLE_SCHEMA"
INCOMPATIBLE_DATE = "INCOMPATIBLE_DATE"
INCOMPATIBLE_HASH = "INCOMPATIBLE_HASH"
SOURCE_REVIEW_REQUIRED = "SOURCE_REVIEW_REQUIRED"
SOURCE_BLOCKED = "SOURCE_BLOCKED"
SOURCE_NOT_ELIGIBLE = "SOURCE_NOT_ELIGIBLE"
SOURCE_MISSING = "SOURCE_MISSING"
AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"

SUPPORTED_MARKET_CONTEXT_SCHEMA_VERSION = market_context.SCHEMA_VERSION
SUPPORTED_CORPORATE_EVENT_SCHEMA_VERSION = corporate_event.SCHEMA_VERSION


@dataclass(frozen=True)
class ArtifactCompatibilityResult:
    artifact_kind: str
    status: str
    schema_compatible: bool
    shadow_read_allowed: bool
    production_decision_allowed: bool
    business_date_aligned: bool
    feature_date_point_in_time: bool
    artifact_hash_valid: bool
    source_lineage_valid: bool
    source_hashes_valid: bool
    lifecycle_status: str
    producer_result_status: str
    runtime_consumer_eligibility: str
    reason_codes: tuple[str, ...]
    artifact_path: str = ""
    schema_version: str = ""
    business_date: str = ""
    feature_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "artifact_path": self.artifact_path,
            "schema_version": self.schema_version,
            "status": self.status,
            "schema_compatible": self.schema_compatible,
            "shadow_read_allowed": self.shadow_read_allowed,
            "production_decision_allowed": self.production_decision_allowed,
            "business_date": self.business_date,
            "feature_date": self.feature_date,
            "business_date_aligned": self.business_date_aligned,
            "feature_date_point_in_time": self.feature_date_point_in_time,
            "artifact_hash_valid": self.artifact_hash_valid,
            "source_lineage_valid": self.source_lineage_valid,
            "source_hashes_valid": self.source_hashes_valid,
            "lifecycle_status": self.lifecycle_status,
            "producer_result_status": self.producer_result_status,
            "runtime_consumer_eligibility": self.runtime_consumer_eligibility,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class CandidateCompatibilityResult:
    status: str
    business_date: str
    output_preserved: bool
    behavior_changed: bool
    candidate_count: int
    security_codes_preserved: bool
    order_preserved: bool
    eligibility_preserved: bool
    reason_codes_preserved: bool
    input_hash: str
    output_hash: str
    artifacts: tuple[ArtifactCompatibilityResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "component": "Candidate",
            "status": self.status,
            "business_date": self.business_date,
            "output_preserved": self.output_preserved,
            "behavior_changed": self.behavior_changed,
            "candidate_count": self.candidate_count,
            "security_codes_preserved": self.security_codes_preserved,
            "order_preserved": self.order_preserved,
            "eligibility_preserved": self.eligibility_preserved,
            "reason_codes_preserved": self.reason_codes_preserved,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "production_consumer_connected": False,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


@dataclass(frozen=True)
class OpportunityCompatibilityResult:
    status: str
    business_date: str
    output_preserved: bool
    behavior_changed: bool
    ranking_changed: bool
    opportunity_count: int
    security_codes_preserved: bool
    score_preserved: bool
    rank_preserved: bool
    feature_vector_preserved: bool
    tie_break_preserved: bool
    input_hash: str
    output_hash: str
    artifacts: tuple[ArtifactCompatibilityResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "component": "Opportunity",
            "status": self.status,
            "business_date": self.business_date,
            "output_preserved": self.output_preserved,
            "behavior_changed": self.behavior_changed,
            "ranking_changed": self.ranking_changed,
            "opportunity_count": self.opportunity_count,
            "security_codes_preserved": self.security_codes_preserved,
            "score_preserved": self.score_preserved,
            "rank_preserved": self.rank_preserved,
            "feature_vector_preserved": self.feature_vector_preserved,
            "tie_break_preserved": self.tie_break_preserved,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "production_consumer_connected": False,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


def validate_market_context_compatibility(
    path: Path | str | None,
    *,
    requested_business_date: str,
    production_use_requested: bool = False,
) -> ArtifactCompatibilityResult:
    if path is None:
        return _missing_result("market_context", requested_business_date=requested_business_date)
    return _validate_artifact(
        kind="market_context",
        path=Path(path),
        requested_business_date=requested_business_date,
        expected_schema_version=SUPPORTED_MARKET_CONTEXT_SCHEMA_VERSION,
        validate_payload=market_context.validate_market_context_artifact,
        calculate_hash=market_context.market_context_hash,
        verify_hashes=market_context.verify_source_hashes,
        production_use_requested=production_use_requested,
    )


def validate_corporate_event_compatibility(
    path: Path | str | None,
    *,
    requested_business_date: str,
    production_use_requested: bool = False,
) -> ArtifactCompatibilityResult:
    if path is None:
        return _missing_result("corporate_event", requested_business_date=requested_business_date)
    return _validate_artifact(
        kind="corporate_event",
        path=Path(path),
        requested_business_date=requested_business_date,
        expected_schema_version=SUPPORTED_CORPORATE_EVENT_SCHEMA_VERSION,
        validate_payload=corporate_event.validate_corporate_event_artifact,
        calculate_hash=corporate_event.corporate_event_hash,
        verify_hashes=corporate_event.verify_source_hashes,
        production_use_requested=production_use_requested,
    )


def build_candidate_compatibility_adapter(
    candidate_rows: Iterable[Mapping[str, Any]],
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None = None,
    corporate_event_artifact_path: Path | str | None = None,
    production_use_requested: bool = False,
) -> tuple[list[dict[str, Any]], CandidateCompatibilityResult]:
    before = _rows(candidate_rows)
    output = copy.deepcopy(before)
    artifacts = _validate_pair(
        business_date=business_date,
        market_context_artifact_path=market_context_artifact_path,
        corporate_event_artifact_path=corporate_event_artifact_path,
        production_use_requested=production_use_requested,
    )
    input_hash = stable_payload_hash(before)
    output_hash = stable_payload_hash(output)
    security_codes_preserved = _column_values(before, "code") == _column_values(output, "code")
    order_preserved = before == output
    eligibility_preserved = _column_values(before, "universe_eligible") == _column_values(output, "universe_eligible")
    reason_codes_preserved = _candidate_reason_values(before) == _candidate_reason_values(output)
    output_preserved = input_hash == output_hash
    return output, CandidateCompatibilityResult(
        status=_combined_status(artifacts),
        business_date=business_date,
        output_preserved=output_preserved,
        behavior_changed=not output_preserved,
        candidate_count=len(output),
        security_codes_preserved=security_codes_preserved,
        order_preserved=order_preserved,
        eligibility_preserved=eligibility_preserved,
        reason_codes_preserved=reason_codes_preserved,
        input_hash=input_hash,
        output_hash=output_hash,
        artifacts=artifacts,
    )


def build_opportunity_compatibility_adapter(
    opportunity_rows: Iterable[Mapping[str, Any]],
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None = None,
    corporate_event_artifact_path: Path | str | None = None,
    production_use_requested: bool = False,
) -> tuple[list[dict[str, Any]], OpportunityCompatibilityResult]:
    before = _rows(opportunity_rows)
    output = copy.deepcopy(before)
    artifacts = _validate_pair(
        business_date=business_date,
        market_context_artifact_path=market_context_artifact_path,
        corporate_event_artifact_path=corporate_event_artifact_path,
        production_use_requested=production_use_requested,
    )
    input_hash = stable_payload_hash(before)
    output_hash = stable_payload_hash(output)
    security_codes_preserved = _column_values(before, "code") == _column_values(output, "code")
    score_preserved = _column_values(before, "expected_edge_score") == _column_values(output, "expected_edge_score")
    rank_preserved = _rank_values(before) == _rank_values(output)
    feature_vector_preserved = _feature_vectors(before) == _feature_vectors(output)
    tie_break_preserved = _tie_break_values(before) == _tie_break_values(output)
    output_preserved = input_hash == output_hash
    ranking_changed = not (rank_preserved and tie_break_preserved)
    return output, OpportunityCompatibilityResult(
        status=_combined_status(artifacts),
        business_date=business_date,
        output_preserved=output_preserved,
        behavior_changed=not output_preserved,
        ranking_changed=ranking_changed,
        opportunity_count=len(output),
        security_codes_preserved=security_codes_preserved,
        score_preserved=score_preserved,
        rank_preserved=rank_preserved,
        feature_vector_preserved=feature_vector_preserved,
        tie_break_preserved=tie_break_preserved,
        input_hash=input_hash,
        output_hash=output_hash,
        artifacts=artifacts,
    )


def produced_compatible_not_consumed_evidence(
    *,
    candidate_result: CandidateCompatibilityResult,
    opportunity_result: OpportunityCompatibilityResult,
) -> dict[str, Any]:
    all_artifacts = [*candidate_result.artifacts, *opportunity_result.artifacts]
    market_results = [artifact for artifact in all_artifacts if artifact.artifact_kind == "market_context"]
    corporate_results = [artifact for artifact in all_artifacts if artifact.artifact_kind == "corporate_event"]
    return {
        "schema_version": "phase22_b_produced_compatible_not_consumed_validation.v1",
        "market_context_artifact_produced": any(result.status != SOURCE_MISSING for result in market_results),
        "corporate_event_artifact_produced": any(result.status != SOURCE_MISSING for result in corporate_results),
        "candidate_schema_compatible": all(result.schema_compatible for result in candidate_result.artifacts),
        "opportunity_schema_compatible": all(result.schema_compatible for result in opportunity_result.artifacts),
        "candidate_production_consumer_connected": False,
        "opportunity_production_consumer_connected": False,
        "candidate_behavior_changed": candidate_result.behavior_changed,
        "opportunity_behavior_changed": opportunity_result.behavior_changed,
        "ranking_changed": opportunity_result.ranking_changed,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
        "production_decision_allowed": any(result.production_decision_allowed for result in all_artifacts),
        "status": (
            "PASS"
            if not candidate_result.behavior_changed
            and not opportunity_result.behavior_changed
            and not opportunity_result.ranking_changed
            and not any(result.production_decision_allowed for result in all_artifacts)
            else "BLOCK"
        ),
    }


def stable_payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_pair(
    *,
    business_date: str,
    market_context_artifact_path: Path | str | None,
    corporate_event_artifact_path: Path | str | None,
    production_use_requested: bool,
) -> tuple[ArtifactCompatibilityResult, ArtifactCompatibilityResult]:
    market_result = validate_market_context_compatibility(
        market_context_artifact_path,
        requested_business_date=business_date,
        production_use_requested=production_use_requested,
    )
    corporate_result = validate_corporate_event_compatibility(
        corporate_event_artifact_path,
        requested_business_date=business_date,
        production_use_requested=production_use_requested,
    )
    if (
        market_result.status != SOURCE_MISSING
        and corporate_result.status != SOURCE_MISSING
        and market_result.business_date
        and corporate_result.business_date
        and market_result.business_date != corporate_result.business_date
    ):
        market_result = _with_status(market_result, INCOMPATIBLE_DATE, "cross_artifact_business_date_mismatch")
        corporate_result = _with_status(corporate_result, INCOMPATIBLE_DATE, "cross_artifact_business_date_mismatch")
    return (market_result, corporate_result)


def _validate_artifact(
    *,
    kind: str,
    path: Path,
    requested_business_date: str,
    expected_schema_version: str,
    validate_payload: Any,
    calculate_hash: Any,
    verify_hashes: Any,
    production_use_requested: bool,
) -> ArtifactCompatibilityResult:
    if not path.is_file():
        return _missing_result(kind, requested_business_date=requested_business_date, artifact_path=str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _schema_result(kind, path, requested_business_date, (f"invalid_json:{type(exc).__name__}",))
    schema_version = str(payload.get("schema_version") or "")
    try:
        validate_payload(payload)
    except Exception as exc:
        return _schema_result(kind, path, requested_business_date, (f"schema_validation_failed:{exc}",), payload=payload)
    if schema_version != expected_schema_version:
        return _schema_result(kind, path, requested_business_date, ("unsupported_schema_version",), payload=payload)

    business_date = str(payload.get("business_date") or "")
    feature_date = str(payload.get("feature_date") or "")
    date_ok = business_date == requested_business_date and bool(feature_date) and feature_date <= business_date
    temporal = payload.get("temporal_safety") if isinstance(payload.get("temporal_safety"), dict) else {}
    pit_ok = date_ok and temporal.get("future_leakage_used") is not True and temporal.get("feature_date_lte_business_date") is not False
    expected_artifact_hash = str(payload.get("artifact_hash") or "")
    actual_artifact_hash = str(calculate_hash(payload))
    artifact_hash_valid = bool(expected_artifact_hash) and expected_artifact_hash == actual_artifact_hash
    source_artifacts = payload.get("source_artifacts")
    source_hashes = payload.get("source_hashes")
    source_lineage_valid = isinstance(source_artifacts, list) and bool(source_artifacts) and isinstance(source_hashes, list) and bool(source_hashes)
    source_hash_result = verify_hashes(payload) if source_lineage_valid else {"status": "REVIEW_REQUIRED", "reason": "source_lineage_missing"}
    source_hashes_valid = source_hash_result.get("status") == "PASS"

    lifecycle_status = str(payload.get("artifact_lifecycle_status") or "")
    producer_result_status = str(payload.get("producer_result_status") or "")
    runtime_consumer_eligibility = str(payload.get("runtime_consumer_eligibility") or "")
    production_decision_allowed = (
        lifecycle_status == "ACCEPTED"
        and producer_result_status == "PASS"
        and runtime_consumer_eligibility == "ELIGIBLE"
        and not production_use_requested
    )
    reasons = [str(reason) for reason in payload.get("reason_codes") or []]
    if production_use_requested and not production_decision_allowed:
        reasons.append("production_use_rejected")

    status = COMPATIBLE_NOT_CONNECTED
    if not date_ok or not pit_ok:
        status = INCOMPATIBLE_DATE
    elif not artifact_hash_valid:
        status = INCOMPATIBLE_HASH
    elif not source_lineage_valid:
        status = SOURCE_REVIEW_REQUIRED
    elif source_hash_result.get("status") == "BLOCK":
        status = SOURCE_BLOCKED
    elif source_hash_result.get("status") == "REVIEW_REQUIRED":
        status = SOURCE_REVIEW_REQUIRED
    elif payload.get("source_authority_status") == "AUTHORITY_CONFLICT":
        status = AUTHORITY_CONFLICT
    elif producer_result_status == "BLOCK" or runtime_consumer_eligibility == "BLOCKED":
        status = SOURCE_BLOCKED
    elif producer_result_status == "REVIEW_REQUIRED":
        status = SOURCE_REVIEW_REQUIRED
    elif runtime_consumer_eligibility == "NOT_ELIGIBLE":
        reasons.extend([SOURCE_LIFECYCLE_DRAFT, SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE])

    return ArtifactCompatibilityResult(
        artifact_kind=kind,
        artifact_path=str(path),
        schema_version=schema_version,
        status=status,
        schema_compatible=True,
        shadow_read_allowed=status in {COMPATIBLE_NOT_CONNECTED, SOURCE_NOT_ELIGIBLE, SOURCE_REVIEW_REQUIRED},
        production_decision_allowed=production_decision_allowed,
        business_date=business_date,
        feature_date=feature_date,
        business_date_aligned=date_ok,
        feature_date_point_in_time=pit_ok,
        artifact_hash_valid=artifact_hash_valid,
        source_lineage_valid=source_lineage_valid,
        source_hashes_valid=source_hashes_valid,
        lifecycle_status=lifecycle_status,
        producer_result_status=producer_result_status,
        runtime_consumer_eligibility=runtime_consumer_eligibility,
        reason_codes=tuple(sorted(set(reasons))),
    )


def _missing_result(kind: str, *, requested_business_date: str, artifact_path: str = "") -> ArtifactCompatibilityResult:
    return ArtifactCompatibilityResult(
        artifact_kind=kind,
        artifact_path=artifact_path,
        schema_version="",
        status=SOURCE_MISSING,
        schema_compatible=False,
        shadow_read_allowed=False,
        production_decision_allowed=False,
        business_date=requested_business_date,
        feature_date="",
        business_date_aligned=False,
        feature_date_point_in_time=False,
        artifact_hash_valid=False,
        source_lineage_valid=False,
        source_hashes_valid=False,
        lifecycle_status="",
        producer_result_status="",
        runtime_consumer_eligibility="",
        reason_codes=("artifact_missing",),
    )


def _schema_result(
    kind: str,
    path: Path,
    requested_business_date: str,
    reasons: tuple[str, ...],
    *,
    payload: dict[str, Any] | None = None,
) -> ArtifactCompatibilityResult:
    payload = payload or {}
    return ArtifactCompatibilityResult(
        artifact_kind=kind,
        artifact_path=str(path),
        schema_version=str(payload.get("schema_version") or ""),
        status=INCOMPATIBLE_SCHEMA,
        schema_compatible=False,
        shadow_read_allowed=False,
        production_decision_allowed=False,
        business_date=str(payload.get("business_date") or requested_business_date),
        feature_date=str(payload.get("feature_date") or ""),
        business_date_aligned=False,
        feature_date_point_in_time=False,
        artifact_hash_valid=False,
        source_lineage_valid=False,
        source_hashes_valid=False,
        lifecycle_status=str(payload.get("artifact_lifecycle_status") or ""),
        producer_result_status=str(payload.get("producer_result_status") or ""),
        runtime_consumer_eligibility=str(payload.get("runtime_consumer_eligibility") or ""),
        reason_codes=reasons,
    )


def _with_status(result: ArtifactCompatibilityResult, status: str, reason: str) -> ArtifactCompatibilityResult:
    return ArtifactCompatibilityResult(
        artifact_kind=result.artifact_kind,
        artifact_path=result.artifact_path,
        schema_version=result.schema_version,
        status=status,
        schema_compatible=result.schema_compatible,
        shadow_read_allowed=False,
        production_decision_allowed=False,
        business_date=result.business_date,
        feature_date=result.feature_date,
        business_date_aligned=False,
        feature_date_point_in_time=result.feature_date_point_in_time,
        artifact_hash_valid=result.artifact_hash_valid,
        source_lineage_valid=result.source_lineage_valid,
        source_hashes_valid=result.source_hashes_valid,
        lifecycle_status=result.lifecycle_status,
        producer_result_status=result.producer_result_status,
        runtime_consumer_eligibility=result.runtime_consumer_eligibility,
        reason_codes=tuple(sorted(set((*result.reason_codes, reason)))),
    )


def _combined_status(artifacts: tuple[ArtifactCompatibilityResult, ...]) -> str:
    blocking = {INCOMPATIBLE_SCHEMA, INCOMPATIBLE_DATE, INCOMPATIBLE_HASH, SOURCE_BLOCKED, SOURCE_MISSING, AUTHORITY_CONFLICT}
    if any(artifact.status in blocking for artifact in artifacts):
        return "BLOCK"
    if any(artifact.status in {SOURCE_NOT_ELIGIBLE, SOURCE_REVIEW_REQUIRED} for artifact in artifacts):
        return COMPATIBLE_NOT_CONNECTED
    return COMPATIBLE_NOT_CONNECTED


def _rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _column_values(rows: list[dict[str, Any]], column: str) -> list[Any]:
    return [row.get(column) for row in rows]


def _candidate_reason_values(rows: list[dict[str, Any]]) -> list[Any]:
    return [row.get("excluded_reason", row.get("reason_codes", row.get("candidate_reason"))) for row in rows]


def _rank_values(rows: list[dict[str, Any]]) -> list[Any]:
    return [row.get("buy_rank", row.get("rank")) for row in rows]


def _feature_vectors(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: value for key, value in row.items() if str(key).startswith("feature__")} for row in rows]


def _tie_break_values(rows: list[dict[str, Any]]) -> list[tuple[Any, Any, Any]]:
    return [(row.get("target_date"), row.get("buy_rank", row.get("rank")), row.get("code")) for row in rows]
