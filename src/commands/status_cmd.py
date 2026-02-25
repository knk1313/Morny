from __future__ import annotations

import discord

from src.db import UserSettings
from src.utils.formatters import format_status_message


def register(bot) -> None:
    @bot.tree.command(name="status", description="現在の設定を表示")
    async def status_command(interaction: discord.Interaction) -> None:
        user_id = str(interaction.user.id)
        settings = bot.db.get_user_settings(user_id) or UserSettings.empty(
            user_id, bot.config.default_timezone
        )
        await interaction.response.send_message(format_status_message(settings))
