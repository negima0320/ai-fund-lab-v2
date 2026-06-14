from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def test_phase6_completion_audit_generates_completion_json(tmp_path: Path) -> None:
    audit = _run(tmp_path)

    assert audit["completion_status"] == "PHASE6_COMPLETE_WITH_DOCUMENTED_LIMITATIONS"
    assert audit["ready_for_phase7"] is True
    assert (tmp_path / "phase6_completion_audit.json").is_file()


def test_phase6_completion_audit_confirms_responsibility_boundary(tmp_path: Path) -> None:
    audit = _run(tmp_path)

    assert audit["responsibility_boundary_audit"]["status"] == "OK"
    executed_flags = audit["responsibility_boundary_audit"]["executed_flags"]
    assert executed_flags["training_executed"] is False
    assert executed_flags["backtest_executed"] is False
    assert executed_flags["broker_api_executed"] is False
    assert executed_flags["order_executed"] is False
    assert executed_flags["paper_trading_executed"] is False
    assert executed_flags["capital_allocation_executed"] is False


def test_phase6_completion_audit_confirms_output_schema(tmp_path: Path) -> None:
    audit = _run(tmp_path)

    assert audit["output_schema_audit"]["status"] == "OK"
    assert audit["output_schema_audit"]["missing_required_columns"] == []
    assert "risk_guard_status" in audit["output_schema_audit"]["calibrated_output_columns"]
    assert "feature_version" in audit["output_schema_audit"]["calibrated_output_columns"]


def test_phase6_completion_audit_confirms_feature_and_label_safety(tmp_path: Path) -> None:
    audit = _run(tmp_path)

    assert audit["feature_safety_audit"]["status"] == "OK"
    assert audit["feature_safety_audit"]["forbidden_feature_column_count"] == 0
    assert audit["label_separation_audit"]["status"] == "OK"
    assert audit["label_separation_audit"]["future_feature_column_count"] == 0
    assert audit["label_separation_audit"]["unprefixed_label_column_count"] == 0


def test_phase6_completion_audit_confirms_add_and_hold_exit_safety(tmp_path: Path) -> None:
    audit = _run(tmp_path)

    assert audit["add_safety_audit"]["status"] == "OK"
    assert audit["add_safety_audit"]["add_loss_position_count_total"] == 0
    assert audit["add_safety_audit"]["add_exit_label_overlap_count_total"] == 0
    assert audit["hold_exit_safety_audit"]["status"] == "OK"
    assert audit["hold_exit_safety_audit"]["continue_winner_exit_count_total"] == 0
    assert audit["hold_exit_safety_audit"]["continue_winner_reduce_count_total"] == 0


def test_phase6_completion_audit_documents_phase6f_limitations(tmp_path: Path) -> None:
    audit = _run(tmp_path)

    limitations = audit["phase6f_limitations"]
    assert limitations["phase5_formal_opportunity_output_used"] is False
    assert limitations["opportunity_signal_source"] == "proxy_from_normalized_quotes"
    assert limitations["row_count"] == 36
    assert limitations["code_count"] == 12
    assert limitations["target_date_count"] == 3
    assert limitations["all_hold"] is True
    assert limitations["all_continue_winner"] is True
    assert limitations["action_diversity_evaluation_sufficient"] is False


def test_phase6_completion_audit_phase7_handoff_is_explicit(tmp_path: Path) -> None:
    audit = _run(tmp_path)

    handoff = audit["phase7_handoff"]
    assert "買い増し候補シグナル" in handoff["ADD"]
    assert "Capital Allocation Engine" in handoff["ADD"]
    assert "hold_score" in handoff["scores_for_phase7"]
    assert "exit_score" in handoff["scores_for_phase7"]
    assert "add_score" in handoff["scores_for_phase7"]
    assert "reduce_score" in handoff["scores_for_phase7"]


def _run(tmp_path: Path) -> dict:
    module = _load_audit_script()
    output_path = tmp_path / "phase6_completion_audit.json"
    audit = module.run_phase6_completion_audit(
        output_path=output_path,
        created_at="2026-06-14T00:00:00+00:00",
    )
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted["completion_status"] == audit["completion_status"]
    return audit


def _load_audit_script():
    path = Path("scripts/audit_phase6_position_management_completion.py")
    spec = importlib.util.spec_from_file_location("phase6_completion_audit_script", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
