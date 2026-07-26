from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _parse_args, _validate_rehearsal_args
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.historical_support.environment import (
    EnvironmentCompositionError,
    HistoricalExecutionSnapshotProvider,
    HistoricalSubmitAdapter,
    resolve_environment_composition,
)
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline


BUSINESS_DATE = "2026-07-08"
EVALUATION_TIME = "2026-07-08T15:00:00+09:00"


def test_historical_environment_composition_manifest_and_boundaries() -> None:
    composition = resolve_environment_composition(
        mode="historical",
        broker_environment="historical_simulated",
        external_delivery=False,
        broker_write=False,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
    )

    manifest = composition.manifest_fields(
        runtime_root=".runtime",
        environment_id="historical:historical_simulated",
        run_id="run-1",
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
    )

    assert manifest["run_type"] == "HISTORICAL"
    assert manifest["runtime_mode"] == "historical"
    assert manifest["broker_environment"] == "historical_simulated"
    assert manifest["simulation"] is True
    assert manifest["historical_replay"] is True
    assert manifest["broker_write"] is False
    assert manifest["production_equivalent"] is False
    assert manifest["acceptance_only"] is False
    assert manifest["external_delivery"] is False
    assert manifest["tachibana_readonly"] is False
    assert manifest["tachibana_demo_write"] is False
    assert manifest["tachibana_production_write"] is False
    assert isinstance(composition.submit_adapter, HistoricalSubmitAdapter)
    assert isinstance(composition.execution_snapshot_provider, HistoricalExecutionSnapshotProvider)


def test_historical_environment_composition_wires_logical_submit_authority_paths(tmp_path: Path) -> None:
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / "run-1"
    market_refresh_root = evidence_root / "daily" / BUSINESS_DATE / "market_refresh"
    input_root = market_refresh_root / "inputs" / "historical_asof" / BUSINESS_DATE
    manifest_path = input_root / "logical_input_manifest.json"
    normalized_path = input_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    raw_path = input_root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed_path = input_root / "raw" / "jquants" / "listed_issues" / "data.parquet"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_historical_logical_input_manifest_v1",
                "status": "PASS",
                "business_date": BUSINESS_DATE,
                "logical_paths": {
                    "normalized_ohlcv": str(normalized_path),
                    "raw_ohlcv": str(raw_path),
                    "listed_issues": str(listed_path),
                },
            }
        ),
        encoding="utf-8",
    )

    composition = resolve_environment_composition(
        mode="historical",
        broker_environment="historical_simulated",
        external_delivery=False,
        broker_write=False,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
        historical_asof_view_path=market_refresh_root / "historical_asof_view.json",
    )

    adapter = composition.submit_adapter
    assert isinstance(adapter, HistoricalSubmitAdapter)
    assert Path(adapter.ohlcv_path) == normalized_path
    assert Path(adapter.raw_ohlcv_path) == raw_path
    assert Path(adapter.listed_issues_path) == listed_path


def test_historical_environment_composition_does_not_fallback_when_logical_manifest_is_invalid(
    tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "reports" / "runtime_tests" / "runs" / "run-1"
    market_refresh_root = evidence_root / "daily" / BUSINESS_DATE / "market_refresh"
    input_root = market_refresh_root / "inputs" / "historical_asof" / BUSINESS_DATE
    manifest_path = input_root / "logical_input_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "runtime_historical_logical_input_manifest_v1",
                "status": "HALT",
                "business_date": BUSINESS_DATE,
                "logical_paths": {},
            }
        ),
        encoding="utf-8",
    )

    composition = resolve_environment_composition(
        mode="historical",
        broker_environment="historical_simulated",
        external_delivery=False,
        broker_write=False,
        business_date=BUSINESS_DATE,
        evaluation_time=EVALUATION_TIME,
        historical_asof_view_path=market_refresh_root / "historical_asof_view.json",
    )

    adapter = composition.submit_adapter
    assert isinstance(adapter, HistoricalSubmitAdapter)
    assert "__missing_historical_logical_authority__" in str(adapter.raw_ohlcv_path)
    assert "operations/jquants/raw" not in str(adapter.raw_ohlcv_path)


