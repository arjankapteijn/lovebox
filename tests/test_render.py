from datetime import date
from io import BytesIO

from PIL import Image

from lovebox.events import Occurrence
from lovebox.render import BG_COLOR, IMG_H, IMG_W, PARTY_PINK, create_image
from lovebox.weather import Weather, clothing_advice

WEATHER = Weather(code=61, temp_max=18, temp_min=11, rain_sum=2.0, wind_kmh=25, date="2026-07-01")

# Koud + zware regen + harde wind = het maximale kledingadvies (4 regels).
WORST_WEATHER = Weather(
    code=75, temp_max=3, temp_min=-2, rain_sum=5.0, wind_kmh=60, date="2026-07-01"
)

TWO_BIRTHDAYS = [
    Occurrence("Ighone", date(2026, 7, 7), 6, "birthday", 5),
    Occurrence("Ivy", date(2026, 7, 20), 19, "birthday", 10),
]


def _open(png_bytes):
    return Image.open(BytesIO(png_bytes))


def _ink_in_band(img, y0, y1):
    """Aantal niet-achtergrond-pixels in de horizontale strook [y0, y1)."""
    px = img.convert("RGB")
    return sum(
        1 for y in range(y0, y1) for x in range(img.width) if px.getpixel((x, y)) != BG_COLOR
    )


def _has_color(img, color):
    """Komt deze exacte kleur ergens in de afbeelding voor?"""
    px = img.convert("RGB")
    return any(px.getpixel((x, y)) == color for y in range(img.height) for x in range(img.width))


def test_image_is_png_320x240_without_events():
    png = create_image(WEATHER, [], "Harderwijk")
    img = _open(png)
    assert img.format == "PNG"
    assert img.size == (IMG_W, IMG_H)


def test_image_with_two_occurrences():
    occ = [
        Occurrence("Emma", date(2026, 7, 11), 10, "birthday", 8),
        Occurrence("Schoolreis", date(2026, 7, 5), 4, "event", None),
    ]
    png = create_image(WEATHER, occ, "Zwolle")
    assert _open(png).size == (IMG_W, IMG_H)


def test_image_handles_none_occurrences():
    png = create_image(WEATHER, None, "Harderwijk")
    assert _open(png).size == (IMG_W, IMG_H)


def test_max_clothing_does_not_hide_birthdays():
    """Regressie: 4 kledingregels mogen géén verjaardag wegduwen.

    Het kledingadvies staat in twee kolommen (vaste hoogte), dus ook het
    volle advies laat beide verjaardagsregels intact en binnen het beeld.
    """
    assert len(clothing_advice(3, 5, 60)) == 4  # worst case = 4 regels
    img = _open(create_image(WORST_WEATHER, TWO_BIRTHDAYS, "Harderwijk"))
    assert img.size == (IMG_W, IMG_H)
    # Het volle kledingadvies is getekend (band 136-173)...
    assert _ink_in_band(img, 136, 173) > 0
    # ...én beide verjaardagsregels (y=202 en y=220) staan er los onder,
    # binnen het scherm van 240px hoog.
    assert _ink_in_band(img, 200, 216) > 0
    assert _ink_in_band(img, 218, 234) > 0


def test_festive_mode_on_birthday_today():
    """Op de verjaardag zelf: feestweergave (ballonnen) i.p.v. kledingadvies."""
    occ = [Occurrence("Ighone", date(2026, 7, 7), 0, "birthday", 5)]
    img = _open(create_image(WEATHER, occ, "Harderwijk"))
    assert img.size == (IMG_W, IMG_H)
    # De roze ballon-kleur komt alleen in de feestweergave voor.
    assert _has_color(img, PARTY_PINK)


def test_festive_mode_handles_birthday_without_age():
    """Een verjaardag zonder geboortejaar (MM-DD) mag ook feestelijk renderen."""
    occ = [Occurrence("Oma", date(2026, 7, 7), 0, "birthday", None)]
    img = _open(create_image(WEATHER, occ, "Harderwijk"))
    assert img.size == (IMG_W, IMG_H)
    assert _has_color(img, PARTY_PINK)


def test_no_festive_mode_when_birthday_is_not_today():
    """Verjaardag over 6 dagen → gewone weergave, geen ballonnen."""
    occ = [Occurrence("Ighone", date(2026, 7, 7), 6, "birthday", 5)]
    img = _open(create_image(WEATHER, occ, "Harderwijk"))
    assert not _has_color(img, PARTY_PINK)
    assert _ink_in_band(img, 136, 173) > 0  # kledingadvies staat er wel
