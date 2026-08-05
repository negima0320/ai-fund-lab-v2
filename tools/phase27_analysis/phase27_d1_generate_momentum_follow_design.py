#!/usr/bin/env python3
"""Generate Phase27-D1 architecture design artifacts.

This script writes documentation and machine-readable design outputs only.
It does not read or mutate runtime state, execute historical tests, or change
Strategy/Runtime implementation logic.
"""

from __future__ import annotations

import json
from pathlib import Path


TASK_ID = "Phase27-D1"
PHASE = "Phase27"
RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
OUT_DIR = Path(
    "reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design"
)
ARCH_DOC = Path(
    "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md"
)
PHASE_REPORT = Path(
    "docs/phase_reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design.md"
)


PRIMARY_JUDGMENT = (
    "PHASE27_D1_MOMENTUM_FOLLOW_CANONICAL_DECISION_DESIGN_COMPLETE_WITH_OPEN_GATES"
)
SUPPORTING_JUDGMENTS = {
    "investment_philosophy": "FROZEN",
    "buy_add_architecture_repair": "DESIGN_READY",
    "canonical_position_decision": "DESIGN_READY",
    "momentum_continuation": "FOUNDATION_READY",
    "incremental_investment_eligibility": "REQUIRES_CALIBRATION",
    "implementation_entry": "STEP_GATED",
}


EVIDENCE_SOURCES = [
    "docs/phase_reports/phase27_a1_100bd_evidence_inventory_and_attribution_readiness_audit.md",
    "docs/phase_reports/phase27_a2_100bd_baseline_attribution_and_hypothesis_evidence_extraction.md",
    "docs/phase_reports/phase27_a3_reentry_causality_and_selection_validity_diagnosis.md",
    "docs/phase_reports/phase27_a4_opportunity_quality_and_final_selection_discrimination_diagnosis.md",
    "docs/phase_reports/phase27_a5_higher_ranked_candidate_ineligibility_and_quality_component_diagnosis.md",
    "docs/phase_reports/phase27_a6_incremental_investment_eligibility_and_fallback_selection_diagnosis.md",
    "docs/phase_reports/phase27_a7_existing_position_position_management_decision_authority_audit.md",
    "docs/phase_reports/phase27_a8_add_authority_contract_review.md",
    "docs/phase_reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review.md",
    "docs/phase_reports/phase27_ar1_phase27a_review_pack.md",
    "docs/phase_reports/phase26_k_final_architecture_conformance_responsibility_fulfillment_and_closure_review.md",
    "docs/phase_reports/phase26_l_final_closure_consolidation_and_phase27_execution_handoff.md",
    "docs/phase_reports/phase26_final_summary_and_phase27_handoff.md",
    "docs/phase_reports/phase26_to_phase27_chatgpt_handoff.md",
    "docs/02_architecture/autonomous_ai_operations_architecture.md",
    "docs/02_architecture/strategy_architecture_v1.md",
    "docs/02_architecture/runtime_architecture_v2.md",
    "docs/02_architecture/adaptive_buy_quality_authority.md",
    "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md",
    "docs/01_requirements/phase_roadmap.md",
]


SUMMARY = {
    "phase": PHASE,
    "task_id": TASK_ID,
    "task_type": "Architecture / Strategy Detailed Design; Implementation Planning; Documentation Only",
    "run_id_reference": RUN_ID,
    "implementation_changed": False,
    "runtime_change": False,
    "strategy_logic_change": False,
    "historical_execution": "PROHIBITED_NOT_EXECUTED",
    "primary_judgment": PRIMARY_JUDGMENT,
    "supporting_judgments": SUPPORTING_JUDGMENTS,
    "baseline_reference": {
        "return": "-1.542%",
        "profit_factor": 0.8384827164270419,
        "maximum_drawdown_jpy": -205890,
        "win_rate_percent": 34.78260869565217,
        "average_cash_ratio": "about 50.11%",
        "final_cash_ratio": "about 65.97%",
    },
    "phase27_a_findings_reflected": [
        "No forced BUY count observed.",
        "No fixed slot-fill behavior observed.",
        "No forced cash deployment observed.",
        "No-BUY and cash retention are valid Strategy results.",
        "Clear disregard of stronger executable candidates was not observed.",
        "Re-entry losses were material, but Re-entry alone was not proven as root cause.",
        "Higher-ranked candidate dropout was dominated by existing-holding zero-delta cases.",
        "7 of 25 BUYs were WEAK or RELATIVE_ONLY under incremental eligibility diagnosis.",
        "BUY Quality is allocation eligibility/scaling authority, not explicit BUY-versus-cash authority.",
        "PM emitted ADD/HOLD/REDUCE/EXIT, including 145 ADD decisions.",
        "Executable BUY_ADD was not observed.",
        "Runtime PM ADD did not resolve into canonical Portfolio Construction in the observed run.",
        "Legacy add_consumer/sell_pipeline ADD path remains active.",
        "Canonical BUY_ADD authority and legacy ADD authority are split.",
    ],
    "design_scope": [
        "Momentum Follow / Momentum Rotation investment philosophy",
        "Canonical position lifecycle and action semantics",
        "Canonical Position Decision artifact",
        "BUY_ADD architecture repair design",
        "Momentum continuation and incremental investment eligibility contracts",
        "Production/Demo/Historical common implementation plan",
        "Observability, validation, controlled experiment, and rollback contracts",
    ],
    "open_gates": [
        "Implement BUY_ADD authority repair before performance experiments.",
        "Prove canonical BUY_ADD contract with targeted tests before long historical tests.",
        "Introduce momentum continuation foundation in shadow mode before granting decision authority.",
        "Calibrate incremental investment eligibility via controlled experiments.",
        "User, not Codex, runs 10BD/100BD/1-year/long historical validations.",
    ],
}


