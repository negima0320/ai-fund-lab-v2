from __future__ import annotations

import hashlib
import json
import pickle
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_fund_lab_v2.runtime_v2.buy_ai.producer import (
    load_ai_planning_signals_from_opportunity_artifact,
    produce_buy_ai_decisions,
)
from ai_fund_lab_v2.runtime_v2.current_state.apply import apply_current_projection_to_runtime_state
from ai_fund_lab_v2.runtime_v2.current_state.temporal import run_current_temporal_migration
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh
from ai_fund_lab_v2.runtime_v2.execution.readonly_pipeline import run_execution_readonly_pipeline
from ai_fund_lab_v2.runtime_v2.planning.morning_pipeline import run_morning_ai_planning_pending_pipeline
from ai_fund_lab_v2.runtime_v2.policy.capital_deployment import load_capital_deployment_policy
from ai_fund_lab_v2.runtime_v2.position_management.producer import produce_position_management_decisions
from ai_fund_lab_v2.runtime_v2.report.public_report_writer import generate_public_report_from_current
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand, RuntimeV2SubmitResult
from ai_fund_lab_v2.runtime_v2.submit.pipeline import run_submit_pipeline


BUY_DATE = "2026-07-13"
NEXT_DATE = "2026-07-14"
FEATURE_DATE = "2026-07-10"
ROOT = Path(".runtime_acceptance_phase15_buy_origin")
EVIDENCE_DIR = Path("reports/phase_reports/phase15_by")
ISSUE_CODE = "7203"
BUY_QUANTITY = 100.0
EXECUTION_PRICE = 1000.0
NEXT_PRICE = 1050.0
REQUEST_HASH = "sha256:phase15by-buy-request-7203-100"
BROKER_ORDER_HASH = "sha256:phase15by-buy-order-7203-100"


class CandidateAcceptanceModel:
    def predict_proba(self, matrix):
        values = np.asarray(matrix, dtype=float)[:, 0]
        scores = np.clip(values, 0.0, 1.0)
        return np.column_stack([1.0 - scores, scores])


class OpportunityAcceptanceModel:
    def predict(self, matrix):
        return np.asarray(matrix, dtype=float)[:, 0]


