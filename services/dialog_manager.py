from __future__ import annotations

import uuid

from config.settings import Settings
from models.entities import DEFAULT_DIALOG_TITLE, Dialog, UserState, get_mode
from storage.json_storage import JsonStorage
from utils.logger import logger


class DialogManager:
    """Управление диалогами пользователя и системными промптами."""

    def __init__(self, storage: JsonStorage, settings: Settings) -> None:
        self.storage = storage
        self.settings = settings

    async def get_user(self, user_id: int) -> UserState:
        return await self.storage.get_user(user_id)

    async def save_user(self, user: UserState) -> None:
        await self.storage.save_user(user)

    def get_dialog(self, user: UserState, dialog_id: str | None = None) -> Dialog:
        if dialog_id:
            for dialog in user.dialogs:
                if dialog.id == dialog_id:
                    return dialog
        return user.active_dialog

    async def create_dialog(
        self,
        user: UserState,
        title: str = DEFAULT_DIALOG_TITLE,
    ) -> Dialog:
        dialog = Dialog(
            id=uuid.uuid4().hex,
            title=title or DEFAULT_DIALOG_TITLE,
            mode_id="assistant",
        )
        user.dialogs.append(dialog)
        user.active_dialog_id = dialog.id
        await self.save_user(user)
        logger.info("Создан диалог '%s'", dialog.title)
        return dialog

    async def rename_dialog(
        self,
        user: UserState,
        dialog_id: str,
        new_title: str,
    ) -> Dialog | None:
        title = new_title.strip() or DEFAULT_DIALOG_TITLE
        for dialog in user.dialogs:
            if dialog.id == dialog_id:
                dialog.title = title[:64]
                await self.save_user(user)
                logger.info("Диалог переименован в '%s'", dialog.title)
                return dialog
        return None

    async def delete_dialog(self, user: UserState, dialog_id: str) -> bool:
        if len(user.dialogs) <= 1:
            return False
        for index, dialog in enumerate(user.dialogs):
            if dialog.id == dialog_id:
                user.dialogs.pop(index)
                if user.active_dialog_id == dialog_id:
                    user.active_dialog_id = user.dialogs[0].id
                await self.save_user(user)
                logger.info("Диалог '%s' удалён", dialog.title)
                return True
        return False

    async def switch_dialog(self, user: UserState, dialog_id: str) -> Dialog | None:
        for dialog in user.dialogs:
            if dialog.id == dialog_id:
                user.active_dialog_id = dialog_id
                await self.save_user(user)
                logger.info("Активный диалог: '%s'", dialog.title)
                return dialog
        return None

    def list_dialogs(self, user: UserState) -> list[Dialog]:
        return list(user.dialogs)

    async def set_mode(self, user: UserState, dialog_id: str, mode_id: str) -> bool:
        dialog = self.get_dialog(user, dialog_id)
        if dialog is None:
            return False
        mode = get_mode(mode_id)
        dialog.mode_id = mode.id
        await self.save_user(user)
        logger.info("Режим '%s' установлен для диалога '%s'", mode.title, dialog.title)
        return True

    def build_system_prompt(self, user: UserState, dialog: Dialog) -> str:
        mode = get_mode(dialog.mode_id)
        parts = [mode.system_prompt]
        if user.long_term_facts:
            facts = "\n".join(f"- {fact}" for fact in user.long_term_facts)
            parts.append(
                "Известные факты о пользователе (учитывай их в ответах):\n" + facts
            )
        return "\n\n".join(parts)

    def mode_title(self, mode_id: str) -> str:
        return get_mode(mode_id).title