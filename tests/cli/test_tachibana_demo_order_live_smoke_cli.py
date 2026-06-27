from __future__ import annotations

import json

from ai_fund_lab_v2.cli.tachibana_demo_order_live_smoke import main


def test_cli_default_skipped(tmp_path, capsys) -> None:
    code = main(["--reports-dir", str(tmp_path)])

    output = json.loads(capsys.readouterr().out)
    assert code == 0
    assert output["status"] == "SKIPPED"
    assert output["executed"] is False


def test_cli_blocks_without_dry_run(tmp_path, capsys) -> None:
    code = main(["--reports-dir", str(tmp_path), "--run-demo-order-live-smoke"])

    output = json.loads(capsys.readouterr().out)
    assert code == 1
    assert output["status"] == "BLOCKED_LIVE_SUBMIT_NOT_IMPLEMENTED"
    assert output["executed"] is False
