"""Runtime regular-path adapters for Candidate AI and Opportunity AI.

The adapters do not change Candidate AI or Opportunity AI scoring.  They call
the existing inference helpers, normalize their outputs into Runtime artifacts,
and expose Opportunity-ranked BUY signals to Morning Planning.
"""

from __future__ import annotations

import json
import pickle
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import CANONICAL_ALIAS_POLICY
from scripts.run_phase4bg_formal_candidate_inference import (
    audit_inference_features,
    build_scored_candidates,
    _feature_matrix as candidate_feature_matrix,
    _predict_scores as predict_candidate_scores,
)

from ai_fund_lab_v2.opportunity_ai.inference import run_opportunity_inference
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import evaluate_opportunity_buy_eligibility
from ai_fund_lab_v2.runtime_v2.artifact_lookup import (
    RuntimeArtifactLookupHalt,
    require_diagnostic_path_matches_registry,
    resolve_runtime_artifact_set,
)
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal
from ai_fund_lab_v2.runtime_v2.storage.json_safe import dumps_json_safe


CANDIDATE_ARTIFACT_SCHEMA_VERSION = "runtime_v2_candidate_decision_v1"
OPPORTUNITY_ARTIFACT_SCHEMA_VERSION = "runtime_v2_opportunity_ranking_v1"
OPPORTUNITY_ARTIFACT_SCHEMA_NAME = "runtime_v2_buy_opportunity_ranking"
OPPORTUNITY_ARTIFACT_ROLE = "BUY_OPPORTUNITY_RANKING"
BUY_AI_INFERENCE_VERSION = "candidate_opportunity_ai_regular_path_v1"
DEFAULT_CANDIDATE_MODEL_PATH = Path(".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl")
DEFAULT_OPPORTUNITY_MODEL_PATH = Path("reports/opportunity_ai/phase5p/models/opportunity_model.pkl")
PROHIBITED_OPPORTUNITY_PHASE5E_METRICS_PATH = Path("reports/opportunity_ai/phase5e/opportunity_training_metrics.json")


@dataclass(frozen=True)
class BuyAIRuntimeResult:
    status: str
    reason: str
    business_date: str
    runtime_id: str
    feature_date: str
    candidate_model_version: str
    candidate_artifact_path: str
    candidate_count: int
    opportunity_model_version: str
    opportunity_artifact_path: str
    opportunity_count: int
    selected_rank_count: int
    generated_at: str
    ai_signals: tuple[AIPlanningSignal, ...]
    candidate_schema_evidence: dict[str, Any]
    opportunity_schema_evidence: dict[str, Any]

    def to_manifest_fields(self) -> dict[str, Any]:
        return {
            "buy_ai_status": self.status,
            "buy_ai_reason": self.reason,
            "candidate_model_version": self.candidate_model_version,
            "candidate_artifact_path": self.candidate_artifact_path,
            "candidate_count": self.candidate_count,
            "opportunity_model_version": self.opportunity_model_version,
            "opportunity_artifact_path": self.opportunity_artifact_path,
            "opportunity_count": self.opportunity_count,
            "selected_rank_count": self.selected_rank_count,
            "buy_ai_generated_at": self.generated_at,
            "candidate_schema_status": self.candidate_schema_evidence.get("schema_status") or "",
            "candidate_required_columns": self.candidate_schema_evidence.get("required_columns") or [],
            "candidate_present_columns": self.candidate_schema_evidence.get("present_columns") or [],
            "candidate_missing_columns": self.candidate_schema_evidence.get("missing_columns") or [],
            "candidate_unexpected_columns": self.candidate_schema_evidence.get("unexpected_columns") or [],
            "candidate_alias_risks": self.candidate_schema_evidence.get("alias_risks") or {},
            "candidate_review_required": bool(self.candidate_schema_evidence.get("review_required")),
            "candidate_review_reason": self.candidate_schema_evidence.get("review_reason") or "",
            "opportunity_schema_status": self.opportunity_schema_evidence.get("schema_status") or "",
            "opportunity_required_columns": self.opportunity_schema_evidence.get("required_columns") or [],
            "opportunity_present_columns": self.opportunity_schema_evidence.get("present_columns") or [],
            "opportunity_missing_columns": self.opportunity_schema_evidence.get("missing_columns") or [],
            "opportunity_unexpected_columns": self.opportunity_schema_evidence.get("unexpected_columns") or [],
            "opportunity_prefix_policy": self.opportunity_schema_evidence.get("prefix_policy") or "",
            "opportunity_double_prefix_detected": bool(
                self.opportunity_schema_evidence.get("double_prefix_detected")
            ),
            "opportunity_review_required": bool(self.opportunity_schema_evidence.get("review_required")),
            "opportunity_review_reason": self.opportunity_schema_evidence.get("review_reason") or "",
        }


