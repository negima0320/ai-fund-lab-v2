import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main


class CandidateFixtureModel:
    def predict_proba(self, matrix):
        values = np.asarray(matrix, dtype=float)[:, 0]
        scores = np.clip(values, 0.0, 1.0)
        return np.column_stack([1.0 - scores, scores])


class OpportunityFixtureModel:
    def predict(self, matrix):
        return np.asarray(matrix, dtype=float)[:, 0]


def test_phase14e15_morning_job_generates_approved_pending_from_feature_inputs(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-08",
            "--feature-date",
            "2026-07-07",
            "--feature-root",
            str(feature_root),
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            *_buy_ai_args(tmp_path),
        ]
    )

    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    manifests = sorted((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-08").glob("*.json"))
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    morning_stage = next(stage for stage in manifest["stages"] if stage["name"] == "morning_ai_planning_pending_pipeline")

    assert exit_code == 0
    assert pending["state"] == "APPROVED"
    assert pending["target_session_date"] == "2026-07-08"
    assert pending["intended_submit_date"] == "2026-07-08"
    assert pending["approval"]["approval_status"] == "APPROVED"
    assert pending["items"]
    assert all(item["symbol"] != "9432" for item in pending["items"])
    assert all(item["quantity"] > 0 for item in pending["items"])
    assert all(item["estimated_price"] != 1000.0 for item in pending["items"])
    assert all(item["price_source"] == "jquants_raw_normalized_daily_quotes_close" for item in pending["items"])
    assert all(item["price_as_of"] == "2026-07-07" for item in pending["items"])
    assert all(item["price_required"] is True for item in pending["items"])
    assert sum(item["estimated_amount"] for item in pending["items"]) <= 1_000_000
    assert morning_stage["status"] == "PASS"
    assert morning_stage["details"]["evaluation_capital"] == 1_000_000
    assert morning_stage["details"]["demo_filtered_9000_count"] >= 1
    assert morning_stage["details"]["price_source_status"] == "PASS"
    assert morning_stage["details"]["selected_price_source"] == "jquants_raw_normalized_daily_quotes_close"
    assert "7203" in morning_stage["details"]["selected_symbols"]


def test_phase14e15_morning_job_generates_new_pending_plan_on_same_day_retry(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")
    feature_root = _write_feature_inputs(tmp_path / ".runtime" / "operations" / "feature_artifacts")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")

    args = [
        "--mode",
        "demo",
        "--job",
        "morning",
        "--business-date",
        "2026-07-08",
        "--feature-date",
        "2026-07-07",
        "--feature-root",
        str(feature_root),
        "--submit-enabled",
        "false",
        "--notification-mode",
        "payload-only",
        "--runtime-root",
        str(runtime_root),
        "--reports-root",
        str(tmp_path / "reports" / "runtime_v2"),
        "--public-reports-root",
        str(tmp_path / "reports" / "public" / "runtime_v2"),
        "--manifest-root",
        str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
        "--log-root",
        str(tmp_path / ".runtime" / "runtime_state" / "logs"),
        "--capital-deployment-policy",
        str(policy_path),
        *_buy_ai_args(tmp_path),
    ]

    assert main(args) == 0
    first = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    assert main(args) == 0
    second = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))

    assert first["pending_plan_id"] != second["pending_plan_id"]
    assert {item["symbol"] for item in first["items"]} == {item["symbol"] for item in second["items"]}
    assert {item["pending_item_id"] for item in first["items"]}.isdisjoint(
        {item["pending_item_id"] for item in second["items"]}
    )


def test_phase14e15_morning_job_records_no_signal_when_all_demo_candidates_are_9000(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        candidate_codes=("9432", "9501"),
    )
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-08",
            "--feature-date",
            "2026-07-07",
            "--feature-root",
            str(feature_root),
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            *_buy_ai_args(tmp_path),
        ]
    )

    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-08").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    morning_stage = next(stage for stage in manifest["stages"] if stage["name"] == "morning_ai_planning_pending_pipeline")

    assert exit_code == 0
    assert pending["state"] == "PENDING_APPROVAL"
    assert pending["items"] == []
    assert morning_stage["status"] == "NO_SIGNAL"
    assert morning_stage["details"]["reason"] == "NO_SIGNAL:demo_capability_filtered_all_9000_series"
    assert manifest["prohibited_actions"]["demo_submit_executed"] is False


