from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from src.commands import register_all_commands

if TYPE_CHECKING:
    from src.config import Config
    from src.db import Database
    from src.scheduler import MorningScheduler
    from src.services.calendar_service import CalendarService
    from src.services.daily_summary_service import DailySummaryService
    from src.services.geocoding_service import GeocodingService
    from src.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


class MornyBot(commands.Bot):
    def __init__(
        self,
        *,
        config: "Config",
        db: "Database",
        calendar_service: "CalendarService",
        weather_service: "WeatherService",
        geocoding_service: "GeocodingService",
        daily_summary_service: "DailySummaryService",
    ):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

        self.config = config
        self.db = db
        self.calendar_service = calendar_service
        self.weather_service = weather_service
        self.geocoding_service = geocoding_service
        self.daily_summary_service = daily_summary_service
        self.morning_scheduler: "MorningScheduler | None" = None

        register_all_commands(self)

    async def setup_hook(self) -> None:
        if self.config.discord_guild_id:
            guild = discord.Object(id=self.config.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Synced %d commands to guild %s", len(synced), self.config.discord_guild_id)
        else:
            synced = await self.tree.sync()
            logger.info("Synced %d global commands", len(synced))

        if self.morning_scheduler:
            self.morning_scheduler.start()

    async def on_ready(self) -> None:
        if self.user:
            logger.info("Logged in as %s (%s)", self.user, self.user.id)

    async def close(self) -> None:
        if self.morning_scheduler:
            self.morning_scheduler.shutdown()
        await super().close()


def create_bot(
    *,
    config: "Config",
    db: "Database",
    calendar_service: "CalendarService",
    weather_service: "WeatherService",
    geocoding_service: "GeocodingService",
    daily_summary_service: "DailySummaryService",
) -> MornyBot:
    return MornyBot(
        config=config,
        db=db,
        calendar_service=calendar_service,
        weather_service=weather_service,
        geocoding_service=geocoding_service,
        daily_summary_service=daily_summary_service,
    )
