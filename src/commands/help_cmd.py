from __future__ import annotations

import discord

from src.utils.formatters import format_help_message


def register(bot) -> None:
    @bot.tree.command(name="help", description="コマンド一覧を表示")
    async def help_command(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(format_help_message())