INVESTMENT_PHILOSOPHY = {
    "financial_objective": {
        "long_term_annual_return_goal": "+50%",
        "acceptance_scope": "Not an acceptance condition for Phase27 alone, but design choices must point toward this objective.",
    },
    "capital_and_risk": {
        "starting_capital_jpy": 1_000_000,
        "risk_posture": "Aggressive / high-risk capital",
        "does_not_mean": [
            "Safety disabled",
            "Unconditional full investment",
            "Fixed cash ratio",
            "Unlimited concentration",
            "Loss-cut refusal",
            "Architecture integrity compromise",
        ],
    },
    "investment_style": "Momentum Follow / Momentum Rotation",
    "style_contract": [
        "Enter symbols with strong forward-looking opportunity evidence.",
        "Hold while momentum continuation remains valid.",
        "Add only when continuation/strengthening and incremental investment eligibility are sufficient.",
        "Reduce when momentum weakens or exposure should be trimmed.",
        "Exit when momentum or expected edge materially deteriorates.",
        "Rotate capital to materially stronger opportunities within portfolio and safety constraints.",
    ],
    "profit_philosophy": {
        "profit_exists_is_exit_reason": False,
        "valid_exit_reasons": [
            "Momentum continuation failure",
            "Expected opportunity deterioration",
            "Signal reliability deterioration",
            "Materially stronger replacement at portfolio level",
            "Risk deterioration",
            "Safety requirement",
        ],
    },
    "loss_philosophy": {
        "fast_loss_control": "Required",
        "boundary": "Repeated Exit -> 1BD Re-entry requires explicit explanation and post-hoc whipsaw observability.",
    },
    "cash_philosophy": {
        "cash_role": "Residual result of valid investment decisions",
        "fixed_cash_ratio_target": False,
        "high_cash": "Neither automatically success nor automatically failure.",
    },
}


POSITION_LIFECYCLE = {
    "canonical_lifecycle": [
        "NO_POSITION",
        "BUY_NEW",
        "OPEN_POSITION",
        "HOLD / ADD / REDUCE",
        "EXIT",
        "NO_POSITION",
        "Optional future BUY_NEW as Re-entry",
    ],
    "state_transitions": [
        {
            "from": "NO_POSITION",
            "action": "BUY_NEW",
            "to": "OPEN_POSITION",
            "campaign_effect": "Create new position_campaign_id.",
        },
        {
            "from": "OPEN_POSITION",
            "action": "HOLD",
            "to": "OPEN_POSITION",
            "campaign_effect": "Keep campaign open and quantity approximately unchanged.",
        },
        {
            "from": "OPEN_POSITION",
            "action": "ADD",
            "to": "OPEN_POSITION",
            "campaign_effect": "Keep campaign open and increase total desired quantity after sizing/safety approval.",
        },
        {
            "from": "OPEN_POSITION",
            "action": "REDUCE",
            "to": "OPEN_POSITION",
            "campaign_effect": "Keep campaign open and partially reduce quantity.",
        },
        {
            "from": "OPEN_POSITION",
            "action": "EXIT",
            "to": "NO_POSITION",
            "campaign_effect": "Close campaign.",
        },
        {
            "from": "NO_POSITION_AFTER_EXIT",
            "action": "BUY_NEW",
            "to": "OPEN_POSITION",
            "campaign_effect": "Re-entry is represented as a new campaign, not a special action.",
        },
    ],
    "reentry_contract": {
        "is_separate_action": False,
        "definition": "A new BUY_NEW after a prior campaign was fully exited.",
        "preferential_treatment": False,
        "strategy_inputs_prohibited": ["Prior campaign PnL", "Past realized loss", "Future outcome"],
        "execution_identity_required": True,
    },
}


CANONICAL_SCHEMA = {
    "artifact": "canonical_position_decision",
    "granularity": "one row per symbol per business_date for decision-scope symbols",
    "schema_version": "phase27_d1.v1",
    "allowed_actions": ["BUY_NEW", "ADD", "HOLD", "REDUCE", "EXIT", "NO_ACTION"],
    "required_fields": [
        "schema_version",
        "run_id",
        "business_date",
        "accepted_generation",
        "symbol",
        "position_campaign_id",
        "current_position_state",
        "current_quantity",
        "current_notional",
        "current_weight",
        "candidate_id",
        "opportunity_id",
        "opportunity_rank",
        "opportunity_score",
        "quality_decision_id",
        "quality_score",
        "quality_action",
        "momentum_continuation_state",
        "momentum_strength",
        "momentum_change",
        "signal_reliability",
        "market_context",
        "portfolio_fit",
        "incremental_investment_eligibility",
        "position_decision",
        "decision_reason_codes",
        "decision_summary",
        "target_membership",
        "target_weight_candidate",
        "target_notional_candidate",
        "target_quantity_candidate",
        "quantity_delta_candidate",
        "order_required",
        "planned_order_side",
        "planning_intent",
        "safety_status",
        "lineage",
    ],
    "action_definitions": {
        "BUY_NEW": "Open a new campaign in a symbol with no current position when incremental investment is justified and downstream feasibility is positive.",
        "ADD": "Increase an existing open position when momentum/eligibility/portfolio/sizing produce a positive quantity delta.",
        "HOLD": "Active Strategy/PM decision to keep the position open with approximately unchanged quantity.",
        "REDUCE": "Keep the campaign open while reducing quantity.",
        "EXIT": "Close the position campaign.",
        "NO_ACTION": "No executable order result for the symbol/date; not equivalent to HOLD unless linked to an explicit HOLD decision.",
    },
    "explanation_contract": {
        "minimum_reason_fields": [
            "decision_reason_codes",
            "decision_summary",
            "positive_evidence",
            "blocking_evidence",
            "lineage",
        ],
        "example": {
            "position_decision": "HOLD",
            "reason": [
                "Momentum continuation remains positive.",
                "Opportunity remains competitive.",
                "Current exposure is appropriate.",
                "Incremental ADD case is not sufficient.",
                "Exit condition is not met.",
            ],
            "order_required": False,
        },
    },
}


