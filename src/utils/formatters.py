from __future__ import annotations

from typing import TYPE_CHECKING

from src.db import UserSettings

if TYPE_CHECKING:
    from src.services.daily_summary_service import DailySummaryResult


def format_help_message() -> str:
    return "\n".join(
        [
            "**Morny コマンド一覧**",
            "/today 今日の予定と天気を表示",
            "/setcalendar <calendar_id> 取得対象カレンダーを登録（複数はカンマ区切り）",
            "/setlocation <地名 or 緯度経度> 天気取得用の場所を登録",
            "/morning_on [time] 毎朝通知をON（省略時 07:30）",
            "/morning_off 毎朝通知をOFF",
            "/status 現在の設定を表示",
            "/help コマンド一覧を表示",
        ]
    )


def format_status_message(settings: UserSettings) -> str:
    calendar = _format_calendar_ids(settings)
    if settings.location_name and settings.latitude is not None and settings.longitude is not None:
        location = f"{settings.location_name} ({settings.latitude:.4f}, {settings.longitude:.4f})"
    else:
        location = "未設定"
    notify_status = "ON" if settings.morning_enabled_bool else "OFF"
    channel = f"<#{settings.notify_channel_id}>" if settings.notify_channel_id else "未設定"

    return "\n".join(
        [
            "**現在の設定**",
            f"カレンダー: {calendar}",
            f"場所: {location}",
            f"通知: {notify_status} ({settings.morning_time})",
            f"チャンネル: {channel}",
            f"タイムゾーン: `{settings.timezone}`",
        ]
    )


def format_daily_report(
    settings: UserSettings,
    summary: "DailySummaryResult",
    *,
    morning_mode: bool = False,
    mention_user: bool = False,
) -> str:
    lines: list[str] = []

    if mention_user:
        lines.append(f"<@{settings.discord_user_id}>")
    if morning_mode:
        lines.append("☀️ おはようございます。今日の予定と天気です。")

    lines.extend(_format_weather_section(settings, summary))
    lines.append("")
    lines.extend(_format_calendar_section(summary))

    return "\n".join(lines).strip()


def _format_weather_section(settings: UserSettings, summary: "DailySummaryResult") -> list[str]:
    if summary.weather_status == "missing":
        return [
            "📍 今日の天気",
            "未設定です。`/setlocation <地名 or 緯度経度>` で登録してください。",
        ]

    if summary.weather_status == "error":
        return [
            "📍 今日の天気",
            "❌ 天気の取得に失敗しました。",
        ]

    weather = summary.weather or {}
    location_label = settings.location_name or _fallback_latlon(settings)
    current_temp = _format_number(weather.get("current_temperature"), suffix="℃")
    max_temp = _format_number(weather.get("temperature_max"), suffix="℃")
    min_temp = _format_number(weather.get("temperature_min"), suffix="℃")
    pop = _format_number(weather.get("precipitation_probability_max"), suffix="%")
    weather_text = weather.get("weather_text") or "不明"

    detail_line = f"{weather_text} / {current_temp}（最高 {max_temp}・最低 {min_temp}）"

    lines = [f"📍 今日の天気（{location_label}）", detail_line]
    if pop != "-":
        lines.append(f"降水確率: {pop}")
    return lines


def _format_calendar_section(summary: "DailySummaryResult") -> list[str]:
    if summary.calendar_status == "missing":
        return [
            "📅 今日の予定",
            "未設定です。`/setcalendar <calendar_id>` で登録してください。",
        ]

    if summary.calendar_status == "error":
        return [
            "📅 今日の予定",
            "❌ 予定の取得に失敗しました。",
        ]

    lines = ["📅 今日の予定"]
    if not summary.events:
        lines.append("予定なし")
        return lines

    for event in summary.events:
        lines.append(_format_event_line(event))
    return lines


def _format_event_line(event: dict) -> str:
    summary = event.get("summary") or "(無題)"
    if event.get("all_day"):
        return f"終日 {summary}"

    start = event.get("start")
    end = event.get("end")
    if start and end:
        return f"{start}-{end} {summary}"
    if start:
        return f"{start} {summary}"
    return summary


def _format_calendar_ids(settings: UserSettings) -> str:
    calendar_ids = settings.calendar_ids
    if not calendar_ids:
        return "未設定"
    if len(calendar_ids) == 1:
        return f"`{calendar_ids[0]}`"
    return " / ".join(f"`{calendar_id}`" for calendar_id in calendar_ids)


def _fallback_latlon(settings: UserSettings) -> str:
    if settings.latitude is None or settings.longitude is None:
        return "未設定"
    return f"{settings.latitude:.4f}, {settings.longitude:.4f}"


def _format_number(value: object, *, suffix: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return f"{int(value)}{suffix}"
        return f"{float(value):.1f}{suffix}"
    return f"{value}{suffix}"