def produce_buy_ai_decisions(
    *,
    runtime_root: Path | str,
    business_date: str,
    feature_root: Path | str,
    feature_date: str,
    candidate_model_path: Path | str | None = None,
    opportunity_model_path: Path | str | None = None,
    opportunity_training_metrics_path: Path | str | None = None,
    top_n: int = 50,
    selected_rank_limit: int | None = None,
    now: datetime | None = None,
) -> BuyAIRuntimeResult:
    root = Path(runtime_root)
    _reject_mode_rooted_runtime_root(root)
    generated_at = _iso(now or datetime.now(timezone.utc))
    runtime_id = f"runtime-v2-buy-ai-{business_date}-{generated_at.replace(':', '').replace('-', '')}"
    artifact_dir = root / "runtime_state" / "buy_ai" / business_date
    artifact_dir.mkdir(parents=True, exist_ok=True)
    candidate_artifact_path = artifact_dir / "candidate_decisions.json"
    opportunity_artifact_path = artifact_dir / "opportunity_rankings.json"
    feature_dir = Path(feature_root) / feature_date
    candidate_feature_path = feature_dir / "candidate_features.parquet"
    opportunity_feature_path = feature_dir / "opportunity_feature_input.parquet"
    try:
        artifact_paths = resolve_buy_ai_artifact_paths(
            candidate_model_path=candidate_model_path,
            opportunity_model_path=opportunity_model_path,
            opportunity_training_metrics_path=opportunity_training_metrics_path,
            allow_isolated_test_paths=_isolated_test_artifact_paths_allowed(root, candidate_model_path, opportunity_model_path, opportunity_training_metrics_path),
        )
    except RuntimeArtifactLookupHalt as exc:
        halt_payload = _candidate_payload(
            business_date=business_date,
            feature_date=feature_date,
            runtime_id=runtime_id,
            generated_at=generated_at,
            model_version="",
            status="HALT",
            reason=str(exc),
            feature_path=candidate_feature_path,
            model_path=None,
            artifact_path=candidate_artifact_path,
            rows=(),
        )
        _write_json(candidate_artifact_path, halt_payload)
        _write_json(opportunity_artifact_path, _empty_opportunity_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            status="HALT",
            reason=str(exc),
            candidate_artifact_path=candidate_artifact_path,
            opportunity_feature_path=opportunity_feature_path,
            review_reason=str(exc),
        ))
        return _result(
            status="HALT",
            reason=str(exc),
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            candidate_payload=halt_payload,
            opportunity_payload=_read_json(opportunity_artifact_path),
            opportunity_artifact_path=opportunity_artifact_path,
            ai_signals=(),
        )

    resolved_candidate_model_path, resolved_opportunity_model_path = (
        artifact_paths["candidate_model"],
        artifact_paths["opportunity_model"],
    )

    candidate_payload = _produce_candidate_artifact(
        feature_path=candidate_feature_path,
        model_path=resolved_candidate_model_path,
        artifact_path=candidate_artifact_path,
        business_date=business_date,
        feature_date=feature_date,
        runtime_id=runtime_id,
        generated_at=generated_at,
        top_n=top_n,
    )
    if candidate_payload["status"] != "PASS":
        _write_json(opportunity_artifact_path, _empty_opportunity_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            status="REVIEW_REQUIRED",
            reason="candidate_dependency_review_required",
            candidate_artifact_path=candidate_artifact_path,
            opportunity_feature_path=opportunity_feature_path,
            review_reason="candidate_dependency_review_required",
            candidate_dependency_status=str(candidate_payload.get("status") or ""),
            candidate_dependency_reason=str(candidate_payload.get("reason") or "candidate_ai_not_ready"),
        ))
        return _result(
            status="REVIEW_REQUIRED",
            reason=str(candidate_payload.get("reason") or "candidate_ai_not_ready"),
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            candidate_payload=candidate_payload,
            opportunity_payload=_read_json(opportunity_artifact_path),
            opportunity_artifact_path=opportunity_artifact_path,
            ai_signals=(),
        )

    opportunity_payload = _produce_opportunity_artifact(
        candidate_artifact_path=candidate_artifact_path,
        opportunity_feature_path=opportunity_feature_path,
        opportunity_model_path=resolved_opportunity_model_path,
        opportunity_training_metrics_path=artifact_paths["opportunity_metrics"],
        artifact_path=opportunity_artifact_path,
        business_date=business_date,
        feature_date=feature_date,
        runtime_id=runtime_id,
        generated_at=generated_at,
    )
    status = "PASS" if opportunity_payload["status"] == "PASS" else str(opportunity_payload.get("status") or "REVIEW_REQUIRED")
    reason = "" if status == "PASS" else str(opportunity_payload.get("reason") or "opportunity_ai_not_ready")
    return _result(
        status=status,
        reason=reason,
        business_date=business_date,
        runtime_id=runtime_id,
        feature_date=feature_date,
        generated_at=generated_at,
        candidate_payload=candidate_payload,
        opportunity_payload=opportunity_payload,
        opportunity_artifact_path=opportunity_artifact_path,
        ai_signals=load_ai_planning_signals_from_opportunity_artifact(
            opportunity_artifact_path,
            selected_rank_limit=selected_rank_limit,
        ) if status == "PASS" else (),
    )


def resolve_buy_ai_model_paths(
    *,
    candidate_model_path: Path | str | None = None,
    opportunity_model_path: Path | str | None = None,
    allow_isolated_test_paths: bool = False,
) -> tuple[Path, Path]:
    paths = resolve_buy_ai_artifact_paths(
        candidate_model_path=candidate_model_path,
        opportunity_model_path=opportunity_model_path,
        opportunity_training_metrics_path=None,
        allow_isolated_test_paths=allow_isolated_test_paths,
    )
    return (paths["candidate_model"], paths["opportunity_model"])