DECISION_AUTHORITY_MATRIX = [
    {
        "decision": "BUY_NEW",
        "producer": "Canonical Position Decision / Portfolio Construction",
        "artifact": "canonical_position_decision + target_portfolio + position_sizing",
        "consumer": "Runtime Planning -> Formal Planning -> Pending -> Approval -> Submit",
        "executable": True,
        "observed_phase27a": "BUY fills observed; no forced BUY observed.",
        "architecture_intent": "Allowed when no current position and positive quantity delta exists after eligibility, portfolio, sizing, and safety.",
        "runtime_behavior": "Existing canonical planning path supports BUY_NEW.",
        "judgment": "DEFINED",
    },
    {
        "decision": "ADD",
        "producer": "PM directional intent plus Canonical Position Decision / Portfolio Construction / Position Sizing",
        "artifact": "PM decision + canonical_position_decision + positive quantity_delta_candidate",
        "consumer": "Runtime Planning BUY_ADD path",
        "executable": True,
        "observed_phase27a": "PM ADD 145; executable BUY_ADD 0; legacy ADD path active.",
        "architecture_intent": "Conditionally executable only through canonical downstream quantity/safety chain.",
        "runtime_behavior": "Partial; canonical and legacy authority split remains.",
        "judgment": "REPAIR_REQUIRED_BEFORE_PERFORMANCE_DESIGN",
    },
    {
        "decision": "HOLD",
        "producer": "Position Management AI / Canonical Position Decision",
        "artifact": "PM decision + canonical_position_decision",
        "consumer": "Portfolio Construction and Position Sizing",
        "executable": False,
        "observed_phase27a": "PM HOLD observed; Planning NO_ACTION observed for all existing position rows.",
        "architecture_intent": "Active Strategy decision that maps to zero quantity delta and no order.",
        "runtime_behavior": "Semantics need canonical artifact separation from NO_ACTION.",
        "judgment": "DEFINED_WITH_OBSERVABILITY_GAP",
    },
    {
        "decision": "REDUCE",
        "producer": "PM directional intent plus Portfolio Construction / Position Sizing",
        "artifact": "canonical_position_decision + target_portfolio + negative partial quantity delta",
        "consumer": "Runtime Planning sell intent -> Formal Planning -> Pending -> Approval -> Submit",
        "executable": True,
        "observed_phase27a": "PM REDUCE 34; final REDUCE 22.",
        "architecture_intent": "Allowed for weakening momentum, risk, concentration, or partial rotation.",
        "runtime_behavior": "Sell-side path observed.",
        "judgment": "DEFINED",
    },
    {
        "decision": "EXIT",
        "producer": "PM directional intent plus Portfolio Construction / Safety",
        "artifact": "canonical_position_decision + target membership removal",
        "consumer": "Runtime Planning sell intent -> Formal Planning -> Pending -> Approval -> Submit",
        "executable": True,
        "observed_phase27a": "PM EXIT 23; final EXIT 23.",
        "architecture_intent": "Close campaign for momentum failure, signal invalidation, risk/safety, or stronger replacement.",
        "runtime_behavior": "Sell-side path observed.",
        "judgment": "DEFINED",
    },
    {
        "decision": "NO_ACTION",
        "producer": "Runtime Planning / Strategy Planning result after zero/no executable delta",
        "artifact": "runtime_planning / formal planning no-order evidence",
        "consumer": "Submit as no-order/no-action completion",
        "executable": False,
        "observed_phase27a": "Planning NO_ACTION 364/364 for existing position audit rows.",
        "architecture_intent": "Execution result, not a substitute for Strategy HOLD reasoning.",
        "runtime_behavior": "Observed, but should be linked back to canonical decision and reason.",
        "judgment": "DEFINED_AS_EXECUTION_RESULT",
    },
]


BUY_ADD_REPAIR_DESIGN = {
    "problem_statement": "A9 confirmed a Producer -> Consumer authority split: PM ADD exists, canonical BUY_ADD is only partial, and legacy add_consumer/sell_pipeline remains active.",
    "not_performance_design": True,
    "canonical_chain": [
        "PM ADD",
        "Canonical Position Decision",
        "Portfolio Construction",
        "Position Sizing",
        "positive quantity_delta_candidate",
        "Runtime Planning BUY_ADD",
        "Formal Planning",
        "Pending",
        "Approval",
        "Submit",
        "Execution",
    ],
    "minimum_repair_target": [
        "Resolve runtime PM decision artifact into the canonical Portfolio Construction input path.",
        "Materialize a canonical Position Decision row before target portfolio/sizing decisions.",
        "Ensure ADD cannot directly create Pending outside canonical sizing and planning authority.",
        "Ensure BUY_ADD requires current position plus positive quantity_delta_candidate.",
        "Preserve Safety, Approval, Submit Guard, and PIT lineage boundaries.",
    ],
    "performance_semantics": [
        "Momentum continuation or strengthening",
        "Existing position remains valid",
        "Incremental investment eligibility",
        "Portfolio concentration acceptance",
        "Positive target quantity delta",
        "Safety acceptance",
    ],
    "prohibited_shortcuts": [
        "Rank1 automatic ADD",
        "PM ADD automatic BUY",
        "Cash deployment ADD",
        "Direct ADD Pending from legacy consumer",
        "Historical-test-specific ADD behavior",
    ],
}


LEGACY_ADD_DISPOSITION = {
    "legacy_path": "runtime_v2/planning/sell_pipeline.py -> runtime_v2/planning/add_consumer.py -> pm_add_order_plan -> pending",
    "a9_classification": "DEPRECATED_BUT_ACTIVE",
    "recommended_final_disposition": "RETIRE",
    "migration_bridge": "COMPATIBILITY_ADAPTER_NON_DECISION",
    "rationale": [
        "A9 found the legacy path can consume PM ADD and create BUY pending outside the canonical Portfolio Construction / Position Sizing chain.",
        "Keeping a second decision-producing ADD path would preserve theoretical double-authority risk.",
        "A compatibility adapter may remain during migration only to read, validate, and report legacy shape without producing new ADD decisions or quantities.",
    ],
    "double_authority_prevention": [
        "Exactly one ADD producer may be decision-authoritative for a run: canonical_position_decision.",
        "Legacy ADD consumer must not create Pending when canonical BUY_ADD authority is enabled.",
        "A run-level mutual-exclusion marker must identify canonical ADD authority status.",
    ],
    "pending_double_generation_prevention": [
        "Pending composition rejects duplicate symbol/date/source_decision ADD items.",
        "Legacy pm_add_order_plan output is observability-only under compatibility mode.",
        "Canonical BUY_ADD items carry position_decision_id and quantity_delta lineage.",
    ],
    "quantity_double_count_prevention": [
        "Position Sizing owns target_quantity_candidate and quantity_delta_candidate.",
        "Runtime Planning maps quantity_delta_candidate to BUY_ADD planned_quantity.",
        "No downstream consumer recomputes or adds PM-requested quantity.",
    ],
    "mode_parity": "Production, Demo, and Historical use the same disposition, artifact contract, and mutual-exclusion guard.",
    "migration_plan": [
        "Add canonical Position Decision artifact in shadow/contract mode.",
        "Wire PM decisions into Portfolio Construction via canonical artifact path.",
        "Disable legacy ADD decision production behind explicit compatibility read-only mode.",
        "Prove canonical BUY_ADD with targeted fixtures.",
        "Remove legacy ADD decision authority after parity evidence is accepted.",
    ],
    "rollback_plan": [
        "Rollback must restore prior code paths only as architecture rollback, not performance tuning.",
        "Do not run canonical and legacy ADD decision producers simultaneously.",
        "Preserve artifacts that prove which ADD authority was active for each run.",
    ],
}


