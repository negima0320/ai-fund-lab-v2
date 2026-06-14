"""Opportunity AI utilities."""

from ai_fund_lab_v2.opportunity_ai.dataset_builder import (
    LABEL_COLUMNS,
    READY_FOR_OPPORTUNITY_TRAINING,
    build_opportunity_dataset,
    build_opportunity_dataset_frame,
)
from ai_fund_lab_v2.opportunity_ai.combined_validation import (
    READY_FOR_PHASE5I_FULL_HISTORY_EXPANSION,
    validate_candidate_opportunity_combined,
)
from ai_fund_lab_v2.opportunity_ai.completion_audit import (
    PHASE5_COMPLETE_WITH_PROMOTION_DISABLED,
    audit_phase5_completion,
)
from ai_fund_lab_v2.opportunity_ai.design_compliance import (
    PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS,
    run_design_compliance_review,
)
from ai_fund_lab_v2.opportunity_ai.historical_candidates import (
    READY_FOR_PHASE5D_DATASET,
    build_historical_candidate_top50,
    build_historical_candidate_top50_frame,
)
from ai_fund_lab_v2.opportunity_ai.full_history_expansion import (
    READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION,
    run_full_history_expansion,
)
from ai_fund_lab_v2.opportunity_ai.inference import (
    READY_FOR_PHASE5G_QUALITY_AUDIT,
    run_opportunity_inference,
)
from ai_fund_lab_v2.opportunity_ai.model_calibration import (
    READY_FOR_PHASE5K_POLICY_FINALIZATION,
    run_model_improvement_calibration,
)
from ai_fund_lab_v2.opportunity_ai.market_sector_completion import run_market_sector_feature_completion
from ai_fund_lab_v2.opportunity_ai.market_sector_split_impact import run_market_sector_split_impact_audit
from ai_fund_lab_v2.opportunity_ai.policy_finalization import (
    READY_FOR_PHASE5L_COMPLETION_AUDIT,
    finalize_opportunity_policy,
)
from ai_fund_lab_v2.opportunity_ai.quality_audit import (
    READY_FOR_PHASE5H_COMBINED_VALIDATION,
    audit_opportunity_quality,
)
from ai_fund_lab_v2.opportunity_ai.random_date_outcome_check import run_random_date_outcome_check
from ai_fund_lab_v2.opportunity_ai.ranking_quality_audit import run_opportunity_ranking_quality_audit
from ai_fund_lab_v2.opportunity_ai.expanded_random_outcome_check import run_expanded_random_date_outcome_check
from ai_fund_lab_v2.opportunity_ai.training import (
    READY_FOR_PHASE5F_INFERENCE,
    TRAINING_COMPLETE_WITH_WARNINGS,
    train_opportunity_model,
)

__all__ = [
    "LABEL_COLUMNS",
    "READY_FOR_PHASE5D_DATASET",
    "READY_FOR_PHASE5F_INFERENCE",
    "READY_FOR_PHASE5G_QUALITY_AUDIT",
    "READY_FOR_PHASE5H_COMBINED_VALIDATION",
    "READY_FOR_PHASE5I_FULL_HISTORY_EXPANSION",
    "READY_FOR_PHASE5J_MODEL_IMPROVEMENT_OR_CALIBRATION",
    "READY_FOR_PHASE5K_POLICY_FINALIZATION",
    "READY_FOR_PHASE5L_COMPLETION_AUDIT",
    "READY_FOR_OPPORTUNITY_TRAINING",
    "TRAINING_COMPLETE_WITH_WARNINGS",
    "PHASE5_COMPLETE_WITH_PROMOTION_DISABLED",
    "PHASE5_DESIGN_COMPLIANT_WITH_KNOWN_GAPS",
    "audit_phase5_completion",
    "audit_opportunity_quality",
    "build_historical_candidate_top50",
    "build_historical_candidate_top50_frame",
    "build_opportunity_dataset",
    "build_opportunity_dataset_frame",
    "finalize_opportunity_policy",
    "run_opportunity_inference",
    "run_full_history_expansion",
    "run_design_compliance_review",
    "run_model_improvement_calibration",
    "run_market_sector_feature_completion",
    "run_market_sector_split_impact_audit",
    "run_random_date_outcome_check",
    "run_opportunity_ranking_quality_audit",
    "run_expanded_random_date_outcome_check",
    "train_opportunity_model",
    "validate_candidate_opportunity_combined",
]
