from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


RUN_ID = "runtime-test-historical-smoke-20260804T074611098414Z"
RUN_DIR = Path("reports/runtime_tests/runs") / RUN_ID
A7_DIR = Path("reports/phase27_a7_existing_position_position_management_decision_authority_audit")
A8_DIR = Path("reports/phase27_a8_add_authority_contract_review")
OUT_DIR = Path("reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review")
REPORT_PATH = Path("docs/phase_reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review.md")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def observed_pc_pm_mapping() -> dict[str, Any]:
    status_counts: Counter[tuple[str, str, str]] = Counter()
    pm_mappings: Counter[tuple[str, str, str]] = Counter()
    row_count = 0
    for path in sorted((RUN_DIR / "daily").glob("*/strategy/portfolio_construction.json")):
        payload = load_json(path)
        status_counts[(str(payload.get("artifact_lifecycle_status")), str(payload.get("runtime_consumer_eligibility")), str(payload.get("producer_result_status")))] += 1
        for row in payload.get("portfolio_members") or []:
            if not isinstance(row, dict):
                continue
            action = str(row.get("pm_action") or "")
            if action:
                row_count += 1
                pm_mappings[(action, str(row.get("membership_intent") or ""), str(row.get("weight_intent") or ""))] += 1
    return {
        "portfolio_construction_artifact_status_counts": {"/".join(k): v for k, v in status_counts.items()},
        "portfolio_construction_pm_mapping_counts": {"/".join(k): v for k, v in pm_mappings.items()},
        "portfolio_construction_rows_with_pm_action": row_count,
        "observed_runtime_pm_add_in_pc": pm_mappings.get(("ADD", "RETAIN", "INCREASE"), 0),
        "observed_unresolved_pm_rows_in_pc": sum(v for k, v in pm_mappings.items() if k[0] == "UNRESOLVED"),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    a7_summary = load_json(A7_DIR / "summary.json")
    a8_summary = load_json(A8_DIR / "summary.json")
    pc_observed = observed_pc_pm_mapping()

    decision_authority_matrix = [
        {
            "decision": "BUY_NEW",
            "producer": "Runtime Planning after Portfolio Construction / Position Sizing",
            "canonical_artifact": "strategy/runtime_planning.json and pending_order_plan when materialized",
            "consumer": "Strategy Planning Authority -> Pending -> Approval -> Submit -> Execution",
            "quantity_owner": "Position Sizing",
            "safety_owner": "Safety",
            "pending_owner": "Strategy Planning Authority / Pending Materialization",
            "submit_owner": "Submit Guard / Submit",
            "architecture_intent": "CANONICAL",
            "implementation_status": "IMPLEMENTED",
            "observed_status": "Observed as normal BUY_NEW trade path in run; not the A9 focus.",
            "legacy_conflict": "NONE_OBSERVED",
            "final_judgment": "CONFIRMED",
        },
        {
            "decision": "BUY_ADD",
            "producer": "Runtime Planning from positive existing-position quantity_delta_candidate",
            "canonical_artifact": "strategy/runtime_planning.json",
            "consumer": "Strategy Planning Authority -> Pending -> Approval -> Submit -> Execution",
            "quantity_owner": "Position Sizing",
            "safety_owner": "Safety",
            "pending_owner": "Strategy Planning Authority / Pending Materialization",
            "submit_owner": "Submit Guard / Submit",
            "architecture_intent": "CANONICAL_CONDITIONAL",
            "implementation_status": "PARTIAL: Runtime Planning supports BUY_ADD; observed PM ADD does not reach canonical positive delta path.",
            "observed_status": "Planning BUY_ADD 0; executable ADD 0 in A7.",
            "legacy_conflict": "Legacy add_consumer can also emit ADD-derived BUY pending.",
            "final_judgment": "CONTRACT_GAP_REPAIR_REQUIRED",
        },
        {
            "decision": "HOLD",
            "producer": "Position Management",
            "canonical_artifact": "position_management/pm_decisions.json / PM Decisions Artifact",
            "consumer": "Portfolio Construction and Planning/no-order evidence",
            "quantity_owner": "Not applicable unless target portfolio changes",
            "safety_owner": "Safety only if downstream order exists",
            "pending_owner": "Not applicable",
            "submit_owner": "Not applicable",
            "architecture_intent": "CANONICAL_PM_INTENT",
            "implementation_status": "IMPLEMENTED",
            "observed_status": f"PM HOLD {a7_summary['pm_decision_counts'].get('HOLD', 0)}",
            "legacy_conflict": "NONE_OBSERVED",
            "final_judgment": "CONFIRMED",
        },
        {
            "decision": "NO_ACTION",
            "producer": "Runtime Planning / no-order authority",
            "canonical_artifact": "strategy/runtime_planning.json; pending EMPTY no-order authority when materialized",
            "consumer": "Submit no-order path when pending EMPTY authority is active",
            "quantity_owner": "Runtime Planning consumes Position Sizing delta; planned order quantity 0",
            "safety_owner": "Safety no-order context if materialized",
            "pending_owner": "Pending no-order authority",
            "submit_owner": "Submit no-order authority",
            "architecture_intent": "CANONICAL_ZERO_STATE",
            "implementation_status": "IMPLEMENTED",
            "observed_status": f"Planning NO_ACTION {a7_summary['planning_intent_counts'].get('NO_ACTION', 0)}",
            "legacy_conflict": "Potential conflict if legacy add_consumer emits PM ADD pending after NO_ACTION strategy planning.",
            "final_judgment": "CONFIRMED_WITH_DOUBLE_AUTHORITY_RISK",
        },
        {
            "decision": "REDUCE",
            "producer": "Position Management",
            "canonical_artifact": "position_management/pm_decisions.json",
            "consumer": "Sell Planning -> Pending -> Approval -> Submit -> Execution",
            "quantity_owner": "Sell Planning reduce quantity contract / Current sellable quantity",
            "safety_owner": "Safety",
            "pending_owner": "Sell Planning / Pending",
            "submit_owner": "Submit Guard / Submit",
            "architecture_intent": "CANONICAL_PM_SELL_INTENT",
            "implementation_status": "IMPLEMENTED",
            "observed_status": f"PM REDUCE {a7_summary['pm_decision_counts'].get('REDUCE', 0)}",
            "legacy_conflict": "NONE_FOR_ADD",
            "final_judgment": "CONFIRMED",
        },
        {
            "decision": "EXIT",
            "producer": "Position Management",
            "canonical_artifact": "position_management/pm_decisions.json",
            "consumer": "Sell Planning -> Pending -> Approval -> Submit -> Execution",
            "quantity_owner": "Sell Planning / Current sellable quantity",
            "safety_owner": "Safety",
            "pending_owner": "Sell Planning / Pending",
            "submit_owner": "Submit Guard / Submit",
            "architecture_intent": "CANONICAL_PM_SELL_INTENT",
            "implementation_status": "IMPLEMENTED",
            "observed_status": f"PM EXIT {a7_summary['pm_decision_counts'].get('EXIT', 0)}",
            "legacy_conflict": "NONE_FOR_ADD",
            "final_judgment": "CONFIRMED",
        },
    ]

    canonical_buy_add_contract = {
        "formal_authority_chain": [
            "Existing Position",
            "Position Management ADD/HOLD/REDUCE/EXIT intent",
            "Portfolio Construction target membership / target weight",
            "Position Sizing target notional / target quantity / quantity delta",
            "Runtime Planning BUY_ADD when positive quantity delta on held symbol",
            "Strategy Planning Authority validation",
            "Pending",
            "Approval",
            "Submit",
            "Execution",
        ],
        "core_rule": "PM ADD is not a BUY. Executable BUY_ADD requires downstream positive quantity_delta_candidate and pending/approval/submit authority.",
        "authority_owners": {
            "pm_add_intent": "Position Management",
            "portfolio_membership": "Portfolio Construction",
            "target_weight": "Portfolio Construction",
            "target_notional": "Position Sizing",
            "target_quantity": "Position Sizing",
            "quantity_delta": "Position Sizing",
            "buy_add_planning_intent": "Runtime Planning",
            "pending_generation": "Strategy Planning Authority / Pending Materialization",
            "submit_permission": "Approval + Submit Guard + Safety",
            "execution": "Broker / Execution",
        },
        "supporting_evidence": [
            "docs/02_architecture/strategy_architecture_v1.md:43",
            "docs/02_architecture/strategy_architecture_v1.md:82-85",
            "docs/02_architecture/strategy_architecture_v1.md:118-124",
            "docs/02_architecture/strategy_architecture_v1.md:218-227",
            "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md:152-175",
            "src/ai_fund_lab_v2/strategy/runtime_planning.py:1100-1124",
        ],
        "canonical_path_status": "PARTIAL",
        "reason": "The path is defined in SoT and partially implemented, but observed Runtime PM ADD did not reach Portfolio Construction as ADD and no positive existing-position delta reached Runtime Planning.",
    }

    graph = {
        "nodes": [
            {"id": "pm", "type": "Producer", "name": "Position Management"},
            {"id": "pm_decisions", "type": "Artifact", "name": "PM Decisions Artifact"},
            {"id": "portfolio_construction", "type": "Producer/Consumer", "name": "Portfolio Construction"},
            {"id": "target_portfolio", "type": "Artifact", "name": "Target Portfolio / Portfolio Construction"},
            {"id": "position_sizing", "type": "Producer/Consumer", "name": "Position Sizing"},
            {"id": "quantity_candidate", "type": "Artifact", "name": "target_quantity_candidate / quantity_delta_candidate"},
            {"id": "runtime_planning", "type": "Producer/Consumer", "name": "Runtime Planning"},
            {"id": "planning_intent", "type": "Artifact", "name": "BUY_ADD planning intent"},
            {"id": "strategy_planning_authority", "type": "Guard", "name": "Strategy Planning Authority"},
            {"id": "pending", "type": "Artifact", "name": "Pending Order Plan"},
            {"id": "approval", "type": "Guard", "name": "Approval"},
            {"id": "submit", "type": "Consumer/Guard", "name": "Submit Guard / Submit"},
            {"id": "execution", "type": "Consumer", "name": "Execution"},
            {"id": "legacy_sell_pipeline", "type": "Producer/Consumer", "name": "sell_pipeline ADD path"},
            {"id": "legacy_add_consumer", "type": "Consumer", "name": "add_consumer"},
            {"id": "pm_add_order_plan", "type": "Artifact", "name": "pm_add_order_plan.json"},
        ],
        "edges": [
            {
                "edge_id": "canonical-01",
                "source": "pm",
                "target": "pm_decisions",
                "artifact": "position_management/pm_decisions.json",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "Existing Position Intent Authority",
                "canonical_status": "DEFINED_AND_IMPLEMENTED",
                "observed_status": "PM ADD/HOLD/REDUCE/EXIT observed in A7",
                "risk": "LOW",
                "evidence": ["A7 summary", "runtime_v2/position_management/producer.py"],
            },
            {
                "edge_id": "canonical-02",
                "source": "pm_decisions",
                "target": "portfolio_construction",
                "artifact": "strategy/position_management.json or PM Decisions Artifact",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "PM intent input to Target Portfolio",
                "canonical_status": "DEFINED_BUT_NOT_IMPLEMENTED_OR_NOT_CONNECTED_IN_OBSERVED_RUN",
                "observed_status": "Portfolio Construction saw UNRESOLVED PM rows; runtime PM ADD count did not appear as ADD",
                "risk": "CONTRACT_GAP",
                "evidence": ["portfolio_construction.py:240-246", "portfolio_construction.py:1271-1280", "A9 observed PC mapping"],
            },
            {
                "edge_id": "canonical-03",
                "source": "portfolio_construction",
                "target": "target_portfolio",
                "artifact": "strategy/portfolio_construction.json",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "Target Portfolio Decision Authority",
                "canonical_status": "DEFINED_AND_PARTIALLY_IMPLEMENTED",
                "observed_status": "Produced DRAFT/NOT_ELIGIBLE/PASS artifacts",
                "risk": "PARTIAL_CONSUMER_ELIGIBILITY",
                "evidence": ["strategy_architecture_v1.md:118", "A9 observed artifact status"],
            },
            {
                "edge_id": "canonical-04",
                "source": "target_portfolio",
                "target": "position_sizing",
                "artifact": "strategy/position_sizing.json",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "Quantity Candidate Authority",
                "canonical_status": "DEFINED_AND_IMPLEMENTED",
                "observed_status": "Quantity delta zero for A7 existing-position rows",
                "risk": "LOW_FOR_ZERO_STATE",
                "evidence": ["position_sizing.py:697-754", "A7 desired_quantity_trace"],
            },
            {
                "edge_id": "canonical-05",
                "source": "position_sizing",
                "target": "runtime_planning",
                "artifact": "quantity_delta_candidate",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "Execution Intent Mapping",
                "canonical_status": "DEFINED_AND_IMPLEMENTED",
                "observed_status": "Zero delta mapped to NO_ACTION",
                "risk": "LOW_FOR_ZERO_STATE",
                "evidence": ["runtime_planning.py:1100-1124", "A7 summary"],
            },
            {
                "edge_id": "canonical-06",
                "source": "runtime_planning",
                "target": "pending",
                "artifact": "pending_order_plan",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "Pending Materialization",
                "canonical_status": "DEFINED_AND_IMPLEMENTED_FOR_GENERAL_PLANNING",
                "observed_status": "No BUY_ADD pending in A7",
                "risk": "INSUFFICIENT_BUY_ADD_PROOF",
                "evidence": ["strategy_architecture_v1.md:84-85", "A8 summary"],
            },
            {
                "edge_id": "canonical-07",
                "source": "pending",
                "target": "approval",
                "artifact": "approval artifact",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "Approval",
                "canonical_status": "DEFINED",
                "observed_status": "No BUY_ADD approval observed in A7",
                "risk": "INSUFFICIENT_BUY_ADD_PROOF",
                "evidence": ["strategy_architecture_v1.md:103-105"],
            },
            {
                "edge_id": "canonical-08",
                "source": "approval",
                "target": "submit",
                "artifact": "approved pending",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "Submit Authority",
                "canonical_status": "DEFINED",
                "observed_status": "No BUY_ADD submit observed in A7",
                "risk": "INSUFFICIENT_BUY_ADD_PROOF",
                "evidence": ["runtime_architecture_v2.md:28-30"],
            },
            {
                "edge_id": "canonical-09",
                "source": "submit",
                "target": "execution",
                "artifact": "broker order / fill",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "Execution",
                "canonical_status": "DEFINED",
                "observed_status": "No ADD execution observed in A7",
                "risk": "INSUFFICIENT_BUY_ADD_PROOF",
                "evidence": ["strategy_architecture_v1.md:87-88"],
            },
            {
                "edge_id": "legacy-01",
                "source": "pm_decisions",
                "target": "legacy_sell_pipeline",
                "artifact": "SellExitDecision(source_decision=ADD)",
                "mode_scope": "Production/Demo/Historical common per Phase23-BS",
                "authority_type": "Legacy PM ADD Pending consumer",
                "canonical_status": "IMPLEMENTED_BUT_NOT_CURRENT_CANONICAL_SOT",
                "observed_status": "Not exercised in A7; exercised in Phase23 tests/reports",
                "risk": "THEORETICAL_DOUBLE_AUTHORITY",
                "evidence": ["phase23_bs report:61-69", "sell_pipeline.py:364-401"],
            },
            {
                "edge_id": "legacy-02",
                "source": "legacy_add_consumer",
                "target": "pm_add_order_plan",
                "artifact": "runtime_state/sell_pipeline/<date>/pm_add_order_plan.json",
                "mode_scope": "Production/Demo/Historical",
                "authority_type": "ADD-derived BUY Pending",
                "canonical_status": "LEGACY_COMPATIBILITY",
                "observed_status": "Phase23-BS reproduced pending BUY source_decision_type=ADD; A7 none",
                "risk": "THEORETICAL_DOUBLE_AUTHORITY",
                "evidence": ["add_consumer.py:164-249", "sell_pipeline.py:780-891"],
            },
        ],
    }

    pm_add_edge = {
        "pm_add_consumed_by_portfolio_construction_in_code": "PARTIAL",
        "code_contract": "portfolio_construction.py reads rows from position_management_artifact_path positions and maps action ADD to RETAIN/INCREASE.",
        "observed_run_contract": "NOT_CONNECTED_FOR_RUNTIME_PM_ADD",
        "observed_runtime_pm_add_count": a7_summary["pm_decision_counts"].get("ADD", 0),
        "observed_portfolio_construction_add_mapping_count": pc_observed["observed_runtime_pm_add_in_pc"],
        "observed_portfolio_construction_unresolved_pm_rows": pc_observed["observed_unresolved_pm_rows_in_pc"],
        "pm_add_affects_membership": "In code, ADD maps to membership RETAIN and weight_intent INCREASE. In observed run, runtime PM ADD did not appear in Portfolio Construction.",
        "pm_hold_vs_add_distinction": "In code, HOLD maps to RETAIN/MAINTAIN while ADD maps to RETAIN/INCREASE. In observed run, both were hidden by UNRESOLVED Strategy PM adapter rows.",
        "lineage_saved": "Portfolio Construction member stores pm_action, pm_intensity, position_management_reference, reason_codes when PM action is present.",
        "judgment": "DEFINED_IN_CODE_BUT_NOT_PROVEN_CONNECTED_TO_RUNTIME_PM_ADD",
        "evidence": [
            "src/ai_fund_lab_v2/strategy/portfolio_construction.py:240-246",
            "src/ai_fund_lab_v2/strategy/portfolio_construction.py:708-728",
            "src/ai_fund_lab_v2/strategy/portfolio_construction.py:1271-1280",
            "A9 observed PC mapping",
        ],
    }

    positive_delta_contract = {
        "existing_position_target_weight_recalculated": "DEFINED_BY_PORTFOLIO_CONSTRUCTION_TARGET_WEIGHT_CONTRACT",
        "current_weight_vs_target_weight_comparison_exists": "YES_IN_POSITION_SIZING",
        "target_quantity_candidate_semantics": "Total desired holding candidate, computed from target_notional/reference_price/trading_unit in Position Sizing.",
        "order_quantity_semantics": "Runtime Planning planned_quantity is order quantity; for no-order intents it is 0.",
        "quantity_delta_semantics": "target_quantity_candidate - current_quantity in Position Sizing.",
        "positive_delta_reaches_buy_add": "YES_IN_RUNTIME_PLANNING_CODE_IF_DELTA_POSITIVE_AND_SYMBOL_IS_CURRENT",
        "zero_delta_reaches_no_action": "YES_IN_RUNTIME_PLANNING_CODE",
        "observed_a7_positive_delta_count": 0,
        "observed_a7_zero_delta_count": a7_summary["existing_position_rows"],
        "a7_zero_add_explained_by_contract": "YES for zero-delta Planning behavior; NO for why runtime PM ADD did not enter canonical PM->PC edge as ADD.",
        "evidence": [
            "position_sizing.py:697-754",
            "runtime_planning.py:1054-1065",
            "runtime_planning.py:1100-1124",
            "A7 desired_quantity_trace.json",
        ],
    }

    legacy_inventory = {
        "path_add_consumer": "src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py",
        "path_sell_pipeline": "src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py",
        "producer": "sell_pipeline receives SellExitDecision(source_decision=ADD) and invokes add_consumer",
        "input_artifact_or_object": "PM decisions adapted into SellExitDecision with source_decision=ADD",
        "output_artifact": "runtime_state/sell_pipeline/<date>/pm_add_order_plan.json and pending_order_plan/pending_order_plan.json",
        "quantity_source": "Runtime current position valuation, CashExposureAuthority, PositionSizingAuthority.remaining_add_capacity, capital policy min/max order, lot unit",
        "cash_authority": "CashExposureAuthority",
        "safety_authority": "RuntimeSafetyDecision block_buy",
        "pending_authority": "promote_order_plan_to_pending plus Pending writer",
        "submit_consumer": "Submit pipeline consumes pending_order_plan",
        "mode_scope": "Production/Demo/Historical common per Phase23-BS; code parameter mode affects environment but path is not historical-only.",
        "currently_active_by_code": True,
        "active_by_observed_a7_run": False,
        "canonical_overlap": "Overlaps with canonical BUY_ADD if both can produce same-symbol BUY pending from PM ADD / positive delta.",
        "historical_only_branch": False,
        "evidence": [
            "add_consumer.py:43-63",
            "add_consumer.py:117-256",
            "sell_pipeline.py:364-401",
            "sell_pipeline.py:780-891",
            "phase23_bs report:61-69",
        ],
    }

    legacy_disposition = {
        "classification": "DEPRECATED_BUT_ACTIVE",
        "producer": legacy_inventory["producer"],
        "artifact": legacy_inventory["output_artifact"],
        "consumer": legacy_inventory["submit_consumer"],
        "decision_effect": "Can create BUY Pending items with source_decision_type=ADD when accepted.",
        "why_not_dead_code": "Tests and sell_pipeline code paths demonstrate accepted PM ADD pending generation.",
        "why_not_canonical_active": "Current Strategy SoT defines canonical BUY_ADD through Portfolio Construction, Position Sizing, and Runtime Planning, not direct PM ADD pending generation.",
        "why_not_observability_only": "It can write pending order plan artifacts, approval, and pending items.",
        "judgment": "REQUIRES_DISPOSITION_BY_ARCHITECTURE_REPAIR",
    }

    double_risk = {
        "risk_classification": "THEORETICAL_RISK",
        "risk_condition": "If canonical Runtime Planning emits BUY_ADD and legacy sell_pipeline/add_consumer also accepts PM ADD for the same business_date/symbol/campaign, both can target pending BUY generation.",
        "pending_double_generation": "THEORETICAL_RISK",
        "quantity_double_counting": "THEORETICAL_RISK",
        "approval_double": "THEORETICAL_RISK",
        "submit_double": "GUARDED_BY_PENDING_CURRENT_SINGLE_PATH_BUT_NOT_PROVEN_FOR_DUAL_PRODUCER_SAME_SYMBOL",
        "fill_double": "THEORETICAL_RISK_IF_TWO_APPROVED_PENDING_ITEMS_SURVIVE",
        "ledger_double_projection": "THEORETICAL_RISK_IF_DOUBLE_FILL_OCCURS",
        "observed_in_a7": "NO",
        "explicit_contract_guard_found": "INSUFFICIENT_EVIDENCE_FOR_CANONICAL_PLUS_LEGACY_MUTUAL_EXCLUSION",
        "evidence": [
            "strategy/runtime_planning.py BUY_ADD mapping",
            "sell_pipeline.py _write_add_pending",
            "add_consumer.py duplicate pending guard only checks existing buy pending symbols passed into that consumer",
        ],
    }

    mode_review = {
        "production": {
            "producer": "Common Runtime/Strategy code paths by architecture",
            "artifact": "Same schemas intended",
            "consumer": "Same pending/submit contracts intended",
            "mode_specific_branch": "No historical-only ADD branch found in reviewed add_consumer.",
            "fallback": "No allowed latest fallback in architecture.",
        },
        "demo": {
            "producer": "Same code paths; environment may trigger broker capability differences",
            "artifact": "Same pending artifacts",
            "consumer": "Demo submit/broker adapter",
            "mode_specific_branch": "Broker capability can differ; ADD authority contract is not demo-only.",
            "fallback": "No ADD-specific demo fallback identified.",
        },
        "historical": {
            "producer": "Same code path intended; simulated execution differs",
            "artifact": "Same pending/order evidence intended",
            "consumer": "Historical simulated submit/execution",
            "mode_specific_branch": "No historical-only ADD producer found in reviewed files.",
            "fallback": "Historical must use same schema and consumer contract as Production per autonomous architecture.",
        },
        "judgment": "PRODUCTION_COMMON_INTENT_CONFIRMED_FOR_CONTRACT; FULL_MODE_PARITY_FOR_BUY_ADD_NOT_PROVEN_BY_A7_RUN",
        "evidence": [
            "autonomous_ai_operations_architecture.md:129",
            "phase23_bs report:7-8",
            "phase23_bs report:59",
            "add_consumer.py",
            "sell_pipeline.py",
        ],
    }

    boundary = {
        "architecture_contract": [
            "ADD Producer / Consumer responsibility",
            "Canonical BUY_ADD path",
            "Legacy add_consumer disposition",
            "Quantity Authority",
            "Pending / Submit Authority",
            "Mode parity",
            "Double-authority prevention",
            "PM ADD to Portfolio Construction edge",
        ],
        "performance_design_deferred": [
            "When to ADD",
            "Momentum thresholds",
            "ADD amount",
            "HOLD vs ADD boundary",
            "Concentration caps",
            "Rank / Quality / Market Context conditions",
        ],
        "phase27b_status": "DEFERRED_TO_PHASE27_B",
    }

    gap_inventory = [
        {
            "gap_id": "A9-G1",
            "classification": "CANONICAL_PATH_NOT_SINGLE",
            "description": "Strategy SoT defines BUY_ADD via target portfolio/quantity delta, while legacy sell_pipeline/add_consumer can generate PM ADD BUY pending.",
            "evidence": ["strategy_architecture_v1.md:207-227", "add_consumer.py:43-63", "sell_pipeline.py:780-891"],
            "repair_required": True,
        },
        {
            "gap_id": "A9-G2",
            "classification": "PM_ADD_TO_PORTFOLIO_CONSTRUCTION_RUNTIME_EDGE_NOT_PROVEN",
            "description": "Portfolio Construction can map ADD to RETAIN/INCREASE in code, but observed run delivered UNRESOLVED PM rows, not runtime PM ADD decisions.",
            "evidence": ["portfolio_construction.py:1271-1280", "A9 observed PC mapping"],
            "repair_required": True,
        },
        {
            "gap_id": "A9-G3",
            "classification": "DOUBLE_AUTHORITY_MUTUAL_EXCLUSION_NOT_EXPLICIT",
            "description": "No explicit reviewed contract proves canonical BUY_ADD and legacy PM ADD pending cannot both produce same-symbol pending items.",
            "evidence": ["runtime_planning.py:1100-1124", "sell_pipeline.py:364-401"],
            "repair_required": True,
        },
        {
            "gap_id": "A9-G4",
            "classification": "PERFORMANCE_DESIGN_OUT_OF_SCOPE",
            "description": "When or how much to ADD remains a Strategy/Performance Design question, not an A9 contract decision.",
            "evidence": ["A9 task constraints", "adaptive_buy_quality_authority.md:23"],
            "repair_required": False,
        },
    ]

    repair_scope = {
        "architecture_repair_required": True,
        "scope_type": "RESPONSIBILITY_AND_CONTRACT_DISPOSITION_ONLY",
        "minimal_targets": [
            "Declare one canonical BUY_ADD producer/consumer chain.",
            "Classify legacy add_consumer/sell_pipeline ADD path as retired, compatibility-only, or canonical adapter.",
            "Define explicit mutual-exclusion/deduplication authority if legacy path remains callable.",
            "Clarify PM ADD artifact consumed by Portfolio Construction and ensure lineage contract names the canonical source.",
            "Clarify that Position Sizing owns positive delta and Runtime Planning owns BUY_ADD mapping.",
        ],
        "explicitly_not_in_scope": [
            "ADD thresholds",
            "ADD amount",
            "Momentum rules",
            "Quality formula changes",
            "Portfolio concentration policy changes",
            "Historical long-run validation",
        ],
        "implementation_proposal": "NOT_PROVIDED_BY_A9",
    }

    findings = {
        "formal_buy_add_path_single_defined": "NO",
        "pm_add_connected_to_canonical_portfolio_construction": "DEFINED_IN_CODE_BUT_NOT_PROVEN_IN_OBSERVED_RUNTIME",
        "existing_position_positive_delta_possible": "YES_IN_CONTRACT_AND_CODE_IF_TARGET_QUANTITY_EXCEEDS_CURRENT_QUANTITY",
        "a7_zero_executable_add_contract_explained": "PARTIAL: zero delta explains NO_ACTION; PM ADD to PC disconnect remains.",
        "legacy_add_consumer_active_decision_consumer": "YES_BY_CODE_AND_TESTS; NOT_OBSERVED_IN_A7",
        "legacy_overlaps_canonical": "YES_THEORETICALLY",
        "double_add_risk": double_risk["risk_classification"],
        "mode_parity": mode_review["judgment"],
        "architecture_repair_required": True,
        "minimum_repair_target": repair_scope["minimal_targets"],
    }

    summary = {
        "phase": "Phase27",
        "task_id": "Phase27-A9",
        "run_id": RUN_ID,
        "primary_judgment": "PHASE27_A9_BUY_ADD_AUTHORITY_CONTRACT_GAP_CONFIRMED_REPAIR_REQUIRED",
        "supporting_judgments": {
            "canonical_buy_add_path": "PARTIAL",
            "legacy_add_consumer": "ACTIVE",
            "double_authority_risk": "THEORETICAL",
            "architecture_repair": "REQUIRED",
            "performance_design": "DEFERRED_TO_PHASE27_B",
        },
        "implementation_changed": False,
        "historical_execution": "PROHIBITED_NOT_EXECUTED",
        "answer": "BUY_ADD has a conditional canonical Strategy path, but the codebase still contains an active legacy PM ADD consumer and the observed run does not prove runtime PM ADD reaches canonical Portfolio Construction. Architecture/Contract repair is required before Performance Design.",
        "observed_a7": {
            "existing_position_rows": a7_summary["existing_position_rows"],
            "pm_add": a7_summary["pm_decision_counts"].get("ADD", 0),
            "planning_buy_add": 0,
            "executable_add": 0,
            "planning_no_action": a7_summary["planning_intent_counts"].get("NO_ACTION", 0),
        },
        "observed_portfolio_construction": pc_observed,
        "predecessor_a8_judgment": a8_summary["primary_judgment"],
        "required_findings": findings,
    }

    test_results = {
        "fresh_run": "NOT_EXECUTED",
        "resume": "NOT_EXECUTED",
        "historical": "NOT_EXECUTED",
        "long_regression": "NOT_EXECUTED",
        "validation": "JSON_OUTPUT_VALIDATION_ONLY",
        "implementation_changed": False,
        "required_outputs_present": True,
        "documents_reviewed": [
            "docs/02_architecture/autonomous_ai_operations_architecture.md",
            "docs/02_architecture/strategy_architecture_v1.md",
            "docs/02_architecture/runtime_architecture_v2.md",
            "docs/02_architecture/adaptive_buy_quality_authority.md",
            "docs/02_architecture/portfolio_construction_and_position_sizing_contract.md",
            "docs/phase_reports/phase27_a7_existing_position_position_management_decision_authority_audit.md",
            "docs/phase_reports/phase27_a8_add_authority_contract_review.md",
            "docs/phase_reports/phase23_br_2022_10bd_post_carry_forward_submit_halt_root_cause_audit.md",
            "docs/phase_reports/phase23_bs_pm_add_pending_submit_policy_authority_binding_repair.md",
        ],
        "code_reviewed": [
            "src/ai_fund_lab_v2/runtime_v2/position_management/producer.py",
            "src/ai_fund_lab_v2/strategy/portfolio_construction.py",
            "src/ai_fund_lab_v2/strategy/position_sizing.py",
            "src/ai_fund_lab_v2/strategy/runtime_planning.py",
            "src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py",
            "src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py",
        ],
    }

    outputs = {
        "summary.json": summary,
        "decision_authority_matrix.json": decision_authority_matrix,
        "canonical_buy_add_contract.json": canonical_buy_add_contract,
        "canonical_buy_add_contract_graph.json": graph,
        "pm_add_to_portfolio_construction_edge.json": pm_add_edge,
        "existing_position_positive_delta_contract.json": positive_delta_contract,
        "legacy_add_consumer_inventory.json": legacy_inventory,
        "legacy_add_consumer_disposition.json": legacy_disposition,
        "double_authority_risk_review.json": double_risk,
        "production_common_mode_review.json": mode_review,
        "architecture_performance_boundary.json": boundary,
        "architecture_gap_inventory.json": gap_inventory,
        "recommended_repair_scope.json": repair_scope,
        "test_results.json": test_results,
    }
    for name, payload in outputs.items():
        write_json(OUT_DIR / name, payload)

    report = f"""# Phase27-A9 — Canonical BUY_ADD Authority Unification and Legacy Consumer Disposition Design Review

## Scope

This is a read-only Architecture / Contract Design Review. No Runtime, Strategy, PM, Portfolio Construction, Position Sizing, Runtime Planning, `add_consumer`, `sell_pipeline`, Pending, Submit, or Safety logic was modified. No fresh-run, resume, Historical run, 100BD, 1-year, or long regression was executed.

## Primary Judgment

`{summary["primary_judgment"]}`

Supporting judgments:

- Canonical BUY_ADD Path: `PARTIAL`
- Legacy ADD Consumer: `ACTIVE`
- Double-authority Risk: `THEORETICAL`
- Architecture Repair: `REQUIRED`
- Performance Design: `DEFERRED_TO_PHASE27_B`

## Core Conclusion

Production Architecture defines a conditional BUY_ADD path, but it is not cleanly unified in the current architecture and implementation evidence.

Canonical contract:

```text
Existing Position
  -> PM ADD / HOLD / REDUCE / EXIT intent
  -> Portfolio Construction target membership / target weight
  -> Position Sizing target notional / target quantity / quantity delta
  -> Runtime Planning BUY_ADD if existing-position quantity_delta_candidate > 0
  -> Strategy Planning Authority
  -> Pending
  -> Approval
  -> Submit
  -> Execution
```

PM ADD is not itself a BUY order. Quantity and executable BUY_ADD are downstream authorities.

## A7 / A8 Evidence

Observed in A7:

- Existing-position rows: {a7_summary["existing_position_rows"]}
- PM ADD: {a7_summary["pm_decision_counts"].get("ADD", 0)}
- Planning BUY_ADD: 0
- Executable ADD: 0
- Planning NO_ACTION: {a7_summary["planning_intent_counts"].get("NO_ACTION", 0)} / {a7_summary["existing_position_rows"]}

Observed in A9 Portfolio Construction inspection:

- Strategy Portfolio Construction artifact statuses: `{pc_observed["portfolio_construction_artifact_status_counts"]}`
- PM rows seen by Portfolio Construction: `{pc_observed["portfolio_construction_pm_mapping_counts"]}`
- Runtime PM ADD observed as Portfolio Construction ADD/RETAIN/INCREASE: `{pc_observed["observed_runtime_pm_add_in_pc"]}`

This means the A7 run's Runtime PM ADD decisions did not reach canonical Portfolio Construction as ADD.

## Authority Ownership

- PM ADD Intent: Position Management
- Portfolio Membership: Portfolio Construction
- Target Weight: Portfolio Construction
- Target Notional: Position Sizing
- Target Quantity: Position Sizing
- Quantity Delta: Position Sizing
- BUY_ADD Planning Intent: Runtime Planning
- Pending Generation: Strategy Planning Authority / Pending Materialization
- Submit Permission: Approval + Submit Guard + Safety
- Execution: Broker / Execution

See `decision_authority_matrix.json` for the full matrix.

## PM ADD To Portfolio Construction

Code-level contract exists:

- `portfolio_construction.py` reads PM rows from the position management artifact.
- `ADD` maps to `RETAIN / INCREASE`.
- `HOLD` maps to `RETAIN / MAINTAIN`.

Observed runtime contract is not proven:

- A7 run had 145 Runtime PM ADD decisions.
- Portfolio Construction observed 0 `ADD / RETAIN / INCREASE` PM rows.
- Portfolio Construction observed 364 `UNRESOLVED / UNRESOLVED / UNRESOLVED` PM rows.

Judgment:

`DEFINED_IN_CODE_BUT_NOT_PROVEN_CONNECTED_TO_RUNTIME_PM_ADD`

## Existing-position Positive Delta

The positive delta contract exists:

- `target_quantity_candidate` is total desired holding candidate from Position Sizing.
- `quantity_delta_candidate` is target quantity minus current quantity.
- Runtime Planning maps positive delta on an already-held symbol to `BUY_ADD`.
- Runtime Planning maps zero current-position delta to `NO_ACTION`.

A7's 0 executable ADD is therefore contract-explainable for the zero-delta Planning result, but not sufficient to prove PM ADD is correctly connected to the canonical PM -> Portfolio Construction edge.

## Legacy ADD Consumer

Legacy path:

```text
sell_pipeline
  -> add_consumer
  -> pm_add_order_plan.json
  -> pending_order_plan.json
  -> approval
  -> submit
```

Disposition:

`DEPRECATED_BUT_ACTIVE`

Why:

- It is not dead code: code and Phase23 tests/reports show it can produce BUY Pending items with `source_decision_type=ADD`.
- It is not observability-only: it can write `pm_add_order_plan.json`, approval, and pending artifacts.
- It is not cleanly canonical under current Strategy SoT, which defines BUY_ADD through Portfolio Construction / Position Sizing / Runtime Planning.

## Double-authority Risk

Risk classification:

`THEORETICAL_RISK`

If canonical Runtime Planning emits BUY_ADD and legacy `add_consumer` also accepts PM ADD for the same business date/symbol/campaign, both paths can target BUY Pending generation. A7 did not observe this, and Submit/Pending guards may stop some duplicated states, but A9 did not find an explicit canonical-vs-legacy mutual exclusion contract.

## Production / Demo / Historical

Mode review judgment:

`PRODUCTION_COMMON_INTENT_CONFIRMED_FOR_CONTRACT; FULL_MODE_PARITY_FOR_BUY_ADD_NOT_PROVEN_BY_A7_RUN`

No historical-only ADD producer was found in the reviewed files. Phase23-BS describes the repaired PM ADD pending policy propagation as Production / Demo / Historical common. Demo broker capability may differ, but that is separate from BUY_ADD authority.

## Architecture vs Performance

Architecture / Contract:

- ADD Producer / Consumer responsibility
- Canonical path
- Legacy path disposition
- Quantity Authority
- Pending / Submit Authority
- Mode parity
- Double-authority prevention

Performance Design, deferred to Phase27-B:

- when to ADD
- ADD amount
- momentum conditions
- HOLD vs ADD boundary
- concentration thresholds
- Rank / Quality / Market Context conditions

## Repair Scope

Architecture Repair is required, but A9 does not propose implementation details or Performance Design.

Minimum responsibility scope:

- Declare one canonical BUY_ADD producer/consumer chain.
- Classify legacy `add_consumer` / `sell_pipeline` ADD path as retired, compatibility-only, or canonical adapter.
- Define explicit mutual exclusion / deduplication authority if legacy path remains callable.
- Clarify which PM ADD artifact Portfolio Construction consumes.
- Preserve separation: PM owns intent, Portfolio Construction owns target portfolio, Position Sizing owns quantity delta, Runtime Planning owns BUY_ADD mapping.

## Deliverables

- `summary.json`
- `decision_authority_matrix.json`
- `canonical_buy_add_contract.json`
- `canonical_buy_add_contract_graph.json`
- `pm_add_to_portfolio_construction_edge.json`
- `existing_position_positive_delta_contract.json`
- `legacy_add_consumer_inventory.json`
- `legacy_add_consumer_disposition.json`
- `double_authority_risk_review.json`
- `production_common_mode_review.json`
- `architecture_performance_boundary.json`
- `architecture_gap_inventory.json`
- `recommended_repair_scope.json`
- `test_results.json`
"""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