MOMENTUM_CONTINUATION_CONTRACT = {
    "purpose": "Enable hold-while-momentum-continues and add-on-strength without using post-hoc performance outcomes.",
    "threshold_status": "NOT_FIXED_IN_PHASE27_D1",
    "inputs": [
        "trend_state",
        "trend_strength",
        "trend_slope",
        "relative_strength",
        "price_structure",
        "volume_confirmation",
        "volatility_adjusted_momentum",
        "momentum_persistence",
        "momentum_acceleration",
        "momentum_deterioration",
        "signal_reliability",
        "market_context_alignment",
    ],
    "outputs": [
        "STRONG_CONTINUATION",
        "CONTINUATION",
        "WEAKENING",
        "BROKEN",
        "INSUFFICIENT_EVIDENCE",
    ],
    "pit_source_assessment": {
        "available_or_expected_pit_sources": [
            "J-Quants daily OHLCV and adjustment-aware historical price inputs",
            "J-Quants listed issues and corporate-event fact authority",
            "Accepted Candidate, Opportunity, Market Context, BUY Quality, PM, and Portfolio Policy artifacts",
            "Current position and valuation artifacts for existing exposure context",
        ],
        "missing_or_requires_confirmation": [
            "Intraday/tick/order-book momentum evidence",
            "Complete sector/benchmark relative-strength coverage if not already materialized",
            "Calibrated thresholds for continuation/weakening/broken states",
            "Accepted schema for momentum component provenance and confidence",
        ],
    },
    "prohibited_inputs": [
        "Future information",
        "Post-hoc winner labels",
        "PnL-based Strategy decisions",
        "Backtest outcome feedback",
        "Selected/bought result labels",
    ],
    "initial_mode": "Shadow evaluation before Strategy authority.",
}


INCREMENTAL_ELIGIBILITY_CONTRACT = {
    "purpose": "Determine whether new capital should be committed, separate from relative rank.",
    "applies_to": ["BUY_NEW", "ADD"],
    "question_answered": "Does this symbol deserve additional capital now?",
    "not_answered_by": "Being the best remaining candidate or being Rank1.",
    "inputs": [
        "Absolute Opportunity Strength",
        "Momentum Continuation / Strength",
        "Signal Reliability",
        "Market Context Alignment",
        "Portfolio Fit",
        "Execution Feasibility",
        "Concentration / Existing Exposure",
    ],
    "outputs": [
        "STRONG",
        "SUFFICIENT",
        "LIMITED",
        "INSUFFICIENT",
        "REVIEW_REQUIRED",
    ],
    "quality_separation": {
        "buy_quality": "Allocation eligibility and adjustment authority.",
        "incremental_investment_eligibility": "BUY/ADD versus no incremental capital decision support.",
    },
    "threshold_status": "Controlled Experiment required; no numeric threshold fixed in Phase27-D1.",
    "initial_mode": "Shadow diagnostic before decision authority.",
}


PORTFOLIO_CONSTRUCTION_CONTRACT = {
    "authority": "Target Portfolio Decision Authority",
    "responsibilities": [
        "Daily reevaluate existing positions.",
        "Consume PM ADD/HOLD/REDUCE/EXIT through canonical Position Decision lineage.",
        "Compare existing positions, BUY_NEW candidates, opportunity evidence, market context, policy, current, cash, and pending.",
        "Represent existing-position zero-delta as justified HOLD when evidence supports it.",
        "Represent ADD as target membership retained with target weight increase.",
        "Represent REDUCE as target membership retained with target weight decrease.",
        "Represent EXIT as target membership removal.",
    ],
    "prohibited": [
        "Fixed Top-N revival",
        "Fixed position-count slot filling",
        "Hidden fallback BUY",
        "Broker quantity or lot-rounding authority",
        "Direct Submit authority",
    ],
}


POSITION_SIZING_CONTRACT = {
    "authority": "Notional / Quantity Candidate Authority",
    "must_distinguish": [
        "Total Desired Quantity",
        "Current Quantity",
        "Quantity Delta",
        "Order Quantity",
    ],
    "contract_formulas": {
        "target_notional_candidate": "target_weight_candidate * canonical_capital_base",
        "target_quantity_candidate": "lot-rounded quantity derived from target_notional_candidate and PIT reference_price",
        "quantity_delta_candidate": "target_quantity_candidate - current_quantity",
    },
    "mapping": {
        "no_current_position_positive_delta": "BUY_NEW",
        "current_position_positive_delta": "BUY_ADD",
        "current_position_zero_delta": "NO_ACTION after explicit HOLD/retain decision",
        "current_position_negative_partial_delta": "REDUCE",
        "current_position_full_negative_delta": "EXIT",
    },
    "capital_base": "Current Total Equity canonical capital base",
    "prohibited": [
        "Reinterpreting Opportunity score to choose membership or target weight",
        "Double-applying Quality adjustment",
        "Changing Strategy target weight",
        "Submit authorization",
    ],
}


CASH_NO_BUY_CONTRACT = {
    "cash_role": "Residual result of valid decisions",
    "fixed_cash_ratio_target": False,
    "no_buy_status": "Valid Strategy result when no sufficiently attractive incremental opportunity exists.",
    "required_evidence": [
        "eligible_opportunity_count",
        "strong_incremental_eligibility_count",
        "planned_buy_notional",
        "executed_buy_notional",
        "unallocated_capital",
        "explicit_non_deployment_reasons",
    ],
    "diagnostic_goal": "Detect excessive filters or authority gaps when strong eligible opportunities exist but capital is not deployed.",
}


