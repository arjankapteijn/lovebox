"""Entrypoint: bouwt het dagbericht en verstuurt het naar de Lovebox.

Twee modi:
  * scheduler (standaard): container blijft draaien, verstuurt dagelijks.
  * run-once (LOVEBOX_RUN_ONCE=true): één keer versturen en stoppen.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from . import api
from .config import Config, is_configured, load_config
from .events import select_occurrences
from .render import create_image
from .scheduler import run_forever
from .weather import fetch_weather, weather_description


def build_and_send(config: Config) -> None:
    tz = ZoneInfo(config.timezone)
    today = datetime.now(tz).date()
    print(f"[{datetime.now(tz):%Y-%m-%d %H:%M}] Lovebox dagbericht starten...", flush=True)

    print(f"  -> Weer ophalen voor {config.location_name}...", flush=True)
    weather = fetch_weather(config.lat, config.lon)
    print(
        f"     {weather_description(weather.code)}"
        f" | max {weather.temp_max:.0f}° / min {weather.temp_min:.0f}°"
        f" | regen {weather.rain_sum:.1f} mm | wind {weather.wind_kmh:.0f} km/u",
        flush=True,
    )

    occurrences = select_occurrences(config, today)
    if occurrences:
        print("  -> Binnenkort: " + "; ".join(o.name for o in occurrences), flush=True)

    print("  -> Afbeelding (320x240) genereren...", flush=True)
    png_bytes = create_image(weather, occurrences, config.location_name)

    preview = os.path.join(
        config.data_dir if os.path.isdir(config.data_dir) else "/tmp", "lovebox_preview.png"
    )
    try:
        with open(preview, "wb") as f:
            f.write(png_bytes)
        print(f"     Preview: {preview} ({len(png_bytes) / 1024:.1f} kB)", flush=True)
    except OSError as exc:
        print(f"     ! Kon preview niet schrijven naar {preview}: {exc}", flush=True)

    print("  -> Inloggen bij Lovebox...", flush=True)
    token = api.login(config.email, config.password)
    device_id, boxes = api.fetch_me(token)
    box_ids = [b["_id"] for b in boxes]
    if config.box_id not in box_ids:
        print(
            f"  ! Waarschuwing: box_id {config.box_id!r} niet in account. Beschikbaar: {box_ids}",
            flush=True,
        )

    print("  -> Verzenden...", flush=True)
    result = api.send_image(token, config.box_id, device_id, png_bytes)
    status = (result.get("status") or {}).get("label")
    print(f"     Verzonden! id={result.get('_id')} status={status}", flush=True)


def main() -> int:
    config = load_config()
    if not is_configured(config):
        print(
            "! Ontbrekende configuratie. Zet LOVEBOX_EMAIL, LOVEBOX_PASSWORD en "
            "LOVEBOX_BOX_ID (zie README / .env.example).",
            file=sys.stderr,
        )
        return 1

    if config.run_once:
        build_and_send(config)
        return 0

    print(
        f"Scheduler actief — dagelijks om {config.run_at} ({config.timezone}). "
        f"run_on_start={config.run_on_start}",
        flush=True,
    )
    run_forever(
        lambda: build_and_send(config),
        run_at=config.run_at,
        timezone=config.timezone,
        data_dir=config.data_dir,
        run_on_start=config.run_on_start,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
