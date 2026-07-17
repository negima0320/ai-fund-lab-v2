from dataclasses import fields
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.planning.models import PlanningInput
from ai_fund_lab_v2.runtime_v2.planning.planner import build_order_plan
from tests.runtime_v2.planning_fixtures import make_planning_input, make_runtime_safety
from tests.runtime_v2.test_phase15k_morning_policy_propagation_hidden_policy_removal import (
    _load_json,
    _run_morning,
    _write_current,
    _write_features,
    _write_policy,
)
from tests.runtime_v2.feature_date_contract_helpers import materialize_feature_date_contract


def test_phase15p_planning_source_has_no_safety_signal_placeholder_allow():
    source_paths = [
        Path("src/ai_fund_lab_v2/runtime_v2/planning/models.py"),
        Path("src/ai_fund_lab_v2/runtime_v2/planning/planner.py"),
        Path("src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py"),
        Path("src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py"),
        Path("src/ai_fund_lab_v2/runtime_v2/simulation/harness.py"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    assert "class SafetySignal" not in combined
    assert "SafetySignal(" not in combined
    assert "safety_signals" not in combined
    assert "placeholder allow" not in combined


def test_phase15p_planning_input_receives_runtime_safety_context():
    field_names = {field.name for field in fields(PlanningInput)}

    assert "runtime_safety" in field_names
    assert "safety_signals" not in field_names

    runtime_safety = make_runtime_safety()
    result = build_order_plan(make_planning_input(runtime_safety=runtime_safety))

    assert result.order_plan.safety_decision_id == runtime_safety.safety_decision_id
    assert result.order_plan.safety_policy_version == runtime_safety.safety_policy_version
    assert result.order_plan.safety_source == runtime_safety.safety_source


def test_phase15p_orderplan_pending_approval_preserve_runtime_safety_context(tmp_path):
    runtime_root = _write_current(tmp_path / ".runtime")
    feature_root = _write_features(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        candidate_codes=("7203", "6501"),
        price=1000,
    )
    materialize_feature_date_contract(runtime_root, business_date="2026-07-09", selected_feature_date="2026-07-08")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json", max_positions=2)

    assert _run_morning(tmp_path, runtime_root, feature_root, policy_path) == 0

    order_plan = _load_json(runtime_root / "runtime_state" / "morning_pipeline" / "2026-07-09" / "order_plan.json")
    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    approval = _load_json(runtime_root / "runtime_state" / "morning_pipeline" / "2026-07-09" / "approval_artifact.json")

    assert order_plan["safety_decision_id"] == "safety-phase15k-fixture"
    assert order_plan["safety_policy_version"] == "safety_policy_v1"
    assert order_plan["safety_decision"] == "ALLOW"
    assert order_plan["items"][0]["safety_decision_id"] == "safety-phase15k-fixture"
    assert order_plan["items"][0]["safety_policy_version"] == "safety_policy_v1"

    assert pending["safety_decision_id"] == "safety-phase15k-fixture"
    assert pending["safety_policy_version"] == "safety_policy_v1"
    assert pending["safety_context"]["safety_decision_id"] == "safety-phase15k-fixture"
    assert pending["items"][0]["safety_decision_id"] == "safety-phase15k-fixture"
    assert pending["items"][0]["safety_policy_version"] == "safety_policy_v1"

    assert approval["safety_decision_id"] == "safety-phase15k-fixture"
    assert approval["safety_policy_version"] == "safety_policy_v1"
    assert pending["approval"]["safety_decision_id"] == "safety-phase15k-fixture"
    assert pending["approval"]["safety_policy_version"] == "safety_policy_v1"
