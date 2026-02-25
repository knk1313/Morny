from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Config:
    discord_bot_token: str
    discord_guild_id: int | None
    google_client_secret_file: Path
    google_token_file: Path
    database_path: Path
    default_timezone: str

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()

        token = (os.getenv("DISCORD_BOT_TOKEN") or "").strip()
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN が未設定です。")

        guild_raw = (os.getenv("DISCORD_GUILD_ID") or "").strip()
        guild_id = int(guild_raw) if guild_raw else None

        client_secret = Path(
            (os.getenv("GOOGLE_CLIENT_SECRET_FILE") or "./credentials.json").strip()
        ).expanduser()
        token_file = Path((os.getenv("GOOGLE_TOKEN_FILE") or "./token.json").strip()).expanduser()
        database_path = Path((os.getenv("DATABASE_PATH") or "./data/bot.db").strip()).expanduser()
        default_timezone = (os.getenv("DEFAULT_TIMEZONE") or "Asia/Tokyo").strip() or "Asia/Tokyo"

        return cls(
            discord_bot_token=token,
            discord_guild_id=guild_id,
            google_client_secret_file=client_secret,
            google_token_file=token_file,
            database_path=database_path,
            default_timezone=default_timezone,
        )
