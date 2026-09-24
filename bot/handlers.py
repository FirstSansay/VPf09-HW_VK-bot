from __future__ import annotations

import json
from typing import Any

from vkbottle import Bot
from vkbottle.tools.mini_types.bot.message import MessageMin
from vkbottle_types.events.bot_events import MessageEvent

from config.settings import Settings
from keyboards import menu as kb
from models.entities import UserState
from services.ai_service import AIService
from services.dialog_manager import DialogManager
from services.fact_service import FactService
from services.memory_manager import MemoryManager
from utils.logger import logger
from utils.text import normalize_text, truncate

from .states import BotStates

MENU_TEXT = (
    "Привет! Я AI-ассистент.\n\n"
    "Что я умею:\n"
    "- общаться в разных режимах (помощник, программист, преподаватель и др.);\n"
    "- вести несколько независимых диалогов;\n"
    "- запоминать факты о тебе.\n\n"
    "Выбери действие в меню ниже или просто напиши сообщение."
)

HELP_TEXT = (
    "Как пользоваться ботом:\n\n"
    "• Новый диалог — создаёт отдельную беседу с собственным контекстом;\n"
    "• Список диалогов — переключение, переименование и удаление диалогов;\n"
    "• Сменить режим — выбор стиля общения для текущего диалога;\n"
    "• Настройки — информация о модели и очистка истории;\n\n"
    "В любой момент можно написать «меню», чтобы вернуться к кнопкам."
)

INFO_TEXT = (
    "Информация о боте:\n\n"
    "• Провайдер: OpenRouter\n"
    "• Модель: {model}\n"
    "• Контекст: последние {history} сообщений диалога\n"
    "• Память: файлы в папке users/\n\n"
    "Бот запоминает долгосрочные факты о тебе и учитывает их в ответах."
)

MENU_COMMANDS = {"/start", "начать", "старт", "меню", "главное меню", "start"}
HELP_COMMANDS = {"помощь", "help", "/help", "подсказка"}


