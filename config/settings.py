from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw is not None and raw.strip() else default
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw is not None and raw.strip() else default
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    vk_token: str = os.getenv("VK_TOKEN", "")
    vk_group_id: int = _get_int("VK_GROUP_ID", 0)
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    model: str = os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-v4-flash-0731")
    temperature: float = _get_float("AI_TEMPERATURE", 0.7)
    max_history_messages: int = _get_int("MAX_HISTORY_MESSAGES", 100)
    max_message_length: int = _get_int("MAX_MESSAGE_LENGTH", 4000)
    fact_extraction_interval: int = _get_int("FACT_EXTRACTION_INTERVAL", 6)
    users_dir: Path = Path(os.getenv("USERS_DIR", str(BASE_DIR / "users")))