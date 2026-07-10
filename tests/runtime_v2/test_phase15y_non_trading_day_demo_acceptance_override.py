import json
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.notification.payload import build_notification_payload_from_summary

from tests.runtime_v2.test_phase15h_capital_deployment_policy import _write_runtime_state


NON_TRADING_DAY = "2026-09-21"
TRADING_DAY = "2026-07-09"


def test_phase15y_production_override_forbidden(tmp_path):
    runtime_root = _write_runtime_state(tmp_path / ".runtime", positions=[])

    exit_code = _run_daily_rehearsal(
        tmp_path,
        runtime_root,
        business_date=NON_TRADING_DAY,
        mode="production",
        allow_override=True,
    )

    manifest = _latest_manifest(runtime_root, NON_TRADING_DAY)
    assert exit_code == 10
    assert manifest["final_state"] == "BLOCKED"
    assert manifest["reason"] == "non_trading_day_demo_override_forbidden_in_production"
    assert manifest["non_trading_day_demo_override"] is False
    assert manifest["override_reason"] == "non_trading_day_demo_override_forbidden_in_production"
    assert manifest["production_equivalent"] is False
    assert manifest["prohibited_actions"]["demo_submit_executed"] is False
    assert manifest["prohibited_actions"]["production_order_executed"] is False


def test_phase15y_demo_non_trading_day_without_override_stops(tmp_path):
    runtime_root = _write_runtime_state(tmp_path / ".runtime", positions=[])

    exit_code = _run_daily_rehearsal(
        tmp_path,
        runtime_root,
        business_date=NON_TRADING_DAY,
        mode="demo",
        allow_override=False,
    )

    manifest = _latest_manifest(runtime_root, NON_TRADING_DAY)
    assert exit_code == 20
    assert manifest["final_state"] == "REVIEW_REQUIRED"
    assert manifest["reason"] == "non_trading_day"
    assert manifest["business_day"] is False
    assert manifest["market_open"] is False
    assert manifest["non_trading_day_demo_override"] is False
    assert manifest["production_equivalent"] is False


def test_phase15y_demo_non_trading_day_with_override_allowed_as_demo_acceptance(tmp_path):
    runtime_root = _write_runtime_state(tmp_path / ".runtime", positions=[])

    exit_code = _run_daily_rehearsal(
        tmp_path,
        runtime_root,
        business_date=NON_TRADING_DAY,
        mode="demo",
        allow_override=True,
    )

    manifest = _latest_manifest(runtime_root, NON_TRADING_DAY)
    assert exit_code == 0
    assert manifest["business_day"] is False
    assert manifest["market_open"] is False
    assert manifest["non_trading_day_demo_override"] is True
    assert manifest["override_source"] == "operator_cli"
    assert manifest["override_reason"] == "demo_acceptance_non_trading_day"
    assert manifest["production_equivalent"] is False
    assert manifest["acceptance_scope"] == "demo_acceptance_only"


def test_phase15y_trading_day_with_override_does_not_change_normal_behavior(tmp_path):
    runtime_root = _write_runtime_state(tmp_path / ".runtime", positions=[])

    exit_code = _run_daily_rehearsal(
        tmp_path,
        runtime_root,
        business_date=TRADING_DAY,
        mode="demo",
        allow_override=True,
    )

    manifest = _latest_manifest(runtime_root, TRADING_DAY)
    assert exit_code == 0
    assert manifest["business_day"] is True
    assert manifest["market_open"] is True
    assert manifest["non_trading_day_demo_override"] is False
    assert manifest["override_reason"] == "trading_day_override_not_applicable"
    assert manifest["production_equivalent"] is True
    assert manifest["acceptance_scope"] == "regular_runtime"


def test_phase15y_manifest_report_notification_propagate_override(tmp_path):
    runtime_root = _write_runtime_state(tmp_path / ".runtime", positions=[])

    assert (
        _run_daily_rehearsal(
            tmp_path,
            runtime_root,
            business_date=NON_TRADING_DAY,
            mode="demo",
            allow_override=True,
        )
        == 0
    )

    report_json = _load_json(tmp_path / "reports" / "runtime_v2" / NON_TRADING_DAY / "runtime_report.json")
    notification_payload = _load_json(
        tmp_path / "reports" / "runtime_v2" / NON_TRADING_DAY / "notification_payload.json"
    )
    payload_model = build_notification_payload_from_summary(
        summary=report_json,
        channel="line",
        source_report_id="phase15y-report",
    )

    assert report_json["non_trading_day_demo_override"]["non_trading_day_demo_override"] is True
    assert report_json["non_trading_day_demo_override"]["production_equivalent"] is False
    assert report_json["non_trading_day_demo_override"]["acceptance_scope"] == "demo_acceptance_only"
    assert notification_payload["non_trading_day_demo_override"] is True
    assert notification_payload["production_equivalent"] is False
    assert notification_payload["acceptance_scope"] == "demo_acceptance_only"
    assert payload_model.non_trading_day_demo_override is True
    assert payload_model.production_equivalent is False
    assert payload_model.acceptance_scope == "demo_acceptance_only"


def test_phase15y_launchd_plists_do_not_include_override():
    for plist in Path("tools/launchd").glob("*.plist"):
        assert "--allow-non-trading-day-demo" not in plist.read_text(encoding="utf-8")


def _run_daily_rehearsal(
    tmp_path: Path,
    runtime_root: Path,
    *,
    business_date: str,
    mode: str,
    allow_override: bool,
) -> int:
    args = [
        "--mode",
        mode,
        "--job",
        "daily_rehearsal",
        "--business-date",
        business_date,
        "--submit-enabled",
        "false",
        "--notification-mode",
        "payload-only",
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
    ]
    if allow_override:
        args.append("--allow-non-trading-day-demo")
    return main(args)


def _latest_manifest(runtime_root: Path, business_date: str):
    manifests = sorted((runtime_root / "runtime_state" / "run_manifest" / business_date).glob("*.json"))
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
