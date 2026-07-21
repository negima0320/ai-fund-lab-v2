from ai_fund_lab_v2.ai_lifecycle.at_latest_jquants_e2e_validation import (
    _au_stop_conditions,
    _final_judgment,
)


def test_phase19_at_final_judgment_blocks_au_when_runtime_inference_not_pass() -> None:
    final = _final_judgment(
        jquants_audit={"status": "PASS"},
        freshness={"status": "REVIEW_REQUIRED"},
        market_dataset={"status": "REVIEW_REQUIRED"},
        dataset_revision={"status": "PASS"},
        label_sufficiency={"status": "PASS"},
        retraining={"status": "PASS"},
        generation={"status": "PASS"},
        committed={"status": "PASS"},
        runtime_checks={
            "candidate": {"status": "REVIEW_REQUIRED"},
            "opportunity": {"status": "REVIEW_REQUIRED"},
        },
        buy_boundary={"status": "REVIEW_REQUIRED"},
        sell={"status": "PASS"},
        failures={"status": "PASS"},
        runtime_non_mutation={"status": "PASS", "runtime_pointer_write_count": 0},
        broker_non_mutation={"status": "PASS"},
    )

    assert final["judgment"] == "PHASE19_AT_REVIEW_REQUIRED"
    assert final["next_state"] == "PHASE19_AU_BLOCKED"
    assert final["acceptance"]["AT-8_candidate_runtime_inference"] == "REVIEW_REQUIRED"
    assert final["acceptance"]["AT-9_opportunity_runtime_inference"] == "REVIEW_REQUIRED"
    assert final["broker_write_count"] == 0


def test_phase19_at_au_stop_conditions_keep_manual_multi_day_blocked() -> None:
    payload = _au_stop_conditions()

    assert payload["status"] == "PASS"
    assert payload["au_readiness"] == "BLOCKED_UNTIL_PHASE19_AT_REVIEW_CLOSED"
    assert "Broker write attempted" in payload["stop_conditions"]

