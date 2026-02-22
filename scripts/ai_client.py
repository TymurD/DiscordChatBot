from __future__ import annotations
import logging
from openai import AsyncOpenAI

from config import BotConfig

logger = logging.getLogger(__name__)

DISCORD_MAX_MESSAGE_LENGTH = 2000


def _chunk_response(text: str) -> list[str]:
    if len(text) <= DISCORD_MAX_MESSAGE_LENGTH:
        return [text]
    chunks = []
    while text:
        if len(text) <= DISCORD_MAX_MESSAGE_LENGTH:
            chunks.append(text)
            break
        split_at = text.rfind(' ', 0, DISCORD_MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = DISCORD_MAX_MESSAGE_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    return chunks


async def generate_response(
        recent_context: list[str],
        relevant_context: list[str],
        config: BotConfig,
        client: AsyncOpenAI,
) -> list[str]:
    all_context = "\n".join(relevant_context + recent_context)

    response = await client.chat.completions.create(
        model=config.model.chat_model,
        temperature=config.model.temperature,
        messages=[
            {
                "role": "system",
                "content": config.prompts.system_instruction
                        + config.prompts.persona_instruction,
            },
            {
                "role": "user",
                "content": f"Messages: \n{all_context}",
            }
        ],
    )

    content = response.choices[0].message.content or ""
    logger.debug("LLM response (%d chars): %s", len(content), content[:120])
    return _chunk_response(content)
