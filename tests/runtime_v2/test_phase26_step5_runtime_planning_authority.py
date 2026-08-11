from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import activate_strategy_planning_authority
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from tests.runtime_v2.test_phase23_i_strategy_planning_authority import (
    BUSINESS_DATE,
    _demo_safety_payload,
    _historical_context,
    _historical_safety_payload,
    _position_sizing_row,
    _runtime_root_for_data_readiness,
    _submit_policy_payload,
    _write_capital_policy,
    _write_current_cash,
    _write_json,
    _write_listed_issues_parquet,
    _write_position_sizing_many,
    _write_strategy_source_input_manifest,
)
from tests.strategy.test_phase22_g_runtime_planning import _produce as produce_runtime_planning_fixture


def test_phase26_step5_strategy_runtime_planning_mode_parity_uses_common_authorities(tmp_path: Path) -> None:
    evidence = []
    for mode in ("production", "demo", "historical"):
        runtime_root = _runtime_root_for_data_readiness(tmp_path / mode)
        _write_current_cash(runtime_root, cash=2_000_000)
        strategy_dir = tmp_path / mode / "strategy"
        strategy_dir.mkdir(parents=True)
        policy = load_capital_deployment_policy(
            _write_capital_policy(tmp_path / mode / "capital_deployment_policy.json", evaluation_capital=2_000_000)
        )
        runtime_plan = produce_runtime_planning_fixture(
            tmp_path / mode / "rp",
            pm_actions={"31330": "HOLD"},
            pc_members={"31330": ("ADD_CANDIDATE", False)},
            current_codes=(),
            position_sizing_positions={
                "31330": _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)
            },
        )
        Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
        _write_position_sizing_many(strategy_dir / "position_sizing.json", symbols=("31330",), target_notional=120_000.0)

        result = activate_strategy_planning_authority(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode=mode,
            strategy_dir=strategy_dir,
            environment_capability_context=_environment_context(mode, tmp_path),
            safety_authority_payload=_safety_payload(mode, tmp_path),
            submit_policy_authority_payload=_submit_policy_payload(policy),
        )
        pending = read_pending_order_plan_path(
            path=runtime_root / "pending_order_plan" / "pending_order_plan.json",
            environment=mode,
        )
        assert result.status == "PASS"
        assert pending.plan is not None
        contract = pending.plan.items[0].quantity_contract
        assert contract is not None
        evidence.append(
            {
                "mode": mode,
                "planning_authority_winner": contract["planning_authority_winner"],
                "planning_consumer": contract["planning_consumer"],
                "planning_fallback_used": contract["planning_fallback_used"],
                "legacy_planning_used": contract["legacy_planning_used"],
                "position_count_runtime_path": contract["position_count_runtime_path"],
                "cash_exposure_runtime_path": contract["cash_exposure_runtime_path"],
                "position_sizing_runtime_path": contract["position_sizing_runtime_path"],
                "position_count_authority_winner": contract["position_count_authority_winner"],
                "cash_exposure_authority_winner": contract["cash_exposure_authority_winner"],
                "position_sizing_authority_winner": contract["position_sizing_authority_winner"],
            }
        )

    assert {item["planning_authority_winner"] for item in evidence} == {"strategy_runtime_planning"}
    assert {item["planning_consumer"] for item in evidence} == {
        "runtime_v2.planning.strategy_authority.activate_strategy_planning_authority"
    }
    assert {item["position_count_runtime_path"] for item in evidence} == {"Production/Demo/Historical common runtime_v2"}
    assert {item["cash_exposure_runtime_path"] for item in evidence} == {"Production/Demo/Historical common runtime_v2"}
    assert {item["position_sizing_runtime_path"] for item in evidence} == {"Production/Demo/Historical common runtime_v2"}
    assert all(item["planning_fallback_used"] is False and item["legacy_planning_used"] is False for item in evidence)
    assert {item["position_count_authority_winner"] for item in evidence} == {"safety_hard_maximum_only"}
    assert {item["cash_exposure_authority_winner"] for item in evidence} == {"strategy_dynamic_cash_exposure"}
    assert {item["position_sizing_authority_winner"] for item in evidence} == {"strategy_position_sizing"}


