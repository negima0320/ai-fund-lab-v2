from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402


PHASE = "Phase4-A Candidate AI Design"
PYTEST_HINT = "python3 -m pytest tests/test_phase4a_candidate_ai_design.py && python3 scripts/audit_phase4a_candidate_ai_design.py"

DESIGN_DOC = ROOT / "docs/03_ai_design/candidate_ai_design.md"
FEATURE_CATALOG = ROOT / "docs/03_ai_design/candidate_feature_catalog.md"
PHASE_REPORT = ROOT / "docs/phase_reports/phase4a_candidate_ai_design.md"

REQUIRED_DOCS = (
    ROOT / "docs/00_vision/investment_philosophy.md",
    ROOT / "docs/01_requirements/system_requirements.md",
    ROOT / "docs/01_requirements/success_metrics.md",
    ROOT / "docs/01_requirements/phase_roadmap.md",
    ROOT / "docs/02_architecture/system_architecture.md",
    DESIGN_DOC,
    FEATURE_CATALOG,
)

FORBIDDEN_DATA = (
    "future_return_*",
    "future_max_return_*",
    "future_max_drawdown_*",
    "top_decile_*",
    "downside_bad_*",
    "backtest result",
    "trade result",
    "selected",
    "bought",
    "sold",
    "cash",
    "portfolio",
    "annual_return",
    "final_assets",
)

REQUIRED_DESIGN_SECTIONS = (
    "入力",
    "出力",
    "成功条件",
    "失敗条件",
    "学習データ",
    "推論フロー",
    "監査方針",
    "利用可能",
    "利用禁止",
    "責務境界",
)

PROHIBITED_IMPLEMENTATION_TERMS = (
    "Candidate AI本体",
    "feature builder本体",
    "学習処理",
    "推論処理",
    "バックテスト",
    "Historical Evaluation",
    "Paper Trading",
    "発注",
)


def run_audit(
    json_report_path: Path | str = "reports/phase_reports/phase4a_candidate_ai_design_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4a_candidate_ai_design_audit.md",
) -> dict[str, Any]:
    design_text = _read(DESIGN_DOC)
    catalog_text = _read(FEATURE_CATALOG)
    report_text = _read(PHASE_REPORT)
    combined_design_text = "\n".join([design_text, catalog_text, report_text])

    checks = {
        "required_docs_present": all(path.is_file() for path in REQUIRED_DOCS),
        "phase4a_report_present": PHASE_REPORT.is_file(),
        "candidate_feature_catalog_present": FEATURE_CATALOG.is_file(),
        "candidate_scope_limited_to_extraction": _contains_any(
            combined_design_text,
            ("全銘柄から「見る価値がある上昇候補」を抽出する", "見る価値がある銘柄を抽出する"),
        )
        and "上昇候補抽出" in combined_design_text,
        "does_not_invade_downstream_responsibilities": _downstream_boundary_present(combined_design_text),
        "required_design_items_present": all(item in combined_design_text for item in REQUIRED_DESIGN_SECTIONS),
        "forbidden_data_list_present": all(item in combined_design_text for item in FORBIDDEN_DATA),
        "daily_quotes_normalized_present": "daily_quotes_normalized" in combined_design_text,
        "no_training_inference_backtest_paper_ordering": _phase4a_non_implementation_boundary_present(combined_design_text),
        "future_labels_not_features": "評価ラベルとしてのみ" in combined_design_text and "feature table" in combined_design_text,
        "audit_policy_present": "leakage" in combined_design_text and "candidate_reason" in combined_design_text,
        "no_candidate_ai_code_added": _no_candidate_ai_code_added(),
    }
    status = "complete" if all(checks.values()) else "incomplete"
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": status,
            "checks": checks,
            "pytest_hint": PYTEST_HINT,
            "reports": {
                "json": str(json_report_path),
                "markdown": str(markdown_report_path),
            },
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-A Candidate AI design criteria.")
    parser.add_argument(
        "--json-report",
        default="reports/phase_reports/phase4a_candidate_ai_design_audit.json",
        help="JSON report output path.",
    )
    parser.add_argument(
        "--markdown-report",
        default="docs/phase_reports/phase4a_candidate_ai_design_audit.md",
        help="Markdown report output path.",
    )
    args = parser.parse_args(argv)
    result = run_audit(json_report_path=Path(args.json_report), markdown_report_path=Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _downstream_boundary_present(text: str) -> bool:
    required = (
        "買うかどうかを決める",
        "期待値順位",
        "購入金額",
        "保有判断",
        "売却判断",
        "Capital Allocation",
        "Paper Trading",
        "発注",
        "Phase5 Opportunity AI",
        "Phase6 Position Management AI",
        "Phase7 Capital Allocation",
        "Phase8 Order Manager",
        "Phase9 Paper Trading",
    )
    return all(item in text for item in required)


def _phase4a_non_implementation_boundary_present(text: str) -> bool:
    return all(item in text for item in PROHIBITED_IMPLEMENTATION_TERMS) and "Phase4-Aでは設計のみ" in text


def _no_candidate_ai_code_added() -> bool:
    src_root = ROOT / "src/ai_fund_lab_v2"
    source_text = _concat_files(src_root / "candidate_ai", "*.py")
    blocked_code_terms = (
        "def train",
        "def predict",
        "def fit",
        "def backtest",
        "def place_order",
        "def submit_order",
        "class CandidateAI(",
        "class CandidateAI:",
        "JQuantsClient",
        "MarketDataStore",
        "read_parquet",
        "read_csv",
    )
    return all(term not in source_text for term in blocked_code_terms)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _concat_files(directory: Path, pattern: str) -> str:
    if not directory.is_dir():
        return ""
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(directory.glob(pattern)))


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Fund Lab vNext Phase4-A Candidate AI Design Audit",
        "",
        "## Audit Result",
        "",
        f"- phase: `{payload['phase']}`",
        f"- status: `{payload['status']}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- `{name}`: {'OK' if passed else 'NG'}" for name, passed in sorted(payload["checks"].items()))
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "Phase4-A is a design-only step. Candidate AI is limited to extracting upward-momentum candidates from all stocks.",
            "Training, inference, backtest, Paper Trading, ordering, broker live access, and portfolio auto-update are not implemented.",
            "",
            "## pytest",
            "",
            f"`{payload['pytest_hint']}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