@pytest.mark.parametrize(
    "kwargs, message",
    (
        ({"business_date": None}, "explicit business_date"),
        ({"evaluation_time": None}, "explicit evaluation_time"),
        ({"broker_environment": "tachibana_demo"}, "historical_simulated"),
        ({"external_delivery": True}, "external_delivery=false"),
        ({"broker_write": True}, "broker_write=false"),
    ),
)
def test_historical_environment_composition_rejects_unsafe_identity(
    kwargs: dict[str, object],
    message: str,
) -> None:
    request = {
        "mode": "historical",
        "broker_environment": "historical_simulated",
        "external_delivery": False,
        "broker_write": False,
        "business_date": BUSINESS_DATE,
        "evaluation_time": EVALUATION_TIME,
    }
    request.update(kwargs)

    with pytest.raises(EnvironmentCompositionError, match=message):
        resolve_environment_composition(**request)  # type: ignore[arg-type]


def test_simulation_mode_is_not_a_formal_runtime_environment() -> None:
    with pytest.raises(EnvironmentCompositionError, match="use --mode historical"):
        resolve_environment_composition(mode="simulation")


def test_historical_submit_adapter_requires_explicit_identity() -> None:
    adapter = HistoricalSubmitAdapter()
    command = RuntimeV2SubmitCommand(
        command_id="cmd-1",
        environment="historical",
        pending_plan_id="pending-1",
        pending_item_id="item-1",
        approval_hash="sha256:approval",
        symbol="7203",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        price_type="MARKET",
        limit_price=0,
        estimated_amount=250000,
        target_session_date=BUSINESS_DATE,
        live_order_allowed=True,
    )

    preflight = adapter.preflight(command)
    submitted = adapter.submit(command)

    assert preflight.status == "HALT"
    assert preflight.broker_api_called is False
    assert submitted.status == "HALT"
    assert submitted.broker_api_called is False
    assert submitted.response_classification["broker_write"] is False


def test_submit_pipeline_requires_composed_historical_adapter(tmp_path: Path) -> None:
    result = run_submit_pipeline(
        runtime_root=tmp_path / ".runtime",
        business_date=BUSINESS_DATE,
        mode="historical",
        submit_enabled=True,
        job="submit",
    )

    assert result.status == "HALT"
    assert "HistoricalSubmitAdapter" in result.reason
    assert result.demo_submit_executed is False


def test_execution_pipeline_requires_composed_historical_snapshot_provider(tmp_path: Path) -> None:
    result = run_execution_readonly_pipeline(
        runtime_root=tmp_path / ".runtime",
        business_date=BUSINESS_DATE,
        mode="historical",
    )

    assert result.status == "HALT"
    assert "HistoricalExecutionSnapshotProvider" in result.reason


def test_historical_snapshot_provider_writes_non_external_snapshot(tmp_path: Path) -> None:
    provider = HistoricalExecutionSnapshotProvider()
    snapshot_path = tmp_path / "snapshot.json"
    report_path = tmp_path / "report.json"

    result = provider(mode="historical", snapshot_path=snapshot_path, report_path=report_path)

    assert result.status == "PASS"
    snapshot_text = snapshot_path.read_text(encoding="utf-8")
    assert '"broker_write": false' in snapshot_text
    assert '"external_delivery": false' in snapshot_text
    assert '"orders": []' in snapshot_text


def test_cli_historical_mode_requires_explicit_temporal_identity() -> None:
    args = _parse_args(["--mode", "historical", "--job", "runtime_state_refresh"])

    with pytest.raises(ValueError, match="--business-date"):
        _validate_rehearsal_args(args)


def test_cli_rejects_simulation_alias() -> None:
    args = _parse_args(["--mode", "simulation", "--job", "runtime_state_refresh"])

    with pytest.raises(ValueError, match="use --mode historical"):
        _validate_rehearsal_args(args)
