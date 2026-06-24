"""
Web chatbot server — a conversational front-end over the database.

The user chats in plain English. The LLM decides when it needs real data and
calls the `query_database` tool; the backend validates the SQL is read-only,
caps it to 10 rows, runs it, and hands the rows back to the model, which then
replies like a human (a short, friendly summary). The raw rows are also sent to
the UI so it can render them as a table.

Run:
    python start_chatbot.py
    # then open http://localhost:8002
"""

import json
import os
import re

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from nl_sql import execute_query, validate_read_only
from nl_sql.config import settings
from nl_sql.db_schema import full_db_context_helper

load_dotenv()

MAX_ROWS = 10

# ── LLM client (OpenRouter if configured, else OpenAI direct) ──────────────────

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if settings.openrouter_api_key:
            _client = OpenAI(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            )
        else:
            _client = OpenAI(api_key=settings.openai_api_key)
    return _client


# ── System prompt: persona + the database "helper" (schema) ────────────────────

SYSTEM_PROMPT = f"""
You are a friendly, helpful data assistant for the AdventureWorks business
(bikes, components, clothing and accessories). You chat with users in natural,
human language.

You have ONE tool: `query_database`. Use it whenever the user asks anything that
needs real data from the database — products, prices, sales, orders, customers,
employees, vendors, inventory, territories, etc. Write a single read-only
PostgreSQL SELECT using the schema below.

Behaviour rules:
- Only call the tool for data questions. For greetings or small talk, just reply.
- Results are capped at {MAX_ROWS} rows — never ask for more.
- After you get rows back, DON'T paste a raw table into your message. The UI
  already shows the table to the user. Instead, give a short, warm,
  human-sounding summary: the key numbers, the highlights, anything notable.
- Keep replies concise and conversational. Be honest if there's no data or an
  error occurred.

---
DATABASE SCHEMA AND SQL RULES:
{full_db_context_helper}
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": (
                "Run a read-only PostgreSQL SELECT against the AdventureWorks "
                "database and get up to 10 rows back as JSON. Use this for any "
                "question about real data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": (
                            "A single read-only SELECT statement. Use "
                            "fully-qualified schema.table names and valid "
                            "PostgreSQL syntax."
                        ),
                    }
                },
                "required": ["sql"],
            },
        },
    }
]


# ── Tool implementation ────────────────────────────────────────────────────────

def _enforce_limit(sql: str, n: int = MAX_ROWS) -> str:
    """Append a LIMIT if the query doesn't already have one."""
    s = sql.strip().rstrip(";").strip()
    if re.search(r"\blimit\b", s, flags=re.IGNORECASE):
        return s
    return f"{s} LIMIT {n}"


def _run_query(sql: str) -> dict:
    """Validate + execute a read-only query. Always returns a dict (never raises)."""
    sql = (sql or "").strip()
    if not sql:
        return {"ok": False, "error": "Empty SQL."}

    limited = _enforce_limit(sql)
    try:
        validate_read_only(limited)
        rows, _ = execute_query(limited)
        rows = jsonable_encoder(rows)[:MAX_ROWS]  # serialize Decimals/dates, hard cap
        columns = list(rows[0].keys()) if rows else []
        return {"ok": True, "sql": limited, "columns": columns, "rows": rows}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "sql": limited}


# ── Chat loop (model ⇄ tool) ────────────────────────────────────────────────────

def run_chat(history: list[dict]) -> tuple[str, list[dict]]:
    """Drive the tool-calling loop. Returns (reply_text, tables_for_ui)."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}, *history]
    tables: list[dict] = []

    for _ in range(5):  # safety bound on tool rounds
        resp = _get_client().chat.completions.create(
            model=settings.llm_model,
            messages=messages,            # type: ignore[arg-type]
            tools=TOOLS,                  # type: ignore[arg-type]
            tool_choice="auto",
            temperature=0.3,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "").strip(), tables

        # Echo the assistant's tool-call message back into the history.
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            }
        )

        for tc in msg.tool_calls:
            if tc.function.name == "query_database":
                args = json.loads(tc.function.arguments or "{}")
                result = _run_query(args.get("sql", ""))
                if result["ok"]:
                    tables.append(
                        {
                            "sql": result["sql"],
                            "columns": result["columns"],
                            "rows": result["rows"],
                        }
                    )
                    tool_content = json.dumps(
                        {"columns": result["columns"], "rows": result["rows"]},
                        default=str,
                    )
                else:
                    tool_content = json.dumps({"error": result["error"]})
            else:
                tool_content = json.dumps({"error": "Unknown tool."})

            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": tool_content}
            )

    return ("Sorry, I couldn't finish that one — try rephrasing?", tables)


# ── FastAPI app ─────────────────────────────────────────────────────────────────

app = FastAPI(title="AdventureWorks Chatbot", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    # Keep only user/assistant turns; the server adds its own system prompt.
    history = [
        {"role": m.role, "content": m.content}
        for m in req.messages
        if m.role in ("user", "assistant")
    ]
    reply, tables = run_chat(history)
    return {"reply": reply, "tables": tables}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": settings.llm_model}


# Static UI mounted last so /chat and /api/* take priority.
app.mount("/", StaticFiles(directory="chatbot_ui", html=True), name="chatbot")


if __name__ == "__main__":
    port = int(os.getenv("CHATBOT_PORT", 8002))
    uvicorn.run("start_chatbot:app", host="0.0.0.0", port=port, reload=True)
