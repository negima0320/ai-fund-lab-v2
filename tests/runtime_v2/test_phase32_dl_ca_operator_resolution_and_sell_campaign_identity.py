from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.corporate_action_adjustment import (
    evaluate_corporate_action_adjustment_authority,
    materialize_corporate_action_adjustment_authority,
    resolve_corporate_action_adjustment_authority,
)
from ai_fund_lab_v2.runtime_v2.planning.strategy_authority import (
    _runtime_planning_position_campaign_id,
    _validate_sell_position_campaign_identity,
)


BUSINESS_DATE = "2023-10-11"
RUN_ID = "runtime-test-historical-extended-smoke-test"


def test_phase32_dl_operator_resolution_materializes_pass_authority_for_50280_shape(tmp_path: Path) -> None:
    runtime_root, source = _unresolved_authority(tmp_path, run_id=RUN_ID, symbol="50280")

    result = resolve_corporate_action_adjustment_authority(
        runtime_root=runtime_root,
        run_id=RUN_ID,
        business_date=BUSINESS_DATE,
        symbol="50280",
        event_type="OPERATOR_RESOLVED_QUANTITY_ADJUSTMENT",
        effective_date=BUSINESS_DATE,
        adjustment_factor=1.0 / 3.0,
        pre_adjustment_quantity=300,
        post_adjustment_quantity=100,
        current_quantity=100,
        broker_available_quantity=100,
        pending_quantity=100,
        submit_quantity=100,
        price_basis_reconciliation_status="PASS",
        already_applied_status="CONFIRMED",
        ledger_adjustment_status="PASS",
        current_adjustment_status="PASS",
        pending_adjustment_status="PASS",
        price_series_adjusted=True,
        quantity_adjusted=True,
        adjustment_already_applied=True,
        reviewer="operator@example.com",
        audit_id="phase32-dl-test-50280",
        resolution_reason="operator reviewed PIT CA evidence and runtime quantity lineage",
        evidence_sources=(str(source),),
        write=True,
    )

    assert result["status"] == "PASS"
    evaluated = evaluate_corporate_action_adjustment_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        symbol="50280",
        side="SELL",
        submit_quantity=100,
        pending_quantity=100,
        current_quantity=100,
        broker_available_quantity=100,
        event_evidence=_event(source, symbol="50280"),
    )
    assert evaluated["corporate_action_adjustment_authority_status"] == "PASS"
    assert evaluated["quantity_reconciliation_status"] == "PASS"
    assert evaluated["future_data_used"] is False


def test_phase32_dl_operator_resolution_does_not_infer_event_type_from_adjfactor(tmp_path: Path) -> None:
    runtime_root, _ = _unresolved_authority(tmp_path, run_id=RUN_ID, symbol="50280")

    result = _resolve(runtime_root, event_type="UNKNOWN_ADJFACTOR_IMPACT")

    assert result["status"] == "PRECONDITION_FAILURE"
    assert "corporate_action_type_unresolved" in result["reason_codes"]


def test_phase32_dl_operator_resolution_blocks_stale_cross_run_source(tmp_path: Path) -> None:
    runtime_root, _ = _unresolved_authority(tmp_path, run_id="runtime-test-old", symbol="50280")

    result = _resolve(runtime_root, event_type="OPERATOR_RESOLVED_QUANTITY_ADJUSTMENT")

    assert result["status"] == "PRECONDITION_FAILURE"
    assert "corporate_action_source_run_binding_mismatch" in result["reason_codes"]


def test_phase32_dl_operator_resolution_requires_regeneration_for_stale_pending_quantity(tmp_path: Path) -> None:
    runtime_root, _ = _unresolved_authority(tmp_path, run_id=RUN_ID, symbol="50280")

    result = _resolve(
        runtime_root,
        event_type="OPERATOR_RESOLVED_QUANTITY_ADJUSTMENT",
        pending_quantity=300,
        submit_quantity=300,
    )

    assert result["status"] == "PRECONDITION_FAILURE"
    assert "corporate_action_pending_quantity_requires_regeneration" in result["reason_codes"]
    assert "corporate_action_submit_quantity_exceeds_adjusted_quantity" in result["reason_codes"]


def test_phase32_dl_operator_resolution_missing_execution_lineage_fails_closed(tmp_path: Path) -> None:
    runtime_root, _ = _unresolved_authority(tmp_path, run_id=RUN_ID, symbol="50280")

    result = _resolve(
        runtime_root,
        event_type="OPERATOR_RESOLVED_QUANTITY_ADJUSTMENT",
        current_adjustment_status="UNKNOWN",
        adjustment_already_applied=False,
    )

    assert result["status"] == "PRECONDITION_FAILURE"
    assert "corporate_action_current_adjustment_missing" in result["reason_codes"]
    assert "corporate_action_already_applied_not_confirmed" in result["reason_codes"]


