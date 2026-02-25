from __future__ import annotations

from typing import Any

import requests

from src.utils.weather_code_map import weather_code_to_japanese


class WeatherServiceError(RuntimeError):
    pass


class WeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout_sec: float = 10.0):
        self.timeout_sec = timeout_sec

    def get_today_weather(self, *, latitude: float, longitude: float, timezone_name: str) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": timezone_name,
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=self.timeout_sec)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise WeatherServiceError("Open-Meteo Forecast APIの呼び出しに失敗しました。") from exc

        current = payload.get("current") or {}
        daily = payload.get("daily") or {}
        daily_weather_code = _first(daily.get("weather_code"))
        effective_code = current.get("weather_code")
        if effective_code is None:
            effective_code = daily_weather_code

        return {
            "current_temperature": current.get("temperature_2m"),
            "current_weather_code": current.get("weather_code"),
            "weather_code": effective_code,
            "weather_text": weather_code_to_japanese(effective_code),
            "temperature_max": _first(daily.get("temperature_2m_max")),
            "temperature_min": _first(daily.get("temperature_2m_min")),
            "precipitation_probability_max": _first(daily.get("precipitation_probability_max")),
            "daily_weather_code": daily_weather_code,
            "latitude": payload.get("latitude", latitude),
            "longitude": payload.get("longitude", longitude),
            "timezone": payload.get("timezone", timezone_name),
        }


def _first(values: Any) -> Any:
    if isinstance(values, list) and values:
        return values[0]
    return None
