import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.data_sources.jquants import JQuantsClientError
from ai_fund_lab_v2.paper_trading.market_data_refresh import run_market_data_refresh
from ai_fund_lab_v2.runtime_v2.market_refresh import pipeline as market_refresh_pipeline
from ai_fund_lab_v2.runtime_v2.market_refresh.pipeline import run_runtime_v2_market_refresh_pipeline


ARTIFACTS = (
    "candidate_features.parquet",
    "opportunity_feature_input.parquet",
    "position_feature_input.parquet",
    "capital_policy_input.parquet",
)


class DiagnosticFailFetcher:
    def __init__(self, *, error_class: str, network_error_type: str = "", http_status="") -> None:
        self.error_class = error_class
        self.network_error_type = network_error_type
        self.http_status = http_status

    def fetch_daily_quotes(self, *, from_date: str, to_date: str):
        raise self._error(date=from_date, from_date=from_date, to_date=to_date)

    def fetch_daily_quotes_for_date(self, *, target_date: str):
        raise self._error(date=target_date)

    def fetch_listed_info(self, *, date: str):
        return [{"Date": date, "Code": "72030", "CompanyName": "Toyota"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str):
        return [{"Date": from_date, "HolDiv": "1"}]

    def _error(self, *, date: str = "", from_date: str = "", to_date: str = "") -> JQuantsClientError:
        return JQuantsClientError(
            "redacted test error",
            diagnostic={
                "endpoint": "/v2/equities/bars/daily",
                "date": date,
                "from_date": from_date,
                "to_date": to_date,
                "error_class": self.error_class,
                "network_error_type": self.network_error_type,
                "http_status": self.http_status,
                "url_host": "api.jquants.com",
            },
        )


def test_phase14e41_url_error_is_api_network_error_not_api_param_error(tmp_path):
    result = run_market_data_refresh(
        from_date="2026-07-08",
        to_date="2026-07-08",
        dry_run=False,
        allow_api_fetch=True,
        fetch_mode="per-date",
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        fetcher=DiagnosticFailFetcher(error_class="API_NETWORK_ERROR", network_error_type="dns"),
        today="2026-07-08",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert result.status == "API_NETWORK_ERROR"
    assert result.api_error_classification == "API_NETWORK_ERROR"
    assert result.next_action == "check_network_connectivity"
    assert "API_PARAM_ERROR" not in result.blocked_reasons
    assert manifest["api_error_classification"] == "API_NETWORK_ERROR"
    assert manifest["next_action"] == "check_network_connectivity"
    assert manifest["api_error_diagnostics"][0]["network_error_type"] == "dns"
    assert "api_key" not in Path(result.manifest_path).read_text(encoding="utf-8").lower()
    assert "x-api-key" not in Path(result.manifest_path).read_text(encoding="utf-8").lower()


def test_phase14e41_http_400_remains_api_param_error(tmp_path):
    result = run_market_data_refresh(
        from_date="2026-07-08",
        to_date="2026-07-08",
        dry_run=False,
        allow_api_fetch=True,
        fetch_mode="per-date",
        raw_output_root=tmp_path / "raw",
        normalized_output_root=tmp_path / "raw_normalized",
        manifest_output_root=tmp_path / "manifest",
        fetcher=DiagnosticFailFetcher(error_class="API_PARAM_ERROR", http_status=400),
        today="2026-07-08",
        markdown_report_path=tmp_path / "report.md",
        json_report_path=tmp_path / "report.json",
    )

    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert result.status == "API_PARAM_ERROR"
    assert result.api_error_classification == "API_PARAM_ERROR"
    assert result.next_action == "review_api_parameters"
    assert manifest["api_error_diagnostics"][0]["http_status"] == 400


def test_phase14e41_network_error_fresh_carryover_is_allowed(tmp_path, monkeypatch):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_inputs(operations_root / "feature_artifacts", feature_date="2026-07-07")

    def fake_operations_market_refresh(**kwargs):
        return {
            "status": "BLOCK",
            "blocked_reasons": ["API_NETWORK_ERROR", "api_fetch_failed:JQuantsClientError", "DATA_FRESHNESS_BLOCKED"],
            "jquants_api_fetch_executed": True,
            "canonical_normalized_updated": True,
            "feature_refresh_executed": True,
            "feature_refresh_status": "FEATURES_READY",
            "latest_available_market_date": "2026-07-07",
            "data_quality_status": "BLOCK",
            "feature_freshness_status": "MARKET_DATA_NOT_YET_AVAILABLE",
        }

    monkeypatch.setattr(market_refresh_pipeline, "_run_operations_market_refresh", fake_operations_market_refresh)

    result = run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-08",
        operations_root=operations_root,
        allow_api_fetch=True,
    )

    assert result.status == "PASS"
    assert result.reason == "carryover_feature_artifacts_available"
    assert result.carryover_used is True
    assert result.freshness_lag_business_days == 1
    assert "API_NETWORK_ERROR" in result.blocked_reasons
    assert "DATA_FRESHNESS_BLOCKED" in result.blocked_reasons


def test_phase14e41_network_error_stale_carryover_blocks(tmp_path, monkeypatch):
    operations_root = tmp_path / ".runtime" / "operations"
    _write_feature_inputs(operations_root / "feature_artifacts", feature_date="2026-07-07")

    def fake_operations_market_refresh(**kwargs):
        return {
            "status": "BLOCK",
            "blocked_reasons": ["API_NETWORK_ERROR", "api_fetch_failed:JQuantsClientError", "DATA_FRESHNESS_BLOCKED"],
            "jquants_api_fetch_executed": True,
            "canonical_normalized_updated": True,
            "feature_refresh_executed": True,
            "feature_refresh_status": "FEATURES_READY",
            "latest_available_market_date": "2026-07-07",
            "data_quality_status": "BLOCK",
            "feature_freshness_status": "MARKET_DATA_NOT_YET_AVAILABLE",
        }

    monkeypatch.setattr(market_refresh_pipeline, "_run_operations_market_refresh", fake_operations_market_refresh)

    result = run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-09",
        operations_root=operations_root,
        allow_api_fetch=True,
    )

    assert result.status == "BLOCKED"
    assert result.reason == "market_refresh_blocked"
    assert result.carryover_used is True
    assert result.freshness_lag_business_days == 2
    assert "API_NETWORK_ERROR" in result.blocked_reasons
    assert "DATA_FRESHNESS_BLOCKED" in result.blocked_reasons


def _write_feature_inputs(root: Path, *, feature_date: str) -> None:
    feature_dir = root / feature_date
    feature_dir.mkdir(parents=True, exist_ok=True)
    for name in ARTIFACTS:
        pd.DataFrame(
            [
                {
                    "target_date": feature_date,
                    "as_of_date": feature_date,
                    "code": "72030",
                    "latest_close": 1000.0,
                }
            ]
        ).to_parquet(feature_dir / name, index=False)
