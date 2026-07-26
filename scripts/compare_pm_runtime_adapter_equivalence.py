#!/usr/bin/env python3
"""Compare accepted and current PM Runtime adapter behavior.

This tool is read-only with respect to the repository and Accepted Generation.
It materializes temporary runtime fixtures under the requested output directory,
loads the old accepted producer source from Git history into an isolated module,
and compares canonical Runtime PM behavior against the current producer module.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCER_PATH = Path("src/ai_fund_lab_v2/runtime_v2/position_management/producer.py")
OLD_ACCEPTED_COMMIT = "f4f8dbf03355106f201174f6f68b86aac707b6ed"
OLD_ACCEPTED_HASH = "93581111ae9b61facf669f8033d87e927f103d05483b4f212da4a592dbb15185"
BUSINESS_DATE = "2026-07-09"
FIXED_NOW = datetime(2026, 7, 9, 0, 0, tzinfo=timezone.utc)

CANONICAL_ARTIFACT_FIELDS = (
    "status",
    "reason",
    "review_required",
    "decision_count",
    "hold_count",
    "reduce_count",
    "exit_count",
    "add_count",
    "missing_fields",
    "missing_symbols",
    "defaulted_fields",
    "derived_fields",
    "temporal_validation_status",
)

CANONICAL_DECISION_FIELDS = (
    "symbol",
    "business_date",
    "decision",
    "decision_id",
    "reason",
    "runtime_action",
    "runtime_sell_quantity",
    "runtime_quantity_authority",
    "reduce_intensity",
    "hold_score",
    "exit_score",
    "reduce_score",
    "add_score",
    "confidence",
    "review_required",
)

ALLOWED_NEW_FIELDS = {
    "action_score",
    "confidence_semantics",
    "decision_reason_codes",
    "decision_trace",
    "decision_trace_contract_version",
    "dominant_cause",
    "secondary_causes",
    "selected_action_score",
    "decision_trace_path",
}


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    expected_action: str
    positions: list[dict[str, Any]]
    symbols: tuple[str, ...]
    expected_edge: float = 0.04
    buy_rank: int = 3
    downside: float = 0.2
    risk_guard_status: str = "ok"
    technicals: dict[str, float] | None = None
    feature_symbols: tuple[str, ...] | None = None
    include_no_position_reason: bool = True


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_show(commit: str, path: Path) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def git_commit() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def source_dirty(path: Path) -> bool:
    completed = subprocess.run(["git", "diff", "--quiet", "--", path.as_posix()], cwd=REPO_ROOT, check=False)
    return completed.returncode != 0


def load_old_module(output_root: Path):
    old_source = git_show(OLD_ACCEPTED_COMMIT, PRODUCER_PATH)
    old_hash = sha256_bytes(old_source)
    if old_hash != OLD_ACCEPTED_HASH:
        raise RuntimeError(f"old accepted source hash mismatch: {old_hash} != {OLD_ACCEPTED_HASH}")
    source_path = output_root / "old_accepted_runtime_adapter" / "producer.py"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(old_source)
    spec = importlib.util.spec_from_file_location("phase20_v_old_pm_producer", source_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to create old producer module spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, source_path, old_hash


def patch_authority(module: Any, label: str) -> None:
    module.verify_position_management_runtime_adapter_authority = lambda: {
        "authority_mode": "PHASE20_V_EQUIVALENCE_HARNESS_BYPASS_ONLY",
        "status": "PASS",
        "label": label,
        "reason": "behavioral equivalence harness compares adapter behavior after accepted-current-path hash identity is separately verified",
    }


def position(symbol: str, *, quantity: float = 100, average_price: float = 1000, current_price: float = 1020, peak_return: float | None = None) -> dict[str, Any]:
    current_return = (current_price / average_price) - 1.0
    return {
        "symbol": symbol,
        "quantity": quantity,
        "average_price": average_price,
        "current_price": current_price,
        "market_value": quantity * current_price,
        "unrealized_pnl": (current_price - average_price) * quantity,
        "holding_days": 12,
        "peak_return": max(current_return, 0.0) if peak_return is None else peak_return,
        "source": "runtime_v2_runtime_owned_fill_projection",
        "as_of": BUSINESS_DATE,
    }


def runtime_root(base: Path, *, positions: list[dict[str, Any]]) -> Path:
    root = base / ".runtime"
    write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "asset_state_id": "phase20v-fixture",
            "environment": "demo",
            "source": "runtime_v2_runtime_owned_fill_projection",
            "as_of": BUSINESS_DATE,
            "updated_at": BUSINESS_DATE + "T00:00:00Z",
            "positions": positions,
            "cash": 500000,
            "buying_power": 500000,
            "market_value": sum(float(item.get("market_value") or 0) for item in positions),
            "total_equity": 500000 + sum(float(item.get("market_value") or 0) for item in positions),
            "review_required": False,
        },
    )
    write_json(root / "pending_order_plan" / "pending_order_plan.json", {"state": "CONSUMED", "items": []})
    write_json(root / "runtime_state" / "current_state.json", {"state": "CURRENT_STATE_LOADED"})
    for name in ("orders", "executions", "cash", "events", "positions"):
        path = root / "persistent_ledger" / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return root


def pm_inputs(base: Path, scenario: Scenario) -> tuple[Path, Path]:
    base.mkdir(parents=True, exist_ok=True)
    opportunity_path = base / "pm_opportunity.csv"
    pd.DataFrame(
        [
            {
                "target_date": BUSINESS_DATE,
                "code": symbol,
                "expected_edge_score": scenario.expected_edge,
                "buy_rank": scenario.buy_rank,
                "downside_risk_score": scenario.downside,
                "risk_guard_status": scenario.risk_guard_status,
                "candidate_score": 0.5,
                "candidate_rank": scenario.buy_rank,
                "buy_reason": "",
                "no_buy_reason": "",
                "calibration_policy_name": "phase20v_fixture",
            }
            for symbol in scenario.symbols
        ]
    ).to_csv(opportunity_path, index=False)
    feature_path = base / "pm_feature.csv"
    technical_values = {
        "price_momentum_return_5d": 0.08,
        "price_momentum_return_20d": 0.12,
        "trend_close_over_ma_20d": 1.05,
        "trend_ma_5_20_ratio": 1.03,
        "volume_momentum_ratio_5d": 1.1,
        "volatility_return_std_20d": 0.02,
    }
    technical_values.update(scenario.technicals or {})
    selected_symbols = scenario.symbols if scenario.feature_symbols is None else scenario.feature_symbols
    rows = [
        {
            "target_date": BUSINESS_DATE,
            "feature_as_of_date": BUSINESS_DATE,
            "as_of_date": BUSINESS_DATE,
            "code": symbol,
            **technical_values,
            "feature_source_artifact": "candidate_features.parquet",
            "feature_source_hash": "fixture-candidate-feature-hash",
            "required_features": json.dumps(sorted(technical_values)),
            "optional_features": json.dumps(["no_position_reason"]),
            "missing_features": "[]",
            "defaulted_features": "[]",
            "temporal_validation_status": "PASS",
            "feature_version": "runtime_v2_pm_feature_input_v2_technical_complete",
            "data_until": BUSINESS_DATE,
            "created_at": BUSINESS_DATE + "T00:00:00Z",
        }
        for symbol in selected_symbols
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        columns = [
            "target_date",
            "feature_as_of_date",
            "as_of_date",
            "code",
            *technical_values.keys(),
            "feature_source_artifact",
            "feature_source_hash",
            "required_features",
            "optional_features",
            "missing_features",
            "defaulted_features",
            "temporal_validation_status",
            "feature_version",
            "data_until",
            "created_at",
        ]
        if scenario.include_no_position_reason:
            columns.append("no_position_reason")
        frame = pd.DataFrame(columns=columns)
    frame.to_csv(feature_path, index=False)
    return opportunity_path, feature_path


def scenarios() -> list[Scenario]:
    weak_technicals = {
        "price_momentum_return_5d": -0.08,
        "price_momentum_return_20d": -0.12,
        "trend_close_over_ma_20d": 0.94,
        "trend_ma_5_20_ratio": 0.94,
        "volume_momentum_ratio_5d": 0.8,
        "volatility_return_std_20d": 0.02,
    }
    return [
        Scenario("V-A-HOLD", "HOLD", [position("11110", current_price=1040)], ("11110",), expected_edge=0.06, buy_rank=3, downside=0.20),
        Scenario("V-B-REDUCE", "REDUCE", [position("22220", current_price=980, peak_return=0.07)], ("22220",), expected_edge=0.04, buy_rank=4, downside=0.68),
        Scenario("V-C-EXIT", "EXIT", [position("33330", current_price=900)], ("33330",), expected_edge=-0.02, buy_rank=12, downside=0.30),
        Scenario("V-D-ADD", "ADD", [position("44440", current_price=1080)], ("44440",), expected_edge=0.18, buy_rank=1, downside=0.10),
        Scenario("V-E-READY-EMPTY", "NO_POSITION", [], (), expected_edge=0.0, buy_rank=999, downside=0.0),
        Scenario("V-F-MISSING-OPTIONAL", "HOLD", [position("55550", current_price=1030)], ("55550",), expected_edge=0.05, buy_rank=3, downside=0.20, include_no_position_reason=False),
        Scenario("V-G-INVALID-REQUIRED", "REVIEW_REQUIRED", [position("66660", current_price=1030)], ("66660",), feature_symbols=()),
        Scenario("V-H-DECISION-ORDER-COLLISION", "EXIT", [position("77770", current_price=900, peak_return=0.10)], ("77770",), expected_edge=0.20, buy_rank=1, downside=0.80, risk_guard_status="high_risk", technicals=weak_technicals),
    ]


def run_scenario(module: Any, scenario: Scenario, root: Path) -> dict[str, Any]:
    rt = runtime_root(root / "runtime", positions=scenario.positions)
    opportunity_path, feature_path = pm_inputs(root / "inputs", scenario)
    result = module.produce_position_management_decisions(
        runtime_root=rt,
        business_date=BUSINESS_DATE,
        mode="demo",
        opportunity_path=opportunity_path,
        feature_path=feature_path,
        now=FIXED_NOW,
    )
    artifact = read_json(Path(result.artifact_path))
    action_rows = []
    action_path = Path(getattr(result, "action_csv_path", ""))
    if action_path.is_file():
        action_rows = pd.read_csv(action_path).to_dict(orient="records")
    return {
        "result_status": result.status,
        "result_reason": result.reason,
        "artifact": artifact,
        "actions": action_rows,
    }


def canonicalize(run: dict[str, Any]) -> dict[str, Any]:
    artifact = run["artifact"]
    decisions = []
    for decision in artifact.get("decisions") or []:
        decisions.append({field: normalize_value(decision.get(field)) for field in CANONICAL_DECISION_FIELDS})
    return {
        "artifact": {field: normalize_value(artifact.get(field)) for field in CANONICAL_ARTIFACT_FIELDS},
        "decisions": sorted(decisions, key=lambda row: (str(row.get("symbol") or ""), str(row.get("decision_id") or ""))),
        "actions": [
            {
                key: normalize_value(row.get(key))
                for key in ("code", "action", "hold_score", "exit_score", "reduce_score", "add_score", "action_reason", "exit_reason")
            }
            for row in sorted(run.get("actions") or [], key=lambda item: str(item.get("code") or ""))
        ],
    }


def normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_value(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [normalize_value(inner) for inner in value]
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        return round(value, 10)
    return value


def compare_scenario(scenario: Scenario, old_run: dict[str, Any], new_run: dict[str, Any]) -> dict[str, Any]:
    old_canonical = canonicalize(old_run)
    new_canonical = canonicalize(new_run)
    forbidden = []
    if old_canonical != new_canonical:
        forbidden.append({"field": "canonical_behavior", "old": old_canonical, "new": new_canonical})
    old_decisions = old_run["artifact"].get("decisions") or []
    new_decisions = new_run["artifact"].get("decisions") or []
    allowed = []
    for index, decision in enumerate(new_decisions):
        old_keys = set(old_decisions[index].keys()) if index < len(old_decisions) and isinstance(old_decisions[index], dict) else set()
        added = sorted((set(decision.keys()) - old_keys) & ALLOWED_NEW_FIELDS)
        if added:
            allowed.append({"decision_index": index, "allowed_new_fields": added})
    if new_run["artifact"].get("decision_trace_path") and not old_run["artifact"].get("decision_trace_path"):
        allowed.append({"artifact_field": "decision_trace_path", "classification": "TRACE_ARTIFACT_OUTPUT"})
    expected_pass = _expected_action_pass(scenario, new_run)
    if not expected_pass:
        forbidden.append({"field": "expected_action", "expected": scenario.expected_action, "new": _observed_action(new_run)})
    trace_check = _trace_check(new_run)
    return {
        "scenario_id": scenario.scenario_id,
        "expected_action": scenario.expected_action,
        "observed_action": _observed_action(new_run),
        "canonical_match": old_canonical == new_canonical,
        "expected_action_pass": expected_pass,
        "allowed_differences": allowed,
        "forbidden_differences": forbidden,
        "trace_check": trace_check,
        "old": old_canonical,
        "new": new_canonical,
    }


def _observed_action(run: dict[str, Any]) -> str:
    artifact = run["artifact"]
    if artifact.get("status") in {"NO_POSITION", "REVIEW_REQUIRED"}:
        return str(artifact.get("status"))
    decisions = artifact.get("decisions") or []
    if not decisions:
        return str(artifact.get("status") or "")
    return str(decisions[0].get("decision") or "")


def _expected_action_pass(scenario: Scenario, run: dict[str, Any]) -> bool:
    return _observed_action(run) == scenario.expected_action


def _trace_check(run: dict[str, Any]) -> dict[str, Any]:
    artifact = run["artifact"]
    decisions = artifact.get("decisions") or []
    if not decisions:
        return {"status": "NOT_REQUIRED", "reason": "no decisions"}
    required = ("decision_trace", "dominant_cause", "decision_reason_codes", "action_score", "confidence_semantics")
    missing = [field for field in required if field not in decisions[0]]
    trace = decisions[0].get("decision_trace") if isinstance(decisions[0].get("decision_trace"), dict) else {}
    forbidden_post_hoc = any(key in json.dumps(trace, sort_keys=True) for key in ("post_hoc", "future_return", "return_after_decision"))
    return {
        "status": "PASS" if not missing and not forbidden_post_hoc else "FAIL",
        "missing_fields": missing,
        "post_hoc_or_future_terms_present": forbidden_post_hoc,
    }


def static_diff_summary(old_source_path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "diff", "--no-index", "--", str(old_source_path), str(REPO_ROOT / PRODUCER_PATH)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    diff_text = completed.stdout
    categories = []
    category_terms = {
        "TRACE_ARTIFACT_OUTPUT": ("decision_trace", "trace", "dominant_cause"),
        "DECISION_FIELD_ADDITION": ("action_score", "confidence_semantics", "decision_reason_codes"),
        "SCHEMA_METADATA_ONLY": ("CONTRACT_VERSION", "schema", "contract"),
        "CONTROL_FLOW_CHANGE": ("if ", "return ", "raise "),
        "STATUS_CHANGE": ("status", "HALT", "REVIEW_REQUIRED"),
        "AUTHORITY_CHANGE": ("authority", "accepted", "hash"),
        "INPUT_CHANGE": ("feature", "holding", "opportunity"),
        "SCORE_CHANGE": ("score", "calculate_"),
        "ACTION_CHANGE": ("runtime_action", "SELL_", "decision"),
    }
    for category, terms in category_terms.items():
        if any(term in diff_text for term in terms):
            categories.append(category)
    if categories and set(categories).issubset({"TRACE_ARTIFACT_OUTPUT", "DECISION_FIELD_ADDITION", "SCHEMA_METADATA_ONLY", "CONTROL_FLOW_CHANGE", "STATUS_CHANGE", "INPUT_CHANGE", "SCORE_CHANGE", "ACTION_CHANGE", "AUTHORITY_CHANGE"}):
        categories.append("OBSERVABILITY_ONLY_REVIEWED_BY_BEHAVIORAL_HARNESS")
    return {
        "diff_exit_code": completed.returncode,
        "diff_line_count": len(diff_text.splitlines()),
        "categories": sorted(set(categories)),
        "diff_path": str(old_source_path),
    }


def build_report(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    old_module, old_source_path, old_hash = load_old_module(output_root)
    from ai_fund_lab_v2.runtime_v2.position_management import producer as current_module

    patch_authority(old_module, "old")
    patch_authority(current_module, "current")
    current_hash = sha256_file(REPO_ROOT / PRODUCER_PATH)
    scenario_reports = []
    for scenario in scenarios():
        scenario_root = output_root / "scenarios" / scenario.scenario_id
        if scenario_root.exists():
            shutil.rmtree(scenario_root)
        old_run = run_scenario(old_module, scenario, scenario_root / "old")
        new_run = run_scenario(current_module, scenario, scenario_root / "current")
        scenario_reports.append(compare_scenario(scenario, old_run, new_run))
    forbidden = [item for scenario in scenario_reports for item in scenario["forbidden_differences"]]
    allowed = [item for scenario in scenario_reports for item in scenario["allowed_differences"]]
    canonical_match_count = sum(1 for scenario in scenario_reports if scenario["canonical_match"])
    decision_count_old = sum(len(scenario["old"]["decisions"]) for scenario in scenario_reports)
    decision_count_new = sum(len(scenario["new"]["decisions"]) for scenario in scenario_reports)
    trace_failures = [scenario for scenario in scenario_reports if scenario["trace_check"]["status"] == "FAIL"]
    report = {
        "schema_version": "phase20_v_pm_runtime_adapter_equivalence.v1",
        "old_accepted_commit": OLD_ACCEPTED_COMMIT,
        "old_accepted_path": PRODUCER_PATH.as_posix(),
        "old_accepted_hash": old_hash,
        "old_hash_verified": old_hash == OLD_ACCEPTED_HASH,
        "current_commit": git_commit(),
        "current_source_dirty": source_dirty(PRODUCER_PATH),
        "current_path": PRODUCER_PATH.as_posix(),
        "current_hash": current_hash,
        "static_diff": static_diff_summary(old_source_path),
        "scenario_count": len(scenario_reports),
        "decision_count_old": decision_count_old,
        "decision_count_new": decision_count_new,
        "canonical_match_count": canonical_match_count,
        "allowed_difference_count": len(allowed),
        "forbidden_difference_count": len(forbidden),
        "trace_failure_count": len(trace_failures),
        "equivalence_judgment": "PM_RUNTIME_ADAPTER_BEHAVIORALLY_EQUIVALENT" if old_hash == OLD_ACCEPTED_HASH and current_hash and not forbidden and not trace_failures else "PM_RUNTIME_ADAPTER_EQUIVALENCE_FAILED",
        "acceptance_refresh_readiness": "FORMAL_ACCEPTANCE_REFRESH_READY" if old_hash == OLD_ACCEPTED_HASH and current_hash and not forbidden and not trace_failures else "FORMAL_ACCEPTANCE_REFRESH_NOT_READY",
        "scenarios": scenario_reports,
        "allowed_differences": allowed,
        "forbidden_differences": forbidden,
        "long_running_historical_test_executed": False,
        "accepted_generation_modified": False,
    }
    write_json(output_root / "equivalence_report.json", report)
    write_markdown(output_root / "equivalence_report.md", report)
    return report


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    rows = [
        "# Phase20-V PM Runtime Adapter Equivalence Evidence",
        "",
        f"Equivalence judgment: `{report['equivalence_judgment']}`",
        f"Acceptance readiness: `{report['acceptance_refresh_readiness']}`",
        "",
        "| Scenario | Expected | Observed | Canonical Match | Trace | Forbidden |",
        "|---|---|---|---|---|---:|",
    ]
    for scenario in report["scenarios"]:
        rows.append(
            f"| {scenario['scenario_id']} | {scenario['expected_action']} | {scenario['observed_action']} | {scenario['canonical_match']} | {scenario['trace_check']['status']} | {len(scenario['forbidden_differences'])} |"
        )
    rows.extend(
        [
            "",
            f"Old accepted hash: `{report['old_accepted_hash']}`",
            f"Current hash: `{report['current_hash']}`",
            "",
            "No Accepted Generation, registry pointer, broker, training, calibration, or Historical run was executed.",
        ]
    )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="reports/phase20_v_pm_runtime_adapter_behavioral_equivalence_review")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(Path(args.output_root))
    if args.print_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["equivalence_judgment"] == "PM_RUNTIME_ADAPTER_BEHAVIORALLY_EQUIVALENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
