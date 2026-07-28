from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import corporate_event, market_context, portfolio_policy, position_management
from ai_fund_lab_v2.strategy.portfolio_construction import (
    PortfolioConstructionConsumerError,
    PortfolioConstructionSchemaError,
    PortfolioConstructionSourceSummary,
    build_portfolio_construction_payload,
    default_runtime_artifact_path,
    load_portfolio_construction_fixture,
    portfolio_construction_hash,
    produce_portfolio_construction_artifact,
    validate_portfolio_construction_artifact,
    verify_source_hashes,
)
from ai_fund_lab_v2.strategy.portfolio_policy import PortfolioPolicyConfig, PortfolioPolicyInputSummary


def test_phase22_e_produces_draft_review_required_not_eligible_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert result.payload["position_count_decided"] is False
    assert result.payload["cash_ratio_decided"] is False
    assert result.payload["exposure_decided"] is False
    assert result.payload["position_sizing_decided"] is False
    assert result.payload["allocation_decided"] is False
    assert result.payload["quantity_decided"] is False
    assert validate_portfolio_construction_artifact(result.payload)["status"] == "PASS"


def test_phase22_e_schema_rejects_invalid_intent_missing_code_status_weight_allocation_quantity(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    mutations = (
        lambda item: item["portfolio_members"][0].update({"membership_intent": "HOLD"}),
        lambda item: item["portfolio_members"][0].update({"weight_intent": "10_PERCENT"}),
        lambda item: item["portfolio_members"][0].pop("security_code"),
        lambda item: item.update({"schema_version": "portfolio_construction.v999"}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
        lambda item: item["portfolio_members"][0].update({"target_weight": 0.1}),
        lambda item: item.update({"allocation_jpy": 100000}),
        lambda item: item["portfolio_members"][0].update({"quantity": 100}),
    )
    for mutation in mutations:
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(PortfolioConstructionSchemaError):
            validate_portfolio_construction_artifact(mutated)


def test_phase22_e_upstream_review_required_not_eligible_propagates_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "upstream_review_required:SOURCE_REVIEW_REQUIRED" in result.payload["reason_codes"]
    assert "upstream_review_required:SOURCE_NOT_ELIGIBLE" not in result.payload["reason_codes"]
    assert result.payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert result.payload["upstream_artifacts"]["portfolio_policy"]["shadow_read_allowed"] is True
    assert result.payload["upstream_artifacts"]["position_management"]["shadow_read_allowed"] is True
    with pytest.raises(PortfolioConstructionConsumerError):
        load_portfolio_construction_fixture(result.artifact_path, for_production=True)


def test_phase22_e_upstream_block_schema_date_hash_propagates(tmp_path: Path) -> None:
    market_bad = _write_market_context(tmp_path, schema_version="strategy_market_context.v999")
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=market_bad,
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert any(reason.startswith("upstream_block:") for reason in payload["reason_codes"])

    pm_bad = _write_position_management(tmp_path)
    mutated = json.loads(pm_bad.read_text(encoding="utf-8"))
    mutated["positions"][0]["action"] = "EXIT"
    _write_json(pm_bad, mutated)
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=pm_bad,
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "upstream_block:INCOMPATIBLE_HASH" in payload["reason_codes"]


def test_phase22_e_reconciles_existing_pm_actions_and_new_candidates_without_duplicate_members(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    by_code = {member["security_code"]: member for member in payload["portfolio_members"]}

    assert by_code["7203"]["membership_intent"] == "RETAIN"
    assert by_code["6758"]["membership_intent"] == "RETAIN"
    assert by_code["6758"]["weight_intent"] == "INCREASE"
    assert by_code["9984"]["membership_intent"] == "REDUCE_CANDIDATE"
    assert by_code["8306"]["membership_intent"] == "REMOVE_CANDIDATE"
    assert by_code["6098"]["membership_intent"] == "ADD_CANDIDATE"
    assert by_code["9999"]["membership_intent"] == "EXCLUDE"
    assert len(payload["portfolio_members"]) == len(by_code)
    assert "duplicate_existing_candidate_reconciled:6758" in payload["reason_codes"]


def test_phase22_e_priority_is_deterministic_and_preserves_input_rank_score_order(tmp_path: Path) -> None:
    first = _produce(tmp_path / "first").payload
    second = _produce(tmp_path / "second").payload

    assert [row["security_code"] for row in first["portfolio_members"]] == [row["security_code"] for row in second["portfolio_members"]]
    new_members = [row for row in first["portfolio_members"] if not row["current_position"]]
    assert [row["security_code"] for row in new_members[:2]] == ["6098", "9999"]
    assert new_members[0]["input_opportunity_rank"] == 1
    assert new_members[0]["input_score"] == 0.92


def test_phase22_e_date_pit_blocks_cross_date_and_future_snapshot(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path, business_date="2026-07-14"),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path, feature_date="2026-07-16"),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "candidate_date_mismatch" in payload["reason_codes"]
    assert "current_portfolio_date_mismatch" in payload["reason_codes"]
    assert "future_feature_or_snapshot_date_detected" in payload["reason_codes"]
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False


def test_phase22_e_hash_lineage_and_artifact_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert result.payload["artifact_hash"] == portfolio_construction_hash(result.payload)
    changed = json.loads(json.dumps(result.payload))
    changed["source_hashes"][0]["sha256"] = "deadbeef"
    assert verify_source_hashes(changed)["status"] == "BLOCK"
    changed = json.loads(json.dumps(result.payload))
    changed["portfolio_members"][0]["membership_intent"] = "REMOVE_CANDIDATE"
    assert changed["artifact_hash"] != portfolio_construction_hash(changed)


def test_phase22_e_bootstrap_missing_inputs_does_not_emit_empty_pass_or_all_retain(tmp_path: Path) -> None:
    payload, _ = build_portfolio_construction_payload(
        business_date="2026-07-15",
        market_context_artifact_path=None,
        corporate_event_artifact_path=None,
        portfolio_policy_artifact_path=None,
        position_management_artifact_path=None,
        candidate_summary=_source_summary(tmp_path, "candidate", status="REVIEW_REQUIRED", rows=[]),
        opportunity_summary=_source_summary(tmp_path, "opportunity", status="REVIEW_REQUIRED", rows=[]),
        current_portfolio_summary=_source_summary(tmp_path, "current", status="REVIEW_REQUIRED", rows=[]),
        pending_summary=None,
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config", status="REVIEW_REQUIRED"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["portfolio_members"] == []
    assert payload["temporal_safety"]["previous_day_portfolio_construction_copied"] is False
    assert "upstream_block:SOURCE_MISSING" in payload["reason_codes"]


def test_phase22_e_behavior_and_capital_deployment_authority_preserved(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload

    assert payload["position_count_decided"] is False
    assert payload["cash_ratio_decided"] is False
    assert payload["exposure_decided"] is False
    assert payload["allocation_decided"] is False
    assert payload["quantity_decided"] is False
    assert payload["production_consumer_connected"] is False
    assert payload["runtime_switch_performed"] is False
    assert payload["legacy_authority_active"] is True


def test_phase22_e_fixture_shadow_reads_draft_and_rejects_production(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = load_portfolio_construction_fixture(result.artifact_path)

    assert payload["schema_version"] == "portfolio_construction.v1"
    with pytest.raises(PortfolioConstructionConsumerError):
        load_portfolio_construction_fixture(result.artifact_path, for_production=True)


def _produce(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    return produce_portfolio_construction_artifact(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path),
        candidate_summary=_candidate_summary(tmp_path),
        opportunity_summary=_opportunity_summary(tmp_path),
        current_portfolio_summary=_current_summary(tmp_path),
        pending_summary=_source_summary(tmp_path, "pending", rows=[]),
        policy_config_summary=_source_summary(tmp_path, "construction_policy_config"),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _candidate_rows() -> list[dict[str, object]]:
    return [
        {"candidate_id": "candidate-6758", "code": "6758", "candidate_order": 1, "candidate_score": 0.88, "universe_eligible": True},
        {"candidate_id": "candidate-6098", "code": "6098", "candidate_order": 2, "candidate_score": 0.9, "universe_eligible": True},
        {"candidate_id": "candidate-9999", "code": "9999", "candidate_order": 3, "candidate_score": 0.7, "universe_eligible": False},
    ]


def _opportunity_rows() -> list[dict[str, object]]:
    return [
        {"opportunity_id": "opportunity-6098", "code": "6098", "opportunity_rank": 1, "expected_edge_score": 0.92},
        {"opportunity_id": "opportunity-6758", "code": "6758", "opportunity_rank": 2, "expected_edge_score": 0.86},
        {"opportunity_id": "opportunity-9999", "code": "9999", "opportunity_rank": 3, "expected_edge_score": 0.71},
    ]


def _current_rows() -> list[dict[str, object]]:
    return [
        {"position_id": "current-7203", "security_code": "7203"},
        {"position_id": "current-6758", "security_code": "6758"},
        {"position_id": "current-9984", "security_code": "9984"},
        {"position_id": "current-8306", "security_code": "8306"},
    ]


def _pm_rows() -> list[dict[str, object]]:
    return [
        {"position_id": "pm-7203", "security_code": "7203", "action": "HOLD", "intensity": "NONE", "confidence": 0.8, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["HOLD_BY_STRONG_CONTINUATION"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
        {"position_id": "pm-6758", "security_code": "6758", "action": "ADD", "intensity": "UNRESOLVED", "confidence": 0.7, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["ADD_BY_STRONG_TREND_AND_RANK"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
        {"position_id": "pm-9984", "security_code": "9984", "action": "REDUCE", "intensity": "MEDIUM", "confidence": 0.6, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["REDUCE_BY_PEAK_DRAWDOWN_WARNING"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
        {"position_id": "pm-8306", "security_code": "8306", "action": "EXIT", "intensity": "NONE", "confidence": 0.9, "uncertainty": "UPSTREAM_REVIEW_REQUIRED", "reason_codes": ["EXIT_BY_HARD_STOP"], "lifecycle_reference": "", "opportunity_reference": "", "market_context_reference": "", "corporate_event_reference": "", "portfolio_policy_reference": ""},
    ]


def _candidate_summary(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> PortfolioConstructionSourceSummary:
    return _source_summary(tmp_path, "candidate", rows=_candidate_rows(), business_date=business_date, feature_date=feature_date)


def _opportunity_summary(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> PortfolioConstructionSourceSummary:
    return _source_summary(tmp_path, "opportunity", rows=_opportunity_rows(), business_date=business_date, feature_date=feature_date)


def _current_summary(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> PortfolioConstructionSourceSummary:
    return _source_summary(tmp_path, "current", rows=_current_rows(), business_date=business_date, feature_date=feature_date)


def _source_summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    rows: list[dict[str, object]] | None = None,
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
) -> PortfolioConstructionSourceSummary:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"{kind}_source.json"
    payload = {"kind": kind, "business_date": business_date, "feature_date": feature_date, "status": status, "rows": rows or []}
    _write_json(path, payload)
    return PortfolioConstructionSourceSummary(
        status=status,
        business_date=business_date,
        feature_date=feature_date,
        source_ref=str(path),
        source_hash=_sha256_file(path),
        rows=tuple(rows or []),
        summary={"kind": kind, "row_count": len(rows or [])},
    )


def _write_position_management(tmp_path: Path) -> Path:
    source = tmp_path / "pm_source.json"
    _write_json(source, {"rows": _pm_rows()})
    payload = {
        "schema_version": position_management.SCHEMA_VERSION,
        "producer_version": "phase22_d_position_management_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "positions": _pm_rows(),
        "position_count": 4,
        "action_taxonomy": ["ADD", "EXIT", "HOLD", "REDUCE"],
        "intensity_taxonomy": ["LIGHT", "MEDIUM", "NONE", "STRONG", "UNRESOLVED"],
        "quantity_decided": False,
        "minimum_holding_decided": False,
        "cooldown_decided": False,
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "upstream_artifacts": {},
        "accepted_generation_reference": {},
        "model_reference": {},
        "scaler_reference": {},
        "source_artifacts": [{"role": "pm_source", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "pm_source", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_pm_artifact_copied": False},
        "production_consumer_connected": False,
        "existing_pm_authority_active": True,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    payload["artifact_hash"] = position_management.position_management_hash(payload)
    path = tmp_path / "position_management.json"
    _write_json(path, payload)
    return path


def _write_portfolio_policy(tmp_path: Path) -> Path:
    config_path = tmp_path / "portfolio_policy_config.json"
    config_payload = {
        "intent_policy": {
            "risk_posture": "BALANCED",
            "entry_posture": "MAINTAIN",
            "position_count_posture": "MAINTAIN",
            "cash_posture": "MAINTAIN",
            "exposure_posture": "MAINTAIN",
            "position_management_bias": "NEUTRAL",
        }
    }
    _write_json(config_path, config_payload)
    result = portfolio_policy.produce_portfolio_policy_artifact(
        business_date="2026-07-15",
        market_context_artifact_path=_write_market_context(tmp_path),
        corporate_event_artifact_path=_write_corporate_event(tmp_path),
        candidate_summary=_pp_summary(tmp_path, "candidate"),
        opportunity_summary=_pp_summary(tmp_path, "opportunity"),
        current_portfolio_summary={},
        current_cash_summary={},
        current_exposure_summary={},
        policy_config=PortfolioPolicyConfig(
            config_version="phase22_e_fixture_policy_config.v1",
            config_source=str(config_path),
            intent_policy=config_payload["intent_policy"],
        ),
        output_path=tmp_path / "portfolio_policy.json",
    )
    return Path(result.artifact_path)


def _pp_summary(tmp_path: Path, kind: str) -> PortfolioPolicyInputSummary:
    path = tmp_path / f"pp_{kind}_summary.json"
    payload = {"kind": kind, "business_date": "2026-07-15", "feature_date": "2026-07-15"}
    _write_json(path, payload)
    return PortfolioPolicyInputSummary("PASS", "2026-07-15", "2026-07-15", payload, str(path), _sha256_file(path))


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
        "temporal_safety": {"point_in_time": feature_date <= business_date, "future_leakage_used": feature_date > business_date, "feature_date_lte_business_date": feature_date <= business_date},
        "metrics": {},
        "threshold_policy": {"status": "CONFIG_REQUIRED", "source": "", "values": None},
    }
    payload["artifact_hash"] = market_context.market_context_hash(payload)
    path = tmp_path / f"market_context_{business_date}_{feature_date}_{schema_version}.json"
    _write_json(path, payload)
    return path


def _write_corporate_event(tmp_path: Path, *, business_date: str = "2026-07-15", feature_date: str = "2026-07-15") -> Path:
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
        "temporal_safety": {"point_in_time": feature_date <= business_date, "future_leakage_used": feature_date > business_date, "feature_date_lte_business_date": feature_date <= business_date},
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
