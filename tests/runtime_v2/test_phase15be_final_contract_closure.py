from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.paper_trading.feature_refresh import run_feature_refresh
from ai_fund_lab_v2.runtime_v2.broker_readonly.refresh import run_broker_readonly_refresh
from ai_fund_lab_v2.runtime_v2.safety.producer import produce_runtime_safety_decision
from ai_fund_lab_v2.runtime_v2.safety_decision import load_runtime_safety_decision, safety_allows_action


BUSINESS_DATE = "2026-07-10"


def test_phase15be_feature_refresh_generates_formal_candidate_opportunity_and_pm_current_rows(tmp_path):
    runtime_root = tmp_path / ".runtime"
    operations_root = runtime_root / "operations"
    quotes_path = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed_path = operations_root / "jquants" / "listed_issues" / "data.parquet"
    _write_quotes(quotes_path, codes=("45910", "68970"))
    _write_listed(listed_path, codes=("45910", "68970"))
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "business_date": BUSINESS_DATE,
            "position_state_as_of": "2026-07-09",
            "positions": [
                {"symbol": "4591", "quantity": 100, "average_price": 101},
                {"symbol": "6897", "quantity": 200, "average_price": 102},
            ],
        },
    )

    result = run_feature_refresh(
        target_data_until=BUSINESS_DATE,
        dry_run=False,
        execute=True,
        daily_quotes_path=quotes_path,
        listed_info_path=listed_path,
        feature_output_root=operations_root / "feature_artifacts",
        manifest_root=operations_root / "feature_refresh_detail",
        markdown_report_path=operations_root / "feature_refresh" / BUSINESS_DATE / "feature_refresh.md",
        json_report_path=operations_root / "feature_refresh" / BUSINESS_DATE / "feature_refresh.json",
        runtime_root=runtime_root,
        created_at="2026-07-10T09:00:00+00:00",
    )
    feature_dir = operations_root / "feature_artifacts" / BUSINESS_DATE
    candidate = pd.read_parquet(feature_dir / "candidate_features.parquet")
    opportunity = pd.read_parquet(feature_dir / "opportunity_feature_input.parquet")
    pm = pd.read_parquet(feature_dir / "position_feature_input.parquet")

    assert result.status == "FEATURES_READY"
    assert candidate["feature_set_name"].unique().tolist() == ["runtime_v2_formal_candidate_feature_producer_v1"]
    assert "candidate_feature_builder_mock" not in set(candidate["feature_set_name"])
    for column in (
        "missing_flags_insufficient_history",
        "missing_flags_price",
        "missing_flags_volume",
        "price_momentum_return_60d",
        "trend_ma_20_60_ratio",
        "trend_ma_5_20_ratio",
        "volume_momentum_ratio_1d_20d",
    ):
        assert column in candidate.columns
        assert column in opportunity.columns
    assert not any(str(column).startswith("feature__") for column in opportunity.columns)
    assert set(pm["broker_issue_code"]) == {"4591", "6897"}
    assert set(pm["code"]) == {"45910", "68970"}


