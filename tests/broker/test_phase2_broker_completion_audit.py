from pathlib import Path

from scripts.audit_phase2_broker_foundation import run_audit


def test_phase2_broker_completion_audit_passes_with_mock_sync(tmp_path: Path) -> None:
    result = run_audit(tmp_path / ".runtime")

    assert result["status"] == "complete"
    checks = result["checks"]
    assert checks["components_present"]
    assert checks["read_only_allowlist_exact"]
    assert checks["forbidden_clmids_exact"]
    assert checks["forbidden_clmids_rejected"]
    assert checks["cli_mock_only"]
    assert checks["broker_sync_success"]
    assert checks["snapshot_counts_present"]
    assert checks["runtime_broker_only"]
    assert checks["snapshot_schema_present"]
    assert checks["sync_result_schema_present"]
    assert checks["sanitizer_masks_canaries"]
    assert checks["saved_outputs_have_no_sensitive_canaries"]


def test_phase2_broker_completion_audit_outputs_portfolio_state_input_paths(tmp_path: Path) -> None:
    result = run_audit(tmp_path / ".runtime")
    sync_result = result["sync_result"]

    assert sync_result["source"] == "mock"
    assert sync_result["status"] == "success"
    assert len(sync_result["snapshot_paths"]) == 3
    assert len(sync_result["manifest_paths"]) == 3
    assert any("/balance/" in path for path in sync_result["snapshot_paths"])
    assert any("/positions/" in path for path in sync_result["snapshot_paths"])
    assert any("/orders/" in path for path in sync_result["snapshot_paths"])
