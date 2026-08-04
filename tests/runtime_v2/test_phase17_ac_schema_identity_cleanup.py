from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.current_state.temporal import CURRENT_TEMPORAL_SCHEMA_VERSION
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh
from ai_fund_lab_v2.runtime_v2.historical_support.asof import (
    ASOF_SCHEMA_VERSION,
    HistoricalAsOfAuthority,
    HistoricalAsOfResolution,
    write_historical_asof_evidence,
)
from tests.runtime_v2.test_phase17_k_runtime_test_runner import (
    CONFIRM_FLAG,
    call_main,
    load_runner,
    make_runtime_root,
)


BUSINESS_DATE = "2026-07-06"


def test_phase17ac_runner_response_and_plan_writer_use_runtime_schema(tmp_path, capsys):
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"

    payload = call_main(
        runner,
        [
            "plan",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--date-from",
            BUSINESS_DATE,
            "--date-to",
            BUSINESS_DATE,
            "--write-evidence",
        ],
        capsys,
    )

    plan_path = Path(payload["expected_evidence_paths"]["plan"])
    plan = _read_json(plan_path)
    assert payload["schema_version"] == "runtime_test_runner_v1"
    assert payload["runtime_test_plan_schema_version"] == "runtime_test_plan_v1"
    assert plan["schema_version"] == "runtime_test_plan_v1"
    assert "phase17" not in payload["schema_version"]
    assert "phase17" not in plan["schema_version"]


def test_phase17ac_runner_run_state_writer_uses_runtime_schema(tmp_path, monkeypatch, capsys):
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)

    def fake_run(command: list[str], *, cwd: Path):
        return subprocess.CompletedProcess(command, 30, "", "halt")

    monkeypatch.setattr(runner, "run_runtime_cli", fake_run)
    payload = call_main(
        runner,
        [
            "run",
            "--runtime-root",
            str(root),
            "--evidence-root",
            str(evidence),
            "--business-days",
            "1",
            "--start-date",
            BUSINESS_DATE,
            "--confirm",
            CONFIRM_FLAG,
        ],
        capsys,
    )

    run_states = sorted((evidence / "runs").glob("*/run_state.json"))
    assert run_states
    run_state = _read_json(run_states[-1])
    assert payload["schema_version"] == "runtime_test_runner_v1"
    assert payload["status"] == "HALT"
    assert payload["_exit_code"] == runner.EXIT_HALT
    assert run_state["schema_version"] == "runtime_test_run_state_v1"


def test_phase17ac_runner_legacy_run_state_read_only_compatible(tmp_path, capsys):
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    run_id = "legacy-run-state"
    run_dir = evidence / "runs" / run_id
    run_dir.mkdir(parents=True)
    before = {
        "schema_version": "phase17_k_run_state_v1",
        "run_id": run_id,
        "status": "HALT",
        "source_baseline": runner.source_baseline(root),
    }
    (run_dir / "run_state.json").write_text(json.dumps(before, sort_keys=True), encoding="utf-8")

    payload = call_main(runner, ["validate", "--runtime-root", str(root), "--evidence-root", str(evidence), "--run-id", run_id], capsys)
    after = _read_json(run_dir / "run_state.json")
    assert payload["status"] == "VALIDATION_FAILURE"
    assert payload["checks"]["historical_evaluation_authority_gate"] is False
    assert after == before


def test_phase17ac_unknown_run_state_schema_fails_closed(tmp_path):
    runner = load_runner()
    evidence = tmp_path / "reports"
    run_id = "unknown-schema"
    run_dir = evidence / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run_state.json").write_text(json.dumps({"schema_version": "runtime_test_run_state_v999"}), encoding="utf-8")

    with pytest.raises(runner.RuntimeTestError) as exc:
        runner.load_run_state(evidence, run_id)
    assert exc.value.status == "TEST_INVALID"
    assert exc.value.exit_code == runner.EXIT_TEST_INVALID


