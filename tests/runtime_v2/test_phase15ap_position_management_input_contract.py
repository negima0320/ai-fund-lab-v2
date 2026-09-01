from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.artifact_lookup import RuntimeArtifactLookupHalt, RuntimeArtifactMember
from ai_fund_lab_v2.runtime_v2.position_management import producer as pm_producer
from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions
from ai_fund_lab_v2.runtime_v2.planning.sell_pipeline import (
    PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT,
    run_sell_planning_pending_pipeline,
)


BUSINESS_DATE = "2026-07-09"
PM_ADAPTER_RELATIVE_PATH = Path("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py")


class _Phase15APArtifactSet:
    artifact_instance_id = "phase15ap.fixture.pm.runtime_adapter@sha256-current"
    accepted_event_id = "phase15ap-fixture-accepted-current"

    def __init__(self, member: RuntimeArtifactMember) -> None:
        self.raw_resolver_result = {
            "schema_version": "artifact_registry_resolver_result.v1",
            "members": [
                {
                    "member_role": "RUNTIME_ADAPTER",
                    "physical_path": member.physical_path.as_posix(),
                    "content_hash": member.content_hash,
                    "authority_mode": "ACCEPTED_CURRENT_PATH",
                    "accepted_current_path": True,
                }
            ],
        }
        self._member = member

    def require_member(self, role: str) -> RuntimeArtifactMember:
        if role != "RUNTIME_ADAPTER":
            raise RuntimeArtifactLookupHalt(f"required artifact member missing: POSITION_MANAGEMENT_POLICY_SET:{role}")
        return self._member


@pytest.fixture(autouse=True)
def _phase15ap_current_pm_adapter_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    source = Path(pm_producer.__file__).resolve()
    digest = _sha(source)
    artifact_set = _Phase15APArtifactSet(
        RuntimeArtifactMember(
            member_role="RUNTIME_ADAPTER",
            physical_path=PM_ADAPTER_RELATIVE_PATH,
            content_hash=digest,
            schema_hash=None,
            artifact_type="RUNTIME_ADAPTER",
            artifact_set_id="control.position_management.accepted_set",
            logical_artifact_id="control.position_management.accepted_set.runtime_adapter",
        )
    )
    monkeypatch.setattr(pm_producer, "resolve_position_management_policy_artifacts", lambda: artifact_set)


def test_phase15ap_valid_pm_input_contract_allows_pm_and_sell_planning(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), expected_edge=-0.05, downside=0.8)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "PASS"
    assert result.to_manifest_fields()["pm_input_schema_status"] == "READY"
    assert artifact["input_contract"]["pm_input_schema_status"] == "READY"
    assert artifact["defaulted_fields"] == []
    assert artifact["decision_count"] == 1


