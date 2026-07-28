from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.strategy import capital_deployment, portfolio_construction, portfolio_policy, position_management, runtime_planning
from ai_fund_lab_v2.strategy.runtime_planning import (
    RuntimePlanningConsumerError,
    RuntimePlanningSchemaError,
    RuntimePlanningSourceSummary,
    build_runtime_planning_payload,
    default_runtime_artifact_path,
    load_runtime_planning_fixture,
    validate_runtime_planning_artifact,
    verify_source_hashes,
)


def test_phase22_g_produces_draft_pass_not_eligible_shadow_artifact(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert result.status == "PASS"
    assert result.payload["artifact_lifecycle_status"] == "DRAFT"
    assert result.payload["runtime_consumer_eligibility"] == "NOT_ELIGIBLE"
    assert result.payload["downstream_calculation_eligibility"] == "CALCULATION_ALLOWED_WITH_REVIEW"
    assert result.payload["concrete_allocation_decided"] is False
    assert result.payload["concrete_quantity_decided"] is False
    assert result.payload["lot_rounding_decided"] is False
    assert result.payload["pending_written"] is False
    assert result.payload["submit_generated"] is False
    assert validate_runtime_planning_artifact(result.payload)["status"] == "PASS"


def test_phase22_g_schema_rejects_invalid_intent_status_and_concrete_fields(tmp_path: Path) -> None:
    payload = _produce(tmp_path).payload
    mutations = (
        lambda item: item["plans"][0].update({"planning_intent": "BUY"}),
        lambda item: item["plans"][0].update({"order_side_intent": "BID"}),
        lambda item: item["plans"][0].pop("planning_id"),
        lambda item: item["plans"][0].pop("security_code"),
        lambda item: item.update({"schema_version": "runtime_planning.v999"}),
        lambda item: item.update({"runtime_consumer_eligibility": "ELIGIBLE"}),
        lambda item: item.update({"allocation_jpy": 100000}),
        lambda item: item["plans"][0].update({"quantity": 100}),
        lambda item: item["plans"][0].update({"lot_rounding_result": 100}),
        lambda item: item.update({"pending_written": True}),
        lambda item: item.update({"submit_generated": True}),
        lambda item: item["plans"][0]["pending_candidate_contract"].update({"pending_writer_connected": True}),
    )
    for mutation in mutations:
        mutated = json.loads(json.dumps(payload))
        mutation(mutated)
        with pytest.raises(RuntimePlanningSchemaError):
            validate_runtime_planning_artifact(mutated)


def test_phase22_g_pm_and_portfolio_mapping_taxonomy(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"7203": "HOLD", "6758": "ADD", "8306": "REDUCE", "9432": "EXIT"},
        pc_members={
            "7203": ("RETAIN", True),
            "6758": ("RETAIN", True),
            "8306": ("RETAIN", True),
            "9432": ("RETAIN", True),
            "6098": ("ADD_CANDIDATE", False),
            "9984": ("EXCLUDE", False),
        },
        current_codes=("7203", "6758", "8306", "9432"),
    )

    intents = {plan["security_code"]: plan["planning_intent"] for plan in result.payload["plans"]}
    assert intents["7203"] == "NO_ACTION"
    assert intents["6758"] == "BUY_ADD"
    assert intents["8306"] == "SELL_REDUCE"
    assert intents["9432"] == "SELL_EXIT"
    assert intents["6098"] == "BUY_NEW"
    assert "9984" not in intents
    assert result.payload["producer_result_status"] == "REVIEW_REQUIRED"


def test_phase22_g_portfolio_sell_membership_alone_does_not_generate_sell(tmp_path: Path) -> None:
    result = _produce(
        tmp_path,
        pm_actions={"8306": "HOLD"},
        pc_members={"8306": ("REMOVE_CANDIDATE", True)},
        current_codes=("8306",),
    )

    plan = result.payload["plans"][0]
    assert plan["planning_intent"] == "UNRESOLVED"
    assert "planning_conflict_review:portfolio_membership_requires_pm_sell_intent:8306" in plan["reason_codes"]
    assert all(plan["planning_intent"] not in {"SELL_REDUCE", "SELL_EXIT"} for plan in result.payload["plans"])


