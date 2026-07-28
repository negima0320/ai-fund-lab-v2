from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import corporate_event, market_context
from ai_fund_lab_v2.strategy.portfolio_policy import (
    PortfolioPolicyConfig,
    PortfolioPolicyConsumerError,
    PortfolioPolicyInputSummary,
    PortfolioPolicySchemaError,
    build_portfolio_policy_payload,
    default_runtime_artifact_path,
    load_portfolio_policy_fixture,
    portfolio_policy_hash,
    produce_portfolio_policy_artifact,
    stable_payload_hash,
    validate_portfolio_policy_artifact,
    verify_source_hashes,
)


def test_phase22_c_produces_draft_review_required_not_eligible_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert result.payload["concrete_values_decided"] is False
    assert result.payload["risk_posture"] == "BALANCED"
    assert result.payload["entry_posture"] == "MAINTAIN"
    assert result.payload["upstream_artifacts"]["market_context"]["shadow_read_allowed"] is True
    assert result.payload["upstream_artifacts"]["corporate_event"]["shadow_read_allowed"] is True
    assert Path(result.artifact_path).is_file()
    assert validate_portfolio_policy_artifact(result.payload)["status"] == "PASS"


def test_phase22_c_schema_rejects_missing_field_invalid_taxonomy_status_and_confidence(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    for mutation in (
        lambda item: item.pop("risk_posture"),
        lambda item: item.update({"cash_posture": "TWENTY_PERCENT"}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
        lambda item: item.update({"confidence": 2.0}),
        lambda item: item.update({"schema_version": "portfolio_policy.v999"}),
    ):
        mutated = dict(payload)
        mutation(mutated)
        with pytest.raises(PortfolioPolicySchemaError):
            validate_portfolio_policy_artifact(mutated)


def test_phase22_c_upstream_review_required_and_not_eligible_propagates(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    reasons = set(result.payload["reason_codes"])
    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "upstream_review_required:SOURCE_REVIEW_REQUIRED" in reasons
    assert "upstream_review_required:SOURCE_NOT_ELIGIBLE" not in reasons
    assert result.payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert result.payload["consumer_eligibility_reason_codes"] == ["SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE"]
    with pytest.raises(PortfolioPolicyConsumerError):
        load_portfolio_policy_fixture(result.artifact_path, for_production=True)


def test_phase22_c_upstream_block_schema_date_and_hash_propagate_to_block(tmp_path: Path) -> None:
    schema_bad_market = _write_market_context(tmp_path, schema_version="strategy_market_context.v999")
    date_bad_corporate = _write_corporate_event(tmp_path, business_date="2026-07-14", feature_date="2026-07-14")
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=schema_bad_market,
        corporate_event_artifact_path=date_bad_corporate,
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        policy_config=_config(tmp_path),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert any(reason.startswith("upstream_block:") for reason in payload["reason_codes"])

    hash_bad = _write_market_context(tmp_path)
    mutated = json.loads(hash_bad.read_text(encoding="utf-8"))
    mutated["trend_strength"] = 0.5
    _write_json(hash_bad, mutated)
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=hash_bad,
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 0},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        policy_config=_config(tmp_path),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "upstream_block:INCOMPATIBLE_HASH" in payload["reason_codes"]


def test_phase22_c_date_pit_rejects_candidate_opportunity_future_and_cross_date(tmp_path: Path) -> None:
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_summary(tmp_path, "candidate", business_date="2026-07-14", feature_date="2026-07-14"),
        opportunity_summary=_summary(tmp_path, "opportunity", feature_date="2026-07-16"),
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=_config(tmp_path),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "candidate_summary_date_mismatch" in payload["reason_codes"]
    assert "opportunity_summary_date_mismatch" in payload["reason_codes"]
    assert "future_feature_date_detected" in payload["reason_codes"]


def test_phase22_c_hash_lineage_config_hash_and_source_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    assert verify_source_hashes(result.payload)["status"] == "PASS"

    bad_config = _config(tmp_path)
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=bad_config,
        expected_policy_config_hash="sha256:deadbeef",
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "policy_config_hash_mismatch" in payload["reason_codes"]

    source_hashes = list(result.payload["source_hashes"])
    source_hashes[0] = {**source_hashes[0], "sha256": "deadbeef"}
    changed = {**result.payload, "source_hashes": source_hashes}
    assert verify_source_hashes(changed)["status"] == "BLOCK"


def test_phase22_c_bootstrap_missing_inputs_review_required_no_fixed_fallback(tmp_path: Path) -> None:
    payload, _ = build_portfolio_policy_payload(
        business_date="2026-07-15",
        market_context_artifact_path=None,
        corporate_event_artifact_path=None,
        candidate_summary=_summary(tmp_path, "candidate", status="REVIEW_REQUIRED"),
        opportunity_summary=_summary(tmp_path, "opportunity", status="REVIEW_REQUIRED"),
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=None,
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["risk_posture"] == "UNRESOLVED"
    assert payload["temporal_safety"]["previous_day_policy_copied"] is False
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False
    assert "policy_config_required" in payload["reason_codes"]


def test_phase22_c_intent_taxonomy_is_axis_separated_and_concrete_values_forbidden(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload

    assert {
        "risk_posture",
        "entry_posture",
        "position_count_posture",
        "cash_posture",
        "exposure_posture",
        "position_management_bias",
    }.issubset(payload)
    assert payload["concrete_values_decided"] is False
    assert "target_positions" not in payload
    payload["target_cash_ratio"] = 0.2
    with pytest.raises(PortfolioPolicySchemaError):
        validate_portfolio_policy_artifact(payload)


def test_phase22_c_fixture_shadow_consumer_reads_draft_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    fixture = load_portfolio_policy_fixture(result.artifact_path)

    assert fixture["schema_version"] == "portfolio_policy.v1"
    assert fixture["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    with pytest.raises(PortfolioPolicyConsumerError):
        load_portfolio_policy_fixture(result.artifact_path, for_production=True)


def test_phase22_c_artifact_hash_is_stable_and_detects_mismatch(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = dict(result.payload)
    assert payload["artifact_hash"] == portfolio_policy_hash(payload)
    payload["cash_posture"] = "RAISE"
    assert payload["artifact_hash"] != portfolio_policy_hash(payload)


def _produce(tmp_path: Path):
    return produce_portfolio_policy_artifact(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_summary(tmp_path, "candidate"),
        opportunity_summary=_summary(tmp_path, "opportunity"),
        current_portfolio_summary={"position_count": 2},
        current_cash_summary={"cash_available": 1000000},
        current_exposure_summary={"gross_exposure": 0},
        policy_config=_config(tmp_path),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _config(tmp_path: Path) -> PortfolioPolicyConfig:
    path = tmp_path / "portfolio_policy_config.json"
    payload = {
        "config_version": "phase22_c_fixture_intent_config.v1",
        "intent_policy": {
            "risk_posture": "BALANCED",
            "entry_posture": "MAINTAIN",
            "position_count_posture": "MAINTAIN",
            "cash_posture": "MAINTAIN",
            "exposure_posture": "MAINTAIN",
            "position_management_bias": "NEUTRAL",
        },
    }
    _write_json(path, payload)
    return PortfolioPolicyConfig(
        config_version="phase22_c_fixture_intent_config.v1",
        config_source=str(path),
        intent_policy=payload["intent_policy"],
    )


def _summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
) -> PortfolioPolicyInputSummary:
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "business_date": business_date, "feature_date": feature_date, "count": 2}
    _write_json(path, payload)
    return PortfolioPolicyInputSummary(
        status=status,
        business_date=business_date,
        feature_date=feature_date,
        summary=payload,
        source_ref=str(path),
        source_hash=_sha256_file(path),
    )


def _write_market_context(
    tmp_path: Path,
    *,
    schema_version: str = market_context.SCHEMA_VERSION,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
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
        "producer_result_status": "REVIEW_REQUIRED",
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
        "producer_result_status": "REVIEW_REQUIRED",
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


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
