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
from typing import Any, Iterable, Mapping

import pandas as pd
import numpy as np

from ai_fund_lab_v2.runtime_v2.accepted_generation_resolver import (
    AcceptedGenerationResolution,
    resolve_accepted_generation,
)
from ai_fund_lab_v2.candidate_ai.formal_inference import (
    audit_inference_features,
    build_scored_candidates,
    feature_matrix as candidate_feature_matrix,
    predict_scores as predict_candidate_scores,
)
from ai_fund_lab_v2.runtime_v2.market_refresh.consumer_readiness import CANONICAL_ALIAS_POLICY
from ai_fund_lab_v2.opportunity_ai.inference import (
    BLOCKED_BY_INFERENCE,
    READY_FOR_PHASE5G_QUALITY_AUDIT,
    audit_opportunity_inference_frame,
    build_inference_feature_frame,
    build_inference_output,
    normalize_candidate_frame,
    read_feature_frame_for_dates,
    run_opportunity_inference,
)
from ai_fund_lab_v2.runtime_v2.buy_ai.generation_bound_inference import (
    GenerationBoundInferenceError,
    load_generation_bound_binding,
    predict_generation_bound_scores,
)
from ai_fund_lab_v2.runtime_v2.buy_ai.opportunity_eligibility import evaluate_opportunity_buy_eligibility
from ai_fund_lab_v2.runtime_v2.artifact_lookup import (
    RuntimeArtifactLookupHalt,
    require_diagnostic_path_matches_registry,
    resolve_runtime_artifact_set,
)
from ai_fund_lab_v2.runtime_v2.ai_lifecycle_gates import evaluate_runtime_ai_gate
from ai_fund_lab_v2.runtime_v2.lifecycle_evidence import build_runtime_lifecycle_evidence
from ai_fund_lab_v2.runtime_v2.planning.models import AIPlanningSignal
from ai_fund_lab_v2.runtime_v2.storage.json_safe import dumps_json_safe


CANDIDATE_ARTIFACT_SCHEMA_VERSION = "runtime_v2_candidate_decision_v1"
OPPORTUNITY_ARTIFACT_SCHEMA_VERSION = "runtime_v2_opportunity_ranking_v1"
OPPORTUNITY_ARTIFACT_SCHEMA_NAME = "runtime_v2_buy_opportunity_ranking"
OPPORTUNITY_ARTIFACT_ROLE = "BUY_OPPORTUNITY_RANKING"
BUY_AI_INFERENCE_VERSION = "candidate_opportunity_ai_regular_path_v1"
CANDIDATE_PIT_QUALITY_SURFACE_SCHEMA_VERSION = "candidate_pit_quality_surface.v1"
CANDIDATE_HYBRID_ORDERING_SCHEMA_VERSION = "candidate_hybrid_ordering_contract.v1"
DEFAULT_CANDIDATE_MODEL_PATH = Path(".runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl")
DEFAULT_OPPORTUNITY_MODEL_PATH = Path("reports/opportunity_ai/phase5p/models/opportunity_model.pkl")
PROHIBITED_OPPORTUNITY_PHASE5E_METRICS_PATH = Path("reports/opportunity_ai/phase5e/opportunity_training_metrics.json")
BUY_QUALITY_PROPAGATED_FEATURE_COLUMNS = (
    "price_momentum_return_1d",
    "price_momentum_return_3d",
    "price_momentum_return_5d",
    "price_momentum_return_10d",
    "price_momentum_return_20d",
    "price_momentum_return_60d",
    "volatility_return_std_20d",
    "recent_move_volatility_z_1d",
    "recent_move_volatility_z_3d",
    "momentum_5d_vs_20d_delta",
    "momentum_1d_vs_5d_delta",
    "trend_close_over_ma_20d",
    "trend_ma_5_20_ratio",
    "trend_ma_20_60_ratio",
    "volume_momentum_ratio_5d",
    "volume_momentum_ratio_1d_20d",
    "liquidity_avg_volume_20d",
)


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
    lifecycle_gate_evidence: dict[str, Any] | None = None

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
            "ai_lifecycle_gate": self.lifecycle_gate_evidence or {},
            "ai_lifecycle_gate_decision": (self.lifecycle_gate_evidence or {}).get("decision") or "",
            "ai_lifecycle_gate_classification": (self.lifecycle_gate_evidence or {}).get("classification") or "",
            "ai_lifecycle_gate_monitoring_action": (self.lifecycle_gate_evidence or {}).get("monitoring_action") or "",
            "ai_lifecycle_gate_trading_permission_effect": (self.lifecycle_gate_evidence or {}).get("trading_permission_effect") or "",
            "ai_lifecycle_gate_runtime_integrity_status": (self.lifecycle_gate_evidence or {}).get("runtime_integrity_status") or "",
            "ai_lifecycle_gate_block_buy": bool((self.lifecycle_gate_evidence or {}).get("block_buy")),
            "ai_lifecycle_gate_block_sell": bool((self.lifecycle_gate_evidence or {}).get("block_sell")),
            "ai_lifecycle_gate_block_submit": bool((self.lifecycle_gate_evidence or {}).get("block_submit")),
            "ai_lifecycle_gate_block_buy_planning": bool((self.lifecycle_gate_evidence or {}).get("block_buy_planning")),
            "ai_lifecycle_gate_block_buy_submit": bool((self.lifecycle_gate_evidence or {}).get("block_buy_submit")),
            "ai_lifecycle_gate_block_sell_planning": bool((self.lifecycle_gate_evidence or {}).get("block_sell_planning")),
            "ai_lifecycle_gate_block_sell_submit": bool((self.lifecycle_gate_evidence or {}).get("block_sell_submit")),
            "ai_lifecycle_gate_allow_current_refresh": bool((self.lifecycle_gate_evidence or {}).get("allow_current_refresh", True)),
            "ai_lifecycle_gate_allow_valuation_refresh": bool((self.lifecycle_gate_evidence or {}).get("allow_valuation_refresh", True)),
            "ai_lifecycle_gate_allow_position_management": bool((self.lifecycle_gate_evidence or {}).get("allow_position_management", True)),
            "ai_lifecycle_gate_allow_safety_evaluation": bool((self.lifecycle_gate_evidence or {}).get("allow_safety_evaluation", True)),
            "ai_lifecycle_gate_allow_sell_planning": bool((self.lifecycle_gate_evidence or {}).get("allow_sell_planning", True)),
            "ai_lifecycle_gate_allow_sell_submit_authorization": bool((self.lifecycle_gate_evidence or {}).get("allow_sell_submit_authorization", True)),
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
    accepted_buy_ai_bundle_path: Path | str | None = None,
    historical_evaluation_authority_path: Path | str | None = None,
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
    lifecycle_gate_artifact_path = artifact_dir / "ai_lifecycle_gate_decision.json"
    feature_dir = Path(feature_root) / feature_date
    candidate_feature_path = feature_dir / "candidate_features.parquet"
    opportunity_feature_path = feature_dir / "opportunity_feature_input.parquet"
    allow_isolated_test_paths = _isolated_test_artifact_paths_allowed(
        root,
        candidate_model_path,
        opportunity_model_path,
        opportunity_training_metrics_path,
    )
    accepted_generation_resolution: AcceptedGenerationResolution | None = None
    if not allow_isolated_test_paths:
        accepted_generation_resolution = resolve_accepted_generation(
            root,
            business_date=business_date,
            fixed_authority_path=historical_evaluation_authority_path,
        )
        if not accepted_generation_resolution.is_resolved:
            return _accepted_generation_block_result(
                resolution=accepted_generation_resolution,
                artifact_path=lifecycle_gate_artifact_path,
                candidate_artifact_path=candidate_artifact_path,
                opportunity_artifact_path=opportunity_artifact_path,
                candidate_feature_path=candidate_feature_path,
                opportunity_feature_path=opportunity_feature_path,
                business_date=business_date,
                runtime_id=runtime_id,
                feature_date=feature_date,
                generated_at=generated_at,
            )
    try:
        artifact_paths = (
            accepted_generation_resolution.artifact_paths()
            if accepted_generation_resolution is not None
            else resolve_buy_ai_artifact_paths(
                candidate_model_path=candidate_model_path,
                opportunity_model_path=opportunity_model_path,
                opportunity_training_metrics_path=opportunity_training_metrics_path,
                allow_isolated_test_paths=allow_isolated_test_paths,
            )
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
        accepted_generation_resolution=accepted_generation_resolution,
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
        accepted_generation_resolution=accepted_generation_resolution,
    )
    lifecycle_gate = _evaluate_and_write_lifecycle_gate(
        artifact_path=lifecycle_gate_artifact_path,
        business_date=business_date,
        feature_date=feature_date,
        runtime_id=runtime_id,
        generated_at=generated_at,
        candidate_payload=candidate_payload,
        opportunity_payload=opportunity_payload,
        runtime_root=root,
        artifact_paths=artifact_paths,
        accepted_buy_ai_bundle_path=accepted_buy_ai_bundle_path,
        accepted_generation_resolution=accepted_generation_resolution,
    )
    if not allow_isolated_test_paths and lifecycle_gate.get("trading_permission_effect") == "BUY_BLOCK":
        opportunity_payload["ai_lifecycle_gate"] = lifecycle_gate
        opportunity_payload["status"] = "BLOCKED" if lifecycle_gate["decision"] == "BLOCK" else "REVIEW_REQUIRED"
        opportunity_payload["reason"] = f"ai_lifecycle_gate_{lifecycle_gate['decision'].lower()}"
        _write_json(opportunity_artifact_path, opportunity_payload)
        return _result(
            status=str(opportunity_payload["status"]),
            reason=str(opportunity_payload["reason"]),
            business_date=business_date,
            runtime_id=runtime_id,
            feature_date=feature_date,
            generated_at=generated_at,
            candidate_payload=candidate_payload,
            opportunity_payload=opportunity_payload,
            opportunity_artifact_path=opportunity_artifact_path,
            ai_signals=(),
            lifecycle_gate_evidence=lifecycle_gate,
        )
    opportunity_payload["ai_lifecycle_gate"] = lifecycle_gate
    _write_json(opportunity_artifact_path, opportunity_payload)
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
        lifecycle_gate_evidence=lifecycle_gate,
    )