class Handlers:
    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        ai_service: AIService,
        dialog_manager: DialogManager,
        memory_manager: MemoryManager,
        fact_service: FactService,
    ) -> None:
        self.bot = bot
        self.settings = settings
        self.ai_service = ai_service
        self.dialog_manager = dialog_manager
        self.memory_manager = memory_manager
        self.fact_service = fact_service

    def register(self) -> None:
        self._register_rename_handler()
        self._register_message_handler()
        self._register_callback_handler()

    # ------------------------------------------------------------------ helpers

    async def _set_typing(self, peer_id: int) -> None:
        group_id = self.settings.vk_group_id
        try:
            if group_id:
                await self.bot.api.messages.set_activity(
                    peer_id=peer_id,
                    group_id=group_id,
                    type="typing",
                )
            else:
                await self.bot.api.messages.set_activity(
                    peer_id=peer_id,
                    type="typing",
                )
        except Exception as exc:
            logger.debug("Не удалось показать индикатор набора: %s", exc)

    async def _ack_callback(self, event: MessageEvent) -> None:
        obj = event.object
        try:
            await event.ctx_api.messages.send_message_event_answer(
                event_id=obj.event_id,
                peer_id=obj.peer_id,
                user_id=obj.user_id,
            )
        except Exception as exc:
            logger.debug("Не удалось подтвердить callback: %s", exc)

    async def _edit_or_send(
        self,
        event: MessageEvent,
        text: str,
        keyboard: str,
    ) -> None:
        obj = event.object
        try:
            await event.ctx_api.messages.edit(
                peer_id=obj.peer_id,
                cmid=obj.conversation_message_id,
                message=text,
                keyboard=keyboard,
            )
        except Exception as exc:
            logger.debug("Не удалось отредактировать сообщение, отправляю новое: %s", exc)
            await event.ctx_api.messages.send(
                peer_id=obj.peer_id,
                message=text,
                keyboard=keyboard,
                random_id=0,
            )

    async def _get_user(self, user_id: int) -> UserState:
        return await self.dialog_manager.get_user(user_id)

    # ----------------------------------------------------------- rename handler

    def _register_rename_handler(self) -> None:
        @self.bot.on.message(state=BotStates.RENAME_DIALOG)
        async def on_rename(message: MessageMin) -> None:
            peer_id = message.peer_id
            state_peer = await self.bot.state_dispenser.get(peer_id)
            dialog_id = state_peer.payload.get("dialog_id") if state_peer else None
            await self.bot.state_dispenser.delete(peer_id)

            user = await self._get_user(message.from_id)
            dialog = None
            if dialog_id:
                dialog = await self.dialog_manager.rename_dialog(
                    user, dialog_id, message.text
                )
            if dialog is None:
                dialog = user.active_dialog
                if dialog is not None:
                    await self.dialog_manager.rename_dialog(
                        user, dialog.id, message.text
                    )

            await message.answer(
                f"Диалог переименован в «{dialog.title}».",
                keyboard=kb.main_menu(),
            )

    # ------------------------------------------------------------ main handler

    def _register_message_handler(self) -> None:
        @self.bot.on.message()
        async def on_message(message: MessageMin) -> None:
            text = normalize_text(message.text)
            lower = text.lower()

            if not text and not message.payload:
                return

            if isinstance(message.payload, str) and message.payload:
                try:
                    payload_action = json.loads(message.payload).get("action")
                except (json.JSONDecodeError, AttributeError):
                    payload_action = None
            else:
                payload_action = None

            if payload_action == "start":
                await message.answer(MENU_TEXT, keyboard=kb.main_menu())
                return

            if lower in MENU_COMMANDS:
                await message.answer(MENU_TEXT, keyboard=kb.main_menu())
                return

            if lower in HELP_COMMANDS:
                await message.answer(HELP_TEXT, keyboard=kb.main_menu())
                return

            await self._handle_ai_message(message)

    async def _handle_ai_message(self, message: MessageMin) -> None:
        user = await self._get_user(message.from_id)
        dialog = user.active_dialog
        if dialog is None:
            dialog = await self.dialog_manager.create_dialog(user)

        text = normalize_text(message.text)
        if not text:
            return
        text = truncate(text, self.settings.max_message_length)

        self.memory_manager.append_message(user, dialog, "user", text)
        await self.dialog_manager.save_user(user)

        system_prompt = self.dialog_manager.build_system_prompt(user, dialog)
        ai_messages = self.memory_manager.build_ai_messages(dialog)

        await self._set_typing(message.peer_id)
        reply = await self.ai_service.chat(system_prompt, ai_messages)
        reply = truncate(reply, self.settings.max_message_length)

        self.memory_manager.append_message(user, dialog, "assistant", reply)
        await self.dialog_manager.save_user(user)

        await self.fact_service.maybe_extract_facts(user)

        await message.answer(reply)

    # --------------------------------------------------------- callback handler

    def _register_callback_handler(self) -> None:
        @self.bot.on.raw_event("message_event", MessageEvent)
        async def on_callback(event: MessageEvent) -> None:
            payload: dict[str, Any] = event.object.payload or {}
            action = payload.get("action")
            if not action:
                return
            await self._ack_callback(event)
            await self._dispatch_callback(event, payload, action)

    async def _dispatch_callback(
        self,
        event: MessageEvent,
        payload: dict[str, Any],
        action: str,
    ) -> None:
        user_id = event.object.user_id
        peer_id = event.object.peer_id
        user = await self._get_user(user_id)
        dialog = user.active_dialog

        if action == "menu":
            await self._edit_or_send(event, MENU_TEXT, kb.main_menu())
            return

        if action == "help":
            await self._edit_or_send(event, HELP_TEXT, kb.main_menu())
            return

        if action == "new_dialog":
            new_dialog = await self.dialog_manager.create_dialog(user)
            keyboard = kb.dialogs_list(
                self.dialog_manager.list_dialogs(user),
                user.active_dialog_id,
            )
            await self._edit_or_send(
                event,
                f"Создан новый диалог «{new_dialog.title}». "
                "Переименовать его можно в списке диалогов.",
                keyboard,
            )
            return

        if action == "list":
            page = int(payload.get("page", 0) or 0)
            keyboard = kb.dialogs_list(
                self.dialog_manager.list_dialogs(user),
                user.active_dialog_id,
                page=page,
            )
            await self._edit_or_send(event, "Ваши диалоги:", keyboard)
            return

        if action == "open":
            dialog_id = payload.get("dialog_id", "")
            switched = await self.dialog_manager.switch_dialog(user, dialog_id)
            if switched is not None:
                keyboard = kb.dialogs_list(
                    self.dialog_manager.list_dialogs(user),
                    user.active_dialog_id,
                )
                text = f"Активный диалог: «{switched.title}»."
            else:
                keyboard = kb.main_menu()
                text = "Диалог не найден."
            await self._edit_or_send(event, text, keyboard)
            return

        if action == "rename":
            dialog_id = payload.get("dialog_id", "")
            if dialog and dialog_id == dialog.id:
                title = dialog.title
            else:
                target = self.dialog_manager.get_dialog(user, dialog_id)
                title = target.title if target else dialog.title if dialog else ""
            await self.bot.state_dispenser.set(
                peer_id,
                BotStates.RENAME_DIALOG,
                dialog_id=dialog_id,
            )
            await self._edit_or_send(
                event,
                f"Введите новое название диалога «{title}»:",
                kb.cancel_keyboard(),
            )
            return

        if action == "cancel_rename":
            await self.bot.state_dispenser.delete(peer_id)
            await self._edit_or_send(event, "Переименование отменено.", kb.main_menu())
            return

        if action == "delete":
            dialog_id = payload.get("dialog_id", "")
            target = self.dialog_manager.get_dialog(user, dialog_id)
            title = target.title if target else "этот диалог"
            await self._edit_or_send(
                event,
                f"Удалить диалог «{title}»? Действие нельзя отменить.",
                kb.delete_confirm(dialog_id),
            )
            return

        if action == "confirm_delete":
            dialog_id = payload.get("dialog_id", "")
            deleted = await self.dialog_manager.delete_dialog(user, dialog_id)
            if deleted:
                keyboard = kb.dialogs_list(
                    self.dialog_manager.list_dialogs(user),
                    user.active_dialog_id,
                )
                text = "Диалог удалён."
            else:
                keyboard = kb.main_menu()
                text = "Нельзя удалить единственный диалог."
            await self._edit_or_send(event, text, keyboard)
            return

        if action == "cancel":
            await self._edit_or_send(event, "Отмена.", kb.main_menu())
            return

        if action == "modes":
            active_mode = dialog.mode_id if dialog else "assistant"
            await self._edit_or_send(
                event,
                "Выберите режим общения для текущего диалога:",
                kb.modes_list(active_mode),
            )
            return

        if action == "set_mode":
            mode_id = payload.get("mode_id", "")
            if dialog is not None:
                await self.dialog_manager.set_mode(user, dialog.id, mode_id)
                mode = self.dialog_manager.mode_title(mode_id)
                await self._edit_or_send(
                    event,
                    f"Режим «{mode}» установлен для диалога «{dialog.title}».",
                    kb.modes_list(dialog.mode_id),
                )
            else:
                await self._edit_or_send(event, "Сначала создайте диалог.", kb.main_menu())
            return

        if action == "settings":
            await self._edit_or_send(event, "Настройки:", kb.settings_menu())
            return

        if action == "info":
            text = INFO_TEXT.format(
                model=self.settings.model,
                history=self.settings.max_history_messages,
            )
            await self._edit_or_send(event, text, kb.settings_menu())
            return

        if action == "clear_history":
            if dialog is not None:
                self.memory_manager.clear_history(dialog)
                await self.dialog_manager.save_user(user)
                await self._edit_or_send(
                    event,
                    f"История диалога «{dialog.title}» очищена.",
                    kb.settings_menu(),
                )
            else:
                await self._edit_or_send(event, "Нет активного диалога.", kb.main_menu())
            return

        await self._edit_or_send(event, "Неизвестная команда.", kb.main_menu())