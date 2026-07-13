from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.artifact_registry.formal_registration_dry_run import run_formal_registration_dry_run
from ai_fund_lab_v2.artifact_registry.validator import read_json


def test_phase16am_four_set_formal_registration_dry_run(tmp_path: Path) -> None:
    formal_event_log = Path(".runtime/artifact_registry/events/registry_events.jsonl").read_bytes()
    formal_index = Path(".runtime/artifact_registry/index/registry_index.json").read_bytes()
    formal_checkpoint = Path(".runtime/artifact_registry/checkpoints/latest.json").read_bytes()

    result = run_formal_registration_dry_run(output_root=tmp_path / "phase16am")

    assert result["overall_result"] == "PASS"
    assert len(result["set_results"]) == 4
    assert {item["artifact_set_type"] for item in result["set_results"]} == {
        "CANDIDATE_AI_SET",
        "OPPORTUNITY_AI_SET",
        "POSITION_MANAGEMENT_POLICY_SET",
        "CAPITAL_ALLOCATION_POLICY_SET",
    }
    for item in result["set_results"]:
        assert item["overall_result"] == "PASS"
        assert item["draft_event_id"]
        assert item["validated_event_id"]
        assert item["acceptance_event_id"]
        assert all(plan_item["overwrite"] is False for plan_item in item["copy_plan"]["items"])
        assert all(plan_item["hash"] and plan_item["size"] > 0 for plan_item in item["copy_plan"]["items"])

    assert result["index_result"]["overall_result"] == "PASS"
    assert result["index_result"]["entry_count"] == 4
    assert result["index_result"]["event_count"] == 12
    index = read_json(Path(result["index_result"]["index_path"]))
    assert all(entry["runtime_use_eligible"] is True for entry in index["entries"].values())
    assert all(entry["accepted_event_id"] for entry in index["entries"].values())

    assert result["checkpoint_result"]["overall_result"] == "PASS"
    assert result["checkpoint_result"]["event_count"] == 12
    assert result["checkpoint_result"]["entry_count"] == 4
    assert result["checkpoint_result"]["event_log_hash"]
    assert result["checkpoint_result"]["materialized_index_hash"] == result["index_result"]["index_hash"]
    assert result["checkpoint_result"]["checkpoint_hash"]

    assert result["protected_hashes_unchanged"] is True
    assert result["formal_registry_changed"] is False
    assert Path(".runtime/artifact_registry/events/registry_events.jsonl").read_bytes() == formal_event_log
    assert Path(".runtime/artifact_registry/index/registry_index.json").read_bytes() == formal_index
    assert Path(".runtime/artifact_registry/checkpoints/latest.json").read_bytes() == formal_checkpoint
