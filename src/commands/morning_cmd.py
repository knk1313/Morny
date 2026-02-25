from __future__ import annotations

import discord
from discord import app_commands

from src.utils.validators import is_valid_hhmm

DEFAULT_MORNING_TIME = "07:30"


def register(bot) -> None:
    @bot.tree.command(name="morning_on", description="毎朝通知をONにする")
    @app_commands.describe(time="HH:MM（省略時 07:30）")
    async def morning_on_command(interaction: discord.Interaction, time: str | None = None) -> None:
        if interaction.channel_id is None:
            await interaction.response.send_message("❌ サーバーのチャンネルで実行してください。")
            return

        notify_time = (time or DEFAULT_MORNING_TIME).strip()
        if not is_valid_hhmm(notify_time):
            await interaction.response.send_message("❌ 時刻の形式が不正です。例: 07:30")
            return

        bot.db.set_morning_on(
            str(interaction.user.id),
            morning_time=notify_time,
            notify_channel_id=str(interaction.channel_id),
        )
        if bot.morning_scheduler:
            bot.morning_scheduler.on_user_settings_updated(str(interaction.user.id))

        await interaction.response.send_message(
            f"✅ 毎朝通知をONにしました（{notify_time}）。このチャンネルに送信します。"
        )

    @bot.tree.command(name="morning_off", description="毎朝通知をOFFにする")
    async def morning_off_command(interaction: discord.Interaction) -> None:
        bot.db.set_morning_off(str(interaction.user.id))
        if bot.morning_scheduler:
            bot.morning_scheduler.on_user_settings_updated(str(interaction.user.id))
        await interaction.response.send_message("✅ 毎朝通知をOFFにしました。")
