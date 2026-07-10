from pathlib import Path

from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy


NEW_POLICY_PATH = Path("configs/runtime_v2/capital_deployment.json")
OLD_DEMO_POLICY = "capital_deployment_demo.json"


def test_phase15ab_new_capital_deployment_policy_loads_with_runtime_reality_name():
    policy = load_capital_deployment_policy(NEW_POLICY_PATH)

    assert policy.policy_version == "capital_deployment_v1"
    assert policy.policy_source == "configs/runtime_v2/capital_deployment.json"
    assert policy.loaded_from == str(NEW_POLICY_PATH)
    assert policy.max_buy_order_amount is None
    assert policy.max_sell_liquidation_amount is None
    assert policy.buy_notional_policy == "derived_from_capital_allocation_and_constraints"
    assert policy.sell_liquidation_policy == "current_owned_available_quantity_policy"


def test_phase15ab_acceptance_docs_do_not_use_demo_policy_as_normal_policy():
    acceptance_docs = (
        Path("docs/phase_reports/phase15_u_demo_runtime_review_plan.md"),
        Path("docs/phase_reports/phase15_v_purpose_level_runtime_acceptance_meta_review.md"),
        Path("docs/phase_reports/phase15_w_demo_runtime_review_plan_amendment.md"),
        Path("docs/phase_reports/phase15_x_runtime_reality_rule_demo_production_boundary_contract.md"),
        Path("docs/phase_reports/phase15_y_non_trading_day_demo_acceptance_override.md"),
        Path("docs/phase_reports/phase15_aa_step0_preflight_evidence_review.md"),
    )

    for path in acceptance_docs:
        assert OLD_DEMO_POLICY not in path.read_text(encoding="utf-8")


def test_phase15ab_runtime_core_does_not_hardcode_demo_policy_path():
    for root in (Path("src/ai_fund_lab_v2/runtime_v2"), Path("tests/runtime_v2")):
        for path in root.rglob("*.py"):
            if path.resolve() == Path(__file__).resolve():
                continue
            assert OLD_DEMO_POLICY not in path.read_text(encoding="utf-8")
