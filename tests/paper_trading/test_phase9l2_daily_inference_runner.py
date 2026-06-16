from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.daily_inference_runner import INFERENCE_BLOCKED, INFERENCE_READY, run_daily_inference
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, write_ledger


def test_daily_inference_runner_creates_artifacts_and_reports(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)

    result = run_daily_inference(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        allow_initial_ledger=True,
    )

    assert result.status == INFERENCE_READY
    assert Path(result.artifact_paths["candidate"]).is_file()
    assert Path(result.artifact_paths["opportunity"]).is_file()
    assert Path(result.artifact_paths["position"]).is_file()
    assert Path(result.artifact_paths["allocation"]).is_file()
    assert Path(result.artifact_paths["order_plan"]).is_file()
    assert Path(result.report_paths["internal_markdown"]).is_file()
    assert Path(result.report_paths["public_markdown"]).is_file()
    assert Path(result.report_paths["blog_draft"]).is_file()
    assert not any(result.prohibited_flags.values())
    candidate_payload = json.loads(Path(result.artifact_paths["candidate"]).read_text(encoding="utf-8"))
    assert candidate_payload["rows"][0]["public_confidence_score"] > 0


def test_daily_inference_blocks_when_ledger_missing_without_explicit_initial_option(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)

    result = run_daily_inference(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        allow_initial_ledger=False,
    )

    assert result.status == INFERENCE_BLOCKED
    assert "initial_ledger_required" in result.blocked_reasons
    assert not result.artifact_paths


def test_daily_inference_can_use_existing_ledger_without_writing_fills(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)
    ledger_path = write_ledger(PaperTradingLedger(cash=Decimal("1000000")), runtime_dir=tmp_path / ".runtime")

    result = run_daily_inference(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        ledger_path=ledger_path,
    )

    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert result.status == INFERENCE_READY
    assert manifest["training_executed"] is False
    assert manifest["inference_executed"] is True
    assert manifest["prohibited_flags"]["virtual_fill_executed"] is False


def _write_l2_inputs(tmp_path: Path) -> tuple[Path, Path]:
    feature_dir = tmp_path / "features" / "2026-06-15"
    feature_dir.mkdir(parents=True)
    candidate = pd.DataFrame(
        [
            {
                "target_date": "2026-06-15",
                "as_of_date": "2026-06-15",
                "code": "10010",
                "universe_eligible": True,
                "price_momentum_return_5d": 0.05,
                "price_momentum_return_20d": 0.12,
                "volume_momentum_ratio_5d": 1.5,
                "volatility_return_std_20d": 0.01,
                "trend_close_over_ma_20d": 0.04,
                "liquidity_avg_volume_20d": 100000,
                "data_until": "2026-06-15",
            },
            {
                "target_date": "2026-06-15",
                "as_of_date": "2026-06-15",
                "code": "10020",
                "universe_eligible": True,
                "price_momentum_return_5d": 0.02,
                "price_momentum_return_20d": 0.08,
                "volume_momentum_ratio_5d": 1.1,
                "volatility_return_std_20d": 0.02,
                "trend_close_over_ma_20d": 0.02,
                "liquidity_avg_volume_20d": 90000,
                "data_until": "2026-06-15",
            },
        ]
    )
    candidate.to_parquet(feature_dir / "candidate_features.parquet", index=False)
    opportunity = candidate.rename(
        columns={
            "price_momentum_return_5d": "feature__price_momentum_return_5d",
            "price_momentum_return_20d": "feature__price_momentum_return_20d",
            "volume_momentum_ratio_5d": "feature__volume_momentum_ratio_5d",
            "volatility_return_std_20d": "feature__volatility_return_std_20d",
            "trend_close_over_ma_20d": "feature__trend_close_over_ma_20d",
            "liquidity_avg_volume_20d": "feature__liquidity_avg_volume_20d",
        }
    )
    opportunity.to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame([{"target_date": "2026-06-15", "data_until": "2026-06-15", "code": "__NONE__"}]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": "2026-06-15", "data_until": "2026-06-15", "code": "__POLICY_INPUT__"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    quotes_path = tmp_path / "quotes.parquet"
    pd.DataFrame(
        [
            {"date": "2026-06-15", "code": "10010", "close": 1000.0},
            {"date": "2026-06-15", "code": "10020", "close": 1500.0},
        ]
    ).to_parquet(quotes_path, index=False)
    return tmp_path / "features", quotes_path
