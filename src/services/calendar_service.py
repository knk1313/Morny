from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.utils.time_utils import format_hhmm, parse_iso_datetime_to_local, today_bounds_rfc3339


class CalendarServiceError(RuntimeError):
    pass


class CalendarService:
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def __init__(self, *, client_secret_file: Path, token_file: Path, default_timezone: str = "Asia/Tokyo"):
        self.client_secret_file = Path(client_secret_file)
        self.token_file = Path(token_file)
        self.default_timezone = default_timezone

    def get_today_events(self, *, calendar_id: str, timezone_name: str | None = None) -> list[dict[str, Any]]:
        tz_name = timezone_name or self.default_timezone
        time_min, time_max = today_bounds_rfc3339(tz_name)

        try:
            service = self._build_service()
            result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    timeZone=tz_name,
                )
                .execute()
            )
        except HttpError as exc:
            raise CalendarServiceError("Google Calendar APIの呼び出しに失敗しました。") from exc
        except Exception as exc:
            raise CalendarServiceError("Google Calendarの認証または取得処理に失敗しました。") from exc

        items = result.get("items", [])
        return [self._normalize_event(item, tz_name) for item in items]

    def _build_service(self):
        credentials = self._get_credentials()
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def _get_credentials(self) -> Credentials:
        if not self.client_secret_file.exists() and not self.token_file.exists():
            raise CalendarServiceError(
                "credentials.json / token.json が見つかりません。Google Calendar連携の設定を確認してください。"
            )

        creds: Credentials | None = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.SCOPES)

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
            return creds

        if not self.client_secret_file.exists():
            raise CalendarServiceError("GOOGLE_CLIENT_SECRET_FILE が見つかりません。")

        flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secret_file), self.SCOPES)
        creds = flow.run_local_server(port=0)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def _normalize_event(self, item: dict[str, Any], tz_name: str) -> dict[str, Any]:
        summary = item.get("summary") or "(無題)"
        start_info = item.get("start") or {}
        end_info = item.get("end") or {}

        if start_info.get("date"):
            return {
                "start": None,
                "end": None,
                "summary": summary,
                "all_day": True,
            }

        start_dt_raw = start_info.get("dateTime")
        end_dt_raw = end_info.get("dateTime")
        if not start_dt_raw:
            return {
                "start": None,
                "end": None,
                "summary": summary,
                "all_day": False,
            }

        start_dt = parse_iso_datetime_to_local(start_dt_raw, tz_name)
        end_dt = parse_iso_datetime_to_local(end_dt_raw, tz_name) if end_dt_raw else None

        return {
            "start": format_hhmm(start_dt),
            "end": format_hhmm(end_dt) if end_dt else None,
            "summary": summary,
            "all_day": False,
        }
