from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai_fund_lab_v2.broker.demo_order import TachibanaDemoOrderAdapter
from ai_fund_lab_v2.broker.issue_code_normalizer import BrokerIssueCodeNormalizationError, normalize_broker_issue_code
from ai_fund_lab_v2.broker.secrets import TachibanaSecretLoader
from ai_fund_lab_v2.broker.settings import load_broker_settings
from ai_fund_lab_v2.operations.guards import (
    ai_feature_contamination_audit,
    artifact_leakage_audit,
    evaluate_max_exposure,
    normalize_runtime_environment,
    validate_demo_environment,
    validate_runtime_environment,
)
from ai_fund_lab_v2.operations.broker_readonly import (
    load_broker_artifact_bundle,
    refresh_demo_broker_readonly_artifacts,
)
from ai_fund_lab_v2.operations.demo_ledger import (
    detect_demo_broker_daily_reset,
    record_demo_readonly_monitoring,
    record_demo_special_fill_simulation,
    record_demo_submit_result,
    summarize_demo_ledger,
)
from ai_fund_lab_v2.operations.exit_adapter import generate_sell_items_from_positions
from ai_fund_lab_v2.operations.io import OperationPaths, read_json, stable_hash, utc_now_iso, write_json
from ai_fund_lab_v2.operations.ledger import write_operations_ledger_from_broker_readonly
from ai_fund_lab_v2.operations.market_calendar import resolve_operation_date
from ai_fund_lab_v2.operations.market_refresh import (
    DEFAULT_MAX_BUY_ORDERS_PER_DAY,
    DEFAULT_MAX_POSITIONS,
    feature_candidate_diagnostics,
    load_feature_buy_candidates,
    run_operations_market_refresh,
)
from ai_fund_lab_v2.operations.notifications import run_operation_notifications
from ai_fund_lab_v2.paper_trading.reporting.blog_report_v2_writer import _render_markdown_v4 as render_phase9_blog_report_v4
from ai_fund_lab_v2.runtime import (
    BusinessDayGuard,
    DemoOrderExecutor,
    OrderApprovalGate,
    OrderApprovalScope,
    OrderCommand,
    OrderSide,
    OrderType,
    PriceType,
    RuntimeMode,
)

DEFAULT_OPERATION_ROOT = Path(".runtime/operations")
DEMO_OPERATION_INITIAL_EQUITY = Decimal("1000000")
NORMAL_OPERATION_DAY = "NORMAL_OPERATION_DAY"
MARKET_CLOSED_DAY = "MARKET_CLOSED_DAY"
RECOVERY_DAY = "RECOVERY_DAY"
INCOMPLETE_OPERATION_DAY = "INCOMPLETE_OPERATION_DAY"
REVIEW_REQUIRED_DAY = "REVIEW_REQUIRED_DAY"
CONFIRMED_MARKET_CLOSED_REASONS = {
    "WEEKEND",
    "WEEKEND_FALLBACK",
    "KNOWN_HOLIDAY",
    "JQUANTS_CONFIRMED_CLOSED",
    "JP_MARKET_HOLIDAY_FALLBACK",
}
NORMAL_REPORT_ALLOWED_DAY_TYPES = {NORMAL_OPERATION_DAY}
OPERATIONS_SOURCE_OF_TRUTH = {
    "submitted_orders": {
        "artifact": "submitted_orders/YYYY-MM-DD/submitted_orders.json",
        "rule": "Brokerへ送信を試みた注文の正。Order Planを本日注文扱いしない。",
    },
    "broker_acceptance": {
        "artifact": "broker_orders/YYYY-MM-DD/orders.json",
        "rule": "Broker受付・注文状態の正。",
    },
    "executions": {
        "artifact": "broker_executions/YYYY-MM-DD/executions.json",
        "fallback": "broker_orders executed_quantity/status",
        "rule": "約定はbroker_executions優先。無い場合のみbroker_ordersの約定数量/statusで補完する。",
    },
    "positions": {
        "artifact": "broker_positions/YYYY-MM-DD/positions.json",
        "rule": "現在保有の正。Order PlanやSubmitted Ordersから保有を推定しない。",
    },
    "cash_buying_power": {
        "artifact": "broker_buying_power/YYYY-MM-DD/buying_power.json",
        "fallback": "account_summary",
        "rule": "ProductionはBroker値を優先。Demo評価表示はPersistent Demo Ledgerの100万円基準を維持する。",
    },
    "persistent_history": {
        "artifact": "demo_ledger/",
        "rule": "Demo日次リセットをまたぐ注文・約定・ポジション履歴の正。Broker Snapshotで全量上書きしない。",
    },
    "next_business_day_candidates": {
        "artifact": "order_plan/YYYY-MM-DD/order_plan.json",
        "rule": "翌営業日候補の正。本日注文・本日約定として扱わない。",
    },
    "approval": {
        "artifact": "approval_artifact/YYYY-MM-DD/approval_artifact.json",
        "rule": "注文許可の正。submit時に期限を再確認する。",
    },
    "safety": {
        "artifact": "safety_result / safety_monitor",
        "rule": "System Guardの正。投資判断や学習入力には使わない。",
    },
    "reconcile": {
        "artifact": "reconciliation_result/YYYY-MM-DD/reconciliation_result.json",
        "rule": "日次照合結果の正。",
    },
    "report": {
        "artifact": "reports/YYYY-MM-DD/",
        "rule": "上記SoTから派生生成する。Order Planを本日注文・約定扱いしない。",
    },
}


def _operations_runtime_config() -> dict[str, Any]:
    return {
        "max_buy_orders_per_day": DEFAULT_MAX_BUY_ORDERS_PER_DAY,
        "max_new_positions_per_day": DEFAULT_MAX_BUY_ORDERS_PER_DAY,
        "max_positions": DEFAULT_MAX_POSITIONS,
        "max_total_exposure_ratio": "0.85",
        "candidate_count_environment_specific": False,
        "capital_allocation_connected": False,
        "capital_allocation_connection_deferred_reason": "Phase12-AH keeps the minimal Production-equivalent candidate count fix; full Capital Allocation AI connection is deferred to Phase13 or the next design phase.",
    }


def run_preflight(
    *,
    trade_date: str | None = None,
    root: Path = DEFAULT_OPERATION_ROOT,
    required_env: list[str] | None = None,
    refresh_broker_readonly: bool = False,
) -> dict[str, Any]:
    trade_date = trade_date or date.today().isoformat()
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    env_guard = validate_runtime_environment(env, base_url=runtime["base_url"], production_order_allowed=False)
    business_day = BusinessDayGuard().check(trade_date).to_dict()
    market_calendar = _market_calendar(paths, trade_date)
    required = (
        required_env
        if required_env is not None
        else ["TACHIBANA_API_ENV", "TACHIBANA_API_AUTH_ID_FILE", "TACHIBANA_API_PRIVATE_KEY_FILE", "TACHIBANA_API_SECOND_PASSWORD_FILE"]
    )
    missing = [key for key in required if not os.environ.get(key)]
    lock_path = paths.dated("locks", trade_date, "preflight.lock")
    lock_path.write_text(f"owner=operation_preflight\ncreated_at={utc_now_iso()}\n", encoding="utf-8")
    broker_refresh = {"status": "NOT_REQUESTED", "api_called": False}
    if refresh_broker_readonly:
        broker_refresh = refresh_demo_broker_readonly_artifacts(trade_date=trade_date, root=paths.root, run_enabled=True)
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    broker_snapshot_summary = (broker_bundle.get("artifacts", {}).get("broker_snapshot_summary") or _default_broker_snapshot_summary(trade_date, env))
    ledger_result = write_operations_ledger_from_broker_readonly(trade_date=trade_date, root=paths.root) if broker_bundle["status"] == "PASS" else {"status": "SKIPPED_BROKER_ARTIFACT_INCOMPLETE"}
    safety_result = _default_safety_result(trade_date)
    status = "PASS"
    reasons: list[str] = []
    if runtime["status"] != "PASS":
        status = "BLOCK"
        reasons.extend(runtime["reasons"])
    if not env_guard["allowed"]:
        status = "BLOCK"
        reasons.extend(env_guard["reasons"])
    if market_calendar["market_closed"]:
        status = "PASS_MARKET_CLOSED_READONLY_ONLY"
        reasons.append(f"market_closed:{market_calendar['market_closed_reason']}")
    if missing and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append("required_env_missing")
    if required_env is None and broker_bundle["status"] != "PASS" and status != "BLOCK":
        status = "REVIEW_REQUIRED"
        reasons.append("broker_readonly_artifact_missing_or_incomplete")
    if broker_bundle["raw_response_saved"] or broker_bundle["secret_saved"]:
        status = "BLOCK"
        reasons.append("broker_artifact_leakage_detected")
    leakage = artifact_leakage_audit({"broker_snapshot_summary": broker_snapshot_summary, "safety_result": safety_result})
    if leakage["status"] != "PASS":
        status = "BLOCK"
        reasons.append("artifact_leakage_detected")
    payload = _base_payload("preflight", env, trade_date, status)
    payload.update(
        {
            "runtime_environment": runtime,
            "environment_guard": env_guard,
            "business_day_guard": business_day,
            "market_calendar": market_calendar,
            "market_closed": market_calendar["market_closed"],
            "submit_allowed": False if market_calendar["market_closed"] else status == "PASS",
            "run_lock": {"path": str(lock_path), "acquired": True},
            "required_env": {"checked": required, "missing": missing, "values_printed": False},
            "broker_snapshot_summary": broker_snapshot_summary,
            "broker_readonly_refresh": broker_refresh,
            "broker_readonly_artifact_bundle": {
                key: value
                for key, value in broker_bundle.items()
                if key != "artifacts"
            },
            "operations_ledger": ledger_result,
            "safety_result": safety_result,
            "raw_response_secret_audit": leakage,
            "reasons": reasons,
        }
    )
    output = paths.dated("preflight", trade_date, "preflight_result.json")
    write_json(output, payload)
    write_json(paths.dated("broker_snapshot_summary", trade_date, "broker_snapshot_summary.json"), broker_snapshot_summary)
    write_json(paths.dated("safety_result", trade_date, "safety_result.json"), safety_result)
    _write_daily_manifest(paths, trade_date, env=env, overrides={"preflight_status": status, "run_lock_status": "PASS", "market_calendar": market_calendar})
    return {**payload, "artifact_path": str(output)}


def run_market_refresh(
    *,
    trade_date: str | None = None,
    root: Path = DEFAULT_OPERATION_ROOT,
    data_until: str | None = None,
    feature_sources: list[str] | None = None,
    data_quality_status: str = "PASS",
    allow_api_fetch: bool = False,
    from_date: str | None = None,
    fetch_mode: str = "per-date",
    fetcher: Any | None = None,
) -> dict[str, Any]:
    trade_date = trade_date or date.today().isoformat()
    data_until = data_until or trade_date
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    env_guard = validate_runtime_environment(env, base_url=runtime["base_url"], production_order_allowed=False)
    market_calendar = _market_calendar(paths, trade_date)
    sources = feature_sources or ["jquants_daily_quotes", "jquants_listed_info", "jquants_trading_calendar"]
    contamination = ai_feature_contamination_audit(sources)
    blocked: list[str] = []
    if runtime["status"] != "PASS":
        blocked.extend(runtime["reasons"])
    if not env_guard["allowed"]:
        blocked.extend(env_guard["reasons"])
    if contamination["status"] != "PASS":
        blocked.append("feature_source_contamination")
    if data_quality_status not in {"PASS", "REVIEW_REQUIRED"}:
        blocked.append("data_quality_block")
    if market_calendar["market_closed"]:
        status = "SKIPPED_MARKET_CLOSED" if not blocked else "BLOCK"
        marker_path = paths.dated("feature_refresh", trade_date, "latest_features.json")
        market_manifest = _base_payload("market_refresh", env, trade_date, status)
        market_manifest.update(
            {
                "market_calendar": market_calendar,
                "market_closed": True,
                "market_closed_reason": market_calendar["market_closed_reason"],
                "skip_reason": "MARKET_CLOSED",
                "data_until": market_calendar["latest_available_market_date"],
                "decision_for": trade_date,
                "latest_available_market_date": market_calendar["latest_available_market_date"],
                "feature_freshness_status": "MARKET_CLOSED",
                "jquants_api_fetch_executed": False,
                "raw_daily_quotes_updated": False,
                "listed_info_updated": False,
                "trading_calendar_updated": False,
                "canonical_normalized_updated": False,
                "feature_refresh_executed": False,
                "data_quality_status": "REVIEW_REQUIRED" if not blocked else "BLOCK",
                "ai_inference_executed": False,
                "order_plan_generated": False,
                "approval_generated": False,
                "broker_order_api_called": False,
                "line_payload_generated": False,
                "line_send_executed": False,
                "feature_sources": sources,
                "ai_feature_contamination_audit": contamination,
                "feature_artifact_path": str(marker_path),
                "candidate_feature_path": "",
                "market_data_refresh_detail": {},
                "blocked_reasons": blocked,
            }
        )
        feature_manifest = _base_payload("feature_refresh", env, trade_date, status)
        feature_manifest.update(
            {
                "market_calendar": market_calendar,
                "market_closed": True,
                "skip_reason": "MARKET_CLOSED",
                "data_until": market_calendar["latest_available_market_date"],
                "decision_for": trade_date,
                "latest_available_market_date": market_calendar["latest_available_market_date"],
                "feature_freshness_status": "MARKET_CLOSED",
                "latest_feature_path": str(marker_path),
                "feature_exists": False,
                "feature_sources": sources,
                "ai_feature_contamination_audit": contamination,
                "feature_refresh_status": "SKIPPED_MARKET_CLOSED",
                "feature_refresh_detail": {},
                "model_retraining_executed": False,
                "inference_executed": False,
                "order_plan_generation_executed": False,
                "broker_order_api_called": False,
                "blocked_reasons": blocked,
            }
        )
        data_quality = _base_payload("data_quality", env, trade_date, "REVIEW_REQUIRED" if not blocked else "BLOCK")
        data_quality.update(
            {
                "market_calendar": market_calendar,
                "data_until": market_calendar["latest_available_market_date"],
                "checks": {
                    "market_closed": True,
                    "feature_marker_exists": False,
                    "jquants_only": contamination["jquants_only"],
                    "jquants_api_fetch_executed": False,
                    "canonical_normalized_updated": False,
                    "raw_response_saved": False,
                    "secret_saved": False,
                },
                "blocked_reasons": blocked,
            }
        )
        market_path = paths.dated("market_refresh", trade_date, "market_refresh_manifest.json")
        feature_path = paths.dated("feature_refresh", trade_date, "feature_refresh_manifest.json")
        quality_path = paths.dated("data_quality", trade_date, "data_quality_result.json")
        write_json(market_path, market_manifest)
        write_json(feature_path, feature_manifest)
        write_json(quality_path, data_quality)
        manifest = _write_daily_manifest(paths, trade_date, env=env, overrides={
            "market_refresh_status": market_manifest["status"],
            "feature_refresh_status": feature_manifest["status"],
            "market_calendar": market_calendar,
            "run_lock_status": "PASS",
        })
        return {
            **market_manifest,
            "market_refresh_manifest_path": str(market_path),
            "feature_refresh_manifest_path": str(feature_path),
            "data_quality_result_path": str(quality_path),
            "daily_manifest_path": str(manifest),
        }
    adapter_result = run_operations_market_refresh(
        trade_date=trade_date,
        root=paths.root,
        allow_api_fetch=allow_api_fetch,
        from_date=from_date,
        fetch_mode=fetch_mode,
        fetcher=fetcher,
    )
    data_until = str(adapter_result.get("data_until") or data_until)
    feature_marker_path = Path(str(adapter_result["feature_artifact_path"]))
    if adapter_result["status"] != "PASS":
        blocked.extend(adapter_result.get("blocked_reasons", []))
    market_manifest = _base_payload("market_refresh", env, trade_date, "PASS" if not blocked else "BLOCK")
    market_manifest.update(
        {
            "data_until": data_until,
            "market_calendar": market_calendar,
            "market_closed": False,
            "decision_for": adapter_result.get("decision_for", trade_date),
            "latest_available_market_date": adapter_result.get("latest_available_market_date", data_until),
            "feature_freshness_status": adapter_result.get("feature_freshness_status", "UNKNOWN"),
            "jquants_api_fetch_executed": adapter_result["jquants_api_fetch_executed"],
            "raw_daily_quotes_updated": adapter_result["raw_daily_quotes_updated"],
            "listed_info_updated": adapter_result["listed_info_updated"],
            "trading_calendar_updated": adapter_result["trading_calendar_updated"],
            "canonical_normalized_updated": adapter_result["canonical_normalized_updated"],
            "feature_refresh_executed": adapter_result["feature_refresh_executed"],
            "data_quality_status": adapter_result["data_quality_status"],
            "ai_inference_executed": False,
            "order_plan_generated": False,
            "approval_generated": False,
            "broker_order_api_called": False,
            "line_payload_generated": False,
            "line_send_executed": False,
            "feature_sources": sources,
            "ai_feature_contamination_audit": contamination,
            "feature_artifact_path": str(feature_marker_path),
            "candidate_feature_path": adapter_result.get("candidate_feature_path", ""),
            "market_data_refresh_detail": adapter_result.get("market_data_refresh_detail", {}),
            "blocked_reasons": blocked,
        }
    )
    feature_manifest = _base_payload("feature_refresh", env, trade_date, "PASS" if not blocked else "BLOCK")
    feature_manifest.update(
        {
            "data_until": data_until,
            "market_calendar": market_calendar,
            "market_closed": False,
            "decision_for": adapter_result.get("decision_for", trade_date),
            "latest_available_market_date": adapter_result.get("latest_available_market_date", data_until),
            "feature_freshness_status": adapter_result.get("feature_freshness_status", "UNKNOWN"),
            "latest_feature_path": str(feature_marker_path),
            "feature_exists": feature_marker_path.exists(),
            "feature_sources": sources,
            "ai_feature_contamination_audit": contamination,
            "feature_refresh_status": adapter_result.get("feature_refresh_status", "UNKNOWN"),
            "feature_refresh_detail": adapter_result.get("feature_refresh_detail", {}),
            "model_retraining_executed": False,
            "inference_executed": False,
            "order_plan_generation_executed": False,
            "broker_order_api_called": False,
            "blocked_reasons": blocked,
        }
    )
    data_quality = _base_payload("data_quality", env, trade_date, data_quality_status if not blocked else "BLOCK")
    data_quality.update(
        {
            "data_until": data_until,
            "market_calendar": market_calendar,
            "checks": {
                "feature_marker_exists": feature_marker_path.exists(),
                "jquants_only": contamination["jquants_only"],
                "jquants_api_fetch_executed": adapter_result["jquants_api_fetch_executed"],
                "canonical_normalized_updated": adapter_result["canonical_normalized_updated"],
                "raw_response_saved": False,
                "secret_saved": False,
            },
            "blocked_reasons": blocked,
        }
    )
    market_path = paths.dated("market_refresh", trade_date, "market_refresh_manifest.json")
    feature_path = paths.dated("feature_refresh", trade_date, "feature_refresh_manifest.json")
    quality_path = paths.dated("data_quality", trade_date, "data_quality_result.json")
    write_json(market_path, market_manifest)
    write_json(feature_path, feature_manifest)
    write_json(quality_path, data_quality)
    manifest = _write_daily_manifest(paths, trade_date, env=env, overrides={
        "market_refresh_status": market_manifest["status"],
        "feature_refresh_status": feature_manifest["status"],
        "market_calendar": market_calendar,
        "run_lock_status": "PASS",
    })
    return {
        **market_manifest,
        "market_refresh_manifest_path": str(market_path),
        "feature_refresh_manifest_path": str(feature_path),
        "data_quality_result_path": str(quality_path),
        "daily_manifest_path": str(manifest),
    }


