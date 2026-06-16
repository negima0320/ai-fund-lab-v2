from pathlib import Path


def test_scheduler_templates_exist_and_do_not_auto_install() -> None:
    root = Path("ops/scheduler")
    plist = root / "com.aifundlab.phase9.daily.plist.template"
    cron = root / "phase9_daily_cron.example"
    readme = root / "README_phase9_scheduler.md"
    assert plist.exists()
    assert cron.exists()
    assert readme.exists()
    plist_text = plist.read_text(encoding="utf-8")
    readme_text = readme.read_text(encoding="utf-8")
    assert "run_phase9g_daily_operation.py" in plist_text
    assert "launchctl load" in readme_text
    assert "does not automatically register" in readme_text

