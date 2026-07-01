import json
from datetime import date, timedelta

from lovebox.config import load_config
from lovebox.events import format_line, format_relative, select_occurrences

TODAY = date(2026, 7, 1)


def _cfg(birthdays=None, events=None, **extra):
    env = {}
    if birthdays is not None:
        env["LOVEBOX_BIRTHDAYS"] = json.dumps(birthdays)
    if events is not None:
        env["LOVEBOX_EVENTS"] = json.dumps(events)
    env.update({k: str(v) for k, v in extra.items()})
    return load_config(env=env)


def _in_days(n):
    d = TODAY + timedelta(days=n)
    return f"{d.month:02d}-{d.day:02d}"


def test_birthday_within_30_days_is_shown_with_age():
    cfg = _cfg(birthdays=[{"name": "Emma", "date": f"2018-{_in_days(10)}"}])
    occ = select_occurrences(cfg, TODAY)
    assert len(occ) == 1
    assert occ[0].name == "Emma"
    assert occ[0].days_until == 10
    assert occ[0].age == 8  # 2026 - 2018
    assert occ[0].kind == "birthday"


def test_birthday_beyond_window_is_hidden():
    cfg = _cfg(birthdays=[{"name": "Ver", "date": _in_days(40)}])
    assert select_occurrences(cfg, TODAY) == []


def test_birthday_without_year_has_no_age():
    cfg = _cfg(birthdays=[{"name": "Oma", "date": _in_days(5)}])
    occ = select_occurrences(cfg, TODAY)
    assert occ[0].age is None
    assert format_line(occ[0]) == "Oma jarig (over 5 dgn)"


def test_max_two_and_birthdays_have_priority():
    # 2 verjaardagen binnen venster + 1 activiteit dichterbij:
    # verjaardagen pakken beide slots.
    cfg = _cfg(
        birthdays=[
            {"name": "A", "date": _in_days(20)},
            {"name": "B", "date": _in_days(25)},
        ],
        events=[{"name": "Pretpark", "date": _in_days(2)}],
    )
    occ = select_occurrences(cfg, TODAY)
    assert [o.name for o in occ] == ["A", "B"]


def test_event_fills_remaining_slot_after_birthday():
    cfg = _cfg(
        birthdays=[{"name": "Jarige", "date": _in_days(15)}],
        events=[
            {"name": "Ver weg", "date": _in_days(25)},
            {"name": "Dichtbij", "date": _in_days(3)},
        ],
    )
    occ = select_occurrences(cfg, TODAY)
    assert [o.name for o in occ] == ["Jarige", "Dichtbij"]


def test_event_window_is_configurable():
    events = [{"name": "Later", "date": _in_days(45)}]
    assert select_occurrences(_cfg(events=events), TODAY) == []  # default 30
    occ = select_occurrences(_cfg(events=events, LOVEBOX_EVENT_WINDOW_DAYS=60), TODAY)
    assert [o.name for o in occ] == ["Later"]


def test_one_off_event_in_the_past_is_ignored():
    cfg = _cfg(events=[{"name": "Verleden", "date": "2026-06-01"}])
    assert select_occurrences(cfg, TODAY) == []


def test_recurring_event_rolls_over_to_next_year():
    # Sinterklaas 05-12 is dit jaar nog niet geweest op 1 juli 2026
    cfg = _cfg(events=[{"name": "Sint", "date": "12-05"}], LOVEBOX_EVENT_WINDOW_DAYS=400)
    occ = select_occurrences(cfg, TODAY)
    assert occ[0].when == date(2026, 12, 5)


def test_today_and_tomorrow_formatting():
    cfg = _cfg(birthdays=[{"name": "Nu", "date": _in_days(0)}])
    occ = select_occurrences(cfg, TODAY)
    assert occ[0].days_until == 0
    assert format_relative(0) == "vandaag"
    assert format_relative(1) == "morgen"


def test_event_line_format():
    cfg = _cfg(events=[{"name": "Schoolreis", "date": _in_days(4)}])
    occ = select_occurrences(cfg, TODAY)
    assert format_line(occ[0]) == "Schoolreis (over 4 dgn)"
