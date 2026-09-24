from __future__ import annotations

from typing import Any

from config.settings import Settings
from models.entities import Dialog, Message, UserState
from storage.json_storage import JsonStorage


class MemoryManager:
    """Краткосрочная память: история сообщений, обрезка и формирование контекста."""

    def __init__(self, storage: JsonStorage, settings: Settings) -> None:
        self.storage = storage
        self.settings = settings

    async def get_user(self, user_id: int) -> UserState:
        return await self.storage.get_user(user_id)

    async def save_user(self, user: UserState) -> None:
        await self.storage.save_user(user)

    def append_message(
        self,
        user: UserState,
        dialog: Dialog,
        role: str,
        content: str,
    ) -> None:
        dialog.messages.append(Message(role=role, content=content))
        self.trim_history(dialog)

    def trim_history(self, dialog: Dialog) -> None:
        limit = self.settings.max_history_messages
        if len(dialog.messages) > limit:
            excess = len(dialog.messages) - limit
            del dialog.messages[:excess]

    def clear_history(self, dialog: Dialog) -> None:
        dialog.messages.clear()

    def build_ai_messages(self, dialog: Dialog) -> list[dict[str, str]]:
        return [
            {"role": message.role, "content": message.content}
            for message in dialog.messages
            if message.content.strip()
        ]

    def build_facts_transcript_messages(self, dialog: Dialog) -> list[dict[str, Any]]:
        return [
            {"role": message.role, "content": message.content}
            for message in dialog.messages
            if message.role in {"user", "assistant"} and message.content.strip()
        ]