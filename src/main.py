from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path

from src.bot import create_bot
from src.config import Config
from src.db import Database
from src.scheduler import MorningScheduler
from src.services.calendar_service import CalendarService
from src.services.daily_summary_service import DailySummaryService
from src.services.geocoding_service import GeocodingService
from src.services.weather_service import WeatherService


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def bootstrap_runtime_files(config: Config) -> None:
    # Ensure parent directories exist for file-based runtime state/secrets.
    for path in (
        config.database_path,
        config.google_client_secret_file,
        config.google_token_file,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

    _materialize_json_file_if_missing(
        target_path=config.google_client_secret_file,
        direct_env_key="GOOGLE_CLIENT_SECRET_JSON",
        b64_env_key="GOOGLE_CLIENT_SECRET_JSON_B64",
        required=False,
    )
    _materialize_json_file_if_missing(
        target_path=config.google_token_file,
        direct_env_key="GOOGLE_TOKEN_JSON",
        b64_env_key="GOOGLE_TOKEN_JSON_B64",
        required=False,
    )


def _materialize_json_file_if_missing(
    *,
    target_path: Path,
    direct_env_key: str,
    b64_env_key: str,
    required: bool,
) -> None:
    logger = logging.getLogger(__name__)
    if target_path.exists():
        return

    raw_text = (os.getenv(direct_env_key) or "").strip()
    raw_b64 = (os.getenv(b64_env_key) or "").strip()

    payload_text: str | None = None
    source_key: str | None = None
    if raw_text:
        payload_text = raw_text
        source_key = direct_env_key
    elif raw_b64:
        try:
            payload_text = base64.b64decode(raw_b64).decode("utf-8")
        except Exception as exc:
            raise ValueError(f"{b64_env_key} のbase64デコードに失敗しました。") from exc
        source_key = b64_env_key

    if payload_text is None:
        if required:
            raise ValueError(
                f"{target_path} が存在せず、{direct_env_key} / {b64_env_key} も未設定です。"
            )
        return

    try:
        parsed = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        key_name = source_key or direct_env_key
        raise ValueError(f"{key_name} に有効なJSONを設定してください。") from exc

    target_path.write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Bootstrapped %s from env var %s", target_path, source_key)


def main() -> None:
    configure_logging()

    config = Config.from_env()
    bootstrap_runtime_files(config)

    db = Database(config.database_path)
    db.init_db()

    calendar_service = CalendarService(
        client_secret_file=config.google_client_secret_file,
        token_file=config.google_token_file,
        default_timezone=config.default_timezone,
    )
    weather_service = WeatherService()
    geocoding_service = GeocodingService()
    daily_summary_service = DailySummaryService(
        calendar_service=calendar_service,
        weather_service=weather_service,
    )

    bot = create_bot(
        config=config,
        db=db,
        calendar_service=calendar_service,
        weather_service=weather_service,
        geocoding_service=geocoding_service,
        daily_summary_service=daily_summary_service,
    )
    bot.morning_scheduler = MorningScheduler(
        bot=bot,
        db=db,
        daily_summary_service=daily_summary_service,
    )

    bot.run(config.discord_bot_token)


if __name__ == "__main__":
    main()