def test_phase26_step5_buy_position_sizing_review_does_not_block_sell_planning(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "business_date": BUSINESS_DATE,
            "positions": [{"symbol": "7203", "quantity": 100, "market_value": 100_000}],
            "cash": 1_000_000,
            "buying_power": 1_000_000,
            "market_value": 100_000,
            "total_equity": 1_100_000,
        },
    )
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    listed_issues_path = _write_listed_issues_parquet(
        tmp_path / "listed_issues" / "data.parquet",
        rows=(
            {
                "Date": BUSINESS_DATE,
                "Code": "7203",
                "MktNm": "プライム",
                "ProdCat": "011",
            },
        ),
    )
    _write_strategy_source_input_manifest(
        strategy_dir=strategy_dir,
        business_date=BUSINESS_DATE,
        listed_issues_path=listed_issues_path,
    )
    policy = load_capital_deployment_policy(_write_capital_policy(tmp_path / "capital_deployment_policy.json"))
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"31330": "HOLD", "7203": "EXIT"},
        pc_members={"31330": ("ADD_CANDIDATE", False), "7203": ("RETAIN", True)},
        current_codes=("7203",),
        current_position_rows=({"security_code": "7203", "symbol": "7203", "quantity": 100},),
        position_sizing_positions={
            "31330": _position_sizing_row(target_notional=50_000.0, target_quantity=100, quantity_delta=100),
            "7203": _position_sizing_row(
                target_notional=0.0,
                target_quantity=0,
                quantity_delta=-100,
                quantity_status="RESOLVED_CANDIDATE",
            ),
        },
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing_many(strategy_dir / "position_sizing.json", symbols=("31330", "7203"), target_notional=10_000.0)
    _cap_position_sizing_row(strategy_dir / "position_sizing.json", symbol="31330", amount=10_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        strategy_dir=strategy_dir,
        environment_capability_context={"broker_write": False},
        safety_authority_payload=_demo_safety_payload(),
        submit_policy_authority_payload=_submit_policy_payload(policy),
    )
    pending = read_pending_order_plan_path(
        path=runtime_root / "pending_order_plan" / "pending_order_plan.json",
        environment="demo",
    )
    order_plan = json.loads(Path(result.order_plan_artifact_path).read_text(encoding="utf-8"))

    assert result.status == "PASS"
    assert order_plan["buy_planning_status"] == "PASS"
    assert order_plan["sell_planning_status"] == "PASS"
    assert order_plan["accepted_generation_binding_status"] == "REVIEW_REQUIRED"
    assert pending.plan is not None
    assert pending.plan.state.value == "REVIEW_REQUIRED"
    assert pending.plan.buy_items_status == "REVIEW_REQUIRED"
    assert pending.plan.sell_items_status == "PASS"
    assert pending.plan.sell_continuation_allowed is True
    assert {item.side for item in pending.plan.items} == {"BUY", "SELL"}
    sell_item = next(item for item in pending.plan.items if item.side == "SELL")
    assert sell_item.listed_info is not None
    assert sell_item.listed_info["listed_info_authority"] == "canonical_pit_listed_issues"
    assert sell_item.listed_info["code"] == "7203"


def test_phase26_pf3i_strategy_dir_authorities_flow_to_pending_and_submit_feasibility(tmp_path: Path) -> None:
    runtime_root = _runtime_root_for_data_readiness(tmp_path)
    _write_current_cash(runtime_root, cash=1_000_000)
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    policy = load_capital_deployment_policy(_write_capital_policy(tmp_path / "capital_deployment_policy.json"))
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={"31330": "HOLD"},
        pc_members={"31330": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={
            "31330": _position_sizing_row(
                target_notional=120_000.0,
                target_quantity=100,
                quantity_delta=100,
                reference_price=1000.0,
            )
        },
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing_many(strategy_dir / "position_sizing.json", symbols=("31330",), target_notional=120_000.0)
    _write_strategy_dir_authority_fields(strategy_dir)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        environment_capability_context=_historical_context(tmp_path),
        safety_authority_payload=_historical_safety_payload(tmp_path),
        submit_policy_authority_payload=_submit_policy_payload(policy),
    )
    pending = read_pending_order_plan_path(
        path=runtime_root / "pending_order_plan" / "pending_order_plan.json",
        environment="historical",
    )

    assert result.status == "PASS"
    assert pending.plan is not None
    assert pending.plan.approval is not None
    assert pending.plan.state.value == "APPROVED"
    item = pending.plan.items[0]
    approval_payload = json.loads(Path(result.approval_artifact_path).read_text(encoding="utf-8"))
    approval_conditions = approval_payload["approved_order_conditions"]
    linked_conditions = pending.plan.approval.approved_order_conditions or {}
    approved_condition = approval_conditions[item.pending_item_id]
    assert linked_conditions[item.pending_item_id] == approved_condition
    assert approved_condition["condition_authority"] == "strategy_planning_approval_order_conditions"
    assert approved_condition["condition_consumer"] == "runtime_v2.submit.guards.run_submit_preflight"
    assert approved_condition["issue_code"] == item.symbol
    assert approved_condition["side"] == item.side
    assert approved_condition["order_type"] == item.order_type
    assert approved_condition["quantity"] == item.quantity
    assert approved_condition["target_session"] == pending.plan.target_session_date
    assert approved_condition["price_condition"] == "MARKET"
    assert approved_condition["limit_price"] is None
    assert approved_condition["time_in_force"] == "DAY"
    assert approved_condition["approval_fallback_used"] is False
    assert approved_condition["legacy_approval_used"] is False
    contract = item.quantity_contract or {}
    assert item.quantity == 100.0
    assert item.estimated_amount == 100_000.0
    assert contract["selected_quantity"] == 100
    assert contract["selected_notional"] == 100_000.0
    assert contract["lot_adjusted_quantity"] == 100
    assert contract["lot_adjusted_notional"] == 100_000.0
    assert contract["selected_dynamic_position_count"] == 10
    assert contract["available_position_slots"] == 10
    assert contract["selected_dynamic_cash_ratio"] == 0.5
    assert contract["selected_dynamic_exposure_ratio"] == 0.46
    assert contract["selected_runtime_exposure_limit"] == 460_000.0
    assert contract["selected_position_amount"] == 120_000.0
    assert contract["planning_authority_winner"] == "strategy_runtime_planning"
    assert contract["cash_exposure_authority_winner"] == "strategy_dynamic_cash_exposure"
    assert contract["position_count_authority_winner"] == "safety_hard_maximum_only"
    assert contract["position_sizing_authority_winner"] == "strategy_position_sizing"
    assert contract["legacy_cash_config_used"] is False
    assert contract["legacy_exposure_config_used"] is False
    assert contract["cash_exposure_fallback_used"] is False
    assert contract["position_count_fallback_used"] is False
    assert contract["position_sizing_fallback_used"] is False
    feasibility = pending.plan.planning_submit_feasibility or {}
    assert feasibility["status"] == "PASS"
    assert feasibility["items"][0]["status"] == "PASS"
    assert feasibility["items"][0]["selected_runtime_exposure_limit"] == 460_000.0
    assert feasibility["items"][0]["selected_position_amount"] == 120_000.0
    assert feasibility["items"][0]["estimated_amount"] == 100_000.0


