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


PHASE = "Phase4-C Candidate Feature Builder Design"
PYTEST_HINT = (
    "python3 scripts/audit_phase4c_candidate_feature_builder_design.py && "
    "python3 -m pytest tests/test_phase4c_candidate_feature_builder_design.py && "
    "python3 -m pytest -q"
)

DESIGN_DOC = ROOT / "docs/03_ai_design/candidate_feature_builder_design.md"
PHASE_REPORT = ROOT / "docs/phase_reports/phase4c_candidate_feature_builder_design.md"

REQUIRED_INPUT_DOCS = (
    ROOT / "docs/00_vision/investment_philosophy.md",
    ROOT / "docs/01_requirements/system_requirements.md",
    ROOT / "docs/01_requirements/success_metrics.md",
    ROOT / "docs/01_requirements/phase_roadmap.md",
    ROOT / "docs/02_architecture/system_architecture.md",
    ROOT / "docs/03_ai_design/candidate_ai_design.md",
    ROOT / "docs/03_ai_design/candidate_feature_catalog.md",
    ROOT / "docs/03_ai_design/candidate_training_data_design.md",
    ROOT / "docs/phase_reports/phase4a_candidate_ai_design.md",
    ROOT / "docs/phase_reports/phase4b_candidate_training_data_design.md",
    ROOT / "reports/phase_reports/phase4a_candidate_ai_design_audit.json",
    ROOT / "reports/phase_reports/phase4b_candidate_training_data_design_audit.json",
)

FORBIDDEN_FEATURES = (
    "future_return_*",
    "future_max_return_*",
    "future_max_drawdown_*",
    "top_decile_*",
    "downside_bad_*",
    "momentum_candidate_label",
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
    json_report_path: Path | str = "reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4c_candidate_feature_builder_design_audit.md",
) -> dict[str, Any]:
    design_text = _read(DESIGN_DOC)
    report_text = _read(PHASE_REPORT)
    combined_text = "\n".join([design_text, report_text])

    checks = {
        "required_input_docs_present": all(path.is_file() for path in REQUIRED_INPUT_DOCS),
        "phase4c_design_doc_present": DESIGN_DOC.is_file(),
        "phase4c_report_present": PHASE_REPORT.is_file(),
        "feature_builder_responsibility_present": _all_present(
            combined_text,
            ("Feature Builder Responsibility", "as_of_date時点で観測可能な市場データだけを使い"),
        ),
        "input_source_present": _all_present(
            combined_text,
            ("Input Source", "daily_quotes_normalized", "listed issue master", "trading calendar", "fins_summary"),
        ),
        "output_schema_present": _all_present(
            combined_text,
            ("Output Schema", "universe_eligible", "excluded_reason", "price_momentum_*", "missing_flags_*"),
        ),
        "feature_category_present": _all_present(
            combined_text,
            ("price momentum features", "volume momentum features", "market regime features", "universe eligibility features"),
        ),
        "daily_quotes_normalized_core_input": "中心入力" in combined_text and "daily_quotes_normalized" in combined_text,
        "as_of_date_only_rule_present": "featureはas_of_date時点で見えている情報のみで生成する" in combined_text,
        "lookback_past_only_present": "lookback windowはas_of_dateから過去方向のみ" in combined_text
        and "target_date以降のデータ参照禁止" in combined_text,
        "fins_publication_date_rule_present": _all_present(
            combined_text,
            ("fins_summary publication date rule", "disclosed_date <= as_of_date", "period end dateのみで結合しない"),
        ),
        "market_index_sector_rule_present": _all_present(
            combined_text,
            ("Market Index Feature Rule", "Sector Aggregation Rule", "as_of_date以前"),
        ),
        "missing_value_rule_present": _all_present(
            combined_text,
            ("Missing Value Rule", "必要最小window不足はexcluded_reason", "missing_flags"),
        ),
        "universe_filter_rule_present": _all_present(
            combined_text,
            ("Universe Filter Rule", "上場廃止済み", "流動性不足", "買い判断ではない"),
        ),
        "feature_version_rule_present": _all_present(
            combined_text,
            ("Feature Version Rule", "feature_version", "計算式の変更", "thresholdの変更"),
        ),
        "runtime_output_path_present": _all_present(
            combined_text,
            (
                "Runtime Output Path",
                ".runtime/candidate_ai/features/",
                ".runtime/candidate_ai/manifests/",
                ".runtime/candidate_ai/audit/",
            ),
        ),
        "manifest_audit_integration_present": _all_present(
            combined_text,
            ("Manifest / Audit Integration", "manifest_id", "audit_id", "leakage_audit_status"),
        ),
        "leakage_audit_rule_present": _all_present(
            combined_text,
            (
                "Leakage Audit Rule",
                "feature列名にfuture/top_decile/downside/label/pnl/profit/loss等が含まれる",
                "fins_summaryが公開日前に結合される",
                "backtest/trade/portfolio/cash/order系列が混入する",
            ),
        ),
        "mock_fixture_design_present": _all_present(
            combined_text,
            ("Mock Fixture Design", "daily_quotes_normalized fixture", "fins_summary disclosed_date > as_of_date"),
        ),
        "forbidden_features_present": all(item in combined_text for item in FORBIDDEN_FEATURES),
        "candidate_boundary_present": _candidate_boundary_present(combined_text),
        "non_implementation_boundary_present": all(item in combined_text for item in NON_IMPLEMENTED_ITEMS)
        and "Phase4-Cでは設計のみ" in combined_text,
        "no_candidate_feature_builder_code_added": _no_candidate_feature_builder_code_added(),
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
    parser = argparse.ArgumentParser(description="Audit Phase4-C Candidate Feature Builder Design criteria.")
    parser.add_argument(
        "--json-report",
        default="reports/phase_reports/phase4c_candidate_feature_builder_design_audit.json",
        help="JSON report output path.",
    )
    parser.add_argument(
        "--markdown-report",
        default="docs/phase_reports/phase4c_candidate_feature_builder_design_audit.md",
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


def _no_candidate_feature_builder_code_added() -> bool:
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
        "fins_summary",
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
        "# AI Fund Lab vNext Phase4-C Candidate Feature Builder Design Audit",
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
            "Phase4-C is a design-only step. It fixes Candidate Feature Builder responsibility, input sources, output schema, runtime paths, manifest/audit integration, and leakage audit rules.",
            "Feature builder body, dataset builder, label generation, training, inference, backtest, Paper Trading, ordering, broker live access, and portfolio auto-update are not implemented.",
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
