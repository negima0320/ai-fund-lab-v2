from pathlib import Path

from ai_fund_lab_v2.logging import configure_runtime_logger


def test_logger_writes_under_runtime_log_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "runtime" / "logs"
    logger = configure_runtime_logger("test.phase1a", log_dir, "phase1a.log")

    logger.info("hello")

    log_file = log_dir / "phase1a.log"
    assert log_file.exists()
    assert "hello" in log_file.read_text(encoding="utf-8")