REENTRY_WHIPSAW_BOUNDARY = {
    "reentry_allowed": True,
    "reentry_action": "BUY_NEW",
    "special_preference": False,
    "required_explanation_evidence": [
        "prior_campaign_exit_date",
        "new_entry_date",
        "business_day_interval",
        "current_opportunity",
        "current_momentum_state",
        "current_quality",
        "current_incremental_eligibility",
        "market_context",
    ],
    "strategy_inputs_prohibited": [
        "Prior campaign realized PnL",
        "Future price path",
        "Post-hoc whipsaw label",
    ],
    "whipsaw_scope": "Post-hoc human review diagnosis; not a direct Strategy input.",
    "future_observability": [
        "Exit state-change evidence",
        "Re-entry state-change evidence",
        "Exit-to-reentry interval",
        "Holding-period path",
        "MFE/MAE/winner giveback",
    ],
}


OBSERVABILITY_REQUIREMENTS = {
    "full_candidate_universe": [
        "daily_candidate_universe",
        "eligibility",
        "candidate_rank",
        "candidate_reason",
        "opportunity_conversion",
        "dropout_stage",
    ],
    "direct_buy_lineage_ids": [
        "pending_item_id",
        "order_plan_item_id",
        "quality_decision_id",
        "position_decision_id",
        "position_campaign_id",
    ],
    "position_management_reasoning": [
        "pm_input_state",
        "momentum_continuation_state",
        "decision_components",
        "ADD/HOLD/REDUCE/EXIT reason_codes",
        "target_state",
    ],
    "exit_holding_diagnostics": [
        "MFE",
        "MAE",
        "Winner Giveback",
        "Peak Unrealized PnL",
        "Exit-to-re-entry interval",
        "Holding-period path",
    ],
    "canonical_position_decision_artifact": {
        "timing": "Morning Formal Strategy Artifact",
        "immutability": True,
        "separate_from_eod_shadow": True,
    },
    "pit_boundary": "Diagnostics may support human review but must not become Strategy input without accepted PIT contract.",
}


IMPLEMENTATION_WORKSTREAMS = [
    {
        "id": "WS1",
        "name": "BUY_ADD Architecture Repair",
        "scope": [
            "Canonical PM artifact resolution",
            "PM -> Portfolio Construction wiring",
            "Legacy add_consumer disposition",
            "Double-authority guard",
            "Mode parity",
        ],
        "performance_logic_change": False,
    },
    {
        "id": "WS2",
        "name": "Canonical Position Decision Artifact",
        "scope": [
            "BUY_NEW/ADD/HOLD/REDUCE/EXIT/NO_ACTION",
            "Reason and lineage",
            "Immutable morning artifact",
        ],
    },
    {
        "id": "WS3",
        "name": "Momentum Continuation Foundation",
        "scope": ["Schema", "Producer", "PIT source", "Observability", "Shadow evaluation first"],
    },
    {
        "id": "WS4",
        "name": "Existing Position Target Portfolio Integration",
        "scope": ["ADD/HOLD/REDUCE/EXIT", "Target weight/membership", "Positive and negative delta"],
    },
    {
        "id": "WS5",
        "name": "Incremental Investment Eligibility",
        "scope": ["Shadow-only diagnostic first", "No immediate decision authority", "Calibration/experiment contract"],
    },
    {
        "id": "WS6",
        "name": "Exit / Holding Observability",
        "scope": ["MFE/MAE", "Giveback", "Exit reason", "Re-entry interaction"],
    },
    {
        "id": "WS7",
        "name": "Controlled Performance Experiments",
        "scope": ["One performance change at a time"],
    },
]


IMPLEMENTATION_SEQUENCE = [
    "Architecture / Contract Repair Design Freeze",
    "BUY_ADD Authority Repair",
    "Targeted Unit / Regression",
    "Canonical BUY_ADD Contract Proof",
    "Position Decision Artifact",
    "Momentum Continuation Shadow Foundation",
    "Existing Position Integration",
    "Exit / Holding Observability",
    "Incremental Eligibility Shadow",
    "Controlled Performance Experiment",
    "User-run Long Historical Test",
    "Baseline Comparison",
    "Adopt / Reject / Rollback",
]


TESTING_VALIDATION_PLAN = {
    "codex_allowed": [
        "py_compile",
        "unit tests",
        "targeted regression",
        "short non-mutating contract validation",
        "short synthetic fixture",
        "schema validation",
        "producer-consumer lineage validation",
    ],
    "user_runs": [
        "fresh-run",
        "resume",
        "10BD",
        "100BD",
        "1-year Historical",
        "long smoke",
    ],
    "phase27_d1_executed": ["JSON schema/load validation for generated reports"],
    "phase27_d1_not_executed": [
        "fresh-run",
        "resume",
        "Historical",
        "10BD",
        "100BD",
        "long regression",
    ],
}


CONTROLLED_EXPERIMENT_CONTRACT = {
    "principle": "One performance change at a time.",
    "required_fields": [
        "Experiment ID",
        "Hypothesis",
        "Evidence",
        "Changed Component",
        "Unchanged Components",
        "Expected Effect",
        "Risk",
        "Success Metrics",
        "Failure Metrics",
        "Rollback Condition",
        "Baseline Run",
        "Test Command",
    ],
    "minimum_metrics": [
        "Return",
        "PF",
        "Maximum Drawdown",
        "Win Rate",
        "Average Winner",
        "Average Loser",
        "Payoff Ratio",
        "Holding Period",
        "Re-entry Count",
        "Winner Giveback",
        "Cash / Exposure",
        "BUY_NEW / ADD / HOLD / REDUCE / EXIT distribution",
    ],
    "success_boundary": "Cash ratio alone is not a success condition.",
    "rollback_required_when": [
        "Authority contract regression",
        "PIT boundary violation",
        "Safety/Submit bypass",
        "Worse risk-adjusted performance under accepted metrics",
        "Unexplained decision distribution shift",
    ],
}


DEGRESSION_PREVENTION_CONTRACT = {
    "must_preserve": [
        "Phase26 Authority",
        "Accepted Generation binding",
        "Temporal Authority",
        "Current / Ledger / Broker Authority",
        "BUY Quality lineage",
        "Morning / EOD Shadow separation",
        "Formal Planning Authority",
        "Submit Guard responsibility",
        "Safety",
    ],
    "prohibited": [
        "Historical-only implementation",
        "Specific symbol exception",
        "Specific date exception",
        "Post-hoc condition fitted to results",
        "Multiple simultaneous performance changes",
        "Submit Guard as Strategy producer",
        "PM as quantity authority",
    ],
    "rollback_contract": [
        "Rollback by component/workstream.",
        "Keep artifact version and active authority marker for each run.",
        "Do not mix canonical and legacy ADD authorities during rollback.",
        "Use targeted contract evidence before restoring long historical execution.",
    ],
}