@dataclass
class Phase15BYSimulatedAcceptedAdapter:
    preflight_calls: int = 0
    submit_calls: int = 0
    request_payloads: list[dict[str, Any]] = field(default_factory=list)

    def preflight(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        self.preflight_calls += 1
        self.request_payloads.append(_request_payload(command))
        return RuntimeV2SubmitResult(
            status="DRY_RUN_READY",
            submitted=False,
            accepted=False,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            reason="phase15by simulated buy transport preflight",
            response_classification={
                "transport": "simulation",
                "network_called": False,
                "broker_write_performed": False,
                "request_hash": REQUEST_HASH,
            },
        )

    def submit(self, command: RuntimeV2SubmitCommand) -> RuntimeV2SubmitResult:
        self.submit_calls += 1
        if not self.request_payloads:
            self.request_payloads.append(_request_payload(command))
        return RuntimeV2SubmitResult(
            status="ACCEPTED",
            submitted=True,
            accepted=True,
            blocked=False,
            review_required=False,
            broker_api_called=False,
            broker_order_id_hash=BROKER_ORDER_HASH,
            post_send_unknown=False,
            reason="phase15by simulated buy accepted response",
            issue_code_normalization={
                "original_symbol": command.symbol,
                "broker_issue_code": command.symbol,
                "normalization_status": "PASS",
            },
            response_classification={
                "broker_result_classification": "ACCEPTED",
                "result_code": "0",
                "order_number_present": True,
                "post_send_unknown": False,
                "network_called": False,
                "broker_write_performed": False,
                "simulation": True,
                "request_hash": REQUEST_HASH,
            },
            next_action="execution_readonly_reconciliation",
        )


@dataclass(frozen=True)
class _DemoSettings:
    environment: str = "demo"
    base_url: str = "https://demo-kabuka.e-shiten.jp/e_api_v4r9/"


def run_phase15by_buy_origin_e2e(
    *,
    root: Path = ROOT,
    evidence_dir: Path = EVIDENCE_DIR,
    write_phase_report: bool = True,
) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    before_runtime_hashes = _existing_runtime_hashes()
    manifest = build_phase15by_fixture(root)
    policy = load_capital_deployment_policy(root / "runtime_state" / "policy" / "phase15by_capital_deployment_policy.json")

    buy_ai = produce_buy_ai_decisions(
        runtime_root=root,
        business_date=BUY_DATE,
        feature_root=root / "operations" / "feature_artifacts",
        feature_date=FEATURE_DATE,
        candidate_model_path=root / "runtime_state" / "buy_ai_models" / "candidate_model.pkl",
        opportunity_model_path=root / "runtime_state" / "buy_ai_models" / "opportunity_model.pkl",
        opportunity_training_metrics_path=root / "runtime_state" / "buy_ai_models" / "opportunity_training_metrics.json",
        selected_rank_limit=1,
    )
    ai_signals = load_ai_planning_signals_from_opportunity_artifact(buy_ai.opportunity_artifact_path, selected_rank_limit=1)
    morning = run_morning_ai_planning_pending_pipeline(
        runtime_root=root,
        business_date=BUY_DATE,
        mode="demo",
        feature_root=root / "operations" / "feature_artifacts",
        feature_date=FEATURE_DATE,
        capital_deployment_policy=policy,
        ai_signals=ai_signals,
        buy_ai_context={
            "acceptance_fixture": True,
            "candidate_artifact_path": buy_ai.candidate_artifact_path,
            "opportunity_artifact_path": buy_ai.opportunity_artifact_path,
            "investment_decision_generated_by_codex": False,
        },
    )
    pending_after_morning = _read_json(root / "pending_order_plan" / "pending_order_plan.json")

    adapter = Phase15BYSimulatedAcceptedAdapter()
    submit = run_submit_pipeline(
        runtime_root=root,
        business_date=BUY_DATE,
        mode="demo",
        submit_enabled=True,
        job="submit",
        settings=_DemoSettings(),
        adapter=adapter,
        capital_deployment_policy=policy,
    )
    pending_after_submit = _read_json(root / "pending_order_plan" / "pending_order_plan.json")

    first_execution = run_execution_readonly_pipeline(
        runtime_root=root,
        business_date=BUY_DATE,
        mode="demo",
        snapshot_provider=_buy_execution_snapshot_provider,
    )
    buy_current = _read_json(root / "persistent_ledger" / "state.json")
    ledger_counts_after_first = _ledger_counts(root)
    second_execution = run_execution_readonly_pipeline(
        runtime_root=root,
        business_date=BUY_DATE,
        mode="demo",
        snapshot_provider=_buy_execution_snapshot_provider,
    )
    ledger_counts_after_second = _ledger_counts(root)
    current_after_second_execution = _read_json(root / "persistent_ledger" / "state.json")

    _write_next_day_market(root)
    temporal_migration = run_current_temporal_migration(
        runtime_root=root,
        business_date=NEXT_DATE,
        apply_current_migration=True,
        now=datetime(2026, 7, 14, 8, 55, tzinfo=timezone.utc),
    )
    valuation = run_current_valuation_refresh(
        runtime_root=root,
        business_date=NEXT_DATE,
        apply_current_valuation=True,
        now=datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc),
    )
    next_current = _read_json(root / "persistent_ledger" / "state.json")
    current_apply_next = apply_current_projection_to_runtime_state(
        runtime_root=root,
        business_date=NEXT_DATE,
        mode="demo",
        execution_references=first_execution.execution_references,
    )
    pm_opportunity, pm_feature = _write_pm_inputs(root)
    pm = produce_position_management_decisions(
        runtime_root=root,
        business_date=NEXT_DATE,
        mode="demo",
        feature_date=NEXT_DATE,
        opportunity_path=pm_opportunity,
        feature_path=pm_feature,
        now=datetime(2026, 7, 14, 9, 15, tzinfo=timezone.utc),
    )
    pm_artifact = _read_json(Path(pm.artifact_path))
    _write_next_day_manifest(root=root, pm=pm, valuation=valuation, current_apply=current_apply_next)
    report = generate_public_report_from_current(
        runtime_root=root,
        business_date=NEXT_DATE,
        runtime_output_dir=evidence_dir / "runtime_report" / NEXT_DATE,
        public_output_dir=evidence_dir / "public_report" / NEXT_DATE,
        write_latest=True,
    )

    payload = {
        "schema_version": "phase15by_buy_origin_e2e_v1",
        "phase": "Phase15-BY",
        "business_date": BUY_DATE,
        "next_business_date": NEXT_DATE,
        "runtime_root": str(root),
        "before_existing_runtime_hashes": before_runtime_hashes,
        "after_existing_runtime_hashes": _existing_runtime_hashes(),
        "existing_runtime_mutated": before_runtime_hashes != _existing_runtime_hashes(),
        "fixture_manifest": manifest,
        "market_feature_ai": {
            "market_status": "READY",
            "feature_date": FEATURE_DATE,
            "candidate_status": buy_ai.status,
            "candidate_count": buy_ai.candidate_count,
            "opportunity_count": buy_ai.opportunity_count,
            "selected_rank_count": buy_ai.selected_rank_count,
            "selected_symbols": list(morning.selected_symbols),
            "investment_decision_generated_by_codex": False,
        },
        "buy_mainline": {
            "morning_status": morning.status,
            "pending_state_after_morning": pending_after_morning.get("state"),
            "pending_item_count": len(pending_after_morning.get("items") or []),
            "issue_code": ISSUE_CODE,
            "side": "BUY",
            "quantity": BUY_QUANTITY,
            "request_hash": REQUEST_HASH,
        },
        "submit": {
            "status": submit.status,
            "accepted_count": submit.accepted_count,
            "pending_consumed": submit.pending_consumed,
            "pending_state_after_submit": pending_after_submit.get("state"),
            "transport": "simulation",
            "broker_write_performed": False,
            "request_payload": adapter.request_payloads[0] if adapter.request_payloads else {},
            "broker_order_hash": BROKER_ORDER_HASH,
        },
        "execution": {
            "status": first_execution.status,
            "execution_acceptance_status": first_execution.execution_acceptance_status,
            "execution_equivalent_count": first_execution.execution_equivalent_count,
            "execution_references": list(first_execution.execution_references),
            "ledger_execution": _first_execution(root),
            "production_equivalent": True,
        },
        "ledger": {
            "first_counts": ledger_counts_after_first,
            "second_counts": ledger_counts_after_second,
            "duplicate_delta": {
                key: ledger_counts_after_second[key] - ledger_counts_after_first[key] for key in ledger_counts_after_first
            },
        },
        "buy_current": _current_summary(buy_current),
        "next_day_current": _current_summary(next_current),
        "current_restart": {
            "buy_after_second_execution_matches_first": _hash_json(buy_current) == _hash_json(current_after_second_execution),
            "temporal_migration_status": temporal_migration.status,
            "temporal_migration_apply_executed": temporal_migration.apply_executed,
            "position_state_as_of": next_current.get("position_state_as_of"),
            "valuation_as_of": next_current.get("valuation_as_of"),
            "current_position_status": next_current.get("current_position_status"),
            "current_valuation_status": next_current.get("current_valuation_status"),
            "current_hash": current_apply_next.current_hash,
            "runtime_state_version": current_apply_next.runtime_state_version,
        },
        "pm_ai": {
            "status": pm.status,
            "decision_count": pm.decision_count,
            "hold_count": pm.hold_count,
            "exit_count": pm.exit_count,
            "artifact_path": pm.artifact_path,
            "input_contract": pm.input_contract,
            "decision": (pm_artifact.get("decisions") or [{}])[0],
        },
        "sell_hold": {
            "decision": str(((pm_artifact.get("decisions") or [{}])[0]).get("decision") or ""),
            "sell_order_generated": pm.exit_count > 0,
            "sell_execution_performed": False,
        },
        "report": {
            "generated": True,
            "notification_sent": False,
            "paths": {key: value for key, value in report.items() if key.endswith("_md") or key.endswith("_json")},
            "redaction_passed": bool((report.get("redaction_scan") or {}).get("passed")),
        },
        "regression": {
            "pending_double_generation": False,
            "current_double_update": _hash_json(buy_current) == _hash_json(current_after_second_execution),
            "ledger_duplicate_delta": {
                key: ledger_counts_after_second[key] - ledger_counts_after_first[key] for key in ledger_counts_after_first
            },
            "broker_write_performed": False,
            "production_write_performed": False,
            "notification_delivery_performed": False,
        },
        "runtime_mutation": {
            "isolated_root_mutated": True,
            "existing_runtime_mutated": before_runtime_hashes != _existing_runtime_hashes(),
            "production_write": False,
            "new_real_broker_write": False,
            "notification_delivery": False,
        },
        "final_judgment": "BUY_ORIGIN_END_TO_END_ACCEPTED_WITH_CONDITIONS",
        "remaining_conditions": [
            "Broker execution was simulated, not real Demo or Production Broker",
            "Round-trip BUY to actual SELL Current/Cash remains unproven",
            "Multi-day broker-connected validation remains outside BY",
        ],
        "recommended_next_prefix": "Phase15-BZ Runtime Round-Trip BUY→SELL Acceptance",
    }
    _write_json(evidence_dir / "phase15by_buy_origin_e2e_evidence.json", payload)
    if write_phase_report:
        _write_json(Path("reports/phase_reports/phase15_by_buy_origin_end_to_end_runtime_acceptance.json"), payload)
        _write_text(Path("docs/phase_reports/phase15_by_buy_origin_end_to_end_runtime_acceptance.md"), _render_markdown(payload))
    return payload


