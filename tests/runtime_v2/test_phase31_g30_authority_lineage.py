from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalExecutionSnapshotProvider
from ai_fund_lab_v2.runtime_v2.pending.reader import read_pending_order_plan_path
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import activate_strategy_planning_authority
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from ai_fund_lab_v2.strategy.runtime_planning import build_runtime_planning_payload
from tests.runtime_v2.test_phase17_g_historical_submit_guard_and_fill import (
    BUSINESS_DATE as SUBMIT_DATE,
    _historical_context,
    _pending,
    _runtime_fixture,
)
from tests.runtime_v2.test_phase23_i_strategy_planning_authority import (
    BUSINESS_DATE,
    _position_sizing_row,
    _write_position_sizing,
)
from tests.strategy.test_phase22_g_runtime_planning import (
    _produce as produce_runtime_planning_fixture,
    _runtime_owned_current_position_row,
    _summary,
    _write_portfolio_construction,
    _write_portfolio_policy,
    _write_position_management,
    _write_position_sizing_plan,
)


def test_phase31_g30_runtime_plan_carries_compact_strategy_authority_lineage(tmp_path: Path) -> None:
    result = produce_runtime_planning_fixture(
        tmp_path,
        pm_actions={"6758": "ADD", "7203": "EXIT"},
        pc_members={"31330": ("ADD_CANDIDATE", False), "6758": ("RETAIN", True), "7203": ("REMOVE_CANDIDATE", True)},
        current_codes=("6758", "7203"),
        current_position_rows=(
            {"security_code": "6758", "symbol": "6758", "quantity": 100},
            {"security_code": "7203", "symbol": "7203", "quantity": 100},
        ),
        position_sizing_positions={
            "31330": _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100),
            "6758": _position_sizing_row(target_notional=150_000.0, target_quantity=150, quantity_delta=50),
            "7203": _position_sizing_row(target_notional=0.0, target_quantity=0, quantity_delta=-100),
        },
    )
    payload = result.payload

    lineage = payload["strategy_authority_lineage"]
    assert lineage["schema_version"] == "runtime_authority_lineage.v1"
    assert lineage["field_classification"]["capital_competition"] == "AUTHORITATIVE_DECISION_RESULT"
    assert lineage["field_classification"]["canonical_sizing_evidence"] == "AUTHORITATIVE_DECISION_RESULT"
    assert lineage["downstream_strategy_redecision_allowed"] is False
    assert lineage["full_upstream_artifact_duplicated"] is False
    assert lineage["lineage_hash"].startswith("sha256:")
    assert {item["symbol"] for item in lineage["items"]} == {"31330", "6758", "7203"}
    assert all(plan["strategy_authority_lineage"]["lineage_hash"] == lineage["lineage_hash"] for plan in payload["plans"])


def test_phase31_g30_pending_reload_preserves_strategy_authority_lineage(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    strategy_dir = tmp_path / "strategy"
    strategy_dir.mkdir(parents=True)
    runtime_plan = produce_runtime_planning_fixture(
        tmp_path / "rp",
        pm_actions={},
        pc_members={"31330": ("ADD_CANDIDATE", False)},
        current_codes=(),
        position_sizing_positions={
            "31330": _position_sizing_row(target_notional=120_000.0, target_quantity=100, quantity_delta=100)
        },
    )
    Path(runtime_plan.artifact_path).replace(strategy_dir / "runtime_planning.json")
    _write_position_sizing(strategy_dir / "position_sizing.json", symbol="31330", target_notional=120_000.0)

    result = activate_strategy_planning_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="historical",
        strategy_dir=strategy_dir,
        environment_capability_context={"broker_write": False},
    )
    pending = read_pending_order_plan_path(
        path=runtime_root / "pending_order_plan" / "pending_order_plan.json",
        environment="historical",
    )

    assert result.status == "PASS"
    assert pending.plan is not None
    item = pending.plan.items[0]
    assert pending.plan.strategy_authority_lineage_hash == item.strategy_authority_lineage_hash
    assert item.strategy_authority_lineage is not None
    assert item.strategy_authority_lineage["field_classification"]["risk_pacing_intent"] == "AUTHORITATIVE_DECISION_RESULT"
    assert item.strategy_authority_lineage["item"]["symbol"] == "31330"