def resolve_buy_ai_artifact_paths(
    *,
    candidate_model_path: Path | str | None = None,
    opportunity_model_path: Path | str | None = None,
    opportunity_training_metrics_path: Path | str | None = None,
    allow_isolated_test_paths: bool = False,
) -> dict[str, Path]:
    if allow_isolated_test_paths:
        return {
            "candidate_model": Path(candidate_model_path) if candidate_model_path else DEFAULT_CANDIDATE_MODEL_PATH,
            "candidate_model_manifest": Path(""),
            "candidate_feature_schema": Path(""),
            "opportunity_model": Path(opportunity_model_path) if opportunity_model_path else DEFAULT_OPPORTUNITY_MODEL_PATH,
            "opportunity_metrics": Path(opportunity_training_metrics_path) if opportunity_training_metrics_path else None,  # type: ignore[dict-item]
            "opportunity_feature_schema": Path(""),
        }
    candidate = resolve_runtime_artifact_set(
        "CANDIDATE_AI_SET",
        required_roles=(
            "MODEL",
            "MODEL_MANIFEST",
            "FEATURE_SCHEMA",
            "TRAINING_METADATA",
            "TRAINING_DATA_LINEAGE",
            "VALIDATION_EVIDENCE",
            "METRICS_EVIDENCE",
            "CONSUMER_COMPATIBILITY",
        ),
    )
    opportunity = resolve_runtime_artifact_set(
        "OPPORTUNITY_AI_SET",
        required_roles=(
            "MODEL",
            "METRICS",
            "FEATURE_SCHEMA",
            "TRAINING_METADATA",
            "TRAINING_DATA_LINEAGE",
            "VALIDATION_EVIDENCE",
            "CONSUMER_COMPATIBILITY",
        ),
    )
    candidate_model = candidate.require_member("MODEL")
    opportunity_model = opportunity.require_member("MODEL")
    opportunity_metrics = opportunity.require_member("METRICS")
    opportunity_schema = opportunity.require_member("FEATURE_SCHEMA")
    require_diagnostic_path_matches_registry(candidate_model_path, candidate_model, label="candidate_model_path")
    require_diagnostic_path_matches_registry(opportunity_model_path, opportunity_model, label="opportunity_model_path")
    if opportunity_training_metrics_path is not None and _is_prohibited_phase5e_metrics_path(Path(opportunity_training_metrics_path)):
        raise RuntimeArtifactLookupHalt("Opportunity Phase5-E metrics artifact is prohibited for Runtime use.")
    require_diagnostic_path_matches_registry(opportunity_training_metrics_path, opportunity_metrics, label="opportunity_training_metrics_path")
    if opportunity_model.artifact_set_id != opportunity_metrics.artifact_set_id:
        raise RuntimeArtifactLookupHalt("Opportunity model and metrics are not from the same Registry Artifact Set.")
    return {
        "candidate_model": candidate_model.physical_path,
        "candidate_model_manifest": candidate.require_member("MODEL_MANIFEST").physical_path,
        "candidate_feature_schema": candidate.require_member("FEATURE_SCHEMA").physical_path,
        "opportunity_model": opportunity_model.physical_path,
        "opportunity_metrics": opportunity_metrics.physical_path,
        "opportunity_feature_schema": opportunity_schema.physical_path,
    }


def _isolated_test_artifact_paths_allowed(
    runtime_root: Path,
    candidate_model_path: Path | str | None,
    opportunity_model_path: Path | str | None,
    opportunity_training_metrics_path: Path | str | None,
) -> bool:
    if not any((candidate_model_path, opportunity_model_path, opportunity_training_metrics_path)):
        return False
    try:
        return runtime_root.resolve() != Path(".runtime").resolve()
    except OSError:
        return True


def load_ai_planning_signals_from_opportunity_artifact(
    path: Path | str,
    *,
    selected_rank_limit: int | None = None,
) -> tuple[AIPlanningSignal, ...]:
    artifact_path = Path(path)
    payload = _read_json(artifact_path)
    if payload.get("schema_version") != OPPORTUNITY_ARTIFACT_SCHEMA_VERSION:
        raise ValueError("Opportunity ranking artifact schema mismatch")
    rows = list(payload.get("rankings") or ())
    if selected_rank_limit is not None:
        rows = [row for row in rows if int(row.get("rank") or 999999) <= selected_rank_limit]
    runtime_id = str(payload.get("runtime_id") or "runtime-v2-buy-ai")
    business_date = str(payload.get("business_date") or "")
    feature_date = str(payload.get("feature_date") or payload.get("target_date") or "")
    signals: list[AIPlanningSignal] = []
    for row in sorted(rows, key=lambda item: (int(item.get("rank") or 999999), str(item.get("symbol") or ""))):
        rank = int(row.get("rank") or len(signals) + 1)
        symbol = str(row.get("symbol") or "")
        if not symbol:
            continue
        eligibility = evaluate_opportunity_buy_eligibility(
            symbol=symbol,
            business_date=business_date,
            feature_date=feature_date,
            opportunity_artifact_path=artifact_path,
            opportunity_payload=payload,
            opportunity_row=row,
            excluded_at_stage="buy_ai_signal_loader",
        )
        if not eligibility.eligible:
            continue
        signals.append(
            AIPlanningSignal(
                signal_id=f"{runtime_id}-opportunity-{symbol}-{rank:03d}",
                symbol=symbol,
                side="BUY",
                rank=rank,
                score=float(row.get("opportunity_score") or row.get("expected_edge_score") or 0.0),
                reason=str(row.get("reason") or "opportunity_ai_ranked"),
                source_ai="opportunity_ai",
            )
        )
    return tuple(signals)


