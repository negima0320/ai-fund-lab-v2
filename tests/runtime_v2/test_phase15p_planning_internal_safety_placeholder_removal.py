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
