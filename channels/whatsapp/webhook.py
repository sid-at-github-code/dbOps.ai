"""
Flask app for the WhatsApp Twilio webhook.
Run: python -m channels.whatsapp.webhook
"""

import logging
import os

from dotenv import load_dotenv
from flask import Flask, request

from shared.ai import make_openrouter_client
from shared.conversation import ConversationStore
from shared.prompts import SYSTEM_PROMPT
from channels.whatsapp.utils import get_ai_reply, parse_incoming, twiml_reply

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)

_store  = ConversationStore(system_prompt=SYSTEM_PROMPT)
_client = make_openrouter_client()


@app.route("/webhook", methods=["POST"])
def webhook():
    sender, text = parse_incoming(request.form)

    if not text:
        return twiml_reply("Hi! How can I help you today?")

    reply = get_ai_reply(sender, text, store=_store, ai_client=_client)
    return twiml_reply(reply)


@app.route("/", methods=["GET"])
def health():
    return {"status": "running", "service": "Gloify WhatsApp Bot"}, 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
