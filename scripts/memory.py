from __future__ import annotations
import asyncio
from pathlib import Path
from openai import OpenAI
from chromadb import Documents, EmbeddingFunction, Embeddings
import chromadb

from config import BotConfig


class OpenRouterEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, model_name: str) -> None:
        self.client = OpenAI(
            base_url='https://openrouter.ai/api/v1',
            api_key=api_key
        )
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        response = self.client.embeddings.create(
            input=input,
            model=self.model_name
        )
        return [item.embedding for item in response.data]


class MemoryStore:
    def __init__(self, config: BotConfig, api_key: str) -> None:
        embedding_fn = OpenRouterEmbeddingFunction(
            api_key=api_key,
            model_name=config.model.embedding_model
        )
        Path(config.database.path).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=config.database.path)
        self.collection = client.get_or_create_collection(
            name=config.database.collection_name,
            embedding_function=embedding_fn
        )
        self.history_limit = config.chat.history_limit

    def add(self,
            user: str,
            content: str,
            message_id: int,
            timestamp: str) -> None:
        self.collection.upsert(
            documents=[content],
            metadatas=[{
                'user': user,
                'msg_id': str(message_id),
                'time': timestamp
            }],
            ids=[str(message_id)]
        )

    def query(self, text: str,
              exclude_ids: set[str] | None = None) -> list[dict]:
        results = self.collection.query(
            query_texts=[text],
            n_results=self.history_limit,
        )
        messages = []
        for doc, meta in zip(results["documents"][0],
                             results["metadatas"][0]):
            if exclude_ids and meta["msg_id"] in exclude_ids:
                continue
            messages.append(f"{meta['user']}: {doc} ({meta['time']})")
        return messages

    async def add_async(
            self,
            user: str,
            content: str,
            message_id: int,
            timestamp: str) -> None:
        await asyncio.to_thread(
            self.add,
            user,
            content,
            message_id,
            timestamp
        )

    async def query_async(
            self,
            text: str,
            exclude_ids: set[str] | None = None
    ) -> list[dict]:
        return await asyncio.to_thread(self.query, text, exclude_ids)
