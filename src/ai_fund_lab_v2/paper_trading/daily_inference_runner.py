from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import pandas as pd

from ai_fund_lab_v2.paper_trading.ai_artifact_adapter import AIArtifactPaths, adapt_ai_artifacts
from ai_fund_lab_v2.paper_trading.daily_run_result import DailyRunResult
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, load_ledger, load_latest_ledger
from ai_fund_lab_v2.paper_trading.ledger_integration import apply_ledger_to_daily_result
from ai_fund_lab_v2.paper_trading.reporting.blog_draft_writer import write_blog_draft
from ai_fund_lab_v2.paper_trading.reporting.internal_daily_report_writer import write_internal_daily_report
from ai_fund_lab_v2.paper_trading.reporting.public_confidence_mapper import map_public_confidence
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest, daily_run_id


INFERENCE_READY = "INFERENCE_READY"
INFERENCE_BLOCKED = "INFERENCE_BLOCKED"


@dataclass(frozen=True)
class DailyInferenceResult:
    status: str
    run_id: str
    decision_for: str
    data_until: str
    output_dir: str
    artifact_paths: dict[str, str]
    report_paths: dict[str, str]
    manifest_path: str
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    prohibited_flags: Mapping[str, bool] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["prohibited_flags"] = dict(self.prohibited_flags or prohibited_flags())
        return payload


