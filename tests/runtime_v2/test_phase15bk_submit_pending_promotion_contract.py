from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.pending_promotion import run_submit_pending_promotion_review
from ai_fund_lab_v2.runtime_v2.review_only.sell_hold_morning import run_sell_hold_review_only_morning
from tests.runtime_v2.test_phase15aq_runtime_data_readiness_gate import BUSINESS_DATE, _load_json, _write_json, _write_policy
from tests.runtime_v2.test_phase15bh_sell_hold_review_only_morning import _review_only_runtime_with_4591


EVALUATION_TIME = "2026-07-11T12:00:00+00:00"


def test_phase15bk_promotion_candidate_ready_with_safety_block_and_no_pending_apply(tmp_path):
    runtime_root, policy_path = _runtime_with_review_pending(tmp_path)
    before_pending = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    result = run_submit_pending_promotion_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        now=_dt(EVALUATION_TIME),
    )

    candidate = _load_json(Path(result.promotion_candidate_path))
    approval = _load_json(Path(result.human_approval_path))
    linkage = _load_json(Path(result.review_pending_linkage_path))
    after_pending = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    assert result.status == "PASS"
    assert candidate["promotion_status"] == "READY_BUT_SAFETY_BLOCKED"
    assert candidate["promotion_allowed"] is False
    assert candidate["promotion_block_reasons"] == ["safety_submit_blocked"]
    assert candidate["apply_requested"] is False
    assert candidate["apply_executed"] is False
    assert candidate["submit_executed"] is False
    assert candidate["broker_write_performed"] is False
    assert candidate["authoritative_pending_mutated"] is False
    assert approval["approval_status"] == "APPROVED_FOR_PENDING_PROMOTION"
    assert approval["approved_item_ids"] == ["review-item-4591"]
    assert approval["automatic_trade_authorized"] is False
    assert approval["broker_write_authorized"] is False
    assert linkage["submit_allowed"] is False
    assert linkage["authoritative_submit_pending"] is False
    assert before_pending == after_pending


def test_phase15bk_regular_cli_path_generates_candidate_without_submit_or_pending_mutation(tmp_path):
    runtime_root, policy_path = _runtime_with_review_pending(tmp_path)
    before_pending = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "submit_pending_promotion_review",
            "--business-date",
            BUSINESS_DATE,
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(runtime_root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(runtime_root / "runtime_state" / "logs"),
            "--capital-deployment-policy",
            str(policy_path),
            "--evaluation-time",
            EVALUATION_TIME,
        ]
    )

    manifest = _latest_manifest(runtime_root)
    candidate = _load_json(Path(manifest["promotion_candidate_path"]))
    after_pending = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    assert exit_code == 0
    assert manifest["submit_pending_promotion_review_status"] == "PASS"
    assert manifest["promotion_candidate_status"] == "READY_BUT_SAFETY_BLOCKED"
    assert manifest["submit_executed"] is False
    assert manifest["broker_write_performed"] is False
    assert manifest["authoritative_pending_mutated"] is False
    assert candidate["apply_executed"] is False
    assert before_pending == after_pending


def test_phase15bk_human_approval_missing_or_invalid_blocks_promotion(tmp_path):
    runtime_root, policy_path = _runtime_with_review_pending(tmp_path)
    missing_approval = runtime_root / "runtime_state" / "human_approval" / BUSINESS_DATE / "missing.json"

    result = run_submit_pending_promotion_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        human_approval_path=missing_approval,
        now=_dt(EVALUATION_TIME),
    )

    candidate = _load_json(Path(result.promotion_candidate_path))
    assert result.status == "REVIEW_REQUIRED"
    assert "human_approval_schema_invalid" in candidate["promotion_block_reasons"]
    assert candidate["apply_executed"] is False


def test_phase15bk_expired_future_or_revoked_approval_blocks_promotion(tmp_path):
    runtime_root, policy_path = _runtime_with_review_pending(tmp_path)
    valid = _valid_approval(runtime_root, policy_path)

    for filename, updates, expected in (
        ("expired.json", {"expires_at": "2026-07-11T00:00:00+00:00"}, "approval_expired"),
        ("missing_expires.json", {"expires_at": ""}, "approval_expires_at_missing"),
        ("future_approved.json", {"approved_at": "2026-07-12T00:00:00+00:00"}, "approval_approved_at_future"),
        ("business_date_mismatch.json", {"business_date": "2026-07-09"}, "approval_business_date_mismatch"),
        ("revoked_at.json", {"revoked_at": "2026-07-11T12:00:01+00:00"}, "approval_revoked"),
        ("revoked_status.json", {"approval_status": "REVOKED"}, "human_approval_status_not_approved_for_pending_promotion"),
    ):
        path = runtime_root / "runtime_state" / "human_approval" / BUSINESS_DATE / filename
        payload = {**valid, **updates}
        _write_json(path, payload)

        result = run_submit_pending_promotion_review(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode="demo",
            capital_deployment_policy_path=policy_path,
            human_approval_path=path,
            now=_dt(EVALUATION_TIME),
        )
        candidate = _load_json(Path(result.promotion_candidate_path))

        assert result.status == "REVIEW_REQUIRED"
        assert expected in candidate["promotion_block_reasons"]
        assert candidate["apply_executed"] is False


