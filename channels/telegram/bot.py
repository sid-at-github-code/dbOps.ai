"""
Telegram bot — polling mode via python-telegram-bot.
Run: python -m channels.telegram.bot
"""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from shared.ai import make_openrouter_async_client
from shared.conversation import ConversationStore
from shared.prompts import SYSTEM_PROMPT
from channels.telegram.utils import get_ai_reply

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

_store  = ConversationStore(system_prompt=SYSTEM_PROMPT)
_client = make_openrouter_async_client()

WELCOME_TEXT = (
    "👋 *Welcome to Gloify AI Assistant!*\n\n"
    "I can help you learn about Gloify's digital transformation, software engineering, "
    "and product development capabilities.\n\n"
    "Feel free to ask anything about our services, highlights, or locations!\n\n"
    "💬 *Commands:*\n"
    "/start — Start or restart the conversation\n"
    "/clear — Reset your conversation history\n"
    "/help  — Show this message"
)

HELP_TEXT = (
    "💡 *How to use Gloify AI Assistant:*\n\n"
    "• Type any question about Gloify (e.g. _'What services do you offer?'_)\n"
    "• Use /clear to start a fresh conversation\n\n"
    "Need personal assistance? Visit [gloify.com](https://gloify.com)."
)


# ── Handlers ──────────────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _store.clear(str(chat_id))
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _store.clear(str(chat_id))
    await update.message.reply_text(
        "🧹 *Conversation history cleared!*", parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_TEXT, parse_mode="Markdown", disable_web_page_preview=True
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return

    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    reply = await get_ai_reply(chat_id, text, store=_store, ai_client=_client)
    await update.message.reply_text(reply)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY missing from .env")
        return
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN missing from .env")
        return

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("help",  help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("\n===================================")
    print("      GLOIFY TELEGRAM BOT")
    print("      STATUS: RUNNING...")
    print("===================================\n")

    application.run_polling()


if __name__ == "__main__":
    main()
