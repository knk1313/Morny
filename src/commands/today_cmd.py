from __future__ import annotations

import logging

import discord

from src.db import UserSettings
from src.utils.formatters import format_daily_report

logger = logging.getLogger(__name__)


def register(bot) -> None:
    @bot.tree.command(name="today", description="今日の予定と天気を表示")
    async def today_command(interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        user_id = str(interaction.user.id)
        settings = bot.db.get_user_settings(user_id) or UserSettings.empty(
            user_id, bot.config.default_timezone
        )

        try:
            summary = await bot.daily_summary_service.build_summary_async(settings)
            message = format_daily_report(settings, summary)
            await interaction.followup.send(message)
        except Exception:
            logger.exception("/today failed user=%s", user_id)
            await interaction.followup.send("❌ 予期しないエラーが発生しました。しばらくしてから再試行してください。")
