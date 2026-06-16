from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.daily_run_result import DailyCandidate, DailyPosition, DailyRunResult
from ai_fund_lab_v2.paper_trading.reporting.blog_draft_writer import write_blog_draft
from ai_fund_lab_v2.paper_trading.reporting.internal_daily_report_writer import write_internal_daily_report
from ai_fund_lab_v2.paper_trading.reporting.public_confidence_mapper import map_candidate_public_confidence
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import check_public_report_redaction
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest


def run_audit(*, output_root: Path) -> dict[str, object]:
    manifest = sample_manifest()
    result = sample_result()
    internal_md, internal_json = write_internal_daily_report(
        manifest=manifest,
        result=result,
        reports_dir=output_root / "reports" / "phase9" / "daily",
    )
    public_md = write_public_daily_report(
        manifest=manifest,
        result=result,
        reports_dir=output_root / "reports" / "public" / "phase9_daily",
    )
    blog_md = write_blog_draft(
        manifest=manifest,
        result=result,
        reports_dir=output_root / "reports" / "public" / "phase9_daily",
    )
    confidence = map_candidate_public_confidence(result.buy_candidates[0].to_dict(), safety_status=manifest.safety_status)
    public_check = check_public_report_redaction(public_md.read_text(encoding="utf-8"))
    blog_check = check_public_report_redaction(blog_md.read_text(encoding="utf-8"))
    summary = {
        "phase": "Phase9-B",
        "status": "PASS"
        if all(
            [
                internal_md.exists(),
                internal_json.exists(),
                public_md.exists(),
                blog_md.exists(),
                confidence.public_confidence_score == 81,
                public_check.ready,
                blog_check.ready,
            ]
        )
        else "FAIL",
        "internal_report_generated": internal_md.exists() and internal_json.exists(),
        "public_report_generated": public_md.exists(),
        "blog_draft_generated": blog_md.exists(),
        "confidence_score_generated": confidence.public_confidence_score,
        "redaction_checker_public": public_check.to_dict(),
        "redaction_checker_blog": blog_check.to_dict(),
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "paper_ledger_fill_executed": False,
        "paths": {
            "internal_md": str(internal_md),
            "internal_json": str(internal_json),
            "public_md": str(public_md),
            "blog_md": str(blog_md),
        },
    }
    audit_path = output_root / "reports" / "phase_reports" / "phase9b_report_framework_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def sample_manifest() -> DailyRunManifest:
    return DailyRunManifest(
        run_date="2026-06-16",
        data_until="2026-06-16",
        train_until="2026-06-12",
        decision_for="2026-06-16",
        virtual_order_date="2026-06-17",
        virtual_execution_date="2026-06-17",
        safety_status="OK",
        human_review_status="pending",
        report_status="OK",
    )


def sample_result() -> DailyRunResult:
    return DailyRunResult(
        buy_candidates=(
            DailyCandidate(
                issue_code="7203",
                issue_name="Toyota Motor",
                side="BUY",
                public_confidence_score=81,
                short_reason="トレンドと流動性が比較的良好です。",
                caution_note="仮想運用での検証中です。",
            ),
        ),
        sell_candidates=(DailyCandidate(issue_code="6758", issue_name="Sony Group", side="SELL", public_confidence_score=44),),
        hold_candidates=(DailyCandidate(issue_code="9432", issue_name="NTT", side="HOLD", public_confidence_score=66),),
        cash=Decimal("250000"),
        positions=(DailyPosition(issue_code="9432", issue_name="NTT", quantity=Decimal("100"), market_value=Decimal("16000")),),
        total_equity=Decimal("1016000"),
        realized_pnl=Decimal("12000"),
        unrealized_pnl=Decimal("4000"),
        trade_count=3,
        safety_state={"status": "OK"},
        review_state={"status": "pending"},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-B report framework.")
    parser.add_argument("--output-root", default=".")
    args = parser.parse_args(argv)
    summary = run_audit(output_root=Path(args.output_root))
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

