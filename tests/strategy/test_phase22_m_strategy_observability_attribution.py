from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy.observability import (
    StrategyObservabilitySchemaError,
    build_strategy_decision_trace,
    produce_strategy_decision_trace,
    strategy_decision_trace_hash,
    validate_strategy_decision_trace,
)


BUSINESS_DATE = "2026-07-15"


def test_phase22_m_complete_trace_portfolio_positions_status_and_reason_aggregation(tmp_path: Path) -> None:
    paths = _write_artifact_set(tmp_path)
    result = produce_strategy_decision_trace(
        business_date=BUSINESS_DATE,
        profile="historical-smoke",
        run_id="phase22-m-fixture",
        artifact_paths=paths,
        legacy_context={"max_positions": 5, "target_investment_ratio": 0.85, "cash_buffer": 0.15},
        output_path=tmp_path / "strategy_trace.json",
    )

    payload = result.payload
    assert payload["schema_version"] == "strategy_decision_trace.v1"
    assert payload["overall_status"] == "PASS"
    assert payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert payload["runtime_switch_performed"] is False
    assert payload["portfolio_attribution"]["target_position_count"] == 2
    assert payload["portfolio_attribution"]["add_count"] == 1
    assert payload["portfolio_attribution"]["hold_count"] == 1
    assert len(payload["per_symbol_attribution"]) == 2
    assert payload["per_symbol_attribution"][0]["share_quantity_decided"] is False
    assert payload["outcome_boundary"]["strategy_input_allowed"] is False
    assert payload["artifact_hash"] == strategy_decision_trace_hash(payload)
    assert validate_strategy_decision_trace(payload)["status"] == "PASS"
    assert payload["reason_code_aggregation"]["Market"]
    assert payload["legacy_dynamic_comparison"]["max_positions"] == "DIFFERENT"


def test_phase22_m_partial_missing_artifact_is_incomplete_not_filled(tmp_path: Path) -> None:
    paths = _write_artifact_set(tmp_path)
    paths["position_sizing"] = tmp_path / "missing.json"
    payload = build_strategy_decision_trace(
        business_date=BUSINESS_DATE,
        profile="demo",
        run_id="partial",
        artifact_paths=paths,
    )

    assert payload["overall_status"] == "INCOMPLETE_ATTRIBUTION"
    assert "position_sizing" in payload["artifacts_missing"]
    assert any("required_artifact_missing:position_sizing" == reason for reason in payload["review_reasons"])
    by_code = {row["security_code"]: row for row in payload["per_symbol_attribution"]}
    assert "target_weight" not in by_code["1001"]


def test_phase22_m_hash_cross_date_and_outcome_boundary_block(tmp_path: Path) -> None:
    paths = _write_artifact_set(tmp_path)
    broken = json.loads(Path(paths["market_context"]).read_text(encoding="utf-8"))
    broken["trend_regime"] = "BEAR"
    Path(paths["market_context"]).write_text(json.dumps(broken, sort_keys=True), encoding="utf-8")
    payload = build_strategy_decision_trace(
        business_date=BUSINESS_DATE,
        profile="demo",
        run_id="hash",
        artifact_paths=paths,
    )
    assert payload["overall_status"] == "BLOCK"
    assert "artifact_hash_mismatch" in payload["blocking_reasons"]

    paths = _write_artifact_set(tmp_path / "cross")
    cross = build_strategy_decision_trace(
        business_date="2026-07-16",
        profile="demo",
        run_id="cross",
        artifact_paths=paths,
    )
    assert cross["overall_status"] == "BLOCK"
    assert "cross_date_artifact" in cross["blocking_reasons"]

    paths = _write_artifact_set(tmp_path / "outcome")
    outcome = build_strategy_decision_trace(
        business_date=BUSINESS_DATE,
        profile="demo",
        run_id="outcome",
        artifact_paths=paths,
        outcome_context={"strategy_input_allowed": True},
    )
    with pytest.raises(StrategyObservabilitySchemaError):
        validate_strategy_decision_trace(outcome)


def test_phase22_m_deterministic_and_input_order_independent(tmp_path: Path) -> None:
    paths = _write_artifact_set(tmp_path)
    first = build_strategy_decision_trace(
        business_date=BUSINESS_DATE,
        profile="historical",
        run_id="deterministic",
        artifact_paths=paths,
    )
    second = build_strategy_decision_trace(
        business_date=BUSINESS_DATE,
        profile="historical",
        run_id="deterministic",
        artifact_paths=dict(reversed(list(paths.items()))),
    )
    assert strategy_decision_trace_hash(first) == strategy_decision_trace_hash(second)
    assert first["per_symbol_attribution"] == second["per_symbol_attribution"]


