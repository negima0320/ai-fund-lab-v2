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


PHASE = "Phase4-B Candidate Training Data Design"
PYTEST_HINT = (
    "python3 scripts/audit_phase4b_candidate_training_data_design.py && "
    "python3 -m pytest tests/test_phase4b_candidate_training_data_design.py && "
    "python3 -m pytest -q"
)

DESIGN_DOC = ROOT / "docs/03_ai_design/candidate_training_data_design.md"
PHASE_REPORT = ROOT / "docs/phase_reports/phase4b_candidate_training_data_design.md"

REQUIRED_INPUT_DOCS = (
    ROOT / "docs/00_vision/investment_philosophy.md",
    ROOT / "docs/01_requirements/system_requirements.md",
    ROOT / "docs/01_requirements/success_metrics.md",
    ROOT / "docs/01_requirements/phase_roadmap.md",
    ROOT / "docs/02_architecture/system_architecture.md",
    ROOT / "docs/03_ai_design/candidate_ai_design.md",
    ROOT / "docs/03_ai_design/candidate_feature_catalog.md",
    ROOT / "docs/phase_reports/phase4a_candidate_ai_design.md",
    ROOT / "reports/phase_reports/phase4a_candidate_ai_design_audit.json",
)

FORBIDDEN_FEATURES = (
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
    "paper_trade",
    "position",
    "allocation",
    "order",
    "execution",
    "profit",
    "loss",
    "pnl",
)

NON_IMPLEMENTED_ITEMS = (
    "feature builder本体",
    "dataset builder本体",
    "label生成本体",
    "Candidate AI本体",
    "学習処理",
    "推論処理",
    "バックテスト",
    "Historical Evaluation",
    "Paper Trading",
    "発注",
)


def run_audit(
    json_report_path: Path | str = "reports/phase_reports/phase4b_candidate_training_data_design_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4b_candidate_training_data_design_audit.md",
) -> dict[str, Any]:
    design_text = _read(DESIGN_DOC)
    report_text = _read(PHASE_REPORT)
    combined_text = "\n".join([design_text, report_text])

    checks = {
        "required_input_docs_present": all(path.is_file() for path in REQUIRED_INPUT_DOCS),
        "phase4b_design_doc_present": DESIGN_DOC.is_file(),
        "phase4b_report_present": PHASE_REPORT.is_file(),
        "feature_table_schema_present": _all_present(combined_text, ("feature table schema", "target_date", "as_of_date", "feature_version")),
        "label_table_schema_present": _all_present(
            combined_text,
            ("label table schema", "future_return_5d", "future_max_return_20d", "momentum_candidate_label"),
        ),
        "training_dataset_schema_present": _all_present(combined_text, ("training dataset schema", "dataset_version", "split")),
        "audit_table_schema_present": _all_present(
            combined_text,
            ("audit table schema", "leakage_check_status", "forbidden_feature_detected", "future_label_isolated"),
        ),
        "as_of_date_rule_present": "featureは as_of_date 時点で観測可能な情報のみで作る" in combined_text
        and "as_of_date <= target_date" in combined_text,
        "target_date_rule_present": "target_date rule" in combined_text and "target_date より後" in combined_text,
        "lookback_window_rule_present": "lookback window rule" in combined_text and "5営業日" in combined_text and "60営業日" in combined_text,
        "future_label_isolation_present": "future label isolation" in combined_text and "feature table とは物理的・論理的に分離" in combined_text,
        "time_series_split_present": _all_present(combined_text, ("Train:", "Validation:", "Test:", "2021-06", "2024-12", "2025-01", "2026-01")),
        "random_split_forbidden": "ランダム分割は禁止" in combined_text,
        "forbidden_features_present": all(item in combined_text for item in FORBIDDEN_FEATURES),
        "candidate_boundary_present": _candidate_boundary_present(combined_text),
        "non_implementation_boundary_present": all(item in combined_text for item in NON_IMPLEMENTED_ITEMS)
        and "Phase4-Bでは設計のみ" in combined_text,
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
    parser = argparse.ArgumentParser(description="Audit Phase4-B Candidate Training Data Design criteria.")
    parser.add_argument(
        "--json-report",
        default="reports/phase_reports/phase4b_candidate_training_data_design_audit.json",
        help="JSON report output path.",
    )
    parser.add_argument(
        "--markdown-report",
        default="docs/phase_reports/phase4b_candidate_training_data_design_audit.md",
        help="Markdown report output path.",
    )
    args = parser.parse_args(argv)
    result = run_audit(Path(args.json_report), Path(args.markdown_report))
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == "complete" else 1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _all_present(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle in text for needle in needles)


def _candidate_boundary_present(text: str) -> bool:
    return _all_present(
        text,
        (
            "全銘柄から見る価値がある上昇候補を抽出する",
            "candidate_scoreを出す",
            "candidate_reasonを出す",
            "excluded_reasonを出す",
            "買い判断",
            "売却判断",
            "資金配分",
            "Portfolio更新",
        ),
    )


def _no_candidate_ai_code_added() -> bool:
    src_root = ROOT / "src/ai_fund_lab_v2"
    source_text = _concat_files(src_root / "candidate_ai", "*.py")
    blocked_code_terms = (
        "def build_dataset",
        "def generate_labels",
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


def _concat_files(directory: Path, pattern: str) -> str:
    if not directory.is_dir():
        return ""
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(directory.glob(pattern)))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AI Fund Lab vNext Phase4-B Candidate Training Data Design Audit",
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
            "Phase4-B is a design-only step. It fixes Candidate AI training data schemas, future-label isolation, time-series split, and leakage audit rules.",
            "Feature builder, dataset builder, label generation, training, inference, backtest, Paper Trading, ordering, broker live access, and portfolio auto-update are not implemented.",
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
