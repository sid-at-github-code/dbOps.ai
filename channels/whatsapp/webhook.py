"""
FastAPI app for the WhatsApp Twilio webhook.
Run: python -m channels.whatsapp.webhook
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Response

from shared.ai import make_openrouter_client
from shared.conversation import ConversationStore
from shared.prompts import SYSTEM_PROMPT
from channels.whatsapp.utils import get_ai_reply, parse_incoming, twiml_reply

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="Gloify WhatsApp Bot", docs_url=None, redoc_url=None)

_store = ConversationStore(system_prompt=SYSTEM_PROMPT)
_client = make_openrouter_client()


@app.post("/webhook")
async def webhook(Body: str = Form(""), From: str = Form("")):
    sender, text = parse_incoming({"From": From, "Body": Body})

    if not text:
        return Response(
            content=twiml_reply("Hi! How can I help you today?"), media_type="text/xml"
        )

    # get_ai_reply is a blocking (sync) call — offload to a thread so it
    # doesn't stall the event loop shared with the dashboard/API servers
    # when everything runs together via run_all.py.
    reply = await asyncio.to_thread(get_ai_reply, sender, text, store=_store, ai_client=_client)
    return Response(content=twiml_reply(reply), media_type="text/xml")


@app.get("/")
async def health():
    return {"status": "running", "service": "Gloify WhatsApp Bot"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 5000))
    uvicorn.run("channels.whatsapp.webhook:app", host="0.0.0.0", port=port, reload=True)