def _accepted_generation_block_result(
    *,
    resolution: AcceptedGenerationResolution,
    artifact_path: Path,
    candidate_artifact_path: Path,
    opportunity_artifact_path: Path,
    candidate_feature_path: Path,
    opportunity_feature_path: Path,
    business_date: str,
    runtime_id: str,
    feature_date: str,
    generated_at: str,
) -> BuyAIRuntimeResult:
    reason = resolution.block_reason or resolution.resolution_status
    candidate_payload = _candidate_payload(
        business_date=business_date,
        feature_date=feature_date,
        runtime_id=runtime_id,
        generated_at=generated_at,
        model_version="",
        status="REVIEW_REQUIRED",
        reason=reason,
        feature_path=candidate_feature_path,
        model_path=None,
        artifact_path=candidate_artifact_path,
        rows=(),
        schema_evidence=_empty_schema_evidence(
            schema_status="REVIEW_REQUIRED",
            review_reason=reason,
            artifact_path=candidate_feature_path,
            model_version="",
            feature_date=feature_date,
        ),
    )
    _write_json(candidate_artifact_path, candidate_payload)
    opportunity_payload = _empty_opportunity_payload(
        business_date=business_date,
        runtime_id=runtime_id,
        feature_date=feature_date,
        generated_at=generated_at,
        status="REVIEW_REQUIRED",
        reason=reason,
        candidate_artifact_path=candidate_artifact_path,
        opportunity_feature_path=opportunity_feature_path,
        review_reason=reason,
    )
    _write_json(opportunity_artifact_path, opportunity_payload)
    lifecycle_gate = _evaluate_and_write_lifecycle_gate(
        artifact_path=artifact_path,
        business_date=business_date,
        feature_date=feature_date,
        runtime_id=runtime_id,
        generated_at=generated_at,
        candidate_payload=candidate_payload,
        opportunity_payload=opportunity_payload,
        runtime_root=artifact_path.parents[3],
        artifact_paths={},
        accepted_generation_resolution=resolution,
    )
    status = "BLOCKED" if lifecycle_gate["decision"] == "BLOCK" else "REVIEW_REQUIRED"
    opportunity_payload["ai_lifecycle_gate"] = lifecycle_gate
    opportunity_payload["status"] = status
    opportunity_payload["reason"] = reason
    _write_json(opportunity_artifact_path, opportunity_payload)
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
        ai_signals=(),
        lifecycle_gate_evidence=lifecycle_gate,
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
                score=float(row.get("runtime_opportunity_score", row.get("opportunity_score", row.get("expected_edge_score", 0.0))) or 0.0),
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
    accepted_generation_resolution: AcceptedGenerationResolution | None = None,
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
    generation_binding = None
    if accepted_generation_resolution is not None:
        try:
            generation_binding = load_generation_bound_binding(
                resolution=accepted_generation_resolution,
                component="candidate",
                repo_root=Path("."),
            )
            model_payload = generation_binding.model_payload
        except GenerationBoundInferenceError as exc:
            payload = _candidate_payload(
                business_date=business_date,
                feature_date=feature_date,
                runtime_id=runtime_id,
                generated_at=generated_at,
                model_version="",
                status="HALT",
                reason=exc.reason_code,
                feature_path=feature_path,
                model_path=model_path,
                artifact_path=artifact_path,
                rows=(),
            )
            payload["halt_reason"] = exc.reason_code
            _write_json(artifact_path, payload)
            return payload
    else:
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
    try:
        scores = (
            predict_generation_bound_scores(generation_binding, latest)
            if generation_binding is not None
            else predict_candidate_scores(model_payload["model"], candidate_feature_matrix(latest, feature_columns))
        )
    except GenerationBoundInferenceError as exc:
        payload = _candidate_payload(
            business_date=business_date,
            feature_date=feature_date,
            runtime_id=runtime_id,
            generated_at=generated_at,
            model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
            status="HALT",
            reason=exc.reason_code,
            feature_path=feature_path,
            model_path=model_path,
            artifact_path=artifact_path,
            rows=(),
            schema_evidence=schema_evidence,
        )
        payload["halt_reason"] = exc.reason_code
        if generation_binding is not None:
            payload["generation_bound_inference"] = generation_binding.evidence()
        _write_json(artifact_path, payload)
        return payload
    rows = build_scored_candidates(
        latest.to_dict("records"),
        scores,
        model_version=str(model_payload.get("model_version") or "phase4bf_formal_candidate_model"),
    )
    feature_rows_by_code = {
        str(row.get("code") or ""): row
        for row in latest.to_dict("records")
        if str(row.get("code") or "")
    }
    rows = [
        {
            **row,
            **_buy_quality_feature_metadata(
                feature_rows_by_code.get(str(row.get("code") or ""), {})
            ),
            **_candidate_listed_info_metadata(
                feature_rows_by_code.get(str(row.get("code") or ""), {})
            ),
        }
        for row in rows
    ]
    rows = sorted(rows, key=lambda row: (-float(row["candidate_score"]), str(row["code"])))
    for index, row in enumerate(rows, start=1):
        row["candidate_rank"] = index
        row["score_only_candidate_rank"] = index
        row["candidate_score_semantic_role"] = "momentum_candidate_label_model_score"
    liquidity_lineage_evidence = _candidate_liquidity_lineage_evidence(
        rows,
        feature_path=feature_path,
        business_date=business_date,
        feature_date=feature_date,
    )
    surfaced_rows, surface_evidence = _apply_candidate_pit_quality_surface(
        rows,
        top_n=top_n,
        liquidity_lineage_evidence=liquidity_lineage_evidence,
    )
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
        rows=tuple(surfaced_rows),
        schema_evidence=schema_evidence,
        surface_evidence=surface_evidence,
    )
    if generation_binding is not None:
        payload["generation_bound_inference"] = generation_binding.evidence()
        payload["accepted_generation_binding"] = accepted_generation_resolution.binding_evidence(
            runtime_mode="runtime",
            business_date=business_date,
            consumer="buy_ai_candidate",
        ) if accepted_generation_resolution is not None else {}
        payload["transformation_stage"] = "accepted_generation_bound_imputer_scaler_model"
        payload["legacy_fallback_used"] = False
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
    accepted_generation_resolution: AcceptedGenerationResolution | None = None,
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
    model_authority = _opportunity_model_authority(
        accepted_generation_resolution=accepted_generation_resolution,
        model_path=opportunity_model_path,
        model_payload=model_payload,
    )
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
            model_authority=model_authority,
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
            model_authority=model_authority,
            schema_evidence=schema_evidence,
        )
        payload["metrics_validation"] = metrics_validation
        _write_json(artifact_path, payload)
        return payload
    generation_binding = None
    if accepted_generation_resolution is None:
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
            model_authority = model_authority or _opportunity_model_authority(
                accepted_generation_resolution=accepted_generation_resolution,
                model_path=opportunity_model_path,
                model_payload=model_payload,
                result_summary=result.summary,
            )
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
                model_authority=model_authority,
                review_reason=str(result.summary.get("readiness_status") or "opportunity_inference_not_ready"),
                schema_evidence=schema_evidence,
            )
            _write_json(artifact_path, payload)
            return payload
        output = result.output
        result_summary = result.summary
    else:
        try:
            generation_binding = load_generation_bound_binding(
                resolution=accepted_generation_resolution,
                component="opportunity",
                repo_root=Path("."),
            )
            candidate_payload = _read_json(candidate_artifact_path)
            candidate_rows = pd.DataFrame(candidate_payload.get("rows") or [])
            candidate = normalize_candidate_frame(candidate_rows)
            target_dates = sorted(candidate["target_date"].dropna().astype(str).unique().tolist())
            feature = read_feature_frame_for_dates(opportunity_feature_path, target_dates)
            inference_frame = build_inference_feature_frame(candidate_frame=candidate, feature_frame=feature)
            feature_columns = list(generation_binding.feature_order)
            audit = audit_opportunity_inference_frame(
                inference_frame,
                feature_columns=feature_columns,
                input_candidate_count=len(candidate),
                label_table_read_flag=False,
                created_at=generated_at,
            )
            if audit["leakage_audit_status"] != "OK":
                raise GenerationBoundInferenceError("opportunity_feature_leakage_audit_failed")
            if inference_frame.empty:
                raise GenerationBoundInferenceError("opportunity_join_coverage_empty")
            scores = predict_generation_bound_scores(generation_binding, inference_frame)
            output = build_inference_output(
                inference_frame,
                scores=np.asarray(scores, dtype=float),
                model_version=str(model_payload.get("model_version") or "opportunity_model_unknown"),
                created_at=generated_at,
                inference_run_id=runtime_id,
            )
            result_summary = {
                "status": "OK",
                "readiness_status": READY_FOR_PHASE5G_QUALITY_AUDIT,
                "model_version": str(model_payload.get("model_version") or "opportunity_model_unknown"),
            }
        except GenerationBoundInferenceError as exc:
            model_authority = model_authority or _opportunity_model_authority(
                accepted_generation_resolution=accepted_generation_resolution,
                model_path=opportunity_model_path,
                model_payload=model_payload,
                result_summary={"readiness_status": exc.reason_code},
            )
            payload = _empty_opportunity_payload(
                business_date=business_date,
                runtime_id=runtime_id,
                feature_date=feature_date,
                generated_at=generated_at,
                status="HALT",
                reason=exc.reason_code,
                candidate_artifact_path=candidate_artifact_path,
                opportunity_feature_path=opportunity_feature_path,
                model_version=str(model_payload.get("model_version") or ""),
                model_authority=model_authority,
                review_reason=exc.reason_code,
                schema_evidence=schema_evidence,
            )
            payload["halt_reason"] = exc.reason_code
            payload["readiness_status"] = BLOCKED_BY_INFERENCE
            payload["generation_bound_inference"] = {"status": "HALT", "reason": exc.reason_code}
            _write_json(artifact_path, payload)
            return payload
    model_authority = model_authority or _opportunity_model_authority(
        accepted_generation_resolution=accepted_generation_resolution,
        model_path=opportunity_model_path,
        model_payload=model_payload,
        result_summary=result_summary,
    )
    model_version = str(model_authority.get("model_version") or result_summary.get("model_version") or "")
    candidate_listed_info_by_code = _candidate_listed_info_by_code(candidate_artifact_path)
    opportunity_feature_by_code = _feature_metadata_by_code(
        opportunity_feature_path,
        feature_date=feature_date,
    )
    rows = []
    for row in output.sort_values(["buy_rank", "code"]).to_dict("records"):
        expected_edge_score = _required_float(row.get("expected_edge_score"), field_name="expected_edge_score")
        buy_rank = _required_rank(row.get("buy_rank"), field_name="buy_rank")
        downside_risk_score = _required_float(row.get("downside_risk_score"), field_name="downside_risk_score")
        code = str(row.get("code") or "")
        rows.append(
            {
                "schema_name": OPPORTUNITY_ARTIFACT_SCHEMA_NAME,
                "artifact_role": OPPORTUNITY_ARTIFACT_ROLE,
                "business_date": business_date,
                "target_date": feature_date,
                "runtime_id": runtime_id,
                "model_version": model_version,
                "feature_date": feature_date,
                "code": code,
                "symbol": code,
                "runtime_opportunity_score": expected_edge_score,
                "expected_edge_score": expected_edge_score,
                "opportunity_score": expected_edge_score,
                "buy_rank": buy_rank,
                "rank": buy_rank,
                "expected_return": expected_edge_score,
                "score_semantic_role": "uncalibrated_relative_model_score",
                "economic_units_available": False,
                "calibration_applied": False,
                "expected_edge_score_semantic_role": "deprecated_alias_uncalibrated_runtime_opportunity_score",
                "expected_return_semantic_role": "deprecated_alias_uncalibrated_runtime_opportunity_score_not_economic_return",
                "opportunity_score_semantic_role": "deprecated_alias_uncalibrated_runtime_opportunity_score",
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
                **_buy_quality_feature_metadata(opportunity_feature_by_code.get(code, {})),
                **candidate_listed_info_by_code.get(code, {}),
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
        "model_version": model_version,
        "model_authority": model_authority,
        "feature_date": feature_date,
        "generated_at": generated_at,
        "status": "PASS",
        "reason": "",
        "prediction_metric_name": "opportunity_score",
        "prediction_semantics": "runtime_opportunity_score",
        "canonical_score_field": "runtime_opportunity_score",
        "score_semantic_role": "uncalibrated_relative_model_score",
        "economic_units_available": False,
        "deprecated_score_aliases": {
            "expected_edge_score": "uncalibrated_runtime_opportunity_score_alias_not_economic_edge",
            "expected_return": "uncalibrated_runtime_opportunity_score_alias_not_economic_return",
            "opportunity_score": "uncalibrated_runtime_opportunity_score_alias",
        },
        "transformation_stage": (
            "accepted_generation_bound_imputer_scaler_model"
            if generation_binding is not None
            else "runtime_artifact_opportunity_score"
        ),
        "calibration_applied": False,
        "legacy_fallback_used": False if generation_binding is not None else True,
        "population_scope": "CandidateTop50_single_business_day",
        "candidate_artifact_path": str(candidate_artifact_path),
        "opportunity_feature_path": str(opportunity_feature_path),
        "opportunity_training_metrics_path": str(opportunity_training_metrics_path),
        "metrics_validation": metrics_validation,
        "generation_bound_inference": generation_binding.evidence() if generation_binding is not None else {},
        "accepted_generation_binding": accepted_generation_resolution.binding_evidence(
            runtime_mode="runtime",
            business_date=business_date,
            consumer="buy_ai_opportunity",
        ) if accepted_generation_resolution is not None else {},
        **_opportunity_schema_payload_fields(schema_evidence),
        "ranking_count": len(rows),
        "rankings": rows,
    }
    _write_json(artifact_path, payload)
    return payload


def _opportunity_model_authority(
    *,
    accepted_generation_resolution: AcceptedGenerationResolution | None,
    model_path: Path,
    model_payload: dict[str, Any],
    result_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if accepted_generation_resolution is not None and accepted_generation_resolution.opportunity_member is not None:
        member = accepted_generation_resolution.opportunity_member
        model_hash = str(member.model_hash or "")
        generation_id = str(accepted_generation_resolution.generation_id or "")
        model_version = f"{generation_id}:opportunity:{model_hash[:16]}" if generation_id and model_hash else ""
        actual_hash = _file_sha256(model_path) if model_path.is_file() else ""
        return {
            "schema_version": "runtime_v2_opportunity_model_authority_v1",
            "authority_source": "Accepted Generation COMMITTED opportunity_member",
            "resolution_status": accepted_generation_resolution.resolution_status,
            "accepted_generation_id": generation_id,
            "bundle_manifest_path": accepted_generation_resolution.bundle_manifest_path,
            "model_version": model_version,
            "model_identity": model_version,
            "model_component": "opportunity",
            "model_file": str(member.artifact_path),
            "runtime_model_file": str(model_path),
            "model_ref": str(getattr(member, "model_ref", "") or ""),
            "model_hash": model_hash,
            "runtime_model_hash": actual_hash,
            "hash_match": bool(model_hash and actual_hash and model_hash == actual_hash),
            "authority_hash": accepted_generation_resolution.aggregate_hash,
        }
    model_version = str(model_payload.get("model_version") or (result_summary or {}).get("model_version") or "")
    if not model_version or model_version == "opportunity_model_unknown":
        return {}
    model_hash = _file_sha256(model_path) if model_path.is_file() else ""
    return {
        "schema_version": "runtime_v2_opportunity_model_authority_v1",
        "authority_source": "runtime_loaded_model_payload",
        "resolution_status": "FIXTURE_OR_EXPLICIT_MODEL_PATH",
        "accepted_generation_id": "",
        "bundle_manifest_path": "",
        "model_version": model_version,
        "model_identity": model_version,
        "model_component": "opportunity",
        "model_file": str(model_path),
        "runtime_model_file": str(model_path),
        "model_ref": "",
        "model_hash": model_hash,
        "runtime_model_hash": model_hash,
        "hash_match": bool(model_hash),
        "authority_hash": model_hash,
    }


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


def _evaluate_and_write_lifecycle_gate(
    *,
    artifact_path: Path,
    business_date: str,
    feature_date: str,
    runtime_id: str,
    generated_at: str,
    candidate_payload: dict[str, Any],
    opportunity_payload: dict[str, Any],
    runtime_root: Path,
    artifact_paths: dict[str, Path],
    accepted_buy_ai_bundle_path: Path | str | None = None,
    accepted_generation_resolution: AcceptedGenerationResolution | None = None,
) -> dict[str, Any]:
    lifecycle_evidence = build_runtime_lifecycle_evidence(
        runtime_root=runtime_root,
        business_date=business_date,
        feature_date=feature_date,
        runtime_id=runtime_id,
        candidate_payload=candidate_payload,
        opportunity_payload={**opportunity_payload, "artifact_path": str(artifact_path)},
        artifact_paths=artifact_paths,
        accepted_bundle_path=accepted_buy_ai_bundle_path,
        accepted_generation_resolution=accepted_generation_resolution,
    ).to_dict()
    gate = evaluate_runtime_ai_gate(lifecycle_evidence["gate_input"]).to_dict()
    gate.update(
        {
            "schema_version": "runtime_ai_lifecycle_gate_decision.v1",
            "business_date": business_date,
            "feature_date": feature_date,
            "runtime_id": runtime_id,
            "generated_at": generated_at,
            "created_at": generated_at,
            "inference_execution_permission": "PASS",
            "buy_planning_permission": "BLOCK" if gate["block_buy_planning"] else "PASS",
            "buy_submit_permission": "BLOCK" if gate["block_buy_submit"] else "PASS",
            "sell_planning_permission": "BLOCK" if gate["block_sell_planning"] else "PASS",
            "sell_submit_authorization_permission": "BLOCK" if gate["block_sell_submit"] else "PASS",
            "sell_permission": "PASS" if not gate["block_sell"] else "BLOCK",
            **lifecycle_evidence["artifact_fields"],
        }
    )
    _write_json(artifact_path, gate)
    return gate


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
        value = payload.get(key) or _nested_value(payload, "bindings", key)
        if value:
            return Path(str(value))
    return None


def _same_artifact_path(left: Path, right: Path) -> bool:
    return left == right or left.resolve(strict=False) == right.resolve(strict=False)


def _payload_hash(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = (
            payload.get(key)
            or _nested_value(payload, "bindings", key)
            or _nested_value(payload, "component_hashes", key)
        )
        if value:
            text = str(value)
            return text.removeprefix("sha256:")
    return ""


def _nested_value(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _candidate_listed_info_by_code(candidate_artifact_path: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = _read_json(candidate_artifact_path)
    except FileNotFoundError:
        return {}
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("code") or row.get("symbol") or ""): _candidate_listed_info_metadata(row)
        for row in rows
        if isinstance(row, Mapping) and _candidate_listed_info_metadata(row)
    }


def _candidate_listed_info_metadata(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    nested = row.get("listed_info")
    if isinstance(nested, Mapping):
        nested_info = _listed_info_payload(row, nested)
        if nested_info is not None:
            return _listed_info_metadata_fields(nested_info)
    info = _listed_info_payload(row, row)
    if info is None:
        return {}
    return _listed_info_metadata_fields(info)


def _listed_info_metadata_fields(info: Mapping[str, Any]) -> dict[str, Any]:
    market = str(info.get("market") or "").strip()
    product_category = str(info.get("product_category") or "").strip()
    security_type = str(info.get("security_type") or product_category).strip()
    current_listed = bool(info.get("current_listed", True))
    listed_info = {
        "code": str(info.get("code") or "").strip(),
        "market": market,
        "product_category": product_category,
        "security_type": security_type,
        "current_listed": current_listed,
    }
    return {
        "market": market,
        "market_name": market,
        "product_category": product_category,
        "security_type": security_type,
        "current_listed": current_listed,
        "is_current_listed": current_listed,
        "listed_info": listed_info,
    }


def _feature_metadata_by_code(path: Path, *, feature_date: str) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    frame = pd.read_parquet(path)
    if "target_date" in frame.columns:
        frame = frame[frame["target_date"].astype(str) == feature_date].copy()
    if "code" not in frame.columns:
        return {}
    return {
        str(row.get("code") or ""): row
        for row in frame.to_dict("records")
        if str(row.get("code") or "")
    }


def _buy_quality_feature_metadata(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    metadata: dict[str, Any] = {}
    for column in BUY_QUALITY_PROPAGATED_FEATURE_COLUMNS:
        if column not in row:
            continue
        value = row.get(column)
        if value is None:
            continue
        if isinstance(value, float) and np.isnan(value):
            continue
        metadata[column] = value
    return metadata


def _candidate_liquidity_lineage_evidence(
    rows: Iterable[Mapping[str, Any]],
    *,
    feature_path: Path | None,
    business_date: str,
    feature_date: str,
) -> dict[str, Any]:
    materialized_rows = list(rows)
    present_count = sum(
        1
        for row in materialized_rows
        if _optional_float(row.get("liquidity_avg_volume_20d")) is not None
    )
    return {
        "source_artifact": str(feature_path or ""),
        "source_field": "liquidity_avg_volume_20d",
        "source_date": feature_date,
        "as_of_date": feature_date,
        "business_date": business_date,
        "pit_safety": {
            "feature_date_lte_business_date": str(feature_date) <= str(business_date),
            "source_is_candidate_feature_artifact": True,
            "future_row_used": False,
            "same_day_future_execution_used": False,
            "eod_future_reconstruction_used": False,
        },
        "missing_status": "PASS" if present_count > 0 else "MISSING",
        "present_row_count": present_count,
        "missing_row_count": len(materialized_rows) - present_count,
        "total_row_count": len(materialized_rows),
        "canonical_liquidity_authority_reused": True,
        "duplicate_liquidity_authority_created": False,
        "fallback_liquidity_heuristic_used": False,
    }


def _apply_candidate_pit_quality_surface(
    rows: list[dict[str, Any]],
    *,
    top_n: int,
    liquidity_lineage_evidence: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    score_only_top = rows[:top_n]
    score_only_symbols = [str(row.get("code") or "") for row in score_only_top]
    surfaced_population = [
        _with_candidate_hybrid_ordering(_with_candidate_pit_quality_surface(row))
        for row in rows
    ]
    quality_ordered = sorted(
        surfaced_population,
        key=lambda row: (
            _semantic_hybrid_priority(row),
            -_candidate_score_sort_value(row),
            _surface_state_preference(row),
            str(row.get("code") or ""),
        ),
    )
    quality_top = quality_ordered[:top_n]
    for index, row in enumerate(quality_top, start=1):
        row["quality_aware_candidate_rank"] = index
        row["quality_aware_top50_member"] = True
    quality_symbols = [str(row.get("code") or "") for row in quality_top]
    added = [symbol for symbol in quality_symbols if symbol not in set(score_only_symbols)]
    removed = [symbol for symbol in score_only_symbols if symbol not in set(quality_symbols)]
    liquidity_present_count = sum(
        1
        for row in surfaced_population
        if _optional_float(row.get("liquidity_avg_volume_20d")) is not None
    )
    evidence = {
        "schema_version": CANDIDATE_PIT_QUALITY_SURFACE_SCHEMA_VERSION,
        "hybrid_ordering_schema_version": CANDIDATE_HYBRID_ORDERING_SCHEMA_VERSION,
        "ordering_contract": (
            "SEMANTIC_HYBRID_ELIGIBILITY_BANDS_WITH_CANDIDATE_SCORE_WITHIN_CLASS_AUTHORITY"
        ),
        "not_buy_authority": True,
        "candidate_model_preserved": True,
        "candidate_score_semantic_role": "momentum_candidate_label_model_score",
        "candidate_score_role": "CO_EQUAL_HYBRID_EVIDENCE",
        "candidate_rank_semantic_role": "score_only_model_rank_observable_evidence",
        "candidate_surface_role": "SEMANTIC_HYBRID_AUTHORITY",
        "quality_aware_candidate_rank_semantic_role": "candidate_stage_semantic_hybrid_surface_order",
        "top_n": top_n,
        "market_eligible_count": len(rows),
        "candidate_pre_cut_count": len(rows),
        "liquidity_source_field": "liquidity_avg_volume_20d",
        "liquidity_present_row_count": liquidity_present_count,
        "liquidity_missing_row_count": len(surfaced_population) - liquidity_present_count,
        "liquidity_evidence_lineage": liquidity_lineage_evidence or {},
        "candidate_score_distribution": _numeric_distribution(row.get("candidate_score") for row in rows),
        "candidate_rank_distribution": _numeric_distribution(row.get("candidate_rank") for row in rows),
        "score_evidence_class_distribution": _field_distribution(surfaced_population, "score_evidence_class"),
        "semantic_hybrid_class_distribution": _field_distribution(surfaced_population, "semantic_hybrid_class"),
        "top50_score_evidence_class_distribution": _field_distribution(quality_top, "score_evidence_class"),
        "top50_semantic_hybrid_class_distribution": _field_distribution(quality_top, "semantic_hybrid_class"),
        "candidate_pit_surface_distribution": _surface_distribution(surfaced_population),
        "top50_surface_distribution": _surface_distribution(quality_top),
        "market_healthy_proxy_count": sum(1 for row in surfaced_population if row.get("candidate_pit_market_healthy_proxy")),
        "candidate_healthy_proxy_count": sum(1 for row in quality_top if row.get("candidate_pit_market_healthy_proxy")),
        "healthy_proxy_capture_ratio": _safe_rate(
            sum(1 for row in quality_top if row.get("candidate_pit_market_healthy_proxy")),
            sum(1 for row in surfaced_population if row.get("candidate_pit_market_healthy_proxy")),
        ),
        "final_top50_symbol_order": quality_symbols,
        "score_only_top50_symbol_order": score_only_symbols,
        "score_only_ordering_changed": quality_symbols != score_only_symbols,
        "quality_aware_added_symbols": added,
        "quality_aware_removed_symbols": removed,
        "quality_aware_added_count": len(added),
        "quality_aware_removed_count": len(removed),
        "future_information_used": False,
        "historical_outcome_used_as_runtime_input": False,
        "historical_outcome_used_for_production_parameter_selection": False,
        "test_result_used_as_strategy_input": False,
        "candidate_top50_count_changed": False,
        "candidate_model_retrained": False,
        "candidate_accepted_generation_changed": False,
        "new_ai_created": False,
        "parallel_candidate_path_created": False,
        "weighted_hybrid_score_created": False,
        "hard_lexicographic_surface_first_retired": True,
        "score_only_dominance_retired": True,
        "one_production_candidate_path": True,
    }
    return quality_top, evidence


def _semantic_hybrid_priority(row: Mapping[str, Any]) -> int:
    value = row.get("semantic_hybrid_class_priority")
    if value is None:
        return 99
    try:
        return int(value)
    except (TypeError, ValueError):
        return 99


def _candidate_score_sort_value(row: Mapping[str, Any]) -> float:
    value = _optional_float(row.get("candidate_score"))
    return float(value) if value is not None else 0.0


def _surface_state_preference(row: Mapping[str, Any]) -> int:
    value = row.get("candidate_pit_surface_priority")
    if value is None:
        return 99
    try:
        return int(value)
    except (TypeError, ValueError):
        return 99


def _with_candidate_hybrid_ordering(row: dict[str, Any]) -> dict[str, Any]:
    score_class = _candidate_score_evidence_class(row)
    semantic_class, priority, reason = _candidate_semantic_hybrid_class(
        score_class,
        str(row.get("candidate_pit_surface_state") or ""),
    )
    return {
        **row,
        "candidate_hybrid_ordering_schema_version": CANDIDATE_HYBRID_ORDERING_SCHEMA_VERSION,
        "score_evidence_class": score_class,
        "semantic_hybrid_class": semantic_class,
        "semantic_hybrid_class_priority": priority,
        "semantic_hybrid_class_reason": reason,
        "candidate_score_role": "CO_EQUAL_HYBRID_EVIDENCE",
        "candidate_surface_role": "SEMANTIC_HYBRID_AUTHORITY",
        "weighted_hybrid_score_created": False,
        "candidate_hybrid_ordering_future_information_used": False,
    }


def _candidate_score_evidence_class(row: Mapping[str, Any]) -> str:
    score = _optional_float(row.get("candidate_score"))
    if score is None or score <= 0.0:
        return "WEAK_DISCOVERY_SCORE"
    reason = str(row.get("candidate_reason") or row.get("reason") or "")
    if "high_candidate_score" in {part.strip() for part in reason.split(";") if part.strip()}:
        return "STRONG_DISCOVERY_SCORE"
    if score >= 0.5:
        return "STRONG_DISCOVERY_SCORE"
    return "MODERATE_DISCOVERY_SCORE"


def _candidate_semantic_hybrid_class(score_class: str, surface_state: str) -> tuple[str, int, str]:
    strong_score = score_class == "STRONG_DISCOVERY_SCORE"
    moderate_score = score_class == "MODERATE_DISCOVERY_SCORE"
    strong_surface = surface_state == "STRONG_CONTINUATION_SURFACE"
    valid_surface = surface_state == "VALID_MOMENTUM_SURFACE"
    caution_surface = surface_state == "CAUTION_MOMENTUM_SURFACE"
    insufficient_surface = surface_state == "INSUFFICIENT_SURFACE_EVIDENCE"
    if strong_score and (strong_surface or valid_surface):
        return (
            "CONFIRMED_DISCOVERY_AND_SURFACE",
            1,
            "strong discovery score with strong_or_valid_current_pit_surface",
        )
    if (strong_score and caution_surface) or (moderate_score and strong_surface):
        return (
            "CONFLICT_RESOLUTION_HIGH_DISCOVERY_OR_STRONG_SURFACE",
            2,
            "high discovery caution or moderate discovery strong surface conflict band",
        )
    if (moderate_score and valid_surface) or (strong_score and insufficient_surface):
        return (
            "VALID_BUT_INCOMPLETE_CONFIRMATION",
            3,
            "valid surface with moderate score or strong score with insufficient surface",
        )
    if (moderate_score and caution_surface) or (
        score_class == "WEAK_DISCOVERY_SCORE" and (strong_surface or valid_surface)
    ):
        return (
            "LOW_CONVICTION_OR_SURFACE_ONLY_CHALLENGER",
            4,
            "moderate caution or weak discovery with supportive surface",
        )
    return (
        "INSUFFICIENT_OR_WEAK",
        5,
        "weak discovery or insufficient current PIT confirmation",
    )


def _with_candidate_pit_quality_surface(row: dict[str, Any]) -> dict[str, Any]:
    surface = _candidate_pit_quality_surface(row)
    return {
        **row,
        "candidate_pit_quality_surface": {
            key: value
            for key, value in surface.items()
            if key not in {"priority"}
        },
        "candidate_pit_surface_schema_version": CANDIDATE_PIT_QUALITY_SURFACE_SCHEMA_VERSION,
        "candidate_pit_surface_state": surface["surface_state"],
        "surface_state": surface["surface_state"],
        "candidate_pit_surface_priority": surface["priority"],
        "candidate_pit_surface_reason_codes": surface["reason_codes"],
        "candidate_pit_surface_evidence_sufficiency": surface["evidence_sufficiency"],
        "candidate_pit_market_healthy_proxy": surface["market_healthy_proxy"],
        "candidate_pit_surface_not_buy_authority": True,
        "candidate_pit_surface_future_information_used": False,
    }


def _candidate_pit_quality_surface(row: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "price_momentum_return_5d",
        "price_momentum_return_20d",
        "price_momentum_return_60d",
        "trend_close_over_ma_20d",
        "trend_ma_5_20_ratio",
        "trend_ma_20_60_ratio",
        "momentum_5d_vs_20d_delta",
        "volume_momentum_ratio_5d",
        "volatility_return_std_20d",
        "liquidity_avg_volume_20d",
    )
    raw = {key: _optional_float(row.get(key)) for key in required}
    missing = [key for key, value in raw.items() if value is None]
    if missing:
        return {
            "schema_version": CANDIDATE_PIT_QUALITY_SURFACE_SCHEMA_VERSION,
            "surface_state": "INSUFFICIENT_SURFACE_EVIDENCE",
            "priority": 3,
            "reason_codes": ["candidate_surface_missing_pit_evidence"],
            "evidence_sufficiency": "INSUFFICIENT",
            "missing_inputs": missing,
            "raw_pit_evidence": raw,
            "market_healthy_proxy": False,
            "not_buy_authority": True,
            "future_information_used": False,
        }
    trend_positive = raw["price_momentum_return_5d"] > 0 and raw["price_momentum_return_20d"] > 0
    ma_supportive = raw["trend_close_over_ma_20d"] >= 1.0 and raw["trend_ma_5_20_ratio"] >= 1.0
    long_trend_supportive = raw["price_momentum_return_60d"] >= 0 and raw["trend_ma_20_60_ratio"] >= 1.0
    acceleration_supportive = raw["momentum_5d_vs_20d_delta"] >= 0.0
    acceleration_valid = raw["momentum_5d_vs_20d_delta"] >= -0.02
    participation_supportive = raw["volume_momentum_ratio_5d"] >= 1.0
    volatility_controlled = raw["volatility_return_std_20d"] <= 0.04
    volatility_valid = raw["volatility_return_std_20d"] <= 0.08
    liquidity_valid = raw["liquidity_avg_volume_20d"] > 0
    market_healthy_proxy = bool(trend_positive and ma_supportive and acceleration_valid and liquidity_valid)
    reason_codes: list[str] = []
    if trend_positive:
        reason_codes.append("candidate_surface_positive_5d_20d_momentum")
    if ma_supportive:
        reason_codes.append("candidate_surface_supportive_ma_structure")
    if long_trend_supportive:
        reason_codes.append("candidate_surface_supportive_long_trend")
    if acceleration_supportive:
        reason_codes.append("candidate_surface_supportive_acceleration")
    elif not acceleration_valid:
        reason_codes.append("candidate_surface_deceleration_caution")
    if participation_supportive:
        reason_codes.append("candidate_surface_supportive_participation")
    else:
        reason_codes.append("candidate_surface_weak_participation")
    if volatility_controlled:
        reason_codes.append("candidate_surface_controlled_volatility")
    elif not volatility_valid:
        reason_codes.append("candidate_surface_elevated_volatility")
    if not liquidity_valid:
        reason_codes.append("candidate_surface_invalid_liquidity")
    if trend_positive and ma_supportive and long_trend_supportive and acceleration_supportive and participation_supportive and volatility_controlled and liquidity_valid:
        state = "STRONG_CONTINUATION_SURFACE"
        priority = 0
    elif trend_positive and ma_supportive and acceleration_valid and participation_supportive and volatility_valid and liquidity_valid:
        state = "VALID_MOMENTUM_SURFACE"
        priority = 1
    else:
        state = "CAUTION_MOMENTUM_SURFACE"
        priority = 2
        if not trend_positive:
            reason_codes.append("candidate_surface_trend_not_confirmed")
        if not ma_supportive:
            reason_codes.append("candidate_surface_ma_structure_not_confirmed")
    return {
        "schema_version": CANDIDATE_PIT_QUALITY_SURFACE_SCHEMA_VERSION,
        "surface_state": state,
        "priority": priority,
        "reason_codes": reason_codes,
        "evidence_sufficiency": "SUFFICIENT",
        "missing_inputs": [],
        "raw_pit_evidence": raw,
        "market_healthy_proxy": market_healthy_proxy,
        "not_buy_authority": True,
        "future_information_used": False,
    }


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric):
        return None
    return numeric


def _surface_distribution(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        state = str(row.get("candidate_pit_surface_state") or row.get("surface_state") or "")
        if not state:
            surface = row.get("candidate_pit_quality_surface")
            if isinstance(surface, Mapping):
                state = str(surface.get("surface_state") or "")
        if state:
            counts[state] = counts.get(state, 0) + 1
    return dict(sorted(counts.items()))


def _field_distribution(rows: list[Mapping[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field) or "")
        if value:
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _numeric_distribution(values: Iterable[Any]) -> dict[str, Any]:
    numeric = [_optional_float(value) for value in values]
    clean = [value for value in numeric if value is not None]
    if not clean:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": len(clean),
        "min": round(float(min(clean)), 8),
        "max": round(float(max(clean)), 8),
        "mean": round(float(np.mean(clean)), 8),
    }


def _safe_rate(numerator: int, denominator: int) -> float:
    return round(float(numerator) / float(denominator), 8) if denominator else 0.0


def _listed_info_payload(parent: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any] | None:
    product_category = str(row.get("product_category") or row.get("ProdCat") or "").strip()
    security_type = str(row.get("security_type") or row.get("SecType") or row.get("Type") or product_category).strip()
    market = str(row.get("market") or row.get("MktNm") or row.get("market_name") or "").strip()
    if not product_category and not security_type and not market:
        return None
    code = str(
        row.get("code")
        or row.get("Code")
        or row.get("security_code")
        or row.get("symbol")
        or parent.get("code")
        or parent.get("symbol")
        or ""
    ).strip()
    current_raw = row.get("current_listed", row.get("is_current_listed", True))
    current_listed = str(current_raw).lower() not in {"false", "0", "no", "nan", "none", ""}
    return {
        "code": code,
        "market": market,
        "product_category": product_category,
        "security_type": security_type,
        "current_listed": current_listed,
    }


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
    surface_evidence: dict[str, Any] | None = None,
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
            "score_only_candidate_rank": int(row.get("score_only_candidate_rank") or row.get("candidate_rank") or 0),
            "candidate_score_semantic_role": str(
                row.get("candidate_score_semantic_role") or "momentum_candidate_label_model_score"
            ),
            "candidate_score_role": str(row.get("candidate_score_role") or "CO_EQUAL_HYBRID_EVIDENCE"),
            "score_evidence_class": str(row.get("score_evidence_class") or ""),
            "candidate_rank_semantic_role": "score_only_model_rank_observable_evidence",
            "quality_aware_candidate_rank": int(row.get("quality_aware_candidate_rank") or 0),
            "quality_aware_candidate_rank_semantic_role": "candidate_stage_semantic_hybrid_surface_order",
            "candidate_hybrid_ordering_schema_version": str(
                row.get("candidate_hybrid_ordering_schema_version") or CANDIDATE_HYBRID_ORDERING_SCHEMA_VERSION
            ),
            "semantic_hybrid_class": str(row.get("semantic_hybrid_class") or ""),
            "semantic_hybrid_class_priority": int(row.get("semantic_hybrid_class_priority") or 0),
            "semantic_hybrid_class_reason": str(row.get("semantic_hybrid_class_reason") or ""),
            "candidate_surface_role": str(row.get("candidate_surface_role") or "SEMANTIC_HYBRID_AUTHORITY"),
            "candidate_pit_surface_schema_version": str(
                row.get("candidate_pit_surface_schema_version") or CANDIDATE_PIT_QUALITY_SURFACE_SCHEMA_VERSION
            ),
            "candidate_pit_surface_state": str(row.get("candidate_pit_surface_state") or ""),
            "surface_state": str(row.get("surface_state") or row.get("candidate_pit_surface_state") or ""),
            "candidate_pit_surface_reason_codes": list(row.get("candidate_pit_surface_reason_codes") or []),
            "candidate_pit_surface_evidence_sufficiency": str(
                row.get("candidate_pit_surface_evidence_sufficiency") or ""
            ),
            "candidate_pit_quality_surface": dict(row.get("candidate_pit_quality_surface") or {}),
            "candidate_pit_market_healthy_proxy": bool(row.get("candidate_pit_market_healthy_proxy")),
            "candidate_pit_surface_not_buy_authority": bool(row.get("candidate_pit_surface_not_buy_authority", True)),
            "candidate_pit_surface_future_information_used": bool(
                row.get("candidate_pit_surface_future_information_used", False)
            ),
            **_buy_quality_feature_metadata(row),
            **_candidate_listed_info_metadata(row),
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
        "candidate_pit_quality_surface_evidence": surface_evidence or {},
        "candidate_pit_surface_distribution": dict(
            (surface_evidence or {}).get("top50_surface_distribution") or {}
        ),
        "candidate_coverage_evidence": surface_evidence or {},
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
    model_authority: dict[str, Any] | None = None,
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
        "model_authority": model_authority or {},
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
    lifecycle_gate_evidence: dict[str, Any] | None = None,
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
        lifecycle_gate_evidence=lifecycle_gate_evidence,
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
