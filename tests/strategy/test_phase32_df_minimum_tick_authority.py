from __future__ import annotations

from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.strategy import input_materialization
from ai_fund_lab_v2.strategy.position_sizing import _phase29_l16_strategy_evidence
from ai_fund_lab_v2.strategy.minimum_tick_authority import (
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_KNOWN,
    resolve_minimum_tick,
    validate_minimum_tick_authority,
)


def test_phase32_df_special_fine_tick_resolves_below_one_yen() -> None:
    authority = resolve_minimum_tick(
        symbol="94320",
        business_date="2023-03-15",
        reference_price=157.9,
        security_metadata={
            "code": "94320",
            "Date": "2023-03-15",
            "ProdCat": "011",
            "MktNm": "プライム",
            "ScaleCat": "TOPIX Core30",
            "classification_source": "fixture_listed_issues",
        },
        source_artifact_id="fixture_listed_issues",
        source_artifact_hash="a" * 64,
        runtime_run_id="run-a",
    )

    assert authority["resolution_status"] == STATUS_KNOWN
    assert authority["tick_table_class"] == "TOPIX500"
    assert authority["minimum_tick"] == 0.1
    assert authority["single_tick_pct"] == 0.00063331
    assert validate_minimum_tick_authority(authority, expected_symbol="94320", expected_business_date="2023-03-15", expected_runtime_run_id="run-a")[0] == "PASS"


def test_phase32_df_other_issues_low_price_tick_resolves_with_provenance() -> None:
    authority = resolve_minimum_tick(
        symbol="93180",
        business_date="2023-03-15",
        reference_price=3.0,
        security_metadata={
            "code": "93180",
            "Date": "2023-03-15",
            "ProdCat": "011",
            "MktNm": "スタンダード",
            "ScaleCat": "-",
            "classification_source": "fixture_listed_issues",
        },
        source_artifact_id="fixture_listed_issues",
        source_artifact_hash="b" * 64,
    )

    assert authority["resolution_status"] == STATUS_KNOWN
    assert authority["tick_table_class"] == "OTHER_ISSUES"
    assert authority["minimum_tick"] == 1.0
    assert authority["single_tick_pct"] == 0.33333333
    assert authority["source_artifact_hash"] == "b" * 64


def test_phase32_df_missing_table_class_is_explicit_insufficient_evidence() -> None:
    authority = resolve_minimum_tick(
        symbol="99990",
        business_date="2023-03-15",
        reference_price=500.0,
        security_metadata={"code": "99990", "Date": "2023-03-15"},
    )

    assert authority["resolution_status"] == STATUS_INSUFFICIENT_EVIDENCE
    assert authority["minimum_tick"] is None
    assert "security_type_missing" in authority["resolution_reason_codes"]
    assert "tick_table_class_missing" in authority["resolution_reason_codes"]


def test_phase32_df_future_rule_version_does_not_rewrite_historical_date() -> None:
    historical = resolve_minimum_tick(
        symbol="83060",
        business_date="2023-03-15",
        reference_price=861.5,
        security_metadata={"code": "83060", "Date": "2023-03-15", "ProdCat": "011", "ScaleCat": "TOPIX Core30"},
    )
    future = resolve_minimum_tick(
        symbol="83060",
        business_date="2027-03-01",
        reference_price=861.5,
        security_metadata={"code": "83060", "Date": "2027-03-01", "ProdCat": "011", "ScaleCat": "TOPIX Core30"},
    )

    assert historical["resolution_status"] == STATUS_KNOWN
    assert historical["tick_rule_version"] == "JPX_TSE_CASH_TICK_TABLE_PRE_2027"
    assert future["resolution_status"] == STATUS_INSUFFICIENT_EVIDENCE
    assert "tick_rule_version_not_implemented_for_business_date" in future["resolution_reason_codes"]


