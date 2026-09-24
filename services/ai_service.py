from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from config.settings import OPENROUTER_BASE_URL, Settings
from utils.logger import logger

FALLBACK_RESPONSE = (
    "Не удалось получить ответ от модели. Попробуйте повторить запрос чуть позже."
)

FACT_EXTRACTION_PROMPT = (
    "Ты — модуль, который извлекает долгосрочные факты о пользователе из диалога. "
    "Верни ТОЛЬКО список новых устойчивых фактов: имя, возраст, город, профессия, "
    "интересы, предпочтения, цели, важные обстоятельства. Каждый факт — с новой строки, "
    "начинающейся с дефиса. Не выдумывай факты, которых нет в диалоге. Если фактов нет — "
    "верни пустой ответ."
)


class AIService:
    """Слой работы с LLM через OpenRouter (OpenAI-совместимый API)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=OPENROUTER_BASE_URL,
        )

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        payload: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        payload.extend(messages)

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.model,
                messages=payload,
                temperature=self.settings.temperature,
            )
        except Exception as exc:
            logger.exception("Ошибка запроса к OpenRouter: %s", exc)
            return FALLBACK_RESPONSE

        usage = response.usage
        if usage is not None:
            logger.info(
                "Токены: prompt=%s, completion=%s, total=%s",
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            logger.warning("Модель вернула пустой ответ")
            return FALLBACK_RESPONSE
        return content.strip()

    async def extract_facts(self, transcript: str) -> list[str]:
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.model,
                messages=[
                    {"role": "system", "content": FACT_EXTRACTION_PROMPT},
                    {"role": "user", "content": transcript},
                ],
                temperature=0.0,
            )
        except Exception as exc:
            logger.warning("Не удалось извлечь факты: %s", exc)
            return []

        content = response.choices[0].message.content if response.choices else None
        if not content:
            return []

        facts: list[str] = []
        for line in content.splitlines():
            line = line.strip().lstrip("-•").strip()
            if line and line.lower() not in {"нет", "нет фактов", "пустой ответ", "нет данных"}:
                facts.append(line)
        return facts

    async def build_facts_transcript(
        self, messages: list[dict[str, Any]]
    ) -> str:
        lines: list[str] = []
        for message in messages:
            role = "Пользователь" if message["role"] == "user" else "Бот"
            lines.append(f"{role}: {message['content']}")
        return "\n".join(lines[-30:])