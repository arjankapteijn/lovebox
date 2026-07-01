from lovebox.weather import clothing_advice, weather_description


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
