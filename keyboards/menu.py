from __future__ import annotations

from typing import Any

from vkbottle import Callback, Keyboard, KeyboardButtonColor

from models.entities import MODES, Dialog

DIALOGS_PER_PAGE = 3


def _payload(action: str, **extra: Any) -> dict[str, Any]:
    return {"action": action, **extra}


def main_menu() -> str:
    keyboard = (
        Keyboard(one_time=False, inline=True)
        .add(
            Callback("Новый диалог", _payload("new_dialog")),
            color=KeyboardButtonColor.PRIMARY,
        )
        .row()
        .add(
            Callback("Список диалогов", _payload("list", page=0)),
            color=KeyboardButtonColor.SECONDARY,
        )
        .row()
        .add(
            Callback("Сменить режим", _payload("modes")),
            color=KeyboardButtonColor.SECONDARY,
        )
        .row()
        .add(
            Callback("Настройки", _payload("settings")),
            color=KeyboardButtonColor.SECONDARY,
        )
        .add(Callback("Помощь", _payload("help")), color=KeyboardButtonColor.PRIMARY)
    )
    return keyboard.get_json()


def dialogs_list(
    dialogs: list[Dialog],
    active_dialog_id: str,
    page: int = 0,
) -> str:
    total = len(dialogs)
    pages = max(1, (total + DIALOGS_PER_PAGE - 1) // DIALOGS_PER_PAGE)
    page = max(0, min(page, pages - 1))
    start = page * DIALOGS_PER_PAGE
    chunk = dialogs[start : start + DIALOGS_PER_PAGE]

    keyboard = Keyboard(one_time=False, inline=True)
    for dialog in chunk:
        is_active = dialog.id == active_dialog_id
        label = dialog.title
        if is_active:
            label = f"{label} (активен)"
        color = KeyboardButtonColor.PRIMARY if is_active else KeyboardButtonColor.SECONDARY
        keyboard.add(
            Callback(label, _payload("open", dialog_id=dialog.id)),
            color=color,
        )
        keyboard.add(
            Callback("Переименовать", _payload("rename", dialog_id=dialog.id)),
            color=KeyboardButtonColor.SECONDARY,
        )
        keyboard.add(
            Callback("Удалить", _payload("delete", dialog_id=dialog.id)),
            color=KeyboardButtonColor.NEGATIVE,
        )
        keyboard.row()

    if pages > 1:
        if page > 0:
            keyboard.add(
                Callback("Назад", _payload("list", page=page - 1)),
                color=KeyboardButtonColor.SECONDARY,
            )
        keyboard.add(
            Callback(f"Стр. {page + 1} из {pages}", _payload("list", page=page)),
            color=KeyboardButtonColor.SECONDARY,
        )
        if page < pages - 1:
            keyboard.add(
                Callback("Далее", _payload("list", page=page + 1)),
                color=KeyboardButtonColor.SECONDARY,
            )
        keyboard.row()

    keyboard.add(
        Callback("Главное меню", _payload("menu")),
        color=KeyboardButtonColor.PRIMARY,
    )
    return keyboard.get_json()


def modes_list(active_mode_id: str) -> str:
    keyboard = Keyboard(one_time=False, inline=True)
    for index, mode in enumerate(MODES):
        is_active = mode.id == active_mode_id
        label = f"{mode.title} (выбран)" if is_active else mode.title
        keyboard.add(
            Callback(label, _payload("set_mode", mode_id=mode.id)),
            color=KeyboardButtonColor.PRIMARY if is_active else KeyboardButtonColor.SECONDARY,
        )
        if index % 2 == 1:
            keyboard.row()
    if len(MODES) % 2 == 1:
        keyboard.row()
    keyboard.add(
        Callback("Главное меню", _payload("menu")),
        color=KeyboardButtonColor.PRIMARY,
    )
    return keyboard.get_json()


def settings_menu() -> str:
    keyboard = (
        Keyboard(one_time=False, inline=True)
        .add(
            Callback("О модели", _payload("info")),
            color=KeyboardButtonColor.SECONDARY,
        )
        .add(
            Callback("Очистить историю", _payload("clear_history")),
            color=KeyboardButtonColor.NEGATIVE,
        )
        .row()
        .add(
            Callback("Главное меню", _payload("menu")),
            color=KeyboardButtonColor.PRIMARY,
        )
    )
    return keyboard.get_json()


def cancel_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=True).add(
        Callback("Отмена", _payload("cancel_rename")),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()


def delete_confirm(dialog_id: str) -> str:
    keyboard = (
        Keyboard(one_time=False, inline=True)
        .add(
            Callback("Да, удалить", _payload("confirm_delete", dialog_id=dialog_id)),
            color=KeyboardButtonColor.NEGATIVE,
        )
        .add(
            Callback("Отмена", _payload("cancel")),
            color=KeyboardButtonColor.SECONDARY,
        )
    )
    return keyboard.get_json()