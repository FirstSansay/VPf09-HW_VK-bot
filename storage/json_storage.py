from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from models.entities import DEFAULT_DIALOG_TITLE, DEFAULT_MODE_ID, UserState
from utils.logger import logger


class JsonStorage:
    """Хранение состояния пользователей в JSON-файлах (папка users/)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: dict[int, asyncio.Lock] = {}
        self._cache: dict[int, UserState] = {}
        self._loaded: set[int] = set()

    def _file_path(self, user_id: int) -> Path:
        return self.root / f"{user_id}.json"

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        lock = self._locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[user_id] = lock
        return lock

    @staticmethod
    def _default_state(user_id: int) -> UserState:
        dialog = JsonStorage._new_dialog()
        state = UserState(
            user_id=user_id,
            dialogs=[dialog],
            active_dialog_id=dialog.id,
        )
        return state

    @staticmethod
    def _new_dialog(title: str = DEFAULT_DIALOG_TITLE) -> Any:
        from models.entities import Dialog
        import uuid

        return Dialog(id=uuid.uuid4().hex, title=title, mode_id=DEFAULT_MODE_ID)

    async def get_user(self, user_id: int) -> UserState:
        async with self._lock_for(user_id):
            if user_id not in self._loaded:
                state = self._load_from_disk(user_id)
                self._cache[user_id] = state
                self._loaded.add(user_id)
            return self._cache[user_id]

    async def save_user(self, user: UserState) -> None:
        async with self._lock_for(user.user_id):
            self._cache[user.user_id] = user
            self._write_to_disk(user)

    def _load_from_disk(self, user_id: int) -> UserState:
        path = self._file_path(user_id)
        if not path.exists():
            return self._default_state(user_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = UserState.from_dict(data)
            state.user_id = user_id
            if not state.dialogs:
                return self._default_state(user_id)
            return state
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.error("Не удалось прочитать файл %s: %s", path, exc)
            return self._default_state(user_id)

    def _write_to_disk(self, user: UserState) -> None:
        path = self._file_path(user.user_id)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(user.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(path)
        except OSError as exc:
            logger.error("Не удалось сохранить файл %s: %s", path, exc)