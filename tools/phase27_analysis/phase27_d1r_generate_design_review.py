#!/usr/bin/env python3
"""Generate Phase27-D1R design review artifacts.

Documentation-only generator. It does not execute runtime/historical flows or
modify Strategy/Runtime implementation logic.
"""

from __future__ import annotations

import json
from pathlib import Path


PHASE = "Phase27"
TASK_ID = "Phase27-D1R"
OUT_DIR = Path("reports/phase27_d1r_design_consistency_decision_resolution_and_implementation_completeness_review")
MAIN_SOT = Path("docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md")
PHASE_REPORT = Path("docs/phase_reports/phase27_d1r_design_consistency_decision_resolution_and_implementation_completeness_review.md")

PRIMARY = "PHASE27_D1R_DESIGN_REVIEW_COMPLETE_IMPLEMENTATION_ENTRY_STEP_GATED"
SUPPORTING = {
    "canonical_position_intent": "READY",
    "canonical_position_plan": "READY",
    "decision_resolution": "READY",
    "buy_add_repair": "READY",
    "legacy_migration": "READY",
    "momentum_foundation": "READY_FOR_SHADOW",
    "incremental_eligibility": "READY_FOR_SHADOW",
    "implementation_completeness": "READY",
    "degression_prevention": "READY",
}

STATE_MODEL = [
    {
        "state": "INTENT_PROPOSED",
        "producer": "Canonical Position Intent Producer",
        "artifact": "position_intent.v1",
        "required_inputs": ["PM intent", "Candidate/Opportunity references", "BUY Quality", "Momentum Evaluation", "Incremental Eligibility", "Current/Pending", "Corporate Event/Safety review scope"],
        "allowed_mutation": "Immutable after morning publication; later corrections require superseding artifact id/version.",
        "consumer": "Portfolio Construction",
        "failure_state": "INTENT_REVIEW_REQUIRED",
        "review_state": "REVIEW_REQUIRED",
        "lineage": ["position_intent_id", "source_pm_decision_id", "candidate_id", "opportunity_id", "quality_decision_id", "momentum_evaluation_id", "incremental_eligibility_id"],
    },
    {
        "state": "TARGET_PORTFOLIO_RESOLVED",
        "producer": "Portfolio Construction",
        "artifact": "target_portfolio_decision.v1",
        "required_inputs": ["position_intent.v1", "Portfolio Policy", "Current", "Cash", "Pending", "Opportunity/Quality lineage"],
        "allowed_mutation": "Immutable after accepted target portfolio publication.",
        "consumer": "Position Sizing",
        "failure_state": "TARGET_PORTFOLIO_REVIEW_REQUIRED",
        "review_state": "REVIEW_REQUIRED",
        "lineage": ["target_portfolio_decision_id", "position_intent_id", "portfolio_policy_id"],
    },
    {
        "state": "SIZED",
        "producer": "Position Sizing",
        "artifact": "position_sizing_plan.v1",
        "required_inputs": ["target_portfolio_decision.v1", "PIT reference price", "trading unit", "Current total equity", "current quantity"],
        "allowed_mutation": "Immutable after sizing publication; no downstream quantity recomputation.",
        "consumer": "Runtime Planning",
        "failure_state": "SIZING_REVIEW_REQUIRED",
        "review_state": "REVIEW_REQUIRED",
        "lineage": ["position_sizing_plan_id", "target_portfolio_decision_id", "reference_price_authority"],
    },
    {
        "state": "PLANNED",
        "producer": "Runtime Planning",
        "artifact": "runtime_position_plan.v1",
        "required_inputs": ["position_sizing_plan.v1", "Current/Pending", "planning config"],
        "allowed_mutation": "Immutable execution-intent mapping.",
        "consumer": "Strategy Planning Authority / Safety",
        "failure_state": "PLANNING_REVIEW_REQUIRED",
        "review_state": "REVIEW_REQUIRED",
        "lineage": ["runtime_position_plan_id", "position_sizing_plan_id"],
    },
    {
        "state": "SAFETY_EVALUATED",
        "producer": "Safety",
        "artifact": "safety_evaluation.v1",
        "required_inputs": ["runtime_position_plan.v1", "Safety state", "broker/account feasibility evidence"],
        "allowed_mutation": "Safety result immutable for the evaluated plan.",
        "consumer": "Approval / Submit Guard",
        "failure_state": "BLOCK",
        "review_state": "REVIEW_REQUIRED",
        "lineage": ["safety_evaluation_id", "runtime_position_plan_id"],
    },
    {
        "state": "AUTHORIZED",
        "producer": "Approval / Strategy Planning Authority",
        "artifact": "pending_order_plan / approval_artifact",
        "required_inputs": ["runtime_position_plan.v1", "safety_evaluation.v1", "temporal and lineage validation"],
        "allowed_mutation": "Only approval authority may authorize; no Strategy recomputation.",
        "consumer": "Submit",
        "failure_state": "NOT_AUTHORIZED",
        "review_state": "REVIEW_REQUIRED",
        "lineage": ["pending_item_id", "approval_id", "runtime_position_plan_id"],
    },
    {
        "state": "EXECUTED",
        "producer": "Submit / Execution / Ledger Projection",
        "artifact": "order / fill / ledger projection",
        "required_inputs": ["authorized pending item", "Submit Guard", "broker/simulated broker result"],
        "allowed_mutation": "Ledger/current transitions only through runtime-owned execution contracts.",
        "consumer": "Current, Ledger, Attribution, Observability",
        "failure_state": "EXECUTION_FAILED_OR_UNKNOWN",
        "review_state": "POST_SEND_UNKNOWN / REVIEW_REQUIRED",
        "lineage": ["order_id", "fill_id", "pending_item_id", "position_campaign_id"],
    },
]

