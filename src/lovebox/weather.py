"""Weersverwachting ophalen (Open-Meteo, gratis, geen API-key) + kledingadvies."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

import requests

# WMO-weercodes → omschrijving (geen emoji's; DejaVu rendert die niet)
WEATHER_DESC = {
    0: "Helder",
    1: "Licht bewolkt",
    2: "Halfbewolkt",
    3: "Bewolkt",
    45: "Mist",
    48: "Rijpmist",
    51: "Lichte motregen",
    53: "Motregen",
    55: "Zware motregen",
    61: "Lichte regen",
    63: "Regen",
    65: "Zware regen",
    71: "Lichte sneeuw",
    73: "Sneeuw",
    75: "Zware sneeuw",
    80: "Lichte buien",
    81: "Buien",
    82: "Zware buien",
    95: "Onweer",
    96: "Onweer + hagel",
    99: "Zwaar onweer",
}


@dataclass(frozen=True)
class Weather:
    code: int
    temp_max: float
    temp_min: float
    rain_sum: float
    wind_kmh: float
    date: str  # "YYYY-MM-DD"


def weather_description(code: int) -> str:
    return WEATHER_DESC.get(code, f"Weercode {code}")


def clothing_advice(temp_max: float, rain_sum: float, wind_kmh: float) -> list[str]:
    """Korte adviesregels op basis van max-temp, neerslag en windsnelheid."""
    advice: list[str] = []

    if temp_max >= 22:
        advice.append("Korte broek")
    elif temp_max >= 12:
        advice.append("Lange broek")
    else:
        advice.append("Warme broek")

    if temp_max >= 24:
        advice.append("Korte mouwen")
    elif temp_max >= 18:
        advice.append("T-shirt + vest")
    elif temp_max >= 12:
        advice.append("Trui / sweater")
    else:
        advice.append("Warme jas")

    if rain_sum >= 3:
        advice.append("Regenjas mee!")
    elif rain_sum >= 0.5:
        advice.append("Evt. regenjas")

    if wind_kmh >= 50:
        advice.append("Windproof jas")

    return advice


def fetch_weather(
    lat: float, lon: float, *, timezone: str = "Europe/Amsterdam", timeout: float = 10
) -> Weather:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=weathercode,temperature_2m_max,temperature_2m_min"
        ",precipitation_sum,wind_speed_10m_max"
        f"&timezone={quote(timezone)}"
        "&forecast_days=1"
    )
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    d = resp.json()["daily"]
    return Weather(
        code=int(d["weathercode"][0]),
        temp_max=float(d["temperature_2m_max"][0]),
        temp_min=float(d["temperature_2m_min"][0]),
        rain_sum=float(d["precipitation_sum"][0]),
        wind_kmh=float(d["wind_speed_10m_max"][0]),
        date=d["time"][0],
    )
