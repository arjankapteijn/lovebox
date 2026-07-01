"""Afbeelding genereren voor het Lovebox Color & Photo scherm (320x240).

Geen emoji's — het ingebouwde DejaVu-font rendert die niet. Feest-iconen
(ballonnen, confetti, sterren) worden daarom met tekenprimitieven gemaakt, en
alleen tekens die DejaVu wel kent (zoals ° en ♥) worden als tekst gebruikt.
"""

from __future__ import annotations

import math
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

# Feestkleuren (voor ballonnen/confetti op de verjaardag)
PARTY_PINK = (235, 90, 140)
PARTY_BLUE = (80, 150, 220)
PARTY = [
    (250, 200, 60),  # geel
    PARTY_PINK,  # roze
    PARTY_BLUE,  # blauw
    (95, 190, 120),  # groen
    (155, 95, 200),  # paars
    (245, 140, 60),  # oranje
]

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


def _center(draw: ImageDraw.ImageDraw, text: str, y: int, font, fill) -> None:
    w = draw.textlength(text, font=font)
    draw.text(((IMG_W - w) / 2, y), text, font=font, fill=fill)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int, sizes: list[int]):
    """Kies het grootste bold-font waarbij `text` binnen max_w past."""
    for size in sizes:
        font = load_font(size, bold=True)
        if draw.textlength(text, font=font) <= max_w:
            return font
    return load_font(sizes[-1], bold=True)


# ---------------------------------------------------------------------------
# Gedeelde onderdelen
# ---------------------------------------------------------------------------
def _draw_header(draw: ImageDraw.ImageDraw, weather: Weather, location_name: str) -> None:
    f_tiny = load_font(11)
    f_big = load_font(18, bold=True)
    draw.rectangle([0, 0, IMG_W, 28], fill=ACCENT)
    draw.text((10, 6), f"Weer {location_name}", font=f_big, fill=(255, 255, 255))
    date_str = _format_date(weather.date)
    tw = draw.textlength(date_str, font=f_tiny)
    draw.text((IMG_W - tw - 8, 10), date_str, font=f_tiny, fill=(255, 220, 210))


# ---------------------------------------------------------------------------
# Standaardweergave: weer + kledingadvies + aankomende datums
# ---------------------------------------------------------------------------
def _draw_standard(
    draw: ImageDraw.ImageDraw, weather: Weather, occurrences: list[Occurrence]
) -> None:
    f_small = load_font(13)
    f_med = load_font(15)
    f_temp = load_font(44, bold=True)
    desc = weather_description(weather.code)
    advice = clothing_advice(weather.temp_max, weather.rain_sum, weather.wind_kmh)

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


# ---------------------------------------------------------------------------
# Feestweergave: op de verjaardag zelf
# ---------------------------------------------------------------------------
def _draw_balloon(draw: ImageDraw.ImageDraw, cx: int, cy: int, rx: int, ry: int, color) -> None:
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color, outline=(255, 255, 255))
    # glimlichtje
    draw.ellipse(
        [cx - rx // 2, cy - ry // 2, cx - rx // 2 + 5, cy - ry // 2 + 7], fill=(255, 255, 255)
    )
    # knoopje
    draw.polygon([(cx - 3, cy + ry), (cx + 3, cy + ry), (cx, cy + ry + 5)], fill=color)
    # touwtje (zigzag)
    pts = [(cx, cy + ry + 5)]
    for i in range(1, 6):
        dx = 4 if i % 2 else -4
        pts.append((cx + dx, cy + ry + 5 + i * 6))
    draw.line(pts, fill=(150, 120, 110), width=1)


def _draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color) -> None:
    """Vijfpuntige ster als vorm (rendert overal gelijk, geen font nodig)."""
    pts = []
    for k in range(10):
        ang = math.radians(-90 + k * 36)
        rad = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=color)


def _draw_garland(
    draw: ImageDraw.ImageDraw, x0: int, x1: int, y_top: int, sag: int, n_flags: int
) -> None:
    """Een slinger: een doorzakkend touwtje met vlaggetjes die eronder hangen."""

    def arc_y(x: float) -> float:
        # Neerwaartse parabool: uiteinden op y_top, in het midden `sag` lager.
        t = (x - x0) / (x1 - x0)
        return y_top + sag * (1 - (2 * t - 1) ** 2)

    # Doorzakkend touwtje
    string_pts = [(x, round(arc_y(x))) for x in range(x0, x1 + 1, 4)]
    draw.line(string_pts, fill=(120, 90, 80), width=2)

    # Vlaggetjes hangend aan het touwtje (puntje naar beneden)
    half, drop = 9, 16
    for i in range(n_flags):
        t = (i + 0.5) / n_flags
        x = round(x0 + t * (x1 - x0))
        y = round(arc_y(x))
        color = PARTY[i % len(PARTY)]
        draw.polygon(
            [(x - half, y), (x + half, y), (x, y + drop)],
            fill=color,
            outline=(255, 255, 255),
        )


def _draw_festive(draw: ImageDraw.ImageDraw, weather: Weather, birthdays: list[Occurrence]) -> None:
    f_small = load_font(13)
    f_title = load_font(23, bold=True)
    f_line = load_font(16)
    desc = weather_description(weather.code)

    # Slinger bovenaan: doorzakkend touwtje met vlaggetjes
    _draw_garland(draw, x0=10, x1=310, y_top=32, sag=16, n_flags=9)

    # Ballonnen links en rechts
    _draw_balloon(draw, 34, 132, 24, 30, PARTY_PINK)
    _draw_balloon(draw, 286, 132, 24, 30, PARTY_BLUE)

    # Sterretjes naast de titel
    for cx in (60, 260):
        _draw_star(draw, cx, 84, 7, (250, 200, 60))

    # Gefeliciteerd!
    _center(draw, "Gefeliciteerd!", 72, f_title, ACCENT)

    # Naam/namen zo groot mogelijk laten passen (tussen de ballonnen)
    names = " & ".join(b.name for b in birthdays)
    f_name = _fit_font(draw, names, max_w=196, sizes=[34, 30, 26, 22, 18])
    _center(draw, names, 104, f_name, PARTY_PINK)

    # Leeftijdsregel
    if len(birthdays) == 1 and birthdays[0].age is not None:
        age_line = f"wordt vandaag {birthdays[0].age} jaar!"
    elif len(birthdays) == 1:
        age_line = "is vandaag jarig!"
    else:
        age_line = "zijn vandaag jarig!"
    _center(draw, age_line, 154, f_line, TEXT_DARK)

    # Slot + kleine weerregel als voetregel
    _center(draw, "Hiep hiep hoera!", 180, f_line, ACCENT)
    _center(draw, f"{weather.temp_max:.0f}°  ·  {desc}", 218, f_small, TEXT_LIGHT)


# ---------------------------------------------------------------------------
# Publieke entrypoint
# ---------------------------------------------------------------------------
def create_image(
    weather: Weather,
    occurrences: list[Occurrence] | None,
    location_name: str,
) -> bytes:
    occurrences = occurrences or []
    img = Image.new("RGB", (IMG_W, IMG_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    _draw_header(draw, weather, location_name)

    # Valt er vandaag een verjaardag? Dan feestmodus i.p.v. kledingadvies.
    birthdays_today = [o for o in occurrences if o.kind == "birthday" and o.days_until == 0]
    if birthdays_today:
        _draw_festive(draw, weather, birthdays_today)
    else:
        _draw_standard(draw, weather, occurrences)

    # Hartje rechtsonder
    draw.text((IMG_W - 22, IMG_H - 24), "♥", font=load_font(15), fill=ACCENT)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