def test_phase26_step5_runtime_planning_artifact_declares_old_path_zero(tmp_path: Path) -> None:
    result = produce_runtime_planning_fixture(tmp_path)
    payload = result.payload

    assert payload["runtime_consumer_eligibility"] == "ELIGIBLE"
    assert payload["pending_writer_connected"] is True
    assert payload["runtime_switch_performed"] is True
    assert payload["legacy_authority_active"] is False
    assert payload["legacy_planning_authority_used"] is False
    assert payload["planning_fallback_used"] is False
    assert payload["planning_config_authority_used"] is False
    assert payload["existing_morning_planning_changed"] is True
    assert payload["existing_add_planning_changed"] is True
    assert payload["planning_authority_winner"] == "strategy_runtime_planning"
    assert payload["upstream_artifacts"]["planning_config"]["authority_deleted"] is True
    assert payload["upstream_artifacts"]["planning_config"]["status"] == "NON_CANONICAL_OBSERVABILITY"


def _environment_context(mode: str, tmp_path: Path) -> dict:
    if mode == "historical":
        return _historical_context(tmp_path)
    return {"broker_write": False}


def _safety_payload(mode: str, tmp_path: Path) -> dict:
    if mode == "historical":
        return _historical_safety_payload(tmp_path)
    return _demo_safety_payload()


def _cap_position_sizing_row(path: Path, *, symbol: str, amount: float) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for row in payload.get("positions") or []:
        if isinstance(row, dict) and str(row.get("security_code") or "") == symbol:
            row["target_notional"] = amount
            row["incremental_buy_notional"] = amount
            row["selected_position_amount"] = amount
            row["remaining_add_capacity"] = amount
    _write_json(path, payload)


def _write_strategy_dir_authority_fields(strategy_dir: Path) -> None:
    position_sizing_path = strategy_dir / "position_sizing.json"
    position_sizing = json.loads(position_sizing_path.read_text(encoding="utf-8"))
    position_sizing.update(
        {
            "dynamic_position_count": 1,
            "target_position_count": 1,
            "target_gross_exposure_ratio": 0.46,
            "dynamic_cash_exposure": 0.46,
            "aggregate_exposure_cap": 0.46,
            "residual_cash_ratio": 0.5,
            "portfolio_total_equity": 1_000_000.0,
        }
    )
    _write_json(position_sizing_path, position_sizing)
    _write_json(
        strategy_dir / "portfolio_policy.json",
        {
            "schema_version": "portfolio_policy.v1",
            "business_date": BUSINESS_DATE,
            "producer_result_status": "PASS",
            "cash_reserve_ratio": 0.5,
            "target_gross_exposure_ratio": 0.46,
            "target_position_count": 1,
            "maximum_gross_exposure_ratio": 0.88,
            "maximum_position_count": 10,
        },
    )