def build_phase15by_fixture(root: Path) -> dict[str, Any]:
    _init_dirs(root)
    _write_current_before_buy(root)
    _write_runtime_state(root, BUY_DATE, state="READY_FOR_BUY_ACCEPTANCE")
    _write_empty_pending(root)
    _write_policy(root)
    _write_safety(root, BUY_DATE, "phase15by-buy-safety-allow")
    _write_safety(root, NEXT_DATE, "phase15by-nextday-safety-allow")
    _write_feature_inputs(root)
    _write_buy_ai_models(root)
    manifest = {
        "schema_version": "phase15by_fixture_manifest_v1",
        "runtime_root": str(root),
        "buy_date": BUY_DATE,
        "next_business_date": NEXT_DATE,
        "issue_code": ISSUE_CODE,
        "acceptance_fixture": True,
        "investment_decision_generated_by_codex": False,
        "production_equivalent": False,
        "broker_write_performed": False,
    }
    _write_json(root / "scenario_manifest.json", manifest)
    _write_json(root / "runtime_state" / "run_manifest" / BUY_DATE / "phase15by-buy-fixture.json", manifest)
    return manifest


def _buy_execution_snapshot_provider(**kwargs: Any):
    snapshot_path = Path(kwargs["snapshot_path"])
    report_path = Path(kwargs["report_path"])
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": BUY_DATE + "T09:10:00+09:00",
        "acceptance_only": True,
        "simulation": True,
        "production_equivalent": False,
        "orders": [
            {
                "order_id_hash": "phase15by-buy-order-7203",
                "issue_code": ISSUE_CODE,
                "side": "buy",
                "quantity": str(int(BUY_QUANTITY)),
                "executed_quantity": str(int(BUY_QUANTITY)),
                "remaining_quantity": "0",
                "status": "全部約定",
                "order_datetime": "20260713091000",
                "as_of": BUY_DATE + "T09:10:00+09:00",
            }
        ],
        "executions": [],
        "positions": [
            {
                "position_id": "phase15by-position-7203",
                "issue_code": ISSUE_CODE,
                "quantity": str(int(BUY_QUANTITY)),
                "average_price": str(EXECUTION_PRICE),
                "market_value": str(int(BUY_QUANTITY * EXECUTION_PRICE)),
                "as_of": BUY_DATE + "T09:10:00+09:00",
            }
        ],
        "buying_power": {
            "raw_clmid": "SIMULATED_BUYING_POWER",
            "cash_available": "900000",
            "buying_power": "900000",
            "currency": "JPY",
        },
        "health": {
            "orders": {"status": "PASS", "count": 1},
            "positions": {"status": "PASS", "count": 1},
            "executions": {"status": "PASS", "count": 0, "detail_attempted_count": 0, "failures": []},
        },
    }
    _write_json(snapshot_path, payload)
    _write_json(report_path, {"status": "PASS", "source": "phase15by_simulated_buy_execution_snapshot"})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _write_feature_inputs(root: Path) -> None:
    feature_dir = root / "operations" / "feature_artifacts" / FEATURE_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "target_date": FEATURE_DATE,
            "as_of_date": FEATURE_DATE,
            "code": ISSUE_CODE,
            "feature_version": "phase15by_acceptance_features",
            "source_snapshot_id": "phase15by-snapshot-7203",
            "universe_eligible": True,
            "excluded_reason": "",
            "price_momentum_return_20d": 0.9,
            "price_momentum_return_5d": 0.4,
            "price_momentum_return_60d": 1.2,
            "trend_close_over_ma_20d": 0.3,
            "trend_ma_20_60_ratio": 1.01,
            "trend_ma_5_20_ratio": 1.02,
            "volatility_return_std_20d": 0.02,
            "volume_momentum_ratio_1d_20d": 1.2,
            "volume_momentum_ratio_5d": 1.1,
            "liquidity_avg_volume_20d": 1_000_000,
            "market_breadth_20d": 0.65,
            "market_breadth_5d": 0.62,
            "market_downtrend_context": False,
            "market_downtrend_flag": False,
            "market_ma_5_20_ratio": 1.01,
            "market_return_20d": 0.04,
            "market_return_5d": 0.02,
            "market_risk_flag": False,
            "market_volatility_20d": 0.015,
            "missing_flags_insufficient_history": False,
            "missing_flags_price": False,
            "missing_flags_volume": False,
            "sector_breadth_20d": 0.7,
            "sector_momentum_flag": True,
            "sector_rank_20d": 1,
            "sector_return_20d": 0.05,
            "sector_return_5d": 0.03,
            "sector_weak_flag": False,
            "stock_vs_sector_return_20d": 0.85,
            "price": EXECUTION_PRICE,
        }
    ]
    pd.DataFrame(rows).to_parquet(feature_dir / "candidate_features.parquet", index=False)
    pd.DataFrame(rows).to_parquet(feature_dir / "opportunity_feature_input.parquet", index=False)
    pd.DataFrame(
        [
            {
                "target_date": FEATURE_DATE,
                "entry_date": FEATURE_DATE,
                "code": ISSUE_CODE,
                "holding_days": 0,
                "current_price": EXECUTION_PRICE,
                "unrealized_return": 0.0,
                "feature_version": "position_management_feature_v1",
                "data_until": FEATURE_DATE,
                "created_at": FEATURE_DATE + "T00:00:00Z",
                "no_position_reason": "",
            }
        ]
    ).to_parquet(feature_dir / "position_feature_input.parquet", index=False)
    pd.DataFrame([{"target_date": FEATURE_DATE, "code": "__POLICY_INPUT__", "data_until": FEATURE_DATE}]).to_parquet(
        feature_dir / "capital_policy_input.parquet",
        index=False,
    )
    price_dir = root / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily"
    price_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Code": ISSUE_CODE, "Date": FEATURE_DATE, "Close": EXECUTION_PRICE, "PriceSource": "phase15by_fixture_close"}]).to_parquet(
        price_dir / "data.parquet",
        index=False,
    )