def _produce_candidate_artifact(
    *,
    feature_path: Path,
    model_path: Path | None,
    artifact_path: Path,
    business_date: str,
    feature_date: str,
    runtime_id: str,
    generated_at: str,
    top_n: int,
) -> dict[str, Any]:
    if model_path is None or not model_path.is_file():
        payload = _candidate_payload(
            business_date=business_date,
            feature_date=feature_date,
            runtime_id=runtime_id,
            generated_at=generated_at,
            model_version="",
            status="REVIEW_REQUIRED",
            reason="candidate_model_artifact_missing",
            feature_path=feature_path,
            model_path=model_path,
            artifact_path=artifact_path,
            rows=(),
        )
        _write_json(artifact_path, payload)
        return payload
    if not feature_path.is_file():
        payload = _candidate_payload(
            business_date=business_date,
            feature_date=feature_date,
            runtime_id=runtime_id,
            generated_at=generated_at,
            model_version="",
            status="REVIEW_REQUIRED",
            reason="candidate_feature_artifact_missing",
            feature_path=feature_path,
            model_path=model_path,
            artifact_path=artifact_path,
            rows=(),
        )
        _write_json(artifact_path, payload)
        return payload
    model_payload = _read_pickle(model_path)
    feature_columns = [str(column) for column in model_payload.get("feature_columns") or ()]
    if not feature_columns:
        payload = _candidate_payload(
            business_date=business_date,
            feature_date=feature_date,
            runtime_id=runtime_id,
            generated_at=generated_at,
            model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
            status="REVIEW_REQUIRED",
            reason="candidate_model_feature_columns_missing",
            feature_path=feature_path,
            model_path=model_path,
            artifact_path=artifact_path,
            rows=(),
            schema_evidence=_empty_schema_evidence(
                schema_status="REVIEW_REQUIRED",
                review_reason="candidate_model_feature_columns_missing",
                artifact_path=feature_path,
                model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
                feature_date=feature_date,
            ),
        )
        _write_json(artifact_path, payload)
        return payload
    leakage = audit_inference_features(feature_columns)
    if leakage["status"] != "OK":
        payload = _candidate_payload(
            business_date=business_date,
            feature_date=feature_date,
            runtime_id=runtime_id,
            generated_at=generated_at,
            model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
            status="REVIEW_REQUIRED",
            reason="candidate_feature_leakage_audit_failed",
            feature_path=feature_path,
            model_path=model_path,
            artifact_path=artifact_path,
            rows=(),
            schema_evidence=_empty_schema_evidence(
                schema_status="REVIEW_REQUIRED",
                review_reason="candidate_feature_leakage_audit_failed",
                required_columns=tuple(_strip_feature_prefix(column) for column in feature_columns),
                artifact_path=feature_path,
                model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
                feature_date=feature_date,
            ),
        )
        _write_json(artifact_path, payload)
        return payload
    frame = pd.read_parquet(feature_path)
    schema_evidence = _candidate_schema_evidence(
        frame=frame,
        feature_columns=feature_columns,
        feature_path=feature_path,
        model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
        feature_date=feature_date,
    )
    if schema_evidence["schema_status"] != "READY":
        payload = _candidate_payload(
            business_date=business_date,
            feature_date=feature_date,
            runtime_id=runtime_id,
            generated_at=generated_at,
            model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
            status="REVIEW_REQUIRED",
            reason="candidate_feature_schema_mismatch",
            feature_path=feature_path,
            model_path=model_path,
            artifact_path=artifact_path,
            rows=(),
            schema_evidence=schema_evidence,
        )
        _write_json(artifact_path, payload)
        return payload
    latest = frame[frame["target_date"].astype(str) == feature_date].copy()
    if "universe_eligible" in latest.columns:
        latest = latest[latest["universe_eligible"].fillna(False).astype(bool)].copy()
    if "excluded_reason" in latest.columns:
        latest = latest[latest["excluded_reason"].fillna("").astype(str).eq("")].copy()
    if latest.empty:
        payload = _candidate_payload(
            business_date=business_date,
            feature_date=feature_date,
            runtime_id=runtime_id,
            generated_at=generated_at,
            model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
            status="REVIEW_REQUIRED",
        reason="candidate_feature_rows_empty",
        feature_path=feature_path,
        model_path=model_path,
        artifact_path=artifact_path,
        rows=(),
        schema_evidence=schema_evidence,
        )
        _write_json(artifact_path, payload)
        return payload
    scores = predict_candidate_scores(model_payload["model"], candidate_feature_matrix(latest, feature_columns))
    rows = build_scored_candidates(
        latest.to_dict("records"),
        scores,
        model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
    )
    rows = sorted(rows, key=lambda row: (-float(row["candidate_score"]), str(row["code"])))
    for index, row in enumerate(rows, start=1):
        row["candidate_rank"] = index
    payload = _candidate_payload(
        business_date=business_date,
        feature_date=feature_date,
        runtime_id=runtime_id,
        generated_at=generated_at,
        model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
        status="PASS",
        reason="",
        feature_path=feature_path,
        model_path=model_path,
        artifact_path=artifact_path,
        rows=tuple(rows[:top_n]),
        schema_evidence=schema_evidence,
    )
    _write_json(artifact_path, payload)
    return payload


