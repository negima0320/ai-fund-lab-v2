from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.strategy import corporate_event, market_context
from ai_fund_lab_v2.strategy.candidate_opportunity_compatibility import (
    COMPATIBLE_NOT_CONNECTED,
    INCOMPATIBLE_DATE,
    INCOMPATIBLE_HASH,
    INCOMPATIBLE_SCHEMA,
    SOURCE_MISSING,
    SOURCE_REVIEW_REQUIRED,
    build_candidate_compatibility_adapter,
    build_opportunity_compatibility_adapter,
    produced_compatible_not_consumed_evidence,
    validate_corporate_event_compatibility,
    validate_market_context_compatibility,
)


def test_phase22_b_supported_strategy_artifacts_are_schema_compatible_but_not_production_inputs(tmp_path: Path) -> None:
    market_path = _write_market_context(tmp_path, producer_status="REVIEW_REQUIRED")
    corporate_path = _write_corporate_event(tmp_path, producer_status="REVIEW_REQUIRED")

    market_result = validate_market_context_compatibility(market_path, requested_business_date="2026-07-15")
    corporate_result = validate_corporate_event_compatibility(corporate_path, requested_business_date="2026-07-15")

    assert market_result.schema_compatible
    assert corporate_result.schema_compatible
    assert market_result.status == SOURCE_REVIEW_REQUIRED
    assert corporate_result.status == SOURCE_REVIEW_REQUIRED
    assert market_result.shadow_read_allowed
    assert corporate_result.shadow_read_allowed
    assert market_result.production_decision_allowed is False
    assert corporate_result.production_decision_allowed is False


def test_phase22_qc_lifecycle_not_eligible_does_not_block_shadow_calculation(tmp_path: Path) -> None:
    market_path = _write_market_context(tmp_path, producer_status="PASS")
    corporate_path = _write_corporate_event(tmp_path, producer_status="PASS")

    market_result = validate_market_context_compatibility(market_path, requested_business_date="2026-07-15")
    corporate_result = validate_corporate_event_compatibility(corporate_path, requested_business_date="2026-07-15")

    assert market_result.status == COMPATIBLE_NOT_CONNECTED
    assert corporate_result.status == COMPATIBLE_NOT_CONNECTED
    assert market_result.shadow_read_allowed is True
    assert corporate_result.shadow_read_allowed is True
    assert market_result.production_decision_allowed is False
    assert corporate_result.production_decision_allowed is False
    assert "SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE" in market_result.reason_codes


def test_phase22_b_unsupported_schema_and_missing_required_field_fail_closed(tmp_path: Path) -> None:
    unsupported = _write_market_context(tmp_path, schema_version="strategy_market_context.v999")
    missing = _write_corporate_event(tmp_path)
    payload = json.loads(missing.read_text(encoding="utf-8"))
    payload.pop("events")
    _write_json(missing, payload)

    assert validate_market_context_compatibility(unsupported, requested_business_date="2026-07-15").status == INCOMPATIBLE_SCHEMA
    assert validate_corporate_event_compatibility(missing, requested_business_date="2026-07-15").status == INCOMPATIBLE_SCHEMA


def test_phase22_b_invalid_status_and_accepted_autopromotion_are_rejected(tmp_path: Path) -> None:
    invalid = _write_market_context(tmp_path)
    payload = json.loads(invalid.read_text(encoding="utf-8"))
    payload["runtime_consumer_eligibility"] = "ELIGIBLE"
    payload["artifact_lifecycle_status"] = "ACCEPTED"
    payload["producer_result_status"] = "PASS"
    payload["artifact_hash"] = market_context.market_context_hash(payload)
    _write_json(invalid, payload)

    result = validate_market_context_compatibility(invalid, requested_business_date="2026-07-15", production_use_requested=True)

    assert result.status == INCOMPATIBLE_SCHEMA
    assert result.production_decision_allowed is False


def test_phase22_b_date_alignment_rejects_business_date_mismatch_and_future_feature_date(tmp_path: Path) -> None:
    mismatch = _write_market_context(tmp_path, business_date="2026-07-14", feature_date="2026-07-14")
    future = _write_corporate_event(tmp_path, feature_date="2026-07-16")

    assert validate_market_context_compatibility(mismatch, requested_business_date="2026-07-15").status == INCOMPATIBLE_DATE
    assert validate_corporate_event_compatibility(future, requested_business_date="2026-07-15").status == INCOMPATIBLE_SCHEMA


