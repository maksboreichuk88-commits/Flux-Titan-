import asyncio
import logging
import os
import re
import threading
from datetime import datetime
from typing import Optional

import gspread
from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "").strip()
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "service_account.json")

_ADMIN_CHAT_ID_RAW = (os.getenv("ADMIN_CHAT_ID") or "").strip()
ADMIN_CHAT_ID: Optional[int]
if _ADMIN_CHAT_ID_RAW:
    try:
        ADMIN_CHAT_ID = int(_ADMIN_CHAT_ID_RAW)
    except ValueError as e:
        raise RuntimeError("ADMIN_CHAT_ID должен быть числом (chat_id).") from e
else:
    ADMIN_CHAT_ID = None

NAME, PHONE, COMMENT = range(3)

PHONE_RE = re.compile(r"^[\d\s\+\-\(\)]{5,25}$")

_ws_lock = threading.Lock()
_ws = None


def _require_env(name: str, value: Optional[str]) -> str:
    if not value:
        raise RuntimeError(f"Не задано окружение: {name}")
    return value


def _get_worksheet():
    global _ws
    if _ws is not None:
        return _ws

    gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_PATH)
    sh = gc.open_by_key(_require_env("SPREADSHEET_ID", SPREADSHEET_ID))
    _ws = sh.worksheet(WORKSHEET_NAME) if WORKSHEET_NAME else sh.sheet1
    return _ws


def _append_row_sync(row: list[str]) -> None:
    ws = _get_worksheet()
    with _ws_lock:
        ws.append_row(row, value_input_option="USER_ENTERED")


async def append_row(row: list[str]) -> None:
    await asyncio.to_thread(_append_row_sync, row)


def _normalize_phone(phone: str) -> str:
    phone = phone.strip()
    phone = re.sub(r"\s+", " ", phone)
    return phone


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    msg = update.effective_message
    await msg.reply_text("Привет! Как к вам обращаться?")
    return NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    name = (msg.text or "").strip()
    if len(name) < 2:
        await msg.reply_text("Имя слишком короткое. Напишите, пожалуйста, ещё раз.")
        return NAME

    context.user_data["lead_name"] = name

    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await msg.reply_text("Ок. Теперь отправьте номер телефона (можно кнопкой ниже).", reply_markup=kb)
    return PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message

    phone = ""
    if msg.contact and msg.contact.phone_number:
        phone = msg.contact.phone_number
    else:
        phone = (msg.text or "").strip()

    phone = _normalize_phone(phone)

    if not PHONE_RE.match(phone):
        await msg.reply_text(
            "Не похоже на номер телефона. Пример: +7 999 123-45-67. Попробуйте ещё раз."
        )
        return PHONE

    context.user_data["lead_phone"] = phone
    await msg.reply_text(
        "Отлично. Коротко опишите запрос (или напишите "нет").",
        reply_markup=ReplyKeyboardRemove(),
    )
    return COMMENT


async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    comment = (msg.text or "").strip()
    if comment.lower() in {"нет", "no", "-", "—"}:
        comment = ""

    name = str(context.user_data.get("lead_name", "")).strip()
    phone = str(context.user_data.get("lead_phone", "")).strip()

    created_at = datetime.now().astimezone().replace(microsecond=0).isoformat()
    user = update.effective_user
    user_id = str(user.id) if user else ""
    username = (user.username if user and user.username else "")

    row = [created_at, user_id, username, name, phone, comment]

    try:
        await append_row(row)
    except Exception as e:
        logging.exception("Failed to append row to Google Sheets: %s", e)
        await msg.reply_text("Заявка не отправилась из-за ошибки. Напишите позже или позвоните напрямую.")
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"Ошибка записи в таблицу: {e}",
            )
        return ConversationHandler.END

    await msg.reply_text("Спасибо! Заявка принята. Мы свяжемся с вами.")

    if ADMIN_CHAT_ID:
        admin_text = (
            f"Новая заявка\n"
            f"Дата: {created_at}\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Комментарий: {comment or '-'}\n"
            f"Username: @{username}" if username else
            f"Новая заявка\nДата: {created_at}\nИмя: {name}\nТелефон: {phone}\nКомментарий: {comment or '-'}\nUser ID: {user_id}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    await msg.reply_text("Ок, отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("Unhandled error: %s", context.error)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    _require_env("BOT_TOKEN", BOT_TOKEN)
    _require_env("SPREADSHEET_ID", SPREADSHEET_ID)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("lead", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            PHONE: [
                MessageHandler(filters.CONTACT, handle_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone),
            ],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
