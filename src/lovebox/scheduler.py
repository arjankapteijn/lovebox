"""Ingebouwde dagelijkse scheduler voor de self-scheduling container.

De container blijft draaien en verstuurt één keer per dag rond `run_at`.
Elke tick wordt een heartbeat-bestand aangeraakt zodat de Docker HEALTHCHECK
kan zien dat het proces leeft.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

TICK_SECONDS = 30


def _parse_hhmm(run_at: str) -> tuple[int, int]:
    try:
        hh, mm = run_at.split(":")
        return int(hh), int(mm)
    except ValueError as exc:
        raise ValueError(f"LOVEBOX_RUN_AT moet 'HH:MM' zijn, kreeg {run_at!r}") from exc


def _touch_heartbeat(data_dir: str) -> None:
    try:
        os.makedirs(data_dir, exist_ok=True)
        path = os.path.join(data_dir, "heartbeat")
        with open(path, "w", encoding="utf-8") as f:
            f.write(datetime.now().isoformat())
    except OSError:
        pass  # heartbeat is best-effort; nooit de loop laten crashen


def _due(now: datetime, run_h: int, run_m: int, last_run: date | None) -> bool:
    """True als het na het ingestelde tijdstip is en er vandaag nog niet is gedraaid."""
    if last_run == now.date():
        return False
    return (now.hour, now.minute) >= (run_h, run_m)


def run_forever(
    job: Callable[[], None],
    *,
    run_at: str,
    timezone: str,
    data_dir: str,
    run_on_start: bool = False,
    tick_seconds: int = TICK_SECONDS,
    _now: Callable[[], datetime] | None = None,
    _sleep: Callable[[float], None] = time.sleep,
    _max_iterations: int | None = None,
) -> None:
    """Draai `job` dagelijks rond `run_at`.

    De `_now`, `_sleep` en `_max_iterations` parameters bestaan voor tests.
    """
    tz = ZoneInfo(timezone)
    now_fn = _now or (lambda: datetime.now(tz))
    run_h, run_m = _parse_hhmm(run_at)

    last_run: date | None = None
    if run_on_start:
        _safe_run(job)
        last_run = now_fn().date()

    iterations = 0
    while _max_iterations is None or iterations < _max_iterations:
        iterations += 1
        now = now_fn()
        _touch_heartbeat(data_dir)
        if _due(now, run_h, run_m, last_run):
            _safe_run(job)
            last_run = now.date()
        _sleep(tick_seconds)


def _safe_run(job: Callable[[], None]) -> None:
    try:
        job()
    except Exception as exc:  # noqa: BLE001 — één mislukte dag mag de loop niet stoppen
        print(f"[scheduler] job faalde: {exc!r}", flush=True)
