from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ChatMode:
    id: str
    title: str
    system_prompt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MODES: tuple[ChatMode, ...] = (
    ChatMode(
        id="assistant",
        title="Обычный помощник",
        system_prompt=(
            "Ты — дружелюбный и полезный AI-ассистент. Отвечай по делу, "
            "понятно и структурированно. Если не знаешь ответ — честно скажи об этом. "
            "Отвечай на том же языке, на котором к тебе обращаются."
        ),
    ),
    ChatMode(
        id="programmer",
        title="Программист",
        system_prompt=(
            "Ты — опытный senior-разработчик. Помогай с кодом: объясняй решения, "
            "приводи примеры на актуальных версиях языков, обращай внимание на "
            "производительность и безопасность. Сначала кратко объясни подход, затем код."
        ),
    ),
    ChatMode(
        id="teacher",
        title="Преподаватель",
        system_prompt=(
            "Ты — терпеливый преподаватель. Объясняй сложное простыми словами, "
            "разбивай материал на шаги, задавай уточняющие вопросы, приводи примеры "
            "и аналогии, проверяй понимание собеседника."
        ),
    ),
    ChatMode(
        id="business",
        title="Бизнес-консультант",
        system_prompt=(
            "Ты — бизнес-консультант. Дай практичные рекомендации по стратегии, "
            "маркетингу, финансам и управлению. Структурируй ответ, выделяй ключевые "
            "риски и следующие шаги. Ориентируйся на конкретную ситуацию собеседника."
        ),
    ),
    ChatMode(
        id="friend",
        title="Дружелюбный собеседник",
        system_prompt=(
            "Ты — весёлый и заботливый друг. Веди непринуждённую беседу, поддерживай, "
            "интересуйся настроением и делами собеседника. Отвечай тепло и коротко."
        ),
    ),
)

DEFAULT_MODE_ID = "assistant"
DEFAULT_DIALOG_TITLE = "Основной диалог"


def get_mode(mode_id: str) -> ChatMode:
    for mode in MODES:
        if mode.id == mode_id:
            return mode
    return MODES[0]


@dataclass
class Message:
    role: str
    content: str
    timestamp: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", utc_now_iso()),
        )


@dataclass
class Dialog:
    id: str
    title: str
    mode_id: str
    messages: list[Message] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "mode_id": self.mode_id,
            "messages": [message.to_dict() for message in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dialog":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            title=data.get("title", DEFAULT_DIALOG_TITLE),
            mode_id=data.get("mode_id", DEFAULT_MODE_ID),
            messages=[Message.from_dict(item) for item in data.get("messages", [])],
        )


@dataclass
class UserState:
    user_id: int
    dialogs: list[Dialog] = field(default_factory=list)
    active_dialog_id: str = ""
    long_term_facts: list[str] = field(default_factory=list)
    fact_extraction_counter: int = 0
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def active_dialog(self) -> Dialog | None:
        for dialog in self.dialogs:
            if dialog.id == self.active_dialog_id:
                return dialog
        return self.dialogs[0] if self.dialogs else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "dialogs": [dialog.to_dict() for dialog in self.dialogs],
            "active_dialog_id": self.active_dialog_id,
            "long_term_facts": list(self.long_term_facts),
            "fact_extraction_counter": self.fact_extraction_counter,
            "settings": dict(self.settings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserState":
        return cls(
            user_id=data.get("user_id", 0),
            dialogs=[Dialog.from_dict(item) for item in data.get("dialogs", [])],
            active_dialog_id=data.get("active_dialog_id", ""),
            long_term_facts=list(data.get("long_term_facts", [])),
            fact_extraction_counter=int(data.get("fact_extraction_counter", 0)),
            settings=dict(data.get("settings", {})),
        )