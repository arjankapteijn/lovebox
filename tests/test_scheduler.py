from datetime import datetime
from zoneinfo import ZoneInfo

from lovebox.scheduler import _due, run_forever

TZ = ZoneInfo("Europe/Amsterdam")


def test_due_after_time_and_not_run_today():
    now = datetime(2026, 7, 1, 7, 30, tzinfo=TZ)
    assert _due(now, 7, 0, last_run=None) is True


def test_not_due_before_time():
    now = datetime(2026, 7, 1, 6, 59, tzinfo=TZ)
    assert _due(now, 7, 0, last_run=None) is False


def test_not_due_when_already_ran_today():
    now = datetime(2026, 7, 1, 8, 0, tzinfo=TZ)
    assert _due(now, 7, 0, last_run=now.date()) is False


def test_run_forever_runs_once_per_day(tmp_path):
    calls = []
    # simuleer 07:00 op dag 1, dan 07:01 (zelfde dag), dan 07:00 dag 2
    times = [
        datetime(2026, 7, 1, 7, 0, tzinfo=TZ),
        datetime(2026, 7, 1, 7, 1, tzinfo=TZ),
        datetime(2026, 7, 2, 7, 0, tzinfo=TZ),
    ]
    seq = iter(times)

    run_forever(
        lambda: calls.append(1),
        run_at="07:00",
        timezone="Europe/Amsterdam",
        data_dir=str(tmp_path),
        tick_seconds=0,
        _now=lambda: next(seq),
        _sleep=lambda _: None,
        _max_iterations=len(times),
    )
    assert sum(calls) == 2  # één keer per dag, niet drie keer


def test_run_on_start_triggers_immediately(tmp_path):
    calls = []
    now = datetime(2026, 7, 1, 6, 0, tzinfo=TZ)  # vóór run_at
    run_forever(
        lambda: calls.append(1),
        run_at="07:00",
        timezone="Europe/Amsterdam",
        data_dir=str(tmp_path),
        run_on_start=True,
        tick_seconds=0,
        _now=lambda: now,
        _sleep=lambda _: None,
        _max_iterations=1,
    )
    assert sum(calls) == 1  # meteen gedraaid ondanks dat het nog geen 07:00 is