def test_phase22_b_missing_artifact_and_lineage_shortage_are_not_compatible(tmp_path: Path) -> None:
    missing_result = validate_market_context_compatibility(tmp_path / "missing.json", requested_business_date="2026-07-15")
    lineage_short = _write_corporate_event(tmp_path)
    payload = json.loads(lineage_short.read_text(encoding="utf-8"))
    payload["source_hashes"] = []
    payload["artifact_hash"] = corporate_event.corporate_event_hash(payload)
    _write_json(lineage_short, payload)

    assert missing_result.status == SOURCE_MISSING
    assert validate_corporate_event_compatibility(lineage_short, requested_business_date="2026-07-15").status == SOURCE_REVIEW_REQUIRED


def test_phase22_b_hash_mismatch_blocks_shadow_compatibility(tmp_path: Path) -> None:
    path = _write_market_context(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["trend_strength"] = 0.25
    _write_json(path, payload)

    result = validate_market_context_compatibility(path, requested_business_date="2026-07-15")

    assert result.status == INCOMPATIBLE_HASH
    assert result.shadow_read_allowed is False


def test_phase22_b_cross_artifact_business_date_mismatch_fails_closed(tmp_path: Path) -> None:
    market_path = _write_market_context(tmp_path, business_date="2026-07-15")
    corporate_path = _write_corporate_event(tmp_path, business_date="2026-07-14", feature_date="2026-07-14")

    _, result = build_candidate_compatibility_adapter(
        _candidate_rows(),
        business_date="2026-07-15",
        market_context_artifact_path=market_path,
        corporate_event_artifact_path=corporate_path,
    )

    assert result.status == "BLOCK"
    assert {artifact.status for artifact in result.artifacts} == {INCOMPATIBLE_DATE}


def test_phase22_b_candidate_adapter_preserves_existing_output_semantics(tmp_path: Path) -> None:
    market_path = _write_market_context(tmp_path)
    corporate_path = _write_corporate_event(tmp_path)
    rows = _candidate_rows()

    output, result = build_candidate_compatibility_adapter(
        rows,
        business_date="2026-07-15",
        market_context_artifact_path=market_path,
        corporate_event_artifact_path=corporate_path,
        production_use_requested=True,
    )

    assert output == rows
    assert result.status == COMPATIBLE_NOT_CONNECTED
    assert result.output_preserved
    assert result.behavior_changed is False
    assert result.candidate_count == len(rows)
    assert result.security_codes_preserved
    assert result.order_preserved
    assert result.eligibility_preserved
    assert result.reason_codes_preserved
    assert all("production_use_rejected" in artifact.reason_codes for artifact in result.artifacts)


def test_phase22_b_opportunity_adapter_preserves_scores_rank_and_feature_vectors(tmp_path: Path) -> None:
    market_path = _write_market_context(tmp_path)
    corporate_path = _write_corporate_event(tmp_path)
    rows = _opportunity_rows()

    output, result = build_opportunity_compatibility_adapter(
        rows,
        business_date="2026-07-15",
        market_context_artifact_path=market_path,
        corporate_event_artifact_path=corporate_path,
    )

    assert output == rows
    assert result.status == COMPATIBLE_NOT_CONNECTED
    assert result.output_preserved
    assert result.behavior_changed is False
    assert result.ranking_changed is False
    assert result.score_preserved
    assert result.rank_preserved
    assert result.feature_vector_preserved
    assert result.tie_break_preserved


def test_phase22_b_produced_compatible_but_not_consumed_evidence(tmp_path: Path) -> None:
    market_path = _write_market_context(tmp_path)
    corporate_path = _write_corporate_event(tmp_path)
    _, candidate_result = build_candidate_compatibility_adapter(
        _candidate_rows(),
        business_date="2026-07-15",
        market_context_artifact_path=market_path,
        corporate_event_artifact_path=corporate_path,
    )
    _, opportunity_result = build_opportunity_compatibility_adapter(
        _opportunity_rows(),
        business_date="2026-07-15",
        market_context_artifact_path=market_path,
        corporate_event_artifact_path=corporate_path,
    )

    evidence = produced_compatible_not_consumed_evidence(
        candidate_result=candidate_result,
        opportunity_result=opportunity_result,
    )

    assert evidence["status"] == "PASS"
    assert evidence["market_context_artifact_produced"] is True
    assert evidence["corporate_event_artifact_produced"] is True
    assert evidence["candidate_production_consumer_connected"] is False
    assert evidence["opportunity_production_consumer_connected"] is False
    assert evidence["runtime_switch_performed"] is False
    assert evidence["legacy_authority_active"] is True
    assert evidence["ranking_changed"] is False


def _write_market_context(
    tmp_path: Path,
    *,
    schema_version: str = market_context.SCHEMA_VERSION,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    producer_status: str = "REVIEW_REQUIRED",
) -> Path:
    source = tmp_path / "market_source.parquet"
    source.write_text("market-source", encoding="utf-8")
    payload = {
        "schema_version": schema_version,
        "producer_version": "phase22_a_market_context_producer.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": feature_date,
        "trend_regime": "RANGE",
        "trend_strength": 0.0,
        "market_breadth": "NEUTRAL",
        "volatility_regime": "NORMAL",
        "sector_dispersion": "MODERATE",
        "confidence": 0.0,
        "uncertainty": "THRESHOLD_OR_SOURCE_REVIEW_REQUIRED",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": producer_status,
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "reason_codes": ["market_context_threshold_config_required"],
        "source_artifacts": [{"role": "jquants_daily_quotes", "path": str(source), "required": True, "exists": True}],
        "source_hashes": [{"role": "jquants_daily_quotes", "path": str(source), "sha256": market_context.sha256_file(source)}],
        "temporal_safety": {
            "point_in_time": feature_date <= business_date,
            "future_leakage_used": feature_date > business_date,
            "feature_date_lte_business_date": feature_date <= business_date,
        },
        "metrics": {},
        "threshold_policy": {"status": "CONFIG_REQUIRED", "source": "", "values": None},
    }
    payload["artifact_hash"] = market_context.market_context_hash(payload)
    path = tmp_path / f"market_context_{business_date}_{feature_date}_{schema_version}.json"
    _write_json(path, payload)
    return path


def _write_corporate_event(
    tmp_path: Path,
    *,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    producer_status: str = "REVIEW_REQUIRED",
) -> Path:
    source = tmp_path / "corporate_source.parquet"
    source.write_text("corporate-source", encoding="utf-8")
    payload = {
        "schema_version": corporate_event.SCHEMA_VERSION,
        "producer_version": "phase22_aa_corporate_event_producer.v1",
        "business_date": business_date,
        "as_of": f"{business_date}T00:00:00+00:00",
        "feature_date": feature_date,
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": producer_status,
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "coverage_status": "PARTIAL",
        "events": [],
        "event_count": 0,
        "event_taxonomy": sorted(corporate_event.EVENT_TYPES),
        "event_identity": {
            "algorithm": "sha256",
            "fields": ["security_code", "event_type", "announcement_date", "effective_date", "availability_date", "source_reference", "revision_id"],
            "row_order_dependent": False,
        },
        "reason_codes": ["corporate_event_source_coverage_incomplete"],
        "source_artifacts": [{"role": "jquants_listed_issues", "path": str(source), "required": True, "exists": True}],
        "source_hashes": [{"role": "jquants_listed_issues", "path": str(source), "sha256": corporate_event.sha256_file(source)}],
        "temporal_safety": {
            "point_in_time": feature_date <= business_date,
            "future_leakage_used": feature_date > business_date,
            "feature_date_lte_business_date": feature_date <= business_date,
        },
        "no_event_semantics": {
            "empty_events_meaning": "NO_EVENTS_ONLY_WHEN_SOURCE_COVERAGE_AVAILABLE_AND_PRODUCER_PASS",
            "unknown_event_state_when_source_missing": False,
        },
    }
    payload["artifact_hash"] = corporate_event.corporate_event_hash(payload)
    path = tmp_path / f"corporate_event_{business_date}_{feature_date}.json"
    _write_json(path, payload)
    return path


def _candidate_rows() -> list[dict[str, object]]:
    return [
        {"target_date": "2026-07-15", "code": "7203", "universe_eligible": True, "excluded_reason": "", "candidate_score": 0.91},
        {"target_date": "2026-07-15", "code": "6758", "universe_eligible": False, "excluded_reason": "insufficient_lookback", "candidate_score": 0.0},
    ]


def _opportunity_rows() -> list[dict[str, object]]:
    return [
        {"target_date": "2026-07-15", "code": "7203", "expected_edge_score": 0.12, "buy_rank": 1, "feature__candidate_score": 0.91},
        {"target_date": "2026-07-15", "code": "6758", "expected_edge_score": 0.03, "buy_rank": 2, "feature__candidate_score": 0.55},
    ]


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
