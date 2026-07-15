from __future__ import annotations

from pathlib import Path

import pytest

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import _parse_args, _validate_rehearsal_args
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.historical_support.environment import (
    HistoricalExecutionSnapshotProvider,
    HistoricalSubmitAdapter,
)
from ai_fund_lab_v2.runtime_v2.storage.path_resolver import (
    MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN,
    is_mode_rooted_runtime_root,
)
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline


FORBIDDEN_MODES = ("demo", "production", "historical", "simulation", "backtest")


def test_phase17_j_path_guard_accepts_only_fixed_runtime_root(tmp_path: Path) -> None:
    assert is_mode_rooted_runtime_root(tmp_path / ".runtime") is False
    assert is_mode_rooted_runtime_root(tmp_path / "reports" / "historical_evidence") is False
    for mode in FORBIDDEN_MODES:
        assert is_mode_rooted_runtime_root(tmp_path / ".runtime" / mode) is True
        assert is_mode_rooted_runtime_root(tmp_path / "." / ".runtime" / mode / ".." / mode) is True


def test_phase17_j_submit_pipeline_halts_before_policy_pending_or_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_call(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("later submit stage should not be called")

    monkeypatch.setattr(
        "ai_fund_lab_v2.runtime_v2.submit.pipeline._resolve_capital_deployment_policy",
        forbidden_call,
    )
    result = run_submit_pipeline(
        runtime_root=tmp_path / ".runtime" / "historical",
        business_date="2026-07-06",
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=HistoricalSubmitAdapter(
            runtime_root=tmp_path / ".runtime" / "historical",
            business_date="2026-07-06",
            evaluation_time="2026-07-06T08:30:00+09:00",
        ),
    )

    assert result.status == "HALT"
    assert MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN in result.reason


@pytest.mark.parametrize("mode", FORBIDDEN_MODES)
def test_phase17_j_submit_pipeline_blocks_all_mode_rooted_runtime_roots(tmp_path: Path, mode: str) -> None:
    result = run_submit_pipeline(
        runtime_root=tmp_path / ".runtime" / mode,
        business_date="2026-07-06",
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=HistoricalSubmitAdapter(
            runtime_root=tmp_path / ".runtime" / mode,
            business_date="2026-07-06",
            evaluation_time="2026-07-06T08:30:00+09:00",
        ),
    )

    assert result.status == "HALT"
    assert MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN in result.reason


def test_phase17_j_submit_pipeline_normal_runtime_root_reaches_next_gate(tmp_path: Path) -> None:
    result = run_submit_pipeline(
        runtime_root=tmp_path / ".runtime",
        business_date="2026-07-06",
        mode="historical",
        submit_enabled=True,
        job="submit",
        adapter=HistoricalSubmitAdapter(
            runtime_root=tmp_path / ".runtime",
            business_date="2026-07-06",
            evaluation_time="2026-07-06T08:30:00+09:00",
        ),
    )

    assert result.status != "HALT"
    assert MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN not in result.reason


def test_phase17_j_execution_pipeline_uses_equivalent_mode_rooted_guard(tmp_path: Path) -> None:
    result = run_execution_readonly_pipeline(
        runtime_root=tmp_path / ".runtime" / "historical",
        business_date="2026-07-06",
        mode="historical",
        snapshot_provider=HistoricalExecutionSnapshotProvider(
            runtime_root=tmp_path / ".runtime" / "historical",
            business_date="2026-07-06",
        ),
    )

    assert result.status == "HALT"
    assert MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN in result.reason


def test_phase17_j_cli_rejects_mode_rooted_runtime_roots() -> None:
    historical_args = _parse_args(
        [
            "--mode",
            "historical",
            "--job",
            "market_refresh",
            "--business-date",
            "2026-07-06",
            "--evaluation-time",
            "2026-07-06T08:00:00+09:00",
            "--runtime-root",
            ".runtime/historical",
            "--notification-mode",
            "payload-only",
        ]
    )
    demo_args = _parse_args(["--mode", "demo", "--runtime-root", ".runtime/demo"])
    production_args = _parse_args(["--mode", "production", "--runtime-root", ".runtime/production"])

    for args in (historical_args, demo_args, production_args):
        with pytest.raises(ValueError, match=MODE_ROOTED_RUNTIME_ROOT_FORBIDDEN):
            _validate_rehearsal_args(args)


def test_phase17_j_cli_allows_historical_fixed_runtime_root() -> None:
    args = _parse_args(
        [
            "--mode",
            "historical",
            "--job",
            "market_refresh",
            "--business-date",
            "2026-07-06",
            "--evaluation-time",
            "2026-07-06T08:00:00+09:00",
            "--runtime-root",
            ".runtime",
            "--notification-mode",
            "payload-only",
        ]
    )

    _validate_rehearsal_args(args)
