from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts/run_phase9j3_rebuild_canonical_normalized_daily_quotes.py"
SPEC = importlib.util.spec_from_file_location("phase9j3_rebuild", SCRIPT_PATH)
assert SPEC and SPEC.loader
phase9j3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = phase9j3
SPEC.loader.exec_module(phase9j3)


def test_dry_run_does_not_write_normalized_or_update_config(tmp_path: Path) -> None:
    env = _make_env(tmp_path)

    result = phase9j3.rebuild_canonical_normalized_daily_quotes(
        raw_root=env["raw_root"],
        target_data_until="2026-06-15",
        dry_run=True,
        execute=False,
        output_root=env["output_root"],
        config_path=env["config"],
        supplemental_raw_table=env["supplemental"],
        listed_info_path=env["listed"],
        markdown_report_path=tmp_path / "dry.md",
        json_report_path=tmp_path / "dry.json",
    )

    assert result.status == "CANONICAL_NORMALIZED_REBUILD_DRY_RUN"
    assert not (env["output_root"] / "data.parquet").exists()
    assert "normalized_daily_quotes: null" in env["config"].read_text(encoding="utf-8")


def test_execute_writes_isolated_normalized_and_updates_config_only_on_success(tmp_path: Path) -> None:
    env = _make_env(tmp_path)

    result = phase9j3.rebuild_canonical_normalized_daily_quotes(
        raw_root=env["raw_root"],
        target_data_until="2026-06-15",
        dry_run=False,
        execute=True,
        output_root=env["output_root"],
        config_path=env["config"],
        supplemental_raw_table=env["supplemental"],
        listed_info_path=env["listed"],
        markdown_report_path=tmp_path / "execute.md",
        json_report_path=tmp_path / "execute.json",
        feature_output_root=tmp_path / ".runtime/phase9/features",
        feature_manifest_root=tmp_path / ".runtime/phase9/feature_refresh",
        feature_markdown_report_path=tmp_path / "feature.md",
        feature_json_report_path=tmp_path / "feature.json",
    )
    frame = pd.read_parquet(env["output_root"] / "data.parquet")

    assert result.status == "CANONICAL_NORMALIZED_READY"
    assert result.config_updated is True
    assert str(env["output_root"] / "data.parquet") in env["config"].read_text(encoding="utf-8")
    assert (env["output_root"] / "normalize_manifest.json").is_file()
    assert set(("date", "code", "open", "high", "low", "close", "volume")).issubset(frame.columns)
    assert frame["source"].eq("jquants").all()


def test_existing_raw_normalized_is_not_overwritten(tmp_path: Path) -> None:
    env = _make_env(tmp_path)
    raw_normalized = tmp_path / ".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"
    raw_normalized.parent.mkdir(parents=True, exist_ok=True)
    raw_normalized.write_text("keep-me", encoding="utf-8")

    phase9j3.rebuild_canonical_normalized_daily_quotes(
        raw_root=env["raw_root"],
        target_data_until="2026-06-15",
        dry_run=False,
        execute=True,
        output_root=env["output_root"],
        config_path=env["config"],
        supplemental_raw_table=env["supplemental"],
        listed_info_path=env["listed"],
        markdown_report_path=tmp_path / "execute.md",
        json_report_path=tmp_path / "execute.json",
        feature_output_root=tmp_path / ".runtime/phase9/features",
        feature_manifest_root=tmp_path / ".runtime/phase9/feature_refresh",
        feature_markdown_report_path=tmp_path / "feature.md",
        feature_json_report_path=tmp_path / "feature.json",
    )

    assert raw_normalized.read_text(encoding="utf-8") == "keep-me"


def test_future_rows_excluded_and_duplicates_removed(tmp_path: Path) -> None:
    env = _make_env(tmp_path, include_duplicate=True, include_future=True)

    result = phase9j3.rebuild_canonical_normalized_daily_quotes(
        raw_root=env["raw_root"],
        target_data_until="2026-06-15",
        dry_run=False,
        execute=True,
        output_root=env["output_root"],
        config_path=env["config"],
        supplemental_raw_table=env["supplemental"],
        listed_info_path=env["listed"],
        markdown_report_path=tmp_path / "execute.md",
        json_report_path=tmp_path / "execute.json",
        feature_output_root=tmp_path / ".runtime/phase9/features",
        feature_manifest_root=tmp_path / ".runtime/phase9/feature_refresh",
        feature_markdown_report_path=tmp_path / "feature.md",
        feature_json_report_path=tmp_path / "feature.json",
    )
    frame = pd.read_parquet(env["output_root"] / "data.parquet")

    assert "2026-06-16" not in set(frame["date"].astype(str))
    assert int(frame.duplicated(subset=["date", "code"]).sum()) == 0
    assert result.future_rows_excluded >= 1
    assert result.duplicate_rows_skipped >= 1


