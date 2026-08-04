import json
import pickle
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.approval.models import ApprovalArtifact, ApprovalStatus
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import (
    CANDIDATE_REQUIRED_COLUMNS,
    OPPORTUNITY_REQUIRED_COLUMNS,
    PM_REQUIRED_COLUMNS,
)
from ai_fund_lab_v2.runtime_v2.broker_adapter.capability import get_broker_capability
from ai_fund_lab_v2.runtime_v2.pending.reader import pending_order_plan_from_payload
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import run_morning_ai_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.submit.guards import run_submit_preflight
from tests.runtime_v2.feature_date_contract_helpers import materialize_feature_date_contract
from tests.runtime_v2.test_phase17_k_runtime_test_runner import _write_accepted_generation_authority


class CandidateFixtureModel:
    def predict_proba(self, matrix):
        values = np.asarray(matrix, dtype=float)[:, 0]
        scores = np.clip(values, 0.0, 1.0)
        return np.column_stack([1.0 - scores, scores])


class OpportunityFixtureModel:
    def predict(self, matrix):
        return np.asarray(matrix, dtype=float)[:, 0]
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
    _write_market_evidence(root, business_date="2026-07-08")
    _write_safety_decision(root, business_date="2026-07-08")
    _write_accepted_generation_authority(root, business_date="2026-07-08")
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
    _write_market_evidence(root, business_date="2026-07-09")
    _write_safety_decision(root, business_date="2026-07-09")
    _write_accepted_generation_authority(root, business_date="2026-07-09")
    return root


def _write_feature_inputs(
    root: Path,
    candidate_codes=("9432", "7203", "6501"),
    *,
    position_codes: tuple[str, ...] = (),
    write_price_source: bool = True,
    feature_date: str = "2026-07-07",
    pm_target_date: str = "2026-07-08",
) -> Path:
    feature_dir = root / feature_date
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, code in enumerate(candidate_codes):
        row = {column: _feature_value(column, code=code, index=index) for column in CANDIDATE_REQUIRED_COLUMNS}
        row.update(
            {
                "target_date": feature_date,
                "as_of_date": feature_date,
                "universe_eligible": True,
                "data_until": feature_date,
            }
        )
        rows.append(row)
    candidate = pd.DataFrame(rows)
    candidate.to_parquet(feature_dir / "candidate_features.parquet", index=False)
    opportunity = pd.DataFrame(
        [
            {
                **{column: _feature_value(column, code=str(row["code"]), index=index) for column in OPPORTUNITY_REQUIRED_COLUMNS},
                "target_date": feature_date,
                "as_of_date": feature_date,
                "feature_version": "runtime_v2_opportunity_feature_input_v2_market_sector_fixture",
                "data_until": feature_date,
                "created_at": "2026-07-08T00:00:00Z",
            }
            for index, row in enumerate(rows)
        ]
    )
    opportunity.to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    if position_codes:
        pm_rows = [
            {
                **{column: _feature_value(column, code=code, index=index) for column in PM_REQUIRED_COLUMNS},
                "target_date": pm_target_date,
                "feature_as_of_date": pm_target_date,
                "position_state_as_of": pm_target_date,
                "entry_date": pm_target_date,
                "code": code,
                "broker_issue_code": code,
                "holding_days": 2,
                "average_price": 3000.0,
                "current_price": 3000.0,
                "unrealized_return": 0.0,
                "quantity": 100,
                "feature_source_artifact": str(feature_dir / "position_feature_input.parquet"),
                "feature_source_hash": "phase14e15_fixture_hash",
                "required_features": "[]",
                "optional_features": "[]",
                "missing_features": "[]",
                "defaulted_features": "[]",
                "temporal_validation_status": "PASS",
                "feature_version": "runtime_v2_pm_feature_input_fixture",
                "data_until": pm_target_date,
                "created_at": "2026-07-08T00:00:00Z",
                "no_position_reason": "",
            }
            for index, code in enumerate(position_codes)
        ]
    else:
        pm_rows = [{"target_date": pm_target_date, "code": "__NO_POSITION__", "no_position_reason": "current_positions_confirmed_empty"}]
    pd.DataFrame(pm_rows, columns=[*PM_REQUIRED_COLUMNS, "no_position_reason"]).to_parquet(
        feature_dir / "position_feature_input.parquet",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "target_date": feature_date,
                "code": "__POLICY_INPUT__",
                "policy_input_type": "phase14e15_fixture_refs",
                "data_until": feature_date,
            }
        ]
    ).to_parquet(feature_dir / "capital_policy_input.parquet", index=False)
    if write_price_source:
        price_dir = root.parent / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
        price_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {"Code": str(code), "Date": feature_date, "Close": _fixture_price(code), "PriceSource": "fixture_close"}
                for code in candidate_codes
            ]
        ).to_parquet(price_dir / "data.parquet", index=False)
    return root


