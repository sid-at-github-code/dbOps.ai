"""
NL command parser — reads a free-text command, finds the target user,
and dispatches a call or SMS via TwilioService.
"""

from typing import Any, Dict

from calling.database import add_log, get_users
from calling.models import CommunicationLog, User
from calling.twilio_service import TwilioService

twilio = TwilioService()


async def process_command(command: str) -> Dict[str, Any]:
    """
    Entry point. Returns {"success": bool, "message": str, ...}.

    Parsing logic:
      1. Scan command for a registered username (case-insensitive).
      2. Keywords "message", "sms", "text" → SMS; otherwise → call.
    """
    command_lower = command.lower()

    target: User | None = None
    for user in get_users():
        if user.username.lower() in command_lower:
            target = user
            break

    if not target:
        return {"success": False, "message": "No registered recipient found in command."}

    is_sms = any(kw in command_lower for kw in ("message", "sms", "text"))
    return await (_dispatch_sms if is_sms else _dispatch_call)(target, command)


async def _dispatch_call(user: User, message: str) -> Dict[str, Any]:
    sid    = twilio.make_call(user.phone_number)
    status = "success" if sid else "failed"
    log    = CommunicationLog(
        recipient_name=user.username, recipient_phone=user.phone_number,
        action="call", message=message, status=status, sid=sid,
    )
    add_log(log)
    return {"success": status == "success", "message": f"Call triggered for {user.username}.",
            "sid": sid, "details": log.model_dump(mode="json")}


async def _dispatch_sms(user: User, message: str) -> Dict[str, Any]:
    sid    = twilio.send_sms(user.phone_number, message)
    status = "success" if sid else "failed"
    log    = CommunicationLog(
        recipient_name=user.username, recipient_phone=user.phone_number,
        action="sms", message=message, status=status, sid=sid,
    )
    add_log(log)
    return {"success": status == "success", "message": f"SMS sent to {user.username}.",
            "sid": sid, "details": log.model_dump(mode="json")}
