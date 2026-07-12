from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.pending_apply import run_authoritative_pending_apply_review
from ai_fund_lab_v2.runtime_v2.pending_promotion import run_submit_pending_promotion_review
from tests.runtime_v2.test_phase15aq_runtime_data_readiness_gate import BUSINESS_DATE, _load_json, _write_json
from tests.runtime_v2.test_phase15bk_submit_pending_promotion_contract import (
    EVALUATION_TIME,
    _dt,
    _latest_manifest,
    _runtime_with_review_pending,
)


def test_phase15bl_apply_candidate_ready_but_safety_blocked_without_pending_mutation(tmp_path):
    runtime_root, policy_path, promotion_path = _promotion_candidate(tmp_path)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    before_pending = pending_path.read_text(encoding="utf-8")

    result = run_authoritative_pending_apply_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        promotion_candidate_path=promotion_path,
        now=_dt(EVALUATION_TIME),
    )

    candidate = _load_json(Path(result.apply_candidate_path))
    after_pending = pending_path.read_text(encoding="utf-8")

    assert result.status == "PASS"
    assert candidate["apply_status"] == "READY_BUT_SAFETY_BLOCKED"
    assert candidate["apply_allowed"] is False
    assert candidate["apply_requested"] is False
    assert candidate["apply_executed"] is False
    assert candidate["authoritative_pending_mutated"] is False
    assert candidate["submit_executed"] is False
    assert candidate["broker_write_performed"] is False
    assert candidate["apply_block_reasons"] == ["safety_submit_blocked"]
    assert candidate["before_pending_snapshot"]["hash"] == candidate["after_pending_snapshot"]["hash"]
    assert candidate["authoritative_pending_candidate"]["candidate_only"] is True
    assert candidate["authoritative_pending_candidate"]["items"][0]["order_type"] == "REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY"
    assert before_pending == after_pending


def test_phase15bl_regular_cli_path_generates_apply_candidate_without_submit_or_pending_mutation(tmp_path):
    runtime_root, policy_path, promotion_path = _promotion_candidate(tmp_path)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    before_pending = pending_path.read_text(encoding="utf-8")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "authoritative_pending_apply_review",
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
            "--promotion-candidate-path",
            str(promotion_path),
            "--evaluation-time",
            EVALUATION_TIME,
        ]
    )

    manifest = _latest_manifest(runtime_root)
    candidate = _load_json(Path(manifest["authoritative_pending_apply_candidate_path"]))
    after_pending = pending_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert manifest["authoritative_pending_apply_review_status"] == "PASS"
    assert manifest["apply_candidate_status"] == "READY_BUT_SAFETY_BLOCKED"
    assert manifest["submit_executed"] is False
    assert manifest["broker_write_performed"] is False
    assert manifest["authoritative_pending_mutated"] is False
    assert candidate["apply_executed"] is False
    assert before_pending == after_pending


def test_phase15bl_promotion_candidate_alone_or_missing_approval_blocks_apply(tmp_path):
    runtime_root, policy_path, promotion_path = _promotion_candidate(tmp_path)
    promotion = _load_json(promotion_path)
    broken_path = promotion_path.parent / "promotion-candidate-missing-approval.json"
    promotion.update({"approval_path": str(runtime_root / "runtime_state" / "human_approval" / BUSINESS_DATE / "missing.json")})
    _write_json(broken_path, promotion)

    result = run_authoritative_pending_apply_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        promotion_candidate_path=broken_path,
        now=_dt(EVALUATION_TIME),
    )
    candidate = _load_json(Path(result.apply_candidate_path))

    assert result.status == "REVIEW_REQUIRED"
    assert "human_approval_schema_invalid" in candidate["apply_block_reasons"]
    assert candidate["apply_executed"] is False


def test_phase15bl_expired_revoked_or_consumed_approval_blocks_apply(tmp_path):
    runtime_root, policy_path, promotion_path = _promotion_candidate(tmp_path)
    promotion = _load_json(promotion_path)
    approval_path = Path(promotion["approval_path"])
    approval = _load_json(approval_path)

    for filename, updates, expected in (
        ("expired.json", {"expires_at": "2026-07-11T00:00:00+00:00"}, "approval_expired"),
        ("revoked.json", {"revoked_at": "2026-07-11T12:00:00+00:00"}, "approval_revoked"),
        ("consumed.json", {"approval_consumed": True}, "approval_already_consumed"),
    ):
        next_approval_path = approval_path.parent / filename
        next_approval = {**approval, **updates}
        _write_json(next_approval_path, next_approval)
        next_promotion_path = promotion_path.parent / f"promotion-candidate-{filename}"
        next_promotion = {**promotion, "approval_path": str(next_approval_path), "approval_hash": _hash_json(next_approval)}
        _write_json(next_promotion_path, next_promotion)

        result = run_authoritative_pending_apply_review(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode="demo",
            capital_deployment_policy_path=policy_path,
            promotion_candidate_path=next_promotion_path,
            now=_dt(EVALUATION_TIME),
        )
        candidate = _load_json(Path(result.apply_candidate_path))

        assert result.status == "REVIEW_REQUIRED"
        assert expected in candidate["apply_block_reasons"]
        assert candidate["authoritative_pending_mutated"] is False


