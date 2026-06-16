from ai_fund_lab_v2.paper_trading.mandatory_step_tracker import MandatoryStepTracker


def test_mandatory_step_tracker_updates_status() -> None:
    tracker = MandatoryStepTracker()
    tracker = tracker.update("data_update", status="OK", reason="ready", artifact_refs=("manifest",))
    assert tracker.steps[0].name == "data_update"
    assert tracker.steps[0].status == "OK"
    assert tracker.steps[0].artifact_refs == ("manifest",)
    assert tracker.overall_status == "PENDING"


def test_mandatory_step_tracker_blocked_overall() -> None:
    tracker = MandatoryStepTracker().update("data_update", status="BLOCKED", reason="missing")
    assert tracker.overall_status == "BLOCKED"