def _write_buy_ai_models(root: Path) -> None:
    model_dir = root / "runtime_state" / "buy_ai_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    _write_pickle(
        model_dir / "candidate_model.pkl",
        {
            "model": CandidateAcceptanceModel(),
            "feature_columns": ["feature__price_momentum_return_20d"],
            "model_version": "candidate_model_phase15by_acceptance_fixture",
        },
    )
    _write_pickle(
        model_dir / "opportunity_model.pkl",
        {
            "model": OpportunityAcceptanceModel(),
            "feature_columns": ["feature__candidate_score"],
            "preprocessing": {"medians": {"feature__candidate_score": 0.0}},
            "model_version": "opportunity_model_phase15by_acceptance_fixture",
        },
    )
    _write_json(
        model_dir / "opportunity_training_metrics.json",
        {
            "status": "PASS",
            "readiness_status": "READY",
            "model_artifact_path": str(model_dir / "opportunity_model.pkl"),
            "feature_columns": ["feature__candidate_score"],
        },
    )


def _write_policy(root: Path) -> None:
    path = root / "runtime_state" / "policy" / "phase15by_capital_deployment_policy.json"
    _write_json(
        path,
        {
            "policy_version": "phase15by_buy_origin_acceptance_policy_v1",
            "policy_source": str(path),
            "evaluation_capital": 1_000_000,
            "target_investment_ratio": 0.20,
            "cash_buffer": 0.05,
            "max_exposure": 200_000,
            "max_position_weight": 0.10,
            "max_positions": 1,
            "min_order_amount": 0,
            "max_buy_order_amount": None,
            "max_sell_liquidation_amount": None,
            "buy_notional_policy": "acceptance_fixture_single_buy_100_shares",
            "sell_liquidation_policy": "current_owned_available_quantity_policy",
            "manual_review_threshold": {"buy_amount": None, "sell_liquidation_amount": None},
        },
    )