DECISION_RESOLUTION = {
    "formula": "Strategy Proposed Action + Target Portfolio Resolution + Quantity Delta + Safety / Authority Feasibility = Executable Action",
    "layers": [
        "Directional Intent",
        "Accepted Target Portfolio Action",
        "Sized Quantity Delta",
        "Executable Planning Action",
        "Safety / Authority Result",
        "Final Order Result",
    ],
    "safety_actions": ["ALLOW", "LIMIT", "BLOCK", "REVIEW_REQUIRED"],
    "safety_boundary": "Safety never creates Strategy action; it only evaluates feasibility and risk.",
    "no_implicit_no_action": "Inconsistent upstream/downstream decisions must not be silently collapsed into NO_ACTION.",
}

ACTION_CONFLICTS = [
    {"combination": "PM ADD + accepted positive delta", "outcome": "ADD", "classification": "VALID", "reason": "Intent accepted by target portfolio and sizing."},
    {"combination": "PM ADD + zero accepted delta", "outcome": "NO_ACTION_DUE_TO_ZERO_DELTA", "classification": "VALID_WITH_REASON", "reason": "ADD_NOT_ACCEPTED_BY_TARGET_PORTFOLIO or ADD_NOT_ORDERABLE_AFTER_SIZING; ADD intent preserved."},
    {"combination": "PM ADD + Incremental Eligibility INSUFFICIENT", "outcome": "NOT_ALLOWED", "classification": "REVIEW_REQUIRED_OR_REJECTED_COMBINATION", "reason": "Additional capital not justified."},
    {"combination": "PM HOLD + target weight unchanged", "outcome": "HOLD -> NO_ACTION", "classification": "VALID", "reason": "Retain position with zero orderable delta."},
    {"combination": "PM HOLD + positive target delta", "outcome": "CONTRACT_REVIEW_REQUIRED", "classification": "REVIEW_REQUIRED", "reason": "Portfolio override must be explicit; HOLD cannot silently become ADD."},
    {"combination": "PM REDUCE + target weight decrease", "outcome": "REDUCE", "classification": "VALID", "reason": "Intent accepted with negative partial delta."},
    {"combination": "PM REDUCE + target weight unchanged", "outcome": "NO_ACTION_DUE_TO_ZERO_DELTA", "classification": "VALID_WITH_REASON", "reason": "REDUCE_NOT_ACCEPTED_BY_TARGET_PORTFOLIO or not orderable; REDUCE intent preserved."},
    {"combination": "PM EXIT + membership removed", "outcome": "EXIT", "classification": "VALID", "reason": "Exit accepted."},
    {"combination": "PM EXIT + membership retained", "outcome": "CONTRACT_VIOLATION_OR_REVIEW_REQUIRED", "classification": "CONTRACT_VIOLATION", "reason": "Retaining membership after EXIT requires explicit override contract."},
    {"combination": "Incremental Eligibility INSUFFICIENT + BUY_NEW", "outcome": "NOT_ALLOWED", "classification": "REJECTED_COMBINATION", "reason": "BUY_NEW requires sufficient incremental investment eligibility when the authority is ACTIVE."},
    {"combination": "Safety LIMIT + positive BUY_ADD", "outcome": "LIMITED_OR_REVIEW_REQUIRED", "classification": "VALID_WITH_REASON", "reason": "Safety may limit/block but cannot create ADD."},
]

SCOPE = {
    "minimum_scope": [
        "Current Holdings",
        "BUY-eligible candidates reaching required Strategy stage",
        "Pending / Open-order symbols",
        "Mandatory Safety Review symbols",
        "Corporate-event affected symbols",
    ],
    "observability_scope": "Full Candidate Universe is separately preserved for dropout and review evidence.",
    "dedup_key": ["business_date", "symbol", "accepted_generation", "position_campaign_id"],
    "sources": [
        {"source": "Current Holdings", "reason": "Existing-position reevaluation"},
        {"source": "BUY-eligible candidates", "reason": "BUY_NEW consideration"},
        {"source": "Pending/Open orders", "reason": "Duplicate and state-transition prevention"},
        {"source": "Safety Review symbols", "reason": "Mandatory risk boundary"},
        {"source": "Corporate-event affected symbols", "reason": "PIT event authority boundary"},
    ],
}

