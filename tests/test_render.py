from datetime import date
from io import BytesIO

from PIL import Image

from lovebox.events import Occurrence
from lovebox.render import IMG_H, IMG_W, create_image
from lovebox.weather import Weather

WEATHER = Weather(code=61, temp_max=18, temp_min=11, rain_sum=2.0, wind_kmh=25, date="2026-07-01")


def _open(png_bytes):
    return Image.open(BytesIO(png_bytes))


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
