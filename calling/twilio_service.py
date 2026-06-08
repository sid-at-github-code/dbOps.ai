"""Twilio REST wrapper for outbound calls and SMS."""

import os
from typing import Optional

from twilio.rest import Client


class TwilioService:
    def __init__(self) -> None:
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.base_url    = os.getenv("BASE_URL")

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            print("WARNING: Twilio credentials not set — running in mock mode.")

    def send_sms(self, to_number: str, message: str) -> Optional[str]:
        """Returns Twilio SID on success, None on failure, mock SID in dev mode."""
        if not self.client:
            return "MOCK_SID_SMS"
        try:
            msg = self.client.messages.create(
                body=message, from_=self.from_number, to=to_number
            )
            return msg.sid
        except Exception as e:
            print(f"SMS error: {e}")
            return None

    def make_call(self, to_number: str) -> Optional[str]:
        """
        Trigger an outbound call that connects to the AI voice webhook.
        Returns Twilio call SID on success, None on failure.
        """
        if not self.client:
            return "MOCK_SID_CALL"
        if not self.base_url:
            print("ERROR: BASE_URL not set — outbound calls will not work.")
            return None
        try:
            call = self.client.calls.create(
                url=f"{self.base_url}/voice",
                from_=self.from_number,
                to=to_number,
            )
            return call.sid
        except Exception as e:
            print(f"Call error: {e}")
            return None