def _produce_opportunity_artifact(
    *,
    candidate_artifact_path: Path,
    opportunity_feature_path: Path,
    opportunity_model_path: Path | None,
    opportunity_training_metrics_path: Path | None,
    artifact_path: Path,
    business_date: str,
    feature_date: str,
    runtime_id: str,
    generated_at: str,
) -> dict[str, Any]:
    if opportunity_model_path is None or not opportunity_model_path.is_file():
        payload = _empty_opportunity_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            status="REVIEW_REQUIRED",
            reason="opportunity_model_artifact_missing",
            candidate_artifact_path=candidate_artifact_path,
            opportunity_feature_path=opportunity_feature_path,
            review_reason="opportunity_model_artifact_missing",
        )
        _write_json(artifact_path, payload)
        return payload
    model_payload = _read_pickle(opportunity_model_path)
    metrics_validation = _validate_opportunity_metrics_artifact(
        model_path=opportunity_model_path,
        model_payload=model_payload,
        metrics_path=opportunity_training_metrics_path,
    )
    if metrics_validation["status"] != "PASS":
        payload = _empty_opportunity_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            status="HALT",
            reason=str(metrics_validation["reason"]),
            candidate_artifact_path=candidate_artifact_path,
            opportunity_feature_path=opportunity_feature_path,
            model_version=str(model_payload.get("model_version") or ""),
            review_reason=str(metrics_validation["reason"]),
        )
        payload["halt_reason"] = str(metrics_validation["reason"])
        payload["metrics_validation"] = metrics_validation
        _write_json(artifact_path, payload)
        return payload
    schema_evidence = _opportunity_schema_evidence(
        candidate_artifact_path=candidate_artifact_path,
        opportunity_feature_path=opportunity_feature_path,
        model_payload=model_payload,
        feature_date=feature_date,
    )
    if schema_evidence["schema_status"] != "READY":
        payload = _empty_opportunity_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            status="REVIEW_REQUIRED",
            reason=str(schema_evidence["review_reason"] or "opportunity_feature_schema_mismatch"),
            candidate_artifact_path=candidate_artifact_path,
            opportunity_feature_path=opportunity_feature_path,
            model_version=str(model_payload.get("model_version") or ""),
            schema_evidence=schema_evidence,
        )
        payload["metrics_validation"] = metrics_validation
        _write_json(artifact_path, payload)
        return payload
    result = run_opportunity_inference(
        candidate_path=candidate_artifact_path,
        feature_path=opportunity_feature_path,
        model_path=opportunity_model_path,
        training_metrics_path=opportunity_training_metrics_path,
        output_dir=artifact_path.parent,
        created_at=generated_at,
        inference_run_id=runtime_id,
    )
    if str(result.summary.get("status") or "") != "OK":
        payload = _empty_opportunity_payload(
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            status="REVIEW_REQUIRED",
            reason=str(result.summary.get("readiness_status") or "opportunity_inference_not_ready"),
            candidate_artifact_path=candidate_artifact_path,
            opportunity_feature_path=opportunity_feature_path,
            model_version=str(result.summary.get("model_version") or ""),
            review_reason=str(result.summary.get("readiness_status") or "opportunity_inference_not_ready"),
            schema_evidence=schema_evidence,
        )
        _write_json(artifact_path, payload)
        return payload
    rows = []
    for row in result.output.sort_values(["buy_rank", "code"]).to_dict("records"):
        expected_edge_score = _required_float(row.get("expected_edge_score"), field_name="expected_edge_score")
        buy_rank = _required_rank(row.get("buy_rank"), field_name="buy_rank")
        downside_risk_score = _required_float(row.get("downside_risk_score"), field_name="downside_risk_score")
        rows.append(
            {
                "schema_name": OPPORTUNITY_ARTIFACT_SCHEMA_NAME,
                "artifact_role": OPPORTUNITY_ARTIFACT_ROLE,
                "business_date": business_date,
                "target_date": feature_date,
                "runtime_id": runtime_id,
                "model_version": row.get("model_version"),
                "feature_date": feature_date,
                "code": str(row.get("code") or ""),
                "symbol": str(row.get("code") or ""),
                "expected_edge_score": expected_edge_score,
                "opportunity_score": expected_edge_score,
                "buy_rank": buy_rank,
                "rank": buy_rank,
                "expected_return": expected_edge_score,
                "confidence": _confidence_from_rank(buy_rank),
                "reason": str(row.get("buy_reason") or "opportunity_ai_ranked"),
                "no_buy_reason": str(row.get("no_buy_reason") or ""),
                "is_top5": bool(row.get("is_top5")) if "is_top5" in row else buy_rank <= 5,
                "is_top10": bool(row.get("is_top10")) if "is_top10" in row else buy_rank <= 10,
                "is_top20": bool(row.get("is_top20")) if "is_top20" in row else buy_rank <= 20,
                "generated_at": generated_at,
                "candidate_score": float(row.get("candidate_score") or 0.0),
                "candidate_rank": int(row.get("candidate_rank") or 0),
                "downside_risk_score": downside_risk_score,
            }
        )
    payload = {
        "schema_name": OPPORTUNITY_ARTIFACT_SCHEMA_NAME,
        "schema_version": OPPORTUNITY_ARTIFACT_SCHEMA_VERSION,
        "artifact_role": OPPORTUNITY_ARTIFACT_ROLE,
        "producer": "Runtime v2 BUY AI Producer",
        "producer_version": BUY_AI_INFERENCE_VERSION,
        "business_date": business_date,
        "runtime_id": runtime_id,
        "model_version": str(result.summary.get("model_version") or ""),
        "feature_date": feature_date,
        "generated_at": generated_at,
        "status": "PASS",
        "reason": "",
        "candidate_artifact_path": str(candidate_artifact_path),
        "opportunity_feature_path": str(opportunity_feature_path),
        "opportunity_training_metrics_path": str(opportunity_training_metrics_path),
        "metrics_validation": metrics_validation,
        **_opportunity_schema_payload_fields(schema_evidence),
        "ranking_count": len(rows),
        "rankings": rows,
    }
    _write_json(artifact_path, payload)
    return payload


def _validate_opportunity_metrics_artifact(
    *,
    model_path: Path,
    model_payload: dict[str, Any],
    metrics_path: Path | None,
) -> dict[str, Any]:
    if metrics_path is None:
        return _opportunity_metrics_halt(
            "opportunity_metrics_artifact_not_supplied",
            "Opportunity metrics artifact not supplied. Formal Registry artifact required. Phase5-E fallback prohibited.",
            metrics_path=None,
            model_path=model_path,
        )
    if _is_prohibited_phase5e_metrics_path(metrics_path):
        return _opportunity_metrics_halt(
            "opportunity_phase5e_metrics_rejected",
            "Opportunity Phase5-E metrics artifact is prohibited for Runtime use.",
            metrics_path=metrics_path,
            model_path=model_path,
        )
    if not metrics_path.is_file():
        return _opportunity_metrics_halt(
            "opportunity_metrics_artifact_missing",
            "Opportunity metrics artifact path does not exist.",
            metrics_path=metrics_path,
            model_path=model_path,
        )
    try:
        metrics_payload = _read_json(metrics_path)
    except (OSError, json.JSONDecodeError) as exc:
        return _opportunity_metrics_halt(
            "opportunity_metrics_artifact_invalid_json",
            f"Opportunity metrics artifact is not readable JSON: {exc}",
            metrics_path=metrics_path,
            model_path=model_path,
        )
    model_hash = _file_sha256(model_path)
    metrics_hash = _file_sha256(metrics_path)
    model_set_id = _artifact_set_id(model_payload)
    metrics_set_id = _artifact_set_id(metrics_payload)
    if model_set_id and metrics_set_id and model_set_id != metrics_set_id:
        return _opportunity_metrics_halt(
            "opportunity_model_metrics_artifact_set_mismatch",
            "Opportunity model and metrics artifacts are not from the same Artifact Set.",
            metrics_path=metrics_path,
            model_path=model_path,
            model_hash=model_hash,
            metrics_hash=metrics_hash,
            model_artifact_set_id=model_set_id,
            metrics_artifact_set_id=metrics_set_id,
        )
    metrics_model_path = _payload_path(metrics_payload, "model_artifact_path", "opportunity_model_path", "model_path")
    metrics_model_hash = _payload_hash(metrics_payload, "model_artifact_hash", "opportunity_model_hash", "model_hash")
    metrics_model_path_authority = "path_matches_runtime_model"
    metrics_model_path_hash = ""
    if metrics_model_path and not _same_artifact_path(metrics_model_path, model_path):
        if metrics_model_path.is_file():
            metrics_model_path_hash = _file_sha256(metrics_model_path)
        if metrics_model_hash and metrics_model_hash == model_hash:
            metrics_model_path_authority = "legacy_metrics_path_hash_matches_runtime_model"
        elif metrics_model_path_hash and metrics_model_path_hash == model_hash:
            metrics_model_path_authority = "legacy_metrics_path_content_matches_runtime_model"
        else:
            return _opportunity_metrics_halt(
                "opportunity_metrics_model_path_mismatch",
                "Opportunity metrics artifact points to a different model artifact.",
                metrics_path=metrics_path,
                model_path=model_path,
                model_hash=model_hash,
                metrics_hash=metrics_hash,
                metrics_model_path=metrics_model_path,
                metrics_model_path_hash=metrics_model_path_hash,
            )
    if metrics_model_hash and metrics_model_hash != model_hash:
        return _opportunity_metrics_halt(
            "opportunity_metrics_model_hash_mismatch",
            "Opportunity metrics artifact model hash does not match the supplied model artifact.",
            metrics_path=metrics_path,
            model_path=model_path,
            model_hash=model_hash,
            metrics_hash=metrics_hash,
            metrics_model_hash=metrics_model_hash,
        )
    metrics_feature_columns = [str(column) for column in metrics_payload.get("feature_columns") or ()]
    model_feature_columns = [str(column) for column in model_payload.get("feature_columns") or ()]
    if metrics_feature_columns and model_feature_columns and metrics_feature_columns != model_feature_columns:
        return _opportunity_metrics_halt(
            "opportunity_metrics_feature_schema_mismatch",
            "Opportunity metrics artifact feature schema does not match the supplied model artifact.",
            metrics_path=metrics_path,
            model_path=model_path,
            model_hash=model_hash,
            metrics_hash=metrics_hash,
            metrics_feature_column_count=len(metrics_feature_columns),
            model_feature_column_count=len(model_feature_columns),
        )
    return {
        "status": "PASS",
        "reason": "",
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "model_hash": model_hash,
        "metrics_hash": metrics_hash,
        "model_artifact_set_id": model_set_id,
        "metrics_artifact_set_id": metrics_set_id,
        "metrics_model_path": str(metrics_model_path or ""),
        "metrics_model_path_hash": metrics_model_path_hash,
        "metrics_model_path_authority": metrics_model_path_authority,
        "phase5e_fallback_used": False,
        "consumer_compatibility": "model_metrics_pair_validated_before_opportunity_inference",
    }


