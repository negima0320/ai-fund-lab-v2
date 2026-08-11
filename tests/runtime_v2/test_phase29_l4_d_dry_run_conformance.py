from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_l4d", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    (root / "persistent_ledger").mkdir(parents=True)
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "runtime_state").mkdir(parents=True)
    (root / "artifact_registry" / "checkpoints").mkdir(parents=True)
    (root / "artifact_registry" / "index").mkdir(parents=True)
    (root / "persistent_ledger" / "state.json").write_text(
        json.dumps({"schema_version": "runtime_v2_current_temporal_v1", "environment": "historical", "cash": 12, "buying_power": 12, "positions": []}),
        encoding="utf-8",
    )
    (root / "pending_order_plan" / "pending_order_plan.json").write_text(
        json.dumps({"schema_version": "runtime_v2_pending_slot_v1", "status": "EMPTY", "state": "EMPTY", "active_pending": False}),
        encoding="utf-8",
    )
    (root / "runtime_state" / "current_state.json").write_text(
        json.dumps({"schema_version": "runtime_v2_operation_state_v1", "runtime_mode": "historical", "environment": "historical", "state": "READY"}),
        encoding="utf-8",
    )
    (root / "artifact_registry" / "checkpoints" / "latest.json").write_text(json.dumps({"checkpoint_hash": "checkpoint"}), encoding="utf-8")
    return root


def call_main(module, args: list[str], capsys: pytest.CaptureFixture[str]) -> dict:
    exit_code = module.main(args + ["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    payload["_exit_code"] = exit_code
    return payload


def write_calendar(root: Path, rows: list[dict[str, str]]) -> None:
    target = root / "operations" / "jquants" / "historical_snapshots" / "trading_calendar"
    target.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(target / "data.parquet", index=False)


def write_overlay(root: Path, run_id: str, rows: list[dict[str, str]]) -> None:
    run_root = root / "market_data_acquisition" / "runs" / run_id
    calendar = run_root / "raw" / "jquants" / "trading_calendar"
    calendar.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(calendar / "data.parquet", index=False)
    final_validation = {
        "status": "PASS",
        "future_date_count": 0,
        "normalized_inventory": {"duplicate_key_count": 0},
        "schema_comparison": {"status": "PASS", "runtime_merge_compatible": True},
        "jquants_lineage": {"status": "PASS"},
    }
    (run_root / "state.json").write_text(json.dumps({"status": "PASS", "acquisition_run_id": run_id, "final_validation": final_validation}), encoding="utf-8")
    (run_root / "plan.json").write_text(json.dumps({"status": "PASS", "acquisition_run_id": run_id}), encoding="utf-8")


def test_l4d_dry_run_sunday_end_date_conforms_to_canonical_trading_window(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    write_calendar(root, [{"Date": day, "HolDiv": "1"} for day in ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10"]])

    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--date-from", "2026-07-06", "--date-to", "2026-07-12", "--dry-run"],
        capsys,
    )

    assert payload["status"] == "DRY_RUN"
    assert payload["resolved_date_to"] == "2026-07-10"
    assert payload["request_conformance_status"] == "PASS"
    assert payload["independent_acceptance"]["requested_window_conformance_judgment"] == "PASS"


def test_l4d_dry_run_holiday_end_date_conforms_to_previous_trading_day(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    write_calendar(
        root,
        [
            {"Date": "2026-07-06", "HolDiv": "1"},
            {"Date": "2026-07-07", "HolDiv": "1"},
            {"Date": "2026-07-08", "HolDiv": "3"},
            {"Date": "2026-07-09", "HolDiv": "1"},
            {"Date": "2026-07-10", "HolDiv": "3"},
        ],
    )

    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--date-from", "2026-07-06", "--date-to", "2026-07-10", "--dry-run"],
        capsys,
    )

    assert payload["resolved_business_day_count"] == 3
    assert payload["resolved_date_to"] == "2026-07-09"
    assert payload["request_conformance_status"] == "PASS"


def test_l4d_non_trading_start_date_resolves_to_first_trading_day(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    write_calendar(root, [{"Date": "2026-07-06", "HolDiv": "3"}, {"Date": "2026-07-07", "HolDiv": "1"}, {"Date": "2026-07-08", "HolDiv": "1"}])

    payload = call_main(
        runner,
        ["fresh-run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--date-from", "2026-07-06", "--date-to", "2026-07-08", "--dry-run"],
        capsys,
    )

    assert payload["resolved_date_from"] == "2026-07-07"
    assert payload["request_conformance_status"] == "PASS"


def test_l4d_missing_requested_trading_day_remains_not_pass() -> None:
    runner = load_runner()
    status = runner._fresh_run_request_conformance_status(
        plan_payload={
            "requested_business_days": 3,
            "resolved_business_day_count": 2,
            "window_resolution_status": "REVIEW_REQUIRED",
            "request_conformance_status": "NOT_PASS",
        },
        completed_business_day_count=0,
        dry_run=True,
    )

    assert status == "NOT_PASS"


def test_l4d_calendar_ambiguity_remains_review_required(tmp_path: Path) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    write_calendar(root, [{"Date": "2026-07-06", "HolDiv": "1"}])
    write_overlay(root, "jquants-acquisition-open", [{"Date": "2026-07-07", "HolDiv": "1"}])
    write_overlay(root, "jquants-acquisition-closed", [{"Date": "2026-07-07", "HolDiv": "3"}])

    window = runner.resolve_business_window(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=root,
        business_days=None,
        start_date=None,
        date_from="2026-07-06",
        date_to="2026-07-07",
    )

    assert window["calendar_authority"]["status"] == "REVIEW_REQUIRED"
    assert window["window_resolution_status"] == "REVIEW_REQUIRED"


def test_l4d_actual_run_conformance_still_requires_completed_days() -> None:
    runner = load_runner()
    status = runner._fresh_run_request_conformance_status(
        plan_payload={
            "requested_business_days": 3,
            "resolved_business_day_count": 3,
            "window_resolution_status": "PASS",
            "request_conformance_status": "PASS",
        },
        completed_business_day_count=2,
        dry_run=False,
    )

    assert status == "NOT_PASS"