OPEN_QUESTIONS = {
    "items": [
        {
            "question": "Which momentum continuation components receive decision authority?",
            "resolution_path": "Shadow evidence and controlled calibration.",
        },
        {
            "question": "What is sufficient ADD evidence?",
            "resolution_path": "Controlled experiments after BUY_ADD contract repair.",
        },
        {
            "question": "Where is the HOLD vs ADD boundary?",
            "resolution_path": "Incremental eligibility calibration plus target weight experiments.",
        },
        {
            "question": "Where is the REDUCE vs EXIT boundary?",
            "resolution_path": "Exit/holding diagnostics and controlled exit experiments.",
        },
        {
            "question": "How should absolute opportunity strength be calibrated?",
            "resolution_path": "Shadow incremental eligibility distributions and user-run historical validation.",
        },
        {
            "question": "What threshold separates SUFFICIENT from LIMITED incremental eligibility?",
            "resolution_path": "Controlled Experiment; not fixed in D1.",
        },
        {
            "question": "How should concentration control interact with aggressive capital posture?",
            "resolution_path": "Portfolio construction experiment under Safety hard constraints.",
        },
        {
            "question": "How should market context moderate BUY_NEW/ADD/REDUCE/EXIT?",
            "resolution_path": "PIT market context alignment evidence.",
        },
        {
            "question": "What winner giveback tolerance is acceptable?",
            "resolution_path": "Post-hoc diagnostics first; Strategy authority only after accepted design.",
        },
        {
            "question": "How should repeated Exit -> 1BD BUY_NEW be diagnosed?",
            "resolution_path": "Whipsaw observability, not direct PnL-based Strategy blocking.",
        },
    ],
    "numeric_thresholds_fixed_in_d1": False,
}


TEST_RESULTS = {
    "phase": PHASE,
    "task_id": TASK_ID,
    "implementation_changed": False,
    "runtime_changed": False,
    "strategy_logic_changed": False,
    "historical_execution": "PROHIBITED_NOT_EXECUTED",
    "fresh_run": "NOT_EXECUTED",
    "resume": "NOT_EXECUTED",
    "long_regression": "NOT_EXECUTED",
    "validations": [
        {
            "name": "generated_json_load_validation",
            "status": "PASS",
            "scope": "All required Phase27-D1 JSON artifacts load successfully after generation.",
        }
    ],
}


ARTIFACTS = {
    "summary.json": SUMMARY,
    "investment_philosophy.json": INVESTMENT_PHILOSOPHY,
    "position_lifecycle_contract.json": POSITION_LIFECYCLE,
    "canonical_position_decision_schema.json": CANONICAL_SCHEMA,
    "decision_authority_matrix.json": {
        "rows": DECISION_AUTHORITY_MATRIX,
        "judgment": "Canonical Position Decision unifies explanation; execution still follows downstream sizing/planning/safety authority.",
    },
    "buy_add_repair_design.json": BUY_ADD_REPAIR_DESIGN,
    "legacy_add_disposition.json": LEGACY_ADD_DISPOSITION,
    "momentum_continuation_contract.json": MOMENTUM_CONTINUATION_CONTRACT,
    "incremental_investment_eligibility_contract.json": INCREMENTAL_ELIGIBILITY_CONTRACT,
    "portfolio_construction_contract.json": PORTFOLIO_CONSTRUCTION_CONTRACT,
    "position_sizing_contract.json": POSITION_SIZING_CONTRACT,
    "cash_no_buy_contract.json": CASH_NO_BUY_CONTRACT,
    "reentry_whipsaw_boundary.json": REENTRY_WHIPSAW_BOUNDARY,
    "observability_requirements.json": OBSERVABILITY_REQUIREMENTS,
    "implementation_workstreams.json": {"workstreams": IMPLEMENTATION_WORKSTREAMS},
    "implementation_sequence.json": {"sequence": IMPLEMENTATION_SEQUENCE},
    "testing_validation_plan.json": TESTING_VALIDATION_PLAN,
    "controlled_experiment_contract.json": CONTROLLED_EXPERIMENT_CONTRACT,
    "degression_prevention_contract.json": DEGRESSION_PREVENTION_CONTRACT,
    "open_questions.json": OPEN_QUESTIONS,
    "test_results.json": TEST_RESULTS,
}


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def numbered(items: list[str]) -> str:
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(items, 1))


def matrix_table(rows: list[dict[str, object]]) -> str:
    header = "| Decision | Producer | Consumer | Executable | Judgment |\n|---|---|---|---|---|"
    body = "\n".join(
        f"| {row['decision']} | {row['producer']} | {row['consumer']} | {row['executable']} | {row['judgment']} |"
        for row in rows
    )
    return f"{header}\n{body}"


