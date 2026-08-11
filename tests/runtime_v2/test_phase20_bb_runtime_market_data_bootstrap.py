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
import ai_fund_lab_v2.runtime_v2.market_data_bootstrap as market_data_bootstrap


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


def test_phase29_l4a_bootstrap_post_commit_warmup_becomes_final_authority(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    target = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    source = tmp_path / "source.parquet"
    target.parent.mkdir(parents=True)
    old_days = pd.bdate_range("2026-02-16", "2026-07-14").strftime("%Y-%m-%d").tolist()
    source_days = pd.bdate_range("2022-05-17", "2026-08-07").strftime("%Y-%m-%d").tolist()
    _quotes(old_days).to_parquet(target, index=False)
    _quotes(source_days).to_parquet(source, index=False)

    result = execute_market_data_bootstrap(
        runtime_root=root,
        source_path=source,
        evidence_root=tmp_path / "evidence",
        target_start_date="2022-08-10",
        target_end_date="2026-08-07",
        confirm=True,
        explicit_mutation_confirm=True,
        write_evidence=True,
    )

    assert result["status"] == "PASS"
    assert result["blocked_reasons"] == []
    assert result["commit_status"] == "PASS"
    assert result["bootstrap_readiness"]["status"] == "PASS"
    assert result["pre_commit_warmup_authority"] == "DIAGNOSTIC_ONLY"
    assert result["pre_commit_warmup_sufficiency"]["warmup_sufficiency_judgment"] == "BLOCK"
    assert result["post_commit_warmup_sufficiency"]["warmup_sufficiency_judgment"] == "PASS"
    assert result["warmup_sufficiency"] == result["post_commit_warmup_sufficiency"]
    assert result["warmup_sufficiency"]["actual_source_earliest_date"] == "2022-05-17"
    assert result["warmup_sufficiency"]["actual_source_latest_date"] == "2026-08-07"
    assert result["post_commit_verification"]["status"] == "PASS"
    assert (tmp_path / "evidence" / "pre_commit_warmup_sufficiency.json").is_file()
    assert (tmp_path / "evidence" / "post_commit_warmup_sufficiency.json").is_file()
    assert json.loads((tmp_path / "evidence" / "warmup_requirement_inventory.json").read_text())["warmup_sufficiency_judgment"] == "PASS"


def test_phase29_l4a_bootstrap_blocks_when_post_commit_warmup_is_short(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    target = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    source = tmp_path / "source.parquet"
    target.parent.mkdir(parents=True)
    source_days = pd.bdate_range("2022-08-10", periods=61).strftime("%Y-%m-%d").tolist()
    _quotes([]).to_parquet(target, index=False)
    _quotes(source_days).to_parquet(source, index=False)

    result = execute_market_data_bootstrap(
        runtime_root=root,
        source_path=source,
        evidence_root=tmp_path / "evidence",
        target_start_date="2022-08-10",
        target_end_date=source_days[-1],
        confirm=True,
        explicit_mutation_confirm=True,
    )

    assert result["commit_status"] == "PASS"
    assert result["status"] == "BLOCK"
    assert result["final_judgment"] == "BOOTSTRAP_POST_COMMIT_READINESS_BLOCKED"
    assert result["post_commit_warmup_sufficiency"]["warmup_sufficiency_judgment"] == "BLOCK"
    assert "post_commit_warmup_not_pass" in result["bootstrap_readiness"]["blocked_reasons"]


def test_phase29_l4a_bootstrap_commit_failure_is_fail_closed(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / ".runtime"
    target = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    source = tmp_path / "source.parquet"
    target.parent.mkdir(parents=True)
    days = pd.bdate_range("2022-05-17", "2022-08-12").strftime("%Y-%m-%d").tolist()
    _quotes([]).to_parquet(target, index=False)
    _quotes(days).to_parquet(source, index=False)

    def fail_replace(src: Path, dst: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(market_data_bootstrap.os, "replace", fail_replace)

    result = execute_market_data_bootstrap(
        runtime_root=root,
        source_path=source,
        evidence_root=tmp_path / "evidence",
        target_start_date="2022-08-10",
        target_end_date="2022-08-12",
        confirm=True,
        explicit_mutation_confirm=True,
    )

    assert result["status"] == "BLOCK"
    assert result["final_judgment"] == "BOOTSTRAP_COMMIT_FAILED"
    assert result["runtime_market_data_mutated"] is False
    assert result["bootstrap_readiness"]["status"] == "BLOCK"
    assert "commit_not_pass" in result["bootstrap_readiness"]["blocked_reasons"]


def test_phase29_l4a_bootstrap_target_missing_after_commit_blocks(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / ".runtime"
    target = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    source = tmp_path / "source.parquet"
    target.parent.mkdir(parents=True)
    days = pd.bdate_range("2022-05-17", "2022-08-12").strftime("%Y-%m-%d").tolist()
    _quotes([]).to_parquet(target, index=False)
    _quotes(days).to_parquet(source, index=False)

    def remove_target(src: Path, dst: Path) -> None:
        Path(src).unlink(missing_ok=True)
        Path(dst).unlink(missing_ok=True)

    monkeypatch.setattr(market_data_bootstrap.os, "replace", remove_target)

    result = execute_market_data_bootstrap(
        runtime_root=root,
        source_path=source,
        evidence_root=tmp_path / "evidence",
        target_start_date="2022-08-10",
        target_end_date="2022-08-12",
        confirm=True,
        explicit_mutation_confirm=True,
    )

    assert result["commit_status"] == "PASS"
    assert result["status"] == "BLOCK"
    assert result["post_commit_verification"]["status"] == "BLOCK"
    assert "post_commit_target_missing" in result["post_commit_verification"]["blocked_reasons"]


def test_phase29_l4a_bootstrap_target_content_mismatch_blocks(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / ".runtime"
    target = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    source = tmp_path / "source.parquet"
    target.parent.mkdir(parents=True)
    days = pd.bdate_range("2022-05-17", "2022-08-12").strftime("%Y-%m-%d").tolist()
    _quotes([]).to_parquet(target, index=False)
    _quotes(days).to_parquet(source, index=False)

    def corrupt_replace(src: Path, dst: Path) -> None:
        frame = pd.read_parquet(src).head(1)
        frame.to_parquet(dst, index=False)
        Path(src).unlink(missing_ok=True)

    monkeypatch.setattr(market_data_bootstrap.os, "replace", corrupt_replace)

    result = execute_market_data_bootstrap(
        runtime_root=root,
        source_path=source,
        evidence_root=tmp_path / "evidence",
        target_start_date="2022-08-10",
        target_end_date="2022-08-12",
        confirm=True,
        explicit_mutation_confirm=True,
    )

    assert result["status"] == "BLOCK"
    assert result["post_commit_verification"]["status"] == "BLOCK"
    assert "post_commit_content_hash_mismatch" in result["post_commit_verification"]["blocked_reasons"]
    assert "post_commit_row_count_mismatch" in result["post_commit_verification"]["blocked_reasons"]


def test_phase29_l4a_warmup_exactly_61bd_passes_and_60bd_blocks(tmp_path: Path) -> None:
    root = tmp_path / ".runtime"
    target = root / "operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
    target.parent.mkdir(parents=True)
    exactly_61 = pd.bdate_range(end="2022-08-10", periods=61).strftime("%Y-%m-%d").tolist()
    _quotes(exactly_61).to_parquet(target, index=False)

    pass_guard = build_market_data_warmup_sufficiency(
        runtime_root=root,
        target_start_date="2022-08-10",
        target_end_date="2022-08-10",
    )
    assert pass_guard["warmup_sufficiency_judgment"] == "PASS"
    assert pass_guard["available_business_dates_count"] == 61

    only_60 = exactly_61[1:]
    _quotes(only_60).to_parquet(target, index=False)
    block_guard = build_market_data_warmup_sufficiency(
        runtime_root=root,
        target_start_date="2022-08-10",
        target_end_date="2022-08-10",
    )
    assert block_guard["warmup_sufficiency_judgment"] == "BLOCK"
    assert block_guard["available_business_dates_count"] == 60


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
            "2022-05-16",
            "--target-end-date",
            "2022-05-16",
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
    assert guard["reason"] in {"HISTORICAL_SOURCE_WARMUP_INSUFFICIENT", "QUOTE_TARGET_DATE_MISSING"}
