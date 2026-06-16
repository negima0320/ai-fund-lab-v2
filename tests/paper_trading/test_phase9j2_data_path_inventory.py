from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.audit_phase9j2_data_path_inventory import discover_inventory, inspect_artifact


def test_inventory_detects_parquet_csv_json_and_dates(tmp_path: Path) -> None:
    parquet = tmp_path / ".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"
    parquet.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {"target_date": "2026-06-14", "code": "10010", "source": "jquants", "endpoint": "daily_quotes_normalized"},
            {"target_date": "2026-06-15", "code": "10020", "source": "jquants", "endpoint": "daily_quotes_normalized"},
        ]
    ).to_parquet(parquet, index=False)
    csv = tmp_path / "reports/opportunity_ai/features.csv"
    csv.parent.mkdir(parents=True)
    pd.DataFrame([{"target_date": "2026-06-15", "code": "10010"}]).to_csv(csv, index=False)
    js = tmp_path / ".runtime/data/raw/jquants/listed_issues/data.json"
    js.parent.mkdir(parents=True)
    js.write_text('[{"Date":"2026-06-15","Code":"10010","source":"jquants"}]', encoding="utf-8")

    items = discover_inventory(root=tmp_path, scan_dirs=("reports", ".runtime"))
    by_path = {item.path: item for item in items}

    assert by_path[".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"].artifact_type == "normalized_daily_quotes"
    assert by_path[".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"].max_date == "2026-06-15"
    assert by_path[".runtime/data/raw/jquants/listed_issues/data.json"].artifact_type == "listed_info"
    assert by_path["reports/opportunity_ai/features.csv"].usable_for_phase9 is False


def test_inventory_detects_response_dir_as_long_raw_candidate(tmp_path: Path) -> None:
    response_dir = tmp_path / ".runtime/data/raw/jquants/equities_bars_daily/responses"
    response_dir.mkdir(parents=True)
    (response_dir / "2021-06-14_page_001.json").write_text("{}", encoding="utf-8")
    (response_dir / "2026-06-15_page_001.json").write_text("{}", encoding="utf-8")

    items = discover_inventory(root=tmp_path, scan_dirs=(".runtime",))
    response = next(item for item in items if item.artifact_type == "raw_daily_quotes_response_dir")

    assert response.min_date == "2021-06-14"
    assert response.max_date == "2026-06-15"
    assert response.usable_for_phase9 is True


def test_prohibited_report_source_is_not_usable(tmp_path: Path) -> None:
    path = tmp_path / "reports/capital_allocation_ai/phase7g/trade_ledger.csv"
    path.parent.mkdir(parents=True)
    pd.DataFrame([{"target_date": "2026-06-15", "code": "10010"}]).to_csv(path, index=False)

    item = inspect_artifact(path, root=tmp_path)

    assert item is not None
    assert item.usable_for_phase9 is False
    assert item.reason == "prohibited_source"