def _opportunity_metrics_halt(
    code: str,
    message: str,
    *,
    metrics_path: Path | None,
    model_path: Path,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "status": "HALT",
        "reason": code,
        "message": message,
        "model_path": str(model_path),
        "metrics_path": str(metrics_path or ""),
        "phase5e_fallback_used": False,
        **extra,
    }


def _is_prohibited_phase5e_metrics_path(path: Path) -> bool:
    text = path.as_posix().lower()
    return "reports/opportunity_ai/phase5e/opportunity_training_metrics.json" in text or (
        "phase5e" in text and path.name == PROHIBITED_OPPORTUNITY_PHASE5E_METRICS_PATH.name
    )


def _artifact_set_id(payload: dict[str, Any]) -> str:
    for key in ("artifact_set_id", "opportunity_artifact_set_id", "artifact_set"):
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _payload_path(payload: dict[str, Any], *keys: str) -> Path | None:
    for key in keys:
        value = payload.get(key)
        if value:
            return Path(str(value))
    return None


def _same_artifact_path(left: Path, right: Path) -> bool:
    return left == right or left.resolve(strict=False) == right.resolve(strict=False)


def _payload_hash(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            text = str(value)
            return text.removeprefix("sha256:")
    return ""


def _candidate_payload(
    *,
    business_date: str,
    feature_date: str,
    runtime_id: str,
    generated_at: str,
    model_version: str,
    status: str,
    reason: str,
    feature_path: Path,
    model_path: Path | None,
    artifact_path: Path,
    rows: tuple[dict[str, Any], ...],
    schema_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = schema_evidence or _empty_schema_evidence(
        schema_status="READY" if status == "PASS" else "REVIEW_REQUIRED",
        review_reason=reason,
        artifact_path=feature_path,
        model_version=model_version,
        feature_date=feature_date,
    )
    decisions = [
        {
            "business_date": business_date,
            "target_date": feature_date,
            "feature_date": feature_date,
            "runtime_id": runtime_id,
            "model_version": row.get("model_version") or model_version,
            "generated_at": generated_at,
            "code": str(row.get("code") or ""),
            "symbol": str(row.get("code") or ""),
            "candidate_score": float(row.get("candidate_score") or 0.0),
            "candidate_rank": int(row.get("candidate_rank") or 0),
            "candidate_reason": str(row.get("candidate_reason") or ""),
            "reason": str(row.get("candidate_reason") or ""),
            "confidence": _confidence_from_rank(int(row.get("candidate_rank") or 999999)),
        }
        for row in rows
    ]
    return {
        "schema_version": CANDIDATE_ARTIFACT_SCHEMA_VERSION,
        "business_date": business_date,
        "runtime_id": runtime_id,
        "model_version": model_version,
        "feature_date": feature_date,
        "generated_at": generated_at,
        "status": status,
        "reason": reason,
        "feature_path": str(feature_path),
        "model_path": str(model_path or ""),
        "artifact_path": str(artifact_path),
        "required_columns": list(evidence.get("required_columns") or []),
        "present_columns": list(evidence.get("present_columns") or []),
        "missing_columns": list(evidence.get("missing_columns") or []),
        "unexpected_columns": list(evidence.get("unexpected_columns") or []),
        "alias_risks": dict(evidence.get("alias_risks") or {}),
        "schema_status": str(evidence.get("schema_status") or ""),
        "artifact_schema_version": str(evidence.get("schema_version") or ""),
        "review_required": status != "PASS",
        "review_reason": reason if status != "PASS" else "",
        "candidate_count": len(decisions),
        "rows": decisions,
    }


def _empty_opportunity_payload(
    *,
    business_date: str,
    runtime_id: str,
    feature_date: str,
    generated_at: str,
    status: str,
    reason: str,
    candidate_artifact_path: Path,
    opportunity_feature_path: Path,
    model_version: str = "",
    review_reason: str | None = None,
    candidate_dependency_status: str = "",
    candidate_dependency_reason: str = "",
    schema_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = schema_evidence or _empty_schema_evidence(
        schema_status="REVIEW_REQUIRED" if status != "PASS" else "READY",
        review_reason=review_reason or reason,
        artifact_path=opportunity_feature_path,
        model_version=model_version,
        feature_date=feature_date,
    )
    return {
        "schema_name": OPPORTUNITY_ARTIFACT_SCHEMA_NAME,
        "schema_version": OPPORTUNITY_ARTIFACT_SCHEMA_VERSION,
        "artifact_role": OPPORTUNITY_ARTIFACT_ROLE,
        "producer": "Runtime v2 BUY AI Producer",
        "producer_version": BUY_AI_INFERENCE_VERSION,
        "business_date": business_date,
        "runtime_id": runtime_id,
        "model_version": model_version,
        "feature_date": feature_date,
        "generated_at": generated_at,
        "status": status,
        "reason": reason,
        "candidate_artifact_path": str(candidate_artifact_path),
        "opportunity_feature_path": str(opportunity_feature_path),
        **_opportunity_schema_payload_fields(evidence),
        "candidate_dependency_status": candidate_dependency_status,
        "candidate_dependency_reason": candidate_dependency_reason,
        "ranking_count": 0,
        "rankings": [],
    }


def _result(
    *,
    status: str,
    reason: str,
    business_date: str,
    runtime_id: str,
    feature_date: str,
    generated_at: str,
    candidate_payload: dict[str, Any],
    opportunity_payload: dict[str, Any],
    opportunity_artifact_path: Path,
    ai_signals: tuple[AIPlanningSignal, ...],
) -> BuyAIRuntimeResult:
    return BuyAIRuntimeResult(
        status=status,
        reason=reason,
        business_date=business_date,
        runtime_id=runtime_id,
        feature_date=feature_date,
        candidate_model_version=str(candidate_payload.get("model_version") or ""),
        candidate_artifact_path=str(Path(opportunity_payload.get("candidate_artifact_path") or "")),
        candidate_count=int(candidate_payload.get("candidate_count") or 0),
        opportunity_model_version=str(opportunity_payload.get("model_version") or ""),
        opportunity_artifact_path=str(opportunity_artifact_path),
        opportunity_count=int(opportunity_payload.get("ranking_count") or 0),
        selected_rank_count=len(ai_signals),
        generated_at=generated_at,
        ai_signals=ai_signals,
        candidate_schema_evidence=_schema_evidence_from_payload(candidate_payload, prefix="candidate"),
        opportunity_schema_evidence=_schema_evidence_from_payload(opportunity_payload, prefix="opportunity"),
    )


def _candidate_schema_evidence(
    *,
    frame: pd.DataFrame,
    feature_columns: list[str],
    feature_path: Path,
    model_version: str,
    feature_date: str,
) -> dict[str, Any]:
    required = tuple(_strip_feature_prefix(column) for column in feature_columns)
    present = tuple(str(column) for column in frame.columns)
    missing = tuple(column for column in required if column not in present)
    unexpected = tuple(column for column in present if str(column).startswith("feature__"))
    alias_risks = {
        alias: canonical
        for alias, canonical in CANONICAL_ALIAS_POLICY.items()
        if alias in present and canonical in missing
    }
    missing_keys = tuple(column for column in ("target_date", "code") if column not in present)
    all_missing = tuple(dict.fromkeys(missing_keys + missing))
    status = "READY" if not all_missing and not alias_risks else "REVIEW_REQUIRED"
    reason = "" if status == "READY" else "candidate_feature_schema_mismatch"
    return {
        "schema_status": status,
        "schema_version": "runtime_v2_candidate_feature_input_v1",
        "feature_date": feature_date,
        "model_version": model_version,
        "artifact_path": str(feature_path),
        "required_columns": list(required),
        "present_columns": list(present),
        "missing_columns": list(all_missing),
        "unexpected_columns": list(unexpected),
        "alias_risks": alias_risks,
        "review_required": status != "READY",
        "review_reason": reason,
    }


def _opportunity_schema_evidence(
    *,
    candidate_artifact_path: Path,
    opportunity_feature_path: Path,
    model_payload: dict[str, Any],
    feature_date: str,
) -> dict[str, Any]:
    feature_columns = [str(column) for column in model_payload.get("feature_columns") or ()]
    if not opportunity_feature_path.is_file():
        return _empty_schema_evidence(
            schema_status="REVIEW_REQUIRED",
            review_reason="opportunity_feature_artifact_missing",
            required_columns=tuple(feature_columns),
            artifact_path=opportunity_feature_path,
            model_version=str(model_payload.get("model_version") or ""),
            feature_date=feature_date,
            prefix_policy="artifact_unprefixed_consumer_maps_feature_prefix_once",
        )
    candidate_payload = _read_json(candidate_artifact_path) if candidate_artifact_path.is_file() else {}
    if candidate_payload.get("status") != "PASS":
        return _empty_schema_evidence(
            schema_status="REVIEW_REQUIRED",
            review_reason="candidate_dependency_review_required",
            required_columns=tuple(feature_columns),
            artifact_path=opportunity_feature_path,
            model_version=str(model_payload.get("model_version") or ""),
            feature_date=feature_date,
            prefix_policy="artifact_unprefixed_consumer_maps_feature_prefix_once",
        )
    feature = pd.read_parquet(opportunity_feature_path)
    artifact_columns = tuple(str(column) for column in feature.columns)
    prefixed_artifact_columns = tuple(column for column in artifact_columns if column.startswith("feature__"))
    double_prefix = any(column.startswith("feature__feature__") for column in artifact_columns) or bool(
        prefixed_artifact_columns
    )
    candidate_rows = list(candidate_payload.get("rows") or ())
    candidate_present = set()
    if candidate_rows:
        sample = dict(candidate_rows[0])
        for column in ("candidate_score", "candidate_rank", "candidate_reason"):
            if column in sample:
                candidate_present.add(f"feature__{column}")
    feature_present = {
        column if column.startswith("feature__") else f"feature__{column}"
        for column in artifact_columns
        if column not in {"target_date", "code", "as_of_date", "feature_version", "created_at", "data_until"}
    }
    present = tuple(sorted(candidate_present | feature_present))
    missing = tuple(column for column in feature_columns if column not in set(present))
    model_artifact_columns = tuple(
        _strip_feature_prefix(column)
        for column in feature_columns
        if column not in {"feature__candidate_rank", "feature__candidate_reason", "feature__candidate_score"}
    )
    artifact_model_columns = tuple(column for column in artifact_columns if column in set(model_artifact_columns))
    column_order_status = "MATCH" if artifact_model_columns == model_artifact_columns else "MISMATCH"
    status = (
        "READY"
        if feature_columns and not missing and not prefixed_artifact_columns and column_order_status == "MATCH"
        else "REVIEW_REQUIRED"
    )
    if not feature_columns:
        reason = "opportunity_model_feature_columns_missing"
    elif prefixed_artifact_columns:
        reason = "opportunity_feature_prefix_policy_violation"
    elif missing:
        reason = "opportunity_feature_schema_mismatch"
    elif column_order_status != "MATCH":
        reason = "opportunity_feature_column_order_mismatch"
    else:
        reason = ""
    return {
        "schema_status": status,
        "schema_version": "runtime_v2_opportunity_feature_input_v2",
        "feature_date": feature_date,
        "model_version": str(model_payload.get("model_version") or ""),
        "artifact_path": str(opportunity_feature_path),
        "required_columns": list(feature_columns),
        "present_columns": list(present),
        "required_artifact_columns": list(model_artifact_columns),
        "present_artifact_columns": list(artifact_model_columns),
        "column_order_status": column_order_status,
        "missing_columns": list(missing),
        "unexpected_columns": list(prefixed_artifact_columns),
        "alias_risks": {},
        "prefix_policy": "artifact_unprefixed_consumer_maps_feature_prefix_once",
        "double_prefix_detected": double_prefix,
        "review_required": status != "READY",
        "review_reason": reason,
    }


def _empty_schema_evidence(
    *,
    schema_status: str,
    review_reason: str,
    artifact_path: Path,
    model_version: str,
    feature_date: str,
    required_columns: tuple[str, ...] = (),
    prefix_policy: str = "",
) -> dict[str, Any]:
    return {
        "schema_status": schema_status,
        "schema_version": "",
        "feature_date": feature_date,
        "model_version": model_version,
        "artifact_path": str(artifact_path),
        "required_columns": list(required_columns),
        "present_columns": [],
        "missing_columns": list(required_columns),
        "unexpected_columns": [],
        "alias_risks": {},
        "prefix_policy": prefix_policy,
        "double_prefix_detected": False,
        "review_required": schema_status != "READY",
        "review_reason": review_reason,
    }


def _opportunity_schema_payload_fields(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "required_columns": list(evidence.get("required_columns") or []),
        "present_columns": list(evidence.get("present_columns") or []),
        "missing_columns": list(evidence.get("missing_columns") or []),
        "unexpected_columns": list(evidence.get("unexpected_columns") or []),
        "prefix_policy": str(evidence.get("prefix_policy") or ""),
        "double_prefix_detected": bool(evidence.get("double_prefix_detected")),
        "schema_status": str(evidence.get("schema_status") or ""),
        "artifact_schema_version": str(evidence.get("schema_version") or ""),
        "review_required": bool(evidence.get("review_required")),
        "review_reason": str(evidence.get("review_reason") or ""),
    }


def _schema_evidence_from_payload(payload: dict[str, Any], *, prefix: str) -> dict[str, Any]:
    if prefix == "candidate":
        return {
            "schema_status": payload.get("schema_status") or ("READY" if payload.get("status") == "PASS" else "REVIEW_REQUIRED"),
            "required_columns": payload.get("required_columns") or [],
            "present_columns": payload.get("present_columns") or [],
            "missing_columns": payload.get("missing_columns") or [],
            "unexpected_columns": payload.get("unexpected_columns") or [],
            "alias_risks": payload.get("alias_risks") or {},
            "review_required": bool(payload.get("review_required")),
            "review_reason": payload.get("review_reason") or "",
        }
    return {
        "schema_status": payload.get("schema_status") or ("READY" if payload.get("status") == "PASS" else "REVIEW_REQUIRED"),
        "required_columns": payload.get("required_columns") or [],
        "present_columns": payload.get("present_columns") or [],
        "missing_columns": payload.get("missing_columns") or [],
        "unexpected_columns": payload.get("unexpected_columns") or [],
        "prefix_policy": payload.get("prefix_policy") or "",
        "double_prefix_detected": bool(payload.get("double_prefix_detected")),
        "review_required": bool(payload.get("review_required")),
        "review_reason": payload.get("review_reason") or "",
    }


def _strip_feature_prefix(column: str) -> str:
    return column.replace("feature__", "", 1)


def _confidence_from_rank(rank: int) -> float:
    if rank <= 0 or rank >= 999999:
        return 0.0
    return round(max(0.0, min(1.0, 1.0 - (rank - 1) / 50.0)), 6)


def _required_float(value: Any, *, field_name: str) -> float:
    if value in (None, ""):
        raise ValueError(f"opportunity output missing required field: {field_name}")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"opportunity output invalid numeric field: {field_name}") from exc
    if pd.isna(result):
        raise ValueError(f"opportunity output invalid numeric field: {field_name}")
    return result


def _required_rank(value: Any, *, field_name: str) -> int:
    if value in (None, ""):
        raise ValueError(f"opportunity output missing required field: {field_name}")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"opportunity output invalid rank field: {field_name}") from exc
    if result < 1:
        raise ValueError(f"opportunity output invalid rank field: {field_name}")
    return result


def _read_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    return payload if isinstance(payload, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_json_safe(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _reject_mode_rooted_runtime_root(root: Path) -> None:
    text = str(root)
    if text.endswith("/demo") or "/demo/" in text or text.endswith("/production") or "/production/" in text:
        raise ValueError("mode-rooted Runtime root is not allowed")