def test_phase22_g_conflicts_and_current_position_guards_fail_closed(tmp_path: Path) -> None:
    add_missing = _produce(
        tmp_path / "add_missing",
        pm_actions={"6758": "ADD"},
        pc_members={"6758": ("RETAIN", False)},
        current_codes=(),
    )
    sell_missing = _produce(
        tmp_path / "sell_missing",
        pm_actions={"8306": "REDUCE"},
        pc_members={"8306": ("RETAIN", True)},
        current_codes=(),
    )
    pending_conflict = _produce(
        tmp_path / "pending_conflict",
        pm_actions={"6758": "ADD"},
        pc_members={"6758": ("RETAIN", True)},
        current_codes=("6758",),
        pending_codes=("6758",),
    )

    assert add_missing.payload["producer_result_status"] == "BLOCK"
    assert "add_without_current_position:6758" in add_missing.payload["reason_codes"]
    assert sell_missing.payload["producer_result_status"] == "BLOCK"
    assert "missing_current_position_for_sell:8306" in sell_missing.payload["reason_codes"]
    assert pending_conflict.payload["producer_result_status"] == "REVIEW_REQUIRED"
    assert "existing_pending_conflict:6758" in pending_conflict.payload["reason_codes"]


def test_phase22_g_quantity_authority_boundary_never_decides_quantity(tmp_path: Path) -> None:
    payload = _produce(tmp_path, pm_actions={"6758": "ADD"}, pc_members={"6758": ("RETAIN", True)}, current_codes=("6758",)).payload
    plan = payload["plans"][0]

    assert plan["quantity_required"] is True
    assert plan["quantity_authority"] == "PHASE22_J_OR_DOWNSTREAM"
    assert plan["quantity_status"] == "UNRESOLVED"
    assert "quantity" not in plan
    assert "allocation_jpy" not in plan
    assert payload["concrete_quantity_decided"] is False


def test_phase22_g_upstream_review_not_eligible_and_block_propagate(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    assert result.payload["producer_result_status"] == "PASS"
    assert "upstream_review_required:SOURCE_NOT_ELIGIBLE" not in result.payload["reason_codes"]
    assert result.payload["consumer_eligibility_reason_codes"] == ["SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE"]
    with pytest.raises(RuntimePlanningConsumerError):
        load_runtime_planning_fixture(result.artifact_path, for_production=True)

    bad_cd = Path(_write_capital_deployment(tmp_path / "bad_cd", pm_actions={"7203": "HOLD"}, current_codes=("7203",)))
    mutated = json.loads(bad_cd.read_text(encoding="utf-8"))
    mutated["members"][0]["allocation_posture"] = "WITHHOLD"
    _write_json(bad_cd, mutated)
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path / "bad_cd", {"7203": ("RETAIN", True)}),
        capital_deployment_artifact_path=bad_cd,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path / "bad_cd"),
        position_management_artifact_path=_write_position_management(tmp_path / "bad_cd", {"7203": "HOLD"}),
        current_portfolio_summary=_summary(tmp_path / "bad_cd", "portfolio"),
        current_cash_summary=_summary(tmp_path / "bad_cd", "cash"),
        current_position_summary=_summary(tmp_path / "bad_cd", "position", rows=({"security_code": "7203"},)),
        pending_summary=_summary(tmp_path / "bad_cd", "pending"),
        planning_config_summary=_summary(tmp_path / "bad_cd", "planning_config"),
    )
    assert payload["producer_result_status"] == "BLOCK"
    assert "upstream_block:INCOMPATIBLE_HASH" in payload["reason_codes"]


def test_phase22_g_date_pit_blocks_future_current_and_pending(tmp_path: Path) -> None:
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"7203": ("RETAIN", True)}),
        capital_deployment_artifact_path=_write_capital_deployment(tmp_path, pm_actions={"7203": "HOLD"}, current_codes=("7203",)),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {"7203": "HOLD"}),
        current_portfolio_summary=_summary(tmp_path, "portfolio", feature_date="2026-07-16"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position", rows=({"security_code": "7203"},)),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert "current_portfolio_date_mismatch" in payload["reason_codes"]
    assert "future_current_or_pending_date_detected" in payload["reason_codes"]
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False
    assert payload["temporal_safety"]["previous_day_runtime_planning_copied"] is False


def test_phase22_g_hash_lineage_and_artifact_hash_validation(tmp_path: Path) -> None:
    result = _produce(tmp_path)

    assert verify_source_hashes(result.payload)["status"] == "PASS"
    assert result.payload["artifact_hash"] == runtime_planning.runtime_planning_hash(result.payload)
    changed = json.loads(json.dumps(result.payload))
    changed["source_hashes"][0]["sha256"] = "deadbeef"
    assert verify_source_hashes(changed)["status"] == "BLOCK"


def test_phase22_g_bootstrap_missing_inputs_does_not_use_fixed_fallbacks(tmp_path: Path) -> None:
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=None,
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=None,
        position_management_artifact_path=None,
        current_portfolio_summary=_summary(tmp_path, "portfolio", status="REVIEW_REQUIRED"),
        current_cash_summary=_summary(tmp_path, "cash", status="REVIEW_REQUIRED"),
        current_position_summary=_summary(tmp_path, "position", status="REVIEW_REQUIRED"),
        pending_summary=_summary(tmp_path, "pending", status="REVIEW_REQUIRED"),
        planning_config_summary=_summary(tmp_path, "planning_config", status="REVIEW_REQUIRED"),
    )

    assert payload["producer_result_status"] == "BLOCK"
    assert payload["plans"] == []
    assert payload["temporal_safety"]["implicit_latest_fallback_used"] is False
    assert payload["temporal_safety"]["previous_day_runtime_planning_copied"] is False


