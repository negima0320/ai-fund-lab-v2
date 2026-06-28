from datetime import datetime

from ai_fund_lab_v2.safety_phase11.monitor_schedule import DEFAULT_MONITOR_TIMES, MonitorSchedule, default_monitor_schedule


def test_default_monitor_schedule_has_six_timings():
    schedule = default_monitor_schedule()
    assert schedule.scheduled_times() == ("09:05", "09:30", "10:30", "12:35", "14:45", "15:20")
    assert len(schedule.scheduled_times()) == 6
    assert DEFAULT_MONITOR_TIMES == schedule.scheduled_times()


def test_monitor_schedule_market_hours_and_next_time():
    schedule = MonitorSchedule()
    assert schedule.is_market_hours("09:05") is True
    assert schedule.is_market_hours("08:59") is False
    assert schedule.next_monitor_time("09:06") == "09:30"
    assert schedule.next_monitor_time("15:20") is None


def test_monitor_schedule_next_datetime_preserves_date_and_timezone():
    current = datetime.fromisoformat("2026-06-29T10:00:00+09:00")
    next_run = MonitorSchedule().next_monitor_datetime(current)
    assert next_run is not None
    assert next_run.isoformat() == "2026-06-29T10:30:00+09:00"