def test_phase15be_safety_high_risk_review_keeps_review_but_allows_sell_hold_review(tmp_path):
    runtime_root = tmp_path / ".runtime"
    source = tmp_path / "reports" / "safety" / "phase11" / f"{BUSINESS_DATE}_safety_report.json"
    _write_json(
        source,
        {
            "schema_version": "phase11_safety_report_v2",
            "business_date": BUSINESS_DATE,
            "generated_at": "2026-07-10T08:00:00+00:00",
            "expires_at": "2099-01-01T00:00:00+00:00",
            "environment": "demo",
            "overall_decision": "REVIEW_REQUIRED",
            "next_recommended_safety_state": "BUY_REVIEW_REQUIRED",
            "transition_reason": "HIGH_RISK_REVIEW",
            "blocked_actions": ["auto_sell", "broker_order_api", "demo_order_submit", "new_buy_without_human_review"],
            "review_required_items": [{"reason_code": "HIGH_RISK_REVIEW", "message": "4591 drawdown -26.73%"}],
        },
    )

    result = produce_runtime_safety_decision(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        source_artifact_path=source,
        now=datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc),
    )
    decision = load_runtime_safety_decision(runtime_root=runtime_root, business_date=BUSINESS_DATE, mode="demo")

    assert result.status == "REVIEW_REQUIRED"
    assert decision.decision == "REVIEW_REQUIRED"
    assert decision.action_permissions["buy_planning"] == "BLOCKED"
    assert decision.action_permissions["sell_hold_inference"] == "ALLOWED_FOR_REVIEW"
    assert decision.action_permissions["sell_planning"] == "ALLOWED_FOR_REVIEW"
    assert decision.action_permissions["auto_sell"] == "BLOCKED"
    assert decision.action_permissions["broker_write"] == "BLOCKED"
    assert safety_allows_action(decision, action="planning", side="SELL")[0] is True
    assert safety_allows_action(decision, action="planning", side="BUY")[0] is False


def test_phase15be_broker_mock_source_and_account_mismatch_are_review_required(tmp_path):
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {"positions": [{"symbol": "4591", "quantity": 100}]},
    )

    result = run_broker_readonly_refresh(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=datetime(2026, 7, 10, 9, 10, tzinfo=timezone.utc),
        snapshot_provider=_mock_snapshot_provider,
    )

    assert result.status == "REVIEW_REQUIRED"
    assert result.authenticity_status == "REVIEW_REQUIRED"
    assert result.data_origin == "MOCK"
    assert result.account_alignment_status == "RUNTIME_SCOPE_NOT_BROKER_RECONCILED"
    assert result.broker_write_executed is False
    assert result.current_position_apply_executed is False


def _write_quotes(path: Path, *, codes: tuple[str, ...]) -> None:
    rows = []
    start = datetime(2026, 4, 10)
    current = start
    while len({row["target_date"] for row in rows if row["code"] == codes[0]}) < 65:
        if current.weekday() < 5:
            day_index = len({row["target_date"] for row in rows if row["code"] == codes[0]})
            target_date = current.date().isoformat()
            for index, code in enumerate(codes):
                rows.append(
                    {
                        "target_date": target_date,
                        "Date": target_date,
                        "code": code,
                        "Code": code,
                        "Close": float(100 + day_index + index),
                        "Volume": float(10_000 + day_index * 10 + index),
                    }
                )
        current += timedelta(days=1)
    for row in rows:
        if row["target_date"] == rows[-1]["target_date"]:
            row["target_date"] = BUSINESS_DATE
            row["Date"] = BUSINESS_DATE
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path, *, codes: tuple[str, ...]) -> None:
    rows = [
        {
            "target_date": BUSINESS_DATE,
            "Code": code,
            "CoName": f"Name {code}",
            "ProdCat": "011",
            "MktNm": "プライム",
        }
        for code in codes
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _mock_snapshot_provider(**kwargs):
    snapshot_path = Path(kwargs["snapshot_path"])
    report_path = Path(kwargs["report_path"])
    _write_json(
        snapshot_path,
        {
            "schema_version": "tachibana_broker_snapshot_v1",
            "broker": "tachibana",
            "environment": "demo",
            "session_status": "PASS",
            "generated_at": "2026-07-10T09:05:00+00:00",
            "source": "runtime_v2_broker_readonly_refresh",
            "account_summary": {"source": "mock", "cash_available": "1000000"},
            "buying_power": {"source": "mock", "buying_power": "1000000"},
            "positions": [{"source": "mock", "issue_code": "6501", "quantity": "100"}],
            "orders": [],
            "executions": [],
            "redaction_status": {"auth_identifier_saved": False, "private_secret_saved": False},
        },
    )
    _write_json(report_path, {"status": "PASS"})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
