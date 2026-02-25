from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.db import Database, UserSettings
from src.services.daily_summary_service import DailySummaryService
from src.utils.formatters import format_daily_report
from src.utils.time_utils import now_in_timezone
from src.utils.validators import is_valid_hhmm

logger = logging.getLogger(__name__)


class MorningScheduler:
    def __init__(self, *, bot, db: Database, daily_summary_service: DailySummaryService, poll_seconds: int = 30):
        self.bot = bot
        self.db = db
        self.daily_summary_service = daily_summary_service
        self.poll_seconds = poll_seconds
        self._scheduler = AsyncIOScheduler(timezone=getattr(bot.config, "default_timezone", "Asia/Tokyo"))
        self._started = False
        self._sent_markers: set[str] = set()

    def start(self) -> None:
        if self._started:
            return
        self._scheduler.add_job(
            self._tick,
            trigger="interval",
            seconds=self.poll_seconds,
            id="morny-morning-tick",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._scheduler.start()
        self._started = True
        logger.info("Morning scheduler started (poll=%ss)", self.poll_seconds)

    def shutdown(self) -> None:
        if not self._started:
            return
        try:
            self._scheduler.shutdown(wait=False)
        except Exception:
            logger.exception("Failed to shutdown scheduler")
        finally:
            self._started = False

    def on_user_settings_updated(self, discord_user_id: str) -> None:
        # ポーリング方式のためDB変更は次回tickで自動反映される。
        # 当日送信済みマーカーを消すと同日二重送信の原因になるので、ここでは何もしない。
        _ = discord_user_id

    async def _tick(self) -> None:
        if not self.bot.is_ready():
            return

        users = self.db.list_morning_enabled_users()
        for settings in users:
            try:
                await self._maybe_send_for_user(settings)
            except Exception:
                logger.exception("Morning notification job failed for user=%s", settings.discord_user_id)

        self._cleanup_markers(users)

    async def _maybe_send_for_user(self, settings: UserSettings) -> None:
        if not settings.notify_channel_id:
            return
        if not is_valid_hhmm(settings.morning_time):
            logger.warning("Skip invalid morning_time user=%s time=%s", settings.discord_user_id, settings.morning_time)
            return

        now_local = now_in_timezone(settings.timezone or "Asia/Tokyo")
        if now_local.strftime("%H:%M") != settings.morning_time:
            return

        marker = f"{settings.discord_user_id}:{now_local.date().isoformat()}"
        if marker in self._sent_markers:
            return

        channel = await self._resolve_channel(settings.notify_channel_id)
        if channel is None:
            logger.warning(
                "Notify channel not found user=%s channel_id=%s",
                settings.discord_user_id,
                settings.notify_channel_id,
            )
            return

        summary = await self.daily_summary_service.build_summary_async(settings)
        content = format_daily_report(settings, summary, morning_mode=True, mention_user=True)
        await channel.send(content)
        self._sent_markers.add(marker)
        logger.info(
            "Morning notification sent user=%s channel=%s date=%s",
            settings.discord_user_id,
            settings.notify_channel_id,
            now_local.date().isoformat(),
        )

    async def _resolve_channel(self, channel_id_str: str):
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            return None

        channel = self.bot.get_channel(channel_id)
        if channel is not None:
            return channel

        try:
            return await self.bot.fetch_channel(channel_id)
        except Exception:
            logger.exception("Failed to fetch channel %s", channel_id)
            return None

    def _cleanup_markers(self, users: list[UserSettings]) -> None:
        if not self._sent_markers:
            return
        cutoff_dates = set()
        for settings in users:
            now_local = now_in_timezone(settings.timezone or "Asia/Tokyo")
            cutoff_dates.add((now_local - timedelta(days=2)).date().isoformat())
        if not cutoff_dates:
            now_local = now_in_timezone(getattr(self.bot.config, "default_timezone", "Asia/Tokyo"))
            cutoff_dates.add((now_local - timedelta(days=2)).date().isoformat())
        min_cutoff = min(cutoff_dates)
        kept = set()
        for marker in self._sent_markers:
            try:
                _, date_str = marker.split(":", 1)
            except ValueError:
                continue
            if date_str >= min_cutoff:
                kept.add(marker)
        self._sent_markers = kept