def run_daily_inference(
    *,
    decision_for: str,
    data_until: str,
    runtime_dir: Path | str = ".runtime",
    reports_root: Path | str = "reports",
    feature_root: Path | str = ".runtime/phase9/features",
    canonical_quotes_path: Path | str = ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
    ledger_path: Path | str | None = None,
    allow_initial_ledger: bool = False,
    initial_cash: Decimal = Decimal("1000000"),
    top_candidates: int = 50,
    top_opportunities: int = 20,
    max_buy_orders: int = 5,
) -> DailyInferenceResult:
    run_id = daily_run_id()
    runtime_root = Path(runtime_dir)
    output_dir = runtime_root / "phase9" / "inference" / decision_for
    output_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    blocked: list[str] = []

    feature_paths = {
        "candidate": Path(feature_root) / data_until / "candidate_features.parquet",
        "opportunity": Path(feature_root) / data_until / "opportunity_feature_input.parquet",
        "position": Path(feature_root) / data_until / "position_feature_input.parquet",
        "capital": Path(feature_root) / data_until / "capital_policy_input.parquet",
    }
    for name, path in feature_paths.items():
        if not path.is_file():
            blocked.append(f"{name}_feature_artifact_missing")
    quotes_path = Path(canonical_quotes_path)
    if not quotes_path.is_file():
        blocked.append("canonical_normalized_daily_quotes_missing")

    ledger = _load_operation_ledger(runtime_dir=runtime_root, ledger_path=ledger_path)
    if ledger is None:
        if allow_initial_ledger:
            ledger = PaperTradingLedger(cash=initial_cash)
            warnings.append("initial_ledger_in_memory_only")
        else:
            blocked.append("initial_ledger_required")

    artifact_paths: dict[str, str] = {}
    report_paths: dict[str, str] = {}
    if not blocked and ledger is not None:
        candidate_df = _read_feature_frame(feature_paths["candidate"], decision_for=decision_for, data_until=data_until)
        opportunity_df = _read_feature_frame(feature_paths["opportunity"], decision_for=decision_for, data_until=data_until)
        close_map = _load_close_map(quotes_path, decision_for=decision_for)
        if not close_map:
            blocked.append("decision_for_close_prices_missing")
        else:
            candidate_rows = _build_candidate_rows(
                candidate_df,
                decision_for=decision_for,
                data_until=data_until,
                feature_schema_hash=_feature_schema_hash(candidate_df),
                source_data_refs=_source_data_refs(feature_paths, quotes_path),
                limit=top_candidates,
            )
            opportunity_rows = _build_opportunity_rows(
                opportunity_df,
                candidate_rows=candidate_rows,
                decision_for=decision_for,
                data_until=data_until,
                feature_schema_hash=_feature_schema_hash(opportunity_df),
                source_data_refs=_source_data_refs(feature_paths, quotes_path),
                limit=top_opportunities,
            )
            position_rows = _build_position_rows(ledger=ledger, decision_for=decision_for, data_until=data_until)
            allocation_rows = _build_allocation_rows(
                opportunity_rows=opportunity_rows,
                ledger=ledger,
                close_map=close_map,
                decision_for=decision_for,
                data_until=data_until,
                max_buy_orders=max_buy_orders,
            )
            order_plan = _build_order_plan(
                allocation_rows=allocation_rows,
                decision_for=decision_for,
                data_until=data_until,
                run_id=run_id,
            )
            artifact_paths = {
                "candidate": str(_write_json(output_dir / "candidate_artifact.json", _artifact_payload("candidate", candidate_rows, decision_for, data_until))),
                "opportunity": str(_write_json(output_dir / "opportunity_artifact.json", _artifact_payload("opportunity", opportunity_rows, decision_for, data_until, provisional=True))),
                "position": str(_write_json(output_dir / "position_artifact.json", _artifact_payload("position", position_rows, decision_for, data_until))),
                "allocation": str(_write_json(output_dir / "allocation_artifact.json", _artifact_payload("allocation", allocation_rows, decision_for, data_until))),
                "order_plan": str(_write_json(output_dir / "order_plan_artifact.json", order_plan)),
            }

    status = INFERENCE_BLOCKED if blocked else INFERENCE_READY
    manifest_path = output_dir / "daily_inference_manifest.json"
    report_status = "BLOCKED" if blocked else "GENERATED"
    daily_manifest = DailyRunManifest(
        run_id=run_id,
        run_date=decision_for,
        data_until=data_until,
        train_until="2026-05-18",
        decision_for=decision_for,
        virtual_order_date=_next_business_day(decision_for),
        virtual_execution_date=_next_business_day(decision_for),
        safety_status="READY_FOR_REVIEW" if not blocked else "REVIEW_ONLY_LOCKED",
        human_review_status="pending" if not blocked else "review_only",
        report_status=report_status,
        warnings=tuple(warnings),
        blocked_reasons=tuple(blocked),
    )

    if not blocked and ledger is not None:
        integration = adapt_ai_artifacts(
            decision_for=decision_for,
            data_until=data_until,
            paths=AIArtifactPaths(
                candidate_artifact=Path(artifact_paths["candidate"]),
                opportunity_artifact=Path(artifact_paths["opportunity"]),
                position_artifact=Path(artifact_paths["position"]),
                allocation_artifact=Path(artifact_paths["allocation"]),
                order_plan_artifact=Path(artifact_paths["order_plan"]),
            ),
        )
        if integration.blocked_reasons:
            blocked.extend(integration.blocked_reasons)
            status = INFERENCE_BLOCKED
        daily_result = apply_ledger_to_daily_result(integration.daily_result, ledger)
        daily_result = _with_l2_states(daily_result, status=status, blocked=blocked)
        reports_dir = Path(reports_root)
        internal_md, internal_json = write_internal_daily_report(
            manifest=daily_manifest,
            result=daily_result,
            reports_dir=reports_dir / "phase9" / "daily",
        )
        public_md = write_public_daily_report(
            manifest=daily_manifest,
            result=daily_result,
            reports_dir=reports_dir / "public" / "phase9_daily",
        )
        blog_md = write_blog_draft(
            manifest=daily_manifest,
            result=daily_result,
            reports_dir=reports_dir / "public" / "phase9_daily",
        )
        report_paths = {
            "internal_markdown": str(internal_md),
            "internal_json": str(internal_json),
            "public_markdown": str(public_md),
            "blog_draft": str(blog_md),
        }

    _write_json(
        manifest_path,
        {
            "run_id": run_id,
            "decision_for": decision_for,
            "data_until": data_until,
            "status": status,
            "source_feature_artifacts": {key: str(value) for key, value in feature_paths.items()},
            "source_data_refs": {"canonical_normalized_daily_quotes": str(quotes_path)},
            "artifact_paths": artifact_paths,
            "report_paths": report_paths,
            "model_versions": {
                "candidate_ai": "phase9_candidate_existing_policy_v1",
                "opportunity_ai": "phase5_existing_model_provisional_manifest",
            },
            "policy_versions": {
                "position_management_ai": "position_policy_manifest_v1",
                "capital_allocation_primary": "CAP5",
                "capital_allocation_shadow": ["CAP4", "POLICY_Y_CAP4_EDGE08_CONF5"],
            },
            "retrain_mode": "WEEKLY_RETRAIN_DAILY_INFERENCE",
            "training_executed": False,
            "inference_executed": not bool(blocked),
            "statuses": {
                "candidate": "READY" if artifact_paths.get("candidate") else "BLOCKED",
                "opportunity": "READY" if artifact_paths.get("opportunity") else "BLOCKED",
                "position": "READY" if artifact_paths.get("position") else "BLOCKED",
                "allocation": "READY" if artifact_paths.get("allocation") else "BLOCKED",
                "order_plan": "READY" if artifact_paths.get("order_plan") else "BLOCKED",
            },
            "warnings": warnings,
            "blocked_reasons": blocked,
            "prohibited_flags": prohibited_flags(),
            "created_at": _utc_now_iso(),
        },
    )
    return DailyInferenceResult(
        status=status,
        run_id=run_id,
        decision_for=decision_for,
        data_until=data_until,
        output_dir=str(output_dir),
        artifact_paths=artifact_paths,
        report_paths=report_paths,
        manifest_path=str(manifest_path),
        warnings=tuple(warnings),
        blocked_reasons=tuple(dict.fromkeys(blocked)),
        prohibited_flags=prohibited_flags(),
    )


