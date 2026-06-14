#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.position_management_ai.inference import (  # noqa: E402
    DEFAULT_FEATURE_PATH,
    DEFAULT_HOLDING_PATH,
    DEFAULT_OPPORTUNITY_PATH,
    DEFAULT_OUTPUT_DIR,
    run_position_management_inference,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase6-A Position Management AI small dry-run.")
    parser.add_argument("--holding-path", default=None)
    parser.add_argument("--opportunity-path", default=None)
    parser.add_argument("--feature-path", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--use-fixture", action="store_true", help="Write and use a 4-row local dry-run fixture.")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    if args.use_fixture or not args.holding_path:
        fixture_dir = output_dir / "fixture_inputs"
        fixture_dir.mkdir(parents=True, exist_ok=True)
        holding_path = fixture_dir / "holdings.parquet"
        opportunity_path = fixture_dir / "opportunity.parquet"
        feature_path = fixture_dir / "features.parquet"
        fixture_holding_frame().to_parquet(holding_path, index=False)
        fixture_opportunity_frame().to_parquet(opportunity_path, index=False)
        fixture_feature_frame().to_parquet(feature_path, index=False)
    else:
        holding_path = Path(args.holding_path or DEFAULT_HOLDING_PATH)
        opportunity_path = Path(args.opportunity_path or DEFAULT_OPPORTUNITY_PATH)
        feature_path = Path(args.feature_path or DEFAULT_FEATURE_PATH)

    result = run_position_management_inference(
        holding_path=holding_path,
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        output_dir=output_dir,
    )
    print(json.dumps(result.summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.summary.get("status") in {"OK", "BLOCKED"} else 1


def fixture_holding_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-12", "code": "1001", "entry_price": 100.0, "current_price": 112.0, "holding_days": 12, "position_size": 100, "peak_return": 0.14},
            {"target_date": "2026-06-12", "code": "1002", "entry_price": 100.0, "current_price": 91.0, "holding_days": 15, "position_size": 100, "peak_return": 0.04},
            {"target_date": "2026-06-12", "code": "1003", "entry_price": 100.0, "current_price": 106.0, "holding_days": 20, "position_size": 100, "peak_return": 0.16},
            {"target_date": "2026-06-12", "code": "1004", "entry_price": 100.0, "current_price": 104.0, "holding_days": 8, "position_size": 100, "peak_return": 0.05},
        ]
    )


def fixture_opportunity_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"target_date": "2026-06-12", "code": "1001", "expected_edge_score": 0.16, "buy_rank": 2, "downside_risk_score": 0.20, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "1002", "expected_edge_score": -0.04, "buy_rank": 35, "downside_risk_score": 0.80, "risk_guard_status": "bad"},
            {"target_date": "2026-06-12", "code": "1003", "expected_edge_score": 0.07, "buy_rank": 8, "downside_risk_score": 0.66, "risk_guard_status": "ok"},
            {"target_date": "2026-06-12", "code": "1004", "expected_edge_score": 0.05, "buy_rank": 12, "downside_risk_score": 0.30, "risk_guard_status": "ok"},
        ]
    )


def fixture_feature_frame() -> pd.DataFrame:
    rows = [
        ("1001", 1.08, 1.05, 0.08, 0.18, 0.02, 1.50),
        ("1002", 0.94, 0.96, -0.08, -0.16, 0.08, 0.70),
        ("1003", 1.03, 1.02, 0.02, 0.09, 0.09, 1.20),
        ("1004", 1.04, 1.02, 0.03, 0.08, 0.03, 1.10),
    ]
    return pd.DataFrame(
        [
            {
                "target_date": "2026-06-12",
                "as_of_date": "2026-06-12",
                "code": code,
                "feature_version": "fixture_feature_v1",
                "price_momentum_return_5d": return_5d,
                "price_momentum_return_20d": return_20d,
                "trend_close_over_ma_20d": close_over_ma,
                "trend_ma_5_20_ratio": ma_ratio,
                "volatility_return_std_20d": volatility,
                "volume_momentum_ratio_5d": volume,
            }
            for code, close_over_ma, ma_ratio, return_5d, return_20d, volatility, volume in rows
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
