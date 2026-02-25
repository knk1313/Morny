from __future__ import annotations

import discord
from discord import app_commands

from src.utils.validators import parse_calendar_ids, serialize_calendar_ids


def register(bot) -> None:
    @bot.tree.command(name="setcalendar", description="GoogleカレンダーIDを登録")
    @app_commands.describe(calendar_id="例: primary または primary, xxx@group.calendar.google.com")
    async def setcalendar_command(interaction: discord.Interaction, calendar_id: str) -> None:
        calendar_ids = parse_calendar_ids(calendar_id)
        if not calendar_ids:
            await interaction.response.send_message(
                "❌ カレンダーIDが不正です。空文字不可・各IDは255文字以内、複数はカンマ区切りで入力してください。"
            )
            return

        serialized = serialize_calendar_ids(calendar_ids)
        bot.db.set_calendar_id(str(interaction.user.id), serialized)

        if len(calendar_ids) == 1:
            await interaction.response.send_message(f"✅ カレンダーIDを登録しました: {calendar_ids[0]}")
            return

        preview = "\n".join(f"- `{cid}`" for cid in calendar_ids)
        await interaction.response.send_message(
            f"✅ カレンダーIDを {len(calendar_ids)} 件登録しました。\n{preview}"
        )
