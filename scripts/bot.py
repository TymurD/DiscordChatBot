from __future__ import annotations
import logging
import os
from random import randint

import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import AsyncOpenAI

from config import BotConfig
from memory import MemoryStore
from ai_client import generate_response
from cogs.behavior import setup as setup_behavior
from cogs.temperature import setup as setup_temperature
from cogs.tokens_limit import setup as setup_tokens_limit


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


discord_token = _require_env("DISCORD_TOKEN")
openrouter_key = _require_env("OPENROUTER_KEY")

config = BotConfig.load()
memory = MemoryStore(config, api_key=openrouter_key)
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready() -> None:
    await setup_behavior(bot, config)
    await setup_temperature(bot, config)
    await setup_tokens_limit(bot, config)
    await bot.tree.sync()
    logger.info("Logged in as %s", bot.user)


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return

    timestamp = message.created_at.astimezone(
        config.chat.tz
    ).strftime("%Y-%m-%d %H:%M:%S")
    await memory.add_async(
        user=str(message.author),
        content=message.content,
        message_id=str(message.id),
        timestamp=timestamp,
    )

    content_lower = message.content.lower()
    triggered_by_word = any(
        word in content_lower for word in config.trigger_words
    )
    lucky_roll = randint(1, config.chat.random_response_chance_1_in_x) == 1

    if not triggered_by_word and not lucky_roll:
        await bot.process_commands(message)
        return

    logger.info(
        "Activated in #%s (trigger_word=%s, lucky=%s)",
        message.channel, triggered_by_word, lucky_roll,
    )

    placeholder = await message.channel.send("...")

    logger.info("Placeholder message sent with ID %s", placeholder.id)

    recent: list[str] = []
    recent_ids: list[str] = []
    async for msg in message.channel.history(
        limit=config.chat.recent_history_limit
    ):
        if msg.id == placeholder.id:
            continue
        msg_time = msg.created_at.astimezone(
            config.chat.tz
        ).strftime("%Y-%m-%d %H:%M:%S")
        recent.append(f"{msg.author}: {msg.content} ({msg_time})")
        recent_ids.append(str(msg.id))
    recent.reverse()

    logger.info("Fetched %d recent messages for context", len(recent))

    relevant = await memory.query_async(
        message.content,
        exclude_ids=recent_ids
    )

    logger.info("Retrieved %d relevant messages from memory", len(relevant))
    logger.info("Generating response")

    try:
        chunks = await generate_response(
            recent_context=recent,
            relevant_context=relevant,
            config=config,
            client=openrouter_client,
        )
    except Exception:
        logger.exception("LLM call failed")
        await placeholder.delete()
        await message.channel.send(
            "*Tries to speak but you hear only muffled sounds*"
        )
        await bot.process_commands(message)
        return

    logger.info("Generated response in %d chunks", len(chunks))

    try:
        await placeholder.delete()
        logger.info("Placeholder message deleted")
    except Exception:
        logger.warning("Someone deleted the placeholder message")
        await message.channel.send(
            "*Tries to speak but you hear only muffled sounds*"
        )
        await bot.process_commands(message)
        return

    for chunk in chunks:
        sent = await message.channel.send(chunk)
        sent_time = sent.created_at.astimezone(
            config.chat.tz
        ).strftime("%Y-%m-%d %H:%M:%S")
        await memory.add_async(
            user=str(sent.author),
            content=sent.content,
            message_id=sent.id,
            timestamp=sent_time,
        )

    await bot.process_commands(message)

bot.run(discord_token, log_handler=None)