def render_arch_doc() -> str:
    workstream_lines = [
        f"{w['id']} - {w['name']}: {', '.join(w['scope'])}"
        for w in IMPLEMENTATION_WORKSTREAMS
    ]
    return f"""# Momentum Follow Position Lifecycle and Canonical Decision Architecture

## 1. Status

This document is the Phase27-D1 design source of truth for Momentum Follow / Momentum Rotation position lifecycle and canonical decision architecture.

- Phase: {PHASE}
- Task ID: {TASK_ID}
- Primary judgment: `{PRIMARY_JUDGMENT}`
- Implementation changed: `false`
- Historical execution: `PROHIBITED_NOT_EXECUTED`

The design is complete enough to guide implementation, but entry is step-gated: BUY_ADD authority repair and targeted contract proof must happen before performance experiments or long historical validation.

## 2. Evidence Base

This design reflects Phase27-A1 through A9, Phase27-AR1, Phase26 closure, and the architecture SoT documents listed below.

{bullet(EVIDENCE_SOURCES)}

Key facts carried forward:

{bullet(SUMMARY['phase27_a_findings_reflected'])}

## 3. Investment Philosophy

AI Fund Lab v2 is designed for Momentum Follow / Momentum Rotation with a long-term annual return goal of +50%. The starting capital assumption is 1,000,000 JPY and the posture is aggressive/high-risk, but this does not disable Safety, force full deployment, introduce a fixed cash ratio, permit unlimited concentration, reject loss cuts, or weaken architecture integrity.

The lifecycle philosophy is:

{bullet(INVESTMENT_PHILOSOPHY['style_contract'])}

Profit alone is not an EXIT reason. EXIT must be justified by momentum failure, opportunity deterioration, signal reliability deterioration, materially stronger replacement, risk deterioration, or Safety. Fast loss control remains required; repeated Exit -> 1BD BUY_NEW must be explainable through evidence and diagnosed as possible whipsaw after the fact.

Cash is residual. High cash is neither automatically success nor automatically failure.

## 4. Canonical Position Lifecycle

```text
NO_POSITION
  -> BUY_NEW
  -> OPEN_POSITION
  -> HOLD / ADD / REDUCE
  -> EXIT
  -> NO_POSITION
  -> Optional future BUY_NEW as Re-entry
```

Re-entry is not a separate Strategy action. It is a new BUY_NEW after a prior campaign has fully exited. It must not receive preferential treatment, and prior campaign PnL must not become a Strategy input. Execution and campaign identity still need to record the prior exit and new campaign boundary.

## 5. Canonical Position Decision

For each decision-scope symbol and business date, the system should materialize one canonical position decision row. Allowed actions are:

```text
BUY_NEW
ADD
HOLD
REDUCE
EXIT
NO_ACTION
```

Required fields:

{bullet(CANONICAL_SCHEMA['required_fields'])}

Action semantics:

{bullet([f'{k}: {v}' for k, v in CANONICAL_SCHEMA['action_definitions'].items()])}

HOLD is an active Strategy/PM decision. NO_ACTION is the downstream no-order result. They must remain separate in artifacts even when HOLD maps to zero quantity delta and Runtime Planning NO_ACTION.

## 6. Decision Authority Matrix

{matrix_table(DECISION_AUTHORITY_MATRIX)}

Responsibility separation is mandatory:

- PM owns existing-position directional intent.
- Portfolio Construction owns target membership and target weight.
- Position Sizing owns target notional, target quantity, and quantity delta.
- Runtime Planning maps quantity deltas to BUY_NEW, BUY_ADD, NO_ACTION, REDUCE, or EXIT execution intent.
- Safety remains independent.
- Pending, Approval, and Submit own order authorization and broker boundary.

## 7. BUY_NEW

BUY_NEW opens a new campaign in a symbol with no current position. It requires candidate eligibility, sufficient opportunity, BUY Quality eligibility, sufficient incremental investment eligibility, acceptable portfolio fit, and capital/safety feasibility. Relative rank alone is not sufficient: best remaining candidate does not automatically mean BUY_NEW.

No numeric score threshold or weight is fixed by this design.

## 8. HOLD

HOLD means the current position should remain open, current quantity should remain approximately unchanged, momentum continuation remains valid, exit conditions are not met, and ADD evidence is not sufficient.

Formal mapping:

```text
HOLD
-> target position remains
-> quantity delta = 0
-> Runtime Planning NO_ACTION
```

The HOLD reason must be preserved in the canonical decision artifact.

## 9. ADD and BUY_ADD Repair

PM ADD is directional intent, not an order.

Canonical ADD chain:

```text
PM ADD
-> Canonical Position Decision
-> Portfolio Construction
-> Position Sizing
-> positive quantity delta
-> Runtime Planning BUY_ADD
-> Formal Planning
-> Pending
-> Approval
-> Submit
-> Execution
```

ADD requires momentum continuation or strengthening, existing position validity, incremental investment eligibility, portfolio concentration acceptance, positive target quantity delta, and Safety acceptance. Rank1 alone and PM ADD alone are never automatic ADD.

Legacy ADD disposition:

- Legacy path: `{LEGACY_ADD_DISPOSITION['legacy_path']}`
- A9 classification: `{LEGACY_ADD_DISPOSITION['a9_classification']}`
- Recommended final disposition: `{LEGACY_ADD_DISPOSITION['recommended_final_disposition']}`
- Migration bridge: `{LEGACY_ADD_DISPOSITION['migration_bridge']}`

The legacy path should become a compatibility adapter that cannot produce decisions or quantities during migration, then be retired. The migration must prevent double authority, duplicate Pending generation, and quantity double counting across Production, Demo, and Historical.

## 10. REDUCE

REDUCE keeps the campaign open while shrinking quantity. Valid conceptual reasons include momentum weakening, risk deterioration, concentration adjustment, opportunity deterioration, or partial rotation to a stronger opportunity. REDUCE is not simple profit taking, and Position Sizing owns the partial quantity.

## 11. EXIT

EXIT closes a campaign. Valid conceptual reasons include momentum continuation failure, signal invalidation, material opportunity deterioration, risk or Safety requirement, or portfolio replacement by materially stronger opportunity.

Prohibited EXIT designs include fixed holding-period exit, simple profit-taking exit, symbol-specific exit, and test-period-specific exit. HOLD improvements must not weaken fast loss control.

## 12. Momentum Continuation Contract

Momentum Continuation is a separate PIT-only evaluation contract. Phase27-D1 does not fix thresholds.

Inputs:

{bullet(MOMENTUM_CONTINUATION_CONTRACT['inputs'])}

Outputs:

{bullet(MOMENTUM_CONTINUATION_CONTRACT['outputs'])}

Available or expected PIT sources include J-Quants daily OHLCV, listed issues/corporate-event facts, accepted Candidate/Opportunity/Market Context/BUY Quality/PM/Portfolio Policy artifacts, and Current position/valuation artifacts. Missing or unconfirmed sources include intraday/tick/order-book evidence, complete sector/benchmark relative-strength coverage where not already materialized, calibrated thresholds, and accepted component provenance schema.

## 13. Incremental Investment Eligibility

Incremental Investment Eligibility asks whether a symbol deserves additional capital now. It is separate from relative ranking and separate from BUY Quality.

Inputs:

{bullet(INCREMENTAL_ELIGIBILITY_CONTRACT['inputs'])}

Outputs:

{bullet(INCREMENTAL_ELIGIBILITY_CONTRACT['outputs'])}

BUY Quality remains allocation eligibility and adjustment authority. Incremental Investment Eligibility supports BUY_NEW/ADD versus no incremental capital. Thresholds must be calibrated later through controlled experiments.

## 14. Portfolio Construction

Portfolio Construction generates the target portfolio by integrating BUY_NEW candidates, existing positions, PM intent, Opportunity, BUY Quality, Portfolio Policy, Market Context, Corporate Events, Current, Cash, and Pending.

It must:

{bullet(PORTFOLIO_CONSTRUCTION_CONTRACT['responsibilities'])}

It must not revive fixed Top-N, fixed slot filling, hidden fallback BUY, broker quantity authority, or Submit authority.

## 15. Position Sizing

Position Sizing must distinguish Total Desired Quantity, Current Quantity, Quantity Delta, and Order Quantity.

Contract formulas:

- `target_notional_candidate = target_weight_candidate * canonical_capital_base`
- `target_quantity_candidate = lot-rounded quantity derived from target_notional_candidate and PIT reference_price`
- `quantity_delta_candidate = target_quantity_candidate - current_quantity`

Mapping:

{bullet([f'{k}: {v}' for k, v in POSITION_SIZING_CONTRACT['mapping'].items()])}

Current Total Equity is the canonical capital base. Quality adjustment must not be double-applied.

## 16. Cash and No-BUY

No fixed cash ratio target is introduced. No-BUY remains a valid Strategy result when no sufficiently attractive incremental opportunity exists.

Required non-deployment evidence:

{bullet(CASH_NO_BUY_CONTRACT['required_evidence'])}

## 17. Re-entry and Whipsaw Boundary

Re-entry remains allowed and is processed as normal BUY_NEW. Required explanation evidence:

{bullet(REENTRY_WHIPSAW_BOUNDARY['required_explanation_evidence'])}

Prior realized PnL, future price path, and post-hoc whipsaw labels are prohibited Strategy inputs. Whipsaw is a human-review diagnostic supported by observability.

## 18. Observability

The design requires:

- Full candidate universe and dropout-stage evidence.
- Direct BUY lineage IDs through fills.
- PM reasoning and decision components.
- Exit/holding diagnostics such as MFE, MAE, winner giveback, peak unrealized PnL, exit-to-re-entry interval, and holding-period path.
- Immutable morning canonical Position Decision artifact, separate from EOD shadow.

## 19. Safety and Architecture Boundaries

Safety is not Strategy. Submit Guard is not Strategy. PM Intent is not Quantity Authority. Runtime Planning is not Ranking Authority. Historical Result is not Strategy Input.

ADD repair must not bypass Safety, Approval, Submit Guard, temporal authority, accepted generation, Current/Ledger/Broker authority, BUY Quality lineage, or Morning/EOD shadow separation.

## 20. Implementation Workstreams

{bullet(workstream_lines)}

## 21. Required Sequence

{numbered(IMPLEMENTATION_SEQUENCE)}

ADD conditions, Exit conditions, Momentum thresholds, Quality weights, Position Sizing policy, and cash behavior must not be changed during BUY_ADD architecture repair.

## 22. Validation Plan

Codex may run short and targeted validations only:

{bullet(TESTING_VALIDATION_PLAN['codex_allowed'])}

User-owned long validations:

{bullet(TESTING_VALIDATION_PLAN['user_runs'])}

## 23. Controlled Experiments

Performance changes must happen one at a time. Each experiment must include:

{bullet(CONTROLLED_EXPERIMENT_CONTRACT['required_fields'])}

Minimum metrics:

{bullet(CONTROLLED_EXPERIMENT_CONTRACT['minimum_metrics'])}

Cash ratio alone is not a success condition.

## 24. Degression Prevention

Must preserve:

{bullet(DEGRESSION_PREVENTION_CONTRACT['must_preserve'])}

Prohibited:

{bullet(DEGRESSION_PREVENTION_CONTRACT['prohibited'])}

## 25. Open Questions

No numeric thresholds are fixed in Phase27-D1. Open items are:

{bullet([item['question'] for item in OPEN_QUESTIONS['items']])}
"""


