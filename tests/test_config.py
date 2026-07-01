import pytest

from lovebox.config import Entry, is_configured, load_config, parse_entries


def test_parse_entries_empty():
    assert parse_entries("", var_name="X") == ()
    assert parse_entries("   ", var_name="X") == ()


def test_parse_entries_valid():
    raw = '[{"name": "Emma", "date": "2018-03-15"}, {"name": "Sem", "date": "07-01"}]'
    entries = parse_entries(raw, var_name="LOVEBOX_BIRTHDAYS")
    assert entries == (Entry("Emma", "2018-03-15"), Entry("Sem", "07-01"))


def test_parse_entries_invalid_json():
    with pytest.raises(ValueError, match="geldige JSON"):
        parse_entries("{niet: json}", var_name="X")


def test_parse_entries_not_a_list():
    with pytest.raises(ValueError, match="JSON-lijst"):
        parse_entries('{"name": "x", "date": "01-01"}', var_name="X")


def test_parse_entries_missing_field():
    with pytest.raises(ValueError, match="mist"):
        parse_entries('[{"name": "Emma"}]', var_name="X")


def test_parse_entries_invalid_date_fails_fast():
    # Een typefout in de datum moet bij het laden opvallen, niet pas dagelijks
    # stil in de scheduler (die exceptions slikt).
    with pytest.raises(ValueError, match="ongeldige datum"):
        parse_entries('[{"name": "Emma", "date": "15-40"}]', var_name="X")
    with pytest.raises(ValueError, match="ongeldige datum"):
        parse_entries('[{"name": "Emma", "date": "niet-een-datum"}]', var_name="X")


def test_parse_entries_accepts_leap_day():
    # 29 feb is een geldige (terugkerende) datum, ook al is 2000 hier willekeurig.
    assert parse_entries('[{"name": "Schrikkel", "date": "02-29"}]', var_name="X") == (
        Entry("Schrikkel", "02-29"),
    )


def test_load_config_defaults():
    cfg = load_config(env={})
    assert cfg.location_name == "Harderwijk"
    assert cfg.event_window_days == 30
    assert cfg.birthday_window_days == 30
    assert cfg.max_slots == 2
    assert cfg.run_at == "07:00"
    assert cfg.timezone == "Europe/Amsterdam"
    assert cfg.run_once is False
    assert not is_configured(cfg)


def test_load_config_full():
    cfg = load_config(
        env={
            "LOVEBOX_EMAIL": "a@b.nl",
            "LOVEBOX_PASSWORD": "pw",
            "LOVEBOX_BOX_ID": "box123",
            "LOVEBOX_LAT": "52.1",
            "LOVEBOX_LON": "5.2",
            "LOVEBOX_LOCATION_NAME": "Zwolle",
            "LOVEBOX_EVENT_WINDOW_DAYS": "60",
            "LOVEBOX_MAX_SLOTS": "3",
            "LOVEBOX_RUN_ONCE": "true",
            "LOVEBOX_BIRTHDAYS": '[{"name": "Emma", "date": "03-15"}]',
        }
    )
    assert is_configured(cfg)
    assert cfg.lat == 52.1
    assert cfg.location_name == "Zwolle"
    assert cfg.event_window_days == 60
    assert cfg.max_slots == 3
    assert cfg.run_once is True
    assert cfg.birthdays == (Entry("Emma", "03-15"),)


def test_load_config_bad_int():
    with pytest.raises(ValueError, match="geheel getal"):
        load_config(env={"LOVEBOX_EVENT_WINDOW_DAYS": "abc"})