def test_phase32_bv_pm_producer_propagates_run_scoped_campaign_to_bq_full_exit_actual_path(tmp_path, monkeypatch):
    runtime_root = _runtime_root(
        tmp_path,
        positions=[_position("45750", quantity=100, average_price=1000, current_price=1000)],
        current_as_of=BUSINESS_DATE,
    )
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32bv-test"
    _write_position_campaigns(
        evidence_root,
        symbol="45750",
        campaign_id="pc-1c231f87db41dc41-45750-0001",
        run_id="phase32bv-test",
        business_date=BUSINESS_DATE,
    )
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("45750",), expected_edge=0.05, downside=0.6)

    def _fake_pm_inference(**_kwargs):
        return SimpleNamespace(
            output=pd.DataFrame(
                [
                    {
                        "target_date": BUSINESS_DATE,
                        "code": "45750",
                        "action": "REDUCE",
                        "action_reason": "risk_increased_but_trend_not_broken",
                        "continue_holding": False,
                        "exit_candidate": False,
                        "reduce_candidate": True,
                        "add_candidate": False,
                        "hold_score": 0.20,
                        "exit_score": 0.30,
                        "reduce_score": 0.70,
                        "add_score": 0.10,
                        "model_version": "fixture",
                        "feature_version": "fixture",
                        "created_at": BUSINESS_DATE + "T00:00:00Z",
                    }
                ]
            ),
            summary={"status": "OK"},
        )

    monkeypatch.setattr(pm_producer, "run_position_management_inference", _fake_pm_inference)

    pm_result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        runtime_test_evidence_root=evidence_root,
        runtime_test_run_id="phase32bv-test",
    )
    pm_artifact = _read_json(pm_result.artifact_path)
    sell_decision = pm_result.sell_exit_decisions[0]

    assert pm_result.status == "PASS"
    assert pm_artifact["decisions"][0]["decision"] == "REDUCE"
    assert pm_artifact["decisions"][0]["position_campaign_id"] == "pc-1c231f87db41dc41-45750-0001"
    assert pm_artifact["decisions"][0]["campaign_id"] == "pc-1c231f87db41dc41-45750-0001"
    assert pm_artifact["decisions"][0]["campaign_identity_authority"]["status"] == "PASS"
    assert sell_decision.source_decision == "REDUCE"
    assert sell_decision.quantity == 0
    assert sell_decision.position_campaign_id == "pc-1c231f87db41dc41-45750-0001"

    sell_result = run_sell_planning_pending_pipeline(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        exit_decisions=pm_result.sell_exit_decisions,
        environment_capability_context={
            "runtime_mode": "historical",
            "historical_replay": True,
            "broker_environment": "historical_simulated",
            "simulation": True,
            "broker_write": False,
            "external_delivery": False,
            "tachibana_demo_write": False,
            "tachibana_production_write": False,
            "submit_enabled": False,
            "runtime_test_run_id": "phase32bv-test",
            "runtime_test_profile_id": "historical-smoke",
            "runtime_test_evidence_root": str(evidence_root),
            "lot_blocked_reduce_reconsideration_strategy_intelligence_payload": _strategy_intelligence(
                "45750",
                campaign_id="pc-1c231f87db41dc41-45750-0001",
                run_id="phase32bv-test",
                trend_state="WEAK",
                relative_strength_state="WEAK",
                participation_quality_state="WEAK",
                participation_risk_state="ELEVATED_RISK",
                current_campaign_relative_return=0.5,
            ),
            "lot_blocked_reduce_reconsideration_market_context_payload": _market_context(run_id="phase32bv-test"),
        },
    )
    pending = _read_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    order_plan = _read_json(runtime_root / "runtime_state" / "sell_pipeline" / BUSINESS_DATE / "order_plan.json")

    assert sell_result.status == "PASS"
    assert pending["items"][0]["symbol"] == "45750"
    assert pending["items"][0]["quantity"] == 100
    assert pending["items"][0]["position_campaign_id"] == "pc-1c231f87db41dc41-45750-0001"
    assert pending["items"][0]["quantity_contract"]["reconsideration_reason"] == PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT
    assert pending["items"][0]["quantity_contract"]["source_pm_action"] == "REDUCE"
    assert order_plan["lot_blocked_reduce_reconsiderations"][0]["status"] == "PROMOTED"


def test_phase32_bv_pm_producer_rejects_stale_cross_run_campaign_authority(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("45750")])
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32bv-test"
    _write_position_campaigns(
        evidence_root,
        symbol="45750",
        campaign_id="pc-1c231f87db41dc41-45750-0001",
        run_id="other-run",
        business_date=BUSINESS_DATE,
    )
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("45750",), expected_edge=0.05, downside=0.6)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        runtime_test_evidence_root=evidence_root,
        runtime_test_run_id="phase32bv-test",
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_position_campaign_authority_review_required"
    assert "POSITION_CAMPAIGN_AUTHORITY_RUN_ID_MISMATCH" in artifact["missing_fields"]


def test_phase32_bv_pm_producer_rejects_ambiguous_open_campaign_authority(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("45750")])
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / "phase32bv-test"
    _write_position_campaigns(
        evidence_root,
        symbol="45750",
        campaign_id="pc-1c231f87db41dc41-45750-0001",
        run_id="phase32bv-test",
        business_date=BUSINESS_DATE,
        extra_campaign_ids=("pc-ambiguous-45750-0002",),
    )
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("45750",), expected_edge=0.05, downside=0.6)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        runtime_test_evidence_root=evidence_root,
        runtime_test_run_id="phase32bv-test",
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_position_campaign_authority_review_required"
    assert "POSITION_CAMPAIGN_AUTHORITY_MULTIPLE_OPEN_CAMPAIGNS" in artifact["missing_fields"]