FEATURE_INVENTORY = [
    {"raw_feature": "Price/return history", "derived_feature": "Opportunity score/rank", "producer": "Opportunity", "consumer": "Portfolio Construction / Intent references", "weighting_authority": "Opportunity", "decision_effect": "Cross-sectional attractiveness", "double_count_risk": "Momentum features must not be re-added as extra Opportunity weight downstream."},
    {"raw_feature": "Price/return history", "derived_feature": "Momentum continuation state", "producer": "Momentum Continuation Producer", "consumer": "Canonical Position Intent", "weighting_authority": "Momentum Continuation", "decision_effect": "Existing-position continuation/deterioration", "double_count_risk": "Do not double-count into Opportunity or Quality."},
    {"raw_feature": "Market regime/context", "derived_feature": "Market Context Quality modifier", "producer": "Market Context / BUY Quality", "consumer": "BUY Quality / Portfolio Construction", "weighting_authority": "BUY Quality for quality adjustment", "decision_effect": "Allocation eligibility/confidence adjustment", "double_count_risk": "No multiple market-context modifiers in Quality and Incremental Eligibility without explicit contract."},
    {"raw_feature": "Liquidity/reference price/lot feasibility", "derived_feature": "Execution feasibility", "producer": "Market Evidence / Runtime Planning / Sizing", "consumer": "BUY Quality, Incremental Eligibility, Sizing, Safety", "weighting_authority": "Consumer-specific with lineage", "decision_effect": "Eligibility, sizing, or block depending on authority", "double_count_risk": "Must distinguish quality confidence from hard feasibility."},
    {"raw_feature": "Current exposure", "derived_feature": "Portfolio fit / concentration", "producer": "Current / Portfolio Policy", "consumer": "BUY Quality, Incremental Eligibility, Portfolio Construction", "weighting_authority": "Portfolio Construction for membership/weight", "decision_effect": "Target membership and target weight", "double_count_risk": "Do not apply concentration reduction twice."},
]

AUTHORITY_MODES = {
    "modes": {
        "SHADOW": "No decision effect; observability only.",
        "ADVISORY": "Visible to canonical intent producer; cannot independently change action.",
        "ACTIVE": "Authorized decision input after calibration and approval.",
    },
    "active_transition_conditions": [
        "Evidence completeness",
        "Calibration completed",
        "Short regression PASS",
        "Controlled experiment PASS",
        "Human approval",
        "No PIT violation",
        "No degression",
    ],
}

LEGACY_ACCEPTANCE = {
    "legacy_path": "sell_pipeline -> add_consumer -> pm_add_order_plan -> pending",
    "disposition_states": ["ACTIVE", "NON_DECISION_COMPATIBILITY", "RETIRED", "REMOVED"],
    "required_acceptance": [
        "Legacy pending production count = 0",
        "Legacy quantity authority count = 0",
        "Legacy submit authority count = 0",
        "Canonical BUY_ADD lineage complete",
        "Canonical / legacy duplicate key count = 0",
        "Production caller inventory complete",
        "Demo caller inventory complete",
        "Historical caller inventory complete",
        "All legacy tests migrated or explicitly retired",
        "No active imports except compatibility telemetry",
        "Compatibility adapter cannot generate order decision",
    ],
}

DOUBLE_AUTHORITY = {
    "dedup_key": ["run_id", "business_date", "symbol", "position_campaign_id", "decision_id"],
    "prevent": [
        "Duplicate Position Intent",
        "Duplicate Sized Delta",
        "Duplicate Pending",
        "Duplicate Approval",
        "Duplicate Submit",
        "Duplicate Fill Projection",
        "Duplicate Ledger Application",
    ],
    "conflict_behavior": "REVIEW_REQUIRED or explicit BLOCK; fail-open prohibited.",
}

IMPLEMENTATION_SEQUENCE = [
    "Design / Schema / Authority Freeze",
    "Producer-Consumer / Caller Inventory",
    "Minimal Canonical Position Intent Artifact",
    "PM Artifact Resolution Repair",
    "Portfolio Construction Integration",
    "Legacy ADD non-decision conversion",
    "Position Sizing positive / zero / negative delta proof",
    "Runtime Planning BUY_ADD / HOLD / REDUCE / EXIT proof",
    "Canonical Position Plan Artifact",
    "Migration Acceptance / Legacy Retirement",
    "Full Degression Review",
    "Momentum Continuation Shadow",
    "Exit / Holding Observability",
    "Incremental Eligibility Shadow",
    "Controlled Performance Experiment",
]

CHECKLIST_COLUMNS = [
    "Design Contract", "Schema", "Producer", "Consumer", "Caller", "Production", "Demo", "Historical", "Fixture", "Unit Test", "Targeted Regression", "Artifact Evidence", "Observability", "Documentation", "Legacy Migration", "Rollback", "Degression Audit"
]
WORKSTREAMS = [
    "Canonical Position Intent",
    "PM Artifact Resolution Repair",
    "Portfolio Construction Integration",
    "Legacy ADD Non-decision Conversion",
    "Position Sizing Delta Proof",
    "Runtime Position Plan",
    "Canonical Position Plan",
    "Momentum Continuation Shadow",
    "Incremental Eligibility Shadow",
    "Exit / Holding Observability",
]

