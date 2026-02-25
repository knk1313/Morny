from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.utils.time_utils import iso_now_utc
from src.utils.validators import parse_stored_calendar_ids


@dataclass(slots=True)
class UserSettings:
    discord_user_id: str
    calendar_id: str | None
    location_name: str | None
    latitude: float | None
    longitude: float | None
    timezone: str
    morning_enabled: int
    morning_time: str
    notify_channel_id: str | None
    created_at: str
    updated_at: str

    @property
    def morning_enabled_bool(self) -> bool:
        return bool(self.morning_enabled)

    @property
    def calendar_ids(self) -> list[str]:
        return parse_stored_calendar_ids(self.calendar_id)

    @classmethod
    def empty(cls, discord_user_id: str, timezone_name: str = "Asia/Tokyo") -> "UserSettings":
        now = iso_now_utc()
        return cls(
            discord_user_id=discord_user_id,
            calendar_id=None,
            location_name=None,
            latitude=None,
            longitude=None,
            timezone=timezone_name,
            morning_enabled=0,
            morning_time="07:30",
            notify_channel_id=None,
            created_at=now,
            updated_at=now,
        )


class Database:
    _ALLOWED_COLUMNS = {
        "calendar_id",
        "location_name",
        "latitude",
        "longitude",
        "timezone",
        "morning_enabled",
        "morning_time",
        "notify_channel_id",
    }

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    discord_user_id TEXT PRIMARY KEY,
                    calendar_id TEXT NULL,
                    location_name TEXT NULL,
                    latitude REAL NULL,
                    longitude REAL NULL,
                    timezone TEXT NOT NULL DEFAULT 'Asia/Tokyo',
                    morning_enabled INTEGER NOT NULL DEFAULT 0,
                    morning_time TEXT NOT NULL DEFAULT '07:30',
                    notify_channel_id TEXT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_user_settings(self, row: sqlite3.Row) -> UserSettings:
        return UserSettings(
            discord_user_id=row["discord_user_id"],
            calendar_id=row["calendar_id"],
            location_name=row["location_name"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            timezone=row["timezone"],
            morning_enabled=row["morning_enabled"],
            morning_time=row["morning_time"],
            notify_channel_id=row["notify_channel_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_user_settings(self, discord_user_id: str) -> UserSettings | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_settings WHERE discord_user_id = ?",
                (discord_user_id,),
            ).fetchone()
        return self._row_to_user_settings(row) if row else None

    def list_morning_enabled_users(self) -> list[UserSettings]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM user_settings WHERE morning_enabled = 1"
            ).fetchall()
        return [self._row_to_user_settings(row) for row in rows]

    def upsert_user_settings(self, discord_user_id: str, **fields: Any) -> None:
        invalid = set(fields) - self._ALLOWED_COLUMNS
        if invalid:
            raise ValueError(f"Unsupported columns in upsert: {sorted(invalid)}")

        now = iso_now_utc()
        columns = ["discord_user_id", "created_at", "updated_at", *fields.keys()]
        placeholders = ", ".join(["?"] * len(columns))
        values = [discord_user_id, now, now, *fields.values()]

        update_parts = [f"{col} = excluded.{col}" for col in fields.keys()]
        update_parts.append("updated_at = excluded.updated_at")
        update_clause = ", ".join(update_parts)

        sql = f"""
            INSERT INTO user_settings ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(discord_user_id) DO UPDATE SET {update_clause}
        """
        with self._connect() as conn:
            conn.execute(sql, values)
            conn.commit()

    def set_calendar_id(self, discord_user_id: str, calendar_id: str) -> None:
        self.upsert_user_settings(discord_user_id, calendar_id=calendar_id)

    def set_location(
        self,
        discord_user_id: str,
        *,
        location_name: str,
        latitude: float,
        longitude: float,
    ) -> None:
        self.upsert_user_settings(
            discord_user_id,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
        )

    def set_morning_on(
        self,
        discord_user_id: str,
        *,
        morning_time: str,
        notify_channel_id: str,
    ) -> None:
        self.upsert_user_settings(
            discord_user_id,
            morning_enabled=1,
            morning_time=morning_time,
            notify_channel_id=notify_channel_id,
        )

    def set_morning_off(self, discord_user_id: str) -> None:
        self.upsert_user_settings(discord_user_id, morning_enabled=0)
