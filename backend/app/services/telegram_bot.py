"""Telegram bot: command menu, reply keyboard, and Mini App (Web App) button."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"

BOT_COMMANDS: list[dict[str, str]] = [
    {"command": "start", "description": "Botni ishga tushirish"},
    {"command": "book", "description": "Chipta bron qilish (Mini App)"},
    {"command": "lookup", "description": "Bronni tekshirish"},
    {"command": "help", "description": "Yordam"},
]

WELCOME_TEXT = (
    "🚌 <b>NWay</b> — shaharlar aro avtobus chiptalari\n\n"
    "Reysni tanlang, joyingizni belgilang va Payme, Click yoki karta orqali to‘lang.\n\n"
    "Quyidagi tugmalar orqali Mini App oching yoki buyruqlardan foydalaning:\n"
    "/book — chipta bron qilish\n"
    "/lookup — bron kodini tekshirish\n"
    "/help — yordam"
)

HELP_TEXT = (
    "<b>NWay yordam</b>\n\n"
    "• <b>Chipta bron qilish</b> — Mini App ochiladi, reys va joy tanlaysiz\n"
    "• <b>Bronni tekshirish</b> — JZK-XXXXX kodingizni kiriting\n"
    "• To‘lov: Payme, Click, Uzcard/Humo\n"
    "• Joy 10 daqiqa saqlanadi\n\n"
    "Savollar: @nway_support"
)

MENU_BOOK = "🎫 Chipta bron qilish"
MENU_LOOKUP = "🔍 Bronni tekshirish"
MENU_HELP = "❓ Yordam"


class TelegramBotClient:
    def __init__(self, token: str, webapp_url: str) -> None:
        self.token = token
        self.webapp_url = webapp_url.rstrip("/")
        self._offset = 0

    async def _call(self, method: str, **payload: Any) -> dict[str, Any]:
        url = API_BASE.format(token=self.token, method=method)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data}")
        return data["result"]

    async def setup(self) -> None:
        await self._call("setMyCommands", commands=BOT_COMMANDS)
        await self._call(
            "setChatMenuButton",
            menu_button={
                "type": "web_app",
                "text": "🚌 Chipta bron qilish",
                "web_app": {"url": self.webapp_url},
            },
        )
        logger.info("telegram_bot_configured webapp_url=%s", self.webapp_url)

    def _reply_keyboard(self) -> dict[str, Any]:
        return {
            "keyboard": [
                [{"text": MENU_BOOK, "web_app": {"url": self.webapp_url}}],
                [{"text": MENU_LOOKUP}, {"text": MENU_HELP}],
            ],
            "resize_keyboard": True,
            "is_persistent": True,
        }

    def _inline_open_app(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [{"text": "🚀 Mini App ochish", "web_app": {"url": self.webapp_url}}],
                [{"text": "🔍 Bronni tekshirish", "callback_data": "lookup"}],
            ]
        }

    async def send_welcome(self, chat_id: int) -> None:
        await self._call(
            "sendMessage",
            chat_id=chat_id,
            text=WELCOME_TEXT,
            parse_mode="HTML",
            reply_markup=self._reply_keyboard(),
        )
        await self._call(
            "sendMessage",
            chat_id=chat_id,
            text="Tez kirish uchun quyidagi tugmani bosing:",
            reply_markup=self._inline_open_app(),
        )

    async def send_help(self, chat_id: int) -> None:
        await self._call(
            "sendMessage",
            chat_id=chat_id,
            text=HELP_TEXT,
            parse_mode="HTML",
            reply_markup=self._reply_keyboard(),
        )

    async def send_lookup_hint(self, chat_id: int) -> None:
        lookup_url = f"{self.webapp_url}/lookup"
        await self._call(
            "sendMessage",
            chat_id=chat_id,
            text=(
                "🔍 <b>Bronni tekshirish</b>\n\n"
                "Mini App ichida bron kodingizni (masalan, <code>JZK-8F2KQ</code>) kiriting."
            ),
            parse_mode="HTML",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "🔍 Bronni tekshirish", "web_app": {"url": lookup_url}}],
                ]
            },
        )

    async def send_book_prompt(self, chat_id: int) -> None:
        await self._call(
            "sendMessage",
            chat_id=chat_id,
            text="🎫 Mini App ochiladi — reys va joy tanlang.",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "🚌 Reys topish", "web_app": {"url": self.webapp_url}}],
                ]
            },
        )

    async def handle_update(self, update: dict[str, Any]) -> None:
        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            data = cb.get("data", "")
            await self._call("answerCallbackQuery", callback_query_id=cb["id"])
            if data == "lookup":
                await self.send_lookup_hint(chat_id)
            return

        message = update.get("message") or update.get("edited_message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()
        if not text:
            return

        command = text.split()[0].split("@")[0].lower()

        if command in ("/start", "/book"):
            if command == "/book":
                await self.send_book_prompt(chat_id)
            else:
                await self.send_welcome(chat_id)
        elif command == "/help":
            await self.send_help(chat_id)
        elif command == "/lookup":
            await self.send_lookup_hint(chat_id)
        elif text == MENU_BOOK:
            await self.send_book_prompt(chat_id)
        elif text == MENU_LOOKUP:
            await self.send_lookup_hint(chat_id)
        elif text == MENU_HELP:
            await self.send_help(chat_id)
        else:
            await self._call(
                "sendMessage",
                chat_id=chat_id,
                text="Buyruqni tanlang yoki Mini App tugmasini bosing 👇",
                reply_markup=self._reply_keyboard(),
            )

    async def poll_forever(self) -> None:
        await self.setup()
        logger.info("telegram_bot_polling_started")
        while True:
            try:
                updates = await self._call(
                    "getUpdates",
                    offset=self._offset,
                    timeout=30,
                    allowed_updates=["message", "edited_message", "callback_query"],
                )
                for update in updates:
                    self._offset = update["update_id"] + 1
                    try:
                        await self.handle_update(update)
                    except Exception:
                        logger.exception("telegram_update_failed update_id=%s", update.get("update_id"))
            except httpx.HTTPError:
                logger.exception("telegram_poll_http_error")
                await asyncio.sleep(5)
            except Exception:
                logger.exception("telegram_poll_error")
                await asyncio.sleep(5)


async def run_telegram_bot() -> None:
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Add it to .env to run the bot.")
    if not settings.TELEGRAM_WEBAPP_URL:
        raise SystemExit("TELEGRAM_WEBAPP_URL is not set (public HTTPS URL of the frontend).")

    bot = TelegramBotClient(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_WEBAPP_URL)
    await bot.poll_forever()
