import json
from pathlib import Path

from ai_fund_lab_v2.order_manager.safety_report_links import write_order_manager_safety_links


def test_safety_report_links_writes_json_and_markdown(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".runtime"
    safety_dir = runtime_dir / "safety" / "reports"
    safety_dir.mkdir(parents=True)
    safety_report = safety_dir / "safety_report.json"
    safety_report.write_text("{}", encoding="utf-8")

    path = write_order_manager_safety_links(
        plan_id="plan1",
        runtime_dir=runtime_dir,
        order_plan_path=runtime_dir / "order_manager" / "plans" / "plan1.json",
        reconciliation_id="recon1",
        paper_ledger_path=runtime_dir / "order_manager" / "paper" / "ledgers" / "ledger.json",
        dry_run_report_path=runtime_dir / "order_manager" / "audit" / "report.md",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["plan_id"] == "plan1"
    assert payload["safety_dry_run_report_path"] == str(safety_report)
    assert path.with_suffix(".md").exists()
