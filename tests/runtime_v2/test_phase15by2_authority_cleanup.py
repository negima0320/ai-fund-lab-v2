from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.broker_readonly.normalizer import normalize_broker_readonly_payload
from tests.runtime_v2.phase15by_buy_origin_e2e import run_phase15by_buy_origin_e2e
from tests.runtime_v2.phase15by2_authority_cleanup import run_phase15by2_authority_cleanup


def test_phase15by2_closes_buy_origin_authority_without_semantic_mutation(tmp_path):
    root = tmp_path / ".runtime_acceptance_phase15_buy_origin"
    run_phase15by_buy_origin_e2e(root=root, evidence_dir=tmp_path / "phase15_by", write_phase_report=False)

    result = run_phase15by2_authority_cleanup(root=root, evidence_dir=tmp_path / "phase15_by2", write_phase_report=False)
    after = result["after"]

    assert result["final_judgment"] == "BUY_ORIGIN_RUNTIME_AUTHORITY_CLOSED"
    assert result["classification"]["executions_production_equivalent"] == [False]
    assert result["classification"]["positions_production_equivalent"] == [False]
    assert result["classification"]["cash_production_equivalent"] == [False]
    assert result["classification"]["events_production_equivalent"] == [False]
    assert result["classification"]["current_production_equivalent"] is False
    assert result["classification"]["runtime_state_production_equivalent"] is False
    assert after["current_version_field"]
    assert after["current_hash_field"]
    assert after["runtime_state_version"]
    assert after["execution_reference"].startswith("execution-equivalent:")
    assert after["pending_state"] == "CONSUMED"
    assert after["pending_consumed"] is True
    assert after["pending_item_states"] == ["CONSUMED"]
    assert after["submitted_order_ids"]
    assert after["ledger_order_record_ids"]
    assert result["semantic_state_preserved"] == {
        "quantity_7203": True,
        "average_price": True,
        "current_price": True,
        "cash": True,
        "buying_power": True,
        "market_value": True,
        "total_equity": True,
        "sell_hold": True,
    }
    assert result["idempotency"]["second_run_noop"] is True
    assert result["idempotency"]["ledger_counts_unchanged"] is True
    assert result["existing_runtime_mutated"] is False


def test_phase15by2_normalizer_keeps_production_records_production_equivalent():
    production = normalize_broker_readonly_payload(
        environment="production",
        source="runtime_v2_execution_readonly",
        as_of="2026-07-14T09:00:00+09:00",
        orders=(),
        executions=(),
        positions=(),
        cash=None,
    )
    simulation = normalize_broker_readonly_payload(
        environment="demo",
        source="runtime_v2_execution_readonly_simulation",
        as_of="2026-07-14T09:00:00+09:00",
        orders=(),
        executions=(),
        positions=(),
        cash=None,
    )

    assert production.production_equivalent is True
    assert simulation.production_equivalent is False
