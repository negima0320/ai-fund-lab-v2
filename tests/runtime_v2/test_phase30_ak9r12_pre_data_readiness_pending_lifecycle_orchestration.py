from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main

from tests.runtime_v2.test_phase15ar_pending_lifecycle_stale_handling import (
    BUSINESS_DATE,
    TARGET_DATE,
    _latest_manifest,
    _load_json,
    _runtime_root,
    _write_broker_snapshot,
    _write_partial_submitted_buy_review_pending,
    _write_phase31_a2_mixed_buy_review_sell_continuation_pending,
    _write_phase31_a2_sell_continuation_execution_manifest,
    _write_phase31_a2_sell_continuation_submit_manifest,
)


def test_phase30_ak9r12_real_cli_data_readiness_expires_stale_residual_buy_review(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_partial_submitted_buy_review_pending(runtime_root, target_date=TARGET_DATE)
    _write_broker_snapshot(runtime_root)
    current_before = _load_json(runtime_root / "persistent_ledger" / "state.json")

    exit_code = main(_data_readiness_args(tmp_path, runtime_root))

    manifest = _latest_manifest(runtime_root, BUSINESS_DATE)
    pending = _load_json(pending_path)
    current_after = _load_json(runtime_root / "persistent_ledger" / "state.json")
    stage_names = [stage["name"] for stage in manifest["stages"]]

    assert exit_code == 0
    assert stage_names.index("pre_data_readiness_pending_lifecycle") < stage_names.index("runtime_data_readiness_gate")
    assert manifest["pre_data_readiness_pending_lifecycle_invoked"] is True
    assert manifest["pending_lifecycle_status"] == "EXPIRED"
    assert manifest["transition_reason"] == "STALE_NEXT_DAY_RESIDUAL_BUY_REVIEW_EXPIRED"
    assert manifest["data_readiness_status"] == "READY"
    assert pending["state"] == "EMPTY"
    assert pending["active_pending"] is False
    assert current_after == current_before


def test_phase30_ak9r12_real_cli_data_readiness_fails_closed_for_invalid_residual_review(
    tmp_path: Path,
) -> None:
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_partial_submitted_buy_review_pending(
        runtime_root,
        target_date=TARGET_DATE,
        include_review_sell=True,
    )
    _write_broker_snapshot(runtime_root)

    exit_code = main(_data_readiness_args(tmp_path, runtime_root))

    manifest = _latest_manifest(runtime_root, BUSINESS_DATE)
    pending = _load_json(pending_path)
    stage_names = [stage["name"] for stage in manifest["stages"]]

    assert exit_code == 20
    assert "pre_data_readiness_pending_lifecycle" in stage_names
    assert "runtime_data_readiness_gate" not in stage_names
    assert manifest["pre_data_readiness_pending_lifecycle_invoked"] is True
    assert manifest["pending_lifecycle_status"] == "REVIEW_REQUIRED"
    assert manifest["transition_reason"] == "stale_residual_buy_review_expiration_checks_failed"
    assert pending["state"] == "REVIEW_REQUIRED"
    assert pending["active_pending"] is True


def test_phase31_a2_real_cli_data_readiness_terminalizes_mixed_sell_continuation_before_gate(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path)
    pending_path = _write_phase31_a2_mixed_buy_review_sell_continuation_pending(
        runtime_root,
        target_date=TARGET_DATE,
    )
    _write_phase31_a2_sell_continuation_submit_manifest(runtime_root, business_date=TARGET_DATE)
    _write_phase31_a2_sell_continuation_execution_manifest(runtime_root, business_date=TARGET_DATE)
    _write_broker_snapshot(runtime_root)

    exit_code = main(_data_readiness_args(tmp_path, runtime_root))

    manifest = _latest_manifest(runtime_root, BUSINESS_DATE)
    pending = _load_json(pending_path)
    stage_names = [stage["name"] for stage in manifest["stages"]]

    assert exit_code == 0
    assert stage_names.index("pre_data_readiness_pending_lifecycle") < stage_names.index("runtime_data_readiness_gate")
    assert manifest["pre_data_readiness_pending_lifecycle_invoked"] is True
    assert manifest["pending_lifecycle_status"] == "EXPIRED"
    assert manifest["transition_reason"] == "MIXED_BUY_REVIEW_SELL_CONTINUATION_RESIDUAL_BUY_REVIEW_EXPIRED"
    assert manifest["data_readiness_status"] == "READY"
    assert pending["state"] == "EMPTY"
    assert pending["active_pending"] is False


def _data_readiness_args(tmp_path: Path, runtime_root: Path) -> list[str]:
    return [
        "--mode",
        "demo",
        "--job",
        "data_readiness",
        "--readiness-scope",
        "sell_planning",
        "--business-date",
        BUSINESS_DATE,
        "--evaluation-time",
        BUSINESS_DATE + "T09:00:00+09:00",
        "--runtime-root",
        str(runtime_root),
        "--reports-root",
        str(tmp_path / "reports" / "runtime_v2"),
        "--public-reports-root",
        str(tmp_path / "reports" / "public" / "runtime_v2"),
        "--manifest-root",
        str(runtime_root / "runtime_state" / "run_manifest"),
        "--log-root",
        str(runtime_root / "runtime_state" / "logs"),
    ]