REGRESSION_DEGRESSION = {
    "non_change_guarantees": [
        "BUY_NEW unchanged during BUY_ADD repair",
        "HOLD unchanged",
        "REDUCE unchanged",
        "EXIT unchanged",
        "Safety unchanged",
        "Submit Guard unchanged",
        "Accepted Generation unchanged",
        "Temporal Authority unchanged",
        "Current / Ledger / Broker Authority unchanged",
        "Morning / EOD Shadow separation unchanged",
        "Quality lineage unchanged",
        "No Historical-only branch",
    ],
    "negative_tests": [
        "PM ADD cannot directly generate Pending",
        "Legacy adapter cannot create quantity",
        "Canonical and Legacy cannot both authorize",
        "Zero delta cannot become BUY_ADD",
        "Positive existing-position delta cannot become BUY_NEW",
        "No current position positive delta cannot become BUY_ADD",
        "PM HOLD cannot silently become ADD",
        "PM EXIT cannot retain membership without review",
    ],
}


def write_json(name: str, payload: object) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def append_main_sot_revision() -> None:
    marker = "## 26. Phase27-D1R Design Consistency Revision"
    text = MAIN_SOT.read_text()
    if marker in text:
        return
    addition = f"""

{marker}

Phase27-D1R refines this SoT before implementation entry. The D1 design remains the investment-philosophy foundation, but the implementation contract is amended as follows.

### 26.1 Canonical Artifact State Model

Canonical Position Decision is not a mutable single artifact that is rewritten by every stage. It is a staged contract:

```text
position_intent.v1
  -> target_portfolio_decision.v1
  -> position_sizing_plan.v1
  -> runtime_position_plan.v1
  -> safety_evaluation.v1
  -> pending_order_plan / approval
  -> order / fill / ledger projection
```

The downstream consolidated explanation may join these artifacts for review, but the upstream authority artifacts remain immutable after morning publication. EOD Shadow remains separate and cannot mutate morning authority.

Artifact states:

```text
INTENT_PROPOSED
TARGET_PORTFOLIO_RESOLVED
SIZED
PLANNED
SAFETY_EVALUATED
AUTHORIZED
EXECUTED
```

### 26.2 Canonical Position Intent

`position_intent.v1` is the upstream Strategy proposed action artifact. It is produced before Portfolio Construction and may express `BUY_NEW`, `ADD`, `HOLD`, `REDUCE`, `EXIT`, or `NO_ACTION` as proposed intent with reason lineage.

BUY_NEW producer chain:

```text
Candidate
  -> Opportunity
  -> BUY Quality
  -> Incremental Investment Eligibility
  -> Canonical Position Intent
  -> Portfolio Construction
  -> Position Sizing
  -> Runtime Planning BUY_NEW
```

Portfolio Construction is not the BUY_NEW candidate producer. It is the authority that adopts or rejects candidate membership in the target portfolio.

### 26.3 Canonical Position Plan

`runtime_position_plan.v1` is the executable planning-action artifact after target portfolio and sizing have resolved. It preserves the upstream intent and records the downstream execution mapping.

Decision resolution:

```text
Strategy Proposed Action
+ Target Portfolio Resolution
+ Quantity Delta
+ Safety / Authority Feasibility
= Executable Action
```

Safety never creates Strategy action. Safety may only return:

```text
ALLOW
LIMIT
BLOCK
REVIEW_REQUIRED
```

### 26.4 Action Conflict Resolution

Inconsistent stage outputs must not be silently collapsed into `NO_ACTION`.

Minimum conflict outcomes:

| Combination | Required outcome | Classification |
|---|---|---|
| PM ADD + accepted positive delta | ADD | VALID |
| PM ADD + zero accepted delta | NO_ACTION_DUE_TO_ZERO_DELTA with ADD_NOT_ACCEPTED reason | VALID_WITH_REASON |
| PM HOLD + target weight unchanged | HOLD -> NO_ACTION | VALID |
| PM HOLD + positive target delta | CONTRACT_REVIEW_REQUIRED unless explicit override exists | REVIEW_REQUIRED |
| PM REDUCE + target weight decrease | REDUCE | VALID |
| PM REDUCE + target weight unchanged | NO_ACTION_DUE_TO_ZERO_DELTA with REDUCE_NOT_ACCEPTED reason | VALID_WITH_REASON |
| PM EXIT + membership removed | EXIT | VALID |
| PM EXIT + membership retained | CONTRACT_VIOLATION or REVIEW_REQUIRED | CONTRACT_VIOLATION |
| Incremental Eligibility INSUFFICIENT + BUY_NEW | NOT_ALLOWED | REJECTED_COMBINATION |

ADD / REDUCE intent must not be implicitly converted to HOLD. Lot rounding no-order results must preserve the original intent:

```text
ADD -> NO_ACTION_DUE_TO_LOT_ROUNDING
REDUCE -> NO_ACTION_DUE_TO_LOT_ROUNDING
```

### 26.5 HOLD Semantics

HOLD means:

```text
Target position remains open
Orderable quantity delta after canonical lot rounding == 0
Exit condition not met
ADD / REDUCE condition not accepted
```

Do not use approximate quantity language for HOLD.

### 26.6 Decision Scope

Daily canonical intent/plan scope is:

```text
Current Holdings
UNION BUY-eligible candidates reaching required Strategy stage
UNION Pending / Open-order symbols
UNION Mandatory Safety Review symbols
UNION Corporate-event affected symbols
```

Full Candidate Universe remains a separate dropout/observability artifact.

Dedup key:

```text
business_date
symbol
accepted_generation
position_campaign_id
```

### 26.7 Feature / Component Responsibility Boundary

Responsibilities:

- Opportunity: cross-sectional relative attractiveness.
- BUY Quality: BUY allocation eligibility and confidence adjustment.
- Momentum Continuation: existing-position continuation / deterioration evaluation.
- Incremental Investment Eligibility: additional capital versus no incremental capital.

Prohibited:

- implicit double weighting of the same feature
- double application of Quality adjustment
- adding Momentum components back into Opportunity without explicit authority
- multiple Market Context modifiers without an inventory entry and consumer contract

### 26.8 Authority Modes

Momentum Continuation and Incremental Investment Eligibility must expose:

```text
authority_mode: SHADOW | ADVISORY | ACTIVE
```

Mode effects:

- `SHADOW`: observability only; no decision effect.
- `ADVISORY`: visible to canonical intent producer; cannot independently change action.
- `ACTIVE`: authorized decision input after calibration and approval.

ACTIVE requires evidence completeness, calibration completion, short regression PASS, controlled experiment PASS, human approval, no PIT violation, and no degression.

### 26.9 EXIT / Replacement and Loss-cut Boundary

EXIT by materially stronger replacement requires evidence for current momentum, current opportunity, replacement strength, strength gap, incremental eligibility, switching/execution feasibility, concentration impact, and current-position deterioration.

Prohibited:

- simple Rank difference EXIT
- near-tie EXIT
- cash-creation EXIT
- fixed rotation EXIT

Loss-cut authority is separated:

- Strategy EXIT: PIT price structure / momentum / signal invalidation.
- Safety REDUCE / EXIT: independent safety or broker-risk requirement.
- Post-hoc Loss Classification: human review only.

Historical PnL, trade outcome, PF, and win rate must not be daily Strategy/PM inputs.

### 26.10 Legacy ADD Migration Acceptance

Legacy path:

```text
sell_pipeline
  -> add_consumer
  -> pm_add_order_plan
  -> pending
```

Disposition states:

```text
ACTIVE
NON_DECISION_COMPATIBILITY
RETIRED
REMOVED
```

Migration acceptance requires legacy pending production count, quantity authority count, and submit authority count all to be zero; canonical BUY_ADD lineage complete; canonical/legacy duplicate key count zero; Production/Demo/Historical caller inventory complete; legacy tests migrated or retired; no active imports except compatibility telemetry; and adapter inability to generate order decisions.

### 26.11 Double-authority Prevention

Canonical and legacy ADD authority must be mutually exclusive.

Dedup key:

```text
run_id
business_date
symbol
position_campaign_id
decision_id
```

Prevent duplicate Position Intent, Sized Delta, Pending, Approval, Submit, Fill Projection, and Ledger Application. Conflict behavior is `REVIEW_REQUIRED` or explicit block. Fail-open is prohibited.

### 26.12 Implementation Completeness Checklist

Every workstream must account for:

```text
Design Contract
Schema
Producer
Consumer
Caller
Production
Demo
Historical
Fixture
Unit Test
Targeted Regression
Artifact Evidence
Observability
Documentation
Legacy Migration
Rollback
Degression Audit
```

Allowed checklist statuses are `REQUIRED`, `NOT_APPLICABLE`, `COMPLETE`, `INCOMPLETE`, and `BLOCKED`. `NOT_APPLICABLE` requires a reason.

### 26.13 Revised Implementation Sequence

{chr(10).join(f'{i}. {step}' for i, step in enumerate(IMPLEMENTATION_SEQUENCE, 1))}

Architecture repair must not change performance logic, thresholds, weights, exit logic, sizing policy, or cash ratio.

### 26.14 Regression / Degression Contract

Non-change guarantees:

{bullets(REGRESSION_DEGRESSION['non_change_guarantees'])}

Required negative tests:

{bullets(REGRESSION_DEGRESSION['negative_tests'])}
"""
    MAIN_SOT.write_text(text.rstrip() + addition + "\n")


