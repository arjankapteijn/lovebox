"""Selecteer de eerstvolgende verjaardagen en activiteiten.

Regels (afgesproken):
  * Verjaardagen verschijnen pas als ze binnen `birthday_window_days` vallen
    (standaard 30 dagen) en herhalen jaarlijks.
  * Activiteiten verschijnen binnen `event_window_days` (instelbaar).
  * Er worden maximaal `max_slots` datums getoond (standaard 2), waarbij
    verjaardagen voorrang krijgen boven gewone activiteiten.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .config import Config, Entry


@dataclass(frozen=True)
class Occurrence:
    name: str
    when: date  # eerstvolgende datum waarop het valt
    days_until: int
    kind: str  # "birthday" | "event"
    age: int | None  # leeftijd bij verjaardag als het geboortejaar bekend is


def _parse_month_day_year(value: str) -> tuple[int, int, int | None]:
    """Ondersteunt 'MM-DD' (terugkerend) en 'YYYY-MM-DD' (vaste datum)."""
    parts = value.split("-")
    if len(parts) == 3:
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        return month, day, year
    if len(parts) == 2:
        month, day = int(parts[0]), int(parts[1])
        return month, day, None
    raise ValueError(f"Ongeldige datum {value!r}; gebruik 'MM-DD' of 'YYYY-MM-DD'")


def _safe_date(year: int, month: int, day: int) -> date:
    """Maak een datum; 29 feb in een niet-schrikkeljaar valt terug op 28 feb."""
    try:
        return date(year, month, day)
    except ValueError:
        if month == 2 and day == 29:
            return date(year, 2, 28)
        raise


def validate_date(value: str) -> None:
    """Valideer dat `value` een geldige 'MM-DD' of 'YYYY-MM-DD' datum is.

    Raises ValueError als dat niet zo is. Wordt bij het laden van de config
    aangeroepen zodat een typefout meteen opvalt, in plaats van dagelijks stil
    de hele dagbericht-job te laten falen (de scheduler slikt die exceptie).
    """
    try:
        month, day, year = _parse_month_day_year(value)
    except ValueError as exc:
        # int()-fouten netjes herformuleren tot dezelfde uitleg.
        raise ValueError(f"Ongeldige datum {value!r}; gebruik 'MM-DD' of 'YYYY-MM-DD'") from exc
    # Schrikkeljaar zodat 29 feb geldig is; _safe_date vangt die sowieso af.
    _safe_date(year if year is not None else 2000, month, day)


def _next_annual(month: int, day: int, today: date) -> date:
    """Eerstvolgende voorkomen van een jaarlijks terugkerende maand/dag."""
    candidate = _safe_date(today.year, month, day)
    if candidate < today:
        candidate = _safe_date(today.year + 1, month, day)
    return candidate


def _birthday_occurrence(entry: Entry, today: date) -> Occurrence:
    month, day, year = _parse_month_day_year(entry.date)
    when = _next_annual(month, day, today)
    age = when.year - year if year is not None else None
    return Occurrence(
        name=entry.name,
        when=when,
        days_until=(when - today).days,
        kind="birthday",
        age=age,
    )


def _event_occurrence(entry: Entry, today: date) -> Occurrence | None:
    """Activiteit → Occurrence, of None als de vaste datum al voorbij is."""
    month, day, year = _parse_month_day_year(entry.date)
    if year is not None:
        when = _safe_date(year, month, day)
        if when < today:
            return None  # eenmalige activiteit in het verleden
    else:
        when = _next_annual(month, day, today)  # jaarlijks terugkerend
    return Occurrence(
        name=entry.name,
        when=when,
        days_until=(when - today).days,
        kind="event",
        age=None,
    )


def select_occurrences(config: Config, today: date) -> list[Occurrence]:
    """Geef de te tonen datums terug: verjaardagen eerst, dan activiteiten."""
    birthdays = [
        occ
        for entry in config.birthdays
        if (occ := _birthday_occurrence(entry, today)).days_until <= config.birthday_window_days
    ]
    events = [
        occ
        for entry in config.events
        if (occ := _event_occurrence(entry, today)) is not None
        and occ.days_until <= config.event_window_days
    ]

    birthdays.sort(key=lambda o: (o.days_until, o.name))
    events.sort(key=lambda o: (o.days_until, o.name))

    # Verjaardagen vullen de slots eerst; activiteiten pakken wat overblijft.
    return (birthdays + events)[: config.max_slots]


def format_relative(days_until: int) -> str:
    if days_until <= 0:
        return "vandaag"
    if days_until == 1:
        return "morgen"
    return f"over {days_until} dgn"


_MONTHS = ["", "jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]


def format_line(occ: Occurrence) -> str:
    """Korte regel voor op de afbeelding."""
    rel = format_relative(occ.days_until)
    if occ.kind == "birthday":
        if occ.age is not None:
            return f"{occ.name} wordt {occ.age} ({rel})"
        return f"{occ.name} jarig ({rel})"
    return f"{occ.name} ({rel})"