def test_phase20_s_pm_decision_trace_preserves_runtime_behavior_and_authority(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522", quantity=100, average_price=1000, current_price=850)])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), expected_edge=-0.05, downside=0.8)
    feature = pd.read_csv(feature_path)
    feature["current_price"] = 900
    feature["current_return"] = -0.10
    feature["average_price"] = 1000
    feature["quantity"] = 100
    feature.to_csv(feature_path, index=False)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)
    decision = artifact["decisions"][0]
    trace_path = Path(artifact["decision_trace_path"])
    trace_artifact = _read_json(trace_path)
    trace = trace_artifact["traces"][0]
    sell_decisions = pm_producer.load_sell_exit_decisions_from_pm_artifact(result.artifact_path)

    assert result.status == "PASS"
    assert decision["decision"] == "EXIT"
    assert decision["runtime_action"] == "SELL_FULL_POSITION"
    assert decision["runtime_sell_quantity"] == 100
    assert sell_decisions[0].source_decision == "EXIT"
    assert sell_decisions[0].quantity == 100
    assert artifact["confidence_semantics"] == "selected_action_score_not_calibrated_probability"
    assert decision["confidence"] == decision["action_score"] == decision["selected_action_score"]
    assert decision["decision_trace_contract_version"] == "runtime_v2_pm_decision_trace_contract_v1"
    assert decision["dominant_cause"] == "EXIT_BY_HARD_STOP"
    assert decision["decision_trace"]["position_state"]["current_price"] == 850
    assert decision["decision_trace"]["position_state"]["current_return"] == pytest.approx(-0.15)
    assert decision["decision_trace"]["non_canonical_feature_position_state_copy"]["current_price"] == 900
    assert decision["decision_trace"]["position_state_copy_mismatch"]["status"] == "MISMATCH"
    assert "current_price" in decision["decision_trace"]["position_state_copy_mismatch"]["mismatched_fields"]
    assert trace["decision_result"]["confidence_semantics"] == "selected_action_score_not_calibrated_probability"


def test_phase15ap_stale_current_is_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")], current_as_of="2026-07-08")
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",))

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_input_stale_artifacts"
    assert artifact["stale_artifacts"] == ["current"]
    assert artifact["review_required"] is True


def test_phase15ap_current_positions_with_zero_pm_feature_rows_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), feature_symbols=())

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_feature_rows_missing_for_current_positions"
    assert artifact["missing_symbols"] == ["6522"]


def test_phase15ap_partial_held_symbol_feature_coverage_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522"), _position("7203")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522", "7203"), feature_symbols=("6522",))

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "7203" in artifact["missing_symbols"]


def test_phase15ap_current_empty_with_no_position_reason_is_no_position_ready(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=(), include_no_position_reason=True)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "NO_POSITION"
    assert artifact["input_contract"]["pm_input_schema_status"] == "READY"
    assert artifact["decision_count"] == 0


def test_phase15ap_current_empty_without_no_position_reason_is_no_position_ready(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=(), include_no_position_reason=False)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "NO_POSITION"
    assert artifact["input_contract"]["pm_input_schema_status"] == "READY"
    assert artifact["missing_fields"] == []


def test_phase15ap_opportunity_missing_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    _, feature_path = _pm_inputs(tmp_path, symbols=("6522",))

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=tmp_path / "missing_opportunity.json",
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_opportunity_artifact_missing"
    assert "pm_opportunity_source" in artifact["missing_fields"]


def test_phase15ap_opportunity_review_required_blocks_pm(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), opportunity_status="REVIEW_REQUIRED")

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert artifact["input_contract"]["pm_opportunity_status"] == "REVIEW_REQUIRED"


def test_phase15ap_hidden_default_fields_are_not_used(tmp_path):
    position = _position("6522")
    position.pop("holding_days")
    position.pop("peak_return")
    position.pop("current_price")
    position.pop("market_value")
    runtime_root = _runtime_root(tmp_path, positions=[position])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",))

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert "current.positions[6522].holding_days" in artifact["missing_fields"]
    assert "current.positions[6522].peak_return" in artifact["missing_fields"]
    assert "current.positions[6522].current_price" in artifact["missing_fields"]
    assert artifact["defaulted_fields"] == []


