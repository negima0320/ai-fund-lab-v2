import pandas as pd

from ai_fund_lab_v2.paper_trading.feature_refresh import (
    OPPORTUNITY_MODEL_INPUT_COLUMNS,
    _build_candidate_feature_frame,
    _build_opportunity_feature_input,
    _latest_listed_snapshot,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    OPPORTUNITY_REQUIRED_COLUMNS,
    validate_feature_consumer_readiness,
)


def test_phase17_v_opportunity_feature_refresh_adds_pit_market_sector_columns():
    target_date = "2026-07-06"
    created_at = "2026-07-14T00:00:00+00:00"
    quotes = _quotes_frame(target_date)
    listed = _latest_listed_snapshot(_listed_frame(target_date), target_data_until=target_date)

    candidate = _build_candidate_feature_frame(
        quotes=quotes,
        listed=listed,
        target_data_until=target_date,
        created_at=created_at,
    )
    opportunity = _build_opportunity_feature_input(
        candidate=candidate,
        listed=listed,
        target_data_until=target_date,
        created_at=created_at,
    )

    assert list(opportunity.columns)[6:] == list(OPPORTUNITY_MODEL_INPUT_COLUMNS)
    assert set(OPPORTUNITY_MODEL_INPUT_COLUMNS) <= set(opportunity.columns)
    assert "feature__market_breadth_20d" not in opportunity.columns
    assert opportunity["feature_version"].eq("runtime_v2_opportunity_feature_input_v2_market_sector").all()
    assert opportunity["sector_return_20d"].notna().all()
    assert opportunity["stock_vs_sector_return_20d"].notna().all()


def test_phase17_v_listed_snapshot_excludes_future_sector_revisions():
    listed = _listed_frame("2026-07-06")
    snapshot = _latest_listed_snapshot(listed, target_data_until="2026-07-06")

    by_code = dict(zip(snapshot["Code"].astype(str), snapshot["S33Nm"].astype(str)))
    assert by_code["10010"] == "Tech"
    assert by_code["10020"] == "Banks"
    assert "FutureTech" not in set(snapshot["S33Nm"].astype(str))


def test_phase17_v_consumer_readiness_rejects_legacy_opportunity_contract(tmp_path):
    operations_root = tmp_path / ".runtime" / "operations"
    feature_dir = operations_root / "feature_artifacts" / "2026-07-06"
    feature_dir.mkdir(parents=True)
    legacy = {
        column: _value_for_column(column, "2026-07-06")
        for column in OPPORTUNITY_REQUIRED_COLUMNS
        if not column.startswith("market_") and not column.startswith("sector_") and column != "stock_vs_sector_return_20d"
    }
    pd.DataFrame([legacy]).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame([legacy]).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(columns=["target_date", "code", "no_position_reason"]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": "2026-07-06", "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )

    readiness = validate_feature_consumer_readiness(operations_root=operations_root, feature_date="2026-07-06")

    assert readiness.status == "REVIEW_REQUIRED"
    assert readiness.opportunity_schema_status == "REVIEW_REQUIRED"
    assert "market_breadth_20d" in readiness.opportunity.missing_columns
    assert "sector_rank_20d" in readiness.opportunity.missing_columns


def _quotes_frame(target_date: str) -> pd.DataFrame:
    dates = pd.bdate_range(end=target_date, periods=62).strftime("%Y-%m-%d").tolist()
    rows = []
    for idx, date in enumerate(dates):
        for code, base in (("10010", 100.0), ("10020", 80.0), ("10030", 120.0)):
            rows.append(
                {
                    "target_date": date,
                    "code": code,
                    "Close": base + idx,
                    "Volume": 1000 + idx * 10,
                }
            )
    return pd.DataFrame(rows)


def _listed_frame(target_date: str) -> pd.DataFrame:
    rows = [
        {"Date": target_date, "Code": "10010", "CoName": "A", "ProdCat": "011", "MktNm": "プライム", "S33Nm": "Tech"},
        {"Date": target_date, "Code": "10020", "CoName": "B", "ProdCat": "011", "MktNm": "プライム", "S33Nm": "Banks"},
        {"Date": target_date, "Code": "10030", "CoName": "C", "ProdCat": "011", "MktNm": "プライム", "S33Nm": "Tech"},
        {"Date": "2026-07-07", "Code": "10010", "CoName": "A", "ProdCat": "011", "MktNm": "プライム", "S33Nm": "FutureTech"},
    ]
    return pd.DataFrame(rows)


def _value_for_column(column: str, feature_date: str):
    if column == "target_date":
        return feature_date
    if column == "code":
        return "10010"
    if column.startswith("missing_flags_") or column.endswith("_flag") or column.endswith("_context"):
        return False
    return 1.0