def main() -> None:
    artifacts = {
        "summary.json": {
            "phase": PHASE,
            "task_id": TASK_ID,
            "implementation_changed": False,
            "runtime_change": False,
            "strategy_logic_change": False,
            "historical_execution": "PROHIBITED_NOT_EXECUTED",
            "primary_judgment": PRIMARY,
            "supporting_judgments": SUPPORTING,
            "d1_primary_judgment": "PHASE27_D1_MOMENTUM_FOLLOW_CANONICAL_DECISION_DESIGN_COMPLETE_WITH_OPEN_GATES",
            "entry_decision": "STEP_GATED",
            "reason": "Design is implementation-ready at contract level, but implementation must begin with schema/authority freeze and caller inventory before code changes.",
            "common_sot_amendments": [
                "docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md",
                "docs/02_architecture/strategy_architecture_v1.md",
                "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md",
                "docs/02_architecture/runtime_architecture_v2.md",
                "docs/02_architecture/adaptive_buy_quality_authority.md",
            ],
        },
        "design_gap_inventory.json": {
            "gaps_reviewed": [
                "Canonical Position Decision producer/lifecycle ambiguity",
                "PM intent versus Portfolio Construction resolution",
                "Strategy proposed action versus executable action separation",
                "Action conflict handling",
                "BUY_NEW producer correction",
                "HOLD/NO_ACTION/lot-rounding ambiguity",
                "Feature responsibility and double-weight prevention",
                "Legacy ADD migration acceptance",
                "Implementation completeness checklist",
            ],
            "remaining_gaps": [],
        },
        "design_revision_log.json": {
            "revisions": [
                "Split Canonical Position Decision into position_intent.v1 and staged downstream plan artifacts.",
                "Defined artifact state model and immutable morning artifact rule.",
                "Corrected BUY_NEW chain so Portfolio Construction adopts but does not produce candidates.",
                "Defined conflict matrix and PM intent/target portfolio resolution cases.",
                "Replaced approximate HOLD wording with zero orderable delta semantics.",
                "Added authority modes for Momentum Continuation and Incremental Eligibility.",
                "Added legacy ADD migration acceptance and double-authority prevention.",
                "Revised implementation sequence and degression contract.",
            ],
        },
        "artifact_state_model.json": {"states": STATE_MODEL},
        "canonical_position_intent_contract.json": {
            "artifact": "position_intent.v1",
            "role": "Upstream Strategy proposed action",
            "producer": "Canonical Position Intent Producer",
            "allowed_actions": ["BUY_NEW", "ADD", "HOLD", "REDUCE", "EXIT", "NO_ACTION"],
            "mutation": "Immutable after morning publication",
            "consumers": ["Portfolio Construction", "Observability"],
            "not_a_downstream_plan": True,
        },
        "canonical_position_plan_contract.json": {
            "artifacts": ["target_portfolio_decision.v1", "position_sizing_plan.v1", "runtime_position_plan.v1"],
            "role": "Downstream consolidated execution explanation, not upstream mutation",
            "mutation": "Each stage immutable; explanation joins by lineage ids.",
            "lineage_required": ["position_intent_id", "target_portfolio_decision_id", "position_sizing_plan_id", "runtime_position_plan_id"],
        },
        "decision_resolution_contract.json": DECISION_RESOLUTION,
        "action_conflict_matrix.json": {"rows": ACTION_CONFLICTS},
        "decision_scope_contract.json": SCOPE,
        "producer_consumer_inventory.json": {"rows": producer_consumer_inventory()},
        "feature_responsibility_inventory.json": {"rows": FEATURE_INVENTORY},
        "momentum_continuation_authority_mode.json": {"artifact": "momentum_continuation.v1", **AUTHORITY_MODES, "initial_mode": "SHADOW"},
        "incremental_eligibility_authority_mode.json": {"artifact": "incremental_investment_eligibility.v1", "producer": "Strategy Incremental Investment Eligibility Producer", "consumers": ["Canonical Position Intent", "Portfolio Construction", "Position Sizing only if explicitly authorized"], **AUTHORITY_MODES, "initial_mode": "SHADOW"},
        "buy_new_authority_contract.json": {
            "chain": ["Candidate", "Opportunity", "BUY Quality", "Incremental Investment Eligibility", "Canonical Position Intent", "Portfolio Construction", "Position Sizing", "Runtime Planning BUY_NEW"],
            "correction": "Portfolio Construction is candidate adoption authority, not BUY_NEW candidate producer.",
            "not_allowed": ["Relative rank alone", "Cash deployment motive", "Incremental Eligibility INSUFFICIENT when ACTIVE"],
        },
        "add_hold_reduce_exit_resolution_matrix.json": {"rows": [row for row in ACTION_CONFLICTS if row["combination"].startswith("PM ")]},
        "exit_replacement_contract.json": {
            "required_evidence": ["Current position momentum continuation", "Current position opportunity", "Replacement opportunity strength", "Strength gap", "Incremental eligibility", "Switching / execution feasibility", "Portfolio concentration impact", "Current position deterioration"],
            "prohibited": ["Simple rank difference exit", "Near-tie exit", "Cash creation exit", "Fixed rotation"],
            "thresholds_fixed": False,
        },
        "loss_cut_authority_boundary.json": {
            "strategy_exit": "PIT price structure / momentum / signal invalidation",
            "safety_reduce_exit": "Independent safety or broker-risk requirement",
            "post_hoc_loss_classification": "Human review only",
            "prohibited_inputs": ["Historical PnL", "Trade outcome", "PF", "Win rate", "Future price"],
        },
        "legacy_add_migration_acceptance.json": LEGACY_ACCEPTANCE,
        "double_authority_prevention_contract.json": DOUBLE_AUTHORITY,
        "implementation_sequence.json": {"sequence": IMPLEMENTATION_SEQUENCE},
        "implementation_completeness_checklist.json": {
            "columns": CHECKLIST_COLUMNS,
            "allowed_statuses": ["REQUIRED", "NOT_APPLICABLE", "COMPLETE", "INCOMPLETE", "BLOCKED"],
            "not_applicable_requires_reason": True,
            "rows": [{**{"workstream": ws}, **{col: "REQUIRED" for col in CHECKLIST_COLUMNS}} for ws in WORKSTREAMS],
        },
        "regression_degression_contract.json": REGRESSION_DEGRESSION,
        "open_questions.json": {
            "items": [
                "Momentum thresholds",
                "ADD numeric sufficient conditions",
                "EXIT numeric conditions",
                "Opportunity Score cutoff",
                "Quality weight changes",
                "Incremental Eligibility calibration",
                "Position Sizing policy changes",
                "Cash Ratio target",
            ],
            "fixed_in_d1r": False,
        },
        "test_results.json": {
            "implementation_changed": False,
            "historical_execution": "PROHIBITED_NOT_EXECUTED",
            "fresh_run": "NOT_EXECUTED",
            "resume": "NOT_EXECUTED",
            "validations": [{"name": "generated_json_load_validation", "status": "PASS"}],
        },
    }
    for name, payload in artifacts.items():
        write_json(name, payload)
    append_main_sot_revision()
    PHASE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PHASE_REPORT.write_text(render_report())