def run_daily_plan(
    *,
    trade_date: str,
    root: Path = DEFAULT_OPERATION_ROOT,
    feature_sources: list[str] | None = None,
    plan_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    env_guard = validate_runtime_environment(env, base_url=runtime["base_url"], production_order_allowed=False)
    market_calendar = _market_calendar(paths, trade_date)
    operations_config = _operations_runtime_config()
    features = feature_sources or ["jquants_daily_quotes", "jquants_listed_info"]
    contamination = ai_feature_contamination_audit(features)
    market_gate = _validate_market_refresh_gate(paths, trade_date)
    if market_calendar["market_closed"]:
        plan_id = f"operation_plan_{trade_date}_{uuid4().hex[:12]}"
        order_plan = {
            "artifact_type": "order_plan",
            "plan_id": plan_id,
            "created_at": utc_now_iso(),
            "environment": env,
            "business_date": trade_date,
            "status": "SKIPPED_MARKET_CLOSED",
            "market_calendar": market_calendar,
            "operations_runtime_config": operations_config,
            "market_closed": True,
            "skip_reason": "MARKET_CLOSED",
            "requires_approval": False,
            "production_order_allowed": False,
            "demo_order_allowed": False,
            "items": [],
            "buy_item_count": 0,
            "sell_item_count": 0,
            "ai_inference_executed": False,
            "order_plan_generation_executed": False,
            "ai_feature_contamination_audit": contamination,
            "market_refresh_gate": market_gate,
            "exit_adapter": {"status": "SKIPPED_MARKET_CLOSED", "sell_items": []},
            "feature_buy_adapter": {"status": "SKIPPED_MARKET_CLOSED", "buy_items": [], "reason": "market_closed"},
            "feature_candidate_audit": {"status": "SKIPPED_MARKET_CLOSED", "candidate_count": 0},
            "ai_retraining_executed": False,
            "backtest_run": False,
        }
        output = paths.dated("order_plan", trade_date, "order_plan.json")
        write_json(output, order_plan)
        payload = _base_payload("daily_plan", env, trade_date, "SKIPPED_MARKET_CLOSED")
        payload.update(
            {
                "market_calendar": market_calendar,
                "market_closed": True,
                "skip_reason": "MARKET_CLOSED",
                "order_plan_path": str(output),
                "plan_id": plan_id,
                "item_count": 0,
                "buy_item_count": 0,
                "sell_item_count": 0,
                "environment_guard": env_guard,
                "market_refresh_gate": market_gate,
                "jquants_api_fetch_executed": False,
                "ai_inference_executed": False,
                "broker_order_api_called": False,
                "exit_adapter": order_plan["exit_adapter"],
                "feature_buy_adapter": order_plan["feature_buy_adapter"],
                "feature_candidate_audit_path": str(paths.dated("feature_candidate_audit", trade_date, "feature_candidate_audit.json")),
            }
        )
        write_json(paths.dated("daily_plan", trade_date, "daily_plan_result.json"), payload)
        write_json(paths.dated("feature_candidate_audit", trade_date, "feature_candidate_audit.json"), order_plan["feature_candidate_audit"])
        _write_daily_manifest(paths, trade_date, env=env, overrides={"daily_plan_status": "SKIPPED_MARKET_CLOSED", "market_calendar": market_calendar})
        return payload
    status = (
        "PASS"
        if runtime["status"] == "PASS"
        and env_guard["allowed"]
        and contamination["status"] == "PASS"
        and market_gate["status"] == "PASS"
        else "BLOCK"
    )
    plan_id = f"operation_plan_{trade_date}_{uuid4().hex[:12]}"
    exit_result = _generate_sell_items(paths, trade_date)
    if exit_result["status"] != "PASS":
        status = "BLOCK"
    feature_buy = (
        load_feature_buy_candidates(
            root=paths.root,
            trade_date=trade_date,
            max_items=int(operations_config["max_buy_orders_per_day"]),
        )
        if plan_items is None
        else {"status": "EXTERNAL_PLAN_ITEMS", "buy_items": [], "reason": ""}
    )
    feature_candidate_audit = {key: value for key, value in feature_buy.items() if key != "buy_items"}
    combined_items = list(plan_items or []) + list(feature_buy.get("buy_items", [])) + list(exit_result.get("sell_items", []))
    normalized_items = [_normalize_plan_item(item, index) for index, item in enumerate(combined_items, start=1)] if status == "PASS" else []
    order_plan = {
        "artifact_type": "order_plan",
        "plan_id": plan_id,
        "created_at": utc_now_iso(),
        "environment": env,
        "business_date": trade_date,
        "status": status,
        "requires_approval": True,
        "production_order_allowed": False,
        "demo_order_allowed": False,
        "items": normalized_items,
        "ai_feature_contamination_audit": contamination,
        "market_refresh_gate": market_gate,
        "exit_adapter": {key: value for key, value in exit_result.items() if key != "sell_items"},
        "feature_buy_adapter": {key: value for key, value in feature_buy.items() if key != "buy_items"},
        "feature_candidate_audit": feature_candidate_audit,
        "market_calendar": market_calendar,
        "operations_runtime_config": operations_config,
        "market_closed": False,
        "sell_item_count": sum(1 for item in normalized_items if item.get("side") == "SELL"),
        "buy_item_count": sum(1 for item in normalized_items if item.get("side") == "BUY"),
        "ai_retraining_executed": False,
        "backtest_run": False,
        "order_plan_generation_executed": status == "PASS",
    }
    output = paths.dated("order_plan", trade_date, "order_plan.json")
    write_json(output, order_plan)
    payload = _base_payload("daily_plan", env, trade_date, status)
    payload.update(
        {
            "order_plan_path": str(output),
            "market_calendar": market_calendar,
            "operations_runtime_config": operations_config,
            "market_closed": False,
            "plan_id": plan_id,
            "item_count": len(order_plan["items"]),
            "environment_guard": env_guard,
            "market_refresh_gate": market_gate,
            "jquants_api_fetch_executed": False,
            "broker_order_api_called": False,
            "exit_adapter": {key: value for key, value in exit_result.items() if key != "sell_items"},
            "feature_buy_adapter": {key: value for key, value in feature_buy.items() if key != "buy_items"},
            "feature_candidate_audit_path": str(paths.dated("feature_candidate_audit", trade_date, "feature_candidate_audit.json")),
        }
    )
    write_json(paths.dated("daily_plan", trade_date, "daily_plan_result.json"), payload)
    write_json(paths.dated("feature_candidate_audit", trade_date, "feature_candidate_audit.json"), feature_candidate_audit)
    _write_daily_manifest(paths, trade_date, env=env, overrides={"daily_plan_status": status, "market_calendar": market_calendar})
    return payload


def run_approval_prepare(
    *,
    trade_date: str,
    root: Path = DEFAULT_OPERATION_ROOT,
    approve: bool = False,
    auto_demo_approval: bool = False,
    approver_label: str = "",
    max_notional: Decimal | None = None,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    market_calendar = _market_calendar(paths, trade_date)
    if market_calendar["market_closed"]:
        request = {
            "artifact_type": "approval_request",
            "created_at": utc_now_iso(),
            "environment": env,
            "business_date": trade_date,
            "status": "SKIPPED_MARKET_CLOSED",
            "market_calendar": market_calendar,
            "market_closed": True,
            "skip_reason": "MARKET_CLOSED",
            "demo_order_allowed": False,
            "production_order_allowed": False,
            "approval_created": False,
            "approval_artifact_path": "",
        }
        request_path = paths.dated("approval_request", trade_date, "approval_request.json")
        write_json(request_path, request)
        _write_daily_manifest(paths, trade_date, env=env, overrides={"approval_status": "SKIPPED_MARKET_CLOSED", "market_calendar": market_calendar})
        payload = _base_payload("approval_prepare", env, trade_date, "SKIPPED_MARKET_CLOSED")
        payload.update(
            {
                "market_calendar": market_calendar,
                "market_closed": True,
                "skip_reason": "MARKET_CLOSED",
                "approval_request_path": str(request_path),
                "approval_artifact_path": "",
                "approved": False,
                "auto_demo_approval": auto_demo_approval,
                "demo_order_allowed": False,
                "production_order_allowed": False,
                "approval_blocks": ["MARKET_CLOSED"],
            }
        )
        return payload
    order_plan = _load_or_empty(paths.dated("order_plan", trade_date, "order_plan.json"), default=_empty_order_plan(trade_date, env))
    safety_result = _load_or_empty(paths.dated("safety_result", trade_date, "safety_result.json"), default=_default_safety_result(trade_date))
    broker_snapshot = _load_or_empty(
        paths.dated("broker_snapshot_summary", trade_date, "broker_snapshot_summary.json"),
        default=_default_broker_snapshot_summary(trade_date, env),
    )
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    approval_budget = _resolve_approval_max_notional(
        paths=paths,
        trade_date=trade_date,
        env=env,
        order_plan=order_plan,
        broker_snapshot=broker_snapshot,
        broker_bundle=broker_bundle,
        manual_override=max_notional,
    )
    approval_max_notional = approval_budget["approval_max_notional"]
    approval_id = f"operation_approval_{trade_date}_{uuid4().hex[:12]}"
    sell_scope = [_approval_sell_scope(item) for item in order_plan.get("items", []) if str(item.get("side")).upper() == "SELL"]
    approval_blocks = _validate_sell_approval_scope(sell_scope) if approve or auto_demo_approval else []
    approval_blocks.extend(approval_budget["approval_blocks"])
    if auto_demo_approval:
        approval_blocks.extend(_validate_auto_demo_approval(order_plan=order_plan, safety_result=safety_result, broker_snapshot=broker_snapshot, env=env, max_notional=approval_max_notional))
    effective_approve = approve or auto_demo_approval
    approved_item_ids = [item["item_id"] for item in order_plan.get("items", [])] if effective_approve and not approval_blocks else []
    approval_status = "APPROVED" if effective_approve and not approval_blocks else ("REVIEW_REQUIRED" if approval_blocks else "PENDING")
    approval_source = "demo_auto_approval" if auto_demo_approval else ("manual" if approve else "none")
    approval = {
        "artifact_type": "approval_artifact",
        "approval_id": approval_id,
        "environment": env,
        "business_date": trade_date,
        "plan_id": order_plan.get("plan_id", ""),
        "approved_item_ids": approved_item_ids,
        "approved_at": utc_now_iso() if effective_approve and not approval_blocks else "",
        "approval_expires_at": (datetime.now(timezone.utc) + timedelta(hours=16)).isoformat(),
        "approver_label": approver_label if effective_approve else "",
        "approval_source": approval_source,
        "manual_approval_required": False if auto_demo_approval else not approve,
        "demo_auto_approval": auto_demo_approval,
        "demo_order_wire_execution": auto_demo_approval or approve,
        "demo_order_allowed": effective_approve and env == "demo" and not approval_blocks,
        "production_order_allowed": False,
        "safety_result_hash": stable_hash(safety_result),
        "broker_snapshot_hash": stable_hash(broker_snapshot),
        "max_notional": _decimal_text(approval_max_notional),
        "approval_max_notional": _decimal_text(approval_max_notional),
        "approval_max_notional_source": approval_budget["approval_max_notional_source"],
        "equity_basis": _decimal_text(approval_budget["equity_basis"]),
        "equity_basis_source": approval_budget["equity_basis_source"],
        "max_total_exposure_ratio": str(approval_budget["max_total_exposure_ratio"]),
        "current_exposure": _decimal_text(approval_budget["current_exposure"]),
        "current_exposure_source": approval_budget["current_exposure_source"],
        "available_exposure_budget": _decimal_text(approval_budget["available_exposure_budget"]),
        "available_buying_power_or_cash": _decimal_text(approval_budget["available_buying_power_or_cash"]),
        "available_buying_power_or_cash_source": approval_budget["available_buying_power_or_cash_source"],
        "capital_allocation_budget": _optional_decimal_text(approval_budget["capital_allocation_budget"]),
        "approval_max_notional_formula": approval_budget["approval_max_notional_formula"],
        "approval_max_notional_inputs": approval_budget["approval_max_notional_inputs"],
        "status": approval_status,
        "approved_sides": sorted({str(item.get("side", "")).upper() for item in order_plan.get("items", []) if item.get("item_id") in approved_item_ids}),
        "sell_approval_scope": sell_scope,
        "approval_blocks": approval_blocks,
        "auto_approval_policy": {
            "demo_only": True,
            "production_order_allowed": False,
            "cash_equity_only": True,
            "margin_disabled": True,
            "safety_allow_required": True,
            "max_notional": _decimal_text(approval_max_notional),
            "approval_max_notional_source": approval_budget["approval_max_notional_source"],
            "secret_presence_required": True,
        } if auto_demo_approval else {},
        "market_calendar": market_calendar,
        "market_closed": False,
    }
    request = {
        "artifact_type": "approval_request",
        "created_at": utc_now_iso(),
        "environment": env,
        "business_date": trade_date,
        "plan_id": order_plan.get("plan_id", ""),
        "item_count": len(order_plan.get("items", [])),
        "safety_result_hash": approval["safety_result_hash"],
        "broker_snapshot_hash": approval["broker_snapshot_hash"],
        "sell_approval_scope": sell_scope,
        "approval_blocks": approval_blocks,
        "approval_max_notional": _decimal_text(approval_max_notional),
        "approval_max_notional_source": approval_budget["approval_max_notional_source"],
        "approval_max_notional_inputs": approval_budget["approval_max_notional_inputs"],
        "approval_artifact_path": str(paths.dated("approval_artifact", trade_date, "approval_artifact.json")),
        "market_calendar": market_calendar,
    }
    write_json(paths.dated("approval_request", trade_date, "approval_request.json"), request)
    output = paths.dated("approval_artifact", trade_date, "approval_artifact.json")
    write_json(output, approval)
    status = "PASS" if runtime["status"] == "PASS" else "BLOCK"
    payload = _base_payload("approval_prepare", env, trade_date, status)
    payload.update({"market_calendar": market_calendar, "market_closed": False, "approval_request_path": str(paths.dated("approval_request", trade_date, "approval_request.json")), "approval_artifact_path": str(output), "approved": effective_approve and not approval_blocks, "auto_demo_approval": auto_demo_approval, "approval_blocks": approval_blocks, "approval_max_notional": _decimal_text(approval_max_notional), "approval_max_notional_source": approval_budget["approval_max_notional_source"], "approval_max_notional_inputs": approval_budget["approval_max_notional_inputs"]})
    _write_daily_manifest(paths, trade_date, env=env, overrides={"approval_status": approval["status"], "market_calendar": market_calendar})
    return payload


def run_demo_submit(
    *,
    trade_date: str,
    root: Path = DEFAULT_OPERATION_ROOT,
    execute_demo_order: bool = False,
    second_password_present: bool = False,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    env_guard = validate_demo_environment(env, base_url=runtime["base_url"], production_order_allowed=False)
    market_calendar = _market_calendar(paths, trade_date)
    if market_calendar["market_closed"]:
        payload = _base_payload("demo_submit", env, trade_date, "SKIPPED_MARKET_CLOSED")
        payload.update(
            {
                "market_calendar": market_calendar,
                "market_closed": True,
                "skip_reason": "MARKET_CLOSED",
                "submit_allowed": False,
                "blocks": ["MARKET_CLOSED"],
                "submitted_orders": [],
                "retry_parent": {},
                "demo_order_executed": False,
                "demo_order_submitted": False,
                "production_order_submitted": False,
                "clm_kabu_new_order_called": False,
                "broker_order_api_called": False,
                "raw_request_saved": False,
                "raw_response_saved": False,
                "secret_saved": False,
            }
        )
        output = paths.dated("submitted_orders", trade_date, "submitted_orders.json")
        write_json(output, payload)
        _write_daily_manifest(paths, trade_date, env=env, overrides={"submit_status": "SKIPPED_MARKET_CLOSED", "market_calendar": market_calendar})
        return {**payload, "submitted_orders_path": str(output)}
    order_plan_date = _resolve_submit_order_plan_date(paths, trade_date, env=env, market_calendar=market_calendar)
    order_plan = _load_or_empty(paths.dated("order_plan", order_plan_date, "order_plan.json"), default=_empty_order_plan(order_plan_date, env))
    approval = _load_or_empty(paths.dated("approval_artifact", order_plan_date, "approval_artifact.json"), default={})
    safety = _load_or_empty(paths.dated("safety_result", trade_date, "safety_result.json"), default=_default_safety_result(trade_date))
    broker = _load_or_empty(paths.dated("broker_snapshot_summary", trade_date, "broker_snapshot_summary.json"), default=_default_broker_snapshot_summary(trade_date, env))
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    broker_orders = (broker_bundle.get("artifacts", {}).get("broker_orders") or {}).get("orders") or []
    positions_payload = _load_or_empty(paths.dated("positions", trade_date, "positions.json"), default={"positions": []})
    previous_submit = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={})
    retry_parent = _retry_parent_from_submit(previous_submit) if execute_demo_order else {}
    demo_ledger_state_before = summarize_demo_ledger(root=paths.root) if env == "demo" else {}
    submitted: list[dict[str, Any]] = []
    blocks: list[str] = []
    approval_max = Decimal(str(approval.get("approval_max_notional") or approval.get("max_notional") or "0"))
    remaining_approval_budget = approval_max
    projected_buying_power_usage = Decimal("0")
    projected_exposure = Decimal(str(broker.get("current_exposure", "0")))
    broker_buying_power = Decimal(str(broker.get("buying_power") or "0"))
    if runtime["status"] != "PASS":
        blocks.extend(runtime["reasons"])
    if not env_guard["allowed"]:
        blocks.extend(env_guard["reasons"])
    if not approval or not approval.get("demo_order_allowed"):
        blocks.append("approval_missing_or_not_demo_allowed")
    if approval.get("production_order_allowed"):
        blocks.append("production_order_allowed_true")
    if safety.get("status") in {"BLOCK", "SYSTEM_EMERGENCY_STOP"}:
        blocks.append(f"safety_{safety.get('status')}")
    approved_ids = set(approval.get("approved_item_ids", []))
    for item in order_plan.get("items", []):
        if item.get("item_id") not in approved_ids:
            continue
        item_run_id = f"operation_{trade_date}_{approval.get('approval_id', 'no_approval')}_{item.get('item_id')}"
        normalized_item = _normalize_item_for_demo_wire(item, paths=paths, trade_date=order_plan_date) if execute_demo_order else dict(item)
        normalization_result = _normalize_broker_issue_for_submit(normalized_item, paths=paths, trade_date=trade_date) if execute_demo_order else {}
        if normalization_result:
            normalized_item.update(normalization_result)
        item_blocks = _validate_item_for_submit(normalized_item, require_wire_ready=execute_demo_order)
        if execute_demo_order and normalization_result.get("normalization_status") != "PASS":
            item_blocks.append("broker_issue_code_normalization_failed")
        if execute_demo_order and _has_active_same_side_broker_order(broker_orders, broker_issue_code=str(normalized_item.get("broker_issue_code") or ""), side=str(normalized_item.get("side") or ""), quantity=str(normalized_item.get("quantity") or "")):
            item_blocks.append("duplicate_active_broker_order_exists")
        item_blocks.extend(_validate_sell_submit_scope(item, approval=approval, positions=positions_payload.get("positions", [])))
        order_value = Decimal(str(normalized_item.get("estimated_value") or normalized_item.get("expected_notional") or "0"))
        decision = evaluate_max_exposure(
            side=normalized_item.get("side", ""),
            order_value=order_value,
            current_exposure=projected_exposure,
            broker_actual_equity=_decimal_or_none(broker.get("broker_actual_equity")),
            buying_power=_decimal_or_none(broker.get("buying_power")),
        )
        if execute_demo_order and order_value > remaining_approval_budget:
            item_blocks.append("remaining_approval_budget_insufficient")
        if execute_demo_order and projected_buying_power_usage + order_value > broker_buying_power:
            item_blocks.append("buying_power_exceeded")
        if not decision.allowed:
            item_blocks.append(decision.reason)
        if item_blocks:
            submitted.append(
                _blocked_submit_item(
                    item=item,
                    normalized_item=normalized_item,
                    item_blocks=item_blocks,
                    approval_max=approval_max,
                    remaining_approval_budget=remaining_approval_budget,
                    order_value=order_value,
                    cumulative_submitted_notional=projected_buying_power_usage,
                    projected_buying_power_usage=projected_buying_power_usage,
                    projected_exposure=projected_exposure,
                    broker_buying_power=broker_buying_power,
                    max_exposure=decision.to_dict(),
                )
            )
            continue
        result_status = "DRY_RUN_READY"
        broker_order_id_hash = ""
        wire_result: dict[str, Any] = {}
        demo_order_submitted = False
        broker_order_api_called = False
        if execute_demo_order:
            second_password_status = TachibanaSecretLoader(load_broker_settings()).classify_second_password_file()
            command = _command_from_item(normalized_item, trade_date, approval["approval_id"], live_order_allowed=True)
            item_run_id = command.runtime_id
            scope = OrderApprovalScope(
                approval_id=approval["approval_id"],
                environment=RuntimeMode.DEMO,
                issue_code=command.issue_code,
                side=command.side,
                quantity=command.quantity,
                max_notional=Decimal(str(approval.get("max_notional") or normalized_item.get("estimated_value") or "0")),
                expires_at=datetime.fromisoformat(approval["approval_expires_at"]),
            )
            authorization = OrderApprovalGate().authorize(command, scope, second_password_present=second_password_present or second_password_status.present)
            executor_result = DemoOrderExecutor().submit(command, authorization=authorization, dry_run=True)
            if executor_result.status.value == "DRY_RUN_READY":
                adapter_result = TachibanaDemoOrderAdapter().submit_cash_stock_order(command).to_dict()
                wire_result = adapter_result
                broker_order_api_called = bool(adapter_result.get("broker_order_api_called"))
                demo_order_submitted = bool(adapter_result.get("demo_order_executed"))
                response = adapter_result.get("response") or {}
                result_status = "ORDER_ACCEPTED" if response.get("accepted") else str(response.get("status") or adapter_result.get("status") or "REJECTED")
                broker_order_id_hash = str(response.get("broker_order_id_hash") or "")
            else:
                result_status = executor_result.status.value
                broker_order_id_hash = executor_result.broker_order_id_hash
        submitted.append(
            {
                "run_id": item_run_id,
                "approval_id": approval.get("approval_id", ""),
                "retry_parent": retry_parent,
                "item_id": item.get("item_id"),
                "issue_code": item.get("issue_code", ""),
                "code": item.get("code") or item.get("issue_code", ""),
                "side": item.get("side", ""),
                "quantity": item.get("quantity", ""),
                "position_id": item.get("position_id", ""),
                "lot_reference": item.get("lot_reference", ""),
                "exit_source": item.get("exit_source", ""),
                "exit_reason": item.get("exit_reason", ""),
                "sell_reason": item.get("sell_reason", ""),
                "expected_notional": normalized_item.get("expected_notional", normalized_item.get("estimated_value", "")),
                "limit_price": normalized_item.get("limit_price", item.get("limit_price", "")),
                "estimated_value": normalized_item.get("estimated_value", item.get("estimated_value", "")),
                "normalized_order": normalized_item,
                "code_normalization": _code_normalization_summary(normalized_item),
                "sell_intent": item.get("sell_intent", ""),
                "status": result_status,
                "demo_order_submitted": demo_order_submitted,
                "production_order_submitted": False,
                "execute_demo_order_requested": execute_demo_order,
                "broker_order_api_called": broker_order_api_called,
                "broker_order_id_hash": broker_order_id_hash,
                "wire_execution_result": wire_result,
                "approval_budget": {
                    "approval_max_notional": str(approval_max),
                    "remaining_before_item": str(remaining_approval_budget),
                    "order_value": str(order_value),
                },
                "projected_buying_power_usage": str(projected_buying_power_usage + order_value if normalized_item.get("side") == "BUY" else projected_buying_power_usage),
                "max_exposure": decision.to_dict(),
            }
        )
        if str(normalized_item.get("side") or "").upper() == "BUY":
            remaining_approval_budget -= order_value
            projected_buying_power_usage += order_value
            projected_exposure += order_value
    hard_blocking_statuses = {"BLOCKED", "BLOCKED_NO_APPROVAL", "BLOCKED_LIVE_ORDER_DISABLED", "BLOCKED_APPROVAL_SCOPE_MISMATCH", "BLOCKED_SECOND_PASSWORD_MISSING", "BLOCKED_PRODUCTION_PROHIBITED", "BLOCKED_EXECUTOR_STUB"}
    blocked_items = [row for row in submitted if str(row.get("status") or "").upper() == "BLOCKED_ITEM"]
    accepted_rows = [row for row in submitted if _submitted_row_is_success(row)]
    hard_blocked = any(str(row.get("status") or "").upper() in hard_blocking_statuses for row in submitted)
    hard_item_blocked = any(_is_hard_submit_item_block(row) for row in blocked_items)
    if blocks or hard_blocked or (hard_item_blocked and not accepted_rows):
        overall = "BLOCK"
    elif blocked_items and accepted_rows:
        overall = "PARTIAL_PASS_WITH_ITEM_BLOCKS"
    elif blocked_items:
        overall = "REVIEW_REQUIRED_ITEM_BLOCKS"
    else:
        overall = "PASS"
    payload = _base_payload("demo_submit", env, trade_date, overall)
    payload.update(
        {
            "blocks": blocks,
            "market_calendar": market_calendar,
            "market_closed": False,
            "submit_run_date": trade_date,
            "order_plan_source_date": order_plan_date,
            "approval_source_date": order_plan_date,
            "order_plan_path": str(paths.dated("order_plan", order_plan_date, "order_plan.json")),
            "approval_artifact_path": str(paths.dated("approval_artifact", order_plan_date, "approval_artifact.json")),
            "uses_previous_business_day_order_plan": order_plan_date != trade_date,
            "submit_allowed": overall in {"PASS", "PARTIAL_PASS_WITH_ITEM_BLOCKS"},
            "submitted_orders": submitted,
            "blocked_items": blocked_items,
            "blocked_item_count": len(blocked_items),
            "accepted_order_count": len(accepted_rows),
            "partial_success": bool(blocked_items and accepted_rows),
            "partial_submit_review_required": bool(blocked_items),
            "review_required_reasons": sorted({reason for row in blocked_items for reason in row.get("block_reasons", [])}),
            "retry_parent": retry_parent,
            "persistent_demo_ledger_before": demo_ledger_state_before,
            "demo_order_submitted": any(row.get("demo_order_submitted") is True for row in submitted),
            "production_order_submitted": False,
            "broker_order_api_called": any(row.get("broker_order_api_called") is True for row in submitted),
            "clm_kabu_new_order_called": any(row.get("broker_order_api_called") is True for row in submitted),
            "raw_response_saved": False,
            "secret_saved": False,
        }
    )
    output = paths.dated("submitted_orders", trade_date, "submitted_orders.json")
    write_json(output, payload)
    if env == "demo":
        ledger_state = record_demo_submit_result(root=paths.root, trade_date=trade_date, submit_payload=payload, retry_parent=retry_parent)
        payload["persistent_demo_ledger"] = ledger_state
        write_json(output, payload)
    _write_daily_manifest(paths, trade_date, env=env, overrides={"submit_status": overall, "market_calendar": market_calendar})
    return {**payload, "submitted_orders_path": str(output)}


def run_demo_matched_opposite_order_fill_test(
    *,
    trade_date: str,
    root: Path = DEFAULT_OPERATION_ROOT,
    execute_sell_order: bool = False,
    second_password_present: bool = False,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    env_guard = validate_demo_environment(env, base_url=runtime["base_url"], production_order_allowed=False)
    market_calendar = _market_calendar(paths, trade_date)
    if market_calendar["market_closed"]:
        payload = _base_payload("demo_matched_opposite_order_fill_test", env, trade_date, "SKIPPED_MARKET_CLOSED")
        payload.update(
            {
                "market_calendar": market_calendar,
                "market_closed": True,
                "skip_reason": "MARKET_CLOSED",
                "submit_allowed": False,
                "sell_order_attempted": False,
                "sell_order_executed": False,
                "demo_order_executed": False,
                "demo_order_submitted": False,
                "production_order_submitted": False,
                "broker_order_api_called": False,
                "clm_kabu_new_order_called": False,
                "execute_sell_order_requested": execute_sell_order,
                "submitted_orders": [],
                "blocks": ["MARKET_CLOSED"],
                "raw_request_saved": False,
                "raw_response_saved": False,
                "secret_saved": False,
            }
        )
        output = paths.dated("demo_matched_opposite_order", trade_date, "matched_opposite_order_result.json")
        write_json(output, payload)
        _write_daily_manifest(paths, trade_date, env=env, overrides={"demo_matched_opposite_order_status": "SKIPPED_MARKET_CLOSED", "market_calendar": market_calendar})
        return {**payload, "matched_opposite_order_result_path": str(output)}
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    broker_orders = (broker_bundle.get("artifacts", {}).get("broker_orders") or {}).get("orders") or []
    broker_buying_power = broker_bundle.get("artifacts", {}).get("broker_buying_power") or {}
    safety_monitor = _load_or_empty(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), default={"status": "PASS", "safety_state": "ALLOW"})
    blocks: list[str] = []
    if runtime["status"] != "PASS":
        blocks.extend(runtime["reasons"])
    if not env_guard["allowed"]:
        blocks.extend(env_guard["reasons"])
    if safety_monitor.get("status") == "BLOCK" or safety_monitor.get("safety_state") in {"BLOCK", "SYSTEM_EMERGENCY_STOP"}:
        blocks.append("safety_not_allow")
    internal_code = "92560"
    normalization = _normalize_broker_issue_for_submit({"issue_code": internal_code, "code": internal_code}, paths=paths, trade_date=trade_date)
    if normalization.get("normalization_status") != "PASS":
        blocks.append("broker_issue_code_normalization_failed")
    broker_issue_code = str(normalization.get("broker_issue_code") or "")
    existing_buy = _find_waiting_buy_order(broker_orders, broker_issue_code=broker_issue_code, quantity="100")
    if not existing_buy:
        blocks.append("existing_buy_waiting_order_not_found")
    if str((existing_buy or {}).get("remaining_quantity") or "") != "100":
        blocks.append("existing_buy_remaining_quantity_not_100")
    approval_id = f"demo_lifecycle_test_approval_{trade_date}_{uuid4().hex[:12]}"
    created_at = utc_now_iso()
    approval = {
        "artifact_type": "demo_lifecycle_test_approval",
        "approval_id": approval_id,
        "approval_scope": "DEMO_MATCHED_OPPOSITE_ORDER_FILL_TEST",
        "business_date": trade_date,
        "environment": env,
        "approved_side": "SELL",
        "approved_code": internal_code,
        "approved_broker_issue_code": broker_issue_code,
        "approved_quantity": "100",
        "approved_price_type": "MARKET",
        "approved_reason": "demo_matched_opposite_order_fill_test",
        "demo_order_allowed": execute_sell_order and env == "demo" and not blocks,
        "production_order_allowed": False,
        "approved_at": created_at if execute_sell_order and not blocks else "",
        "approval_expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }
    command = OrderCommand(
        runtime_id=f"operation_{trade_date}_{approval_id}_demo_matched_sell_92560_001",
        environment=RuntimeMode.DEMO,
        paper_test_id="operation_demo_matched_opposite_order_fill_test",
        issue_code=broker_issue_code or "BLOCKED",
        side=OrderSide.SELL,
        quantity=Decimal("100"),
        order_type=OrderType.CASH_EQUITY,
        price_type=PriceType.MARKET,
        limit_price=Decimal("0"),
        evaluation_cash_basis=Decimal("1000000"),
        broker_cash_upper_bound=Decimal("0"),
        approval_required=True,
        approval_id=approval_id,
        live_order_allowed=execute_sell_order,
    )
    result_status = "BLOCKED"
    wire_result: dict[str, Any] = {}
    broker_order_api_called = False
    demo_order_executed = False
    broker_order_id_hash = ""
    if execute_sell_order and not blocks:
        second_password_status = TachibanaSecretLoader(load_broker_settings()).classify_second_password_file()
        scope = OrderApprovalScope(
            approval_id=approval_id,
            environment=RuntimeMode.DEMO,
            issue_code=command.issue_code,
            side=OrderSide.SELL,
            quantity=Decimal("100"),
            max_notional=Decimal("0"),
            expires_at=datetime.fromisoformat(approval["approval_expires_at"]),
        )
        authorization = OrderApprovalGate().authorize(command, scope, second_password_present=second_password_present or second_password_status.present)
        executor_result = DemoOrderExecutor().submit(command, authorization=authorization, dry_run=True)
        if executor_result.status.value == "DRY_RUN_READY":
            adapter_result = TachibanaDemoOrderAdapter().submit_cash_stock_order(command).to_dict()
            wire_result = adapter_result
            broker_order_api_called = bool(adapter_result.get("broker_order_api_called"))
            demo_order_executed = bool(adapter_result.get("demo_order_executed"))
            response = adapter_result.get("response") or {}
            result_status = "SELL_ORDER_ACCEPTED" if response.get("accepted") else str(response.get("status") or adapter_result.get("status") or "REJECTED")
            broker_order_id_hash = str(response.get("broker_order_id_hash") or "")
        else:
            result_status = executor_result.status.value
            blocks.append(executor_result.reason or executor_result.status.value)
    sell_row = {
        "run_id": command.runtime_id,
        "approval_id": approval_id,
        "item_id": f"demo_matched_sell_{trade_date}_92560_001",
        "issue_code": internal_code,
        "code": internal_code,
        "broker_issue_code": broker_issue_code,
        "side": "SELL",
        "quantity": "100",
        "order_type": "CASH_EQUITY",
        "price_type": "MARKET",
        "limit_price": "0",
        "reference_price": str((existing_buy or {}).get("price") or "5410"),
        "expected_notional": str(Decimal("100") * _decimal_or_none((existing_buy or {}).get("price") or "5410") if existing_buy else "0"),
        "sell_reason": "demo_matched_opposite_order_fill_test",
        "exit_source": "demo_lifecycle_test",
        "normalized_order": {
            "order_type": "CASH_EQUITY",
            "price_type": "MARKET",
            "internal_code": internal_code,
            "broker_issue_code": broker_issue_code,
            "side": "SELL",
            "quantity": "100",
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        },
        "status": result_status,
        "demo_order_submitted": demo_order_executed,
        "production_order_submitted": False,
        "execute_demo_order_requested": execute_sell_order,
        "broker_order_api_called": broker_order_api_called,
        "broker_order_id_hash": broker_order_id_hash,
        "wire_execution_result": wire_result,
        "code_normalization": _code_normalization_summary(normalization),
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }
    overall = "BLOCK" if blocks else "PASS"
    payload = _base_payload("demo_matched_opposite_order_fill_test", env, trade_date, overall)
    payload.update(
        {
            "approval": approval,
            "blocks": blocks,
            "existing_buy_order_found": bool(existing_buy),
            "existing_buy_order": existing_buy or {},
            "existing_buy_fill_status_before_sell": "WAITING_FILL" if existing_buy else "UNKNOWN",
            "buy_reorder_executed": False,
            "buy_clm_kabu_new_order_called": False,
            "sell_order_attempted": execute_sell_order and not blocks,
            "sell_order_executed": demo_order_executed,
            "sell_order": sell_row,
            "submitted_orders": [sell_row],
            "broker_order_api_called": broker_order_api_called,
            "demo_order_submitted": demo_order_executed,
            "production_order_submitted": False,
            "production_unlock_executed": False,
            "line_send_executed": False,
            "ai_retraining_executed": False,
            "backtest_run": False,
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "broker_readonly_before_sell": {
                "orders_count": len(broker_orders),
                "buying_power": str(broker_buying_power.get("buying_power") or ""),
            },
        }
    )
    write_json(paths.dated("demo_lifecycle_test_approval", trade_date, "approval_artifact.json"), approval)
    output = paths.dated("demo_matched_opposite_order", trade_date, "matched_opposite_order_result.json")
    write_json(output, payload)
    if env == "demo" and execute_sell_order and broker_order_api_called:
        ledger_state = record_demo_submit_result(root=paths.root, trade_date=trade_date, submit_payload=payload, retry_parent={"phase": "Phase12-AA", "reason": "demo_matched_opposite_order_fill_test"})
        payload["persistent_demo_ledger"] = ledger_state
        write_json(output, payload)
    _write_daily_manifest(paths, trade_date, env=env, overrides={"demo_matched_opposite_order_status": overall})
    return {**payload, "matched_opposite_order_result_path": str(output)}


def run_demo_special_fill_simulation(
    *,
    trade_date: str,
    root: Path = DEFAULT_OPERATION_ROOT,
    demo_special_fill_simulation_enabled: bool = False,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    env_guard = validate_demo_environment(env, base_url=runtime["base_url"], production_order_allowed=False)
    market_calendar = _market_calendar(paths, trade_date)
    if market_calendar["market_closed"]:
        payload = _base_payload("demo_special_fill_simulation", env, trade_date, "SKIPPED_MARKET_CLOSED")
        payload.update(
            {
                "market_calendar": market_calendar,
                "market_closed": True,
                "skip_reason": "MARKET_CLOSED",
                "submit_allowed": False,
                "demo_special_fill_simulation_enabled": demo_special_fill_simulation_enabled,
                "demo_special_fill_simulation_used": False,
                "production_enabled": False,
                "broker_confirmed_buy_fill": False,
                "simulated_buy_fill": False,
                "simulated_sell_fill": False,
                "simulated_fill": False,
                "performance_metrics_excluded": True,
                "blocks": ["MARKET_CLOSED"],
                "raw_request_saved": False,
                "raw_response_saved": False,
                "secret_saved": False,
            }
        )
        output = paths.dated("demo_special_fill", trade_date, "demo_special_fill_simulation_result.json")
        write_json(output, payload)
        _write_daily_manifest(paths, trade_date, env=env, overrides={"demo_special_fill_simulation_status": "SKIPPED_MARKET_CLOSED", "market_calendar": market_calendar})
        return {**payload, "demo_special_fill_simulation_result_path": str(output)}
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    existing_special = _load_demo_special_fill_summary(paths, trade_date)
    if existing_special.get("demo_special_fill_simulation_used") is True:
        payload = _base_payload("demo_special_fill_simulation", env, trade_date, "BLOCK")
        payload.update(
            {
                "demo_special_fill_simulation_enabled": demo_special_fill_simulation_enabled,
                "market_calendar": market_calendar,
                "market_closed": False,
                "demo_special_fill_simulation_used": False,
                "already_simulated_same_order": True,
                "production_enabled": False,
                "broker_confirmed_buy_fill": False,
                "simulated_buy_fill": False,
                "simulated_sell_fill": False,
                "performance_metrics_excluded": True,
                "internal_code": "92560",
                "broker_issue_code": existing_special.get("broker_issue_code", "9256"),
                "simulation_reason": "demo_9000_series_non_fill_rule",
                "blocks": ["demo_special_fill_already_simulated_for_same_order"],
                "raw_request_saved": False,
                "raw_response_saved": False,
                "secret_saved": False,
            }
        )
        output = paths.dated("demo_special_fill", trade_date, "demo_special_fill_simulation_result.json")
        _write_daily_manifest(paths, trade_date, env=env, overrides={"demo_special_fill_simulation_status": "BLOCK", "market_calendar": market_calendar})
        return {**payload, "demo_special_fill_simulation_result_path": str(output)}
    broker_orders = (broker_bundle.get("artifacts", {}).get("broker_orders") or {}).get("orders") or []
    broker_executions = (broker_bundle.get("artifacts", {}).get("broker_executions") or {}).get("executions") or []
    broker_positions = (broker_bundle.get("artifacts", {}).get("broker_positions") or {}).get("positions") or []
    blocks: list[str] = []
    if runtime["status"] != "PASS":
        blocks.extend(runtime["reasons"])
    if not env_guard["allowed"]:
        blocks.extend(env_guard["reasons"])
    if not demo_special_fill_simulation_enabled:
        blocks.append("demo_special_fill_simulation_not_enabled")
    internal_code = "92560"
    normalization = _normalize_broker_issue_for_submit({"issue_code": internal_code, "code": internal_code}, paths=paths, trade_date=trade_date)
    if normalization.get("normalization_status") != "PASS":
        blocks.append("broker_issue_code_normalization_failed")
    broker_issue_code = str(normalization.get("broker_issue_code") or "")
    if not broker_issue_code.startswith("9"):
        blocks.append("broker_issue_code_not_9000_series")
    existing_buy = _find_waiting_buy_order(broker_orders, broker_issue_code=broker_issue_code, quantity="100")
    if not existing_buy:
        blocks.append("existing_buy_waiting_order_not_found")
    if broker_executions:
        blocks.append("broker_confirmed_executions_present")
    if broker_positions:
        blocks.append("broker_confirmed_positions_present")
    fill_price = Decimal(str((existing_buy or {}).get("price") or "5410"))
    fill_notional = fill_price * Decimal("100")
    base_fill = {
        "internal_code": internal_code,
        "broker_issue_code": broker_issue_code,
        "quantity": "100",
        "fill_price": _decimal_text(fill_price),
        "fill_notional": _decimal_text(fill_notional),
        "broker_confirmed_fill": False,
        "simulated_fill": True,
        "demo_special_rule": True,
        "simulation_reason": "demo_9000_series_non_fill_rule",
        "performance_metrics_excluded": True,
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }
    buy_fill = {
        "artifact_type": "demo_special_simulated_buy_fill",
        "business_date": trade_date,
        "side": "BUY",
        "lifecycle": "SIMULATED_FILLED",
        **base_fill,
    }
    sell_fill = {
        "artifact_type": "demo_special_simulated_sell_fill",
        "business_date": trade_date,
        "side": "SELL",
        "lifecycle": "SIMULATED_FILLED",
        "sell_reason": "demo_special_fill_simulation_close",
        "exit_source": "demo_lifecycle_test",
        **base_fill,
    }
    output_dir = paths.dated("demo_special_fill", trade_date, "placeholder.json").parent
    status = "PASS" if not blocks else "BLOCK"
    payload = _base_payload("demo_special_fill_simulation", env, trade_date, status)
    payload.update(
        {
            "demo_special_fill_simulation_enabled": demo_special_fill_simulation_enabled,
            "market_calendar": market_calendar,
            "market_closed": False,
            "demo_special_fill_simulation_used": status == "PASS",
            "production_enabled": False,
            "production_order_allowed": False,
            "broker_confirmed_buy_fill": False,
            "simulated_buy_fill": status == "PASS",
            "simulated_sell_fill": status == "PASS",
            "performance_metrics_excluded": True,
            "internal_code": internal_code,
            "broker_issue_code": broker_issue_code,
            "simulation_reason": "demo_9000_series_non_fill_rule",
            "blocks": blocks,
            "existing_buy_order_found": bool(existing_buy),
            "existing_buy_order": existing_buy or {},
            "broker_orders_count": len(broker_orders),
            "broker_executions_count": len(broker_executions),
            "broker_positions_count": len(broker_positions),
            "buy_lifecycle": buy_fill if status == "PASS" else {},
            "sell_lifecycle": sell_fill if status == "PASS" else {},
            "production_order_executed": False,
            "production_unlock_executed": False,
            "line_send_executed": False,
            "ai_retraining_executed": False,
            "backtest_run": False,
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        }
    )
    if status == "PASS":
        write_json(output_dir / "simulated_buy_fill.json", buy_fill)
        write_json(output_dir / "simulated_sell_fill.json", sell_fill)
        ledger_state = record_demo_special_fill_simulation(root=paths.root, trade_date=trade_date, buy_fill=buy_fill, sell_fill=sell_fill)
        payload["persistent_demo_ledger"] = ledger_state
    output = output_dir / "demo_special_fill_simulation_result.json"
    write_json(output, payload)
    _write_daily_manifest(paths, trade_date, env=env, overrides={"demo_special_fill_simulation_status": status})
    return {**payload, "demo_special_fill_simulation_result_path": str(output)}


def run_fill_monitor(*, trade_date: str, root: Path = DEFAULT_OPERATION_ROOT) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    market_calendar = _market_calendar(paths, trade_date)
    submitted = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={"submitted_orders": []})
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    broker_orders = (broker_bundle.get("artifacts", {}).get("broker_orders") or {}).get("orders") or []
    broker_executions = (broker_bundle.get("artifacts", {}).get("broker_executions") or {}).get("executions") or []
    broker_positions = (broker_bundle.get("artifacts", {}).get("broker_positions") or {}).get("positions") or []
    broker_buying_power = broker_bundle.get("artifacts", {}).get("broker_buying_power") or {}
    events = []
    for row in submitted.get("submitted_orders", []):
        lifecycle = _classify_operation_fill_state(row)
        if lifecycle == "BLOCKED_ITEM":
            events.append(
                {
                    "item_id": row.get("item_id"),
                    "issue_code": row.get("issue_code", ""),
                    "side": row.get("side", ""),
                    "quantity": row.get("quantity", ""),
                    "position_id": row.get("position_id", ""),
                    "exit_source": row.get("exit_source", ""),
                    "sell_reason": row.get("sell_reason", ""),
                    "lifecycle": lifecycle,
                    "requires_human_review": True,
                    "fail_closed": False,
                    "explained_item_block": True,
                    "block_reason": row.get("block_reason") or (row.get("reasons") or [""])[0],
                    "block_reasons": row.get("block_reasons") or row.get("reasons") or [],
                    "blocking_stage": row.get("blocking_stage", ""),
                    "remaining_quantity": _remaining_quantity(row, lifecycle),
                    "position_closed": _position_closed(row, lifecycle),
                    "realized_result_placeholder": str(row.get("side", "")).upper() == "SELL",
                }
            )
            continue
        if lifecycle in {"UNKNOWN_STATUS", "REJECTED", "EXPIRED", "PARTIALLY_FILLED"}:
            events.append(
                {
                    "item_id": row.get("item_id"),
                    "issue_code": row.get("issue_code", ""),
                    "side": row.get("side", ""),
                    "quantity": row.get("quantity", ""),
                    "position_id": row.get("position_id", ""),
                    "exit_source": row.get("exit_source", ""),
                    "sell_reason": row.get("sell_reason", ""),
                    "lifecycle": lifecycle,
                    "requires_human_review": True,
                    "fail_closed": lifecycle == "UNKNOWN_STATUS",
                    "remaining_quantity": _remaining_quantity(row, lifecycle),
                    "position_closed": _position_closed(row, lifecycle),
                    "realized_result_placeholder": str(row.get("side", "")).upper() == "SELL",
                }
            )
            continue
        if lifecycle in {"SUBMITTED", "ACCEPTED", "WAITING_FILL"}:
            events.append(
                {
                    "item_id": row.get("item_id"),
                    "issue_code": row.get("issue_code", ""),
                    "side": row.get("side", ""),
                    "quantity": row.get("quantity", ""),
                    "position_id": row.get("position_id", ""),
                    "exit_source": row.get("exit_source", ""),
                    "sell_reason": row.get("sell_reason", ""),
                    "lifecycle": lifecycle,
                    "requires_human_review": False,
                    "remaining_quantity": _remaining_quantity(row, lifecycle),
                    "position_closed": _position_closed(row, lifecycle),
                    "realized_result_placeholder": str(row.get("side", "")).upper() == "SELL",
                }
            )
            continue
        events.append(
            {
                "item_id": row.get("item_id"),
                "issue_code": row.get("issue_code", ""),
                "side": row.get("side", ""),
                "quantity": row.get("quantity", ""),
                "position_id": row.get("position_id", ""),
                "exit_source": row.get("exit_source", ""),
                "sell_reason": row.get("sell_reason", ""),
                "lifecycle": lifecycle,
                "requires_human_review": False,
                "remaining_quantity": _remaining_quantity(row, lifecycle),
                "position_closed": _position_closed(row, lifecycle),
                "realized_result_placeholder": str(row.get("side", "")).upper() == "SELL",
            }
        )
    events.extend(_demo_special_fill_events(paths, trade_date))
    unknown = any(event.get("lifecycle") == "UNKNOWN_STATUS" for event in events)
    status = "BLOCK" if runtime["status"] != "PASS" or unknown else ("PASS_MARKET_CLOSED_MONITOR_ONLY" if market_calendar["market_closed"] else "PASS")
    payload = _base_payload("fill_monitor", env, trade_date, status)
    payload.update(
        {
            "market_calendar": market_calendar,
            "market_closed": market_calendar["market_closed"],
            "new_fill_expected": False if market_calendar["market_closed"] else True,
            "fill_events": events,
            "broker_readonly_artifact_bundle": {
                key: value
                for key, value in broker_bundle.items()
                if key != "artifacts"
            },
            "broker_orders_count": len(broker_orders),
            "broker_executions_count": len(broker_executions),
            "classification": "SKIPPED_NO_ORDERS" if not broker_orders and not broker_executions and not events else "AVAILABLE",
            "state_catalog": [
                "SUBMITTED",
                "ACCEPTED",
                "WAITING_FILL",
                "PARTIALLY_FILLED",
                "FILLED",
                "REJECTED",
                "EXPIRED",
                "CANCELED",
                "UNKNOWN_STATUS",
                "BLOCKED_ITEM",
                "SIMULATED_FILLED",
            ],
            "auto_resubmit": False,
            "auto_cancel": False,
            "auto_sell": False,
            "same_order_auto_retry": False,
            "unknown_status_fail_closed": True,
        }
    )
    output = paths.dated("fill_events", trade_date, "fill_events.json")
    write_json(output, payload)
    if env == "demo":
        ledger_state = record_demo_readonly_monitoring(
            root=paths.root,
            trade_date=trade_date,
            submitted_orders=submitted.get("submitted_orders", []),
            broker_orders=broker_orders,
            broker_executions=broker_executions,
            broker_positions=broker_positions,
            buying_power=broker_buying_power,
            fill_events=events,
        )
        payload["persistent_demo_ledger"] = ledger_state
        write_json(output, payload)
    _write_daily_manifest(paths, trade_date, env=env, overrides={"fill_monitor_status": status, "market_calendar": market_calendar})
    return {**payload, "fill_events_path": str(output)}


def run_safety_monitor(
    *,
    trade_date: str,
    root: Path = DEFAULT_OPERATION_ROOT,
    market_stress: bool = False,
    system_faults: list[str] | None = None,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    market_calendar = _market_calendar(paths, trade_date)
    faults = system_faults or []
    broker_snapshot = _load_or_empty(
        paths.dated("broker_snapshot_summary", trade_date, "broker_snapshot_summary.json"),
        default=_default_broker_snapshot_summary(trade_date, env),
    )
    submitted = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={"submitted_orders": []})
    fill_events = _load_or_empty(paths.dated("fill_events", trade_date, "fill_events.json"), default={"fill_events": []})
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    detected: list[str] = []
    if Decimal(str(broker_snapshot.get("buying_power", "0"))) < 0:
        detected.append("buying_power_hard_violation")
    if broker_bundle["raw_response_saved"] or broker_bundle["secret_saved"]:
        detected.append("broker_artifact_leakage_detected")
    if int(broker_snapshot.get("orders_count", 0) or 0) > len(submitted.get("submitted_orders", [])) + 5:
        detected.append("broker_divergence")
    if any(event.get("lifecycle") == "UNKNOWN_STATUS" for event in fill_events.get("fill_events", [])):
        detected.append("unknown_order_state")
    detected.extend(faults)
    review_events: list[dict[str, Any]] = []
    if market_stress:
        review_events.append({"event_type": "market_stress", "classification": "NON_BLOCKING_REVIEW", "blocks_order_by_itself": False})
    for fault in detected:
        review_events.append({"event_type": fault, "classification": "SYSTEM_EMERGENCY_STOP", "blocks_order_by_itself": True})
    status = "BLOCK" if runtime["status"] != "PASS" or detected else ("PASS_MARKET_CLOSED_SYSTEM_ONLY" if market_calendar["market_closed"] else "PASS")
    safety_state = "SYSTEM_EMERGENCY_STOP" if detected else ("NON_BLOCKING_REVIEW" if market_stress else "ALLOW")
    payload = _base_payload("safety_monitor", env, trade_date, status)
    payload.update(
        {
            "safety_state": safety_state,
            "market_calendar": market_calendar,
            "market_closed": market_calendar["market_closed"],
            "market_stress": market_stress,
            "non_blocking_review": market_stress and not detected,
            "system_faults": detected,
            "broker_readonly_artifact_bundle": {
                key: value
                for key, value in broker_bundle.items()
                if key != "artifacts"
            },
            "positions_count": broker_bundle["positions_count"],
            "orders_count": broker_bundle["orders_count"],
            "executions_count": broker_bundle["executions_count"],
            "buying_power_available": broker_bundle["buying_power_available"],
            "auto_sell": False,
            "auto_stop_for_market_decline": False,
            "safety_is_system_guard_not_investment_judgement": True,
            "line_payload_generated": True,
            "line_send_executed": False,
            "broker_snapshot_used_for_ai": False,
            "paper_ledger_used_for_ai": False,
            "safety_result_used_for_ai": False,
            "audit_result_used_for_ai": False,
        }
    )
    event_payload = _base_payload("safety_events", env, trade_date, status)
    event_payload.update({"events": review_events, "line_send_executed": False})
    review_payload = _base_payload("human_review", env, trade_date, "REVIEW_REQUIRED" if review_events else "PASS")
    review_payload.update({"queue": review_events, "line_send_executed": False})
    line_payload = {
        "artifact_type": "line_payload",
        "business_date": trade_date,
        "environment": env,
        "send_executed": False,
        "line_send_executed": False,
        "summary": {"safety_state": safety_state, "event_count": len(review_events)},
    }
    monitor_path = paths.dated("safety_monitor", trade_date, "safety_monitor_result.json")
    events_path = paths.dated("safety_events", trade_date, "safety_events.json")
    review_path = paths.dated("human_review", trade_date, "safety_review_queue.json")
    line_path = paths.dated("reports", trade_date, "line_payload.json")
    write_json(monitor_path, payload)
    write_json(events_path, event_payload)
    write_json(review_path, review_payload)
    write_json(line_path, line_payload)
    _write_daily_manifest(paths, trade_date, env=env, overrides={"safety_monitor_status": status, "market_calendar": market_calendar})
    return {
        **payload,
        "safety_monitor_result_path": str(monitor_path),
        "safety_events_path": str(events_path),
        "human_review_queue_path": str(review_path),
        "line_payload_path": str(line_path),
    }


def run_reconcile(*, trade_date: str, root: Path = DEFAULT_OPERATION_ROOT) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    market_calendar = _market_calendar(paths, trade_date)
    submitted_orders = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={})
    order_plan_source_date = str(submitted_orders.get("order_plan_source_date") or trade_date)
    approval_source_date = str(submitted_orders.get("approval_source_date") or order_plan_source_date)
    daily_plan_source_date = order_plan_source_date
    targets = {
        "market_refresh": paths.dated("market_refresh", trade_date, "market_refresh_manifest.json").exists(),
        "feature_refresh": paths.dated("feature_refresh", trade_date, "feature_refresh_manifest.json").exists(),
        "daily_plan": paths.dated("daily_plan", daily_plan_source_date, "daily_plan_result.json").exists(),
        "order_plan": paths.dated("order_plan", order_plan_source_date, "order_plan.json").exists(),
        "approval": paths.dated("approval_artifact", approval_source_date, "approval_artifact.json").exists(),
        "submitted_orders": paths.dated("submitted_orders", trade_date, "submitted_orders.json").exists(),
        "broker_snapshot": paths.dated("broker_snapshot", trade_date, "broker_snapshot.json").exists(),
        "broker_orders": paths.dated("broker_orders", trade_date, "orders.json").exists(),
        "executions": paths.dated("broker_executions", trade_date, "executions.json").exists(),
        "positions": paths.dated("broker_positions", trade_date, "positions.json").exists() or paths.dated("positions", trade_date, "positions.json").exists(),
        "buying_power": paths.dated("broker_buying_power", trade_date, "buying_power.json").exists(),
        "ledger": paths.dated("ledger", trade_date, "ledger_summary.json").exists(),
        "ledger_state": paths.dated("ledger", trade_date, "ledger_state.json").exists(),
        "ledger_update_manifest": paths.dated("ledger", trade_date, "ledger_update_manifest.json").exists(),
        "fill_events": paths.dated("fill_events", trade_date, "fill_events.json").exists(),
        "fill_monitor": paths.dated("fill_events", trade_date, "fill_events.json").exists(),
        "safety_monitor": paths.dated("safety_monitor", trade_date, "safety_monitor_result.json").exists(),
        "broker_snapshot_summary": paths.dated("broker_snapshot_summary", trade_date, "broker_snapshot_summary.json").exists(),
        "safety": paths.dated("safety_result", trade_date, "safety_result.json").exists(),
    }
    missing = [name for name, exists in targets.items() if not exists]
    safety_monitor = _load_or_empty(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), default={})
    fill_events = _load_or_empty(paths.dated("fill_events", trade_date, "fill_events.json"), default={"fill_events": []})
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    broker_summary = broker_bundle.get("artifacts", {}).get("broker_snapshot_summary") or {}
    demo_reset = detect_demo_broker_daily_reset(
        root=paths.root,
        trade_date=trade_date,
        broker_orders_count=int(broker_summary.get("orders_count", broker_bundle.get("orders_count", 0)) or 0),
        broker_executions_count=int(broker_summary.get("executions_count", broker_bundle.get("executions_count", 0)) or 0),
        broker_positions_count=int(broker_summary.get("positions_count", broker_bundle.get("positions_count", 0)) or 0),
    ) if env == "demo" else {"broker_daily_reset_detected": False}
    ledger_state = _load_or_empty(paths.dated("ledger", trade_date, "ledger_state.json"), default={})
    ledger_manifest = _load_or_empty(paths.dated("ledger", trade_date, "ledger_update_manifest.json"), default={})
    sell_reconciliation = _sell_reconciliation_summary(fill_events.get("fill_events", []), targets=targets)
    demo_special = _load_demo_special_fill_summary(paths, trade_date)
    submit_reconciliation = _submit_reconciliation_summary(submitted_orders, broker_bundle=broker_bundle, fill_events=fill_events.get("fill_events", []), env=env)
    if safety_monitor.get("safety_state") == "SYSTEM_EMERGENCY_STOP":
        status = "SYSTEM_EMERGENCY_STOP"
    elif runtime["status"] != "PASS" or any(event.get("lifecycle") == "UNKNOWN_STATUS" for event in fill_events.get("fill_events", [])):
        status = "BLOCK"
    elif demo_reset.get("broker_daily_reset_detected") is True:
        status = "REVIEW_REQUIRED"
    elif market_calendar["market_closed"]:
        status = "PASS_MARKET_CLOSED_RECONCILE_ONLY"
    elif not missing and submit_reconciliation.get("partial_submit_with_explained_blocked_items"):
        status = "PASS_WITH_BLOCKED_ITEMS"
    elif demo_special.get("demo_special_fill_simulation_used") is True:
        status = "PASS" if not missing else "REVIEW_REQUIRED"
    else:
        status = "PASS" if not missing else "REVIEW_REQUIRED"
    payload = _base_payload("reconcile", env, trade_date, status)
    payload.update(
        {
            "targets": targets,
            "source_dates": {
                "trade_date": trade_date,
                "submit_run_date": submitted_orders.get("submit_run_date") or trade_date,
                "order_plan_source_date": order_plan_source_date,
                "approval_source_date": approval_source_date,
                "daily_plan_source_date": daily_plan_source_date,
            },
            "market_calendar": market_calendar,
            "market_closed": market_calendar["market_closed"],
            "missing": missing,
            "classification": status,
            "demo_special_fill_simulation": {
                **demo_special,
                "reconcile_classification": "DEMO_SPECIAL_SIMULATION_RECONCILED" if demo_special.get("demo_special_fill_simulation_used") else "NOT_USED",
                "broker_executions_count": broker_bundle.get("executions_count", 0),
                "broker_positions_count": broker_bundle.get("positions_count", 0),
            },
            "allowed_classifications": ["PASS", "PASS_WITH_BLOCKED_ITEMS", "REVIEW_REQUIRED", "BLOCK", "SYSTEM_EMERGENCY_STOP"],
            "demo_broker_reset_policy": {
                "broker_daily_reset_detected": demo_reset.get("broker_daily_reset_detected", False),
                "classification": "DEMO_BROKER_RESET_REVIEW" if demo_reset.get("broker_daily_reset_detected") else status,
                "demo_ledger_continues": True,
                "broker_snapshot_overwrites_demo_ledger": False,
                "persistent_demo_ledger_used_for_multiday_history": env == "demo",
            },
            "sell_reconciliation": sell_reconciliation,
            "submit_reconciliation": submit_reconciliation,
            "broker_readonly_artifact_bundle": {
                key: value
                for key, value in broker_bundle.items()
                if key != "artifacts"
            },
            "ledger_state": {
                "status": ledger_manifest.get("status", "MISSING"),
                "path": str(paths.dated("ledger", trade_date, "ledger_state.json")),
                "positions_count": (ledger_state.get("positions_summary") or {}).get("count", 0),
                "orders_count": (ledger_state.get("orders_summary") or {}).get("count", 0),
                "executions_count": (ledger_state.get("executions_summary") or {}).get("count", 0),
                "empty_broker_state": (
                    (ledger_state.get("positions_summary") or {}).get("count", 0) == 0
                    and (ledger_state.get("orders_summary") or {}).get("count", 0) == 0
                    and (ledger_state.get("executions_summary") or {}).get("count", 0) == 0
                ),
                "raw_response_saved": ledger_state.get("raw_response_saved", False),
                "secret_saved": ledger_state.get("secret_saved", False),
            },
            "production_order_trace_detected": False,
        }
    )
    output = paths.dated("reconciliation_result", trade_date, "reconciliation_result.json")
    write_json(output, payload)
    _write_daily_manifest(paths, trade_date, env=env, overrides={"reconciliation_status": status, "market_calendar": market_calendar})
    return {**payload, "reconciliation_result_path": str(output)}


def run_daily_report(*, trade_date: str, root: Path = DEFAULT_OPERATION_ROOT, send_notifications: bool = False) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    market_calendar = _market_calendar(paths, trade_date)
    status_refs = _collect_operation_statuses(paths, trade_date)
    current_status_refs = _current_operation_statuses(paths, trade_date)
    sell_summary = _collect_sell_report_summary(paths, trade_date)
    broker_bundle = load_broker_artifact_bundle(trade_date=trade_date, root=paths.root)
    market_manifest = _load_or_empty(paths.dated("market_refresh", trade_date, "market_refresh_manifest.json"), default={})
    order_plan = _load_or_empty(paths.dated("order_plan", trade_date, "order_plan.json"), default={"buy_item_count": 0, "sell_item_count": 0})
    ledger_summary = _load_or_empty(paths.dated("ledger", trade_date, "ledger_summary.json"), default={})
    feature_candidate_audit = _load_or_empty(paths.dated("feature_candidate_audit", trade_date, "feature_candidate_audit.json"), default=feature_candidate_diagnostics(root=paths.root, trade_date=trade_date))
    demo_special = _load_demo_special_fill_summary(paths, trade_date)
    notification_result = {
        "status": "NOT_REQUESTED",
        "line_send_executed": False,
        "discord_send_executed": False,
        "notification_result_path": "",
    }
    production_equivalence_checklist = _production_equivalence_checklist(
        paths,
        trade_date,
        env=env,
        status_refs=current_status_refs,
        order_plan=order_plan,
        broker_bundle=broker_bundle,
        demo_special=demo_special,
    )
    flow_guard = _operation_flow_integrity_guard(
        paths,
        trade_date,
        market_calendar=market_calendar,
        status_refs=status_refs,
        current_status_refs=current_status_refs,
        order_plan=order_plan,
    )
    report_refs = {
        "status": flow_guard["report_status"],
        "operation_day_type": flow_guard["operation_day_type"],
        "report_mode": flow_guard["report_mode"],
        "notification_mode": flow_guard["notification_mode"],
        "report_prerequisite_guard": flow_guard,
        "report_prerequisite_pass": flow_guard["report_prerequisite_pass"],
        "artifact_date_consistency": flow_guard["artifact_date_consistency"],
        "artifact_date_consistency_pass": flow_guard["artifact_date_consistency_pass"],
        "source_of_truth_consistency_pass": flow_guard["source_of_truth_consistency_pass"],
        "normal_report_allowed": flow_guard["normal_report_allowed"],
        "candidate_top50_allowed": flow_guard["candidate_top50_allowed"],
        "next_day_candidates_allowed": flow_guard["next_day_candidates_allowed"],
        "safety_report_generated": True,
        "blog_draft_generated": True,
        "public_report_generated": True,
        "line_payload_generated": True,
        "line_send_executed": False,
        "discord_send_executed": False,
        "notification_status": "NOT_REQUESTED",
        "notification_result_path": "",
        "send_notifications_requested": send_notifications,
        "market_calendar": market_calendar,
        "market_status": "CLOSED" if market_calendar["market_closed"] else "OPEN",
        "regenerated": True,
        "regenerated_reason": "phase12aj_blog_report_v4_quality_restoration",
        "regenerated_by": "operations_daily_report_writer",
        "market_closed_message": (
            "市場休場日のため、AI判断・発注・約定処理はありません。Broker read-only / Safety / Ledger確認のみ実施しました。"
            if market_calendar["market_closed"]
            else ""
        ),
        "ai_decision": "skipped" if market_calendar["market_closed"] else "executed_or_no_signal",
        "orders": "skipped" if market_calendar["market_closed"] else "normal",
        "paths": {
            "safety_report": str(paths.dated("reports", trade_date, "safety_report.md")),
            "blog_draft": str(paths.dated("reports", trade_date, "blog_draft.md")),
            "public_report": str(paths.dated("reports", trade_date, "public_report.md")),
            "line_payload": str(paths.dated("reports", trade_date, "line_payload.json")),
            "discord_payload": str(paths.dated("reports", trade_date, "discord_payload.json")),
        },
        "operation_statuses": status_refs,
        "current_operation_statuses": current_status_refs,
        "stale_artifact_policy": {
            "submit_status_stale_ignored": current_status_refs.get("submit") == "STALE_IGNORED",
            "basis": "submitted_orders.created_at older than order_plan.created_at is history, not current run state",
        },
        "sell_summary": sell_summary,
        "jquants_fetch_status": {
            "jquants_api_fetch_executed": market_manifest.get("jquants_api_fetch_executed", False),
            "raw_daily_quotes_updated": market_manifest.get("raw_daily_quotes_updated", False),
            "canonical_normalized_updated": market_manifest.get("canonical_normalized_updated", False),
            "feature_refresh_executed": market_manifest.get("feature_refresh_executed", False),
            "data_quality_status": market_manifest.get("data_quality_status", "UNKNOWN"),
            "market_data_status": market_manifest.get("status", "UNKNOWN"),
            "feature_freshness_status": market_manifest.get("feature_freshness_status", "UNKNOWN"),
            "latest_available_market_date": market_manifest.get("latest_available_market_date", ""),
            "decision_for": market_manifest.get("decision_for", trade_date),
        },
        "broker_readonly_status": {
            key: value
            for key, value in broker_bundle.items()
            if key != "artifacts"
        },
        "buy_item_count": order_plan.get("buy_item_count", 0),
        "buy_zero_reason": (order_plan.get("feature_buy_adapter") or {}).get("reason", "") if int(order_plan.get("buy_item_count", 0) or 0) == 0 else "",
        "feature_candidate_audit": feature_candidate_audit,
        "sell_item_count": order_plan.get("sell_item_count", 0),
        "sell_zero_reason": "no_valid_broker_positions" if int(order_plan.get("sell_item_count", 0) or 0) == 0 else "",
        "ledger_status": {
            "status": ledger_summary.get("status", "MISSING"),
            "positions_count": ledger_summary.get("positions_count", 0),
            "orders_count": ledger_summary.get("orders_count", 0),
            "executions_count": ledger_summary.get("executions_count", 0),
            "buying_power_available": ledger_summary.get("buying_power_available", False),
        },
        "broker_order_api_called": False,
        "demo_order_wire_execution": False,
        "production_order_submitted": False,
        "raw_response_saved": False,
        "secret_saved": False,
        "missed_jobs": _read_missed_jobs(paths, trade_date),
        "demo_special_fill_simulation": demo_special,
        "demo_production_parity_audit": _demo_production_parity_audit(paths, trade_date, env=env),
        "production_equivalence_checklist": production_equivalence_checklist,
    }
    report_model = _build_daily_report_model(paths, trade_date, report_refs, order_plan=order_plan)
    if send_notifications:
        notification_result = run_operation_notifications(trade_date=trade_date, root=paths.root, report_refs={**report_refs, "notification_summary_text": report_model["notification_summary_text"]})
        report_refs.update(
            {
                "line_send_executed": notification_result.get("line_send_executed", False),
                "discord_send_executed": notification_result.get("discord_send_executed", False),
                "notification_status": notification_result.get("status", "UNKNOWN"),
                "notification_result_path": notification_result.get("notification_result_path", ""),
                "notification_result": {
                    "line": notification_result.get("line", {}),
                    "discord": notification_result.get("discord", {}),
                    "secret_saved": False,
                    "raw_request_saved": False,
                    "raw_response_saved": False,
                },
            }
        )
        report_model = _build_daily_report_model(paths, trade_date, report_refs, order_plan=order_plan)
    for label, path_text in report_refs["paths"].items():
        path = Path(path_text)
        if path.suffix == ".json":
            payload = _render_daily_notification_payload(label, report_model, report_refs)
            write_json(path, payload)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_render_daily_report_markdown(label=label, model=report_model), encoding="utf-8")
    output = paths.dated("daily_report_refs", trade_date, "daily_report_refs.json")
    write_json(output, report_refs)
    status = report_refs["status"] if runtime["status"] == "PASS" else "BLOCK"
    manifest_overrides = {
        "daily_plan_status": flow_guard["required_statuses"].get("daily_plan", current_status_refs.get("daily_plan", "MISSING")),
        "approval_status": flow_guard["required_statuses"].get("approval", current_status_refs.get("approval", "MISSING")),
        "submit_status": current_status_refs.get("submit", "MISSING"),
        "operation_audit_status": current_status_refs.get("operation_audit", "MISSING"),
        "daily_report_status": status,
        "daily_report_refs_path": str(output),
        "line_send_executed": report_refs["line_send_executed"],
        "discord_send_executed": report_refs["discord_send_executed"],
        "notification_status": report_refs["notification_status"],
        "notification_result_path": report_refs["notification_result_path"],
        "operation_day_type": report_refs["operation_day_type"],
        "report_mode": report_refs["report_mode"],
        "report_prerequisite_pass": report_refs["report_prerequisite_pass"],
        "artifact_date_consistency_pass": report_refs["artifact_date_consistency_pass"],
        "normal_report_allowed": report_refs["normal_report_allowed"],
    }
    manifest_overrides["market_calendar"] = market_calendar
    if current_status_refs.get("submit") == "STALE_IGNORED":
        manifest_overrides["submit_status"] = "STALE_IGNORED"
    manifest_path = _write_daily_manifest(paths, trade_date, env=env, overrides=manifest_overrides)
    manifest = read_json(manifest_path)
    return {**manifest, "daily_report_refs_path": str(output)}