def _write_artifact_set(root: Path) -> dict[str, Path]:
    rows = {
        "market_context": {
            "schema_version": "strategy_market_context.v1",
            "producer_version": "phase22_l_market_context_authority_policy.v1",
            "trend_regime": "BULL",
            "regime_state": "BULL",
            "market_breadth": "STRONG",
            "volatility_regime": "NORMAL",
            "sector_contexts": [{"sector_id": "Tech"}],
            "reason_codes": ["market_context:benchmark_resolved"],
            "confidence": 0.9,
            "uncertainty": "LOW",
        },
        "corporate_event": {"schema_version": "corporate_event_authority.v1", "producer_version": "phase22_aa_corporate_event_producer.v1", "reason_codes": []},
        "portfolio_policy": {"schema_version": "portfolio_policy.v1", "producer_version": "phase22_c_portfolio_policy_producer.v1", "risk_posture": "RISK_ON", "reason_codes": ["portfolio_policy:risk_on"]},
        "dynamic_position_count": {"schema_version": "dynamic_position_count.v1", "producer_version": "phase22_h_dynamic_position_count_producer.v1", "target_position_count": 2, "reason_codes": ["dynamic_position_count:target_2"]},
        "dynamic_cash_exposure": {"schema_version": "dynamic_cash_exposure.v1", "producer_version": "phase22_i_dynamic_cash_exposure_producer.v1", "target_cash_ratio": 0.2, "target_gross_exposure_ratio": 0.8, "reason_codes": ["cash_exposure:balanced"]},
        "portfolio_construction": {
            "schema_version": "portfolio_construction.v1",
            "producer_version": "phase22_e_portfolio_construction_producer.v1",
            "portfolio_members": [
                {"security_code": "1001", "membership_intent": "ADD_CANDIDATE", "input_candidate_order": 1, "input_opportunity_rank": 1, "input_score": 0.9, "reason_codes": ["membership:selected"]},
                {"security_code": "1002", "membership_intent": "RETAIN", "input_candidate_order": 2, "input_opportunity_rank": 2, "input_score": 0.7, "reason_codes": ["membership:retain"]},
            ],
            "reason_codes": [],
        },
        "position_sizing": {
            "schema_version": "position_sizing.v1",
            "producer_version": "phase22_j_position_sizing_producer.v1",
            "target_position_count": 2,
            "total_target_weight": 0.8,
            "positions": [
                {"security_code": "1001", "target_weight": 0.45, "target_notional": 450000, "sizing_status": "PASS", "reason_codes": ["sizing:quality"]},
                {"security_code": "1002", "target_weight": 0.35, "target_notional": 350000, "sizing_status": "PASS", "reason_codes": ["sizing:base"]},
            ],
            "reason_codes": [],
        },
        "position_management": {
            "schema_version": "position_management.v1",
            "producer_version": "phase22_k_regime_event_position_management_producer.v1",
            "positions": [
                {"security_code": "1001", "action": "ADD", "intensity": "MEDIUM", "confidence": 0.8, "uncertainty": "LOW", "reason_codes": ["pm:add"]},
                {"security_code": "1002", "action": "HOLD", "intensity": "NONE", "confidence": 0.8, "uncertainty": "LOW", "reason_codes": ["pm:hold"]},
            ],
            "reason_codes": [],
        },
        "runtime_planning": {
            "schema_version": "runtime_planning.v1",
            "producer_version": "phase22_g_runtime_planning_producer.v1",
            "planning_intents": [
                {"security_code": "1001", "planning_intent": "BUY_NEW", "order_side_intent": "BUY", "reason_codes": ["planning:buy_new"]},
                {"security_code": "1002", "planning_intent": "NO_ACTION", "order_side_intent": "NONE", "reason_codes": ["planning:hold"]},
            ],
            "reason_codes": [],
        },
    }
    paths: dict[str, Path] = {}
    for kind, payload in rows.items():
        path = root / f"{kind}.json"
        source = root / f"{kind}.source"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(kind, encoding="utf-8")
        payload.update(
            {
                "business_date": BUSINESS_DATE,
                "feature_date": BUSINESS_DATE,
                "artifact_lifecycle_status": "DRAFT",
                "source_authority_status": "VALID",
                "producer_result_status": "PASS",
                "runtime_consumer_eligibility": "NOT_ELIGIBLE",
                "source_artifacts": [{"role": kind, "path": str(source), "required": True, "status": "PASS"}],
                "source_hashes": [{"role": kind, "path": str(source), "sha256": _file_hash(source)}],
                "config_hash": _file_hash(source),
            }
        )
        payload["artifact_hash"] = _payload_hash(payload)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        paths[kind] = path
    return paths


def _payload_hash(payload: dict) -> str:
    clean = {key: value for key, value in payload.items() if key != "artifact_hash"}
    encoded = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib

    return hashlib.sha256(encoded).hexdigest()


def _file_hash(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
