from __future__ import annotations
import logging
import discord
from discord.ext import commands

from config import BotConfig

logger = logging.getLogger(__name__)


class TemperatureCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config: BotConfig) -> None:
        self.bot = bot
        self.config = config

    @discord.app_commands.command(
        name="temperature",
        description="Set the bot's temperature."
    )
    async def set_temperature(
        self, interaction: discord.Interaction, temperature: float
    ) -> None:
        if not (0.0 <= temperature <= 2.0):
            await interaction.response.send_message(
                "Temperature must be between 0.0 and 2.0", ephemeral=True
            )
            return

        self.config.model.temperature = temperature
        self.config.save_config()
        logger.info(
            f"Temperature set to {temperature} by {interaction.user}"
        )
        await interaction.response.send_message(
            f"Temperature set to {temperature}", ephemeral=True
        )

    @discord.app_commands.command(
        name="temperature_show",
        description="Show the bot's current temperature."
    )
    async def show_temperature(self, interaction: discord.Interaction) -> None:
        temperature = self.config.model.temperature
        await interaction.response.send_message(
            f"Current temperature is {temperature}", ephemeral=True
        )


async def setup(bot: commands.Bot, config: BotConfig) -> None:
    await bot.add_cog(TemperatureCog(bot, config))
