from __future__ import annotations
import logging
import discord
from discord.ext import commands

from config import BotConfig

logger = logging.getLogger(__name__)

DISCORD_MAX_MESSAGE_LENGTH = 2000


def _clean_instruction(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if not text.endswith((".", "!", "?")):
        text += "."
    return text + " "


class BehaviorCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config: BotConfig) -> None:
        self.bot = bot
        self.config = config

    @discord.app_commands.command(
        name="behavior",
        description="Set the bot's persona. Leave empty to reset to default."
    )
    async def set_behavior(
        self, interaction: discord.Interaction, behavior: str | None = None
    ) -> None:
        if behavior is None:
            self.config.prompts.persona_instruction = ""
            reply = "Persona reset to default."
        else:
            self.config.prompts.persona_instruction = _clean_instruction(
                behavior
            )
            reply = self.config.prompts.persona_instruction

        self.config.save_config()
        logger.info("Persona set by %s", interaction.user)
        await interaction.response.send_message(reply, ephemeral=True)

    @discord.app_commands.command(
        name="behavior_append",
        description="Append text to the bot's current persona."
    )
    async def append_behavior(
        self, interaction: discord.Interaction, behavior: str
    ) -> None:
        self.config.prompts.persona_instruction += _clean_instruction(behavior)
        self.config.save_config()
        logger.info("Persona appended by %s", interaction.user)
        await interaction.response.send_message(
            self.config.prompts.persona_instruction, ephemeral=True
        )

    @discord.app_commands.command(
        name='behavior_show',
        description="Show the bot's current persona instruction."
    )
    async def show_behavior(self, interaction: discord.Interaction) -> None:
        persona = self.config.prompts.persona_instruction
        if not persona:
            reply = "No persona instruction set."
        elif len(persona) > DISCORD_MAX_MESSAGE_LENGTH:
            reply = "Current persona instruction is too long to display."
        else:
            reply = persona
        await interaction.response.send_message(reply, ephemeral=True)


async def setup(bot: commands.Bot, config: BotConfig) -> None:
    await bot.add_cog(BehaviorCog(bot, config))
