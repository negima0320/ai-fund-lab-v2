from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ai_fund_lab_v2.data_store.market_data_store import MarketDataStore


@dataclass(frozen=True)
class FeatureBuilder:
    """Phase1-A feature-builder entry point.

    Future labels such as future_return_*, future_max_return_*, and
    future_max_drawdown_* must be produced by a label builder and saved to the
    label layer, never mixed into inference features.
    """

    store: MarketDataStore

    def build_daily_quote_feature_skeleton(self, raw_records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        features: list[dict[str, Any]] = []
        for record in raw_records:
            features.append(
                {
                    "target_date": record.get("target_date") or record.get("Date"),
                    "code": record.get("code") or record.get("Code"),
                    "close": record.get("AdjC") or record.get("C"),
                    "volume": record.get("AdjVo") or record.get("Vo"),
                    "price_momentum": None,
                    "volume_momentum": None,
                    "moving_average": None,
                    "high_breakout": None,
                    "volatility": None,
                }
            )
        return features

    def save_daily_quote_feature_skeleton(self, raw_records: Iterable[dict[str, Any]]) -> None:
        features = self.build_daily_quote_feature_skeleton(raw_records)
        self.store.save_features(features, endpoint="/features/daily_quotes")
