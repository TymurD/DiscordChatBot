from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


CONFIG_PATH = Path(__file__).parent.parent / 'config.json'


@dataclass
class ModelSettings:
    chat_model: str
    temperature: float
    embedding_model: str


@dataclass
class ChatSettings:
    history_limit: int
    recent_history_limit: int
    random_response_chance_1_in_x: int
    timezone: str

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@dataclass
class DatabaseSettings:
    path: str
    collection_name: str


@dataclass
class Prompts:
    system_instruction: str
    persona_instruction: str


@dataclass
class BotConfig:
    model: ModelSettings
    chat: ChatSettings
    database: DatabaseSettings
    trigger_words: list
    prompts: Prompts

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> BotConfig:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(
            model=ModelSettings(**data['model_settings']),
            chat=ChatSettings(**data['chat_settings']),
            database=DatabaseSettings(**data['database']),
            trigger_words=data['trigger_words'],
            prompts=Prompts(**data['prompts']),
        )

    def save_config(self, path: Path = CONFIG_PATH) -> None:
        data = {
            "model_settings": {
                "chat_model": self.model.chat_model,
                "temperature": self.model.temperature,
                "embedding_model": self.model.embedding_model,
            },
            "chat_settings": {
                "history_limit": self.chat.history_limit,
                "recent_history_limit": self.chat.recent_history_limit,
                "random_response_chance_1_in_x": (
                    self.chat.random_response_chance_1_in_x
                ),
                "timezone": self.chat.timezone,
            },
            "database": {
                "path": self.database.path,
                "collection_name": self.database.collection_name,
            },
            "trigger_words": self.trigger_words,
            "prompts": {
                "system_instruction": self.prompts.system_instruction,
                "persona_instruction": self.prompts.persona_instruction,
            },
        }
        with path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