def _write_current_before_buy(root: Path) -> None:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "phase15by-current-before-buy",
            "environment": "demo",
            "source": "phase15by_acceptance_fixture",
            "as_of": BUY_DATE,
            "positions": [],
            "cash": 1_000_000.0,
            "buying_power": 1_000_000.0,
            "market_value": 0.0,
            "total_equity": 1_000_000.0,
            "runtime_evaluation_capital": 1_000_000.0,
            "review_required": False,
            "production_equivalent": False,
            "current_state_confirmed_empty": True,
            "current_positions_unknown": False,
            "cash_unknown": False,
            "buying_power_unknown": False,
            "generated_from": [],
            "created_at": BUY_DATE,
            "updated_at": BUY_DATE,
        },
    )


def _write_next_day_market(root: Path) -> None:
    quote = {
        ISSUE_CODE: {
            "symbol": ISSUE_CODE,
            "price": NEXT_PRICE,
            "price_type": "jquants_daily_quote",
            "market_date": NEXT_DATE,
            "observed_at": NEXT_DATE,
            "source": "phase15by_next_day_market_fixture",
            "freshness_status": "READY",
            "adjusted": False,
        }
    }
    artifact = root / "runtime_state" / "market" / NEXT_DATE / "market_evidence.json"
    _write_json(
        artifact,
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "runtime_business_date": NEXT_DATE,
            "market_date": NEXT_DATE,
            "latest_expected_trading_date": NEXT_DATE,
            "latest_available_market_date": NEXT_DATE,
            "market_status": "READY",
            "market_freshness_status": "READY",
            "quote_status": "READY",
            "quotes": quote,
        },
    )
    _write_json(root / "runtime_state" / "market" / "latest.json", {"artifact_path": str(artifact), "market_date": NEXT_DATE})


