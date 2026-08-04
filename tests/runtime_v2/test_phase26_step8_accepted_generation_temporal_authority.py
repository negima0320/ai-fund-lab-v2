from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import resolve_accepted_generation
from ai_fund_lab_v2.runtime_v2.approval.linkage import link_approval_to_pending
from ai_fund_lab_v2.runtime_v2.pending.writer import write_pending_order_plan
from ai_fund_lab_v2.runtime_v2.planning_submit_feasibility import load_runtime_current_exposure
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline
from ai_fund_lab_v2.runtime_v2.temporal.resolver import resolve_temporal_context

from tests.runtime_v2.test_phase14e17_submit_pipeline_connection import _demo_settings
from tests.runtime_v2.test_phase19_ad_u1_a_accepted_generation_resolver import (
    _accepted_manifest_with_scalers,
    _append_history,
    _install_generation,
    _read_json,
    _runtime_root as _generation_runtime_root,
    _write_json,
)
from tests.runtime_v2.test_phase24_ht_planning_submit_feasibility import (
    _approval,
    _item,
    _pending,
    _position,
    _runtime_root,
    _write_current,
    _write_policy,
)


BUSINESS_DATE = "2026-07-09"


def test_phase26_step8_matching_business_date_generation_materializes_binding(tmp_path: Path) -> None:
    runtime_root = _generation_runtime_root(tmp_path)
    manifest = _accepted_manifest_with_scalers(
        runtime_root.parent,
        generation_id="step8-accepted",
        accepted_at="2026-07-01T00:00:00+00:00",
        effective_from="2026-07-01",
    )
    _install_generation(runtime_root, manifest)
    _append_history(runtime_root, manifest)

    resolution = resolve_accepted_generation(runtime_root, business_date=BUSINESS_DATE)
    binding = resolution.binding_evidence(runtime_mode="demo", business_date=BUSINESS_DATE, consumer="test")

    assert resolution.resolution_status == "RESOLVED_COMMITTED"
    assert binding["generation_binding_status"] == "PASS"
    assert binding["requested_business_date"] == BUSINESS_DATE
    assert binding["selected_business_date"] == BUSINESS_DATE
    assert binding["latest_fallback_used"] is False


def test_phase26_step8_missing_business_date_and_missing_generation_fail_closed(tmp_path: Path) -> None:
    runtime_root = _generation_runtime_root(tmp_path)

    no_date = resolve_accepted_generation(runtime_root)
    missing = resolve_accepted_generation(runtime_root, business_date=BUSINESS_DATE)

    assert no_date.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_business_date_required" in no_date.reason_codes
    assert missing.resolution_status == "NO_ACCEPTED_GENERATION"
    assert "NO_ACCEPTED_GENERATION_BOOTSTRAP" in missing.reason_codes


def test_phase26_step8_future_generation_and_multiple_accepted_are_review_required(tmp_path: Path) -> None:
    runtime_root = _generation_runtime_root(tmp_path)
    future = _accepted_manifest_with_scalers(
        tmp_path,
        generation_id="future-generation",
        accepted_at="2026-07-20T00:00:00+00:00",
        effective_from="2026-07-20",
    )
    _install_generation(runtime_root, future)
    _append_history(runtime_root, future)

    future_resolution = resolve_accepted_generation(runtime_root, business_date=BUSINESS_DATE)

    assert future_resolution.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_accepted_at_after_business_date" in future_resolution.reason_codes

    old_a = _accepted_manifest_with_scalers(tmp_path, generation_id="old-a", accepted_at="2026-07-01T00:00:00+00:00", effective_from="2026-07-01")
    old_b = _accepted_manifest_with_scalers(tmp_path, generation_id="old-b", accepted_at="2026-07-02T00:00:00+00:00", effective_from="2026-07-02")
    _install_generation(runtime_root, old_a)
    _install_generation(runtime_root, old_b)
    _append_history(runtime_root, old_a)
    _append_history(runtime_root, old_b)

    conflict = resolve_accepted_generation(runtime_root, business_date=BUSINESS_DATE)

    assert conflict.resolution_status == "REVIEW_REQUIRED"
    assert "accepted_generation_conflict_multiple_eligible" in conflict.reason_codes
    assert conflict.source_evidence["generation_conflict"] is True


def test_phase26_pf3g_historical_fixed_authority_separates_market_asof_from_evaluation_time(tmp_path: Path) -> None:
    runtime_root = _generation_runtime_root(tmp_path)
    manifest = _accepted_manifest_with_scalers(
        tmp_path,
        generation_id="future-fixed",
        accepted_at="2026-07-20T00:00:00+00:00",
        effective_from="2026-07-20",
    )
    payload = _read_json(manifest)
    authority_path = tmp_path / "historical_authority.json"
    _write_json(
        authority_path,
        {
            "generation_id": payload["generation_id"],
            "bundle_manifest_path": str(manifest),
            "aggregate_hash": payload["aggregate_hash"],
            "evaluation_authority_time": "2026-08-03T00:00:00Z",
            "historical_business_date_acceptance_comparison": "NOT_APPLIED_TO_ACCEPTED_GENERATION",
            "latest_fallback_used": False,
        },
    )

    resolution = resolve_accepted_generation(
        runtime_root,
        business_date=BUSINESS_DATE,
        fixed_authority_path=authority_path,
    )

    assert resolution.resolution_status == "RESOLVED_COMMITTED"
    assert resolution.source_evidence["market_as_of_business_date"] == BUSINESS_DATE
    assert resolution.source_evidence["selected_business_date"] == "2026-08-03"
    assert resolution.source_evidence["business_date_temporal_comparison_applied"] is False