def prohibited_flags() -> dict[str, bool]:
    return {
        "broker_order_api_called": False,
        "moomoo_simulate_order_called": False,
        "tachibana_order_called": False,
        "open_d_started": False,
        "login_called": False,
        "logout_called": False,
        "unlock_trade_called": False,
        "paper_ledger_fill_executed": False,
        "virtual_fill_executed": False,
        "model_retraining_executed": False,
        "full_backtest_executed": False,
        "scheduler_auto_registered": False,
    }


def _load_operation_ledger(*, runtime_dir: Path, ledger_path: Path | str | None) -> PaperTradingLedger | None:
    if ledger_path:
        path = Path(ledger_path)
        if path.is_file():
            return load_ledger(path)
        return None
    return load_latest_ledger(runtime_dir)


def _read_feature_frame(path: Path, *, decision_for: str, data_until: str) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    date_col = "target_date" if "target_date" in frame.columns else "as_of_date"
    if date_col in frame.columns:
        frame = frame[frame[date_col].astype(str) == decision_for]
    if "data_until" in frame.columns:
        frame = frame[frame["data_until"].astype(str) == data_until]
    return frame.copy()


def _build_candidate_rows(
    frame: pd.DataFrame,
    *,
    decision_for: str,
    data_until: str,
    feature_schema_hash: str,
    source_data_refs: dict[str, str],
    limit: int,
) -> list[dict[str, Any]]:
    if "universe_eligible" in frame.columns:
        frame = frame[frame["universe_eligible"].astype(bool)]
    rows: list[dict[str, Any]] = []
    for item in frame.to_dict(orient="records"):
        raw_score = _candidate_raw_score(item)
        rank_score = raw_score
        score_clipped = _clip(raw_score, 0.0, 100.0)
        confidence = map_public_confidence(
            internal_score=score_clipped,
            risk_penalty=0,
            safety_status="READY_FOR_REVIEW",
            short_reason="Momentum and liquidity screen passed.",
        )
        rows.append(
            {
                "code": str(item.get("code") or item.get("Code") or ""),
                "issue_code": str(item.get("code") or item.get("Code") or ""),
                "issue_name": "",
                "score": round(rank_score, 6),
                "raw_score_preclip": round(raw_score, 6),
                "rank_score": round(rank_score, 6),
                "score_clipped": round(score_clipped, 6),
                "score_saturation_flag": _score_saturation_flag(raw_score, score_clipped),
                "score_source": "raw_preclip_rank_score",
                "rank_tiebreaker": "rank_score_desc,liquidity_desc,code_asc",
                "confidence": round(score_clipped / 100.0, 6),
                "public_confidence_score": confidence.public_confidence_score,
                "public_confidence_label": confidence.public_confidence_label,
                "short_reason": confidence.short_reason,
                "caution_note": confidence.caution_note,
                "reason": "existing_candidate_policy_v1",
                "decision_for": decision_for,
                "data_until": data_until,
                "feature_schema_hash": feature_schema_hash,
                "source_data_refs": source_data_refs,
                "is_current_listed": bool(item.get("is_current_listed", True)),
                "has_current_name": bool(item.get("has_current_name", True)),
                "is_fresh_price": bool(item.get("is_fresh_price", True)),
                "product_category": str(item.get("product_category") or ""),
                "market_name": str(item.get("market_name") or ""),
                "is_allowed_product": bool(item.get("is_allowed_product", True)),
                "universe_exclusion_reason": str(item.get("universe_exclusion_reason") or ""),
                "rank_liquidity": round(_candidate_liquidity_rank_value(item), 6),
            }
        )
    rows.sort(key=lambda row: (-float(row["rank_score"]), -float(row["rank_liquidity"]), row["code"]))
    rows = rows[:limit]
    _assign_public_scores_from_rank_score(rows, raw_key="rank_score")
    for index, row in enumerate(rows[:limit], start=1):
        row["rank"] = index
    return rows


