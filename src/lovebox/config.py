"""Configuratie uit omgevingsvariabelen.

Alles wat persoonlijk is (namen, datums, credentials, locatie) komt uit de
omgeving zodat de repo publiek kan zijn. Zie `.env.example` voor het formaat.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    """Een verjaardag of activiteit zoals opgegeven in de env-JSON."""

    name: str
    date: str  # "MM-DD" (jaarlijks terugkerend) of "YYYY-MM-DD" (vaste datum)


@dataclass(frozen=True)
class Config:
    # Credentials + doelbox
    email: str
    password: str
    box_id: str
    # Locatie voor de weersverwachting
    lat: float
    lon: float
    location_name: str
    # Agenda
    birthdays: tuple[Entry, ...]
    events: tuple[Entry, ...]
    birthday_window_days: int
    event_window_days: int
    max_slots: int
    # Scheduler
    run_at: str  # "HH:MM"
    timezone: str
    run_once: bool
    run_on_start: bool
    data_dir: str


def _get(env: Mapping[str, str], name: str, default: str = "") -> str:
    return (env.get(name) or default).strip()


def _get_bool(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = _get(env, name).lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "ja", "on")


def _get_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _get(env, name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} moet een geheel getal zijn, kreeg {raw!r}") from exc


def _get_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = _get(env, name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} moet een getal zijn, kreeg {raw!r}") from exc


def parse_entries(raw: str, *, var_name: str) -> tuple[Entry, ...]:
    """Parse een JSON-lijst van {"name": ..., "date": ...} objecten.

    Een lege/afwezige waarde levert een lege tuple op. Ongeldige JSON, een
    verkeerde structuur of een onbruikbare datum geeft een duidelijke ValueError.
    """
    # Lazy import: events importeert config, dus op modulniveau zou dit een
    # circulaire import zijn.
    from .events import validate_date

    raw = (raw or "").strip()
    if not raw:
        return ()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{var_name} is geen geldige JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"{var_name} moet een JSON-lijst zijn")

    entries: list[Entry] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{var_name}[{i}] moet een object zijn")
        name = str(item.get("name", "")).strip()
        date = str(item.get("date", "")).strip()
        if not name or not date:
            raise ValueError(f"{var_name}[{i}] mist 'name' of 'date'")
        try:
            validate_date(date)
        except ValueError as exc:
            raise ValueError(f"{var_name}[{i}] heeft een ongeldige datum: {exc}") from exc
        entries.append(Entry(name=name, date=date))
    return tuple(entries)


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Lees de volledige configuratie uit de omgeving (default: os.environ)."""
    env = os.environ if env is None else env

    default_window = _get_int(env, "LOVEBOX_EVENT_WINDOW_DAYS", 30)

    return Config(
        email=_get(env, "LOVEBOX_EMAIL"),
        password=_get(env, "LOVEBOX_PASSWORD"),
        box_id=_get(env, "LOVEBOX_BOX_ID"),
        lat=_get_float(env, "LOVEBOX_LAT", 52.3415),
        lon=_get_float(env, "LOVEBOX_LON", 5.6147),
        location_name=_get(env, "LOVEBOX_LOCATION_NAME", "Harderwijk"),
        birthdays=parse_entries(env.get("LOVEBOX_BIRTHDAYS", ""), var_name="LOVEBOX_BIRTHDAYS"),
        events=parse_entries(env.get("LOVEBOX_EVENTS", ""), var_name="LOVEBOX_EVENTS"),
        birthday_window_days=_get_int(env, "LOVEBOX_BIRTHDAY_WINDOW_DAYS", 30),
        event_window_days=default_window,
        max_slots=_get_int(env, "LOVEBOX_MAX_SLOTS", 2),
        run_at=_get(env, "LOVEBOX_RUN_AT", "07:00"),
        timezone=_get(env, "LOVEBOX_TZ", "Europe/Amsterdam"),
        run_once=_get_bool(env, "LOVEBOX_RUN_ONCE", False),
        run_on_start=_get_bool(env, "LOVEBOX_RUN_ON_START", False),
        data_dir=_get(env, "LOVEBOX_DATA_DIR", "/data"),
    )


def is_configured(config: Config) -> bool:
    """True als de verplichte credentials aanwezig zijn."""
    return bool(config.email and config.password and config.box_id)