def test_phase19_bu_pm_required_technical_feature_missing_fails_closed(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",))
    feature = pd.read_csv(feature_path).drop(columns=["price_momentum_return_5d"])
    feature.to_csv(feature_path, index=False)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "pm_feature_required_columns_missing"
    assert "pm_feature.price_momentum_return_5d" in artifact["missing_fields"]
    assert artifact["required_feature_validation"]["status"] == "FAIL"


def test_phase19_bu_pm_future_feature_data_rejected(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",))
    feature = pd.read_csv(feature_path)
    feature["feature_as_of_date"] = "2026-07-10"
    feature.to_csv(feature_path, index=False)

    result = produce_position_management_decisions(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
    )
    artifact = _read_json(result.artifact_path)

    assert result.status == "REVIEW_REQUIRED"
    assert artifact["temporal_validation_status"] == "FAIL"
    assert "temporal_validation_failed" in artifact["required_feature_validation"]["reasons"]


def test_phase19_bu_pm_technical_features_affect_score_path(tmp_path):
    positive_runtime_root = _runtime_root(tmp_path / "positive_runtime", positions=[_position("6522", average_price=1000, current_price=1020)])
    negative_runtime_root = _runtime_root(tmp_path / "negative_runtime", positions=[_position("6522", average_price=1000, current_price=1020)])
    high_vol_runtime_root = _runtime_root(tmp_path / "high_vol_runtime", positions=[_position("6522", average_price=1000, current_price=1020)])
    positive_opportunity, positive_feature = _pm_inputs(tmp_path / "positive", symbols=("6522",), expected_edge=0.08, downside=0.2)
    negative_opportunity, negative_feature = _pm_inputs(
        tmp_path / "negative",
        symbols=("6522",),
        expected_edge=0.08,
        downside=0.2,
        technicals={
            "price_momentum_return_5d": -0.08,
            "price_momentum_return_20d": -0.12,
            "trend_close_over_ma_20d": 0.94,
            "trend_ma_5_20_ratio": 0.94,
            "volume_momentum_ratio_5d": 1.0,
            "volatility_return_std_20d": 0.02,
        },
    )
    high_vol_opportunity, high_vol_feature = _pm_inputs(
        tmp_path / "high_vol",
        symbols=("6522",),
        expected_edge=0.08,
        downside=0.2,
        technicals={"volatility_return_std_20d": 0.16},
    )

    positive = produce_position_management_decisions(
        runtime_root=positive_runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=positive_opportunity,
        feature_path=positive_feature,
    )
    negative = produce_position_management_decisions(
        runtime_root=negative_runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=negative_opportunity,
        feature_path=negative_feature,
    )
    high_vol = produce_position_management_decisions(
        runtime_root=high_vol_runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=high_vol_opportunity,
        feature_path=high_vol_feature,
    )
    positive_action = pd.read_csv(Path(positive.action_csv_path)).iloc[0]
    negative_action = pd.read_csv(Path(negative.action_csv_path)).iloc[0]
    high_vol_action = pd.read_csv(Path(high_vol.action_csv_path)).iloc[0]

    assert positive.status == "PASS"
    assert negative.status == "PASS"
    assert high_vol.status == "PASS"
    assert float(positive_action["hold_score"]) > float(negative_action["hold_score"])
    assert float(negative_action["exit_score"]) > float(positive_action["exit_score"])
    assert float(high_vol_action["reduce_score"]) > float(positive_action["reduce_score"])


def test_phase19_bu_pm_feature_contract_mode_parity(tmp_path):
    for mode in ("historical", "demo", "production"):
        runtime_root = _runtime_root(tmp_path / f"rt_{mode}", positions=[_position("6522")])
        opportunity_path, feature_path = _pm_inputs(tmp_path / f"inputs_{mode}", symbols=("6522",))
        result = produce_position_management_decisions(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode=mode,
            opportunity_path=opportunity_path,
            feature_path=feature_path,
        )
        artifact = _read_json(result.artifact_path)
        assert result.status == "PASS"
        assert artifact["feature_contract_version"] == "runtime_v2_pm_feature_input_contract_v2"
        assert artifact["input_contract"]["pm_required_feature_validation"]["status"] == "PASS"


def test_phase15ap_cli_does_not_enter_sell_planning_on_pm_review_required(tmp_path):
    runtime_root = _runtime_root(tmp_path, positions=[_position("6522")])
    opportunity_path, feature_path = _pm_inputs(tmp_path, symbols=("6522",), feature_symbols=())
    policy_path = _write_policy(tmp_path / "capital_deployment.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "sell_planning",
            "--business-date",
            BUSINESS_DATE,
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--pm-opportunity-path",
            str(opportunity_path),
            "--pm-feature-path",
            str(feature_path),
        ]
    )
    manifest = _latest_manifest(runtime_root)
    stage_names = {stage["name"] for stage in manifest["stages"]}

    assert exit_code == 20
    assert manifest["pm_status"] == "REVIEW_REQUIRED"
    assert manifest["pm_input_schema_status"] == "REVIEW_REQUIRED"
    assert "runtime_data_readiness_gate" in stage_names
    assert "position_management_ai_runtime_producer" not in stage_names
    assert "sell_planning_pending_pipeline" not in stage_names


def _runtime_root(tmp_path: Path, *, positions: list[dict[str, Any]], current_as_of: str = BUSINESS_DATE) -> Path:
    root = tmp_path / ".runtime"
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15ap",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": current_as_of,
            "updated_at": current_as_of + "T00:00:00Z",
            "positions": positions,
            "cash": 500000,
            "buying_power": 500000,
            "market_value": sum(float(item.get("market_value") or 0) for item in positions),
            "total_equity": 500000 + sum(float(item.get("market_value") or 0) for item in positions),
            "review_required": False,
        },
    )
    _write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "items": []})
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED"})
    _write_safety_decision(root)
    for name in ("orders", "executions", "cash", "events", "positions"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _position(symbol: str, *, quantity: float = 100, average_price: float = 1000, current_price: float = 850) -> dict[str, Any]:
    current_return = (current_price / average_price) - 1.0
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "current_price": current_price,
        "market_value": quantity * current_price,
        "unrealized_pnl": (current_price - average_price) * quantity,
        "holding_days": 12,
        "peak_return": max(current_return, 0.0),
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": BUSINESS_DATE,
    }


