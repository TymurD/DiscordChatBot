import os
from random import randint
import asyncio
from zoneinfo import ZoneInfo
import json
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
import discord
from discord.ext import commands
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

discord_token = os.getenv("DISCORD_TOKEN")
openrouter_key = os.getenv("OPENROUTER_KEY")

if not discord_token or not openrouter_key:
    raise ValueError(
        'Missing required environment variables. '
        'Please check your .env file.'
    )

try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("config.json not found. "
                            "Ensure it exists in the root directory.")
except json.JSONDecodeError:
    raise ValueError("config.json is not valid JSON.")

chat_model_name = config['model_settings']['chat_model']
chat_model_temperature = config['model_settings']['temperature']
chat_history_limit = config['chat_settings']['history_limit']
recent_chat_history_limit = config['chat_settings']['recent_history_limit']
trigger_words = tuple(config['trigger_words'])
default_instruction = config['prompts']['default_instruction']
persona_instruction = config['prompts']['persona_instruction']
embeddings_model_name = config['model_settings']['embedding_model']
db_path = config['database']['path']
db_collection = config['database']['collection_name']
random_trigger_chance = (config['chat_settings']
                               ['random_response_chance_1_in_x'])


def save_config():
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to save config: {e}")


class OpenRouterEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model_name = embeddings_model_name

    def __call__(self, input: Documents) -> Embeddings:
        response = self.client.embeddings.create(
            input=input,
            model=self.model_name
        )
        return [data.embedding for data in response.data]


embedding_fn = OpenRouterEmbeddingFunction(api_key=openrouter_key)
chroma_client = chromadb.PersistentClient(path=db_path)
chat_history = chroma_client.get_or_create_collection(
    name=db_collection,
    embedding_function=embedding_fn
)


intents = discord.Intents.all()
intents.message_content = True
discord_client = commands.Bot(command_prefix='/', intents=intents)
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key
)


@discord_client.event
async def on_ready():
    print(f'We have logged in as {discord_client.user}')
    await discord_client.tree.sync()
    print('Global application commands synced!')


def add_memory(user, message_content, message_id, timestamp):
    chat_history.upsert(
        documents=[message_content],
        metadatas=[{'user': str(user),
                    'msg_id': str(message_id),
                    'time': str(timestamp)}],
        ids=[str(message_id)]
    )


async def add_memory_async(user, message_content, message_id, timestamp):
    return await asyncio.to_thread(add_memory,
                                   user,
                                   message_content,
                                   message_id,
                                   timestamp)


def get_relevant_context(query_text):
    results = chat_history.query(
        query_texts=[query_text],
        n_results=chat_history_limit
    )

    reconstructed_messages = []

    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        user = meta.get('user', 'Unknown')
        timestamp = meta.get('time', 'Unknown Time')

        full_entry = f"{user}: {doc} ({timestamp})"
        reconstructed_messages.append(full_entry)
    return reconstructed_messages


async def get_relevant_context_async(query_text):
    return await asyncio.to_thread(get_relevant_context, query_text)


def clean_string(input_string):
    if not input_string:
        return ''
    cleaned_string = input_string.strip()
    if not cleaned_string:
        return ''
    cleaned_string = cleaned_string[0].capitalize() + cleaned_string[1:]
    if not cleaned_string.endswith('.'):
        cleaned_string += '.'
    cleaned_string += ' '
    return cleaned_string


@discord_client.tree.command(name="behavior",
                             description="sets the bot's behavior")
async def change_persona(interaction: discord.Interaction,
                         behavior: str = None):
    global persona_instruction
    if behavior is None:
        persona_instruction = ""
        message = "Behavior reset to default."
    else:
        persona_instruction = clean_string(behavior)
        message = persona_instruction
    config['prompts']['persona_instruction'] = persona_instruction
    save_config()
    await interaction.response.send_message(message, ephemeral=True)


@discord_client.tree.command(name="behavior_append",
                             description="appends to the bot's behavior")
async def append_persona(interaction: discord.Interaction, behavior: str):
    global persona_instruction
    persona_instruction += clean_string(behavior)
    config['prompts']['persona_instruction'] = persona_instruction
    save_config()
    await interaction.response.send_message(persona_instruction,
                                            ephemeral=True)


@discord_client.tree.command(name="behavior_show",
                             description="shows the bot's current behavior")
async def show_persona(interaction: discord.Interaction):
    if len(persona_instruction) >= 1900:
        await interaction.response.send_message(
            "Current persona instruction is too long to display.",
            ephemeral=True)
        return
    if not persona_instruction:
        await interaction.response.send_message(
            "No persona instruction set.",
            ephemeral=True)
        return
    await interaction.response.send_message(persona_instruction,
                                            ephemeral=True)


@discord_client.event
async def on_message(message):
    if message.author == discord_client.user:
        return

    msg_timestamp = message.created_at.astimezone(
        ZoneInfo("Europe/Kyiv")
    ).strftime("%Y-%m-%d %H:%M")

    await add_memory_async(
        message.author,
        message.content,
        message.id,
        msg_timestamp
    )

    channel_id = message.channel.id
    message_content_lower = message.content.lower()

    is_triggered_by_word = False
    for word in trigger_words:
        if word in message_content_lower:
            is_triggered_by_word = True
            break

    is_lucky_roll = randint(1, random_trigger_chance) == random_trigger_chance

    if not is_lucky_roll and not is_triggered_by_word:
        return

    placeholder_message = await message.channel.send('...')
    print(f'Bot activated in {channel_id}, by word: {is_triggered_by_word}')

    messages = []
    async for msg in message.channel.history(limit=recent_chat_history_limit + 1):
        if msg.id == placeholder_message.id:
            continue
        msg_time = msg.created_at.astimezone(
            ZoneInfo("Europe/Kyiv")
        ).strftime("%Y-%m-%d %H:%M")
        formatted_message = f'{msg.author}: {msg.content} ({msg_time})'
        messages.append(formatted_message)
    messages.reverse()

    print('Got recent chat history')

    relevant_messages = await get_relevant_context_async(message.content)

    print('Got relevant long-term context')

    all_context = relevant_messages + messages
    formatted_messages = "\n".join(all_context)

    try:
        response = await openrouter_client.chat.completions.create(
            model=chat_model_name,
            temperature=chat_model_temperature,
            messages=[
                {
                    'role': 'system',
                    'content': default_instruction + persona_instruction
                },
                {
                    'role': 'user',
                    'content': f'Messages: {formatted_messages}'
                }
            ],
        )
        print(formatted_messages)

        ai_response_content = response.choices[0].message.content
        try:
            await placeholder_message.delete()
        except discord.NotFound:
            await message.channel.send(
                content='*Tries to speak but you hear only muffled sounds*'
            )
            return
        final_message = await message.channel.send(
            content=ai_response_content
        )
        final_msg_time = final_message.created_at.astimezone(
            ZoneInfo("Europe/Kyiv")
        ).strftime("%Y-%m-%d %H:%M")
        await add_memory_async(final_message.author,
                               final_message.content,
                               final_message.id,
                               final_msg_time)
    except Exception as e:
        print(f"An error occurred with the API call: {e}")
        try:
            await placeholder_message.delete()
        except discord.NotFound:
            await message.channel.send(
                content='*Tries to speak but you hear only muffled sounds*'
            )
            return
        await message.channel.send(content='Error occured')

discord_client.run(discord_token)