def test_phase26_step8_temporal_invalid_and_future_business_date_fail_closed() -> None:
    invalid = resolve_temporal_context(runtime_business_date="not-a-date")
    future = resolve_temporal_context(
        runtime_business_date="2026-08-04",
        now=datetime(2026, 8, 3, 9, tzinfo=ZoneInfo("Asia/Tokyo")),
    )

    assert invalid.temporal_authority_status == "REVIEW_REQUIRED"
    assert invalid.temporal_authority_reason == "runtime_business_date_invalid"
    assert future.temporal_authority_status == "REVIEW_REQUIRED"
    assert future.temporal_authority_reason == "runtime_business_date_future"
    assert future.temporal_fallback_used is False


def test_phase26_step8_submit_blocks_buy_generation_mismatch_but_allows_sell(tmp_path: Path) -> None:
    root = _runtime_root(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")
    policy = load_capital_deployment_policy(policy_path)
    _write_current(root, cash=500_000, positions=[_position("1111", 100, 1000)])
    buy = _item("buy-1", amount=100_000, symbol="7203")
    sell = replace(
        _item("sell-1", amount=50_000, symbol="1111"),
        side="SELL",
        quantity=50,
        estimated_price=1000,
        estimated_amount=50_000,
    )
    binding = _binding("gen-a")
    buy = replace(
        buy,
        accepted_generation_id="gen-b",
        accepted_generation_business_date=BUSINESS_DATE,
        accepted_generation_binding_status="PASS",
        accepted_generation_binding=_binding("gen-b"),
    )
    sell = replace(sell, accepted_generation_binding_status="NOT_REQUIRED")
    pending = _pending((buy, sell), policy=policy)
    pending = replace(
        pending,
        accepted_generation_id="gen-a",
        accepted_generation_business_date=BUSINESS_DATE,
        accepted_generation_binding_status="PASS",
        accepted_generation_binding=binding,
    )
    pending = link_approval_to_pending(
        pending_plan=pending,
        approval_artifact=_approval(pending),
        planning_submit_feasibility_current=load_runtime_current_exposure(root / "persistent_ledger" / "state.json"),
        planning_submit_feasibility_policy=policy,
    )
    pending = replace(
        pending,
        approval=replace(
            pending.approval,
            accepted_generation_id="gen-a",
            accepted_generation_business_date=BUSINESS_DATE,
            accepted_generation_binding_status="PASS",
            accepted_generation_binding=binding,
        ),
    )
    write_pending_order_plan(root / "pending_order_plan" / "pending_order_plan.json", pending)
    _write_broker_snapshot(root)

    result = run_submit_pipeline(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_demo_settings(),
        capital_deployment_policy_path=policy_path,
    )

    by_id = {item["pending_item_id"]: item for item in result.submit_guard_item_evidence}
    assert result.status == "REVIEW_REQUIRED"
    assert by_id["buy-1"]["submit_generation_binding_status"] == "BLOCKED"
    assert "accepted_generation_id_mismatch" in by_id["buy-1"]["submit_generation_binding_reason"]
    assert by_id["sell-1"]["submit_generation_binding_status"] == "PASS"
    assert by_id["sell-1"]["submit_generation_binding_reason"] == "SELL_NOT_REQUIRED"


def _binding(generation_id: str) -> dict:
    return {
        "schema_version": "phase26_step8_accepted_generation_binding.v1",
        "consumer": "test",
        "mode": "demo",
        "requested_business_date": BUSINESS_DATE,
        "selected_business_date": BUSINESS_DATE,
        "accepted_generation_id": generation_id,
        "accepted_generation_business_date": BUSINESS_DATE,
        "generation_binding_status": "PASS",
        "temporal_binding_status": "PASS",
        "latest_fallback_used": False,
        "shared_state_fallback_used": False,
        "default_generation_used": False,
        "legacy_component_fallback_used": False,
        "promotion_candidate_fallback_used": False,
        "manual_model_path_used": False,
    }


def _write_broker_snapshot(root: Path) -> None:
    path = root / "broker" / "snapshots" / "positions" / "positions_20260709.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "source": "broker_readonly",
                "as_of": "2026-07-09T08:50:00+09:00",
                "production_equivalent": True,
                "records": [
                    {
                        "issue_code": "1111",
                        "quantity": 100,
                        "available_quantity": 100,
                        "account_type": "specific",
                        "production_equivalent": True,
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