def render_phase_report() -> str:
    return f"""# Phase27-D1 Momentum Follow Position Lifecycle and Canonical Decision Architecture Design

## 1. Scope

Phase27-D1 produced the formal design SoT for Momentum Follow / Momentum Rotation position lifecycle and canonical decision architecture.

This was documentation-only work.

```text
Implementation Change: false
Runtime Change: false
Strategy Logic Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY_JUDGMENT}
```

The design is complete, but implementation entry is step-gated because BUY_ADD architecture repair must be proven before performance logic, momentum thresholds, or incremental eligibility thresholds are changed.

## 3. Supporting Judgments

```json
{json.dumps(SUPPORTING_JUDGMENTS, ensure_ascii=False, indent=2)}
```

## 4. Evidence Reflected

{bullet(SUMMARY['phase27_a_findings_reflected'])}

## 5. Design Decisions

- Investment style is frozen as Momentum Follow / Momentum Rotation.
- Long-term annual return target is +50%, with aggressive/high-risk capital posture for 1,000,000 JPY starting capital.
- Profit alone is not an EXIT reason.
- Fast loss control remains required.
- Cash is residual and no fixed cash ratio target is introduced.
- BUY_NEW, ADD, HOLD, REDUCE, EXIT, and NO_ACTION are formalized.
- HOLD is active Strategy/PM intent; NO_ACTION is execution result.
- PM ADD is not a BUY order.
- BUY_ADD must pass PM -> Canonical Position Decision -> Portfolio Construction -> Position Sizing -> Runtime Planning -> Formal Planning -> Pending -> Approval -> Submit.
- Legacy add_consumer/sell_pipeline ADD is recommended for retirement, with a compatibility non-decision bridge during migration.
- Incremental Investment Eligibility is separated from BUY Quality and relative ranking.
- Momentum Continuation is introduced as PIT-only foundation, initially shadow.
- Production, Demo, and Historical must share the same implementation contract.

## 6. Deliverables

Main design document:

```text
{ARCH_DOC}
```

Machine-readable outputs:

{bullet(str(OUT_DIR / name) for name in ARTIFACTS)}

## 7. Open Gates

{bullet(SUMMARY['open_gates'])}

## 8. Validation

Only documentation generation and JSON load validation are in scope for this task. Fresh-run, resume, Historical, 10BD, 100BD, and long regression were not executed.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in ARTIFACTS.items():
        write_json(OUT_DIR / name, data)
    ARCH_DOC.parent.mkdir(parents=True, exist_ok=True)
    ARCH_DOC.write_text(render_arch_doc())
    PHASE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PHASE_REPORT.write_text(render_phase_report())


if __name__ == "__main__":
    main()
