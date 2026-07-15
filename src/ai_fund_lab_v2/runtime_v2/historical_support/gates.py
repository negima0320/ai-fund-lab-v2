"""Historical Runtime entry gate aggregation.

Gate evaluation is read-only. It reports whether 5BD may start; it does not
execute reset, feature generation, submit, execution, or broker simulation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.historical_support.baseline import collect_regression_baseline
from ai_fund_lab_v2.runtime_v2.historical_support.reset_plan import build_reset_plan, validate_reset_plan


PHASE17_B1_DATES: tuple[str, ...] = (
    "2026-07-06",
    "2026-07-07",
    "2026-07-08",
    "2026-07-09",
    "2026-07-10",
)


def evaluate_historical_runtime_entry_gates(
    *,
    runtime_root: Path | str,
    repo_root: Path | str = ".",
    environment_id: str = "phase17-b1-historical",
    run_id: str = "phase17-b1-readiness",
) -> dict[str, Any]:
    """Evaluate historical Runtime gates and stop before 5BD if any gate is not PASS."""

    root = Path(runtime_root)
    repo = Path(repo_root)
    baseline = collect_regression_baseline(runtime_root=root, repo_root=repo)
    reset_plan = build_reset_plan(
        runtime_root=root,
        environment_id=environment_id,
        run_id=run_id,
        git_commit=str(baseline.get("git_commit") or "UNKNOWN"),
        runtime_version="runtime_v2",
    )
    reset_validation = validate_reset_plan(reset_plan)
    feature_window = _feature_window_status(root)
    pm_status = baseline["pm_adapter_authority"]["status"]
    gates = [
        _gate(
            "NORMAL_MAINLINE_READY",
            "DESIGN_CHANGE_REQUIRED",
            "NORMAL_MAINLINE_NOT_EXPOSABLE",
            "Submit pipeline and execution pipeline do not currently accept simulation as a normal mainline mode.",
        ),
        _gate(
            "RESET_READY",
            "PASS" if reset_validation["status"] == "PASS" else "HALT",
            "TEST_SUPPORT_IMPLEMENTATION_GAP" if reset_validation["status"] != "PASS" else "PASS",
            "Reset plan validation is available; reset execution was intentionally not run.",
        ),
        _gate(
            "HISTORICAL_CLOCK_READY",
            "REVIEW_REQUIRED",
            "CLOCK_CONFIGURATION_GAP",
            "CLI supports explicit business/evaluation time, but full job sequence clock audit is not accepted.",
        ),
        _gate(
            "HISTORICAL_BROKER_READY",
            "DESIGN_CHANGE_REQUIRED",
            "BROKER_ADAPTER_DEFECT",
            "Historical broker adapter exists only outside official CLI submit/execution selection.",
        ),
        _gate(
            "CANONICAL_DATA_INPUT_READY",
            "IMPLEMENTATION_REQUIRED",
            "CANONICAL_DATA_GAP",
            "Runtime feature path still relies on operational recent data, not accepted canonical historical input resolver.",
        ),
        _gate(
            "POINT_IN_TIME_READY",
            "IMPLEMENTATION_REQUIRED",
            "CANONICAL_DATA_GAP",
            "Point-in-time manifests for market/calendar/listed/universe/corporate action are not complete for 5BD.",
        ),
        _gate(
            "FEATURE_GENERATION_READY",
            "PASS" if feature_window["complete"] else "IMPLEMENTATION_REQUIRED",
            "FEATURE_DEFECT" if not feature_window["complete"] else "PASS",
            feature_window["reason"],
        ),
        _gate(
            "REGISTRY_FREEZE_READY",
            "PASS",
            "PASS",
            "Registry hashes and accepted set summary were collected read-only.",
        ),
        _gate(
            "PM_ADAPTER_AUTHORITY_READY",
            "PASS" if pm_status == "PASS" else "ARCHITECTURE_REVIEW_REQUIRED",
            "ARTIFACT_AUTHORITY_GAP" if pm_status != "PASS" else "PASS",
            "Current PM source is not byte-identical to the accepted frozen runtime adapter.",
        ),
        _gate(
            "EXTERNAL_EFFECTS_DISABLED",
            "REVIEW_REQUIRED",
            "OPTIONAL_COMPONENT_CONFIGURATION_GAP",
            "Payload-only evidence is available, but command-level historical network guard is not accepted.",
        ),
        _gate(
            "REGRESSION_BASELINE_READY",
            "PASS",
            "PASS",
            "Formal read-only regression baseline manifest was collected.",
        ),
        _gate(
            "TEST_WINDOW_READY",
            "PASS" if feature_window["complete"] else "NOT_READY",
            "FEATURE_DEFECT" if not feature_window["complete"] else "PASS",
            feature_window["reason"],
        ),
    ]
    all_pass = all(gate["status"] == "PASS" for gate in gates)
    return {
        "schema_version": "runtime_historical_entry_gate_evaluation_v1",
        "runtime_root": str(root),
        "environment_id": environment_id,
        "run_id": run_id,
        "candidate_dates": list(PHASE17_B1_DATES),
        "entry_gates": gates,
        "baseline": baseline,
        "reset_plan": reset_plan,
        "reset_validation": reset_validation,
        "feature_window": feature_window,
        "five_bd_started": False,
        "five_bd_start_allowed": all_pass,
        "stop_reason": "" if all_pass else "ENTRY_GATE_NOT_ALL_PASS",
    }


def _gate(gate: str, status: str, classification: str, reason: str) -> dict[str, Any]:
    return {
        "gate": gate,
        "status": status,
        "classification": classification,
        "blocking": status != "PASS",
        "reason": reason,
    }


def _feature_window_status(root: Path) -> dict[str, Any]:
    base = root / "operations" / "feature_artifacts"
    required = (
        "candidate_features.parquet",
        "opportunity_feature_input.parquet",
        "position_feature_input.parquet",
        "capital_policy_input.parquet",
    )
    dates: dict[str, Any] = {}
    missing: list[str] = []
    for business_date in PHASE17_B1_DATES:
        date_dir = base / business_date
        date_missing = [name for name in required if not (date_dir / name).exists()]
        dates[business_date] = {
            "path": str(date_dir),
            "exists": date_dir.exists(),
            "missing": date_missing,
            "complete": not date_missing,
        }
        if date_missing:
            missing.append(business_date)
    complete = not missing
    return {
        "complete": complete,
        "dates": dates,
        "missing_dates": missing,
        "reason": "5BD feature window complete" if complete else "Feature artifacts are incomplete for: " + ", ".join(missing),
    }