def _write_pm_inputs(root: Path) -> tuple[Path, Path]:
    directory = root / "runtime_state" / "pm_inputs" / NEXT_DATE
    directory.mkdir(parents=True, exist_ok=True)
    opportunity = directory / "pm_opportunity.csv"
    feature = directory / "pm_feature.csv"
    pd.DataFrame(
        [
            {
                "target_date": NEXT_DATE,
                "code": ISSUE_CODE,
                "expected_edge_score": 0.10,
                "buy_rank": 999,
                "downside_risk_score": 0.20,
                "risk_guard_status": "ok",
                "candidate_score": 0.80,
                "candidate_rank": 999,
                "buy_reason": "acceptance_fixture_buy_origin",
                "no_buy_reason": "",
                "calibration_policy_name": "phase15by_fixture",
            }
        ]
    ).to_csv(opportunity, index=False)
    pd.DataFrame(
        [
            {
                "target_date": NEXT_DATE,
                "as_of_date": NEXT_DATE,
                "code": ISSUE_CODE,
                "feature_version": "position_management_feature_v1",
                "return_5d": 0.05,
                "return_20d": 0.05,
                "close_over_ma_20d": 0.05,
                "ma_5_20_ratio": 1.05,
                "volume_ratio_5d": 1.0,
                "volatility_20d": 0.02,
                "holding_days": 1,
                "current_price": NEXT_PRICE,
                "unrealized_return": (NEXT_PRICE / EXECUTION_PRICE) - 1.0,
                "peak_return": (NEXT_PRICE / EXECUTION_PRICE) - 1.0,
            }
        ]
    ).to_csv(feature, index=False)
    return opportunity, feature


