from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from ai_fund_lab_v2.paper_trading.feature_refresh import run_feature_refresh
from ai_fund_lab_v2.operations.market_refresh import run_operations_market_refresh
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    CANDIDATE_REQUIRED_COLUMNS,
    OPPORTUNITY_REQUIRED_COLUMNS,
    validate_feature_consumer_readiness,
)


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"


def test_phase17_ad_position_feature_uses_asset_sot_and_carries_day1_positions(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    codes = ("81050", "67400", "66590", "36670", "45640")
    _write_quotes(operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet", codes=codes)
    _write_listed(operations_root / "jquants" / "listed_issues" / "data.parquet", codes=codes)
    _write_current(
        runtime_root,
        business_date="2026-07-06",
        position_state_as_of="2026-07-06",
        positions=[{"symbol": code, "quantity": 100 + i, "average_price": 10 + i, "unrealized_pnl": 9999} for i, code in enumerate(codes)],
    )
    _write_runtime_state(runtime_root, business_date="2026-07-07")

    result = run_feature_refresh(
        target_data_until="2026-07-07",
        dry_run=False,
        execute=True,
        daily_quotes_path=operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet",
        listed_info_path=operations_root / "jquants" / "listed_issues" / "data.parquet",
        feature_output_root=operations_root / "feature_artifacts",
        manifest_root=operations_root / "feature_refresh_detail",
        markdown_report_path=operations_root / "feature_refresh" / "2026-07-07" / "feature_refresh.md",
        json_report_path=operations_root / "feature_refresh" / "2026-07-07" / "feature_refresh.json",
        runtime_root=runtime_root,
        created_at="2026-07-07T08:00:00+09:00",
    )
    readiness = validate_feature_consumer_readiness(operations_root=operations_root, feature_date="2026-07-07")
    pm = pd.read_parquet(operations_root / "feature_artifacts" / "2026-07-07" / "position_feature_input.parquet")
    position_status = next(item for item in result.to_dict()["artifacts"] if item["ai_name"] == "position")

    assert result.status == "FEATURES_READY"
    assert readiness.consumer_ready is True
    assert readiness.pm_schema_status == "READY"
    assert len(pm) == 5
    assert set(pm["code"].astype(str)) == set(codes)
    assert pm["target_date"].unique().tolist() == ["2026-07-07"]
    assert pm["position_state_as_of"].unique().tolist() == ["2026-07-06"]
    assert position_status["source_data_refs"]["current_authority_path"].endswith(".runtime/persistent_ledger/state.json")
    assert position_status["source_data_refs"]["current_position_count"] == "5"
    assert position_status["source_data_refs"]["no_fill_carry_used"] == "True"
    assert position_status["reason"] == "position_feature_ready"
    forbidden = {
        "cash",
        "buying_power",
        "total_equity",
        "realized_pnl",
        "unrealized_pnl",
        "runtime_test_status",
        "backtest_result",
        "safety_decision",
    }
    assert forbidden.isdisjoint(set(pm.columns))


def test_phase17_ad_market_refresh_generates_features_when_api_fetch_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    codes = ("81050", "67400", "66590", "36670", "45640")
    _write_quotes(operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet", codes=codes)
    _write_listed(operations_root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet", codes=codes)
    _write_current(
        runtime_root,
        business_date="2026-07-06",
        position_state_as_of="2026-07-06",
        positions=[{"symbol": code, "quantity": 100, "average_price": 10} for code in codes],
    )
    _write_runtime_state(runtime_root, business_date="2026-07-07")

    class FakeMarketRefresh:
        status = "DRY_RUN"
        blocked_reasons: tuple[str, ...] = ()
        jquants_api_fetch_executed = False
        latest_normalized_daily_quotes_date = "2026-07-07"

        def to_dict(self) -> dict[str, Any]:
            return {
                "status": self.status,
                "blocked_reasons": [],
                "latest_normalized_daily_quotes_date": "2026-07-07",
                "jquants_api_fetch_executed": False,
                "endpoints": [],
            }

    monkeypatch.setattr("ai_fund_lab_v2.operations.market_refresh.run_market_data_refresh", lambda **kwargs: FakeMarketRefresh())

    result = run_operations_market_refresh(
        trade_date="2026-07-07",
        root=operations_root,
        allow_api_fetch=False,
    )
    pm = pd.read_parquet(operations_root / "feature_artifacts" / "2026-07-07" / "position_feature_input.parquet")

    assert result["feature_refresh_executed"] is True
    assert result["feature_refresh_status"] == "FEATURES_READY"
    assert len(pm) == 5


def test_phase17_ad_confirmed_empty_current_is_ready_zero_rows(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    quotes_path = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed_path = operations_root / "jquants" / "listed_issues" / "data.parquet"
    _write_quotes(quotes_path, codes=("81050",))
    _write_listed(listed_path, codes=("81050",), target_date="2026-07-01")
    _write_current(runtime_root, business_date="2026-07-06", position_state_as_of="2026-07-06", positions=[], confirmed_empty=True)
    _write_runtime_state(runtime_root, business_date="2026-07-07")

    result = run_feature_refresh(
        target_data_until="2026-07-07",
        dry_run=False,
        execute=True,
        daily_quotes_path=quotes_path,
        listed_info_path=listed_path,
        feature_output_root=operations_root / "feature_artifacts",
        manifest_root=operations_root / "feature_refresh_detail",
        markdown_report_path=operations_root / "feature_refresh.md",
        json_report_path=operations_root / "feature_refresh.json",
        runtime_root=runtime_root,
        created_at="2026-07-07T08:00:00+09:00",
    )
    pm_status = next(item for item in result.to_dict()["artifacts"] if item["ai_name"] == "position")

    assert result.status == "FEATURES_READY"
    assert pm_status["row_count"] == 0
    assert pm_status["reason"] == "position_feature_ready_confirmed_empty_current"
    assert pm_status["source_data_refs"]["current_position_count"] == "0"


def test_phase20_n_ledger_confirmed_empty_without_legacy_confirmed_empty_is_ready_empty(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    quotes_path = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed_path = operations_root / "jquants" / "listed_issues" / "data.parquet"
    _write_quotes(quotes_path, codes=("81050",))
    _write_listed(listed_path, codes=("81050",), target_date="2026-07-01")
    _write_current(
        runtime_root,
        business_date="2026-06-30",
        position_state_as_of="2026-06-30",
        positions=[],
        confirmed_empty=False,
        current_position_status="READY",
        current_positions_unknown=False,
        no_position=True,
        no_position_reason="current_has_no_runtime_owned_positions",
        position_state_source="runtime_owned_execution_ledger",
        temporal_status="READY",
        review_required=False,
    )
    _write_runtime_state(runtime_root, business_date="2026-07-01")

    result = run_feature_refresh(
        target_data_until="2026-07-01",
        dry_run=False,
        execute=True,
        daily_quotes_path=quotes_path,
        listed_info_path=listed_path,
        feature_output_root=operations_root / "feature_artifacts",
        manifest_root=operations_root / "feature_refresh_detail",
        markdown_report_path=operations_root / "feature_refresh.md",
        json_report_path=operations_root / "feature_refresh.json",
        runtime_root=runtime_root,
        created_at="2026-07-01T08:00:00+09:00",
    )
    readiness = validate_feature_consumer_readiness(operations_root=operations_root, feature_date="2026-07-01")
    pm_status = next(item for item in result.to_dict()["artifacts"] if item["ai_name"] == "position")
    pm = pd.read_parquet(operations_root / "feature_artifacts" / "2026-07-01" / "position_feature_input.parquet")

    assert result.status == "FEATURES_READY"
    assert len(pm) == 0
    assert pm_status["status"] == "FEATURES_READY"
    assert pm_status["reason"] == "position_feature_ready_confirmed_empty_current"
    assert pm_status["source_data_refs"]["current_authority_status"] == "READY_EMPTY"
    assert pm_status["source_data_refs"]["current_position_count"] == "0"
    assert pm_status["source_data_refs"]["no_fill_carry_used"] == "True"
    assert readiness.status == "READY"
    assert readiness.consumer_ready is True
    assert readiness.pm_schema_status == "READY"
    assert readiness.pm.evidence["current_authority_status"] == "READY_EMPTY"
    assert readiness.pm.evidence["current_position_status"] == "READY"
    assert readiness.pm.evidence["current_positions_unknown"] is False
    assert readiness.pm.evidence["current_state_confirmed_empty"] is False
    assert readiness.pm.evidence["no_position"] is True
    assert readiness.pm.evidence["no_position_reason"] == "current_has_no_runtime_owned_positions"
    assert readiness.pm.evidence["position_state_source"] == "runtime_owned_execution_ledger"
    assert readiness.pm.evidence["temporal_status"] == "READY"
    assert readiness.pm.evidence["review_required"] is False
    assert readiness.pm.evidence["position_feature_status"] == "READY_EMPTY"
    assert readiness.pm.evidence["position_feature_reason"] == "current_positions_confirmed_empty"
    assert readiness.pm.evidence["pm_consumer_status"] == "NOT_REQUIRED"
    assert readiness.pm.evidence["pm_inference_required"] is False
    assert readiness.pm.evidence["runtime_continuation_status"] == "PASS"


def test_phase20_n_empty_position_conflicting_metadata_fails_closed(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    feature_dir = operations_root / "feature_artifacts" / "2026-07-01"
    _write_consumer_feature_artifacts(feature_dir, feature_date="2026-07-01", position_rows=[])
    _write_current(
        runtime_root,
        business_date="2026-06-30",
        position_state_as_of="2026-06-30",
        positions=[],
        confirmed_empty=False,
        current_position_status="READY",
        current_positions_unknown=False,
        no_position=False,
        temporal_status="READY",
        review_required=False,
    )
    _write_runtime_state(runtime_root, business_date="2026-07-01")

    readiness = validate_feature_consumer_readiness(operations_root=operations_root, feature_date="2026-07-01")

    assert readiness.status == "REVIEW_REQUIRED"
    assert readiness.consumer_ready is False
    assert readiness.pm_schema_status == "REVIEW_REQUIRED"
    assert readiness.pm.reason == "current_position_metadata_conflict_empty_not_marked_no_position"


def test_phase17_ad_unknown_and_missing_current_fail_closed(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    feature_dir = operations_root / "feature_artifacts" / "2026-07-07"
    _write_consumer_feature_artifacts(feature_dir, feature_date="2026-07-07", position_rows=[])
    _write_current(runtime_root, business_date="2026-07-06", position_state_as_of="2026-07-06", positions=[], confirmed_empty=False)
    _write_runtime_state(runtime_root, business_date="2026-07-07")

    readiness = validate_feature_consumer_readiness(operations_root=operations_root, feature_date="2026-07-07")
    assert readiness.pm_schema_status == "REVIEW_REQUIRED"
    assert readiness.pm.reason == "current_positions_unknown"

    (runtime_root / "persistent_ledger" / "state.json").unlink()
    missing = validate_feature_consumer_readiness(operations_root=operations_root, feature_date="2026-07-07")
    assert missing.pm_schema_status == "REVIEW_REQUIRED"
    assert missing.pm.reason == "current_authority_missing_asset_sot"


def test_phase17_ad_current_output_mismatch_is_review_required(tmp_path: Path) -> None:
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    feature_dir = operations_root / "feature_artifacts" / "2026-07-07"
    _write_consumer_feature_artifacts(feature_dir, feature_date="2026-07-07", position_rows=[])
    _write_current(
        runtime_root,
        business_date="2026-07-06",
        position_state_as_of="2026-07-06",
        positions=[{"symbol": f"1000{i}", "quantity": 100, "average_price": 10} for i in range(5)],
    )
    _write_runtime_state(runtime_root, business_date="2026-07-07")

    readiness = validate_feature_consumer_readiness(operations_root=operations_root, feature_date="2026-07-07")

    assert readiness.consumer_ready is False
    assert readiness.pm_schema_status == "REVIEW_REQUIRED"
    assert readiness.pm.reason == "position_feature_current_output_mismatch"
    assert readiness.pm.evidence["current_position_count"] == 5
    assert readiness.pm.evidence["output_row_count"] == 0


def test_phase17_ad_runner_requires_exact_existing_plan_run_id(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = _load_runner()
    runtime_root = _make_runtime_root(tmp_path)
    evidence_root = tmp_path / "reports"
    planned_run_id = "runtime-test-historical-smoke-20260715T015929082437Z"
    plan = runner.build_plan(
        profile=runner.load_profile("historical-smoke"),
        runtime_root=runtime_root,
        evidence_root=evidence_root,
        business_days=1,
        start_date="2026-07-06",
        date_from=None,
        date_to=None,
        run_id=planned_run_id,
    )
    runner.write_json_atomic(evidence_root / "runs" / planned_run_id / "plan.json", plan)

    accepted = _call_main(
        runner,
        ["run", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root), "--run-id", planned_run_id, "--dry-run"],
        capsys,
    )
    missing_z = _call_main(
        runner,
        ["run", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root), "--run-id", planned_run_id.rstrip("Z"), "--dry-run"],
        capsys,
    )
    unknown = _call_main(
        runner,
        ["run", "--runtime-root", str(runtime_root), "--evidence-root", str(evidence_root), "--run-id", "runtime-test-unknown", "--dry-run"],
        capsys,
    )

    assert accepted["status"] == "DRY_RUN"
    assert accepted["run_id"] == planned_run_id
    assert missing_z["status"] == "PRECONDITION_FAILURE"
    assert planned_run_id in missing_z["error"]
    assert unknown["status"] == "PRECONDITION_FAILURE"


def _write_quotes(path: Path, *, codes: tuple[str, ...]) -> None:
    rows: list[dict[str, Any]] = []
    current = date(2026, 4, 1)
    while len({row["target_date"] for row in rows if row["code"] == codes[0]}) < 70:
        if current.weekday() < 5:
            day_index = len({row["target_date"] for row in rows if row["code"] == codes[0]})
            target_date = current.isoformat()
            for offset, code in enumerate(codes):
                rows.append(
                    {
                        "target_date": target_date,
                        "Date": target_date,
                        "code": code,
                        "Code": code,
                        "Close": float(100 + day_index + offset),
                        "Volume": float(10_000 + day_index + offset),
                    }
                )
        current += timedelta(days=1)
    for row in rows:
        if row["target_date"] == rows[-1]["target_date"]:
            row["target_date"] = "2026-07-07"
            row["Date"] = "2026-07-07"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path, *, codes: tuple[str, ...], target_date: str = "2026-07-07") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"target_date": target_date, "Date": target_date, "Code": code, "CoName": f"Name {code}", "ProdCat": "011", "MktNm": "プライム"}
            for code in codes
        ]
    ).to_parquet(path, index=False)


def _write_current(
    runtime_root: Path,
    *,
    business_date: str,
    position_state_as_of: str,
    positions: list[dict[str, Any]],
    confirmed_empty: bool = False,
    current_position_status: str | None = None,
    current_positions_unknown: bool | None = None,
    no_position: bool | None = None,
    no_position_reason: str = "",
    position_state_source: str = "",
    temporal_status: str = "",
    review_required: bool = False,
) -> None:
    path = runtime_root / "persistent_ledger" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_current_temporal_v1",
                "business_date": business_date,
                "position_state_as_of": position_state_as_of,
                "positions": positions,
                "current_state_confirmed_empty": confirmed_empty,
                "current_positions_unknown": False if current_positions_unknown is None else current_positions_unknown,
                "review_required": review_required,
                "cash": 999999,
                "total_equity": 999999,
                "unrealized_pnl": 12345,
                "realized_pnl": 0,
            }
        ),
        encoding="utf-8",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if current_position_status is not None:
        payload["current_position_status"] = current_position_status
    if no_position is not None:
        payload["no_position"] = no_position
    if no_position_reason:
        payload["no_position_reason"] = no_position_reason
    if position_state_source:
        payload["position_state_source"] = position_state_source
    if temporal_status:
        payload["temporal_status"] = temporal_status
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_runtime_state(runtime_root: Path, *, business_date: str) -> None:
    path = runtime_root / "runtime_state" / "current_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_v2_operation_state_v1",
                "business_date": business_date,
                "asset_state_is_authoritative_here": False,
                "asset_state_source": "persistent_ledger/state.json",
            }
        ),
        encoding="utf-8",
    )


