"""
Telegram bot utilities — async, built for python-telegram-bot.

All AI logic lives here. The bot.py handlers just call these functions.

Quick start:
    from shared.conversation import ConversationStore
    from shared.ai import make_openrouter_async_client
    from channels.telegram.utils import get_ai_reply

    store  = ConversationStore(system_prompt=SYSTEM_PROMPT)
    client = make_openrouter_async_client()

    reply = await get_ai_reply(chat_id, text, store=store, ai_client=client)
"""

import logging
import os
from openai import AsyncOpenAI
from shared.ai import get_completion_async

_DEFAULT_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

logger = logging.getLogger(__name__)

FALLBACK = "⚠️ Sorry, an error occurred. Please try again or visit https://gloify.com"


async def get_ai_reply(
    chat_id: int | str,
    message: str,
    *,
    store,              # shared.conversation.ConversationStore
    ai_client: AsyncOpenAI,
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.7,
    fallback: str = FALLBACK,
) -> str:
    """
    Add message to history, call OpenRouter async, return reply text.
    Logs errors and returns fallback string instead of raising.
    """
    uid = str(chat_id)
    store.add_user_message(uid, message)

    try:
        reply = await get_completion_async(
            ai_client, store.get(uid), model=model, temperature=temperature
        )
    except Exception as exc:
        logger.error("Telegram AI error for chat %s: %s", uid, exc)
        reply = fallback

    store.add_assistant_message(uid, reply)
    logger.info("TG reply to %s: %.80s", uid, reply)
    return reply