def test_phase15bl_hash_policy_safety_current_broker_target_mismatch_blocks_apply(tmp_path):
    runtime_root, policy_path, promotion_path = _promotion_candidate(tmp_path)
    cases = (
        ("candidate_hash.json", {"candidate_hash": "sha256:wrong"}, "promotion_candidate_hash_mismatch"),
        ("approval_hash.json", {"approval_hash": "sha256:wrong"}, "approval_hash_mismatch"),
        ("policy_hash.json", {"policy_hash": "sha256:wrong"}, "policy_hash_mismatch"),
        ("safety.json", {"safety_decision_id": "wrong-safety"}, "safety_decision_id_mismatch"),
        ("current.json", {"current_state_id": "wrong-current"}, "current_state_id_mismatch"),
        ("broker.json", {"broker_snapshot_id": "wrong-broker"}, "broker_snapshot_id_mismatch"),
        ("target.json", {"target_session": "2026-07-09"}, "target_session_mismatch"),
    )
    original = _load_json(promotion_path)
    for filename, updates, expected in cases:
        path = promotion_path.parent / f"promotion-candidate-{filename}"
        _write_json(path, {**original, **updates})

        result = run_authoritative_pending_apply_review(
            runtime_root=runtime_root,
            business_date=BUSINESS_DATE,
            mode="demo",
            capital_deployment_policy_path=policy_path,
            promotion_candidate_path=path,
            now=_dt(EVALUATION_TIME),
        )
        candidate = _load_json(Path(result.apply_candidate_path))

        assert result.status == "REVIEW_REQUIRED"
        assert expected in candidate["apply_block_reasons"]
        assert candidate["submit_executed"] is False


def test_phase15bl_pending_non_empty_blocks_without_mutation(tmp_path):
    runtime_root, policy_path, promotion_path = _promotion_candidate(tmp_path)
    pending_path = runtime_root / "pending_order_plan" / "pending_order_plan.json"
    pending = _load_json(pending_path)
    _write_json(pending_path, {**pending, "state": "APPROVED", "active_pending": True})
    before_pending = pending_path.read_text(encoding="utf-8")

    result = run_authoritative_pending_apply_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        promotion_candidate_path=promotion_path,
        now=_dt(EVALUATION_TIME),
    )
    candidate = _load_json(Path(result.apply_candidate_path))
    after_pending = pending_path.read_text(encoding="utf-8")

    assert result.status == "REVIEW_REQUIRED"
    assert "pending_slot_not_empty" in candidate["apply_block_reasons"]
    assert candidate["authoritative_pending_mutated"] is False
    assert before_pending == after_pending


def test_phase15bl_broker_stale_and_duplicate_candidate_block_apply(tmp_path):
    runtime_root, policy_path, promotion_path = _promotion_candidate(tmp_path)
    broker_latest_path = runtime_root / "runtime_state" / "broker_readonly" / "latest.json"
    broker_latest = _load_json(broker_latest_path)
    _write_json(broker_latest_path, {**broker_latest, "freshness_status": "STALE"})

    stale_result = run_authoritative_pending_apply_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        promotion_candidate_path=promotion_path,
        now=_dt(EVALUATION_TIME),
    )
    stale_candidate = _load_json(Path(stale_result.apply_candidate_path))

    assert stale_result.status == "REVIEW_REQUIRED"
    assert "broker_not_ready" in stale_candidate["apply_block_reasons"]
    assert stale_candidate["authoritative_pending_mutated"] is False

    _write_json(broker_latest_path, broker_latest)
    promotion = _load_json(promotion_path)
    duplicate_path = promotion_path.parent / "promotion-candidate-already-applied.json"
    _write_json(duplicate_path, {**promotion, "apply_executed": True})

    duplicate_result = run_authoritative_pending_apply_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        promotion_candidate_path=duplicate_path,
        now=_dt(EVALUATION_TIME),
    )
    duplicate_candidate = _load_json(Path(duplicate_result.apply_candidate_path))

    assert duplicate_result.status == "REVIEW_REQUIRED"
    assert "promotion_candidate_already_applied" in duplicate_candidate["apply_block_reasons"]
    assert duplicate_candidate["submit_executed"] is False


def _promotion_candidate(tmp_path: Path) -> tuple[Path, Path, Path]:
    runtime_root, policy_path = _runtime_with_review_pending(tmp_path)
    result = run_submit_pending_promotion_review(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        capital_deployment_policy_path=policy_path,
        now=_dt(EVALUATION_TIME),
    )
    return runtime_root, policy_path, Path(result.promotion_candidate_path)


def _hash_json(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    import hashlib

    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
