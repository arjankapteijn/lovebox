"""Afbeelding genereren voor het Lovebox Color & Photo scherm (320x240).

Geen emoji's — het ingebouwde DejaVu-font rendert die niet. Alleen tekens die
DejaVu wel kent (zoals ° en het hartje ♥) worden gebruikt.
"""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from .events import Occurrence, format_line
from .weather import Weather, clothing_advice, weather_description

IMG_W, IMG_H = 320, 240

# Kleuren
BG_COLOR = (255, 245, 235)
ACCENT = (220, 80, 60)
TEXT_DARK = (40, 30, 30)
TEXT_LIGHT = (130, 110, 100)
TEMP_COLOR = (200, 60, 40)
LINE_COLOR = (230, 200, 180)

_DAYS = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
_MONTHS = ["", "jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"]

# Font-kandidaten: eerst DejaVu (in de container), dan macOS-fallbacks voor
# lokale previews, dan het ingebouwde PIL-font.
_FONT_CANDIDATES = {
    False: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ],
    True: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ],
}


def load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES[bold]:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _format_date(iso_date: str) -> str:
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return f"{_DAYS[dt.weekday()].capitalize()} {dt.day} {_MONTHS[dt.month]}"


def create_image(
    weather: Weather,
    occurrences: list[Occurrence] | None,
    location_name: str,
) -> bytes:
    occurrences = occurrences or []
    desc = weather_description(weather.code)
    advice = clothing_advice(weather.temp_max, weather.rain_sum, weather.wind_kmh)

    img = Image.new("RGB", (IMG_W, IMG_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    f_tiny = load_font(11)
    f_small = load_font(13)
    f_med = load_font(15)
    f_big = load_font(18, bold=True)
    f_temp = load_font(44, bold=True)

    # Header
    draw.rectangle([0, 0, IMG_W, 28], fill=ACCENT)
    draw.text((10, 6), f"Weer {location_name}", font=f_big, fill=(255, 255, 255))
    date_str = _format_date(weather.date)
    tw = draw.textlength(date_str, font=f_tiny)
    draw.text((IMG_W - tw - 8, 10), date_str, font=f_tiny, fill=(255, 220, 210))

    # Temperatuur (links)
    draw.text((12, 32), f"{weather.temp_max:.0f}°", font=f_temp, fill=TEMP_COLOR)
    draw.text((14, 86), f"min {weather.temp_min:.0f}°", font=f_small, fill=TEXT_LIGHT)

    # Weer (rechts)
    draw.text((122, 38), desc, font=f_med, fill=TEXT_DARK)
    draw.text((122, 64), f"Regen: {weather.rain_sum:.1f} mm", font=f_small, fill=TEXT_LIGHT)
    draw.text((122, 84), f"Wind:  {weather.wind_kmh:.0f} km/u", font=f_small, fill=TEXT_LIGHT)

    # Kledingadvies in twee kolommen
    draw.line([(8, 110), (IMG_W - 8, 110)], fill=LINE_COLOR, width=1)
    draw.text((10, 114), "Kleding kids:", font=f_med, fill=ACCENT)
    col_x = (14, 168)
    for i, line in enumerate(advice[:4]):
        x = col_x[i // 2]
        y = 136 + (i % 2) * 18
        draw.text((x, y), f"- {line}", font=f_small, fill=TEXT_DARK)

    # Aankomend (alleen tonen als er iets is)
    if occurrences:
        draw.line([(8, 176), (IMG_W - 8, 176)], fill=LINE_COLOR, width=1)
        draw.text((10, 180), "Binnenkort:", font=f_med, fill=ACCENT)
        for i, occ in enumerate(occurrences[:2]):
            y = 202 + i * 18
            marker = "♥" if occ.kind == "birthday" else "•"
            draw.text((14, y), marker, font=f_small, fill=ACCENT)
            draw.text((30, y), format_line(occ), font=f_small, fill=TEXT_DARK)

    # Hartje rechtsonder
    draw.text((IMG_W - 22, IMG_H - 24), "♥", font=f_med, fill=ACCENT)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