def _pm_inputs(
    tmp_path: Path,
    *,
    symbols: tuple[str, ...],
    feature_symbols: tuple[str, ...] | None = None,
    expected_edge: float = -0.05,
    downside: float = 0.8,
    include_no_position_reason: bool = True,
    opportunity_status: str = "CSV",
    technicals: dict[str, float] | None = None,
) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    if opportunity_status == "REVIEW_REQUIRED":
        opportunity_path = tmp_path / "pm_opportunity.json"
        _write_json(
            opportunity_path,
            {
                "status": "REVIEW_REQUIRED",
                "review_required": True,
                "feature_date": BUSINESS_DATE,
                "model_version": "opportunity_fixture",
                "generated_at": BUSINESS_DATE + "T00:00:00Z",
                "rankings": [],
            },
        )
    else:
        opportunity_path = tmp_path / "pm_opportunity.csv"
        pd.DataFrame(
            [
                {
                    "target_date": BUSINESS_DATE,
                    "code": symbol,
                    "expected_edge_score": expected_edge,
                    "buy_rank": 999,
                    "downside_risk_score": downside,
                    "risk_guard_status": "high_risk" if downside >= 0.7 else "ok",
                    "candidate_score": 0.5,
                    "candidate_rank": 999,
                    "buy_reason": "",
                    "no_buy_reason": "",
                    "calibration_policy_name": "fixture",
                }
                for symbol in symbols
            ]
        ).to_csv(opportunity_path, index=False)
    feature_path = tmp_path / "pm_feature.csv"
    selected_feature_symbols = symbols if feature_symbols is None else feature_symbols
    technical_values = {
        "price_momentum_return_5d": 0.08,
        "price_momentum_return_20d": 0.12,
        "trend_close_over_ma_20d": 1.05,
        "trend_ma_5_20_ratio": 1.03,
        "volume_momentum_ratio_5d": 1.1,
        "volatility_return_std_20d": 0.02,
    }
    technical_values.update(technicals or {})
    feature_rows = [
        {
            "target_date": BUSINESS_DATE,
            "feature_as_of_date": BUSINESS_DATE,
            "as_of_date": BUSINESS_DATE,
            "code": symbol,
            **technical_values,
            "feature_source_artifact": "candidate_features.parquet",
            "feature_source_hash": "fixture-candidate-feature-hash",
            "required_features": json.dumps(sorted(technical_values)),
            "optional_features": json.dumps(["no_position_reason"]),
            "missing_features": "[]",
            "defaulted_features": "[]",
            "temporal_validation_status": "PASS",
            "feature_version": "runtime_v2_pm_feature_input_v2_technical_complete",
            "data_until": BUSINESS_DATE,
            "created_at": BUSINESS_DATE + "T00:00:00Z",
        }
        for symbol in selected_feature_symbols
    ]
    frame = pd.DataFrame(feature_rows)
    if frame.empty:
        columns = [
            "target_date",
            "feature_as_of_date",
            "as_of_date",
            "code",
            *technical_values.keys(),
            "feature_source_artifact",
            "feature_source_hash",
            "required_features",
            "optional_features",
            "missing_features",
            "defaulted_features",
            "temporal_validation_status",
            "feature_version",
            "data_until",
            "created_at",
        ]
        if include_no_position_reason:
            columns.append("no_position_reason")
        frame = pd.DataFrame(columns=columns)
    frame.to_csv(feature_path, index=False)
    return opportunity_path, feature_path


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )
    return path