def test_phase14e28_morning_job_blocks_when_reliable_price_source_is_missing(tmp_path):
    runtime_root = _write_fixed_current(tmp_path / ".runtime")
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        write_price_source=False,
    )
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-08",
            "--feature-date",
            "2026-07-07",
            "--feature-root",
            str(feature_root),
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            *_buy_ai_args(tmp_path),
        ]
    )

    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-08").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    morning_stage = next(stage for stage in manifest["stages"] if stage["name"] == "morning_ai_planning_pending_pipeline")
    order_plan = json.loads((runtime_root / "runtime_state" / "morning_pipeline" / "2026-07-08" / "order_plan.json").read_text(encoding="utf-8"))

    assert exit_code == 20
    assert pending["state"] == "REVIEW_REQUIRED"
    assert pending["items"] == []
    assert morning_stage["status"] == "REVIEW_REQUIRED"
    assert morning_stage["details"]["reason"] == "reliable_price_source_missing"
    assert morning_stage["details"]["price_source_status"] == "MISSING"
    assert order_plan["price_source_contract"]["fallback_allowed"] is False
    assert order_plan["price_source_contract"]["required_for_buy"] is True


def test_phase14e29_next_planning_uses_current_cash_and_excludes_existing_positions(tmp_path):
    runtime_root = _write_runtime_owned_current_with_positions(tmp_path / ".runtime")
    feature_root = _write_feature_inputs(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        candidate_codes=("72030", "65010", "67580", "99840"),
    )
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-09",
            "--feature-date",
            "2026-07-07",
            "--feature-root",
            str(feature_root),
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            *_buy_ai_args(tmp_path),
        ]
    )

    pending = json.loads((runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        next((tmp_path / ".runtime" / "runtime_state" / "run_manifest" / "2026-07-09").glob("*.json")).read_text(
            encoding="utf-8"
        )
    )
    morning_stage = next(stage for stage in manifest["stages"] if stage["name"] == "morning_ai_planning_pending_pipeline")
    public_report = (tmp_path / "reports" / "public" / "runtime_v2" / "latest.md").read_text(encoding="utf-8")

    assert exit_code == 0
    assert pending["state"] == "APPROVED"
    assert {item["symbol"] for item in pending["items"]}.isdisjoint({"72030"})
    assert sum(item["estimated_amount"] for item in pending["items"]) <= 700_000
    assert sum(item["estimated_amount"] for item in pending["items"]) < 1_000_000
    assert all(item["price_source"] == "jquants_raw_normalized_daily_quotes_close" for item in pending["items"])
    assert all(item["price_required"] is True for item in pending["items"])
    assert morning_stage["status"] == "PASS"
    assert morning_stage["details"]["evaluation_capital"] == 1_000_000
    assert morning_stage["details"]["available_cash"] == 700_000
    assert morning_stage["details"]["planning_budget"] == 550_000
    assert morning_stage["details"]["capital_deployment_policy_used_by_morning"] is True
    assert morning_stage["details"]["morning_policy_source"] == str(policy_path)
    assert morning_stage["details"]["morning_hidden_cap_removed"] is True
    assert morning_stage["details"]["current_exposure"] == 300_000
    assert morning_stage["details"]["current_position_symbols"] == ["7203"]
    assert morning_stage["details"]["existing_position_excluded_count"] == 1
    assert "700,000" in public_report
    assert "7203" in public_report


def _write_fixed_current(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e15",
            "environment": "demo",
            "source": "phase14e8_demo_operation_initial_state",
            "as_of": "2026-07-08",
            "positions": [],
            "cash": 1_000_000.0,
            "buying_power": 1_000_000.0,
            "market_value": 0,
            "total_equity": 1_000_000.0,
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "generated_from": ["fixture"],
            "created_at": "2026-07-08",
            "updated_at": "2026-07-08",
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-e15-initial",
            "state": "PENDING_APPROVAL",
            "environment": "demo",
            "created_at": "2026-07-08T00:00:00+09:00",
            "updated_at": "2026-07-08T00:00:00+09:00",
            "items": [],
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase14e15-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": "2026-07-08T00:00:00+09:00",
        },
    )
    for name in ("orders", "executions", "positions", "cash", "events"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_safety_decision(root)
    return root


def _write_runtime_owned_current_with_positions(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-e29",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2026-07-09",
            "positions": [
                {
                    "symbol": "7203",
                    "quantity": 100,
                    "average_price": 3000.0,
                    "market_value": 300_000.0,
                    "source": "runtime_owned_projection_fixture",
                    "as_of": "2026-07-09",
                }
            ],
            "cash": 700_000.0,
            "buying_power": 700_000.0,
            "market_value": 300_000.0,
            "total_equity": 1_000_000.0,
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": False,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "generated_from": ["runtime_owned_projection_fixture"],
            "created_at": "2026-07-09",
            "updated_at": "2026-07-09",
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-e29-initial",
            "state": "PENDING_APPROVAL",
            "environment": "demo",
            "created_at": "2026-07-09T00:00:00+09:00",
            "updated_at": "2026-07-09T00:00:00+09:00",
            "items": [],
        },
    )
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "1",
            "runtime_id": "runtime-v2-demo",
            "run_id": "phase14e29-test",
            "state": "CURRENT_STATE_LOADED",
            "environment": "demo",
            "updated_at": "2026-07-09T00:00:00+09:00",
        },
    )
    for name in ("orders", "executions", "positions", "cash", "events"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    _write_safety_decision(root)
    return root


def _write_feature_inputs(root: Path, candidate_codes=("9432", "7203", "6501"), *, write_price_source: bool = True) -> Path:
    feature_dir = root / "2026-07-07"
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, code in enumerate(candidate_codes):
        rows.append(
            {
                "target_date": "2026-07-07",
                "as_of_date": "2026-07-07",
                "code": code,
                "universe_eligible": True,
                "price_momentum_return_20d": 0.90 - index * 0.10,
                "price_momentum_return_5d": 0.50 - index * 0.05,
                "trend_close_over_ma_20d": 0.20,
                "volatility_return_std_20d": 0.02,
                "volume_momentum_ratio_1d_20d": 1.2,
                "liquidity_avg_volume_20d": 1_000_000 - index,
                "data_until": "2026-07-07",
            }
        )
    candidate = pd.DataFrame(rows)
    candidate.to_parquet(feature_dir / "candidate_features.parquet", index=False)
    candidate.to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(
        columns=[
            "target_date",
            "entry_date",
            "code",
            "holding_days",
            "current_price",
            "unrealized_return",
            "feature_version",
            "data_until",
            "created_at",
            "no_position_reason",
        ]
    ).to_parquet(feature_dir / "position_feature_input.parquet", index=False)
    pd.DataFrame(
        [
            {
                "target_date": "2026-07-07",
                "code": "__POLICY_INPUT__",
                "policy_input_type": "phase14e15_fixture_refs",
                "data_until": "2026-07-07",
            }
        ]
    ).to_parquet(feature_dir / "capital_policy_input.parquet", index=False)
    if write_price_source:
        price_dir = root.parent / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
        price_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {"Code": str(code), "Date": "2026-07-07", "Close": _fixture_price(code), "PriceSource": "fixture_close"}
                for code in candidate_codes
            ]
        ).to_parquet(price_dir / "data.parquet", index=False)
    return root