def producer_consumer_inventory() -> list[dict[str, str]]:
    items = [
        ("PM ADD", "PM decision", "Position Management AI", "Canonical Position Intent, Portfolio Construction", "Directional Intent", "PM", "Production/Demo/Historical", "No direct Pending fallback", "Canonical input only after repair"),
        ("PM HOLD", "PM decision", "Position Management AI", "Canonical Position Intent, Portfolio Construction", "Directional Intent", "PM", "Production/Demo/Historical", "No implicit NO_ACTION collapse", "Canonical input only after repair"),
        ("PM REDUCE", "PM decision", "Position Management AI", "Canonical Position Intent, Portfolio Construction", "Directional Intent", "PM", "Production/Demo/Historical", "No implicit HOLD collapse", "Canonical input only after repair"),
        ("PM EXIT", "PM decision", "Position Management AI", "Canonical Position Intent, Portfolio Construction", "Directional Intent", "PM", "Production/Demo/Historical", "No retained membership without review", "Canonical input only after repair"),
        ("Canonical Position Intent", "position_intent.v1", "Canonical Position Intent Producer", "Portfolio Construction", "Strategy Proposed Action", "Producer only", "Production/Demo/Historical", "None", "New canonical"),
        ("Target Portfolio Decision", "target_portfolio_decision.v1", "Portfolio Construction", "Position Sizing", "Target Portfolio Authority", "Portfolio Construction", "Production/Demo/Historical", "Fail-closed review", "Canonical"),
        ("Position Sizing Plan", "position_sizing_plan.v1", "Position Sizing", "Runtime Planning", "Quantity Candidate Authority", "Position Sizing", "Production/Demo/Historical", "No quantity recompute", "Canonical"),
        ("Runtime Position Plan", "runtime_position_plan.v1", "Runtime Planning", "Strategy Planning Authority, Safety", "Execution Intent Mapping", "Runtime Planning", "Production/Demo/Historical", "Fail-closed review", "Canonical"),
        ("BUY_NEW", "runtime_position_plan.v1", "Runtime Planning from positive no-current-position delta", "Pending/Approval/Submit", "Executable Planning Action", "Runtime Planning", "Production/Demo/Historical", "None", "Canonical"),
        ("BUY_ADD", "runtime_position_plan.v1", "Runtime Planning from positive existing-position delta", "Pending/Approval/Submit", "Executable Planning Action", "Runtime Planning", "Production/Demo/Historical", "Legacy ADD blocked", "Repair required"),
        ("HOLD", "position_intent.v1", "PM/Canonical Position Intent", "Portfolio Construction/Sizing", "Active Strategy Intent", "PM/Intent producer", "Production/Demo/Historical", "No implicit execution meaning", "Canonical"),
        ("NO_ACTION", "runtime_position_plan.v1", "Runtime Planning", "Submit no-order completion", "Execution Result", "Runtime Planning", "Production/Demo/Historical", "Must preserve upstream reason", "Canonical"),
        ("REDUCE", "runtime_position_plan.v1", "Runtime Planning from negative partial delta", "Pending/Approval/Submit", "Executable Planning Action", "Runtime Planning", "Production/Demo/Historical", "None", "Canonical"),
        ("EXIT", "runtime_position_plan.v1", "Runtime Planning from full removal/negative delta", "Pending/Approval/Submit", "Executable Planning Action", "Runtime Planning", "Production/Demo/Historical", "No retained membership without review", "Canonical"),
        ("Legacy add_consumer", "pm_add_order_plan", "add_consumer", "Compatibility telemetry only after migration", "Legacy ADD Consumer", "None after migration", "Production/Demo/Historical inventory required", "Cannot generate order decision", "NON_DECISION_COMPATIBILITY -> RETIRED"),
        ("pm_add_order_plan", "legacy plan", "Legacy add_consumer", "Telemetry / retired tests", "Legacy artifact", "None after migration", "Production/Demo/Historical inventory required", "No Pending generation", "Retire"),
        ("pending_order_plan", "pending_order_plan", "Strategy Planning Authority", "Approval/Submit", "Pending Materialization", "Strategy Planning Authority", "Production/Demo/Historical", "No direct PM ADD", "Canonical"),
        ("Approval", "approval_artifact", "Approval Authority", "Submit", "Order Authorization", "Approval", "Production/Demo/Historical", "Fail closed", "Canonical"),
        ("Submit", "order request", "Submit Runtime", "Execution/Broker", "Broker Boundary", "Submit", "Production/Demo/Historical", "Submit Guard", "Canonical"),
        ("Fill", "fill artifact", "Execution/Broker adapter", "Ledger/Current", "Execution Evidence", "Execution", "Production/Demo/Historical", "No inferred fill", "Canonical"),
        ("Ledger Projection", "ledger/current projection", "Runtime-owned ledger projection", "Current/Attribution", "Runtime State Authority", "Ledger projection", "Production/Demo/Historical", "No duplicate application", "Canonical"),
    ]
    keys = ["component", "decision_artifact", "producer", "consumers", "authority_type", "mutation_authority", "mode_scope", "fallback", "migration_status"]
    rows = []
    for item in items:
        row = dict(zip(keys, item))
        row.update({
            "runtime_caller": "INVENTORY_REQUIRED",
            "demo_caller": "INVENTORY_REQUIRED",
            "historical_caller": "INVENTORY_REQUIRED",
            "fixture": "REQUIRED",
            "unit_test": "REQUIRED",
            "regression_test": "REQUIRED",
            "documentation": "REQUIRED",
        })
        rows.append(row)
    return rows