def test_phase32_df_stale_or_cross_run_authority_is_rejected() -> None:
    authority = resolve_minimum_tick(
        symbol="94320",
        business_date="2023-03-15",
        reference_price=157.9,
        security_metadata={"code": "94320", "Date": "2023-03-15", "ProdCat": "011", "ScaleCat": "TOPIX Core30"},
        runtime_run_id="run-a",
    )

    status, reasons = validate_minimum_tick_authority(
        authority,
        expected_symbol="94320",
        expected_business_date="2023-03-15",
        expected_runtime_run_id="run-b",
    )

    assert status == "BLOCK"
    assert "runtime_run_id_mismatch" in reasons


def test_phase32_df_technical_features_materialize_minimum_tick_authority(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", symbol="94320", days=35, close=157.9)
    listed = tmp_path / "listed.parquet"
    pd.DataFrame(
        [
            {
                "Date": "2023-03-15",
                "Code": "94320",
                "ProdCat": "011",
                "MktNm": "プライム",
                "ScaleCat": "TOPIX Core30",
            }
        ]
    ).to_parquet(listed)

    result = input_materialization.produce_pm_technical_feature_artifact(
        business_date="2023-03-15",
        feature_date="2023-03-15",
        source_path=quotes,
        output_path=tmp_path / "technical.json",
        symbols=("94320",),
        listed_issues_path=listed,
        runtime_run_id="run-a",
        as_of="2023-03-15T00:00:00+00:00",
    )
    row = result.payload["rows"][0]

    assert result.status == "PASS"
    assert row["minimum_tick_authority_status"] == STATUS_KNOWN
    assert row["minimum_tick"] == 0.1
    assert row["minimum_tick_authority_hash"] == row["minimum_tick_authority"]["authority_hash"]
    assert row["minimum_tick_authority"]["runtime_run_id"] == "run-a"


def test_phase32_df_technical_features_missing_metadata_stays_item_scoped(tmp_path: Path) -> None:
    quotes = _write_quotes(tmp_path / "quotes.parquet", symbol="99990", days=35, close=500.0)

    result = input_materialization.produce_pm_technical_feature_artifact(
        business_date="2023-03-15",
        feature_date="2023-03-15",
        source_path=quotes,
        output_path=tmp_path / "technical.json",
        symbols=("99990",),
        as_of="2023-03-15T00:00:00+00:00",
    )
    row = result.payload["rows"][0]

    assert result.status == "PASS"
    assert row["minimum_tick_authority_status"] == STATUS_INSUFFICIENT_EVIDENCE
    assert row["minimum_tick"] is None
    assert row["decision_resolution"] == "RESOLVED"


def test_phase32_df_position_sizing_context_preserves_authority_hash() -> None:
    authority = resolve_minimum_tick(
        symbol="93180",
        business_date="2023-03-15",
        reference_price=3.0,
        security_metadata={"code": "93180", "Date": "2023-03-15", "ProdCat": "011", "ScaleCat": "-"},
    )

    evidence = _phase29_l16_strategy_evidence(
        {
            "single_tick_pct": authority["single_tick_pct"],
            "price_tick_risk_tier": "EXTREME",
            "minimum_tick_authority_status": authority["resolution_status"],
            "minimum_tick_authority": authority,
            "minimum_tick_authority_hash": authority["authority_hash"],
            "minimum_tick_resolution": {"status": authority["resolution_status"]},
        }
    )

    assert evidence["minimum_tick_authority_status"] == STATUS_KNOWN
    assert evidence["minimum_tick_authority_hash"] == authority["authority_hash"]
    assert evidence["minimum_tick_authority"]["minimum_tick"] == 1.0


def _write_quotes(path: Path, *, symbol: str, days: int, close: float) -> Path:
    dates = pd.bdate_range(end="2023-03-15", periods=days)
    rows = []
    for idx, day in enumerate(dates):
        rows.append(
            {
                "target_date": day.date().isoformat(),
                "code": symbol,
                "Close": close + (idx % 5) * 0.1,
                "Volume": 1_000_000 + idx,
            }
        )
    pd.DataFrame(rows).to_parquet(path)
    return path
