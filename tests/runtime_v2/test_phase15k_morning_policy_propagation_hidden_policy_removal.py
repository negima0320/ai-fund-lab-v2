import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from tests.runtime_v2.feature_date_contract_helpers import materialize_feature_date_contract


class CandidateFixtureModel:
    def predict_proba(self, matrix):
        values = np.asarray(matrix, dtype=float)[:, 0]
        scores = np.clip(values, 0.0, 1.0)
        return np.column_stack([1.0 - scores, scores])


class OpportunityFixtureModel:
    def predict(self, matrix):
        return np.asarray(matrix, dtype=float)[:, 0]


def test_phase15k_morning_uses_policy_max_positions_not_hidden_five(tmp_path):
    runtime_root = _write_current(tmp_path / ".runtime")
    feature_root = _write_features(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        candidate_codes=("7203", "6501", "6758", "6861", "4452", "4502", "7011"),
        price=1000,
    )
    materialize_feature_date_contract(runtime_root, business_date="2026-07-09", selected_feature_date="2026-07-08")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json", max_positions=6)

    assert _run_morning(tmp_path, runtime_root, feature_root, policy_path) == 0

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    manifest = _latest_manifest(tmp_path / ".runtime", "2026-07-09")
    morning_stage = next(stage for stage in manifest["stages"] if stage["name"] == "morning_ai_planning_pending_pipeline")

    assert len(pending["items"]) == 6
    assert morning_stage["details"]["morning_policy_max_positions"] == 6
    assert morning_stage["details"]["morning_order_count_source"] == "capital_deployment_policy.max_positions"
    assert morning_stage["details"]["morning_hidden_cap_removed"] is True


def test_phase15k_morning_per_order_budget_not_capped_at_100k(tmp_path):
    runtime_root = _write_current(tmp_path / ".runtime")
    feature_root = _write_features(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        candidate_codes=("7203", "6501", "6758", "6861"),
        price=1000,
    )
    materialize_feature_date_contract(runtime_root, business_date="2026-07-09", selected_feature_date="2026-07-08")
    policy_path = _write_policy(
        tmp_path / "capital_deployment_policy.json",
        max_positions=4,
        target_investment_ratio=1.0,
        cash_buffer=0.0,
        max_exposure=1_000_000,
        max_position_weight=0.2,
    )

    assert _run_morning(tmp_path, runtime_root, feature_root, policy_path) == 0

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    manifest = _latest_manifest(tmp_path / ".runtime", "2026-07-09")
    morning_stage = next(stage for stage in manifest["stages"] if stage["name"] == "morning_ai_planning_pending_pipeline")

    assert pending["items"]
    assert max(item["estimated_amount"] for item in pending["items"]) == 200_000
    assert all(item["estimated_amount"] > 100_000 for item in pending["items"])
    assert morning_stage["details"]["morning_per_order_budget_source"] == "capital_deployment_policy_derived"


def test_phase15k_pending_and_approval_preserve_policy_context(tmp_path):
    runtime_root = _write_current(tmp_path / ".runtime")
    feature_root = _write_features(
        tmp_path / ".runtime" / "operations" / "feature_artifacts",
        candidate_codes=("7203", "6501"),
        price=1000,
    )
    materialize_feature_date_contract(runtime_root, business_date="2026-07-09", selected_feature_date="2026-07-08")
    policy_path = _write_policy(tmp_path / "capital_deployment_policy.json", max_positions=2)

    assert _run_morning(tmp_path, runtime_root, feature_root, policy_path) == 0

    pending = _load_json(runtime_root / "pending_order_plan" / "pending_order_plan.json")
    approval = _load_json(runtime_root / "runtime_state" / "morning_pipeline" / "2026-07-09" / "approval_artifact.json")

    item = pending["items"][0]
    assert pending["policy_version"] == "capital_deployment_v1"
    assert pending["policy_source"] == str(policy_path)
    assert pending["pending_policy_hash"].startswith("sha256:")
    assert item["policy_version"] == "capital_deployment_v1"
    assert item["policy_source"] == str(policy_path)
    assert item["capital_allocation_amount"] == item["estimated_amount"]
    assert item["sizing_policy_reason"]
    assert approval["policy_version"] == "capital_deployment_v1"
    assert approval["policy_source"] == str(policy_path)
    assert approval["pending_policy_hash"] == pending["pending_policy_hash"]


def test_phase15k_morning_mainline_has_no_hidden_policy_literals():
    source = Path("src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py").read_text(encoding="utf-8")

    assert "max_orders: int = 5" not in source
    assert "per_order_budget = min(float(planning_budget) / max(max_orders, 1), 100_000.0)" not in source
    assert "100_000.0" not in source


def _run_morning(tmp_path: Path, runtime_root: Path, feature_root: Path, policy_path: Path) -> int:
    return main(
        [
            "--mode",
            "demo",
            "--job",
            "morning",
            "--business-date",
            "2026-07-09",
            "--feature-date",
            "2026-07-08",
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
            "--candidate-model-path",
            str(_write_candidate_model(tmp_path / "candidate_model.pkl")),
            "--opportunity-model-path",
            str(opportunity_model_path := _write_opportunity_model(tmp_path / "opportunity_model.pkl")),
            "--opportunity-training-metrics-path",
            str(_write_opportunity_metrics(tmp_path / "opportunity_training_metrics.json", opportunity_model_path)),
        ]
    )