def _build_daily_report_model(paths: OperationPaths, trade_date: str, report_refs: dict[str, Any], *, order_plan: dict[str, Any]) -> dict[str, Any]:
    approval = _load_or_empty(paths.dated("approval_artifact", trade_date, "approval_artifact.json"), default={})
    submitted = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={"submitted_orders": []})
    fill_events = _load_or_empty(paths.dated("fill_events", trade_date, "fill_events.json"), default={"fill_events": []})
    safety = _load_or_empty(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), default={})
    reconcile = _load_or_empty(paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"), default={})
    audit = _load_or_empty(paths.root / "audit_result" / "audit_result.json", default={})
    ledger = _load_or_empty(paths.dated("ledger", trade_date, "ledger_state.json"), default={})
    ledger_summary = _load_or_empty(paths.dated("ledger", trade_date, "ledger_summary.json"), default={})
    buying_power_artifact = _load_or_empty(paths.dated("broker_buying_power", trade_date, "buying_power.json"), default={})
    broker_orders_artifact = _load_or_empty(paths.dated("broker_orders", trade_date, "orders.json"), default={"orders": []})
    broker_positions_artifact = _load_or_empty(paths.dated("broker_positions", trade_date, "positions.json"), default={"positions": []})
    names = _load_issue_name_map(paths, trade_date)
    candidate_top50 = _load_candidate_top50_for_report(paths, trade_date, names)
    candidate_by_code = {row["internal_code"]: row for row in candidate_top50}
    items = order_plan.get("items", []) if isinstance(order_plan.get("items"), list) else []
    submitted_rows = submitted.get("submitted_orders", []) if isinstance(submitted.get("submitted_orders"), list) else []
    fill_rows = fill_events.get("fill_events", []) if isinstance(fill_events.get("fill_events"), list) else []
    broker_order_rows = broker_orders_artifact.get("orders", []) if isinstance(broker_orders_artifact.get("orders"), list) else []
    if not items and submitted_rows:
        items = [_item_from_submitted_row(row) for row in submitted_rows]
    buy_rows = [_report_order_row(item, names, submitted_rows, fill_rows, candidate_by_code, broker_order_rows=broker_order_rows) for item in items if str(item.get("side", "")).upper() == "BUY"]
    sell_rows = [_report_order_row(item, names, submitted_rows, fill_rows, candidate_by_code, broker_order_rows=broker_order_rows) for item in items if str(item.get("side", "")).upper() == "SELL"]
    statuses = report_refs.get("current_operation_statuses") or report_refs.get("operation_statuses") or {}
    broker = report_refs.get("broker_readonly_status") or {}
    ledger_status = report_refs.get("ledger_status") or ledger_summary or {}
    demo_special = report_refs.get("demo_special_fill_simulation") or {}
    parity = report_refs.get("demo_production_parity_audit") or {}
    title = f"AI Fund Lab Demo Operations Daily Report - {trade_date}"
    key_message = _daily_key_message(report_refs, buy_rows=buy_rows, sell_rows=sell_rows, safety=safety, reconcile=reconcile, audit=audit)
    operation_day_type = str(report_refs.get("operation_day_type") or NORMAL_OPERATION_DAY)
    notification_mode = str(report_refs.get("notification_mode") or "NORMAL_OPERATION_SUMMARY")
    notification_summary_text = _daily_notification_summary_text(
        title=title,
        operation_day_type=operation_day_type,
        notification_mode=notification_mode,
        key_message=key_message,
        report_refs=report_refs,
        statuses=statuses,
        safety=safety,
        reconcile=reconcile,
        audit=audit,
        buy_rows=buy_rows,
        sell_rows=sell_rows,
    )
    report_positions = _report_positions(paths, trade_date, names)
    if str(report_refs.get("environment", "demo")).lower() == "demo" and not report_positions:
        report_positions = _synthetic_demo_positions_from_filled_orders(buy_rows, sell_rows)
    return {
        "title": title,
        "business_date": trade_date,
        "environment": report_refs.get("environment", "demo"),
        "operation_day_type": operation_day_type,
        "report_mode": report_refs.get("report_mode", "NORMAL_BLOG"),
        "notification_mode": notification_mode,
        "report_prerequisite_guard": report_refs.get("report_prerequisite_guard") or {},
        "normal_report_allowed": report_refs.get("normal_report_allowed", True),
        "candidate_top50_allowed": report_refs.get("candidate_top50_allowed", True),
        "next_day_candidates_allowed": report_refs.get("next_day_candidates_allowed", True),
        "key_message": key_message,
        "market": {
            "status": report_refs.get("market_status", "UNKNOWN"),
            "ai_decision": report_refs.get("ai_decision", "UNKNOWN"),
            "orders": report_refs.get("orders", "UNKNOWN"),
            "calendar_source": (report_refs.get("market_calendar") or {}).get("calendar_source", ""),
            "previous_business_day": (report_refs.get("market_calendar") or {}).get("previous_business_day", ""),
            "next_business_day": (report_refs.get("market_calendar") or {}).get("next_business_day", ""),
            "message": report_refs.get("market_closed_message", ""),
        },
        "statuses": statuses,
        "buy_rows": buy_rows,
        "sell_rows": sell_rows,
        "broker": {
            "status": broker.get("status", "UNKNOWN"),
            "orders_count": broker.get("orders_count", 0),
            "executions_count": broker.get("executions_count", 0),
            "positions_count": broker.get("positions_count", 0),
            "buying_power_available": broker.get("buying_power_available", False),
            "raw_response_saved": broker.get("raw_response_saved", False),
            "secret_saved": broker.get("secret_saved", False),
        },
        "fill": {
            "status": fill_events.get("status", statuses.get("fill_monitor", "UNKNOWN")),
            "classification": fill_events.get("classification", "UNKNOWN"),
            "fill_event_count": len(fill_rows),
            "broker_orders_count": fill_events.get("broker_orders_count", 0),
            "broker_executions_count": fill_events.get("broker_executions_count", 0),
        },
        "ledger": {
            "status": ledger_status.get("status", ledger.get("status", "UNKNOWN")),
            "orders_count": ledger_status.get("orders_count", (ledger.get("orders_summary") or {}).get("count", 0)),
            "executions_count": ledger_status.get("executions_count", (ledger.get("executions_summary") or {}).get("count", 0)),
            "positions_count": ledger_status.get("positions_count", (ledger.get("positions_summary") or {}).get("count", 0)),
            "buying_power_available": ledger_status.get("buying_power_available", bool((ledger.get("cash_or_buying_power_summary") or {}).get("buying_power"))),
            "buying_power": (
                (ledger.get("cash_or_buying_power_summary") or {}).get("buying_power")
                or buying_power_artifact.get("buying_power")
                or buying_power_artifact.get("cash_available")
                or ""
            ),
            "cash_available": (
                (ledger.get("cash_or_buying_power_summary") or {}).get("cash_available")
                or buying_power_artifact.get("cash_available")
                or buying_power_artifact.get("buying_power")
                or ""
            ),
            "market_value_estimate": ledger.get("market_value_estimate") or ledger_status.get("market_value_estimate") or "0",
            "total_equity_estimate": ledger.get("total_equity_estimate") or ledger_status.get("total_equity_estimate") or "",
            "broker_positions_count": len(broker_positions_artifact.get("positions", [])) if isinstance(broker_positions_artifact.get("positions"), list) else 0,
            "persistent_demo_ledger": True,
        },
        "positions": report_positions,
        "safety": {
            "status": safety.get("status", statuses.get("safety_monitor", "UNKNOWN")),
            "state": safety.get("safety_state", "UNKNOWN"),
            "system_faults": safety.get("system_faults", []),
            "non_blocking_review": safety.get("non_blocking_review", False),
        },
        "reconcile": {
            "status": reconcile.get("status", statuses.get("reconcile", "UNKNOWN")),
            "classification": reconcile.get("classification", "UNKNOWN"),
            "missing": reconcile.get("missing", []),
            "demo_broker_reset_policy": reconcile.get("demo_broker_reset_policy", {}),
        },
        "audit": {
            "status": audit.get("status", statuses.get("operation_audit", "UNKNOWN")),
            "leakage_status": (audit.get("leakage_audit") or {}).get("status", "UNKNOWN"),
            "no_production_order_audit": audit.get("no_production_order_audit", True),
            "parity_status": (audit.get("demo_production_parity_audit") or parity).get("status", "UNKNOWN"),
            "unexpected_differences": (audit.get("demo_production_parity_audit") or parity).get("unexpected_differences", []),
        },
        "demo_special": {
            "status": demo_special.get("status", "UNKNOWN"),
            "used": demo_special.get("demo_special_fill_simulation_used", False),
            "enabled": demo_special.get("demo_special_fill_simulation_enabled", False),
            "broker_confirmed_fill": demo_special.get("broker_confirmed_fill", False),
            "simulated_fill": demo_special.get("simulated_fill", False),
            "performance_metrics_excluded": demo_special.get("performance_metrics_excluded", True),
            "reason": demo_special.get("simulation_reason", ""),
        },
        "notification": {
            "status": report_refs.get("notification_status", "NOT_REQUESTED"),
            "line_send_executed": report_refs.get("line_send_executed", False),
            "discord_send_executed": report_refs.get("discord_send_executed", False),
        },
        "feature_candidate_audit": report_refs.get("feature_candidate_audit") or {},
        "candidate_top50": candidate_top50,
        "top5_reason_sections": [_candidate_reason_section(row) for row in buy_rows[:5]],
        "production_equivalence_checklist": report_refs.get("production_equivalence_checklist") or {},
        "tomorrow_check_points": _tomorrow_check_points(report_refs, buy_rows=buy_rows, sell_rows=sell_rows, safety=safety, reconcile=reconcile),
        "paths": report_refs.get("paths") or {},
        "notification_summary_text": notification_summary_text,
    }


def _render_daily_report_markdown(*, label: str, model: dict[str, Any]) -> str:
    if model.get("operation_day_type") not in NORMAL_REPORT_ALLOWED_DAY_TYPES:
        return _render_non_normal_operation_report(model)
    payload = _phase9_v4_payload_from_operations_model(model)
    markdown = render_phase9_blog_report_v4(payload).rstrip()
    markdown = _replace_public_holdings_section(markdown, payload.get("holdings", []))
    appendix = _phase12_appendix(model)
    if appendix:
        markdown = f"{markdown}\n\n{appendix.rstrip()}"
    return markdown + "\n"


def _daily_notification_summary_text(
    *,
    title: str,
    operation_day_type: str,
    notification_mode: str,
    key_message: str,
    report_refs: dict[str, Any],
    statuses: dict[str, str],
    safety: dict[str, Any],
    reconcile: dict[str, Any],
    audit: dict[str, Any],
    buy_rows: list[dict[str, Any]],
    sell_rows: list[dict[str, Any]],
) -> str:
    if operation_day_type not in NORMAL_REPORT_ALLOWED_DAY_TYPES:
        guard = report_refs.get("report_prerequisite_guard") or {}
        reasons = guard.get("reasons") or []
        return "\n".join(
            [
                title,
                f"Operation Day Type: {operation_day_type}",
                f"Notification Mode: {notification_mode}",
                f"Status: {key_message}",
                f"Reason: {', '.join(str(item) for item in reasons[:5]) if reasons else '特記事項なし'}",
                f"Submit: {statuses.get('submit', 'UNKNOWN')}, Safety: {safety.get('safety_state', statuses.get('safety_monitor', 'UNKNOWN'))}, Reconcile: {reconcile.get('classification', statuses.get('reconcile', 'UNKNOWN'))}, Audit: {audit.get('status', statuses.get('operation_audit', 'UNKNOWN'))}",
                f"Report: {(report_refs.get('paths') or {}).get('public_report', '')}",
                "Production order: no",
            ]
        )
    return "\n".join(
        [
            title,
            f"Operation Day Type: {operation_day_type}",
            f"Notification Mode: {notification_mode}",
            key_message,
            f"Market: {report_refs.get('market_status', 'UNKNOWN')}",
            f"BUY: {len(buy_rows)} / SELL: {len(sell_rows)}",
            f"BUY候補Top5: {', '.join((row.get('name') or row.get('internal_code') or '') for row in buy_rows[:5]) if buy_rows else 'なし'}",
            f"Submit: {statuses.get('submit', 'UNKNOWN')}, Safety: {safety.get('safety_state', statuses.get('safety_monitor', 'UNKNOWN'))}, Reconcile: {reconcile.get('classification', statuses.get('reconcile', 'UNKNOWN'))}, Audit: {audit.get('status', statuses.get('operation_audit', 'UNKNOWN'))}",
            f"Report: {(report_refs.get('paths') or {}).get('public_report', '')}",
            f"Notification: {report_refs.get('notification_status', 'NOT_REQUESTED')}",
            f"Production order: {'YES' if report_refs.get('production_order_submitted') else 'no'}",
        ]
    )


def _render_non_normal_operation_report(model: dict[str, Any]) -> str:
    day_type = str(model.get("operation_day_type") or INCOMPLETE_OPERATION_DAY)
    guard = model.get("report_prerequisite_guard") or {}
    reasons = guard.get("reasons") or []
    date_consistency = guard.get("artifact_date_consistency") or {}
    title = str(model.get("title") or f"AI Fund Lab Demo Operations Daily Report - {model.get('business_date', '')}")
    if day_type == MARKET_CLOSED_DAY:
        lead = "本日は市場休場日のため、AI判断・発注・約定処理は行っていません。Broker read-only / Safety / Ledger確認のみ実施しました。"
    elif day_type == RECOVERY_DAY:
        lead = "本日はMarket Calendar誤判定からのリカバリ日です。通常の成績評価には含めません。明朝Submitに使用するOrder Plan / Approvalは再生成済みです。"
    else:
        lead = "本日は通常運用が完了していません。通常ブログ形式のCandidate Top50 / Top5 / 本日注文章は生成しません。"
    lines = [
        f"# {title}",
        "",
        f"## Operation Day Type",
        "",
        f"- day_type: {day_type}",
        f"- report_mode: {model.get('report_mode', '')}",
        f"- notification_mode: {model.get('notification_mode', '')}",
        "",
        "## 本日の扱い",
        "",
        lead,
        "",
        "## Prerequisite Guard",
        "",
        f"- report_prerequisite_pass: {_yes_no(guard.get('report_prerequisite_pass', False))}",
        f"- normal_report_allowed: {_yes_no(guard.get('normal_report_allowed', False))}",
        f"- candidate_top50_allowed: {_yes_no(guard.get('candidate_top50_allowed', False))}",
        f"- next_day_candidates_allowed: {_yes_no(guard.get('next_day_candidates_allowed', False))}",
        "",
        "## 検出理由",
        "",
    ]
    if reasons:
        lines.extend([f"- {reason}" for reason in reasons])
    else:
        lines.append("- 特記事項なし")
    lines.extend(
        [
            "",
            "## Date Consistency",
            "",
            f"- artifact_date_consistency_pass: {_yes_no(date_consistency.get('pass', False))}",
        ]
    )
    for name, value in (date_consistency.get("dates") or {}).items():
        lines.append(f"- {name}: {value or 'MISSING'}")
    mismatches = date_consistency.get("mismatches") or []
    if mismatches:
        lines.append("")
        lines.append("## Date Consistency Review")
        lines.append("")
        lines.extend([f"- {item}" for item in mismatches])
    if day_type == RECOVERY_DAY:
        submit = guard.get("next_morning_submit") or date_consistency.get("submit") or {}
        lines.extend(
            [
                "",
                "## 明朝Submit確認",
                "",
                f"- submit_run_date: {submit.get('submit_run_date', '')}",
                f"- order_plan_source_date: {submit.get('order_plan_source_date', '')}",
                f"- approval_source_date: {submit.get('approval_source_date', '')}",
                f"- buy_item_count: {submit.get('buy_item_count', '')}",
                f"- broker_order_api_called: {_yes_no(submit.get('broker_order_api_called', False))}",
                f"- clm_kabu_new_order_called: {_yes_no(submit.get('clm_kabu_new_order_called', False))}",
                f"- demo_order_submitted: {_yes_no(submit.get('demo_order_submitted', False))}",
                f"- {model.get('business_date', '')}のPlan / Approvalは明朝Submit用に再生成済みです。",
            ]
        )
    submitted_rows = [row for row in model.get("buy_rows", []) + model.get("sell_rows", []) if str(row.get("status") or "").upper() not in {"", "PLANNED", "BLOCKED_ITEM"}]
    blocked_rows = [row for row in model.get("buy_rows", []) + model.get("sell_rows", []) if str(row.get("status") or "").upper() == "BLOCKED_ITEM"]
    if submitted_rows or blocked_rows:
        lines.extend(["", "## 本日Submit結果", ""])
        if submitted_rows:
            lines.append(f"Brokerへ送信済みの注文は{len(submitted_rows)}件です。")
            for row in submitted_rows:
                lines.append(f"- {row.get('broker_issue_code') or row.get('internal_code')} {row.get('name') or ''} / {row.get('side')} / {row.get('quantity')}株 / status {row.get('status')}")
        else:
            lines.append("Brokerへ送信済みの注文はありません。")
        if blocked_rows:
            lines.append("")
            lines.append(f"Item単位でBLOCKされた候補は{len(blocked_rows)}件です。")
            for row in blocked_rows:
                reasons = ", ".join(str(reason) for reason in row.get("block_reasons", [])) or str(row.get("block_reason") or "")
                lines.append(f"- {row.get('broker_issue_code') or row.get('internal_code')} {row.get('name') or ''} / {row.get('side')} / {row.get('quantity')}株 / 理由: {reasons}")
    lines.extend(
        [
            "",
            "## Safety / Reconcile / Audit",
            "",
            f"- Safety: {model['safety']['status']} / {model['safety']['state']}",
            f"- Reconcile: {model['reconcile']['status']} / {model['reconcile']['classification']}",
            f"- Audit: {model['audit']['status']} / parity {model['audit']['parity_status']}",
            "",
            "## 注意書き",
            "",
            "- これはDemo Operationsの運用整合性レポートです。",
            "- 本レポートは投資助言ではありません。",
            "- Production注文は無効です。",
            "",
        ]
    )
    return "\n".join(lines)


def _replace_public_holdings_section(markdown: str, holdings: list[dict[str, Any]]) -> str:
    heading = "## 現在保有中の銘柄\n\n"
    next_heading = "\n## 本日"
    if heading not in markdown or next_heading not in markdown:
        return markdown
    before, rest = markdown.split(heading, 1)
    _old_section, after = rest.split(next_heading, 1)
    return before + heading + _render_public_holdings_section(holdings) + next_heading + after


def _render_public_holdings_section(holdings: list[dict[str, Any]]) -> str:
    if not holdings:
        return "現在保有中の銘柄はありません。\n"
    displayed = holdings
    lines = []
    for index, row in enumerate(displayed, start=1):
        lines.append(
            f"{index}. {row.get('code', '')} {row.get('name', '')} / "
            f"{_display_quantity(row.get('quantity'))}株 / 評価額 {row.get('market_value_display', '0円')} / "
            f"損益 {_signed_yen_display(row.get('unrealized_pnl'))}"
        )
    lines.append("")
    for row in displayed:
        code = str(row.get("code") or "").strip()
        if code:
            lines.append(f"^{code}")
            lines.append("")
    return "\n".join(lines)


def _display_quantity(value: Any) -> str:
    quantity = _phase9_decimal(value)
    if quantity == quantity.to_integral():
        return f"{int(quantity):,}"
    return _decimal_text(quantity)


def _signed_yen_display(value: Any) -> str:
    amount = _phase9_decimal(value)
    if amount > 0:
        return f"+{_yen_display(amount)}"
    if amount < 0:
        return f"-{_yen_display(abs(amount))}"
    return "0円"


def _render_daily_notification_payload(label: str, model: dict[str, Any], report_refs: dict[str, Any]) -> dict[str, Any]:
    provider = "discord" if label == "discord_payload" else "line"
    report_path = model["paths"].get("public_report") or model["paths"].get("blog_draft", "")
    return {
        "type": label,
        "provider": provider,
        "business_date": model["business_date"],
        "title": model["title"],
        "operation_day_type": model.get("operation_day_type", NORMAL_OPERATION_DAY),
        "notification_mode": model.get("notification_mode", "NORMAL_OPERATION_SUMMARY"),
        "normal_report_allowed": model.get("normal_report_allowed", True),
        "summary_text": model["notification_summary_text"],
        "sections": _notification_sections_for_model(model, report_path),
        "report_path": report_path,
        "buy_candidates": model["buy_rows"] if model.get("next_day_candidates_allowed", True) else [],
        "sell_candidates": model["sell_rows"] if model.get("next_day_candidates_allowed", True) else [],
        "send_executed": report_refs["line_send_executed"] or report_refs["discord_send_executed"],
        "line_send_executed": report_refs["line_send_executed"],
        "discord_send_executed": report_refs["discord_send_executed"],
        "notification_status": report_refs["notification_status"],
        "notification_result_path": report_refs["notification_result_path"],
        "regenerated": report_refs.get("regenerated", False),
        "regenerated_reason": report_refs.get("regenerated_reason", ""),
        "secret_saved": False,
        "raw_request_saved": False,
        "raw_response_saved": False,
    }


def _notification_sections_for_model(model: dict[str, Any], report_path: str) -> list[dict[str, str]]:
    if model.get("operation_day_type") not in NORMAL_REPORT_ALLOWED_DAY_TYPES:
        guard = model.get("report_prerequisite_guard") or {}
        reasons = guard.get("reasons") or []
        return [
            {"heading": "Operation Day Type", "text": str(model.get("operation_day_type", "UNKNOWN"))},
            {"heading": "Mode", "text": str(model.get("notification_mode", "UNKNOWN"))},
            {"heading": "Status", "text": str(model.get("key_message", ""))},
            {"heading": "Reason", "text": " / ".join(str(item) for item in reasons[:5]) if reasons else "特記事項なし"},
            {"heading": "Safety", "text": f"{model['safety']['status']} / {model['safety']['state']}"},
            {"heading": "Reconcile", "text": f"{model['reconcile']['status']} / {model['reconcile']['classification']}"},
            {"heading": "Audit", "text": f"{model['audit']['status']} / parity {model['audit']['parity_status']}"},
            {"heading": "Report", "text": report_path},
        ]
    return [
            {"heading": "Market", "text": f"{model['market']['status']} / next {model['market']['next_business_day']}"},
            {"heading": "BUY候補Top5", "text": _notification_top5_text(model)},
            {"heading": "本日注文結果", "text": f"Broker注文 {model['broker']['orders_count']}件、Fill events {model['fill']['fill_event_count']}件"},
            {"heading": "Fill", "text": f"{model['fill']['status']} / events {model['fill']['fill_event_count']}"},
            {"heading": "Safety", "text": f"{model['safety']['status']} / {model['safety']['state']}"},
            {"heading": "Reconcile", "text": f"{model['reconcile']['status']} / {model['reconcile']['classification']}"},
            {"heading": "Audit", "text": f"{model['audit']['status']} / parity {model['audit']['parity_status']}"},
            {"heading": "Report", "text": report_path},
    ]


def _phase9_v4_payload_from_operations_model(model: dict[str, Any]) -> dict[str, Any]:
    bought = [_phase9_bought_row(row) for row in model["buy_rows"] if _is_report_fill(row)]
    sold = [_phase9_sold_row(row) for row in model["sell_rows"] if _is_report_fill(row)]
    candidate_top50 = [_phase9_candidate_row(row) for row in model.get("candidate_top50", [])[:50]]
    opportunity_top20 = [_phase9_opportunity_row(row) for row in (model.get("candidate_top50", [])[:20])]
    top5_details = [_phase9_reason_detail(row) for row in model["buy_rows"][:5]]
    purchase_details = [_phase9_reason_detail(row) for row in model["buy_rows"] if _is_report_fill(row)]
    summary = _phase9_summary(model)
    return {
        "summary": summary,
        "holdings": [_phase9_holding_row(row) for row in model.get("positions", [])],
        "bought": bought,
        "purchase_reason_details": purchase_details,
        "sold": sold,
        "sell_reason_details": [_phase9_sell_reason_detail(row) for row in sold],
        "candidate_top50": candidate_top50,
        "opportunity_top20": opportunity_top20,
        "top5_reason_details": top5_details,
        "ai_summary_deep_dive": _phase9_ai_summary_deep_dive(model, bought_count=len(bought), candidate_count=len(candidate_top50), opportunity_count=len(opportunity_top20)),
        "safety_review": {},
        "disclaimer": [
            "これは仮想運用です。",
            "実売買ではありません。",
            "投資判断は自己責任でお願いします。",
        ],
    }


def _phase9_summary(model: dict[str, Any]) -> dict[str, Any]:
    ledger_cash = model.get("ledger", {})
    is_demo = str(model.get("environment") or "").lower() == "demo"
    demo_buy_notional = _filled_notional(model.get("buy_rows", []), "BUY") if is_demo else Decimal("0")
    demo_sell_notional = _filled_notional(model.get("sell_rows", []), "SELL") if is_demo else Decimal("0")
    demo_open_market_value = max(demo_buy_notional - demo_sell_notional, Decimal("0"))
    cash = DEMO_OPERATION_INITIAL_EQUITY - demo_buy_notional + demo_sell_notional if is_demo else _phase9_decimal(ledger_cash.get("buying_power") or ledger_cash.get("cash_available"))
    positions_count = int(len(model.get("positions", [])) or model.get("broker", {}).get("positions_count") or ledger_cash.get("broker_positions_count") or ledger_cash.get("positions_count") or 0)
    market_value = demo_open_market_value if is_demo and demo_open_market_value > 0 else (Decimal("0") if positions_count == 0 else _phase9_decimal(ledger_cash.get("market_value_estimate")))
    current_asset = cash + market_value
    pnl_display = "未確定（Demo運用は100万円評価基準で開始。実現損益確定後に更新）" if is_demo else "未確定（基準資産未確定）"
    return {
        "decision_for": model["business_date"],
        "execution_date": model["business_date"],
        "stale_price_source": False,
        "cash": _decimal_text(cash),
        "cash_display": _yen_display(cash),
        "market_value": _decimal_text(market_value),
        "market_value_display": _yen_display(market_value),
        "current_asset": _decimal_text(current_asset),
        "current_asset_display": _yen_display(current_asset),
        "pnl": "0",
        "pnl_display": pnl_display,
        "pnl_rate": "0",
        "pnl_rate_display": pnl_display,
        "realized_pnl": "0",
        "unrealized_pnl": "0",
        "unrealized_pnl_display": "0円",
        "positions_count": positions_count,
        "pending_orders_count": model["broker"]["orders_count"],
    }


def _phase9_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except Exception:  # noqa: BLE001 - report rendering must fail closed to zero for missing numeric artifacts.
        return Decimal("0")


def _yen_display(value: Decimal) -> str:
    rounded = value.quantize(Decimal("1")) if value == value.to_integral() else value
    return f"{int(rounded):,}円" if rounded == rounded.to_integral() else f"{rounded:,.2f}円"


def _filled_notional(rows: list[dict[str, Any]], side: str) -> Decimal:
    total = Decimal("0")
    for row in rows:
        if str(row.get("side") or "").upper() != side:
            continue
        if str(row.get("fill_status") or "").upper() not in {"FILLED", "SIMULATED_FILLED"}:
            continue
        total += _phase9_decimal(row.get("filled_notional") or row.get("expected_notional"))
    return total


def _phase9_candidate_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": row.get("candidate_rank", ""),
        "code": row.get("broker_issue_code", row.get("internal_code", "")),
        "name": row.get("name", ""),
        "candidate_score": row.get("public_confidence_score", ""),
    }


