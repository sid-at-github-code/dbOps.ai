"""
Send a one-off WhatsApp message via Twilio.

Edit TO_NUMBER below with the recipient's number, then run:
    python -m channels.whatsapp.send_message

Notes:
  - FROM defaults to the Twilio WhatsApp *sandbox* number (+14155238886).
    Override with TWILIO_WHATSAPP_FROM in .env once you have an approved sender.
  - With the sandbox, the recipient must first join by sending the
    "join <code>" message to the sandbox number from their WhatsApp.
"""

import os

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

# ── Edit this ───────────────────────────────────────────────────────────────
TO_NUMBER = "+919677957616"     # recipient, full international format
MESSAGE = "good morning"
# ────────────────────────────────────────────────────────────────────────────

FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886")  # sandbox default


def _wa(number: str) -> str:
    """Ensure the number carries the 'whatsapp:' prefix Twilio expects."""
    number = number.strip()
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


def send_whatsapp(to_number: str, message: str) -> str | None:
    """Send a WhatsApp message. Returns the Twilio message SID (or None)."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set in .env")

    client = Client(account_sid, auth_token)
    msg = client.messages.create(
        from_=_wa(FROM_NUMBER),
        to=_wa(to_number),
        body=message,
    )
    return msg.sid


if __name__ == "__main__":
    if "X" in TO_NUMBER:
        raise SystemExit("Edit TO_NUMBER in send_message.py before running.")
    sid = send_whatsapp(TO_NUMBER, MESSAGE)
    print(f"Sent! Message SID: {sid}")
