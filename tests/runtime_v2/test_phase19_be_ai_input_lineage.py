from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.historical_support.isolated_root import protected_shared_runtime_hashes
from ai_fund_lab_v2.runtime_v2.system_status import _runtime_input_lineage_contract


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_TEST = REPO_ROOT / "scripts/runtime_test.py"
ISOLATED_ROOT = REPO_ROOT / ".runtime/runtime_tests/phase19_bb_historical_smoke_20260706_clean_day1/.runtime"


def _run_system_status(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src:."
    return subprocess.run(
        [sys.executable, str(RUNTIME_TEST), "system-status", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _report() -> dict:
    result = _run_system_status("--runtime-root", str(ISOLATED_ROOT), "--json")
    assert result.returncode in {0, 20}
    return json.loads(result.stdout)["system_status_report"]


def test_candidate_and_opportunity_dataset_source_windows_visible() -> None:
    report = _report()
    candidate = report["candidate_input_lineage"]
    opportunity = report["opportunity_input_lineage"]

    assert candidate["status"] == "PASS"
    assert candidate["training_dataset_revision"] == "candidate_dataset_revision_policy_amended_95eedc15c17fee4e"
    assert candidate["dataset_source_earliest_date"] == "2021-06-14"
    assert candidate["dataset_source_latest_date"] == "2026-05-15"
    assert candidate["dataset_source_row_count"] != "UNRESOLVED"
    assert candidate["dataset_source_content_hash"] != "UNRESOLVED"

    assert opportunity["status"] == "PASS"
    assert opportunity["training_dataset_revision"] == "opportunity_dataset_revision_policy_amended_e7f9478409126d8e"
    assert opportunity["dataset_source_earliest_date"] == "2021-09-08"
    assert opportunity["dataset_source_latest_date"] == "2026-05-15"
    assert opportunity["dataset_source_row_count"] != "UNRESOLVED"


def test_split_window_statistics_visible_or_not_recorded() -> None:
    report = _report()
    stats = report["split_window_statistics"]

    assert stats["candidate"]["Training"]["row_count"] == 3496880
    assert stats["candidate"]["Training"]["symbol_count"] == 4588
    assert stats["candidate"]["Calibration"]["mode"] == "SHARED_WITH_VALIDATION"
    assert stats["candidate"]["Validation"]["row_count"] == 934105
    assert stats["candidate"]["Test"]["row_count"] == 165028
    assert stats["candidate"]["Recent Holdout"]["row_count"] == 121158

    assert stats["opportunity"]["Training"]["row_count"] == 39563
    assert stats["opportunity"]["Validation"]["symbol_count"] == 955
    assert stats["opportunity"]["Test"]["row_count"] == 1940
    assert stats["opportunity"]["Recent Holdout"]["row_count"] == 1440


def test_recent_holdout_and_calibration_independence_in_lineage() -> None:
    report = _report()
    for key in ("candidate_input_lineage", "opportunity_input_lineage"):
        lineage = report[key]
        holdout = lineage["recent_holdout_usage"]
        independence = lineage["calibration_validation_independence"]

        assert holdout["recent_holdout_usage_status"] == "NOT_USED_IN_PHASE19"
        assert holdout["recent_holdout_used_for_training"] is False
        assert holdout["recent_holdout_used_for_calibration"] is False
        assert holdout["recent_holdout_used_for_validation"] is False
        assert holdout["recent_holdout_used_for_model_selection"] is False
        assert holdout["recent_holdout_runtime_authority_impact"] == "NONE"
        assert independence["calibration_mode"] == "SHARED_WITH_VALIDATION"
        assert independence["calibration_fit_target"] == "score calibration only"
        assert independence["model_selection_use"] is False
        assert independence["independence_status"] == "PASS"


def test_runtime_input_lineage_planned_pre_run_contract_visible() -> None:
    report = _report()
    runtime = report["runtime_input_lineage_contract"]

    assert runtime["runtime_stage"] == "PRE_RUN"
    assert runtime["target_business_date"] == "2026-07-06"
    assert runtime["required_market_data_through_date"] == "2026-07-06"
    assert runtime["planned_feature_source_date"] == "2026-07-06"
    assert runtime["temporal_cutoff_policy"] == "consumer input must be <= target business date"
    assert runtime["future_row_guard"] == "ENABLED_BY_TEMPORAL_GUARD"
    assert runtime["actual_feature_business_date"] == "NOT_YET_MATERIALIZED"


def test_runtime_input_lineage_switches_to_actual_values_after_materialization_fixture() -> None:
    contract = _runtime_input_lineage_contract(
        inspection_context={
            "runtime_stage": "FEATURE_READY",
            "target_business_date": "2026-07-06",
        },
        target_period_data_sufficiency={
            "per_day": [
                {
                    "business_date": "2026-07-06",
                    "raw_quotes": True,
                    "normalized_quotes": True,
                }
            ]
        },
        data_inspection={
            "runtime_features": [
                {
                    "component_id": "candidate_runtime_feature",
                    "status": "PASS",
                    "materialization_status": "READY",
                    "feature_date": "2026-07-06",
                    "row_count": 4321,
                    "symbol_count": 1234,
                }
            ]
        },
        ai_inventory={
            "active_ai_models": [
                {
                    "component_id": "candidate_ai",
                    "latest_inference_date": "2026-07-06",
                }
            ]
        },
    )

    assert contract["pre_run_contract_status"] == "NOT_APPLICABLE"
    assert contract["actual_feature_business_date"] == "2026-07-06"
    assert contract["actual_raw_normalized_input_range"] == "SEE_RUNTIME_FEATURE_ARTIFACT"
    assert contract["actual_input_row_count"] == 4321
    assert contract["actual_symbol_count"] == 1234
    assert contract["inference_business_date"] == "2026-07-06"


def test_human_output_has_be_sections_and_json_parity() -> None:
    report = _report()
    human = report["human_summary"]

    for text in [
        "Complete Data Source Inventory",
        "AI Input Lineage",
        "Runtime Input Lineage",
        "Runtime Baseline Traceability",
        "Freshness Policy Traceability",
        "candidate_input_lineage",
        "recent_holdout_usage",
        "calibration_validation_independence",
        "Components with complete input-lineage inspection: 2",
    ]:
        assert text in human
    assert report["candidate_input_lineage"]["dataset_source_earliest_date"] in human
    assert report["opportunity_input_lineage"]["dataset_source_earliest_date"] in human


def test_complete_data_source_inventory_common_contract_visible() -> None:
    report = _report()
    names = {item["component_name"] for item in report["data_source_inventory"]["items"]}

    assert {
        "Daily Quotes Raw",
        "Daily Quotes Normalized",
        "Listed Issues",
        "Trading Calendar",
        "Universe / Eligibility Data",
        "Financial Statements",
        "TOPIX / Market Index",
        "Corporate Actions",
    }.issubset(names)


def test_no_ambiguous_empty_values_for_be_fields_and_non_mutation() -> None:
    before = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")
    report = _report()
    after = protected_shared_runtime_hashes(REPO_ROOT / ".runtime")
    keys = {"dataset_path", "input_row_count", "business_date", "artifact_created_at", "dataset_artifact_path", "dataset_manifest_path"}
    hits: list[str] = []

    def walk(value, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else key
                if key in keys and child == "":
                    hits.append(child_path)
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(report)
    assert hits == []
    assert before == after
    assert report["non_mutation"]["broker_access"] == "NOT_PERFORMED"
    assert report["non_mutation"]["broker_write"] == 0