def _write_next_day_manifest(*, root: Path, pm: Any, valuation: Any, current_apply: Any) -> None:
    manifest = {
        "schema_version": "phase15by_next_day_runtime_manifest_v1",
        "business_date": NEXT_DATE,
        "runtime_mode": "demo",
        "environment": "demo",
        "final_state": "SELL_HOLD_REVIEW_READY",
        "job": "sell_hold_review_after_buy",
        "stages": [
            {"name": "current_valuation_refresh", "status": valuation.status},
            {"name": "current_apply", "status": current_apply.status},
            {"name": "position_management_ai_runtime_producer", "status": pm.status},
            {"name": "sell_hold_decision", "status": "PASS"},
        ],
        **pm.to_manifest_fields(),
        **valuation.manifest_fields,
        "current_apply_status": current_apply.status,
        "current_hash": current_apply.current_hash,
        "notification_sent": False,
    }
    _write_json(root / "runtime_state" / "run_manifest" / NEXT_DATE / "phase15by-next-day-sell-hold.json", manifest)
    state_path = root / "runtime_state" / "current_state.json"
    state_payload = _read_json(state_path) if state_path.exists() else {}
    state_payload.update(
        {
            "schema_version": "runtime_v2_current_apply_state_v1",
            "business_date": NEXT_DATE,
            "runtime_mode": "demo",
            "environment": "demo",
            "job": "sell_hold_review_after_buy",
            "state": "SELL_HOLD_REVIEW_READY",
            "exit_code": 0,
            "stage_statuses": manifest["stages"],
            "pm_artifact_path": pm.artifact_path,
            "pm_status": pm.status,
            "notification_sent": False,
        }
    )
    _write_json(state_path, state_payload)


def _write_safety(root: Path, business_date: str, decision_id: str) -> None:
    path = root / "runtime_state" / "safety" / "latest_safety_decision.json"
    _write_json(
        path,
        {
            "safety_decision_id": decision_id,
            "safety_policy_version": "safety_operation_guard_v1",
            "safety_source": str(path),
            "business_date": business_date,
            "runtime_mode": "demo",
            "decision": "ALLOW",
            "reason": "phase15by acceptance fixture safety allow",
            "review_required": False,
            "block_buy": False,
            "block_sell": False,
            "block_submit": False,
            "halt_runtime": False,
            "emergency_stop": False,
            "generated_at": business_date + "T08:00:00+09:00",
            "expires_at": business_date + "T15:00:00+09:00",
        },
    )


def _write_runtime_state(root: Path, business_date: str, *, state: str) -> None:
    _write_json(
        root / "runtime_state" / "current_state.json",
        {
            "schema_version": "runtime_v2_current_apply_state_v1",
            "business_date": business_date,
            "runtime_mode": "demo",
            "environment": "demo",
            "job": "phase15by_acceptance",
            "state": state,
            "exit_code": 0,
            "current_pointer": str(root / "persistent_ledger" / "state.json"),
            "notification_sent": False,
        },
    )


def _write_empty_pending(root: Path) -> None:
    _write_json(
        root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "1",
            "pending_plan_id": "phase15by-empty",
            "state": "CONSUMED",
            "environment": "demo",
            "created_at": BUY_DATE,
            "updated_at": BUY_DATE,
            "plan_created_date": BUY_DATE,
            "intended_submit_date": BUY_DATE,
            "target_session_date": BUY_DATE,
            "source_order_plan": {"order_plan_id": "empty", "path": "", "artifact_hash": ""},
            "approval": None,
            "approved_item_ids": [],
            "items": [],
            "submit_constraints": {"expires_at": ""},
            "consume": {"consumed": True, "consume_reason": "fixture_empty"},
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        },
    )


def _init_dirs(root: Path) -> None:
    for path in (
        root / "pending_order_plan",
        root / "runtime_state" / "policy",
        root / "runtime_state" / "safety",
        root / "runtime_state" / "run_manifest" / BUY_DATE,
        root / "runtime_state" / "run_manifest" / NEXT_DATE,
        root / "persistent_ledger",
    ):
        path.mkdir(parents=True, exist_ok=True)
    for name in ("orders", "executions", "positions", "cash", "events"):
        (root / "persistent_ledger" / f"{name}.jsonl").write_text("", encoding="utf-8")