def test_phase17ac_backup_manifest_writer_and_legacy_reader(tmp_path, capsys):
    runner = load_runner()
    root = make_runtime_root(tmp_path)
    evidence = tmp_path / "reports"
    payload = call_main(runner, ["backup", "--runtime-root", str(root), "--evidence-root", str(evidence), "--confirm", CONFIRM_FLAG], capsys)
    manifest_path = evidence / "backups" / payload["backup_id"] / "backup_manifest.json"
    manifest = _read_json(manifest_path)
    assert payload["schema_version"] == "runtime_test_runner_v1"
    assert manifest["schema_version"] == "runtime_test_backup_manifest_v1"

    manifest["schema_version"] = "phase17_k_backup_manifest_v1"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    loaded = runner.load_backup_manifest(evidence, payload["backup_id"])
    assert loaded["schema_version"] == "phase17_k_backup_manifest_v1"


def test_phase17ac_historical_asof_writer_uses_runtime_schema(tmp_path):
    resolution = HistoricalAsOfResolution(
        status="PASS",
        reason="historical_asof_view_ready",
        business_date=BUSINESS_DATE,
        logical_identity=f"historical-asof:{BUSINESS_DATE}",
        authorities=(
            HistoricalAsOfAuthority(
                authority="normalized_ohlcv",
                status="PASS",
                reason="ready",
                business_date=BUSINESS_DATE,
                physical_source_path=str(tmp_path / "ohlcv.parquet"),
                physical_source_hash="hash",
                physical_row_count=1,
                physical_max_date=BUSINESS_DATE,
                logical_cutoff=BUSINESS_DATE,
                logical_row_count=1,
                logical_max_date=BUSINESS_DATE,
                future_rows_excluded_count=0,
            ),
        ),
    )

    path = write_historical_asof_evidence(evidence_root=tmp_path, business_date=BUSINESS_DATE, resolution=resolution)
    payload = _read_json(path)
    assert payload["schema_version"] == ASOF_SCHEMA_VERSION
    assert payload["schema_version"] == "runtime_historical_asof_view_v1"


def test_phase17ac_legacy_historical_asof_reader_compatible_and_unknown_fails_closed(tmp_path):
    pd = pytest.importorskip("pandas")
    root = tmp_path / ".runtime"
    root.mkdir()
    _write_current(root)
    parquet = tmp_path / "ohlcv.parquet"
    pd.DataFrame([{"Date": BUSINESS_DATE, "Code": "7203", "Close": 1100.0}]).to_parquet(parquet)
    legacy = _write_asof_view(tmp_path / "legacy" / "historical_asof_view.json", "phase17_l_historical_asof_view_v1", parquet)

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        market_evidence_path=legacy,
        now=None,
    )

    unknown = _write_asof_view(tmp_path / "unknown" / "historical_asof_view.json", "runtime_historical_asof_view_v999", parquet)
    rejected = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        market_evidence_path=unknown,
        now=None,
    )
    assert result.status == "READY"
    assert rejected.status == "HALT"
    assert "unsupported historical_asof_view schema_version" in rejected.reason
    assert _read_json(legacy)["schema_version"] == "phase17_l_historical_asof_view_v1"


def _write_current(root: Path) -> None:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "temporal_schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "position_state_as_of": BUSINESS_DATE,
            "valuation_as_of": BUSINESS_DATE,
            "source_market_date": BUSINESS_DATE,
            "last_execution_date": BUSINESS_DATE,
            "last_reconciled_at": BUSINESS_DATE + "T00:00:00+00:00",
            "positions": [
                {
                    "symbol": "7203",
                    "quantity": 100,
                    "average_price": 900,
                    "current_price": 1000,
                    "market_value": 100000,
                    "unrealized_pnl": 10000,
                    "ownership": "runtime_owned",
                }
            ],
            "cash": 900000,
            "buying_power": 900000,
            "market_value": 100000,
            "total_equity": 1000000,
        },
    )


def _write_asof_view(path: Path, schema_version: str, parquet: Path) -> Path:
    _write_json(
        path,
        {
            "schema_version": schema_version,
            "status": "PASS",
            "reason": "historical_asof_view_ready",
            "business_date": BUSINESS_DATE,
            "latest_available_market_date": BUSINESS_DATE,
            "authorities": [
                {
                    "authority": "normalized_ohlcv",
                    "status": "PASS",
                    "business_date": BUSINESS_DATE,
                    "physical_source_path": str(parquet),
                }
            ],
        },
    )
    return path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