def test_phase32_dl_sell_campaign_id_inherits_run_scoped_open_campaign(tmp_path: Path) -> None:
    planning_path = _write_campaign_artifact(tmp_path, symbol="50280", campaign_id="pc-d468aca3b9d6da8f-50280-0001")

    campaign_id = _runtime_planning_position_campaign_id(
        plan={"planning_intent": "SELL_EXIT", "order_side_intent": "SELL"},
        symbol="50280",
        business_date=BUSINESS_DATE,
        source_decision_id="rp-2023-10-11-50280-sell_exit",
        runtime_planning_path=planning_path,
    )

    assert campaign_id == "pc-d468aca3b9d6da8f-50280-0001"


def test_phase32_dl_sell_campaign_mismatch_fails_closed(tmp_path: Path) -> None:
    planning_path = _write_campaign_artifact(tmp_path, symbol="50280", campaign_id="pc-actual-50280-0001")

    validation = _validate_sell_position_campaign_identity(
        plan={"position_campaign_id": "pc-other-50280-0001", "planning_intent": "SELL_EXIT"},
        symbol="50280",
        side="SELL",
        position_campaign_id="pc-other-50280-0001",
        runtime_planning_path=planning_path,
    )

    assert validation["status"] == "REVIEW_REQUIRED"
    assert validation["reason"] == "sell_position_campaign_identity_mismatch"


def _resolve(runtime_root: Path, **overrides: object) -> dict[str, object]:
    kwargs = {
        "runtime_root": runtime_root,
        "run_id": RUN_ID,
        "business_date": BUSINESS_DATE,
        "symbol": "50280",
        "event_type": "OPERATOR_RESOLVED_QUANTITY_ADJUSTMENT",
        "effective_date": BUSINESS_DATE,
        "adjustment_factor": 1.0 / 3.0,
        "pre_adjustment_quantity": 300,
        "post_adjustment_quantity": 100,
        "current_quantity": 100,
        "broker_available_quantity": 100,
        "pending_quantity": 100,
        "submit_quantity": 100,
        "price_basis_reconciliation_status": "PASS",
        "already_applied_status": "CONFIRMED",
        "ledger_adjustment_status": "PASS",
        "current_adjustment_status": "PASS",
        "pending_adjustment_status": "PASS",
        "price_series_adjusted": True,
        "quantity_adjusted": True,
        "adjustment_already_applied": True,
        "reviewer": "operator@example.com",
        "audit_id": "phase32-dl-test",
        "resolution_reason": "operator reviewed PIT CA evidence and runtime quantity lineage",
        "evidence_sources": (),
        "write": False,
    }
    kwargs.update(overrides)
    return resolve_corporate_action_adjustment_authority(**kwargs)


def _event(source: Path, *, symbol: str) -> dict[str, object]:
    return {
        "corporate_action_status": "IMPACT_DETECTED",
        "corporate_action_type": "UNKNOWN_ADJFACTOR_IMPACT",
        "corporate_action_type_authority": "not_available_from_adjfactor_only",
        "corporate_action_effective_date": BUSINESS_DATE,
        "corporate_action_adjustment_factor": 1.0 / 3.0,
        "corporate_action_artifact_path": str(source),
        "corporate_action_source": "jquants_raw_equities_bars_daily_adjfactor",
    }


def _unresolved_authority(tmp_path: Path, *, run_id: str, symbol: str) -> tuple[Path, Path]:
    runtime_root = tmp_path / ".runtime"
    source = tmp_path / "reports" / "runtime_tests" / "runs" / run_id / "daily" / BUSINESS_DATE / "market" / "raw.parquet"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("pit-adjfactor-evidence", encoding="utf-8")
    materialize_corporate_action_adjustment_authority(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        symbol=symbol,
        event_evidence=_event(source, symbol=symbol),
        current_quantity=100,
        broker_available_quantity=100,
        pending_quantity=100,
        submit_quantity=100,
    )
    return runtime_root, source


def _write_campaign_artifact(tmp_path: Path, *, symbol: str, campaign_id: str) -> Path:
    planning_path = tmp_path / "run" / "daily" / BUSINESS_DATE / "strategy" / "runtime_planning.json"
    campaign_path = planning_path.parent.parent / "positions" / "position_campaigns.json"
    campaign_path.parent.mkdir(parents=True, exist_ok=True)
    campaign_path.write_text(
        json.dumps(
            {
                "campaigns": [
                    {
                        "symbol": symbol,
                        "position_campaign_id": campaign_id,
                        "status": "OPEN",
                        "current_quantity": 100,
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    planning_path.parent.mkdir(parents=True, exist_ok=True)
    planning_path.write_text(json.dumps({"plans": []}, sort_keys=True), encoding="utf-8")
    return planning_path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
