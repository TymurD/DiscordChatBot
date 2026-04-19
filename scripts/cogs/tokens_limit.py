from __future__ import annotations
import logging
import discord
from discord.ext import commands

from config import BotConfig

logger = logging.getLogger(__name__)

class TokensLimitCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config: BotConfig) -> None:
        self.bot = bot
        self.config = config

    @discord.app_commands.command(
        name="tokens_limit",
        description="Set the maximum tokens for the bot's responses."
    )
    async def set_tokens_limit(
        self, interaction: discord.Interaction, tokens_limit: int
    ) -> None:
        if tokens_limit <= 0:
            await interaction.response.send_message(
                "Tokens limit must be >= 1", ephemeral=True
            )
            return

        self.config.chat.max_response_tokens = tokens_limit
        self.config.save_config()
        logger.info(
            f"Max response tokens set to {tokens_limit} by {interaction.user}"
        )
        await interaction.response.send_message(
            f"Max response tokens set to {tokens_limit}", ephemeral=True
        )
    
    @discord.app_commands.command(
        name="tokens_limit_show",
        description="Show the bot's current maximum tokens for responses."
    )
    async def show_tokens_limit(self, interaction: discord.Interaction) -> None:
        tokens_limit = self.config.chat.max_response_tokens
        await interaction.response.send_message(
            f"Current max response tokens is {tokens_limit}", ephemeral=True
        )

async def setup(bot: commands.Bot, config: BotConfig) -> None:
    await bot.add_cog(TokensLimitCog(bot, config))