from __future__ import annotations

import asyncio

from vkbottle import Bot

from bot.handlers import Handlers
from config.settings import Settings
from services.ai_service import AIService
from services.dialog_manager import DialogManager
from services.fact_service import FactService
from services.memory_manager import MemoryManager
from storage.json_storage import JsonStorage
from utils.logger import logger


def _validate(settings: Settings) -> None:
    missing: list[str] = []
    if not settings.vk_token:
        missing.append("VK_TOKEN")
    if not settings.openrouter_api_key:
        missing.append("OPENROUTER_API_KEY")
    if missing:
        logger.error(
            "Не заданы обязательные переменные окружения: %s. "
            "Заполните файл .env (пример — .env.example).",
            ", ".join(missing),
        )
        raise SystemExit(1)


async def main() -> None:
    settings = Settings()
    _validate(settings)

    bot = Bot(token=settings.vk_token)

    storage = JsonStorage(settings.users_dir)
    ai_service = AIService(settings)
    dialog_manager = DialogManager(storage, settings)
    memory_manager = MemoryManager(storage, settings)
    fact_service = FactService(ai_service, memory_manager, settings)

    Handlers(
        bot=bot,
        settings=settings,
        ai_service=ai_service,
        dialog_manager=dialog_manager,
        memory_manager=memory_manager,
        fact_service=fact_service,
    ).register()

    logger.info(
        "Бот запущен. Модель: %s (OpenRouter). Хранилище: %s",
        settings.model,
        settings.users_dir,
    )
    await bot.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")