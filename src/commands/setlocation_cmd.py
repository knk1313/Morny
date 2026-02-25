from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands

from src.services.geocoding_service import GeocodingServiceError
from src.utils.validators import looks_like_coordinate_input, parse_lat_lon

logger = logging.getLogger(__name__)


def register(bot) -> None:
    @bot.tree.command(name="setlocation", description="天気取得用の場所を登録")
    @app_commands.describe(location="地名または lat,lon (例: 36.08,140.11)")
    async def setlocation_command(interaction: discord.Interaction, location: str) -> None:
        user_id = str(interaction.user.id)
        text = location.strip()
        if not text:
            await interaction.response.send_message("❌ 地点を入力してください。")
            return

        await interaction.response.defer(thinking=True)

        try:
            parsed = parse_lat_lon(text)
        except ValueError:
            await interaction.followup.send("❌ 緯度経度の範囲が不正です。例: 36.08,140.11")
            return

        if parsed is not None:
            lat, lon = parsed
            bot.db.set_location(
                user_id,
                location_name=text,
                latitude=lat,
                longitude=lon,
            )
            await interaction.followup.send(
                f"✅ 天気取得地点を登録しました: {text} ({lat:.2f}, {lon:.2f})"
            )
            return

        if looks_like_coordinate_input(text):
            await interaction.followup.send("❌ 緯度経度の形式が不正です。例: 36.08,140.11")
            return

        try:
            result = await asyncio.to_thread(bot.geocoding_service.geocode, text)
        except GeocodingServiceError:
            logger.exception("Geocoding failed for input=%s", text)
            await interaction.followup.send("❌ 地名の検索に失敗しました。時間をおいて再試行してください。")
            return

        if result is None:
            await interaction.followup.send("❌ 地名の候補が見つかりませんでした")
            return

        bot.db.set_location(
            user_id,
            location_name=result.location_name,
            latitude=result.latitude,
            longitude=result.longitude,
        )
        await interaction.followup.send(
            "✅ 天気取得地点を登録しました: "
            f"{result.location_name} ({result.latitude:.2f}, {result.longitude:.2f})"
        )