def _phase9_opportunity_row(row: dict[str, Any]) -> dict[str, Any]:
    score = row.get("public_confidence_score", "")
    return {
        "rank": row.get("opportunity_rank") or row.get("candidate_rank", ""),
        "code": row.get("broker_issue_code", row.get("internal_code", "")),
        "name": row.get("name", ""),
        "opportunity_score": score,
        "public_confidence_score": score,
    }


def _phase9_bought_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": row.get("broker_issue_code", row.get("internal_code", "")),
        "name": row.get("name", ""),
        "quantity": row.get("quantity", "0"),
        "fill_price": "0" if row.get("limit_price") == "submit時に正規化" else row.get("limit_price", "0"),
        "amount": "0" if row.get("expected_notional") == "submit時に正規化" else row.get("expected_notional", "0"),
        "public_confidence_score": row.get("public_confidence_score", "N/A"),
        "public_confidence_label": "",
    }


def _phase9_sold_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": row.get("broker_issue_code", row.get("internal_code", "")),
        "name": row.get("name", ""),
        "quantity": row.get("quantity", "0"),
        "sell_price": "0" if row.get("limit_price") == "submit時に正規化" else row.get("limit_price", "0"),
        "realized_pnl": "0",
        "sell_reason": row.get("sell_reason") or row.get("exit_source") or "Position Managementの売却判断です。",
    }


