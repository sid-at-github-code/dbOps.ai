import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from nl_sql.logger import get_logger
from nl_sql.nl_to_sql import nl_to_sql
from nl_sql.query_executor import execute_query
from nl_sql.sql_validator import validate_read_only

router = APIRouter()
log = get_logger(__name__)

OUTPUT_DIR = Path("output")


def _save_excel(columns: list, rows: list, question: str) -> str:
    import openpyxl
    OUTPUT_DIR.mkdir(exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(columns)
    for row in rows:
        ws.append([row.get(c) for c in columns])
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = "".join(c if c.isalnum() else "_" for c in question[:30]).strip("_")
    filename = f"{ts}-{slug}.xlsx"
    wb.save(OUTPUT_DIR / filename)
    return filename


def _send_whatsapp(filename: str, question: str) -> str | None:
    from twilio.rest import Client
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    base_url    = os.getenv("BASE_URL", "").rstrip("/")
    to          = os.getenv("WHATSAPP_TO", "")
    from_num    = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886")
    if not all([account_sid, auth_token, base_url, to]):
        return None

    def wa(n: str) -> str:
        return n if n.startswith("whatsapp:") else f"whatsapp:{n}"

    client = Client(account_sid, auth_token)
    media_url = f"{base_url}/output/{filename}"
    msg = client.messages.create(
        from_=wa(from_num),
        to=wa(to),
        body=f"Query results: {question}",
        media_url=[media_url],
    )
    return msg.sid


class QueryRequest(BaseModel):
    question: str


@router.post("/query", include_in_schema=False)
async def run_query(req: QueryRequest):
    log.info("query | question=%r", req.question)

    result: dict = {
        "sql": None,
        "llm_time": 0.0,
        "db_time": 0.0,
        "rows": [],
        "columns": [],
        "row_count": 0,
        "validated": False,
        "error": None,
    }

    try:
        sql, llm_time = nl_to_sql(req.question)
        result["sql"] = sql
        result["llm_time"] = round(llm_time, 3)
    except Exception as exc:
        log.error("query | LLM error | question=%r | error=%s", req.question, exc)
        result["error"] = f"LLM error: {exc}"
        return result

    try:
        validate_read_only(sql)
        result["validated"] = True
    except ValueError as exc:
        log.warning("query | read-only validation failed | sql=%r | reason=%s", sql, exc)
        result["error"] = str(exc)
        return result

    try:
        rows, db_time = execute_query(sql)
        result["db_time"] = round(db_time, 3)
        result["rows"] = rows
        result["row_count"] = len(rows)
        if rows:
            result["columns"] = list(rows[0].keys())
    except Exception as exc:
        log.error("query | DB error | sql=%r | error=%s", sql, exc)
        result["error"] = f"DB error: {exc}"
        return result

    log.info(
        "query | done | rows=%d | llm=%.3fs | db=%.3fs | error=%s",
        result["row_count"],
        result["llm_time"],
        result["db_time"],
        result["error"],
    )
    return result
