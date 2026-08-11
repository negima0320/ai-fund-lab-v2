from pathlib import Path

from ai_fund_lab_v2.data_store import DataLayer, MarketDataStore
from ai_fund_lab_v2.features import FeatureBuilder
from ai_fund_lab_v2.runtime import RuntimePaths


def test_feature_builder_saves_skeleton_to_feature_layer(tmp_path: Path) -> None:
    store = MarketDataStore(RuntimePaths(runtime_dir=tmp_path / "runtime"))
    builder = FeatureBuilder(store)

    builder.save_daily_quote_feature_skeleton(
        [{"Date": "2026-06-01", "Code": "72030", "AdjC": 1010.0, "AdjVo": 100_000}]
    )

    records = store.read_layer(DataLayer.FEATURES, "/features/daily_quotes")
    assert len(records) == 1
    assert records[0]["close"] == 1010.0
    assert records[0]["price_momentum"] is None
    assert records[0]["endpoint"] == "/features/daily_quotes"


def test_phase29_l16_candidate_features_emit_rolling_median_traded_value_when_available() -> None:
    from ai_fund_lab_v2.candidate_ai.feature_builder import build_candidate_features_mock

    rows = [
        {
            "date": f"2026-06-{day:02d}",
            "code": "72030",
            "close": 100.0 + day,
            "volume": 100_000 + day,
            "traded_value": 1_000_000 + day,
        }
        for day in range(1, 22)
    ]

    features = build_candidate_features_mock(rows, as_of_date="2026-06-21")

    assert features[0]["rolling_median_traded_value_20"] == 1_000_011.5