def _feature_value(column: str, *, code: str, index: int):
    if column == "target_date":
        return "2026-07-07"
    if column == "code":
        return code
    if column.startswith("missing_flags_") or column.endswith("_flag") or column.endswith("_context"):
        return False
    if column == "price_momentum_return_20d":
        return 0.90 - index * 0.10
    if column == "price_momentum_return_5d":
        return 0.50 - index * 0.05
    if column == "price_momentum_return_60d":
        return 1.00 - index * 0.10
    if column == "liquidity_avg_volume_20d":
        return 1_000_000 - index
    if column == "trend_close_over_ma_20d":
        return 0.20
    if column in {"trend_ma_5_20_ratio", "trend_ma_20_60_ratio"}:
        return 1.0
    if column == "volatility_return_std_20d":
        return 0.02
    if column in {"volume_momentum_ratio_1d_20d", "volume_momentum_ratio_5d"}:
        return 1.2
    return 0.1


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


def _write_historical_logical_price_source(
    evidence_root: Path,
    *,
    business_date: str,
    rows: list[dict[str, object]],
) -> Path:
    input_root = evidence_root / "daily" / business_date / "market_refresh" / "inputs" / "historical_asof" / business_date
    price_path = input_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    price_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(price_path, index=False)
    _write_json(
        input_root / "logical_input_manifest.json",
        {
            "schema_version": "historical_logical_input_manifest_v1",
            "status": "PASS",
            "reason": "fixture",
            "business_date": business_date,
            "input_root": str(input_root),
            "logical_paths": {
                "normalized_ohlcv": str(price_path),
            },
        },
    )
    return price_path


def _rewrite_asset_state_date(runtime_root: Path, *, business_date: str, environment: str) -> None:
    state_path = runtime_root / "persistent_ledger" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update(
        {
            "environment": environment,
            "as_of": business_date,
            "business_date": business_date,
            "position_state_as_of": business_date,
            "updated_at": business_date,
        }
    )
    _write_json(state_path, state)
    _write_accepted_generation_authority(runtime_root, business_date=business_date)


def _write_policy(path: Path) -> Path:
    _write_json(
        path,
        {
            "policy_version": "capital_deployment_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
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
    opportunity_model_path = _write_opportunity_model(tmp_path / "opportunity_model.pkl")
    opportunity_metrics_path = _write_opportunity_metrics(
        tmp_path / "opportunity_training_metrics.json",
        opportunity_model_path,
    )
    return [
        "--candidate-model-path",
        str(_write_candidate_model(tmp_path / "candidate_model.pkl")),
        "--opportunity-model-path",
        str(opportunity_model_path),
        "--opportunity-training-metrics-path",
        str(opportunity_metrics_path),
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
            "artifact_set_id": "phase14e15_fixture_set",
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
            "artifact_set_id": "phase14e15_fixture_set",
            "feature_columns": ["feature__candidate_score"],
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


def _write_market_evidence(root: Path, *, business_date: str) -> None:
    _write_json(
        root / "runtime_state" / "market" / business_date / "market_evidence.json",
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "business_date": business_date,
            "as_of": business_date,
            "generated_at": f"{business_date}T00:00:00Z",
            "market_status": "READY",
            "quote_status": "READY",
            "quote_count": 3,
            "market_summary": {"source": "phase14e15_fixture"},
        },
    )


def _write_safety_decision(root: Path, *, business_date: str) -> Path:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": "safety-phase14e15-allow",
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": business_date,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase14e15 fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": f"{business_date}T00:00:00+09:00",
            "expires_at": f"{business_date}T23:59:59+09:00",
        },
    )
    return path


def _write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