def test_phase15bk_linkage_item_quantity_hash_and_event_mismatch_block_promotion(tmp_path):
    runtime_root, policy_path = _runtime_with_review_pending(tmp_path)
    valid = _valid_approval(runtime_root, policy_path)

    cases = (
        ("hash_mismatch.json", {"review_pending_hash": "sha256:wrong"}, "review_pending_hash_mismatch"),
        ("event_mismatch.json", {"source_safety_event_id": "wrong-event"}, "safety_event_id_mismatch"),
        ("review_mismatch.json", {"source_human_review_id": "wrong-review"}, "human_review_id_mismatch"),
        ("item_out_of_scope.json", {"approved_item_ids": ["review-item-9999"]}, "approved_item_out_of_scope"),
        (
            "quantity_mismatch.json",
            {"approved_quantities": {"review-item-4591": 100.0}},
            "approved_quantity_mismatch",
        ),
        (
            "item_hash_mismatch.json",
            {"approved_review_item_hashes": {"review-item-4591": "sha256:wrong"}},
            "review_item_hash_mismatch",
        ),
    )
    for filename, updates, expected in cases:
        path = runtime_root / "runtime_state" / "human_approval" / BUSINESS_DATE / filename
        payload = {**valid, **updates}
        _write_json(path, payload)

        result = run_submit_pending_promotion_review(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode="demo",
            capital_deployment_policy_path=policy_path,
            human_approval_path=path,
            now=_dt(EVALUATION_TIME),
        )
        candidate = _load_json(Path(result.promotion_candidate_path))

        assert result.status == "REVIEW_REQUIRED"
        assert expected in candidate["promotion_block_reasons"]
        assert candidate["submit_executed"] is False
        assert candidate["broker_write_performed"] is False


def test_phase15bk_pending_slot_non_empty_blocks_without_mutation(tmp_path):
    runtime_root, policy_path = _runtime_with_review_pending(tmp_path)
    valid = _valid_approval(runtime_root, policy_path)
    approval_path = runtime_root / "runtime_state" / "human_approval" / BUSINESS_DATE / "valid.json"
    _write_json(approval_path, valid)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    before = _load_json(pending_path)
    _write_json(pending_path, {**before, "state": "APPROVED", "active_pending": True})

    result = run_submit_pending_promotion_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        human_approval_path=approval_path,
        now=_dt(EVALUATION_TIME),
    )

    candidate = _load_json(Path(result.promotion_candidate_path))
    after = _load_json(pending_path)
    assert result.status == "REVIEW_REQUIRED"
    assert "pending_slot_not_empty" in candidate["promotion_block_reasons"]
    assert after["state"] == "APPROVED"
    assert after["active_pending"] is True
    assert candidate["apply_executed"] is False


def _runtime_with_review_pending(tmp_path: Path) -> tuple[Path, Path]:
    runtime_root = _review_only_runtime_with_4591(tmp_path)
    policy_path = _write_policy(tmp_path / "capital_deployment.json")
    current_path = runtime_root / "persistent_ledger" / "state.json"
    current = _load_json(current_path)
    current.update(
        {
            "asset_state_id": "asset-phase15bk",
            "position_state_as_of": BUSINESS_DATE,
            "valuation_as_of": BUSINESS_DATE,
            "current_position_status": "READY",
            "current_valuation_status": "READY",
        }
    )
    _write_json(current_path, current)
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "state": "EMPTY",
            "status": "EMPTY",
            "active_pending": False,
            "last_terminal_state": "EXPIRED",
        },
    )
    _write_json(
        runtime_root / "runtime_state" / "broker_readonly" / "latest.json",
        {
            "schema_version": "runtime_v2_broker_readonly_latest_v1",
            "business_date": BUSINESS_DATE,
            "runtime_business_date": BUSINESS_DATE,
            "snapshot_path": str(runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json"),
            "freshness_status": "READY",
            "authenticity_status": "READY",
            "account_alignment_status": "NOT_APPLICABLE",
            "read_only": True,
        },
    )
    _write_json(
        runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json",
        {
            "schema_version": "runtime_v2_broker_readonly_snapshot_v1",
            "positions": [
                {
                    "issue_code": "4591",
                    "quantity": "5000",
                    "available_quantity": "5000",
                    "data_origin": "BROKER_API",
                    "mock_used": False,
                    "fixture_used": False,
                    "read_only": True,
                }
            ],
        },
    )
    result = run_sell_hold_review_only_morning(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        feature_date=BUSINESS_DATE,
        now=_dt(EVALUATION_TIME),
    )
    return runtime_root, policy_path


def _valid_approval(runtime_root: Path, policy_path: Path) -> dict:
    result = run_submit_pending_promotion_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        now=_dt(EVALUATION_TIME),
    )
    return json.loads(Path(result.human_approval_path).read_text(encoding="utf-8"))


def _latest_manifest(runtime_root: Path) -> dict:
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / BUSINESS_DATE).glob("*.json"))
    return _load_json(manifests[-1])


def _dt(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))