def _write_current(root: Path) -> Path:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "asset-phase15k",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": "2026-07-09",
            "updated_at": "2026-07-09T00:00:00+09:00",
            "positions": [],
            "cash": 1_000_000.0,
            "buying_power": 1_000_000.0,
            "market_value": 0,
            "total_equity": 1_000_000.0,
            "review_required": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
        },
    )
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "pending-phase15k-initial",
            "state": "PENDING_APPROVAL",
            "environment": "demo",
            "created_at": "2026-07-09T00:00:00+09:00",
            "updated_at": "2026-07-09T00:00:00+09:00",
            "items": [],
        },
    )
    _write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED", "environment": "demo"})
    _write_safety_decision(root)
    _write_market_evidence(root)
    for name in ("orders", "executions", "positions", "cash", "events"):
        _write_jsonl(root / "persistent_ledger" / f"{name}.jsonl", [])
    return root


def _write_market_evidence(root: Path) -> None:
    _write_json(
        root / "runtime_state" / "market" / "2026-07-09" / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": "2026-07-09",
            "as_of": "2026-07-09",
            "generated_at": "2026-07-09T00:00:00Z",
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 1,
            "market_summary": {"source": "phase15k_fixture"},
        },
    )


def _write_features(root: Path, *, candidate_codes: tuple[str, ...], price: float) -> Path:
    feature_dir = root / "2026-07-08"
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "target_date": "2026-07-08",
            "as_of_date": "2026-07-08",
            "code": code,
            "universe_eligible": True,
            "price_momentum_return_20d": 1.0 - index * 0.01,
            "price_momentum_return_5d": 0.5 - index * 0.01,
            "price_momentum_return_60d": 1.1 - index * 0.01,
            "trend_close_over_ma_20d": 0.20,
            "trend_ma_20_60_ratio": 1.01,
            "trend_ma_5_20_ratio": 1.02,
            "volatility_return_std_20d": 0.02,
            "volume_momentum_ratio_1d_20d": 1.2,
            "volume_momentum_ratio_5d": 1.1,
            "liquidity_avg_volume_20d": 1_000_000 - index,
            "market_breadth_20d": 0.5,
            "market_breadth_5d": 0.5,
            "market_downtrend_context": 0.0,
            "market_downtrend_flag": False,
            "market_ma_5_20_ratio": 1.0,
            "market_return_20d": 0.02,
            "market_return_5d": 0.01,
            "market_risk_flag": False,
            "market_volatility_20d": 0.02,
            "missing_flags_insufficient_history": False,
            "missing_flags_price": False,
            "missing_flags_volume": False,
            "data_until": "2026-07-08",
            "sector_breadth_20d": 0.5,
            "sector_momentum_flag": True,
            "sector_rank_20d": index + 1,
            "sector_return_20d": 0.03,
            "sector_return_5d": 0.01,
            "sector_weak_flag": False,
            "stock_vs_sector_return_20d": 0.01,
        }
        for index, code in enumerate(candidate_codes)
    ]
    candidate = pd.DataFrame(rows)
    candidate.to_parquet(feature_dir / "candidate_features.parquet", index=False)
    candidate.to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(columns=["target_date", "code", "data_until", "no_position_reason"]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    pd.DataFrame([{"target_date": "2026-07-08", "code": "__POLICY_INPUT__", "data_until": "2026-07-08"}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    price_dir = root.parent / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    price_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"Code": code, "Date": "2026-07-08", "Close": price, "PriceSource": "fixture_close"} for code in candidate_codes]
    ).to_parquet(price_dir / "data.parquet", index=False)
    return root


def _write_policy(
    path: Path,
    *,
    max_positions: int,
    target_investment_ratio: float = 0.85,
    cash_buffer: float = 0.05,
    max_exposure: float = 850_000,
    max_position_weight: float = 0.2,
) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "target_investment_ratio": target_investment_ratio,
            "cash_buffer": cash_buffer,
            "max_exposure": max_exposure,
            "max_position_weight": max_position_weight,
            "max_positions": max_positions,
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


def _latest_manifest(runtime_root: Path, business_date: str):
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _write_opportunity_metrics(path: Path, model_path: Path) -> Path:
    _write_json(
        path,
        {
            "status": "PASS",
            "readiness_status": "READY",
            "model_artifact_path": str(model_path),
            "feature_columns": ["feature__candidate_score"],
        },
    )
    return path


def _write_pickle(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(payload, handle)


def _write_safety_decision(root: Path) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase15k-fixture",
            "safety_policy_version": "safety_policy_v1",
            "safety_source": str(path),
            "business_date": "2026-07-09",
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15k fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": "2026-07-09T08:00:00+09:00",
            "expires_at": "2026-07-09T15:00:00+09:00",
        },
    )
    return path


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
