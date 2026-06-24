import asyncio
import os

from fastapi import APIRouter, BackgroundTasks, Form, Response

from nl_sql.logger import get_logger
from nl_sql.nl_to_sql import nl_to_sql
from nl_sql.query_executor import execute_query
from nl_sql.sql_validator import validate_read_only
from api.query import _save_excel

router = APIRouter()
log = get_logger(__name__)

EMPTY_TWIML = '<?xml version="1.0"?><Response></Response>'


def _wa(number: str) -> str:
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


def _reply(to: str, body: str, media_url: str | None = None):
    from twilio.rest import Client
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    from_num = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886")
    kwargs = dict(from_=_wa(from_num), to=to, body=body)
    if media_url:
        kwargs["media_url"] = [media_url]
    client.messages.create(**kwargs)


def _process(question: str, sender: str):
    log.info("wa_webhook | question=%r | from=%s", question, sender)
    try:
        sql, _ = nl_to_sql(question)
        validate_read_only(sql)
        rows, _ = execute_query(sql)
    except Exception as exc:
        log.warning("wa_webhook | pipeline error | %s", exc)
        _reply(sender, f"Sorry, couldn't process that: {str(exc)[:200]}")
        return

    if not rows:
        _reply(sender, "Query returned 0 rows.")
        return

    columns = list(rows[0].keys())
    try:
        filename = _save_excel(columns, rows, question)
        base_url = os.getenv("BASE_URL", "").rstrip("/")
        media_url = f"{base_url}/output/{filename}"
        _reply(sender, f"Results: {len(rows)} row(s)", media_url=media_url)
        log.info("wa_webhook | sent excel | file=%s | to=%s", filename, sender)
    except Exception as exc:
        log.warning("wa_webhook | send failed | %s", exc)
        _reply(sender, f"Got {len(rows)} rows but failed to send file: {str(exc)[:150]}")


@router.post("/whatsapp")
async def whatsapp_webhook(
    background_tasks: BackgroundTasks,
    Body: str = Form(""),
    From: str = Form(""),
):
    question = Body.strip()
    if question:
        background_tasks.add_task(asyncio.to_thread, _process, question, From)
    return Response(content=EMPTY_TWIML, media_type="text/xml")