def _write_safety_decision(root: Path) -> None:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase15ap-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": BUSINESS_DATE,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15ap fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": BUSINESS_DATE + "T00:00:00+09:00",
            "expires_at": "2026-07-10T00:00:00+09:00",
        },
    )


def _write_position_campaigns(
    evidence_root: Path,
    *,
    symbol: str,
    campaign_id: str,
    run_id: str,
    business_date: str,
    extra_campaign_ids: tuple[str, ...] = (),
) -> None:
    campaigns = [
        {
            "position_campaign_id": item_campaign_id,
            "campaign_id": item_campaign_id,
            "symbol": symbol,
            "campaign_status": "OPEN",
            "opened_business_date": "2026-07-01",
            "current_quantity": 100,
            "events": [{"business_date": "2026-07-01", "side": "BUY", "stage": "BUY"}],
        }
        for item_campaign_id in (campaign_id, *extra_campaign_ids)
    ]
    _write_json(
        evidence_root / "daily" / business_date / "positions" / "position_campaigns.json",
        {
            "schema_version": "position_campaign_observability.v1",
            "contract_version": "phase32_bv_run_scoped_campaign_authority_fixture.v1",
            "business_date": business_date,
            "run_id": run_id,
            "authority": "CANONICAL_PRE_ACTION_POSITION_CAMPAIGN_LIFECYCLE",
            "position_campaigns": campaigns,
            "temporal_safety": {
                "temporal_stage": "PRE_ACTION_DECISION_SNAPSHOT",
                "same_day_eod_campaign_reconstruction_used": False,
                "future_information_used": False,
            },
        },
    )


def _strategy_intelligence(
    symbol: str,
    *,
    campaign_id: str,
    run_id: str,
    trend_state: str,
    relative_strength_state: str,
    participation_quality_state: str,
    participation_risk_state: str,
    current_campaign_relative_return: float,
) -> dict[str, Any]:
    return {
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "run_id": run_id,
        "profile_id": "historical-smoke",
        "future_information_used": False,
        "symbol_intelligence": {
            symbol: {
                "expected_edge": {"status": "ADEQUATE", "future_information_used": False},
                "entry_admission": {
                    "entry_state": "CONTINUATION_WITH_CAUTION",
                    "admission_action": "ADD_REDUCED_ONLY",
                    "future_information_used": False,
                    "consumed_evidence": {"strong_medium_term_structure": False},
                },
                "continuation_quality": {
                    "status": "PASS",
                    "trend_health": {"state": trend_state, "as_of_date": BUSINESS_DATE},
                    "relative_strength": {"state": relative_strength_state, "as_of_date": BUSINESS_DATE},
                    "participation_quality": {"state": participation_quality_state, "as_of_date": BUSINESS_DATE},
                    "exhaustion_risk": {"state": "MIXED", "as_of_date": BUSINESS_DATE},
                    "persistence": {"state": "MIXED", "as_of_date": BUSINESS_DATE},
                    "future_information_used": False,
                },
                "downside_risk": {
                    "status": "PASS",
                    "participation_risk": {"state": participation_risk_state, "as_of_date": BUSINESS_DATE},
                },
                "lifecycle_context": {
                    "position_campaign_id": campaign_id,
                    "campaign_identity_authority_status": "COMPLETE",
                    "campaign_age_business_days": 20,
                    "current_campaign_relative_return": current_campaign_relative_return,
                },
            }
        },
    }


def _market_context(*, run_id: str) -> dict[str, Any]:
    return {
        "business_date": BUSINESS_DATE,
        "feature_date": BUSINESS_DATE,
        "run_id": run_id,
        "profile_id": "historical-smoke",
        "trend_regime": "RECOVERY",
        "regime_state": "RECOVERY",
    }


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return _read_json(manifests[-1])


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
