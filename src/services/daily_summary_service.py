from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

from src.db import UserSettings
from src.services.calendar_service import CalendarService, CalendarServiceError
from src.services.weather_service import WeatherService, WeatherServiceError

Status = Literal["ok", "missing", "error"]


@dataclass(slots=True)
class DailySummaryResult:
    calendar_status: Status = "missing"
    weather_status: Status = "missing"
    events: list[dict[str, Any]] = field(default_factory=list)
    weather: dict[str, Any] | None = None
    calendar_error: str | None = None
    weather_error: str | None = None


class DailySummaryService:
    def __init__(self, *, calendar_service: CalendarService, weather_service: WeatherService):
        self.calendar_service = calendar_service
        self.weather_service = weather_service

    async def build_summary_async(self, settings: UserSettings) -> DailySummaryResult:
        return await asyncio.to_thread(self.build_summary, settings)

    def build_summary(self, settings: UserSettings) -> DailySummaryResult:
        result = DailySummaryResult()
        tz_name = settings.timezone or "Asia/Tokyo"

        calendar_ids = settings.calendar_ids
        if calendar_ids:
            calendar_errors: list[str] = []
            aggregated_events: list[dict[str, Any]] = []
            for calendar_id in calendar_ids:
                try:
                    aggregated_events.extend(
                        self.calendar_service.get_today_events(
                            calendar_id=calendar_id,
                            timezone_name=tz_name,
                        )
                    )
                except CalendarServiceError as exc:
                    calendar_errors.append(f"{calendar_id}: {exc}")

            if aggregated_events:
                result.events = sorted(aggregated_events, key=_event_sort_key)
                result.calendar_status = "ok"
                if calendar_errors:
                    result.calendar_error = " / ".join(calendar_errors)
            elif not calendar_errors:
                # 取得成功・予定0件のケースは「未設定」ではなく「予定なし」として扱う。
                result.calendar_status = "ok"
            elif calendar_errors:
                result.calendar_status = "error"
                result.calendar_error = " / ".join(calendar_errors)

        if settings.latitude is not None and settings.longitude is not None:
            try:
                result.weather = self.weather_service.get_today_weather(
                    latitude=settings.latitude,
                    longitude=settings.longitude,
                    timezone_name=tz_name,
                )
                result.weather_status = "ok"
            except WeatherServiceError as exc:
                result.weather_status = "error"
                result.weather_error = str(exc)

        return result


def _event_sort_key(event: dict[str, Any]) -> tuple[int, str, str]:
    if event.get("all_day"):
        return (0, "", str(event.get("summary") or ""))
    start = str(event.get("start") or "")
    return (1, start, str(event.get("summary") or ""))