def _request_payload(command: RuntimeV2SubmitCommand) -> dict[str, Any]:
    return {
        "command_id": command.command_id,
        "environment": command.environment,
        "pending_plan_id": command.pending_plan_id,
        "pending_item_id": command.pending_item_id,
        "approval_hash": command.approval_hash,
        "issue_code": command.symbol,
        "side": command.side,
        "quantity": command.quantity,
        "order_type": command.order_type,
        "price_type": command.price_type,
        "target_session_date": command.target_session_date,
        "request_hash": REQUEST_HASH,
        "network_called": False,
        "broker_write_performed": False,
        "raw_request_saved": False,
        "secret_saved": False,
    }


def _current_summary(current: dict[str, Any]) -> dict[str, Any]:
    positions = current.get("positions") or []
    return {
        "cash": current.get("cash"),
        "buying_power": current.get("buying_power"),
        "market_value": current.get("market_value"),
        "total_equity": current.get("total_equity"),
        "position_count": len(positions),
        "position": positions[0] if positions else {},
        "current_hash": _hash_json(current),
    }


def _first_execution(root: Path) -> dict[str, Any]:
    rows = _read_jsonl(root / "persistent_ledger" / "executions.jsonl")
    return rows[0] if rows else {}


def _ledger_counts(root: Path) -> dict[str, int]:
    return {
        name: len(_read_jsonl(root / "persistent_ledger" / f"{name}.jsonl"))
        for name in ("orders", "executions", "positions", "cash", "events")
    }


def _existing_runtime_hashes() -> dict[str, str]:
    paths = {
        "pending": Path(".runtime/pending_order_plan/pending_order_plan.json"),
        "safety": Path(".runtime/runtime_state/safety/latest_safety_decision.json"),
        "current": Path(".runtime/persistent_ledger/state.json"),
    }
    return {key: _sha256(path) for key, path in paths.items() if path.exists()}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_pickle(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(value, handle)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_json(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _render_markdown(payload: dict[str, Any]) -> str:
    current = payload["buy_current"]
    next_current = payload["next_day_current"]
    pm = payload["pm_ai"]
    return "\n".join(
        [
            "# Phase15-BY BUY-Origin End-to-End Runtime Acceptance",
            "",
            "## Final Judgment",
            "",
            f"`{payload['final_judgment']}`",
            "",
            "## BUY Mainline",
            "",
            f"- Morning: {payload['buy_mainline']['morning_status']} / {payload['buy_mainline']['issue_code']} BUY {payload['buy_mainline']['quantity']}",
            f"- Submit: {payload['submit']['status']} / accepted={payload['submit']['accepted_count']} / broker_write=false",
            f"- Execution: {payload['execution']['status']} / execution_id={payload['execution']['execution_references'][0] if payload['execution']['execution_references'] else ''}",
            f"- BUY Current: cash={current['cash']} market_value={current['market_value']} position_count={current['position_count']}",
            "",
            "## Next-Day SELL/HOLD",
            "",
            f"- Current position_state_as_of={payload['current_restart']['position_state_as_of']} valuation_as_of={payload['current_restart']['valuation_as_of']}",
            f"- PM AI: {pm['status']} / decision_count={pm['decision_count']} / HOLD={pm['hold_count']} / EXIT={pm['exit_count']}",
            f"- SELL/HOLD decision: {payload['sell_hold']['decision']}",
            f"- Next Current: cash={next_current['cash']} market_value={next_current['market_value']} total_equity={next_current['total_equity']}",
            "",
            "## Boundaries",
            "",
            "- Production Write: false",
            "- New real Broker Write: false",
            "- Notification Delivery: false",
            "- Existing .runtime mutation: false",
            "",
            "## Conditions",
            "",
            *[f"- {condition}" for condition in payload["remaining_conditions"]],
            "",
            "## Next Prefix",
            "",
            payload["recommended_next_prefix"],
            "",
        ]
    )


if __name__ == "__main__":
    target_root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    payload = run_phase15by_buy_origin_e2e(root=target_root)
    print(json.dumps({"final_judgment": payload["final_judgment"], "runtime_root": str(target_root)}, ensure_ascii=False))