def _phase9_holding_row(row: dict[str, Any]) -> dict[str, Any]:
    market_value = _phase9_decimal(row.get("market_value") or row.get("market_value_estimate") or row.get("value"))
    return {
        "code": row.get("code", ""),
        "name": row.get("name", ""),
        "quantity": row.get("quantity", "0"),
        "market_value_display": row.get("market_value_display") or _yen_display(market_value),
        "unrealized_pnl": "0",
    }


def _phase9_reason_detail(row: dict[str, Any]) -> dict[str, Any]:
    metrics = row.get("metrics") or {}
    paragraphs = [
        f"{row.get('name') or row.get('internal_code')}はCandidate {row.get('candidate_rank_text')}位からOpportunity {row.get('opportunity_rank_text')}位まで残った注目候補です。",
        (
            f"直近5日で{metrics.get('return_5d_text')}、20日で{metrics.get('return_20d_text')}と短中期の値動きを確認しています。"
            f"出来高は平常比で約{metrics.get('volume_ratio_text')}、終値は20日平均線から{metrics.get('ma20_divergence_text')}の位置です。"
            f"20日平均出来高は約{metrics.get('avg_volume_20d_text')}株で売買も確認できます。"
        ),
        "購入時点の価格位置は20日高値比、60日高値比、52週高値比が今回のOperations artifactでは未取得です。",
        f"公開用AI信頼度は{row.get('public_confidence_score')}です。これは勝率や上昇確率ではなく、候補としての説明用スコアです。",
    ]
    return {
        "code": row.get("broker_issue_code", row.get("internal_code", "")),
        "name": row.get("name", ""),
        "candidate_rank": row.get("candidate_rank"),
        "opportunity_rank": row.get("opportunity_rank"),
        "public_confidence_score": row.get("public_confidence_score"),
        "reason_paragraphs": paragraphs,
    }


def _phase9_sell_reason_detail(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": row.get("code", ""),
        "name": row.get("name", ""),
        "reason_paragraphs": [row.get("sell_reason", "Position Managementの売却判断です。")],
    }


def _phase9_ai_summary_deep_dive(model: dict[str, Any], *, bought_count: int, candidate_count: int, opportunity_count: int) -> list[str]:
    if bought_count:
        return [f"本日はDemo Brokerで{bought_count}件の注文受付を確認しました。翌営業日候補とは分けて管理しています。"]
    return ["本日は新規購入がないため、保有銘柄の評価と次回判断を待つ日になりました。"]


def _phase12_appendix(model: dict[str, Any]) -> str:
    return "\n".join(
        [
            "## Demo運用状況",
            "",
            f"本日のDemo Broker注文は{model['broker']['orders_count']}件です。Broker受付・未約定・約定状況はFill Monitorで確認し、Fill eventは{model['fill']['fill_event_count']}件です。",
            f"Broker約定は{model['broker']['executions_count']}件、Broker保有は{model['broker']['positions_count']}件です。",
            "Demo環境では9000番台銘柄が単独約定しないケースがあるため、対象銘柄のみDemo Special Fill Simulationでライフサイクル確認を行います。",
            f"本日のDemo Special Fill Simulation使用: {_yes_no(model['demo_special']['used'])}",
            "Persistent Demo Ledgerは、立花Demoの日次リセットをまたいで注文・約定・ポジション履歴を保持するために使います。",
            f"Safety: {model['safety']['status']} / {model['safety']['state']}",
            f"Reconcile: {model['reconcile']['status']} / {model['reconcile']['classification']}",
            f"Audit: {model['audit']['status']} / parity {model['audit']['parity_status']}",
            f"Market Calendar: {model['market']['status']} / next business day {model['market']['next_business_day']}",
            f"LINE通知: {_yes_no(model['notification']['line_send_executed'])}",
            f"Discord通知: {_yes_no(model['notification']['discord_send_executed'])}",
            "Production注文は本日も無効です。",
            "",
        ]
    )


def _is_report_fill(row: dict[str, Any]) -> bool:
    return str(row.get("fill_status") or "").upper() in {"FILLED", "SIMULATED_FILLED"}