def _write_consumer_feature_artifacts(feature_dir: Path, *, feature_date: str, position_rows: list[dict[str, Any]]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{column: _value_for_column(column, feature_date) for column in CANDIDATE_REQUIRED_COLUMNS}]).to_parquet(
        feature_dir / "candidate_features.parquet",
        index=False,
    )
    pd.DataFrame([{column: _value_for_column(column, feature_date) for column in OPPORTUNITY_REQUIRED_COLUMNS}]).to_parquet(
        feature_dir / "opportunity_feature_input.parquet",
        index=False,
    )
    columns = [
        "target_date",
        "position_state_as_of",
        "entry_date",
        "code",
        "broker_issue_code",
        "holding_days",
        "average_price",
        "current_price",
        "unrealized_return",
        "quantity",
        "feature_version",
        "data_until",
        "created_at",
        "no_position_reason",
    ]
    pd.DataFrame(position_rows, columns=columns).to_parquet(feature_dir / "position_feature_input.parquet", index=False)


def _value_for_column(column: str, feature_date: str) -> Any:
    if column == "target_date":
        return feature_date
    if column == "code":
        return "81050"
    if column.startswith("missing_flags_"):
        return False
    return 1.0


def _load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_ad", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _call_main(module, args: list[str], capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    exit_code = module.main(args + ["--json"])
    payload = json.loads(capsys.readouterr().out)
    payload["_exit_code"] = exit_code
    return payload


def _make_runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    _write_current(root, business_date="2026-07-06", position_state_as_of="2026-07-06", positions=[], confirmed_empty=True)
    _write_runtime_state(root, business_date="2026-07-06")
    (root / "pending_order_plan").mkdir(parents=True)
    (root / "pending_order_plan" / "pending_order_plan.json").write_text(
        json.dumps({"schema_version": "runtime_v2_pending_slot_v1", "status": "EMPTY", "state": "EMPTY", "active_pending": False}),
        encoding="utf-8",
    )
    (root / "operations" / "feature_date_contract").mkdir(parents=True, exist_ok=True)
    (root / "operations" / "feature_date_contract" / "2026-07-06.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "requested_feature_date": "2026-07-06",
                "selected_feature_date": "2026-07-06",
                "latest_available_market_date": "2026-07-06",
                "generated_feature_artifacts": {},
            }
        ),
        encoding="utf-8",
    )
    return root
