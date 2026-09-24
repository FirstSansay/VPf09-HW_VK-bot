from __future__ import annotations

from typing import Any

from config.settings import Settings
from models.entities import UserState
from services.ai_service import AIService
from services.memory_manager import MemoryManager
from utils.logger import logger


class FactService:
    """Долгосрочные факты о пользователе: извлечение и сохранение."""

    def __init__(
        self,
        ai_service: AIService,
        memory_manager: MemoryManager,
        settings: Settings,
    ) -> None:
        self.ai_service = ai_service
        self.memory_manager = memory_manager
        self.settings = settings

    async def maybe_extract_facts(self, user: UserState) -> None:
        dialog = user.active_dialog
        if dialog is None:
            return

        user.fact_extraction_counter += 1
        if user.fact_extraction_counter < self.settings.fact_extraction_interval:
            return

        user.fact_extraction_counter = 0
        messages = self.memory_manager.build_facts_transcript_messages(dialog)
        if len(messages) < 2:
            return

        transcript = await self.ai_service.build_facts_transcript(messages)
        new_facts = await self.ai_service.extract_facts(transcript)
        if not new_facts:
            return

        known = {fact.lower() for fact in user.long_term_facts}
        added: list[str] = []
        for fact in new_facts:
            if fact.lower() not in known and len(fact) <= 160:
                user.long_term_facts.append(fact)
                known.add(fact.lower())
                added.append(fact)

        if added:
            await self.memory_manager.save_user(user)
            logger.info(
                "Добавлены долгосрочные факты для пользователя %s: %s",
                user.user_id,
                added,
            )