def test_prohibited_flags_remain_false(tmp_path: Path) -> None:
    env = _make_env(tmp_path)

    result = phase9j3.rebuild_canonical_normalized_daily_quotes(
        raw_root=env["raw_root"],
        target_data_until="2026-06-15",
        dry_run=False,
        execute=True,
        output_root=env["output_root"],
        config_path=env["config"],
        supplemental_raw_table=env["supplemental"],
        listed_info_path=env["listed"],
        markdown_report_path=tmp_path / "execute.md",
        json_report_path=tmp_path / "execute.json",
        feature_output_root=tmp_path / ".runtime/phase9/features",
        feature_manifest_root=tmp_path / ".runtime/phase9/feature_refresh",
        feature_markdown_report_path=tmp_path / "feature.md",
        feature_json_report_path=tmp_path / "feature.json",
    )

    assert result.jquants_only_source_used is True
    assert result.model_retraining_executed is False
    assert result.inference_executed is False
    assert result.order_plan_generation_executed is False
    assert result.broker_order_api_called is False
    assert result.open_d_started is False
    assert result.unlock_trade_called is False
    assert result.paper_ledger_fill_executed is False
    assert result.virtual_fill_executed is False


def _make_env(tmp_path: Path, *, include_duplicate: bool = False, include_future: bool = False) -> dict[str, Path]:
    raw_root = tmp_path / ".runtime/data/raw/jquants/equities_bars_daily/responses"
    supplemental = tmp_path / ".runtime/data/raw/jquants/equities_bars_daily/data.parquet"
    listed = tmp_path / ".runtime/data/raw/jquants/listed_issues/data.parquet"
    output_root = tmp_path / ".runtime/phase9/canonical_data/normalized_daily_quotes"
    config = tmp_path / "config/phase9_data_sources.yaml"
    _write_raw_responses(raw_root, include_duplicate=include_duplicate, include_future=include_future)
    _write_supplemental(supplemental)
    _write_listed(listed)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "\n".join(
            [
                "phase9_data_sources:",
                f"  raw_daily_quotes: {raw_root}",
                "  normalized_daily_quotes: null",
                f"  listed_info: {listed}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "raw_root": raw_root,
        "supplemental": supplemental,
        "listed": listed,
        "output_root": output_root,
        "config": config,
    }


def _write_raw_responses(raw_root: Path, *, include_duplicate: bool, include_future: bool) -> None:
    raw_root.mkdir(parents=True, exist_ok=True)
    for day in pd.bdate_range("2026-05-01", "2026-06-12"):
        date = day.strftime("%Y-%m-%d")
        rows = [_raw_record(date, "10010", 100.0)]
        if include_duplicate and date == "2026-05-08":
            rows.append(_raw_record(date, "10010", 101.0))
        payload = {"date": date, "payload": {"data": rows}, "phase": 9}
        (raw_root / f"{date}_page_001.json").write_text(json.dumps(payload), encoding="utf-8")
    if include_future:
        payload = {"date": "2026-06-16", "payload": {"data": [_raw_record("2026-06-16", "10010", 200.0)]}, "phase": 9}
        (raw_root / "2026-06-16_page_001.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_supplemental(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for day in pd.bdate_range("2026-06-01", "2026-06-15"):
        date = day.strftime("%Y-%m-%d")
        rows.append(_raw_record(date, "10010", 150.0))
        rows.append(_raw_record(date, "10020", 170.0))
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "target_date": "2026-06-15",
                "Date": "2026-06-15",
                "code": "10010",
                "Code": "10010",
                "CoName": "Fixture One",
                "ProdCat": "011",
                "MktNm": "プライム",
            },
            {
                "target_date": "2026-06-15",
                "Date": "2026-06-15",
                "code": "10020",
                "Code": "10020",
                "CoName": "Fixture Two",
                "ProdCat": "011",
                "MktNm": "スタンダード",
            },
        ]
    ).to_parquet(path, index=False)


def _raw_record(date: str, code: str, base: float) -> dict[str, object]:
    return {
        "Date": date,
        "Code": code,
        "AdjO": base,
        "AdjH": base + 2,
        "AdjL": base - 1,
        "AdjC": base + 1,
        "AdjVo": 1000,
        "O": base,
        "H": base + 2,
        "L": base - 1,
        "C": base + 1,
        "Vo": 1000,
    }