def test_phase31_g30_submit_and_execution_preserve_lineage_without_redecision(tmp_path: Path) -> None:
    runtime_root, policy_path, adapter = _runtime_fixture(tmp_path, side="BUY")
    lineage = _lineage("BUY_NEW")
    pending = _pending("historical", side="BUY", policy_path=policy_path)
    item = replace(
        pending.items[0],
        strategy_authority_lineage=lineage,
        strategy_authority_lineage_hash=lineage["lineage_hash"],
    )
    pending = replace(
        pending,
        items=(item,),
        strategy_authority_lineage=lineage,
        strategy_authority_lineage_hash=lineage["lineage_hash"],
    )
    write_pending_order_plan(runtime_root / "pending_order_plan" / "pending_order_plan.json", pending)

    submit = run_submit_pipeline(
        runtime_root=runtime_root,
        business_date=SUBMIT_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=adapter,
        capital_deployment_policy_path=policy_path,
        environment_context=_historical_context(),
    )
    execution = run_execution_readonly_pipeline(
        runtime_root=runtime_root,
        business_date=SUBMIT_DATE,
        mode="historical",
        snapshot_provider=HistoricalExecutionSnapshotProvider(runtime_root=runtime_root, business_date=SUBMIT_DATE),
    )
    order_records = [
        json.loads(line)
        for line in (runtime_root / "persistent_ledger" / "orders.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert submit.status == "PASS"
    assert submit.item_results[0].guard_evidence["guard_decision"] == "PASS"
    assert execution.status == "PASS"
    assert {record["strategy_authority_lineage_hash"] for record in order_records} == {lineage["lineage_hash"]}
    assert all(record["strategy_authority_lineage"]["downstream_strategy_redecision_allowed"] is False for record in order_records)


def test_phase31_g30_no_action_runtime_payload_preserves_authority_lineage(tmp_path: Path) -> None:
    position_sizing_plan_path = _write_position_sizing_plan(
        tmp_path,
        {"6758": {"source_pm_intent": "ADD", "current_quantity": 100, "target_quantity_candidate": 100, "quantity_delta_candidate": 0}},
    )
    payload, _ = build_runtime_planning_payload(
        business_date="2026-07-15",
        portfolio_construction_artifact_path=_write_portfolio_construction(tmp_path, {"6758": ("RETAIN", True)}),
        capital_deployment_artifact_path=None,
        portfolio_policy_artifact_path=_write_portfolio_policy(tmp_path),
        position_management_artifact_path=_write_position_management(tmp_path, {"6758": "ADD"}),
        current_portfolio_summary=_summary(tmp_path, "portfolio"),
        current_cash_summary=_summary(tmp_path, "cash"),
        current_position_summary=_summary(
            tmp_path,
            "position",
            rows=(_runtime_owned_current_position_row("6758", quantity=100, as_of="2026-07-15", source="runtime_owned_execution_ledger"),),
        ),
        pending_summary=_summary(tmp_path, "pending"),
        planning_config_summary=_summary(tmp_path, "planning_config"),
        position_sizing_plan_artifact_path=position_sizing_plan_path,
    )

    assert payload["plans"][0]["planning_intent"] == "NO_ACTION"
    assert payload["strategy_authority_lineage"]["lineage_hash"].startswith("sha256:")
    assert payload["strategy_authority_lineage"]["items"][0]["position_sizing_decision"]["quantity_delta_candidate"] == 0


def _lineage(intent: str) -> dict:
    return {
        "schema_version": "runtime_authority_lineage.item.v1",
        "lineage_hash": "sha256:g30-lineage-fixture",
        "lineage_ref": "runtime_planning.strategy_authority_lineage",
        "business_date": SUBMIT_DATE,
        "as_of": f"{SUBMIT_DATE}T00:00:00+00:00",
        "field_classification": {
            "capital_competition": "AUTHORITATIVE_DECISION_RESULT",
            "canonical_sizing_evidence": "AUTHORITATIVE_DECISION_RESULT",
        },
        "item": {
            "symbol": "7203",
            "planning_intent": intent,
            "order_side_intent": "BUY",
            "position_sizing_decision": {
                "quantity_delta_candidate": 100,
                "planned_quantity": 100,
                "quantity_status": "RESOLVED_EXECUTABLE",
            },
        },
        "downstream_strategy_redecision_allowed": False,
    }