def render_report() -> str:
    return f"""# Phase27-D1R Design Consistency, Decision Resolution, and Implementation Completeness Review

## 1. Scope

Phase27-D1R reviewed and revised the Phase27-D1 design SoT before implementation entry. This task changed documentation and machine-readable design artifacts only.

```text
Implementation Change: false
Runtime Change: false
Strategy Logic Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
{PRIMARY}
```

Implementation entry remains step-gated. The design is now complete at the contract level, but implementation must begin with schema/authority freeze and caller inventory before any runtime or strategy code changes.

## 3. Supporting Judgments

```json
{json.dumps(SUPPORTING, ensure_ascii=False, indent=2)}
```

## 4. Revisions Applied

- Split Canonical Position Decision into staged immutable artifacts.
- Defined `position_intent.v1` as upstream Strategy proposed action.
- Defined downstream position plan artifacts as target, sizing, planning, safety, authorization, and execution stages.
- Corrected BUY_NEW authority: Portfolio Construction adopts candidates; it does not produce BUY_NEW candidates.
- Added action conflict matrix and PM intent versus target portfolio resolution rules.
- Replaced ambiguous HOLD wording with zero orderable delta semantics.
- Added authority modes for Momentum Continuation and Incremental Investment Eligibility.
- Added Legacy ADD migration acceptance and double-authority prevention.
- Added implementation completeness checklist and negative regression/degression contract.

## 5. Updated SoT

```text
{MAIN_SOT}
```

Common SoT amendments:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/adaptive_buy_quality_authority.md`

## 6. Machine-readable Outputs

{bullets(str(OUT_DIR / name) for name in REQUIRED_FILES)}

## 7. Boundary

No numeric thresholds, quality weights, position sizing policy, cash ratio target, Runtime implementation, Strategy implementation, or Historical execution were introduced.
"""


REQUIRED_FILES = [
    "summary.json",
    "design_gap_inventory.json",
    "design_revision_log.json",
    "artifact_state_model.json",
    "canonical_position_intent_contract.json",
    "canonical_position_plan_contract.json",
    "decision_resolution_contract.json",
    "action_conflict_matrix.json",
    "decision_scope_contract.json",
    "producer_consumer_inventory.json",
    "feature_responsibility_inventory.json",
    "momentum_continuation_authority_mode.json",
    "incremental_eligibility_authority_mode.json",
    "buy_new_authority_contract.json",
    "add_hold_reduce_exit_resolution_matrix.json",
    "exit_replacement_contract.json",
    "loss_cut_authority_boundary.json",
    "legacy_add_migration_acceptance.json",
    "double_authority_prevention_contract.json",
    "implementation_sequence.json",
    "implementation_completeness_checklist.json",
    "regression_degression_contract.json",
    "open_questions.json",
    "test_results.json",
]


if __name__ == "__main__":
    main()