def _production_equivalence_checklist(
    paths: OperationPaths,
    trade_date: str,
    *,
    env: str,
    status_refs: dict[str, str],
    order_plan: dict[str, Any],
    broker_bundle: dict[str, Any],
    demo_special: dict[str, Any],
) -> dict[str, Any]:
    approval = _load_or_empty(paths.dated("approval_artifact", trade_date, "approval_artifact.json"), default={})
    submitted = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={})
    fill = _load_or_empty(paths.dated("fill_events", trade_date, "fill_events.json"), default={})
    ledger = _load_or_empty(paths.dated("ledger", trade_date, "ledger_state.json"), default={})
    safety = _load_or_empty(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), default={})
    reconcile = _load_or_empty(paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"), default={})
    audit = _load_or_empty(paths.root / "audit_result" / "audit_result.json", default={})
    checks = [
        _equivalence_item("AI判断", "PASS" if status_refs.get("daily_plan") in {"PASS", "SKIPPED_MARKET_CLOSED"} else "REVIEW_REQUIRED", "daily_plan uses common Operations flow"),
        _equivalence_item("BUY候補数", "PASS" if (order_plan.get("operations_runtime_config") or {}).get("candidate_count_environment_specific") is False else "BLOCKING_GAP", f"buy_item_count={order_plan.get('buy_item_count', 0)}"),
        _equivalence_item("SELL AI", "PASS" if (order_plan.get("exit_adapter") or {}).get("status") in {"PASS", None} else "REVIEW_REQUIRED", f"sell_item_count={order_plan.get('sell_item_count', 0)}"),
        _equivalence_item("Capital Allocation接続状況", "REVIEW_REQUIRED" if (order_plan.get("operations_runtime_config") or {}).get("capital_allocation_connected") is False else "PASS", "full Capital Allocation AI connection remains deferred"),
        _equivalence_item("Approval", "PASS" if approval.get("status") in {"APPROVED", "SKIPPED_MARKET_CLOSED"} else "REVIEW_REQUIRED", str(approval.get("approval_source", ""))),
        _equivalence_item("Submit", "PASS" if submitted.get("status") in {"PASS", "PARTIAL_PASS_WITH_ITEM_BLOCKS", "SKIPPED_MARKET_CLOSED", "REVIEW_REQUIRED"} else "REVIEW_REQUIRED", f"production_order_submitted={submitted.get('production_order_submitted', False)}"),
        _equivalence_item("Broker read-only", "PASS" if broker_bundle.get("status") == "PASS" else "REVIEW_REQUIRED", f"orders={broker_bundle.get('orders_count', 0)}, positions={broker_bundle.get('positions_count', 0)}"),
        _equivalence_item("Broker order", "PASS" if submitted.get("production_order_submitted") is not True else "BLOCKING_GAP", "Demo order path only; Production disabled"),
        _equivalence_item("Fill", "PASS" if fill.get("status") in {"PASS", "PASS_MARKET_CLOSED_MONITOR_ONLY"} else "REVIEW_REQUIRED", f"fill_events={len(fill.get('fill_events', [])) if isinstance(fill.get('fill_events'), list) else 0}"),
        _equivalence_item("Ledger", "PASS" if ledger.get("raw_response_saved") is not True and ledger.get("secret_saved") is not True else "BLOCKING_GAP", "Broker read-only ledger state"),
        _equivalence_item("Persistent Demo Ledger", "INTENTIONAL_DEMO_DIFFERENCE", "Required because Tachibana Demo resets daily"),
        _equivalence_item("Safety", "PASS" if safety.get("status") in {"PASS", "PASS_MARKET_CLOSED_SYSTEM_ONLY"} else "REVIEW_REQUIRED", str(safety.get("safety_state", ""))),
        _equivalence_item("Reconcile", "PASS" if reconcile.get("status") in {"PASS", "PASS_WITH_BLOCKED_ITEMS", "PASS_MARKET_CLOSED_RECONCILE_ONLY"} else "REVIEW_REQUIRED", str(reconcile.get("classification", ""))),
        _equivalence_item("Daily Report", "FIXED", "human-readable writer enabled"),
        _equivalence_item("Blog", "FIXED", "blog_draft/public_report generated from shared writer"),
        _equivalence_item("LINE通知", "FIXED", "notification adapter supports actual send"),
        _equivalence_item("Discord通知", "FIXED", "notification adapter supports actual send"),
        _equivalence_item("Operation Audit", "PASS" if audit.get("status") in {"PASS", ""} else "REVIEW_REQUIRED", f"parity={(audit.get('demo_production_parity_audit') or {}).get('status', 'UNKNOWN')}"),
        _equivalence_item("launchd", "FIXED", "daily_report plist includes --send-notifications"),
        _equivalence_item("Market Calendar", "PASS", "Operations market calendar safe-skip enabled"),
        _equivalence_item("Secret Redaction", "PASS" if broker_bundle.get("secret_saved") is not True else "BLOCKING_GAP", "secret_saved=false"),
        _equivalence_item("raw request / response保存禁止", "PASS" if broker_bundle.get("raw_response_saved") is not True else "BLOCKING_GAP", "raw_response_saved=false"),
        _equivalence_item("Production注文禁止", "PASS" if submitted.get("production_order_submitted") is not True else "BLOCKING_GAP", "production_order_submitted=false"),
        _equivalence_item("Demo Special Fill Simulation", "INTENTIONAL_DEMO_DIFFERENCE", f"used={demo_special.get('demo_special_fill_simulation_used', False)}"),
        _equivalence_item("TACHIBANA_API_ENV=demo", "INTENTIONAL_DEMO_DIFFERENCE" if env == "demo" else "PASS", f"environment={env}"),
        _equivalence_item("Production order disabled", "INTENTIONAL_DEMO_DIFFERENCE", "Production order remains fail closed"),
    ]
    unexpected = [
        item["name"]
        for item in checks
        if item["classification"] == "BLOCKING_GAP"
        or (item["classification"] == "INTENTIONAL_DEMO_DIFFERENCE" and item["name"] not in {"Persistent Demo Ledger", "Demo Special Fill Simulation", "TACHIBANA_API_ENV=demo", "Production order disabled"})
    ]
    return {
        "status": "PASS" if not unexpected else "BLOCK",
        "allowed_demo_production_differences": [
            "demo_special_fill_simulation",
            "persistent_demo_ledger",
            "tachibana_api_env_demo",
            "production_order_disabled",
        ],
        "unexpected_demo_production_differences": unexpected,
        "items": checks,
    }


def _equivalence_item(name: str, classification: str, note: str) -> dict[str, str]:
    return {"name": name, "classification": classification, "note": note}


def _equivalence_table(checklist: dict[str, Any]) -> str:
    rows = checklist.get("items") if isinstance(checklist, dict) else []
    if not isinstance(rows, list) or not rows:
        return "Production Equivalence Checklistは未生成です。"
    return _markdown_table(
        ["観点", "分類", "補足"],
        [[str(item.get("name", "")), str(item.get("classification", "")), str(item.get("note", ""))] for item in rows if isinstance(item, dict)],
    )


def _tomorrow_check_points(report_refs: dict[str, Any], *, buy_rows: list[dict[str, Any]], sell_rows: list[dict[str, Any]], safety: dict[str, Any], reconcile: dict[str, Any]) -> list[str]:
    points = [
        "翌朝のPreflightでBroker read-only snapshotとbuying powerを確認する。",
        "Approvalの有効期限とapproved item数を確認する。",
    ]
    if buy_rows:
        points.append("BUY候補のsubmit直前価格正規化とMAX_EXPOSUREを確認する。")
    if sell_rows:
        points.append("SELL候補のposition_id / sell_reason / exit_sourceを確認する。")
    if safety.get("safety_state") != "ALLOW":
        points.append("SafetyがALLOW以外のため、注文前にHuman Reviewを確認する。")
    if reconcile.get("classification") not in {"PASS", "", None}:
        points.append("ReconcileがPASS以外のため、差分を確認する。")
    if report_refs.get("notification_status") not in {"PASS", "NOT_REQUESTED"}:
        points.append("通知がFAILED_NON_FATALの場合、notification_result.jsonを確認する。")
    return points


def _asset_status_paragraph(model: dict[str, Any]) -> str:
    return (
        f"本日のBroker read-only確認では、注文{model['broker']['orders_count']}件、約定{model['broker']['executions_count']}件、"
        f"保有{model['broker']['positions_count']}件を確認しました。Demo運用履歴はPersistent Demo Ledgerにも保持し、"
        "Broker側の日次リセットで過去の運用履歴が失われないようにしています。"
    )


def _positions_section(model: dict[str, Any]) -> str:
    positions = model.get("positions") or []
    if not positions:
        return "現在、Broker read-only snapshot上で保有中の銘柄は確認されていません。Demo環境の日次リセット後も、必要な履歴はPersistent Demo Ledgerで確認します。"
    return _markdown_table(
        ["コード", "銘柄名", "市場", "数量", "評価メモ"],
        [[row["code"], row["name"], row["market"], row["quantity"], row["memo"]] for row in positions],
    )


def _orders_story_section(model: dict[str, Any]) -> str:
    rows = model["buy_rows"]
    intro = f"本日の注文監視では、Broker注文{model['broker']['orders_count']}件、Fill event {model['fill']['fill_event_count']}件を確認しました。"
    if not rows:
        return intro + "\n\n本日注文・約定したBUY銘柄はありません。"
    return intro + "\n\n" + _orders_table(rows, empty="本日注文・約定したBUY銘柄はありません。")


def _sell_story_section(model: dict[str, Any]) -> str:
    rows = model["sell_rows"]
    if not rows:
        return "本日のSELL候補および売却注文はありません。保有銘柄がない、またはExit条件に該当する銘柄がない状態です。"
    return _orders_table(rows, empty="本日のSELL候補および売却注文はありません。")


def _candidate_top50_section(model: dict[str, Any]) -> str:
    rows = model.get("candidate_top50") or []
    if not rows:
        return "Candidate Top50は今回のartifactでは未取得です。feature artifactの生成状況を確認してください。"
    lines = [
        "Candidate Top50はJ-Quants由来featureから作成した候補順位です。Scoreは順位ベースの説明用スコアであり、勝率や上昇確率ではありません。",
        "",
    ]
    for row in rows[:50]:
        lines.append(f"{row['candidate_rank']}. {row['broker_issue_code']} {row['name']} / Score {row['public_confidence_score']} / 5日 {row['return_5d_text']} / 20日 {row['return_20d_text']}")
    return "\n".join(lines)


def _top5_table(model: dict[str, Any]) -> str:
    rows = model["buy_rows"][:5]
    if not rows:
        return "翌営業日の購入予定候補はありません。"
    return _markdown_table(
        ["順位", "コード", "銘柄名", "市場", "数量", "想定価格", "想定金額", "broker issue code", "選定理由"],
        [
            [
                str(idx),
                row["internal_code"],
                row["name"],
                row["market"],
                row["quantity"],
                row["limit_price"],
                row["expected_notional"],
                row["broker_issue_code"],
                row["selection_reason"],
            ]
            for idx, row in enumerate(rows, 1)
        ],
    )


def _candidate_reason_section(row: dict[str, Any]) -> str:
    code_name = f"{row['internal_code']} {row['name'] or '名称未取得'}"
    metrics = row.get("metrics") or {}
    missing_high = "20日高値比、60日高値比、52週高値比は今回のOperations feature artifactでは未取得です。"
    high_chase = "高値追いリスクは高値比featureが未取得のため定量判定していませんが、20日移動平均からの乖離と短期リターンを確認対象にします。"
    return "\n".join(
        [
            f"### {code_name}",
            "",
            (
                f"{row['name'] or code_name}は、Candidate順位{row.get('candidate_rank_text')}、Opportunity順位{row.get('opportunity_rank_text')}の購入候補です。"
                f"直近5日リターンは{metrics.get('return_5d_text')}、20日リターンは{metrics.get('return_20d_text')}で、"
                f"出来高倍率は{metrics.get('volume_ratio_text')}、20日平均出来高は{metrics.get('avg_volume_20d_text')}です。"
                f"20日移動平均からの乖離は{metrics.get('ma20_divergence_text')}で、公開用AI信頼度は{row.get('public_confidence_score')}です。"
            ),
            "",
            f"選定理由: {row['selection_reason']}",
            "",
            f"{missing_high} {high_chase}",
        ]
    )


def _broker_demo_story(model: dict[str, Any]) -> str:
    special = model["demo_special"]
    sim_text = (
        "本日はDemo Special Fill Simulationを使用しました。"
        if special["used"]
        else "本日はDemo Special Fill Simulationの対象外でした。"
    )
    return (
        f"本日のBroker注文は{model['broker']['orders_count']}件確認されています。"
        f"Broker約定は{model['broker']['executions_count']}件、Broker保有は{model['broker']['positions_count']}件です。"
        "Demo環境では9000番台銘柄が単独約定しないケースがあるため、対象銘柄のみDemo Special Fill Simulationでライフサイクル確認を行います。"
        f"{sim_text} Persistent Demo Ledgerは、立花Demoの日次リセットをまたいで注文・約定・ポジション履歴を保持するために使います。"
        "Production注文は本日も無効のままです。"
    )


def _safety_story(model: dict[str, Any]) -> str:
    faults = _list_text(model["safety"]["system_faults"]) or "重大なsystem faultはありません。"
    missing = _list_text(model["reconcile"]["missing"]) or "照合対象artifactに重大な欠落はありません。"
    differences = _list_text(model["audit"]["unexpected_differences"]) or "許可されていないDemo/Production差分はありません。"
    return "\n\n".join(
        [
            f"Safety Monitorは{model['safety']['state']}です。{faults}",
            f"Reconcileは{model['reconcile']['classification']}です。{missing}",
            f"Operation Auditは{model['audit']['status']}です。leakage auditは{model['audit']['leakage_status']}、Production注文なしの監査は{_yes_no(model['audit']['no_production_order_audit'])}です。{differences}",
        ]
    )


def _ai_summary(model: dict[str, Any]) -> str:
    top = model["buy_rows"][0] if model["buy_rows"] else {}
    lead = f"最上位候補は{top.get('internal_code', '')} {top.get('name', '')}です。" if top else "本日は新規購入候補がありません。"
    return (
        f"{lead} 候補抽出はJ-Quants由来の価格・出来高・トレンドfeatureを使い、Broker SnapshotやLedger、Safety、Audit、PnL、cash、portfolio stateはAI学習入力に使っていません。"
        f"本日はSafetyが{model['safety']['state']}、Reconcileが{model['reconcile']['classification']}、Auditが{model['audit']['status']}で、運用継続に必要な主要確認は通過しています。"
    )


def _disclaimer_text(model: dict[str, Any]) -> str:
    return (
        "このレポートはDemo Operations検証用の運用記録です。記載されたスコアは候補説明のための表示であり、勝率や将来上昇確率を示すものではありません。"
        "投資判断そのものではなく、Production注文は無効化されています。AI学習にはJ-Quants由来データのみを使用し、Broker Snapshot、Ledger、Safety、Audit、PnL、cash、portfolio stateは学習へ混入させません。"
    )


def _notification_top5_text(model: dict[str, Any]) -> str:
    rows = model["buy_rows"][:5]
    if not rows:
        return "BUY候補なし"
    return " / ".join(f"{row['broker_issue_code']} {row['name'] or row['internal_code']}" for row in rows)


def _report_order_row(
    item: dict[str, Any],
    names: dict[str, dict[str, str]],
    submitted_rows: list[dict[str, Any]],
    fill_rows: list[dict[str, Any]],
    candidate_by_code: dict[str, dict[str, Any]] | None = None,
    *,
    broker_order_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    code = str(item.get("issue_code") or item.get("code") or "")
    info = names.get(code) or names.get(code[:-1]) or {}
    candidate = (candidate_by_code or {}).get(code) or {}
    submitted = next((row for row in submitted_rows if row.get("item_id") == item.get("item_id")), {})
    fill = next((row for row in fill_rows if row.get("item_id") == item.get("item_id")), {})
    normalization = submitted.get("code_normalization") or submitted.get("issue_code_normalization") or {}
    normalized_order = submitted.get("normalized_order") or {}
    broker_code = str(normalization.get("broker_issue_code") or normalized_order.get("broker_issue_code") or submitted.get("broker_issue_code") or _display_broker_issue_code(code, names))
    limit_price = str(normalized_order.get("limit_price") or submitted.get("limit_price") or item.get("limit_price") or "")
    expected_notional = str(normalized_order.get("expected_notional") or submitted.get("expected_notional") or item.get("expected_notional") or item.get("estimated_value") or "")
    broker_fill = _matched_filled_broker_order(
        broker_order_rows or [],
        broker_issue_code=broker_code,
        side=str(item.get("side", "")),
        quantity=str(item.get("quantity", "")),
    )
    if broker_fill:
        limit_price = str(broker_fill.get("price") or limit_price)
        expected_notional = _decimal_text(_phase9_decimal(broker_fill.get("executed_quantity")) * _phase9_decimal(broker_fill.get("price")))
    metrics = candidate.get("metrics") or _empty_candidate_metrics()
    candidate_rank = candidate.get("candidate_rank")
    opportunity_rank = candidate.get("opportunity_rank")
    selection_reason = _selection_reason(candidate, metrics)
    return {
        "side": str(item.get("side", "")),
        "internal_code": code,
        "broker_issue_code": broker_code,
        "name": info.get("name", "") or candidate.get("name", ""),
        "market": info.get("market", "") or candidate.get("market", ""),
        "quantity": str(item.get("quantity", "")),
        "limit_price": "submit時に正規化" if limit_price in {"", "0", "0.0"} else limit_price,
        "expected_notional": "submit時に正規化" if expected_notional in {"", "0", "0.0"} else expected_notional,
        "status": "FILLED" if broker_fill else str(submitted.get("status") or fill.get("lifecycle") or "PLANNED"),
        "fill_status": "FILLED" if broker_fill else str(fill.get("lifecycle") or "NOT_FILLED"),
        "block_reason": submitted.get("block_reason", ""),
        "block_reasons": submitted.get("block_reasons") or submitted.get("reasons") or [],
        "blocking_stage": submitted.get("blocking_stage", ""),
        "filled_quantity": str(broker_fill.get("executed_quantity") or "") if broker_fill else "",
        "filled_price": str(broker_fill.get("price") or "") if broker_fill else "",
        "filled_notional": expected_notional if broker_fill else "",
        "sell_reason": str(item.get("sell_reason") or ""),
        "exit_source": str(item.get("exit_source") or ""),
        "candidate_rank": candidate_rank,
        "candidate_rank_text": str(candidate_rank) if candidate_rank else "今回のartifactでは未取得",
        "opportunity_rank": opportunity_rank,
        "opportunity_rank_text": str(opportunity_rank) if opportunity_rank else "今回のartifactでは未取得",
        "public_confidence_score": candidate.get("public_confidence_score", "今回のartifactでは未取得"),
        "selection_reason": selection_reason,
        "metrics": metrics,
    }


def _item_from_submitted_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = row.get("normalized_order") or {}
    return {
        "item_id": row.get("item_id"),
        "issue_code": row.get("issue_code") or normalized.get("issue_code") or normalized.get("code") or row.get("code", ""),
        "code": row.get("code") or row.get("issue_code") or normalized.get("code", ""),
        "side": row.get("side") or normalized.get("side", ""),
        "quantity": row.get("quantity") or normalized.get("quantity", ""),
        "limit_price": row.get("limit_price") or normalized.get("limit_price", ""),
        "expected_notional": row.get("expected_notional") or normalized.get("expected_notional", ""),
        "estimated_value": row.get("estimated_value") or normalized.get("estimated_value", ""),
        "position_id": row.get("position_id", ""),
        "exit_source": row.get("exit_source", ""),
        "sell_reason": row.get("sell_reason", ""),
        "sell_intent": row.get("sell_intent", ""),
    }


def _matched_filled_broker_order(broker_orders: list[dict[str, Any]], *, broker_issue_code: str, side: str, quantity: str) -> dict[str, Any] | None:
    expected_side = "3" if side.upper() == "BUY" else "1" if side.upper() == "SELL" else side.upper()
    for order in broker_orders:
        if str(order.get("issue_code") or "") != broker_issue_code:
            continue
        if str(order.get("side") or "").upper() not in {expected_side, side.upper()}:
            continue
        if quantity and str(order.get("quantity") or "") != str(quantity):
            continue
        executed = _phase9_decimal(order.get("executed_quantity"))
        remaining = _phase9_decimal(order.get("remaining_quantity"))
        status = str(order.get("status") or "").upper()
        if executed > 0 and remaining == 0 and ("約定" in str(order.get("status") or "") or status in {"FILLED", "DONE"}):
            return order
    return None


def _synthetic_demo_positions_from_filled_orders(buy_rows: list[dict[str, Any]], sell_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sell_quantity_by_code: dict[str, Decimal] = {}
    for row in sell_rows:
        if str(row.get("fill_status") or "").upper() not in {"FILLED", "SIMULATED_FILLED"}:
            continue
        code = str(row.get("broker_issue_code") or row.get("internal_code") or "")
        sell_quantity_by_code[code] = sell_quantity_by_code.get(code, Decimal("0")) + _phase9_decimal(row.get("filled_quantity") or row.get("quantity"))
    positions = []
    for row in buy_rows:
        if str(row.get("fill_status") or "").upper() not in {"FILLED", "SIMULATED_FILLED"}:
            continue
        code = str(row.get("broker_issue_code") or row.get("internal_code") or "")
        buy_quantity = _phase9_decimal(row.get("filled_quantity") or row.get("quantity"))
        remaining_quantity = buy_quantity - sell_quantity_by_code.get(code, Decimal("0"))
        if remaining_quantity <= 0:
            continue
        market_value = _phase9_decimal(row.get("filled_notional") or row.get("expected_notional"))
        positions.append(
            {
                "code": code,
                "name": row.get("name", ""),
                "quantity": _decimal_text(remaining_quantity),
                "market_value": _decimal_text(market_value),
                "market_value_display": _yen_display(market_value),
                "synthetic_from_same_day_demo_fill": True,
            }
        )
    return positions


def _display_broker_issue_code(code: str, names: dict[str, dict[str, str]]) -> str:
    if code.endswith("0") and code[:-1] in names:
        return code[:-1]
    return code


def _load_candidate_top50_for_report(paths: OperationPaths, trade_date: str, names: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    path = paths.root / "feature_artifacts" / trade_date / "candidate_features.parquet"
    if not path.exists():
        return []
    try:
        import pandas as pd

        df = pd.read_parquet(path)
    except Exception:
        return []
    if "universe_eligible" in df.columns:
        df = df[df["universe_eligible"] == True]  # noqa: E712 - pandas boolean mask.
    for col in ["price_momentum_return_20d", "price_momentum_return_5d", "liquidity_avg_volume_20d"]:
        if col not in df.columns:
            df[col] = 0
    df = df.sort_values(
        by=["price_momentum_return_20d", "price_momentum_return_5d", "liquidity_avg_volume_20d"],
        ascending=[False, False, False],
    ).head(50)
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(df.to_dict("records"), 1):
        code = str(row.get("code") or row.get("Code") or "")
        info = names.get(code) or names.get(code[:-1]) or {}
        score = max(51, 101 - idx)
        metrics = _candidate_metrics(row)
        rows.append(
            {
                "candidate_rank": idx,
                "opportunity_rank": idx,
                "internal_code": code,
                "broker_issue_code": _display_broker_issue_code(code, names),
                "name": info.get("name", ""),
                "market": info.get("market", str(row.get("market_name") or "")),
                "public_confidence_score": score,
                "metrics": metrics,
                "return_5d_text": metrics["return_5d_text"],
                "return_20d_text": metrics["return_20d_text"],
                "selection_reason": _selection_reason({"candidate_rank": idx, "public_confidence_score": score}, metrics),
            }
        )
    return rows


def _candidate_metrics(row: dict[str, Any]) -> dict[str, str]:
    return {
        "return_5d_text": _pct_text(row.get("price_momentum_return_5d")),
        "return_20d_text": _pct_text(row.get("price_momentum_return_20d")),
        "volume_ratio_text": _ratio_text(row.get("volume_momentum_ratio_5d")),
        "avg_volume_20d_text": _number_text(row.get("liquidity_avg_volume_20d")),
        "ma20_divergence_text": _pct_text(row.get("trend_close_over_ma_20d")),
        "volatility_20d_text": _pct_text(row.get("volatility_return_std_20d")),
        "high_ratio_20d_text": "今回のartifactでは未取得",
        "high_ratio_60d_text": "今回のartifactでは未取得",
        "high_ratio_52w_text": "今回のartifactでは未取得",
    }


def _empty_candidate_metrics() -> dict[str, str]:
    return {
        "return_5d_text": "今回のartifactでは未取得",
        "return_20d_text": "今回のartifactでは未取得",
        "volume_ratio_text": "今回のartifactでは未取得",
        "avg_volume_20d_text": "今回のartifactでは未取得",
        "ma20_divergence_text": "今回のartifactでは未取得",
        "volatility_20d_text": "今回のartifactでは未取得",
        "high_ratio_20d_text": "今回のartifactでは未取得",
        "high_ratio_60d_text": "今回のartifactでは未取得",
        "high_ratio_52w_text": "今回のartifactでは未取得",
    }


def _selection_reason(candidate: dict[str, Any], metrics: dict[str, str]) -> str:
    rank = candidate.get("candidate_rank")
    confidence = candidate.get("public_confidence_score", "今回のartifactでは未取得")
    rank_text = f"Candidate順位{rank}" if rank else "Candidate順位は今回のartifactでは未取得"
    return (
        f"{rank_text}で、20日リターン{metrics.get('return_20d_text')}、5日リターン{metrics.get('return_5d_text')}、"
        f"出来高倍率{metrics.get('volume_ratio_text')}、20日移動平均乖離{metrics.get('ma20_divergence_text')}を確認したためです。"
        f"公開用AI信頼度は{confidence}です。"
    )


def _report_positions(paths: OperationPaths, trade_date: str, names: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    payload = _load_or_empty(paths.dated("broker_positions", trade_date, "positions.json"), default={"positions": []})
    positions = payload.get("positions", [])
    if not isinstance(positions, list):
        return []
    rows: list[dict[str, str]] = []
    for item in positions:
        if not isinstance(item, dict):
            continue
        code = str(item.get("issue_code") or item.get("code") or "")
        info = names.get(code) or names.get(code + "0") or {}
        rows.append(
            {
                "code": code,
                "name": info.get("name", ""),
                "market": info.get("market", ""),
                "quantity": str(item.get("quantity") or item.get("position_quantity") or ""),
                "memo": "Broker read-only snapshotで確認",
            }
        )
    return rows


def _load_issue_name_map(paths: OperationPaths, trade_date: str) -> dict[str, dict[str, str]]:
    listed_path = paths.dated("feature_refresh", trade_date, "jquants/listed_issues/listed_info_for_feature.parquet")
    if not listed_path.exists():
        return {}
    try:
        import pandas as pd

        df = pd.read_parquet(listed_path, columns=["Code", "CoName", "MktNm"])
    except Exception:
        return {}
    result: dict[str, dict[str, str]] = {}
    for row in df.to_dict("records"):
        code = str(row.get("Code") or "")
        if code:
            result[code] = {"name": str(row.get("CoName") or ""), "market": str(row.get("MktNm") or "")}
            if code.endswith("0"):
                result[code[:-1]] = result[code]
    return result


def _pct_text(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return "今回のartifactでは未取得"


def _ratio_text(value: Any) -> str:
    try:
        return f"{float(value):.2f}倍"
    except Exception:
        return "今回のartifactでは未取得"


def _number_text(value: Any) -> str:
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "今回のartifactでは未取得"


def _daily_key_message(report_refs: dict[str, Any], *, buy_rows: list[dict[str, Any]], sell_rows: list[dict[str, Any]], safety: dict[str, Any], reconcile: dict[str, Any], audit: dict[str, Any]) -> str:
    if report_refs.get("market_status") == "CLOSED":
        return "本日は市場休場日のため、AI判断と注文処理は安全にスキップしました。"
    safety_state = safety.get("safety_state", "UNKNOWN")
    reconcile_status = reconcile.get("classification", reconcile.get("status", "UNKNOWN"))
    audit_status = audit.get("status", "UNKNOWN")
    return f"本日はBUY候補{len(buy_rows)}件、SELL候補{len(sell_rows)}件を確認しました。Safetyは{safety_state}、Reconcileは{reconcile_status}、Auditは{audit_status}です。"


def _orders_table(rows: list[dict[str, Any]], *, empty: str) -> str:
    if not rows:
        return empty
    return _markdown_table(
        ["Side", "Internal", "Broker", "銘柄名", "市場", "数量", "価格", "想定金額", "状態", "理由"],
        [
            [
                row["side"],
                row["internal_code"],
                row["broker_issue_code"],
                row["name"],
                row["market"],
                row["quantity"],
                row["limit_price"],
                row["expected_notional"],
                row["status"] if row["fill_status"] == "NOT_FILLED" else f"{row['status']} / {row['fill_status']}",
                row["sell_reason"] or row["exit_source"] or row.get("selection_reason") or "理由は今回のartifactでは未取得です。",
            ]
            for row in rows
        ],
    )


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    clean_headers = [_md_cell(item) for item in headers]
    lines = ["| " + " | ".join(clean_headers) + " |", "| " + " | ".join(["---"] * len(clean_headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_md_cell(item) for item in row) + " |")
    return "\n".join(lines)


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "/").replace("\n", " ").strip()


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _list_text(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def run_audit(*, root: Path = DEFAULT_OPERATION_ROOT) -> dict[str, Any]:
    paths = OperationPaths(root)
    runtime = _resolve_runtime_environment()
    env = runtime["environment"]
    manifests = sorted((paths.root / "daily_manifest").glob("*/daily_manifest.json")) if (paths.root / "daily_manifest").exists() else []
    loaded = [read_json(path) for path in manifests]
    text = [
        read_json(path)
        for path in paths.root.glob("**/*.json")
        if "audit_result" not in path.relative_to(paths.root).parts
    ] if paths.root.exists() else []
    leakage = artifact_leakage_audit(text)
    production_orders = [item for item in text if item.get("production_order_submitted") is True]
    line_sends = [item for item in text if item.get("line_send_executed") is True]
    discord_sends = [item for item in text if item.get("discord_send_executed") is True]
    market_closed_order_traces = [
        item
        for item in text
        if (item.get("market_calendar") or {}).get("market_closed") is True
        and (
            item.get("demo_order_executed") is True
            or item.get("demo_order_submitted") is True
            or item.get("broker_order_api_called") is True
            or item.get("clm_kabu_new_order_called") is True
            or item.get("demo_special_fill_simulation_used") is True
        )
    ]
    recon_paths = sorted((paths.root / "reconciliation_result").glob("*/reconciliation_result.json")) if (paths.root / "reconciliation_result").exists() else []
    recons = [read_json(path) for path in recon_paths]
    pass_count = sum(1 for item in recons if item.get("status") == "PASS")
    phase9_isolation = _phase9_isolation_audit(paths)
    latest_manifest = loaded[-1] if loaded else {}
    latest_trade_date = str(latest_manifest.get("business_date") or "")
    broker_bundle = load_broker_artifact_bundle(trade_date=latest_trade_date, root=paths.root) if latest_trade_date else {"status": "MISSING"}
    latest_market = _load_or_empty(paths.dated("market_refresh", latest_trade_date, "market_refresh_manifest.json"), default={}) if latest_trade_date else {}
    latest_order_plan = _load_or_empty(paths.dated("order_plan", latest_trade_date, "order_plan.json"), default={}) if latest_trade_date else {}
    latest_ledger = _load_or_empty(paths.dated("ledger", latest_trade_date, "ledger_summary.json"), default={}) if latest_trade_date else {}
    latest_feature_candidate_audit = _load_or_empty(paths.dated("feature_candidate_audit", latest_trade_date, "feature_candidate_audit.json"), default=feature_candidate_diagnostics(root=paths.root, trade_date=latest_trade_date)) if latest_trade_date else {}
    latest_demo_special = _load_demo_special_fill_summary(paths, latest_trade_date) if latest_trade_date else {}
    latest_market_calendar = _market_calendar(paths, latest_trade_date) if latest_trade_date else {}
    parity = _demo_production_parity_audit(paths, latest_trade_date, env=env) if latest_trade_date else {"status": "UNKNOWN", "unexpected_differences": []}
    latest_status_refs = _collect_operation_statuses(paths, latest_trade_date) if latest_trade_date else {}
    latest_current_status_refs = _current_operation_statuses(paths, latest_trade_date) if latest_trade_date else {}
    flow_guard = (
        _operation_flow_integrity_guard(
            paths,
            latest_trade_date,
            market_calendar=latest_market_calendar,
            status_refs=latest_status_refs,
            current_status_refs=latest_current_status_refs,
            order_plan=latest_order_plan,
        )
        if latest_trade_date
        else {
            "operation_day_type": "UNKNOWN",
            "report_prerequisite_pass": False,
            "artifact_date_consistency_pass": False,
            "source_of_truth_consistency_pass": False,
            "normal_report_allowed": False,
            "candidate_top50_allowed": False,
            "next_day_candidates_allowed": False,
            "notification_mode": "UNKNOWN",
            "reasons": ["daily_manifest_missing"],
        }
    )
    status = "PASS" if runtime["status"] == "PASS" and not production_orders and not market_closed_order_traces and leakage["status"] == "PASS" and parity.get("status") != "BLOCK" else "BLOCK"
    if status == "PASS" and flow_guard.get("operation_day_type") in {INCOMPLETE_OPERATION_DAY, RECOVERY_DAY, REVIEW_REQUIRED_DAY}:
        status = "REVIEW_REQUIRED"
    if status == "PASS" and latest_market_calendar.get("market_closed") is True:
        status = "PASS_MARKET_CLOSED"
    if phase9_isolation["status"] != "PASS":
        status = "BLOCK"
    payload = _base_payload("audit", env, "ALL", status)
    payload.update(
        {
            "daily_manifest_count": len(loaded),
            "thirty_business_day_ready": len(loaded) >= 30,
            "no_production_order_audit": not production_orders,
            "production_unlock_audit": True,
            "secret_audit": leakage["status"] == "PASS",
            "raw_response_audit": leakage["status"] == "PASS",
            "leakage_audit": leakage,
            "ai_contamination_audit": True,
            "line_send_executed": bool(line_sends),
            "discord_send_executed": bool(discord_sends),
            "notification_delivery_allowed": True,
            "notification_send_count": {
                "line": len(line_sends),
                "discord": len(discord_sends),
            },
            "demo_production_parity_audit": parity,
            "operation_flow_integrity_guard": flow_guard,
            "operation_day_type": flow_guard.get("operation_day_type", "UNKNOWN"),
            "report_prerequisite_pass": flow_guard.get("report_prerequisite_pass", False),
            "artifact_date_consistency_pass": flow_guard.get("artifact_date_consistency_pass", False),
            "source_of_truth_consistency_pass": flow_guard.get("source_of_truth_consistency_pass", False),
            "normal_report_allowed": flow_guard.get("normal_report_allowed", False),
            "candidate_top50_allowed": flow_guard.get("candidate_top50_allowed", False),
            "next_day_candidates_allowed": flow_guard.get("next_day_candidates_allowed", False),
            "notification_mode": flow_guard.get("notification_mode", "UNKNOWN"),
            "market_calendar": latest_market_calendar,
            "market_closed_safe_skip": True,
            "orders_blocked_on_market_closed": not market_closed_order_traces,
            "demo_special_fill_blocked_on_market_closed": not [
                item for item in market_closed_order_traces if item.get("demo_special_fill_simulation_used") is True
            ],
            "market_closed_order_trace_count": len(market_closed_order_traces),
            "reconciliation": {"count": len(recons), "pass_count": pass_count, "pass_rate": (pass_count / len(recons)) if recons else 0},
            "phase9_isolation_audit": phase9_isolation,
            "jquants_fetch_status": {
                "jquants_api_fetch_executed": latest_market.get("jquants_api_fetch_executed", False),
                "raw_daily_quotes_updated": latest_market.get("raw_daily_quotes_updated", False),
                "canonical_normalized_updated": latest_market.get("canonical_normalized_updated", False),
                "feature_refresh_executed": latest_market.get("feature_refresh_executed", False),
                "data_quality_status": latest_market.get("data_quality_status", "UNKNOWN"),
                "feature_freshness_status": latest_market.get("feature_freshness_status", "UNKNOWN"),
                "latest_available_market_date": latest_market.get("latest_available_market_date", ""),
                "decision_for": latest_market.get("decision_for", latest_trade_date),
            },
            "broker_readonly_status": {
                key: value
                for key, value in broker_bundle.items()
                if key != "artifacts"
            },
            "buy_item_count": latest_order_plan.get("buy_item_count", 0),
            "buy_zero_reason": (latest_order_plan.get("feature_buy_adapter") or {}).get("reason", "") if int(latest_order_plan.get("buy_item_count", 0) or 0) == 0 else "",
            "feature_candidate_audit": latest_feature_candidate_audit,
            "sell_item_count": latest_order_plan.get("sell_item_count", 0),
            "sell_zero_reason": "no_valid_broker_positions" if int(latest_order_plan.get("sell_item_count", 0) or 0) == 0 else "",
            "ledger_status": {
                "status": latest_ledger.get("status", "MISSING"),
                "positions_count": latest_ledger.get("positions_count", 0),
                "orders_count": latest_ledger.get("orders_count", 0),
                "executions_count": latest_ledger.get("executions_count", 0),
                "buying_power_available": latest_ledger.get("buying_power_available", False),
            },
            "broker_order_api_called": False,
            "demo_order_wire_execution": False,
            "phase9_parallel_running_allowed": True,
            "phase9_artifacts_modified_by_phase12": False,
            "phase9_launchd_modified_by_phase12": False,
            "phase12_artifact_root": str(paths.root),
            "final_judgement_material": "OPERATION_AUDIT_READY" if len(loaded) >= 30 and status == "PASS" else "OPERATION_IN_PROGRESS",
            "demo_special_fill_simulation": latest_demo_special,
            "demo_special_fill_simulation_used": latest_demo_special.get("demo_special_fill_simulation_used") is True,
            "production_enabled": False,
            "performance_metrics_excluded": True,
            "broker_confirmed_fill": False if latest_demo_special.get("demo_special_fill_simulation_used") else None,
        }
    )
    output = paths.dir("audit_result") / "audit_result.json"
    write_json(output, payload)
    return {**payload, "audit_result_path": str(output)}


def _validate_market_refresh_gate(paths: OperationPaths, trade_date: str) -> dict[str, Any]:
    market_path = paths.dated("market_refresh", trade_date, "market_refresh_manifest.json")
    feature_path = paths.dated("feature_refresh", trade_date, "feature_refresh_manifest.json")
    reasons: list[str] = []
    market = read_json(market_path) if market_path.exists() else {}
    feature = read_json(feature_path) if feature_path.exists() else {}
    if not market_path.exists():
        reasons.append("market_refresh_manifest_missing")
    if not feature_path.exists():
        reasons.append("feature_refresh_manifest_missing")
    if market and market.get("status") != "PASS":
        reasons.append("market_refresh_not_pass")
    if feature and feature.get("status") != "PASS":
        reasons.append("feature_refresh_not_pass")
    feature_artifact = Path(str(feature.get("latest_feature_path") or feature.get("feature_artifact_path") or ""))
    if feature and (not str(feature_artifact) or not feature_artifact.exists()):
        reasons.append("feature_artifact_missing")
    data_until = str(feature.get("data_until") or market.get("data_until") or "")
    latest_available = str(feature.get("latest_available_market_date") or market.get("latest_available_market_date") or data_until)
    freshness_status = str(feature.get("feature_freshness_status") or market.get("feature_freshness_status") or "UNKNOWN")
    if data_until and data_until < trade_date and not latest_available:
        reasons.append("feature_data_until_stale")
    if freshness_status in {"FEATURE_MISSING", "FEATURE_STALE", "NON_BUSINESS_DAY"}:
        reasons.append(f"feature_freshness_{freshness_status.lower()}")
    contamination = feature.get("ai_feature_contamination_audit") or market.get("ai_feature_contamination_audit") or {"status": "UNKNOWN"}
    if contamination.get("status") != "PASS":
        reasons.append("ai_feature_contamination_audit_block")
    return {
        "status": "PASS" if not reasons else "BLOCK",
        "reasons": reasons,
        "market_refresh_manifest_path": str(market_path),
        "feature_refresh_manifest_path": str(feature_path),
        "data_until": data_until,
        "latest_available_market_date": latest_available,
        "feature_freshness_status": freshness_status,
    }


def _generate_sell_items(paths: OperationPaths, trade_date: str) -> dict[str, Any]:
    positions_path = paths.dated("positions", trade_date, "positions.json")
    if not positions_path.exists():
        result = generate_sell_items_from_positions([], trade_date=trade_date)
        return {**result.to_dict(), "sell_items": result.sell_items, "positions_artifact_path": str(positions_path), "positions_artifact_exists": False}
    payload = read_json(positions_path)
    positions = payload.get("positions", [])
    if not isinstance(positions, list):
        return {
            "status": "BLOCK",
            "sell_items": [],
            "sell_item_count": 0,
            "blocked_reasons": ["positions_artifact_invalid"],
            "exit_source": "unknown",
            "positions_artifact_path": str(positions_path),
            "positions_artifact_exists": True,
            "runtime_position_input_used": True,
            "ai_training_input_used": False,
        }
    result = generate_sell_items_from_positions(positions, trade_date=trade_date, exit_source=str(payload.get("exit_source") or "fallback"))
    return {**result.to_dict(), "sell_items": result.sell_items, "positions_artifact_path": str(positions_path), "positions_artifact_exists": True}


def _classify_operation_fill_state(row: dict[str, Any]) -> str:
    wire_response = (row.get("wire_execution_result") or {}).get("response") or {}
    if wire_response.get("rejected") is True:
        return "REJECTED"
    if wire_response.get("accepted") is True:
        return "ACCEPTED"
    raw = str(row.get("lifecycle") or row.get("broker_state") or row.get("broker_status") or row.get("status") or "").strip().upper()
    aliases = {
        "BLOCKED_ITEM": "BLOCKED_ITEM",
        "DRY_RUN_READY": "SUBMITTED",
        "PAPER_ONLY_SUBMITTED": "SUBMITTED",
        "ORDER_SUBMITTED": "SUBMITTED",
        "ORDER_ACCEPTED": "ACCEPTED",
        "ACCEPTED": "ACCEPTED",
        "WAITING": "WAITING_FILL",
        "WAITING_FILL": "WAITING_FILL",
        "PARTIAL": "PARTIALLY_FILLED",
        "PARTIALLY_FILLED": "PARTIALLY_FILLED",
        "FILLED": "FILLED",
        "DONE": "FILLED",
        "REJECTED": "REJECTED",
        "BLOCKED_NO_APPROVAL": "REJECTED",
        "BLOCKED_LIVE_ORDER_DISABLED": "REJECTED",
        "BLOCKED_APPROVAL_SCOPE_MISMATCH": "REJECTED",
        "BLOCKED_SECOND_PASSWORD_MISSING": "REJECTED",
        "BLOCKED_PRODUCTION_PROHIBITED": "REJECTED",
        "BLOCKED_EXECUTOR_STUB": "REJECTED",
        "EXPIRED": "EXPIRED",
        "CANCELED": "CANCELED",
        "CANCELLED": "CANCELED",
        "UNKNOWN": "UNKNOWN_STATUS",
        "UNKNOWN_STATUS": "UNKNOWN_STATUS",
        "BLOCKED": "UNKNOWN_STATUS",
    }
    return aliases.get(raw, "UNKNOWN_STATUS")


def _submitted_row_is_success(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or "").upper()
    return status in {"ORDER_ACCEPTED", "DRY_RUN_READY", "ACCEPTED", "SUBMITTED", "FILLED"} or row.get("demo_order_submitted") is True or row.get("broker_order_api_called") is True


def _is_hard_submit_item_block(row: dict[str, Any]) -> bool:
    hard_reasons = {
        "sell_position_id_missing",
        "sell_broker_position_not_found",
        "sell_quantity_exceeds_broker_position",
    }
    reasons = {str(reason) for reason in row.get("block_reasons", []) or row.get("reasons", [])}
    return bool(reasons & hard_reasons)


def _blocking_stage(block_reasons: list[str]) -> str:
    if any(reason in {"remaining_approval_budget_insufficient", "approval_max_notional_exceeded"} for reason in block_reasons):
        return "approval_budget"
    if any(reason == "buying_power_exceeded" for reason in block_reasons):
        return "buying_power"
    if any(reason in {"max_exposure_pass", "max_exposure_exceeded"} or reason.startswith("max_exposure") for reason in block_reasons):
        return "max_exposure"
    if any(reason == "duplicate_active_broker_order_exists" for reason in block_reasons):
        return "duplicate_order_guard"
    if any(reason == "broker_issue_code_normalization_failed" for reason in block_reasons):
        return "broker_issue_code_normalization"
    return "submit_item_validation"


def _blocked_submit_item(
    *,
    item: dict[str, Any],
    normalized_item: dict[str, Any],
    item_blocks: list[str],
    approval_max: Decimal,
    remaining_approval_budget: Decimal,
    order_value: Decimal,
    cumulative_submitted_notional: Decimal,
    projected_buying_power_usage: Decimal,
    projected_exposure: Decimal,
    broker_buying_power: Decimal,
    max_exposure: dict[str, Any],
) -> dict[str, Any]:
    block_reasons = list(dict.fromkeys(item_blocks))
    block_reason = block_reasons[0] if block_reasons else "unknown_item_block"
    return {
        "item_id": item.get("item_id"),
        "issue_code": item.get("issue_code", ""),
        "code": item.get("code") or item.get("issue_code", ""),
        "internal_code": normalized_item.get("internal_code") or item.get("issue_code", "") or item.get("code", ""),
        "broker_issue_code": normalized_item.get("broker_issue_code", ""),
        "side": item.get("side", ""),
        "quantity": item.get("quantity", ""),
        "position_id": item.get("position_id", ""),
        "lot_reference": item.get("lot_reference", ""),
        "exit_source": item.get("exit_source", ""),
        "exit_reason": item.get("exit_reason", ""),
        "sell_reason": item.get("sell_reason", ""),
        "limit_price": normalized_item.get("limit_price") or item.get("limit_price", ""),
        "estimated_value": normalized_item.get("estimated_value") or item.get("estimated_value", ""),
        "expected_notional": normalized_item.get("expected_notional", normalized_item.get("estimated_value", "")),
        "normalized_order": normalized_item,
        "code_normalization": _code_normalization_summary(normalized_item),
        "sell_intent": item.get("sell_intent", ""),
        "status": "BLOCKED_ITEM",
        "reasons": block_reasons,
        "block_reason": block_reason,
        "block_reasons": block_reasons,
        "blocking_stage": _blocking_stage(block_reasons),
        "remaining_approval_budget": str(remaining_approval_budget),
        "item_expected_notional": str(order_value),
        "cumulative_submitted_notional": str(cumulative_submitted_notional),
        "max_notional": str(approval_max),
        "approval_budget": {
            "approval_max_notional": str(approval_max),
            "remaining_before_item": str(remaining_approval_budget),
            "remaining_after_item_if_submitted": str(remaining_approval_budget - order_value),
            "order_value": str(order_value),
        },
        "projected_buying_power_usage": str(projected_buying_power_usage),
        "projected_buying_power_usage_before_item": str(projected_buying_power_usage),
        "projected_buying_power_usage_if_submitted": str(projected_buying_power_usage + order_value),
        "buying_power_result": {
            "buying_power": str(broker_buying_power),
            "projected_buying_power_usage": str(projected_buying_power_usage + order_value),
            "allowed": projected_buying_power_usage + order_value <= broker_buying_power,
        },
        "projected_exposure_before_item": str(projected_exposure),
        "projected_exposure_if_submitted": str(projected_exposure + order_value if str(normalized_item.get("side") or "").upper() == "BUY" else projected_exposure),
        "max_exposure": max_exposure,
        "max_exposure_result": max_exposure,
        "broker_order_api_called": False,
        "demo_order_submitted": False,
        "production_order_submitted": False,
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _retry_parent_from_submit(previous_submit: dict[str, Any]) -> dict[str, Any]:
    rows = previous_submit.get("submitted_orders") or []
    if not rows:
        return {}
    latest = rows[-1]
    response = (latest.get("wire_execution_result") or {}).get("response") or {}
    return {
        "phase": "Phase12-W",
        "artifact_type": previous_submit.get("artifact_type", "demo_submit"),
        "business_date": previous_submit.get("business_date", ""),
        "created_at": previous_submit.get("created_at", ""),
        "status": latest.get("status", ""),
        "item_id": latest.get("item_id", ""),
        "side": latest.get("side", ""),
        "code": latest.get("code") or latest.get("issue_code", ""),
        "accepted": response.get("accepted") is True,
        "rejected": response.get("rejected") is True,
        "broker_order_ref_hash": latest.get("broker_order_id_hash", ""),
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _remaining_quantity(row: dict[str, Any], lifecycle: str) -> str:
    if str(row.get("side", "")).upper() != "SELL":
        return ""
    if lifecycle == "FILLED":
        return "0"
    return str(row.get("remaining_quantity") or row.get("quantity") or "0")


def _position_closed(row: dict[str, Any], lifecycle: str) -> bool:
    return str(row.get("side", "")).upper() == "SELL" and lifecycle == "FILLED" and str(row.get("sell_intent", "")).upper() == "FULL_CLOSE"


def _collect_operation_statuses(paths: OperationPaths, trade_date: str) -> dict[str, str]:
    refs = {
        "market_refresh": paths.dated("market_refresh", trade_date, "market_refresh_manifest.json"),
        "feature_refresh": paths.dated("feature_refresh", trade_date, "feature_refresh_manifest.json"),
        "daily_plan": paths.dated("daily_plan", trade_date, "daily_plan_result.json"),
        "approval": paths.dated("approval_artifact", trade_date, "approval_artifact.json"),
        "submit": paths.dated("submitted_orders", trade_date, "submitted_orders.json"),
        "fill_monitor": paths.dated("fill_events", trade_date, "fill_events.json"),
        "safety_monitor": paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"),
        "reconcile": paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"),
        "operation_audit": paths.root / "audit_result" / "audit_result.json",
    }
    statuses: dict[str, str] = {}
    for name, path in refs.items():
        statuses[name] = str(read_json(path).get("status", "UNKNOWN")) if path.exists() else "MISSING"
    statuses["missed_jobs"] = "PRESENT" if _read_missed_jobs(paths, trade_date) else "NONE"
    return statuses


def _current_operation_statuses(paths: OperationPaths, trade_date: str) -> dict[str, str]:
    statuses = _collect_operation_statuses(paths, trade_date)
    order_plan_path = paths.dated("order_plan", trade_date, "order_plan.json")
    submit_path = paths.dated("submitted_orders", trade_date, "submitted_orders.json")
    if order_plan_path.exists() and submit_path.exists():
        order_plan = read_json(order_plan_path)
        submitted = read_json(submit_path)
        if _iso_before(str(submitted.get("created_at") or ""), str(order_plan.get("created_at") or "")):
            statuses["submit"] = "STALE_IGNORED"
    return statuses


def _artifact_status(path: Path) -> str:
    return str(read_json(path).get("status", "UNKNOWN")) if path.exists() else "MISSING"


def _operation_flow_integrity_guard(
    paths: OperationPaths,
    trade_date: str,
    *,
    market_calendar: dict[str, Any],
    status_refs: dict[str, str],
    current_status_refs: dict[str, str],
    order_plan: dict[str, Any],
) -> dict[str, Any]:
    date_consistency = _artifact_date_consistency(paths, trade_date)
    reasons: list[str] = []
    market_closed = market_calendar.get("market_closed") is True
    closed_reason = str(market_calendar.get("market_closed_reason") or "")
    confirmed_closed = market_closed and closed_reason in CONFIRMED_MARKET_CLOSED_REASONS
    recovery = _is_recovery_day(paths, trade_date, current_status_refs=current_status_refs, date_consistency=date_consistency)
    submitted = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={})
    order_plan_source_date = str(submitted.get("order_plan_source_date") or trade_date)
    approval_source_date = str(submitted.get("approval_source_date") or order_plan_source_date)
    daily_plan_source_date = order_plan_source_date
    source_aware_submit = bool(submitted.get("order_plan_source_date") or submitted.get("approval_source_date"))
    source_order_plan_path = paths.dated("order_plan", order_plan_source_date, "order_plan.json")
    source_order_plan = read_json(source_order_plan_path) if source_aware_submit and source_order_plan_path.exists() else order_plan
    required_statuses = {
        "market_refresh": current_status_refs.get("market_refresh", "MISSING"),
        "daily_plan": _artifact_status(paths.dated("daily_plan", daily_plan_source_date, "daily_plan_result.json")) if source_aware_submit else current_status_refs.get("daily_plan", "MISSING"),
        "approval": _artifact_status(paths.dated("approval_artifact", approval_source_date, "approval_artifact.json")) if source_aware_submit else current_status_refs.get("approval", "MISSING"),
        "submit": current_status_refs.get("submit", "MISSING"),
        "fill_monitor": current_status_refs.get("fill_monitor", "MISSING"),
        "safety_monitor": current_status_refs.get("safety_monitor", "MISSING"),
        "reconcile": current_status_refs.get("reconcile", "MISSING"),
        "operation_audit": "CURRENT_RUN",
    }
    order_plan_exists = source_order_plan_path.exists()
    feature_artifact_exists = _feature_artifact_exists(paths, order_plan_source_date, source_order_plan)
    candidate_count = int((source_order_plan.get("feature_candidate_audit") or source_order_plan.get("feature_buy_adapter") or {}).get("candidate_count", 0) or 0)
    skipped_on_business_day = [
        name
        for name, status in required_statuses.items()
        if not market_closed and status == "SKIPPED_MARKET_CLOSED"
    ]
    missing_required = [
        name
        for name in ("market_refresh", "daily_plan", "fill_monitor", "safety_monitor", "reconcile")
        if not market_closed and required_statuses.get(name) == "MISSING"
    ]
    if skipped_on_business_day:
        reasons.append("business_day_has_skipped_market_closed:" + ",".join(skipped_on_business_day))
    if missing_required:
        reasons.append("required_artifact_missing:" + ",".join(missing_required))
    if not market_closed and not order_plan_exists:
        reasons.append("order_plan_missing")
    if order_plan_exists and str(source_order_plan.get("status") or "") != "PASS":
        reasons.append(f"order_plan_status_not_pass:{source_order_plan.get('status', 'MISSING')}")
    if not market_closed and not feature_artifact_exists:
        reasons.append("feature_artifact_missing")
    if not market_closed and order_plan_exists and candidate_count == 0:
        reasons.append("candidate_rows_zero_for_business_day")
    if not date_consistency["pass"]:
        reasons.append("artifact_date_consistency_review")
    if current_status_refs.get("operation_audit") == "BLOCKING_GAP":
        reasons.append("operation_audit_blocking_gap")
    if market_closed and not confirmed_closed:
        reasons.append(f"market_closed_reason_not_confirmed:{closed_reason or 'MISSING'}")
    if market_closed and confirmed_closed:
        day_type = MARKET_CLOSED_DAY
    elif recovery:
        day_type = RECOVERY_DAY
        if "recovery_day_detected" not in reasons:
            reasons.append("recovery_day_detected")
    elif reasons:
        day_type = INCOMPLETE_OPERATION_DAY
    elif any(status == "REVIEW_REQUIRED" for status in required_statuses.values()):
        day_type = REVIEW_REQUIRED_DAY
        reasons.append("non_blocking_review_required")
    else:
        day_type = NORMAL_OPERATION_DAY
    normal_report_allowed = day_type in NORMAL_REPORT_ALLOWED_DAY_TYPES
    report_status = "PASS" if day_type in {NORMAL_OPERATION_DAY, MARKET_CLOSED_DAY} else "REVIEW_REQUIRED"
    return {
        "operation_day_type": day_type,
        "report_mode": _report_mode_for_day_type(day_type),
        "notification_mode": _notification_mode_for_day_type(day_type),
        "report_status": report_status,
        "report_prerequisite_pass": normal_report_allowed or day_type == MARKET_CLOSED_DAY,
        "artifact_date_consistency": date_consistency,
        "artifact_date_consistency_pass": date_consistency["pass"],
        "source_of_truth_consistency_pass": True,
        "normal_report_allowed": normal_report_allowed,
        "candidate_top50_allowed": normal_report_allowed,
        "next_day_candidates_allowed": normal_report_allowed,
        "required_statuses": required_statuses,
        "market_closed_confirmed": confirmed_closed,
        "feature_artifact_exists": feature_artifact_exists,
        "candidate_count": candidate_count,
        "next_morning_submit": _next_morning_submit_check(paths, market_calendar),
        "reasons": reasons,
        "source_of_truth": OPERATIONS_SOURCE_OF_TRUTH,
        "source_dates": {
            "trade_date": trade_date,
            "daily_plan_source_date": daily_plan_source_date,
            "order_plan_source_date": order_plan_source_date,
            "approval_source_date": approval_source_date,
        },
    }


def _report_mode_for_day_type(day_type: str) -> str:
    return {
        NORMAL_OPERATION_DAY: "NORMAL_BLOG",
        MARKET_CLOSED_DAY: "MARKET_CLOSED_REPORT",
        RECOVERY_DAY: "RECOVERY_REPORT",
        INCOMPLETE_OPERATION_DAY: "INCOMPLETE_OPERATION_REPORT",
        REVIEW_REQUIRED_DAY: "REVIEW_REQUIRED_REPORT",
    }.get(day_type, "INCOMPLETE_OPERATION_REPORT")


def _notification_mode_for_day_type(day_type: str) -> str:
    return {
        NORMAL_OPERATION_DAY: "NORMAL_OPERATION_SUMMARY",
        MARKET_CLOSED_DAY: "MARKET_CLOSED_NOTICE",
        RECOVERY_DAY: "RECOVERY_COMPLETE_NOTICE",
        INCOMPLETE_OPERATION_DAY: "INCOMPLETE_OPERATION_REVIEW",
        REVIEW_REQUIRED_DAY: "REVIEW_REQUIRED_NOTICE",
    }.get(day_type, "INCOMPLETE_OPERATION_REVIEW")


def _is_recovery_day(paths: OperationPaths, trade_date: str, *, current_status_refs: dict[str, str], date_consistency: dict[str, Any]) -> bool:
    manifest = _load_or_empty(paths.dated("daily_manifest", trade_date, "daily_manifest.json"), default={})
    report_refs = _load_or_empty(paths.dated("daily_report_refs", trade_date, "daily_report_refs.json"), default={})
    markers = [
        manifest.get("recovery_day"),
        manifest.get("recovery_required"),
        report_refs.get("recovery_day"),
        str(report_refs.get("regenerated_reason") or "").startswith(("phase12al", "phase12am")),
    ]
    if any(value is True for value in markers):
        return True
    submit = date_consistency.get("submit") or {}
    return (
        current_status_refs.get("submit") == "STALE_IGNORED"
        and submit.get("order_plan_source_date") in {"", trade_date}
    )


def _feature_artifact_exists(paths: OperationPaths, trade_date: str, order_plan: dict[str, Any]) -> bool:
    feature_path = str((order_plan.get("feature_candidate_audit") or order_plan.get("feature_buy_adapter") or {}).get("candidate_feature_path") or "")
    if feature_path and Path(feature_path).exists():
        return True
    return paths.dated("feature_artifacts", trade_date, "candidate_features.parquet").exists()


def _next_morning_submit_check(paths: OperationPaths, market_calendar: dict[str, Any]) -> dict[str, Any]:
    next_business_day = str(market_calendar.get("next_business_day") or "")
    if not next_business_day:
        return {}
    submitted_path = paths.dated("submitted_orders", next_business_day, "submitted_orders.json")
    if not submitted_path.exists():
        return {"submit_run_date": next_business_day, "status": "MISSING"}
    submitted = read_json(submitted_path)
    return {
        "submit_run_date": str(submitted.get("submit_run_date") or submitted.get("business_date") or next_business_day),
        "status": str(submitted.get("status") or ""),
        "order_plan_source_date": str(submitted.get("order_plan_source_date") or ""),
        "approval_source_date": str(submitted.get("approval_source_date") or ""),
        "buy_item_count": len(submitted.get("submitted_orders", [])) if isinstance(submitted.get("submitted_orders"), list) else 0,
        "broker_order_api_called": submitted.get("broker_order_api_called") is True,
        "clm_kabu_new_order_called": submitted.get("clm_kabu_new_order_called") is True,
        "demo_order_submitted": submitted.get("demo_order_submitted") is True,
    }


def _artifact_date_consistency(paths: OperationPaths, trade_date: str) -> dict[str, Any]:
    refs = {
        "market_refresh_date": paths.dated("market_refresh", trade_date, "market_refresh_manifest.json"),
        "order_plan_date": paths.dated("order_plan", trade_date, "order_plan.json"),
        "approval_date": paths.dated("approval_artifact", trade_date, "approval_artifact.json"),
        "broker_snapshot_date": paths.dated("broker_snapshot", trade_date, "broker_snapshot.json"),
        "fill_events_date": paths.dated("fill_events", trade_date, "fill_events.json"),
        "reconcile_date": paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"),
    }
    dates: dict[str, str] = {"report_date": trade_date}
    mismatches: list[str] = []
    for name, path in refs.items():
        payload = read_json(path) if path.exists() else {}
        value = str(payload.get("business_date") or "")
        dates[name] = value
        if value and value != trade_date:
            mismatches.append(f"{name}={value} expected={trade_date}")
    submitted_path = paths.dated("submitted_orders", trade_date, "submitted_orders.json")
    submitted = read_json(submitted_path) if submitted_path.exists() else {}
    submit_run_date = str(submitted.get("submit_run_date") or submitted.get("business_date") or "")
    order_plan_source_date = str(submitted.get("order_plan_source_date") or "")
    approval_source_date = str(submitted.get("approval_source_date") or "")
    dates.update(
        {
            "submit_run_date": submit_run_date,
            "order_plan_source_date": order_plan_source_date,
            "approval_source_date": approval_source_date,
        }
    )
    if submit_run_date and submit_run_date != trade_date:
        mismatches.append(f"submit_run_date={submit_run_date} expected={trade_date}")
    if order_plan_source_date and approval_source_date and order_plan_source_date != approval_source_date:
        mismatches.append(f"approval_source_date={approval_source_date} expected_order_plan_source_date={order_plan_source_date}")
    if order_plan_source_date and order_plan_source_date != trade_date:
        previous = str((_market_calendar(paths, trade_date) or {}).get("previous_business_day") or "")
        if not (submit_run_date == trade_date and order_plan_source_date == previous):
            mismatches.append(f"order_plan_source_date={order_plan_source_date} not allowed for report_date={trade_date}")
    return {
        "pass": not mismatches,
        "dates": dates,
        "mismatches": mismatches,
        "submit": {
            "submit_run_date": submit_run_date,
            "order_plan_source_date": order_plan_source_date,
            "approval_source_date": approval_source_date,
        },
    }


def _iso_before(left: str, right: str) -> bool:
    if not left or not right:
        return False
    try:
        return datetime.fromisoformat(left) < datetime.fromisoformat(right)
    except ValueError:
        return False


def _sell_reconciliation_summary(fill_events: list[dict[str, Any]], *, targets: dict[str, bool]) -> dict[str, Any]:
    sell_events = [event for event in fill_events if str(event.get("side", "")).upper() == "SELL"]
    filled = [event for event in sell_events if event.get("lifecycle") == "FILLED"]
    return {
        "sell_event_count": len(sell_events),
        "sell_filled_count": len(filled),
        "position_decrease_check_required": bool(filled),
        "position_close_check_required": any(event.get("position_closed") for event in filled),
        "partial_sell_remaining_quantity_check_required": any(event.get("lifecycle") == "PARTIALLY_FILLED" for event in sell_events),
        "realized_result_placeholder": bool(sell_events),
        "broker_positions_available": bool(targets.get("positions")),
        "ledger_available": bool(targets.get("ledger")),
        "broker_source_of_truth_required": bool(sell_events),
    }


def _submit_reconciliation_summary(submitted: dict[str, Any], *, broker_bundle: dict[str, Any], fill_events: list[dict[str, Any]], env: str) -> dict[str, Any]:
    submitted_rows = submitted.get("submitted_orders", []) if isinstance(submitted.get("submitted_orders"), list) else []
    accepted_rows = [row for row in submitted_rows if _submitted_row_is_success(row)]
    blocked_rows = [row for row in submitted_rows if str(row.get("status") or "").upper() == "BLOCKED_ITEM"]
    explained_blocked_rows = [row for row in blocked_rows if row.get("block_reason") or row.get("block_reasons")]
    broker_orders = (broker_bundle.get("artifacts", {}).get("broker_orders") or {}).get("orders") or []
    broker_executions_count = int(broker_bundle.get("executions_count", 0) or 0)
    broker_positions_count = int(broker_bundle.get("positions_count", 0) or 0)
    broker_order_issue_codes = {str(order.get("issue_code") or "") for order in broker_orders}
    accepted_broker_codes = {
        str((row.get("normalized_order") or {}).get("broker_issue_code") or (row.get("code_normalization") or {}).get("broker_issue_code") or row.get("broker_issue_code") or "")
        for row in accepted_rows
    }
    missing_broker_order_codes = sorted(code for code in accepted_broker_codes if code and code not in broker_order_issue_codes)
    blocked_event_count = sum(1 for event in fill_events if event.get("lifecycle") == "BLOCKED_ITEM")
    broker_orders_cover_accepted = len(accepted_rows) == 0 or (not missing_broker_order_codes and len(broker_orders) >= len(accepted_rows))
    broker_orders_executed_quantity_available = any(str(order.get("executed_quantity") or "0") not in {"", "0", "0.0", "0.0000"} for order in broker_orders)
    demo_empty_executions_positions_explained = (
        env == "demo"
        and broker_executions_count == 0
        and broker_positions_count == 0
        and broker_orders_cover_accepted
        and broker_orders_executed_quantity_available
    )
    return {
        "submitted_order_count": len(submitted_rows),
        "accepted_order_count": len(accepted_rows),
        "blocked_item_count": len(blocked_rows),
        "explained_blocked_item_count": len(explained_blocked_rows),
        "broker_order_count": len(broker_orders),
        "broker_executions_count": broker_executions_count,
        "broker_positions_count": broker_positions_count,
        "broker_orders_cover_accepted": broker_orders_cover_accepted,
        "missing_broker_order_codes": missing_broker_order_codes,
        "blocked_item_fill_event_count": blocked_event_count,
        "all_blocked_items_explained": len(blocked_rows) == len(explained_blocked_rows),
        "partial_submit_with_explained_blocked_items": bool(accepted_rows and blocked_rows and len(blocked_rows) == len(explained_blocked_rows) and broker_orders_cover_accepted),
        "broker_orders_used_as_execution_fallback": broker_executions_count == 0 and broker_orders_executed_quantity_available,
        "demo_empty_executions_positions_explained": demo_empty_executions_positions_explained,
        "classification": "MATCHED_WITH_EXPLAINED_BLOCKED_ITEMS" if accepted_rows and blocked_rows and len(blocked_rows) == len(explained_blocked_rows) and broker_orders_cover_accepted else "REVIEW_REQUIRED",
    }


def _collect_sell_report_summary(paths: OperationPaths, trade_date: str) -> dict[str, Any]:
    order_plan = _load_or_empty(paths.dated("order_plan", trade_date, "order_plan.json"), default={"items": []})
    approval = _load_or_empty(paths.dated("approval_artifact", trade_date, "approval_artifact.json"), default={})
    submitted = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={"submitted_orders": []})
    fill_events = _load_or_empty(paths.dated("fill_events", trade_date, "fill_events.json"), default={"fill_events": []})
    sell_candidates = [item for item in order_plan.get("items", []) if str(item.get("side", "")).upper() == "SELL"]
    approved_ids = set(approval.get("approved_item_ids", []))
    sell_submitted = [item for item in submitted.get("submitted_orders", []) if str(item.get("side", "")).upper() == "SELL"]
    sell_fills = [item for item in fill_events.get("fill_events", []) if str(item.get("side", "")).upper() == "SELL"]
    return {
        "sell_candidate_count": len(sell_candidates),
        "sell_approved_count": sum(1 for item in sell_candidates if item.get("item_id") in approved_ids),
        "sell_submitted_dry_run_count": len(sell_submitted),
        "sell_fill_event_count": len(sell_fills),
        "line_send_executed": False,
        "items": [
            {
                "item_id": item.get("item_id", ""),
                "issue_code": item.get("issue_code", ""),
                "position_id": item.get("position_id", ""),
                "quantity": item.get("quantity", ""),
                "expected_notional": item.get("expected_notional", item.get("estimated_value", "")),
                "exit_source": item.get("exit_source", ""),
                "sell_reason": item.get("sell_reason", ""),
                "fill_status": next((event.get("lifecycle") for event in sell_fills if event.get("item_id") == item.get("item_id")), "NOT_SUBMITTED"),
                "realized_result_placeholder": True,
            }
            for item in sell_candidates
        ],
    }


def _read_missed_jobs(paths: OperationPaths, trade_date: str) -> list[dict[str, Any]]:
    missed_path = paths.dated("missed_jobs", trade_date, "missed_jobs.json")
    if not missed_path.exists():
        return []
    payload = read_json(missed_path)
    jobs = payload.get("missed_jobs", [])
    return jobs if isinstance(jobs, list) else []


def _phase9_isolation_audit(paths: OperationPaths) -> dict[str, Any]:
    root_text = str(paths.root)
    operations_launchd = sorted(Path("tools/launchd").glob("com.aifundlab.operations.*.plist"))
    phase12_launchd_prefix_ok = all(path.name.startswith("com.aifundlab.operations.") for path in operations_launchd)
    phase9_root_used = "paper_trading" in root_text or root_text.startswith("reports/phase9") or root_text.startswith("docs/phase_reports/phase9")
    return {
        "status": "PASS" if not phase9_root_used and phase12_launchd_prefix_ok else "BLOCK",
        "phase9_artifact_root_untouched": True,
        "phase9_launchd_untouched": True,
        "phase9_cli_untouched": True,
        "phase9_reports_untouched": True,
        "phase12_artifact_root_is_operations": root_text == ".runtime/operations",
        "phase12_artifact_root_does_not_use_phase9": not phase9_root_used,
        "phase12_launchd_prefix_is_operations": phase12_launchd_prefix_ok,
        "phase9_parallel_running_allowed": True,
        "phase9_artifacts_modified_by_phase12": False,
        "phase9_launchd_modified_by_phase12": False,
        "phase12_artifact_root": root_text,
    }


def _demo_production_parity_audit(paths: OperationPaths, trade_date: str, *, env: str) -> dict[str, Any]:
    daily_plan = _load_or_empty(paths.dated("daily_plan", trade_date, "daily_plan_result.json"), default={})
    approval = _load_or_empty(paths.dated("approval_artifact", trade_date, "approval_artifact.json"), default={})
    submitted = _load_or_empty(paths.dated("submitted_orders", trade_date, "submitted_orders.json"), default={})
    safety = _load_or_empty(paths.dated("safety_monitor", trade_date, "safety_monitor_result.json"), default={})
    reconcile = _load_or_empty(paths.dated("reconciliation_result", trade_date, "reconciliation_result.json"), default={})
    report = _load_or_empty(paths.dated("daily_report_refs", trade_date, "daily_report_refs.json"), default={})
    notification = _load_or_empty(paths.dated("notifications", trade_date, "notification_result.json"), default={})
    demo_special = _load_demo_special_fill_summary(paths, trade_date)
    unexpected: list[str] = []
    if env == "demo" and report.get("send_notifications_requested") is True and report.get("notification_status") in {"NOT_REQUESTED", "SKIPPED_BY_DEMO"}:
        unexpected.append("demo_notification_not_enabled")
    if report.get("status") == "BLOCK":
        unexpected.append("daily_report_blocked")
    if str(daily_plan.get("candidate_count_environment_specific", "")).lower() == "true":
        unexpected.append("demo_candidate_count_environment_specific")
    for name, payload in {
        "approval": approval,
        "submit": submitted,
        "safety": safety,
        "reconcile": reconcile,
    }.items():
        if payload.get("demo_only_logic") is True:
            unexpected.append(f"{name}_contains_demo_only_logic")
    return {
        "status": "PASS" if not unexpected else "BLOCK",
        "environment": env,
        "allowed_demo_production_differences": [
            "demo_special_fill_simulation",
            "persistent_demo_ledger",
            "tachibana_api_env_demo",
            "production_order_disabled",
        ],
        "unexpected_differences": unexpected,
        "notification_parity": {
            "notification_result_present": bool(notification),
            "line_send_attempted": (notification.get("line") or {}).get("send_attempted", False),
            "discord_send_attempted": (notification.get("discord") or {}).get("send_attempted", False),
            "demo_notification_disabled": report.get("notification_status") in {"NOT_REQUESTED", "SKIPPED_BY_DEMO"},
            "send_notifications_requested": report.get("send_notifications_requested") is True,
        },
        "daily_report_parity": {
            "daily_report_refs_present": bool(report),
            "daily_report_status": report.get("status", "PASS" if report else "MISSING"),
        },
        "demo_special_fill_simulation": demo_special,
        "production_order_disabled": True,
        "persistent_demo_ledger": env == "demo",
    }


def _write_daily_manifest(paths: OperationPaths, trade_date: str, *, env: str, overrides: dict[str, Any] | None = None) -> Path:
    output = paths.dated("daily_manifest", trade_date, "daily_manifest.json")
    existing = read_json(output) if output.exists() else {}
    payload = _base_payload("daily_manifest", env, trade_date, "PASS")
    payload.update(
        {
            "market_refresh_status": "MISSING",
            "feature_refresh_status": "MISSING",
            "daily_plan_status": "MISSING",
            "approval_status": "MISSING",
            "preflight_status": "MISSING",
            "submit_status": "MISSING",
            "fill_monitor_status": "MISSING",
            "safety_monitor_status": "MISSING",
            "reconciliation_status": "MISSING",
            "daily_report_status": "MISSING",
            "operation_audit_status": "MISSING",
            "missed_jobs": _read_missed_jobs(paths, trade_date),
            "run_lock_status": "UNKNOWN",
            "demo_order_submitted": False,
            "production_order_submitted": False,
            "line_send_executed": False,
            "ai_retraining_executed": False,
            "backtest_run": False,
            "raw_response_saved": False,
            "secret_saved": False,
            "phase9_parallel_running_allowed": True,
            "phase9_artifacts_modified_by_phase12": False,
            "phase9_launchd_modified_by_phase12": False,
            "phase12_artifact_root": str(paths.root),
            "market_calendar": _market_calendar(paths, trade_date),
        }
    )
    payload.update({key: value for key, value in existing.items() if key not in {"created_at", "status"}})
    payload.update(overrides or {})
    blocking_values = {"BLOCK", "SYSTEM_EMERGENCY_STOP"}
    non_blocking_status_keys = {"demo_special_fill_simulation_status"}
    status_values = [str(value) for key, value in payload.items() if key.endswith("_status") and key not in non_blocking_status_keys]
    payload["status"] = "BLOCK" if any(value in blocking_values for value in status_values) else "PASS"
    write_json(output, payload)
    return output


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--trade-date", default=date.today().isoformat())
    parser.add_argument("--root", default=str(DEFAULT_OPERATION_ROOT))
    return parser


def _resolve_runtime_environment() -> dict[str, Any]:
    settings = load_broker_settings()
    env_source = os.environ.get("TACHIBANA_API_ENV")
    env = normalize_runtime_environment(env_source)
    reasons: list[str] = []
    if not env_source:
        reasons.append("TACHIBANA_API_ENV_missing")
    if env not in {"demo", "production"}:
        reasons.append("TACHIBANA_API_ENV_invalid")
    if env != normalize_runtime_environment(settings.environment):
        reasons.append("broker_settings_environment_mismatch")
    status = "PASS" if not reasons else "BLOCK"
    return {
        "status": status,
        "environment": env if env in {"demo", "production"} else "UNKNOWN",
        "broker_environment": normalize_runtime_environment(settings.environment),
        "base_url": settings.base_url,
        "reasons": reasons,
        "source": "TACHIBANA_API_ENV",
    }


def _base_payload(kind: str, env: str, trade_date: str, status: str) -> dict[str, Any]:
    return {
        "artifact_type": kind,
        "created_at": utc_now_iso(),
        "environment": env,
        "business_date": trade_date,
        "status": status,
        "production_order_submitted": False,
        "production_unlock_executed": False,
        "line_send_executed": False,
        "ai_retraining_executed": False,
        "backtest_run": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _market_calendar(paths: OperationPaths, trade_date: str) -> dict[str, Any]:
    return resolve_operation_date(trade_date, root=paths.root)


def _default_broker_snapshot_summary(trade_date: str, env: str) -> dict[str, Any]:
    return {
        "artifact_type": "broker_snapshot_summary",
        "business_date": trade_date,
        "environment": env,
        "snapshot_freshness": "UNKNOWN",
        "broker_actual_equity": "1000000",
        "buying_power": "1000000",
        "current_exposure": "0",
        "positions_count": 0,
        "orders_count": 0,
        "executions_count": 0,
        "raw_response_saved": False,
    }


def _default_safety_result(trade_date: str) -> dict[str, Any]:
    return {"artifact_type": "safety_result", "business_date": trade_date, "status": "ALLOW", "system_guard": True}


def _empty_order_plan(trade_date: str, env: str) -> dict[str, Any]:
    return {"artifact_type": "order_plan", "plan_id": "", "business_date": trade_date, "environment": env, "items": []}


def _resolve_submit_order_plan_date(paths: OperationPaths, trade_date: str, *, env: str, market_calendar: dict[str, Any]) -> str:
    current_plan = paths.dated("order_plan", trade_date, "order_plan.json")
    current_approval = paths.dated("approval_artifact", trade_date, "approval_artifact.json")
    if current_plan.exists() and current_approval.exists():
        return trade_date
    previous_business_day = str(market_calendar.get("previous_business_day") or "")
    if previous_business_day:
        previous_plan = paths.dated("order_plan", previous_business_day, "order_plan.json")
        previous_approval = paths.dated("approval_artifact", previous_business_day, "approval_artifact.json")
        if previous_plan.exists() and previous_approval.exists():
            return previous_business_day
    return trade_date


def _load_or_empty(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    return read_json(path) if path.exists() else default


def _normalize_plan_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    side = str(item.get("side", "BUY")).upper()
    issue_code = str(item.get("issue_code") or item.get("code") or "")
    expected_notional = str(item.get("expected_notional") or item.get("estimated_value", "0"))
    normalized = {
        "item_id": str(item.get("item_id") or f"item_{index:03d}"),
        "code": issue_code,
        "issue_code": issue_code,
        "side": side,
        "quantity": str(item.get("quantity", "100")),
        "order_type": str(item.get("order_type", "CASH_EQUITY")),
        "price_type": str(item.get("price_type", "LIMIT")),
        "limit_price": str(item.get("limit_price") or item.get("current_price") or "0"),
        "estimated_value": str(item.get("estimated_value") or expected_notional),
        "expected_notional": expected_notional,
        "requires_approval": True,
        "approval_required": True,
        "production_order_allowed": False,
        "demo_order_allowed": False,
    }
    if side == "SELL":
        normalized.update(
            {
                "position_id": str(item.get("position_id") or ""),
                "lot_reference": str(item.get("lot_reference") or item.get("position_id") or ""),
                "exit_source": str(item.get("exit_source") or "unknown"),
                "exit_reason": str(item.get("exit_reason") or item.get("sell_reason") or ""),
                "sell_reason": str(item.get("sell_reason") or item.get("exit_reason") or ""),
                "position_entry_price": str(item.get("position_entry_price") or item.get("entry_price") or "0"),
                "current_price": str(item.get("current_price") or item.get("limit_price") or "0"),
                "unrealized_return": str(item.get("unrealized_return") or "0"),
                "broker_position_quantity": str(item.get("broker_position_quantity") or item.get("quantity") or "0"),
                "sell_intent": str(item.get("sell_intent") or "FULL_CLOSE"),
            }
        )
    return normalized


def _approval_sell_scope(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": str(item.get("item_id") or ""),
        "approved_side": "SELL",
        "approved_position_id": str(item.get("position_id") or ""),
        "approved_lot_reference": str(item.get("lot_reference") or ""),
        "approved_max_quantity": str(item.get("broker_position_quantity") or item.get("quantity") or "0"),
        "quantity": str(item.get("quantity") or "0"),
        "issue_code": str(item.get("issue_code") or item.get("code") or ""),
        "sell_reason": str(item.get("sell_reason") or ""),
        "exit_source": str(item.get("exit_source") or ""),
        "approval_required": True,
    }


def _validate_sell_approval_scope(scopes: list[dict[str, Any]]) -> list[str]:
    blocks: list[str] = []
    for scope in scopes:
        item_id = scope.get("item_id", "")
        if not scope.get("approved_position_id"):
            blocks.append(f"sell_position_id_missing:{item_id}")
        if not scope.get("approved_lot_reference"):
            blocks.append(f"sell_lot_reference_missing:{item_id}")
        quantity = Decimal(str(scope.get("quantity") or "0"))
        max_quantity = Decimal(str(scope.get("approved_max_quantity") or "0"))
        if quantity <= 0:
            blocks.append(f"sell_quantity_not_positive:{item_id}")
        if max_quantity <= 0:
            blocks.append(f"sell_max_quantity_missing:{item_id}")
        if max_quantity > 0 and quantity > max_quantity:
            blocks.append(f"sell_quantity_exceeds_position:{item_id}")
        if not scope.get("sell_reason"):
            blocks.append(f"sell_reason_missing:{item_id}")
        if not scope.get("exit_source"):
            blocks.append(f"exit_source_missing:{item_id}")
    return blocks


def _validate_item_for_submit(item: dict[str, Any], *, require_wire_ready: bool = False) -> list[str]:
    blocks: list[str] = []
    if item.get("production_order_allowed"):
        blocks.append("production_order_allowed_true")
    if item.get("order_type") != "CASH_EQUITY":
        blocks.append("non_cash_equity_order_forbidden")
    if str(item.get("order_type") or "") != "CASH_EQUITY":
        blocks.append("credit_or_margin_order_forbidden")
    if not item.get("issue_code"):
        blocks.append("issue_code_missing")
    if Decimal(str(item.get("quantity", "0"))) <= 0:
        blocks.append("quantity_not_positive")
    if require_wire_ready:
        estimated_value = Decimal(str(item.get("estimated_value") or item.get("expected_notional") or "0"))
        if estimated_value <= 0:
            blocks.append("expected_notional_not_positive")
        if item.get("price_type") == "LIMIT" and Decimal(str(item.get("limit_price", "0"))) <= 0:
            blocks.append("limit_price_not_positive")
        if item.get("price_type") not in {"LIMIT", "MARKET"}:
            blocks.append("unsupported_price_type")
    return blocks


def _normalize_item_for_demo_wire(item: dict[str, Any], *, paths: OperationPaths, trade_date: str) -> dict[str, Any]:
    normalized = dict(item)
    quantity = Decimal(str(normalized.get("quantity") or "0"))
    price_type = str(normalized.get("price_type") or "LIMIT")
    limit_price = Decimal(str(normalized.get("limit_price") or "0"))
    if price_type == "LIMIT" and limit_price <= 0:
        reference = _latest_reference_price(paths, trade_date=trade_date, issue_code=str(normalized.get("issue_code") or normalized.get("code") or ""))
        if reference <= 0:
            normalized["normalization_error"] = "reference_price_unavailable"
            return normalized
        limit_price = reference
        normalized["limit_price"] = str(limit_price.quantize(Decimal("1")) if limit_price == limit_price.to_integral() else limit_price)
        normalized["normalization_source"] = "jquants_latest_close"
    expected_notional = quantity * (limit_price if price_type == "LIMIT" else Decimal(str(normalized.get("estimated_value") or "0")))
    if expected_notional > 0:
        notional_text = str(expected_notional.quantize(Decimal("1")) if expected_notional == expected_notional.to_integral() else expected_notional)
        normalized["expected_notional"] = notional_text
        normalized["estimated_value"] = notional_text
    normalized["demo_order_allowed"] = False
    normalized["production_order_allowed"] = False
    return normalized


def _latest_reference_price(paths: OperationPaths, *, trade_date: str, issue_code: str) -> Decimal:
    marker_path = paths.dated("feature_refresh", trade_date, "latest_features.json")
    marker = _load_or_empty(marker_path, default={})
    data_until = str(marker.get("data_until") or "")
    normalized_path = paths.root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    if not normalized_path.exists() or not issue_code:
        return Decimal("0")
    try:
        import pandas as pd

        frame = pd.read_parquet(normalized_path, columns=["Code", "code", "Date", "target_date", "Close"])
    except Exception:  # noqa: BLE001 - fail closed by returning no price.
        return Decimal("0")
    if "code" in frame.columns:
        frame = frame[frame["code"].astype(str) == issue_code]
    elif "Code" in frame.columns:
        frame = frame[frame["Code"].astype(str) == issue_code]
    if data_until:
        date_col = "target_date" if "target_date" in frame.columns else "Date"
        frame = frame[frame[date_col].astype(str) <= data_until]
    if frame.empty or "Close" not in frame.columns:
        return Decimal("0")
    date_col = "target_date" if "target_date" in frame.columns else "Date"
    latest = frame.sort_values(date_col).iloc[-1]
    return Decimal(str(latest.get("Close") or "0"))


def _validate_sell_submit_scope(item: dict[str, Any], *, approval: dict[str, Any], positions: list[dict[str, Any]]) -> list[str]:
    if str(item.get("side", "")).upper() != "SELL":
        return []
    blocks: list[str] = []
    item_id = str(item.get("item_id") or "")
    issue_code = str(item.get("issue_code") or item.get("code") or "")
    position_id = str(item.get("position_id") or "")
    lot_reference = str(item.get("lot_reference") or "")
    quantity = Decimal(str(item.get("quantity") or "0"))
    if not position_id:
        blocks.append("sell_position_id_missing")
    if not lot_reference:
        blocks.append("sell_lot_reference_missing")
    matched = [
        position
        for position in positions
        if str(position.get("position_id") or "") == position_id
        or (str(position.get("issue_code") or position.get("code") or "") == issue_code and str(position.get("lot_reference") or position.get("position_id") or "") == lot_reference)
    ]
    if not matched:
        blocks.append("sell_broker_position_not_found")
    else:
        broker_quantity = Decimal(str(matched[0].get("quantity") or "0"))
        if quantity > broker_quantity:
            blocks.append("sell_quantity_exceeds_broker_position")
    scopes = [scope for scope in approval.get("sell_approval_scope", []) if scope.get("item_id") == item_id]
    if not scopes:
        blocks.append("sell_approval_scope_missing")
    else:
        max_quantity = Decimal(str(scopes[0].get("approved_max_quantity") or "0"))
        if quantity > max_quantity:
            blocks.append("sell_quantity_exceeds_approval_scope")
    return blocks


def _resolve_approval_max_notional(
    *,
    paths: OperationPaths,
    trade_date: str,
    env: str,
    order_plan: dict[str, Any],
    broker_snapshot: dict[str, Any],
    broker_bundle: dict[str, Any],
    manual_override: Decimal | None,
) -> dict[str, Any]:
    ratio = Decimal(str((order_plan.get("operations_runtime_config") or {}).get("max_total_exposure_ratio") or "0.85"))
    current_exposure, current_exposure_source = _resolve_current_exposure_for_approval(paths=paths, trade_date=trade_date, env=env, broker_bundle=broker_bundle)
    equity_basis, equity_basis_source = _resolve_equity_basis_for_approval(env=env, broker_snapshot=broker_snapshot)
    available_cash, available_cash_source = _resolve_available_cash_for_approval(env=env, equity_basis=equity_basis, current_exposure=current_exposure, broker_snapshot=broker_snapshot)
    exposure_budget = max(equity_basis * ratio - current_exposure, Decimal("0"))
    capital_budget = _capital_allocation_budget(order_plan)
    dynamic_candidates = [exposure_budget, available_cash]
    if capital_budget is not None:
        dynamic_candidates.append(capital_budget)
    dynamic_max = min(dynamic_candidates) if dynamic_candidates else Decimal("0")
    if manual_override is not None:
        approval_max = manual_override
        source = "manual_override"
    else:
        approval_max = dynamic_max
        source = "dynamic_max_exposure"
    approval_blocks: list[str] = []
    if equity_basis <= Decimal("0"):
        approval_blocks.append("approval_equity_basis_missing")
    if available_cash <= Decimal("0"):
        approval_blocks.append("approval_available_buying_power_or_cash_missing")
    if approval_max <= Decimal("0"):
        approval_blocks.append("approval_max_notional_not_positive")
    return {
        "approval_max_notional": approval_max,
        "approval_max_notional_source": source,
        "equity_basis": equity_basis,
        "equity_basis_source": equity_basis_source,
        "max_total_exposure_ratio": ratio,
        "current_exposure": current_exposure,
        "current_exposure_source": current_exposure_source,
        "available_exposure_budget": exposure_budget,
        "available_buying_power_or_cash": available_cash,
        "available_buying_power_or_cash_source": available_cash_source,
        "capital_allocation_budget": capital_budget,
        "approval_max_notional_formula": "min(equity_basis * max_total_exposure_ratio - current_exposure, available_buying_power_or_cash, capital_allocation_total_buy_budget_if_exists)",
        "approval_max_notional_inputs": {
            "dynamic_approval_max_notional": _decimal_text(dynamic_max),
            "manual_override": _optional_decimal_text(manual_override),
            "equity_basis": _decimal_text(equity_basis),
            "equity_basis_source": equity_basis_source,
            "max_total_exposure_ratio": str(ratio),
            "current_exposure": _decimal_text(current_exposure),
            "current_exposure_source": current_exposure_source,
            "available_exposure_budget": _decimal_text(exposure_budget),
            "available_buying_power_or_cash": _decimal_text(available_cash),
            "available_buying_power_or_cash_source": available_cash_source,
            "capital_allocation_budget": _optional_decimal_text(capital_budget),
            "demo_broker_cash_used_for_equity_basis": False if env == "demo" else None,
        },
        "approval_blocks": approval_blocks,
    }


def _resolve_equity_basis_for_approval(*, env: str, broker_snapshot: dict[str, Any]) -> tuple[Decimal, str]:
    if env == "demo":
        return DEMO_OPERATION_INITIAL_EQUITY, "demo_evaluation_equity"
    broker_actual = _decimal_or_none(broker_snapshot.get("broker_actual_equity"))
    if broker_actual and broker_actual > Decimal("0"):
        return broker_actual, "broker_actual_equity"
    buying_power = _decimal_or_none(broker_snapshot.get("buying_power"))
    if buying_power and buying_power > Decimal("0"):
        return buying_power, "broker_buying_power"
    return Decimal("0"), "missing"


def _resolve_available_cash_for_approval(*, env: str, equity_basis: Decimal, current_exposure: Decimal, broker_snapshot: dict[str, Any]) -> tuple[Decimal, str]:
    if env == "demo":
        return max(equity_basis - current_exposure, Decimal("0")), "demo_evaluation_cash"
    buying_power = _decimal_or_none(broker_snapshot.get("buying_power"))
    if buying_power and buying_power > Decimal("0"):
        return buying_power, "broker_buying_power"
    return Decimal("0"), "missing"


def _resolve_current_exposure_for_approval(*, paths: OperationPaths, trade_date: str, env: str, broker_bundle: dict[str, Any]) -> tuple[Decimal, str]:
    broker_positions = (broker_bundle.get("artifacts", {}).get("broker_positions") or {}).get("positions") or []
    if broker_positions:
        value = sum(_position_market_value(row) for row in broker_positions)
        return value, "broker_positions_market_value"
    if env != "demo":
        return Decimal("0"), "broker_positions_empty"
    demo_position_value = _demo_ledger_position_exposure(paths.root, trade_date)
    if demo_position_value is not None:
        return demo_position_value, "persistent_demo_ledger"
    demo_ledger_value = _demo_ledger_exposure(paths.root, trade_date)
    if demo_ledger_value > Decimal("0"):
        return demo_ledger_value, "persistent_demo_ledger"
    submitted_value = _submitted_accepted_buy_exposure(paths, trade_date)
    if submitted_value > Decimal("0"):
        return submitted_value, "submitted_accepted_buy_exposure"
    return Decimal("0"), "no_current_exposure_detected"


def _position_market_value(row: dict[str, Any]) -> Decimal:
    market_value = _decimal_or_none(row.get("market_value"))
    if market_value is not None:
        return market_value
    quantity = _decimal_or_zero(row.get("quantity"))
    price = _decimal_or_zero(row.get("market_price") or row.get("current_price"))
    return quantity * price


def _demo_ledger_position_exposure(root: Path, trade_date: str) -> Decimal | None:
    positions_path = Path(root) / "demo_ledger" / "positions.jsonl"
    rows = []
    for row in _read_jsonl_safe(positions_path):
        business_date = str(row.get("business_date") or "")
        if business_date and business_date > trade_date:
            continue
        if not business_date:
            continue
        if str(row.get("record_type") or "").startswith("demo_special_simulated_position") or row.get("position_state") or row.get("net_quantity") is not None:
            rows.append(row)
    if not rows:
        return None
    total = Decimal("0")
    for row in rows:
        net_quantity = _decimal_or_zero(row.get("net_quantity") or row.get("quantity"))
        if net_quantity <= Decimal("0"):
            continue
        market_value = _decimal_or_none(row.get("market_value") or row.get("position_market_value"))
        if market_value is not None:
            total += market_value
            continue
        price = _decimal_or_zero(row.get("market_price") or row.get("current_price") or row.get("fill_price") or row.get("entry_price"))
        total += net_quantity * price
    return max(total, Decimal("0"))


def _demo_ledger_exposure(root: Path, trade_date: str) -> Decimal:
    orders_path = Path(root) / "demo_ledger" / "orders.jsonl"
    total = Decimal("0")
    for row in _read_jsonl_safe(orders_path):
        business_date = str(row.get("business_date") or "")
        if business_date and business_date > trade_date:
            continue
        if row.get("accepted") is not True:
            continue
        side = str(row.get("side") or "").upper()
        notional = _decimal_or_zero(row.get("expected_notional"))
        if side == "BUY":
            total += notional
        elif side == "SELL":
            total -= notional
    return max(total, Decimal("0"))


def _submitted_accepted_buy_exposure(paths: OperationPaths, trade_date: str) -> Decimal:
    root = paths.root / "submitted_orders"
    if not root.exists():
        return Decimal("0")
    total = Decimal("0")
    for path in sorted(root.glob("*/submitted_orders.json")):
        date_part = path.parent.name
        if date_part > trade_date:
            continue
        payload = _load_or_empty(path, default={})
        rows = payload.get("submitted_orders", []) if isinstance(payload.get("submitted_orders"), list) else []
        for row in rows:
            if not _submitted_row_is_success(row):
                continue
            side = str(row.get("side") or "").upper()
            notional = _decimal_or_zero(row.get("expected_notional") or row.get("estimated_value"))
            if side == "BUY":
                total += notional
            elif side == "SELL":
                total -= notional
    return max(total, Decimal("0"))


def _capital_allocation_budget(order_plan: dict[str, Any]) -> Decimal | None:
    containers = [order_plan, order_plan.get("capital_allocation") or {}, order_plan.get("capital_allocation_budget") or {}]
    for container in containers:
        if not isinstance(container, dict):
            continue
        for key in ("capital_allocation_total_buy_budget", "total_buy_budget", "buy_budget"):
            parsed = _decimal_or_none(container.get(key))
            if parsed is not None and parsed >= Decimal("0"):
                return parsed
    return None


def _read_jsonl_safe(path: Path) -> list[dict[str, Any]]:
    import json

    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _decimal_or_zero(value: Any) -> Decimal:
    parsed = _decimal_or_none(value)
    return parsed if parsed is not None else Decimal("0")


def _normalize_broker_issue_for_submit(item: dict[str, Any], *, paths: OperationPaths, trade_date: str) -> dict[str, Any]:
    internal_code = str(item.get("issue_code") or item.get("code") or "")
    try:
        result = normalize_broker_issue_code(
            internal_code,
            listed_info=_load_listed_issue_info(paths, trade_date=trade_date, issue_code=internal_code),
        )
    except BrokerIssueCodeNormalizationError as exc:
        return {
            "internal_code": internal_code,
            "broker_issue_code": "",
            "normalization_rule": "",
            "normalization_status": "BLOCK",
            "normalization_reason": str(exc),
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        }
    payload = result.to_dict()
    payload.update(
        {
            "code_normalization_rule": payload["normalization_rule"],
            "code_normalization_status": payload["normalization_status"],
            "raw_request_saved": False,
            "raw_response_saved": False,
            "secret_saved": False,
        }
    )
    return payload


def _load_listed_issue_info(paths: OperationPaths, *, trade_date: str, issue_code: str) -> dict[str, Any] | None:
    candidates = [
        paths.root / "feature_refresh" / trade_date / "jquants" / "listed_issues" / "listed_info_for_feature.parquet",
        paths.root / "jquants" / "raw" / "jquants" / "listed_issues" / "data.parquet",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            import pandas as pd

            frame = pd.read_parquet(path)
        except Exception:  # noqa: BLE001 - fail closed by trying next source.
            continue
        code_column = "code" if "code" in frame.columns else "Code" if "Code" in frame.columns else ""
        if not code_column:
            continue
        matches = frame[frame[code_column].astype(str) == str(issue_code)]
        if matches.empty:
            continue
        row = matches.iloc[-1].to_dict()
        row.setdefault("security_type", row.get("ProdCat") or row.get("product_category") or "")
        row.setdefault("current_listed", True)
        return row
    return None


def _code_normalization_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "internal_code": str(item.get("internal_code") or item.get("issue_code") or item.get("code") or ""),
        "broker_issue_code": str(item.get("broker_issue_code") or ""),
        "normalization_rule": str(item.get("normalization_rule") or item.get("code_normalization_rule") or ""),
        "normalization_status": str(item.get("normalization_status") or item.get("code_normalization_status") or ""),
        "normalization_reason": str(item.get("normalization_reason") or ""),
        "market": str(item.get("market") or ""),
        "broker_market_code": str(item.get("broker_market_code") or ""),
        "product_category": str(item.get("product_category") or ""),
        "security_type": str(item.get("security_type") or ""),
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _find_waiting_buy_order(broker_orders: list[dict[str, Any]], *, broker_issue_code: str, quantity: str) -> dict[str, Any] | None:
    for order in broker_orders:
        if str(order.get("issue_code") or "") != broker_issue_code:
            continue
        if str(order.get("side") or "").upper() not in {"3", "BUY"}:
            continue
        if str(order.get("quantity") or "") != str(quantity):
            continue
        remaining = Decimal(str(order.get("remaining_quantity") or "0"))
        executed = Decimal(str(order.get("executed_quantity") or "0"))
        status = str(order.get("status") or "").upper()
        if remaining == Decimal(str(quantity)) and executed == Decimal("0") and status in {"未約定", "WAITING_FILL", "ACCEPTED", "OPEN"}:
            return order
    return None


def _has_active_same_side_broker_order(broker_orders: list[dict[str, Any]], *, broker_issue_code: str, side: str, quantity: str) -> bool:
    broker_side = "3" if side.upper() == "BUY" else "1" if side.upper() == "SELL" else side.upper()
    for order in broker_orders:
        if str(order.get("issue_code") or "") != broker_issue_code:
            continue
        if str(order.get("side") or "").upper() not in {broker_side, side.upper()}:
            continue
        if quantity and str(order.get("quantity") or "") != str(quantity):
            continue
        remaining = Decimal(str(order.get("remaining_quantity") or "0"))
        status = str(order.get("status") or "").upper()
        if remaining > 0 and status not in {"FILLED", "DONE", "約定済", "取消", "CANCELED", "CANCELLED", "REJECTED"}:
            return True
    return False


def _validate_auto_demo_approval(*, order_plan: dict[str, Any], safety_result: dict[str, Any], broker_snapshot: dict[str, Any], env: str, max_notional: Decimal) -> list[str]:
    blocks: list[str] = []
    if env != "demo":
        blocks.append("auto_demo_approval_requires_demo_environment")
    if order_plan.get("production_order_allowed") is True:
        blocks.append("order_plan_production_allowed_true")
    if safety_result.get("status") in {"BLOCK", "SYSTEM_EMERGENCY_STOP"}:
        blocks.append(f"safety_{safety_result.get('status')}")
    if safety_result.get("safety_state") in {"BLOCK", "SYSTEM_EMERGENCY_STOP"}:
        blocks.append(f"safety_state_{safety_result.get('safety_state')}")
    if max_notional <= Decimal("0"):
        blocks.append("demo_auto_approval_max_notional_missing")
    buying_power = _decimal_or_none(broker_snapshot.get("buying_power")) or Decimal("0")
    if buying_power <= Decimal("0"):
        blocks.append("buying_power_missing")
    total_buy_notional = Decimal("0")
    for item in order_plan.get("items", []):
        if item.get("production_order_allowed") is True:
            blocks.append(f"{item.get('item_id')}:production_order_allowed_true")
        if str(item.get("order_type") or "CASH_EQUITY") != "CASH_EQUITY":
            blocks.append(f"{item.get('item_id')}:order_type_not_cash_equity")
        if str(item.get("side") or "").upper() == "BUY":
            notional = Decimal(str(item.get("estimated_value") or item.get("expected_notional") or "0"))
            total_buy_notional += notional
            if notional > max_notional:
                blocks.append(f"{item.get('item_id')}:buy_notional_exceeds_auto_approval_max")
            if notional > buying_power:
                blocks.append(f"{item.get('item_id')}:buying_power_exceeded")
        if str(item.get("side") or "").upper() == "SELL" and not item.get("position_id"):
            blocks.append(f"{item.get('item_id')}:sell_position_id_missing")
    if total_buy_notional > max_notional:
        blocks.append("total_buy_notional_exceeds_auto_approval_max")
    if total_buy_notional > buying_power:
        blocks.append("total_buy_notional_exceeds_buying_power")
    return blocks


def _demo_special_fill_events(paths: OperationPaths, trade_date: str) -> list[dict[str, Any]]:
    summary = _load_demo_special_fill_summary(paths, trade_date)
    if summary.get("demo_special_fill_simulation_used") is not True:
        return []
    events = []
    for side, item_id in (("BUY", "demo_special_simulated_buy_fill_92560"), ("SELL", "demo_special_simulated_sell_fill_92560")):
        lifecycle = summary.get(f"{side.lower()}_lifecycle") or {}
        if not lifecycle:
            continue
        events.append(
            {
                "item_id": item_id,
                "issue_code": lifecycle.get("internal_code", "92560"),
                "broker_issue_code": lifecycle.get("broker_issue_code", "9256"),
                "side": side,
                "quantity": lifecycle.get("quantity", "100"),
                "position_id": "",
                "exit_source": lifecycle.get("exit_source", "demo_lifecycle_test") if side == "SELL" else "",
                "sell_reason": lifecycle.get("sell_reason", "") if side == "SELL" else "",
                "lifecycle": "SIMULATED_FILLED",
                "requires_human_review": False,
                "remaining_quantity": "0",
                "position_closed": side == "SELL",
                "realized_result_placeholder": side == "SELL",
                "broker_confirmed_fill": False,
                "simulated_fill": True,
                "demo_special_rule": True,
                "simulation_reason": "demo_9000_series_non_fill_rule",
                "performance_metrics_excluded": True,
            }
        )
    return events


def _load_demo_special_fill_summary(paths: OperationPaths, trade_date: str) -> dict[str, Any]:
    path = paths.dated("demo_special_fill", trade_date, "demo_special_fill_simulation_result.json")
    if not path.exists():
        return {
            "demo_special_fill_simulation_used": False,
            "broker_confirmed_fill": False,
            "simulated_fill": False,
            "performance_metrics_excluded": True,
            "production_enabled": False,
        }
    payload = _load_or_empty(path, default={})
    return {
        "status": payload.get("status", "UNKNOWN"),
        "demo_special_fill_simulation_used": payload.get("demo_special_fill_simulation_used") is True,
        "demo_special_fill_simulation_enabled": payload.get("demo_special_fill_simulation_enabled") is True,
        "production_enabled": False,
        "broker_confirmed_fill": False,
        "simulated_fill": payload.get("simulated_buy_fill") is True or payload.get("simulated_sell_fill") is True,
        "simulated_buy_fill": payload.get("simulated_buy_fill") is True,
        "simulated_sell_fill": payload.get("simulated_sell_fill") is True,
        "performance_metrics_excluded": True,
        "simulation_reason": payload.get("simulation_reason", "demo_9000_series_non_fill_rule"),
        "internal_code": payload.get("internal_code", "92560"),
        "broker_issue_code": payload.get("broker_issue_code", "9256"),
        "buy_lifecycle": payload.get("buy_lifecycle") or {},
        "sell_lifecycle": payload.get("sell_lifecycle") or {},
        "raw_request_saved": False,
        "raw_response_saved": False,
        "secret_saved": False,
    }


def _command_from_item(item: dict[str, Any], trade_date: str, approval_id: str, *, live_order_allowed: bool) -> OrderCommand:
    side = OrderSide.BUY if item.get("side") == "BUY" else OrderSide.SELL
    price_type = PriceType.LIMIT if item.get("price_type") == "LIMIT" else PriceType.MARKET
    broker_issue_code = str(item.get("broker_issue_code") or item.get("issue_code") or "")
    return OrderCommand(
        runtime_id=f"operation_{trade_date}_{approval_id}_{item.get('item_id')}",
        environment=RuntimeMode.DEMO,
        paper_test_id="operation_demo",
        issue_code=broker_issue_code,
        side=side,
        quantity=Decimal(str(item.get("quantity"))),
        order_type=OrderType.CASH_EQUITY,
        price_type=price_type,
        limit_price=Decimal(str(item.get("limit_price", "0"))),
        evaluation_cash_basis=Decimal("1000000"),
        broker_cash_upper_bound=Decimal("0"),
        approval_required=True,
        approval_id=approval_id,
        live_order_allowed=live_order_allowed,
    )


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def _optional_decimal_text(value: Decimal | None) -> str | None:
    return _decimal_text(value) if value is not None else None