def test_phase22_g_existing_authorities_and_fixture_shadow_preserved(tmp_path: Path) -> None:
    result = _produce(tmp_path)
    payload = load_runtime_planning_fixture(result.artifact_path)

    assert payload["production_consumer_connected"] is False
    assert payload["pending_writer_connected"] is False
    assert payload["runtime_switch_performed"] is False
    assert payload["legacy_authority_active"] is True
    assert payload["existing_morning_planning_changed"] is False
    assert payload["existing_add_planning_changed"] is False
    assert payload["existing_sell_planning_changed"] is False
    assert payload["pending_changed"] is False
    assert payload["approval_changed"] is False
    assert payload["submit_changed"] is False
    assert payload["execution_changed"] is False
    evidence = runtime_planning.produced_but_not_consumed_evidence(payload)
    assert evidence["runtime_planning_production_consumer_connected"] is False
    assert evidence["pending_written"] is False
    assert evidence["submit_generated"] is False


def _produce(
    tmp_path: Path,
    *,
    pm_actions: dict[str, str] | None = None,
    pc_members: dict[str, tuple[str, bool]] | None = None,
    current_codes: tuple[str, ...] = ("7203",),
    pending_codes: tuple[str, ...] = (),
):
    pm_actions = pm_actions or {"7203": "HOLD", "6098": "HOLD"}
    pc_members = pc_members or {"7203": ("RETAIN", True), "6098": ("ADD_CANDIDATE", False)}
    return runtime_planning.produce_runtime_planning_artifact(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, pc_members),
        capital_deployment_artifact_path=_write_capital_deployment(tmp_path, pm_actions=pm_actions, current_codes=current_codes, pc_members=pc_members),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, pm_actions),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(tmp_path, "position", rows=tuple({"security_code": code} for code in current_codes)),
        pending_summary=_summary(tmp_path, "pending", rows=tuple({"security_code": code} for code in pending_codes)),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        output_path=default_runtime_artifact_path(tmp_path / ".runtime", "2026-07-15"),
    )


def _summary(
    tmp_path: Path,
    kind: str,
    *,
    status: str = "PASS",
    business_date: str = "2026-07-15",
    feature_date: str = "2026-07-15",
    rows: tuple[dict[str, object], ...] = (),
) -> RuntimePlanningSourceSummary:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"{kind}_summary.json"
    payload = {"kind": kind, "business_date": business_date, "feature_date": feature_date, "status": status, "rows": list(rows)}
    _write_json(path, payload)
    return RuntimePlanningSourceSummary(status, business_date, feature_date, str(path), _sha256_file(path), rows)


def _write_capital_deployment(
    tmp_path: Path,
    *,
    pm_actions: dict[str, str],
    current_codes: tuple[str, ...],
    pc_members: dict[str, tuple[str, bool]] | None = None,
) -> Path:
    return capital_deployment.produce_capital_deployment_artifact(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, pc_members or {code: ("RETAIN", True) for code in set(pm_actions) | set(current_codes)}),
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, pm_actions),
        current_cash_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "cash_cd")), _sha256_file(_write_source(tmp_path, "cash_cd")), {}),
        current_exposure_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "exposure_cd")), _sha256_file(_write_source(tmp_path, "exposure_cd")), {}),
        current_portfolio_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "portfolio_cd")), _sha256_file(_write_source(tmp_path, "portfolio_cd")), {}),
        pending_reservation_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "pending_cd")), _sha256_file(_write_source(tmp_path, "pending_cd")), {}),
        policy_config_summary=capital_deployment.CapitalDeploymentSourceSummary("PASS", "2026-07-15", "2026-07-15", str(_write_source(tmp_path, "policy_config_cd")), _sha256_file(_write_source(tmp_path, "policy_config_cd")), {}),
        output_path=tmp_path / "capital_deployment.json",
    ).artifact_path


