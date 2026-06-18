"""
WhatsApp / Twilio Messaging utilities.

All functions are pure and stateless — pass in what they need.
Wire them into Flask, FastAPI, or any other framework.

Quick start:
    from shared.conversation import ConversationStore
    from shared.ai import make_openrouter_client
    from channels.whatsapp.utils import parse_incoming, get_ai_reply, twiml_reply

    store  = ConversationStore(system_prompt=SYSTEM_PROMPT)
    client = make_openrouter_client()

    sender, text = parse_incoming(request.form)
    reply = get_ai_reply(sender, text, store=store, ai_client=client)
    return twiml_reply(reply)
"""

import logging
import os
from typing import Any

from twilio.twiml.messaging_response import MessagingResponse

from shared.ai import get_completion

_DEFAULT_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

logger = logging.getLogger(__name__)


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_incoming(form_data: dict[str, Any]) -> tuple[str, str]:
    """
    Extract sender ID and message text from a Twilio webhook POST body.

    Returns:
        (sender, message) — sender is e.g. "whatsapp:+919999999999"
    """
    sender = form_data.get("From", "unknown")
    message = form_data.get("Body", "").strip()
    return sender, message


# ── AI reply ──────────────────────────────────────────────────────────────────

def get_ai_reply(
    sender: str,
    message: str,
    *,
    store,          # shared.conversation.ConversationStore
    ai_client,      # openai.OpenAI (any compatible client)
    model: str = _DEFAULT_MODEL,
    fallback: str = "Sorry, I'm having trouble right now. Please visit https://gloify.com for assistance.",
) -> str:
    """
    Add message to history, call the AI, return the reply text.
    Logs errors and returns fallback instead of raising.
    """
    store.add_user_message(sender, message)
    try:
        reply = get_completion(ai_client, store.get(sender), model=model)
    except Exception as exc:
        logger.error("WhatsApp AI error for %s: %s", sender, exc)
        reply = fallback

    store.add_assistant_message(sender, reply)
    logger.info("WA reply to %s: %s", sender, reply[:80])
    return reply


# ── TwiML response builder ────────────────────────────────────────────────────

def twiml_reply(text: str) -> tuple[str, int, dict[str, str]]:
    """
    Build a TwiML MessagingResponse.

    Returns a (body, status_code, headers) tuple — drop straight into Flask:
        return twiml_reply("Hello!")
    """
    resp = MessagingResponse()
    resp.message(text)
    return str(resp), 200, {"Content-Type": "text/xml"}
