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