def _write_portfolio_construction(tmp_path: Path, members: dict[str, tuple[str, bool]]) -> Path:
    source = _write_source(tmp_path, "pc_source")
    payload = {
        "schema_version": portfolio_construction.SCHEMA_VERSION,
        "producer_version": "phase22_e_portfolio_construction_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "portfolio_members": [
            {
                "member_id": f"pc-{code}",
                "security_code": code,
                "current_position": current,
                "membership_intent": intent,
                "construction_priority": index,
                "weight_intent": "MAINTAIN" if intent == "RETAIN" else ("AVOID" if intent == "EXCLUDE" else "INCREASE"),
                "candidate_reference": f"candidate-{code}" if intent == "ADD_CANDIDATE" else "",
                "opportunity_reference": f"opportunity-{code}" if intent == "ADD_CANDIDATE" else "",
                "position_management_reference": f"pm-{code}" if current else "",
                "portfolio_policy_reference": "",
                "confidence": 0.8,
                "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
                "reason_codes": ["fixture"],
            }
            for index, (code, (intent, current)) in enumerate(sorted(members.items()), start=1)
        ],
        "member_count": len(members),
        "membership_intent_taxonomy": sorted(portfolio_construction.MEMBERSHIP_INTENTS),
        "weight_intent_taxonomy": sorted(portfolio_construction.WEIGHT_INTENTS),
        "position_count_policy_reference": "policy",
        "cash_policy_reference": "policy",
        "exposure_policy_reference": "policy",
        "concrete_values_decided": False,
        "position_count_decided": False,
        "cash_ratio_decided": False,
        "exposure_decided": False,
        "position_sizing_decided": False,
        "allocation_decided": False,
        "quantity_decided": False,
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "upstream_artifacts": {},
        "source_artifacts": [{"role": "pc", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "pc", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_portfolio_construction_copied": False},
        "production_consumer_connected": False,
        "runtime_switch_performed": False,
        "legacy_authority_active": True,
    }
    payload["artifact_hash"] = portfolio_construction.portfolio_construction_hash(payload)
    path = tmp_path / "portfolio_construction.json"
    _write_json(path, payload)
    return path


def _write_portfolio_policy(tmp_path: Path) -> Path:
    source = _write_source(tmp_path, "policy_source")
    payload = {
        "schema_version": portfolio_policy.SCHEMA_VERSION,
        "producer_version": "phase22_c_portfolio_policy_producer.v1",
        "business_date": "2026-07-15",
        "as_of": "2026-07-15T00:00:00+00:00",
        "feature_date": "2026-07-15",
        "artifact_lifecycle_status": "DRAFT",
        "source_authority_status": "VALID",
        "producer_result_status": "REVIEW_REQUIRED",
        "runtime_consumer_eligibility": "NOT_ELIGIBLE",
        "risk_posture": "BALANCED",
        "entry_posture": "MAINTAIN",
        "position_count_posture": "MAINTAIN",
        "cash_posture": "MAINTAIN",
        "exposure_posture": "MAINTAIN",
        "position_management_bias": "NEUTRAL",
        "confidence": 0.0,
        "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "deferred_concrete_values": [],
        "concrete_values_decided": False,
        "upstream_artifacts": {},
        "source_artifacts": [{"role": "policy", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "policy", "path": str(source), "sha256": _sha256_file(source)}],
        "temporal_safety": {"point_in_time": True, "future_leakage_used": False, "feature_date_lte_business_date": True, "implicit_latest_fallback_used": False, "previous_day_policy_copied": False},
    }
    payload["artifact_hash"] = portfolio_policy.portfolio_policy_hash(payload)
    path = tmp_path / "portfolio_policy.json"
    _write_json(path, payload)
    return path


def _write_position_management(tmp_path: Path, actions: dict[str, str]) -> Path:
    source = _write_source(tmp_path, "pm_source")
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
        "positions": [
            {
                "position_id": f"pm-{code}",
                "security_code": code,
                "action": action,
                "intensity": "NONE" if action in {"HOLD", "ADD", "EXIT"} else "MEDIUM",
                "confidence": 0.8,
                "uncertainty": "UPSTREAM_REVIEW_REQUIRED",
                "reason_codes": ["fixture"],
                "lifecycle_reference": "",
                "opportunity_reference": "",
                "market_context_reference": "",
                "corporate_event_reference": "",
                "portfolio_policy_reference": "",
            }
            for code, action in sorted(actions.items())
        ],
        "position_count": len(actions),
        "action_taxonomy": sorted(position_management.PM_ACTIONS),
        "intensity_taxonomy": sorted(position_management.PM_INTENSITIES),
        "quantity_decided": False,
        "minimum_holding_decided": False,
        "cooldown_decided": False,
        "reason_codes": ["upstream_review_required:SOURCE_NOT_ELIGIBLE"],
        "upstream_artifacts": {},
        "accepted_generation_reference": {},
        "model_reference": {},
        "scaler_reference": {},
        "source_artifacts": [{"role": "pm", "path": str(source), "required": True, "status": "PASS"}],
        "source_hashes": [{"role": "pm", "path": str(source), "sha256": _sha256_file(source)}],
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


def _write_source(tmp_path: Path, name: str) -> Path:
    path = tmp_path / f"{name}.json"
    _write_json(path, {"source": name})
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