def _fixture_price(code: str) -> float:
    return {
        "7203": 500.0,
        "72030": 3000.0,
        "6501": 2500.0,
        "65010": 1000.0,
        "67580": 1200.0,
        "99840": 1500.0,
        "9432": 150.0,
        "9501": 800.0,
    }.get(str(code), 750.0)


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "target_investment_ratio": 0.85,
            "cash_buffer": 0.05,
            "max_exposure": 850_000,
            "max_position_weight": 0.2,
            "max_positions": 5,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "derived_from_capital_allocation_and_constraints",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {
                "buy_amount": None,
                "sell_liquidation_amount": None,
            },
        },
    )
    return path


def _buy_ai_args(tmp_path: Path) -> list[str]:
    return [
        "--candidate-model-path",
        str(_write_candidate_model(tmp_path / "candidate_model.pkl")),
        "--opportunity-model-path",
        str(_write_opportunity_model(tmp_path / "opportunity_model.pkl")),
    ]


def _write_candidate_model(path: Path) -> Path:
    _write_pickle(
        path,
        {
            "model": CandidateFixtureModel(),
            "feature_columns": ["feature__price_momentum_return_20d"],
            "model_version": "candidate_model_phase15ag_fixture",
        },
    )
    return path


def _write_opportunity_model(path: Path) -> Path:
    _write_pickle(
        path,
        {
            "model": OpportunityFixtureModel(),
            "feature_columns": ["feature__candidate_score"],
            "preprocessing": {"medians": {"feature__candidate_score": 0.0}},
            "model_version": "opportunity_model_phase15ag_fixture",
        },
    )
    return path


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_pickle(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(payload, handle)


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase14e15-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": "2026-07-09",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase14e15 fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-09T00:00:00+09:00",
            "expires_at": "2026-07-10T00:00:00+09:00",
        },
    )
    return path


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
