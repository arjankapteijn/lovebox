import pytest
import requests

from lovebox.weather import clothing_advice, fetch_weather, weather_description

_DAILY = {
    "daily": {
        "weathercode": [3],
        "temperature_2m_max": [21.0],
        "temperature_2m_min": [15.0],
        "precipitation_sum": [1.2],
        "wind_speed_10m_max": [18.0],
        "time": ["2026-07-14"],
    }
}


class _FakeResp:
    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload or _DAILY

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"{self.status_code}")
            err.response = self
            raise err

    def json(self):
        return self._payload


def test_weather_description_known_and_unknown():
    assert weather_description(0) == "Helder"
    assert weather_description(61) == "Lichte regen"
    assert weather_description(1234) == "Weercode 1234"


def test_clothing_advice_warm_dry():
    advice = clothing_advice(temp_max=26, rain_sum=0, wind_kmh=10)
    assert "Korte broek" in advice
    assert "Korte mouwen" in advice
    assert all("regenjas" not in a.lower() for a in advice)


def test_clothing_advice_cold_wet_windy():
    advice = clothing_advice(temp_max=5, rain_sum=4, wind_kmh=55)
    assert "Warme broek" in advice
    assert "Warme jas" in advice
    assert "Regenjas mee!" in advice
    assert "Windproof jas" in advice


def test_clothing_advice_mild_light_rain():
    advice = clothing_advice(temp_max=15, rain_sum=1.0, wind_kmh=20)
    assert "Lange broek" in advice
    assert "Trui / sweater" in advice
    assert "Evt. regenjas" in advice


def test_clothing_advice_boundaries():
    # precies op de grens 22 -> korte broek, 12 -> lange broek
    assert "Korte broek" in clothing_advice(22, 0, 0)
    assert "Lange broek" in clothing_advice(12, 0, 0)
    assert "Warme broek" in clothing_advice(11, 0, 0)


def test_fetch_weather_retries_on_503_then_succeeds(monkeypatch):
    """Twee keer 503, daarna 200: de retry vangt de tijdelijke storing op."""
    responses = [_FakeResp(503), _FakeResp(503), _FakeResp(200)]
    calls = {"n": 0}

    def fake_get(url, timeout):
        calls["n"] += 1
        return responses.pop(0)

    sleeps: list[float] = []
    monkeypatch.setattr(requests, "get", fake_get)

    weather = fetch_weather(52.0, 5.0, _sleep=sleeps.append)

    assert calls["n"] == 3
    assert weather.temp_max == 21.0
    assert weather.date == "2026-07-14"
    assert sleeps == [2.0, 4.0]  # exponentiële backoff tussen de pogingen


def test_fetch_weather_gives_up_after_retries(monkeypatch):
    """Blijvende 503: na alle pogingen wordt de HTTPError doorgegeven."""
    calls = {"n": 0}

    def fake_get(url, timeout):
        calls["n"] += 1
        return _FakeResp(503)

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        fetch_weather(52.0, 5.0, retries=2, _sleep=lambda _s: None)

    assert calls["n"] == 3  # eerste poging + 2 retries


def test_fetch_weather_does_not_retry_on_404(monkeypatch):
    """Een harde 4xx is blijvend: meteen doorgeven, niet opnieuw proberen."""
    calls = {"n": 0}

    def fake_get(url, timeout):
        calls["n"] += 1
        return _FakeResp(404)

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        fetch_weather(52.0, 5.0, _sleep=lambda _s: None)

    assert calls["n"] == 1
