from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.market_data_bootstrap import (
    build_market_data_bootstrap_plan,
    build_market_data_warmup_sufficiency,
    execute_market_data_bootstrap,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts/runtime_test.py"


def _quotes(days: list[str], codes: tuple[str, ...] = ("13010",)) -> pd.DataFrame:
    rows = []
    for day in days:
        for code in codes:
            rows.append(
                {
                    "Date": day,
                    "Code": code,
                    "Open": 100.0,
                    "High": 101.0,
                    "Low": 99.0,
                    "Close": 100.0,
                    "Volume": 1000.0,
                    "PriceSource": "adjusted",
                    "SchemaVersion": 2,
                    "source_endpoint": "/v2/equities/bars/daily",
                    "target_date": day,
                    "code": code,
                    "business_key": code,
                    "endpoint": "daily_quotes_normalized",
                    "source": "jquants",
                }
            )
    return pd.DataFrame(rows)


def test_phase20_bb_warmup_guard_blocks_short_runtime_source(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    path = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    path.parent.mkdir(parents=True)
    days = pd.bdate_range("2026-02-16", "2026-03-24").strftime("%Y-%m-%d").tolist()
    _quotes(days).to_parquet(path, index=False)

    guard = build_market_data_warmup_sufficiency(
        runtime_root=root,
        target_start_date="2026-03-24",
        target_end_date="2026-03-24",
    )

    assert guard["warmup_sufficiency_judgment"] == "BLOCK"
    assert guard["reason"] == "HISTORICAL_SOURCE_WARMUP_INSUFFICIENT"
    assert guard["missing_warmup_business_days"] > 0


def test_phase23_ac_warmup_guard_distinguishes_target_date_missing(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    path = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    path.parent.mkdir(parents=True)
    days = pd.bdate_range("2026-04-21", "2026-07-14").strftime("%Y-%m-%d").tolist()
    assert len(days) == 61
    _quotes(days).to_parquet(path, index=False)

    guard = build_market_data_warmup_sufficiency(
        runtime_root=root,
        target_start_date="2026-07-15",
        target_end_date="2026-07-15",
    )

    assert guard["warmup_sufficiency_judgment"] == "BLOCK"
    assert guard["reason"] == "QUOTE_TARGET_DATE_MISSING"
    assert guard["missing_warmup_business_days"] == 0
    assert guard["target_date_available"] is False


def test_phase23_ac_warmup_guard_distinguishes_empty_source(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    path = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    path.parent.mkdir(parents=True)
    _quotes([]).to_parquet(path, index=False)

    guard = build_market_data_warmup_sufficiency(
        runtime_root=root,
        target_start_date="2026-07-15",
        target_end_date="2026-07-15",
    )

    assert guard["warmup_sufficiency_judgment"] == "BLOCK"
    assert guard["reason"] == "SOURCE_ROWS_EMPTY"
    assert guard["target_date_available"] is False


def test_phase20_bb_bootstrap_plan_rejects_non_five_year_source(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    target = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    source = tmp_path / "source.parquet"
    target.parent.mkdir(parents=True)
    days = pd.bdate_range("2026-02-16", "2026-07-14").strftime("%Y-%m-%d").tolist()
    _quotes(days).to_parquet(target, index=False)
    _quotes(pd.bdate_range("2026-06-01", "2026-06-26").strftime("%Y-%m-%d").tolist()).to_parquet(source, index=False)

    plan = build_market_data_bootstrap_plan(
        runtime_root=root,
        source_path=source,
        evidence_root=tmp_path / "evidence",
        target_start_date="2021-07-14",
        target_end_date="2026-07-14",
    )

    assert plan["status"] == "BLOCK"
    assert plan["source_reuse_status"] == "COVERAGE_INSUFFICIENT"
    assert "source_not_five_year_scale" in plan["blocked_reasons"]


def test_phase20_bb_bootstrap_run_requires_explicit_market_data_confirmation(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    target = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    source = tmp_path / "source.parquet"
    target.parent.mkdir(parents=True)
    days = pd.bdate_range("2026-01-01", "2026-07-14").strftime("%Y-%m-%d").tolist()
    _quotes(days[-5:]).to_parquet(target, index=False)
    _quotes(days).to_parquet(source, index=False)

    result = execute_market_data_bootstrap(
        runtime_root=root,
        source_path=source,
        evidence_root=tmp_path / "evidence",
        target_start_date="2026-04-01",
        target_end_date="2026-07-14",
        confirm=True,
        explicit_mutation_confirm=False,
    )

    assert result["status"] == "BLOCK"
    assert result["runtime_market_data_mutated"] is False
    assert len(pd.read_parquet(target)) == 5


def test_phase20_bb_system_status_data_scope_reports_warmup_guard() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:."
    result = subprocess.run(
        [
            sys.executable,
            str(RUNTIME_TEST),
            "system-status",
            "--scope",
            "data",
            "--target-start-date",
            "2026-03-24",
            "--target-end-date",
            "2026-03-24",
            "--json",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(result.stdout)
    guard = payload["sections"]["data"]["runtime_market_data_warmup_sufficiency"]
    assert guard["warmup_sufficiency_judgment"] == "BLOCK"
    assert guard["reason"] == "HISTORICAL_SOURCE_WARMUP_INSUFFICIENT"