def _build_opportunity_rows(
    frame: pd.DataFrame,
    *,
    candidate_rows: list[dict[str, Any]],
    decision_for: str,
    data_until: str,
    feature_schema_hash: str,
    source_data_refs: dict[str, str],
    limit: int,
) -> list[dict[str, Any]]:
    by_code = {str(row.get("code")): row for row in frame.to_dict(orient="records")}
    rows: list[dict[str, Any]] = []
    for candidate in candidate_rows:
        code = str(candidate["code"])
        features = by_code.get(code, {})
        candidate_rank_score = float(candidate.get("rank_score") or candidate.get("raw_score_preclip") or candidate.get("score") or 0.0)
        raw_score = _opportunity_raw_score(candidate_rank_score, features)
        rank_score = raw_score
        score_clipped = _clip(raw_score, 0.0, 100.0)
        confidence = map_public_confidence(
            internal_score=score_clipped,
            risk_penalty=0,
            safety_status="READY_FOR_REVIEW",
            short_reason="Candidate strength with opportunity ranking.",
        )
        rows.append(
            {
                "code": code,
                "issue_code": code,
                "issue_name": "",
                "opportunity_score": round(rank_score, 6),
                "candidate_rank_score": round(candidate_rank_score, 6),
                "raw_score_preclip": round(raw_score, 6),
                "rank_score": round(rank_score, 6),
                "score_clipped": round(score_clipped, 6),
                "expected_edge_score": round(score_clipped / 100.0, 6),
                "score_saturation_flag": _score_saturation_flag(raw_score, score_clipped),
                "score_source": "raw_preclip_rank_score",
                "rank_tiebreaker": "rank_score_desc,liquidity_desc,code_asc",
                "public_confidence_score": confidence.public_confidence_score,
                "public_confidence_label": confidence.public_confidence_label,
                "short_reason": confidence.short_reason,
                "caution_note": confidence.caution_note,
                "reason": "existing_opportunity_model_provisional_manifest_no_retrain",
                "decision_for": decision_for,
                "data_until": data_until,
                "feature_schema_hash": feature_schema_hash,
                "source_data_refs": source_data_refs,
                "provisional_inference_manifest": True,
                "is_current_listed": bool(candidate.get("is_current_listed", True)),
                "has_current_name": bool(candidate.get("has_current_name", True)),
                "is_fresh_price": bool(candidate.get("is_fresh_price", True)),
                "product_category": str(candidate.get("product_category") or ""),
                "market_name": str(candidate.get("market_name") or ""),
                "is_allowed_product": bool(candidate.get("is_allowed_product", True)),
                "universe_exclusion_reason": str(candidate.get("universe_exclusion_reason") or ""),
                "rank_liquidity": round(_opportunity_liquidity_rank_value(features), 6),
            }
        )
    rows.sort(key=lambda row: (-float(row["rank_score"]), -float(row["rank_liquidity"]), row["code"]))
    rows = rows[:limit]
    _assign_public_scores_from_rank_score(rows, raw_key="rank_score", expected_edge=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _build_position_rows(*, ledger: PaperTradingLedger, decision_for: str, data_until: str) -> list[dict[str, Any]]:
    if not ledger.positions:
        return [
            {
                "code": "",
                "issue_code": "",
                "action": "HOLD",
                "position_status": "NO_CURRENT_POSITIONS",
                "public_confidence_score": 50,
                "short_reason": "No current paper positions.",
                "caution_note": "Position Management did not create a sell signal.",
                "decision_for": decision_for,
                "data_until": data_until,
            }
        ]
    rows: list[dict[str, Any]] = []
    for position in ledger.positions:
        rows.append(
            {
                "code": position.code,
                "issue_code": position.code,
                "issue_name": position.name,
                "action": "HOLD",
                "position_score": 50,
                "public_confidence_score": 50,
                "short_reason": "Existing paper position held for review.",
                "caution_note": "Paper Trading validation only.",
                "decision_for": decision_for,
                "data_until": data_until,
            }
        )
    return rows


def _build_allocation_rows(
    *,
    opportunity_rows: list[dict[str, Any]],
    ledger: PaperTradingLedger,
    close_map: Mapping[str, Decimal],
    decision_for: str,
    data_until: str,
    max_buy_orders: int,
) -> list[dict[str, Any]]:
    total_equity = ledger.performance.total_equity if ledger.performance else ledger.cash
    cash_buffer = (total_equity * Decimal("0.05")).quantize(Decimal("1"), rounding=ROUND_FLOOR)
    available_cash = max(Decimal("0"), ledger.cash - cash_buffer)
    existing_codes = {position.code for position in ledger.positions}
    rows: list[dict[str, Any]] = []
    for row in opportunity_rows:
        if len(rows) >= max_buy_orders:
            break
        code = str(row["code"])
        if code in existing_codes:
            continue
        price = close_map.get(code)
        if not price or price <= 0:
            continue
        slot_count = max(1, max_buy_orders - len(rows))
        budget = min(total_equity * Decimal("0.20"), available_cash / Decimal(slot_count))
        quantity = _lot_quantity(budget=budget, price=price)
        if quantity <= 0:
            continue
        planned_amount = (price * Decimal(quantity)).quantize(Decimal("1"), rounding=ROUND_FLOOR)
        if planned_amount > available_cash:
            continue
        available_cash -= planned_amount
        rows.append(
            {
                "code": code,
                "issue_code": code,
                "side": "BUY",
                "quantity": quantity,
                "planned_quantity": quantity,
                "reference_price": str(price),
                "planned_amount": str(planned_amount),
                "public_confidence_score": row.get("public_confidence_score"),
                "public_confidence_label": row.get("public_confidence_label"),
                "short_reason": "CAP5 paper allocation candidate.",
                "caution_note": "Review-only paper order. Not an instruction to trade.",
                "reason": "CAP5_PRIMARY_SELL_FIRST_BUY_AFTER_FILL",
                "decision_for": decision_for,
                "data_until": data_until,
                "policy_version": "CAP5",
                "shadow_policy_versions": ["CAP4", "POLICY_Y_CAP4_EDGE08_CONF5"],
                "cash_buffer_rate": "0.05",
                "max_position_weight": "0.20",
                "lot_size": 100,
                "sell_first_buy_after_fill": True,
            }
        )
    return rows


def _build_order_plan(*, allocation_rows: list[dict[str, Any]], decision_for: str, data_until: str, run_id: str) -> dict[str, Any]:
    return {
        "artifact_type": "phase9_order_plan",
        "run_id": run_id,
        "decision_for": decision_for,
        "data_until": data_until,
        "executable": False,
        "live_order_allowed": False,
        "requires_human_review": True,
        "sell_first_buy_after_fill": True,
        "items": [
            {
                "order_id": f"phase9_l2_order_{uuid4().hex}",
                "code": row["code"],
                "issue_code": row["issue_code"],
                "side": row["side"],
                "quantity": row["quantity"],
                "planned_quantity": row["planned_quantity"],
                "planned_amount": row["planned_amount"],
                "public_confidence_score": row.get("public_confidence_score"),
                "public_confidence_label": row.get("public_confidence_label"),
                "short_reason": row.get("short_reason"),
                "caution_note": row.get("caution_note"),
                "reason": row.get("reason"),
                "decision_for": decision_for,
                "data_until": data_until,
                "executable": False,
                "live_order_allowed": False,
                "requires_human_review": True,
            }
            for row in allocation_rows
        ],
    }


def _candidate_raw_score(row: Mapping[str, Any]) -> float:
    ret5 = _float(row.get("price_momentum_return_5d"))
    ret20 = _float(row.get("price_momentum_return_20d"))
    volume = _float(row.get("volume_momentum_ratio_5d"), default=1.0)
    volatility = _float(row.get("volatility_return_std_20d"))
    trend = _float(row.get("trend_close_over_ma_20d"))
    liquidity = math.log10(max(_float(row.get("liquidity_avg_volume_20d")), 1.0)) / 7.0
    return 50.0 + ret5 * 80.0 + ret20 * 120.0 + (volume - 1.0) * 8.0 + trend * 100.0 - volatility * 300.0 + liquidity * 10.0


def _candidate_score(row: Mapping[str, Any]) -> float:
    return _clip(_candidate_raw_score(row), 0.0, 100.0)


def _opportunity_raw_score(candidate_rank_score: float, row: Mapping[str, Any]) -> float:
    ret20 = _float(row.get("feature__price_momentum_return_20d"))
    trend = _float(row.get("feature__trend_close_over_ma_20d"))
    volume = _float(row.get("feature__volume_momentum_ratio_5d"), default=1.0)
    volatility = _float(row.get("feature__volatility_return_std_20d"))
    return candidate_rank_score * 0.65 + 35.0 + ret20 * 80.0 + trend * 70.0 + (volume - 1.0) * 5.0 - volatility * 220.0


def _opportunity_score(candidate_score: float, row: Mapping[str, Any]) -> float:
    return _clip(_opportunity_raw_score(candidate_score, row), 0.0, 100.0)


def _candidate_liquidity_rank_value(row: Mapping[str, Any]) -> float:
    return _float(row.get("liquidity_avg_volume_20d"))


def _opportunity_liquidity_rank_value(row: Mapping[str, Any]) -> float:
    return _float(row.get("feature__liquidity_avg_volume_20d"))


def _score_saturation_flag(raw_score: float, score_clipped: float) -> bool:
    return abs(raw_score - score_clipped) > 1e-9


def _assign_public_scores_from_rank_score(rows: list[dict[str, Any]], *, raw_key: str, expected_edge: bool = False) -> None:
    values = [float(row.get(raw_key) or 0.0) for row in rows]
    if not rows:
        return
    min_value = min(values)
    max_value = max(values)
    span = max_value - min_value
    for row in rows:
        raw_value = float(row.get(raw_key) or 0.0)
        if span <= 1e-12:
            normalized = 0.5
        else:
            normalized = (raw_value - min_value) / span
        public_score = max(0, min(100, int(round(40 + normalized * 60))))
        confidence = map_public_confidence(
            internal_score=public_score,
            risk_penalty=0,
            safety_status="READY_FOR_REVIEW",
            short_reason=str(row.get("short_reason") or "Phase9 rank score based public score."),
        )
        row["public_confidence_score"] = confidence.public_confidence_score
        row["public_confidence_label"] = confidence.public_confidence_label
        if expected_edge:
            row["expected_edge_score"] = round(normalized, 6)


def _load_close_map(path: Path, *, decision_for: str) -> dict[str, Decimal]:
    frame = pd.read_parquet(path, columns=["date", "code", "close"])
    frame = frame[frame["date"].astype(str) == decision_for]
    prices: dict[str, Decimal] = {}
    for row in frame.to_dict(orient="records"):
        close = row.get("close")
        if close in (None, "") or pd.isna(close):
            continue
        price = Decimal(str(close))
        if not price.is_finite() or price <= 0:
            continue
        prices[str(row["code"])] = price
    return prices


def _lot_quantity(*, budget: Decimal, price: Decimal) -> int:
    if price <= 0:
        return 0
    lots = int((budget / price / Decimal("100")).to_integral_value(rounding=ROUND_FLOOR))
    return lots * 100


def _with_l2_states(result: DailyRunResult, *, status: str, blocked: list[str]) -> DailyRunResult:
    return DailyRunResult(
        buy_candidates=result.buy_candidates,
        sell_candidates=(),
        hold_candidates=(),
        cash=result.cash,
        current_cash=result.current_cash,
        positions=result.positions,
        current_positions=result.current_positions,
        pending_orders=result.pending_orders,
        total_equity=result.total_equity,
        market_value=result.market_value,
        realized_pnl=result.realized_pnl,
        unrealized_pnl=result.unrealized_pnl,
        trade_count=result.trade_count,
        safety_state={"status": "READY_FOR_REVIEW" if status == INFERENCE_READY else "REVIEW_ONLY_LOCKED", "blocked_reasons": blocked},
        review_state={"status": "pending", "requires_human_review": True},
        artifact_state=result.artifact_state,
        execution_state={"status": "NOT_EXECUTED", "virtual_fill_executed": False},
    )


def _artifact_payload(
    artifact_type: str,
    rows: list[dict[str, Any]],
    decision_for: str,
    data_until: str,
    *,
    provisional: bool = False,
) -> dict[str, Any]:
    return {
        "artifact_type": f"phase9_{artifact_type}_artifact",
        "decision_for": decision_for,
        "data_until": data_until,
        "row_count": len(rows),
        "provisional_inference_manifest": provisional,
        "retraining_executed": False,
        "rows": rows,
    }


def _feature_schema_hash(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns if str(column) != "created_at"]
    return sha256(json.dumps(columns, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _source_data_refs(feature_paths: Mapping[str, Path], quotes_path: Path) -> dict[str, str]:
    return {
        "candidate_features": str(feature_paths["candidate"]),
        "opportunity_features": str(feature_paths["opportunity"]),
        "position_features": str(feature_paths["position"]),
        "capital_policy_input": str(feature_paths["capital"]),
        "canonical_normalized_daily_quotes": str(quotes_path),
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _float(value: Any, *, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _next_business_day(value: str) -> str:
    current = date.fromisoformat(value) + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current.isoformat()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
