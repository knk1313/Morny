from __future__ import annotations

from dataclasses import dataclass

import requests


class GeocodingServiceError(RuntimeError):
    pass


@dataclass(slots=True)
class GeocodingResult:
    location_name: str
    latitude: float
    longitude: float


class GeocodingService:
    BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self, timeout_sec: float = 10.0):
        self.timeout_sec = timeout_sec

    def geocode(self, query: str) -> GeocodingResult | None:
        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "name": query,
                    "count": 1,
                    "language": "ja",
                    "format": "json",
                },
                timeout=self.timeout_sec,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise GeocodingServiceError("Open-Meteo Geocoding APIの呼び出しに失敗しました。") from exc

        results = payload.get("results") or []
        if not results:
            return None

        item = results[0]
        lat = float(item["latitude"])
        lon = float(item["longitude"])
        location_name = self._build_location_name(item)
        return GeocodingResult(location_name=location_name, latitude=lat, longitude=lon)

    def _build_location_name(self, item: dict) -> str:
        parts = []
        for key in ("name", "admin1", "country"):
            value = item.get(key)
            if value and value not in parts:
                parts.append(str(value))
        return " / ".join(parts) if parts else "不明な地点"
