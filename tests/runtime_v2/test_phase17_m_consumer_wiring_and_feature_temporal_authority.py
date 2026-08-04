from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.market_refresh import pipeline
from ai_fund_lab_v2.runtime_v2.market_refresh.feature_date_contract import FeatureDateContract


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "runtime_test.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("runtime_test_script_phase17_m", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_market_authorities(root: Path) -> None:
    operations = root / "operations"
    normalized = operations / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    raw = operations / "jquants" / "raw" / "jquants" / "equities_bars_daily"
    calendar = operations / "jquants" / "raw" / "jquants" / "trading_calendar"
    listed = operations / "jquants" / "raw" / "jquants" / "listed_issues"
    for path in (normalized, raw, calendar, listed):
        path.mkdir(parents=True, exist_ok=True)
    quotes = pd.DataFrame(
        [
            {"target_date": "2026-07-06", "code": "7203", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100},
            {"target_date": "2026-07-10", "code": "7203", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100},
        ]
    )
    quotes.to_parquet(normalized / "data.parquet", index=False)
    quotes.to_parquet(raw / "data.parquet", index=False)
    pd.DataFrame([{"Date": "2026-07-06"}, {"Date": "2026-07-10"}]).to_parquet(calendar / "data.parquet", index=False)
    pd.DataFrame([{"Date": "2026-07-06", "Code": "7203"}, {"Date": "2026-07-10", "Code": "7203"}]).to_parquet(listed / "data.parquet", index=False)


def contract_for(selected: str, status: str = "PASS") -> FeatureDateContract:
    root = Path(".runtime/operations/feature_artifacts") / selected
    return FeatureDateContract(
        status=status,
        reason="fixture",
        requested_feature_date="2026-07-06",
        selected_feature_date=selected,
        latest_available_market_date=selected,
        carryover_used=False,
        carryover_reason="",
        freshness_lag_business_days=0,
        freshness_limit_business_days=1,
        feature_artifact_dir=str(root),
        generated_feature_artifacts={
            "candidate_features.parquet": str(root / "candidate_features.parquet"),
            "opportunity_feature_input.parquet": str(root / "opportunity_feature_input.parquet"),
            "position_feature_input.parquet": str(root / "position_feature_input.parquet"),
            "capital_policy_input.parquet": str(root / "capital_policy_input.parquet"),
        },
        missing_feature_artifacts=(),
        requested_feature_artifact_dir=str(root),
        requested_missing_feature_artifacts=(),
        price_source_alignment="selected_feature_date",
        consumer_ready=True,
        candidate_schema_status="READY",
        opportunity_schema_status="READY",
        pm_schema_status="READY",
    )


class DummyMarketEvidence:
    status = "READY"
    reason = "market_evidence_ready"
    latest_expected_trading_date = "2026-07-06"
    latest_available_market_date = "2026-07-06"
    artifact_path = ""
    latest_pointer_path = ""
    history_artifact_path = ""
    market_date = "2026-07-06"
    market_freshness_status = "READY"
    quote_status = "READY"
    quote_count = 1
    missing_quote_count = 0
    market_summary_status = "READY"
    publication_status = "READY"
    provider_status = "READY"
def test_phase17_m_future_feature_artifact_is_blocked(tmp_path: Path, monkeypatch) -> None:
    write_market_authorities(tmp_path / ".runtime")
    monkeypatch.setattr(
        pipeline,
        "_run_operations_market_refresh",
        lambda **kwargs: {
            "status": "PASS",
            "blocked_reasons": [],
            "latest_available_market_date": "2026-07-06",
            "data_quality_status": "PASS",
            "feature_refresh_status": "FEATURES_READY",
        },
    )
    monkeypatch.setattr(pipeline, "resolve_feature_date_contract", lambda **kwargs: contract_for("2026-07-10"))
    monkeypatch.setattr(pipeline, "write_feature_date_contract", lambda **kwargs: tmp_path / "contract.json")
    monkeypatch.setattr(pipeline, "produce_market_quote_evidence", lambda **kwargs: DummyMarketEvidence())
    result = pipeline.run_runtime_v2_market_refresh_pipeline(
        business_date="2026-07-06",
        operations_root=tmp_path / ".runtime" / "operations",
        mode="historical",
        runtime_test_context={
            "run_id": "run-b",
            "profile_id": "historical-smoke",
            "evidence_root": str(tmp_path / "reports" / "runtime_tests" / "runs" / "run-b"),
            "job": "market_refresh",
        },
    )
    assert result.status == "BLOCKED"
    assert result.reason == "TEMPORAL_CONTRACT_VIOLATION"
    assert any("artifact_date_after_business_date" in reason for reason in result.blocked_reasons)


def make_runtime_root(tmp_path: Path, *, contract_status: str = "PASS") -> Path:
    root = tmp_path / ".runtime"
    (root / "operations" / "feature_date_contract").mkdir(parents=True)
    selected = {
        "2026-07-06": "2026-07-06",
        "2026-07-07": "2026-07-07",
        "2026-07-08": "2026-07-07",
        "2026-07-09": "2026-07-08",
        "2026-07-10": "2026-07-10",
    }
    for business_date, feature_date in selected.items():
        (root / "operations" / "feature_date_contract" / f"{business_date}.json").write_text(
            json.dumps(
                {
                    "status": contract_status,
                    "reason": "fixture",
                    "requested_feature_date": business_date,
                    "selected_feature_date": feature_date,
                    "latest_available_market_date": feature_date,
                    "generated_feature_artifacts": {},
                }
            ),
            encoding="utf-8",
        )
    return root


def call_main(module, args: list[str], capsys) -> dict:
    exit_code = module.main(args + ["--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    payload["_exit_code"] = exit_code
    return payload


def test_phase17_m_plan_blocks_review_required_contract(tmp_path: Path, capsys) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, contract_status="REVIEW_REQUIRED")
    payload = call_main(runner, ["plan", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1"], capsys)
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE


def test_phase17_m_run_revalidates_plan_before_cli_invocation(tmp_path: Path, monkeypatch, capsys) -> None:
    runner = load_runner()
    root = make_runtime_root(tmp_path, contract_status="REVIEW_REQUIRED")

    def forbidden_run(command: list[str], *, cwd: Path):
        raise AssertionError("runtime cli must not run when plan gate fails")

    monkeypatch.setattr(runner, "run_runtime_cli", forbidden_run)
    payload = call_main(runner, ["run", "--runtime-root", str(root), "--evidence-root", str(tmp_path / "reports"), "--business-days", "1", "--dry-run"], capsys)
    assert payload["status"] == "PRECONDITION_FAILURE"
    assert payload["_exit_code"] == runner.EXIT_PRECONDITION_FAILURE
