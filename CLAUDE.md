# agentic-fetcher — Codebase Map

Multi-channel AI communication platform. Connects a natural-language → SQL engine to a web dashboard, a public REST API, WhatsApp, Telegram, and voice calls (Twilio + Gemini Live).

---

## Quick orientation

```
agentic-fetcher/
├── nl_sql/          NL-to-SQL engine (OpenAI + PostgreSQL)
├── api/             FastAPI routers (dashboard query + public v1)
├── static/          Frontend dashboard (HTML/CSS/JS, no build step)
├── channels/
│   ├── whatsapp/    Twilio WhatsApp bot (Flask)
│   └── telegram/    Telegram bot (python-telegram-bot, polling)
├── calling/         Voice agent (FastAPI + Twilio + Gemini Live WS)
├── shared/          Cross-cutting utilities (AI clients, conversation store, prompts)
├── tests/           Pytest unit + integration tests (all mocked)
├── start_dashboard.py   Entry point — dashboard server (port 8000)
└── start_api.py         Entry point — public API server (port 8001)
```

---

## Modules

### `nl_sql/` — NL-to-SQL engine

Core pipeline: natural language → validated PostgreSQL SELECT → rows.

| File | Exports / purpose |
|---|---|
| `__init__.py` | Public API: `nl_to_sql`, `execute_query`, `validate_read_only` |
| `nl_to_sql.py` | `nl_to_sql(question) → (sql, elapsed_sec)` — calls OpenAI, strips markdown fences |
| `query_executor.py` | `execute_query(sql) → (rows, elapsed_sec)` — psycopg2, RealDictCursor |
| `sql_validator.py` | `validate_read_only(sql)` — raises `ValueError` on INSERT/UPDATE/DELETE/DDL |
| `config.py` | `NlSqlSettings` (pydantic-settings): `openai_api_key`, `llm_model`, `db_*`, `v1_api_key`, `v1_plan_tier` |
| `db_schema.py` | `full_db_context_helper` — **paste your DB schema here** (system prompt for the LLM) |
| `logger.py` | `get_logger(name)` — thin wrapper around stdlib `logging` |

**Import pattern:**
```python
from nl_sql import nl_to_sql, execute_query, validate_read_only
```

**Env vars needed:**
```
OPENAI_API_KEY, LLM_MODEL, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
```

---

### `api/` — FastAPI routers

| File | Route | Used by |
|---|---|---|
| `query.py` | `POST /api/query` | Dashboard frontend (internal, excluded from schema) |
| `v1.py` | `POST /v1/query` | Public API consumers (Bearer auth, rate limiting, plan tiers) |

**`api/query.py` — request/response:**
```python
# Request
{ "question": "Show top 10 bonds by issue size" }

# Response
{
  "sql": "SELECT ...",
  "llm_time": 1.23,
  "db_time": 0.04,
  "rows": [...],
  "columns": ["col1", "col2"],
  "row_count": 10,
  "validated": true,
  "error": null
}
```

**`api/v1.py` — request/response:**
```python
# Request
{ "query": "Show PSU bonds", "user_type": "pro" }

# Success response
{ "status": "success", "sql": "SELECT ..." }

# Error response
{ "status": "error", "code": "RATE_LIMITED", "message": "..." }
```

`v1.py` guards: 401 (bad API key) → 429 (rate limit: 20 req/60 s) → 403 (plan tier) → 422 (LLM/validation fail) → 500.

**Env vars needed:**
```
V1_API_KEY     (leave blank → dev mode, auth skipped)
V1_PLAN_TIER   (free | basic | pro | enterprise, default: pro)
```

---

### `static/` — Frontend dashboard

Vanilla JS, no build step. Served by `start_dashboard.py`.

| File | Purpose |
|---|---|
| `index.html` | Two-panel layout: left (query input, SQL display, timings) + right (results table) |
| `app.js` | Fetch → `POST /api/query`, render results, sort/filter table, copy SQL, SQL syntax highlight |
| `style.css` | Dark theme. CSS variables in `:root`. All JS-generated class names styled here. |

**CSS classes used by `app.js`** (do not rename without updating both):
`kw`, `fn`, `str` (SQL highlighting) · `td-null`, `td-num`, `td-bool`, `bool-true`, `bool-false` (cell types) · `sortable`, `sorted`, `sort-icon`, `th-label`, `filter-row`, `col-filter` (table header) · `hidden`, `centered-state`, `spinner`, `results-state` (panel states)

---

### `channels/whatsapp/` — WhatsApp bot

Framework: **Flask** (sync). Uses Twilio Sandbox → webhook.

| File | Purpose |
|---|---|
| `utils.py` | `parse_incoming(form_data)→(sender,msg)`, `get_ai_reply(...)→str`, `twiml_reply(text)→(body,200,headers)` |
| `webhook.py` | Flask app. `POST /webhook` handles Twilio callbacks. **Run this.** |

**Run:**
```bash
python -m channels.whatsapp.webhook   # port from PORT env, default 5000
```

**Env vars needed:** `OPENROUTER_API_KEY`, `PORT`

---

### `channels/telegram/` — Telegram bot

Framework: **python-telegram-bot** (async, polling mode).

| File | Purpose |
|---|---|
| `utils.py` | `get_ai_reply(chat_id, message, *, store, ai_client)→str` (async) |
| `bot.py` | Registers `/start`, `/clear`, `/help` handlers + message handler. `main()` runs polling. **Run this.** |

**Run:**
```bash
python -m channels.telegram.bot
```

**Env vars needed:** `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`

---

### `calling/` — Voice agent (standalone service)

Framework: **FastAPI** + WebSocket. Completely separate from the rest — do not import `calling.*` from other modules.

| File | Purpose |
|---|---|
| `app.py` | FastAPI app + all routes. **Entry point.** |
| `models.py` | Pydantic: `User`, `UserCreate`, `UserUpdate`, `CommunicationLog`, `CommandRequest` |
| `database.py` | JSON file persistence in `calling/data/` (`users.json`, `logs.json`) |
| `twilio_service.py` | `TwilioService.make_call(phone)`, `TwilioService.send_sms(phone, msg)` |
| `orchestrator.py` | `process_command(text)→dict` — NL parsing → call or SMS dispatch |
| `voice.py` | `handle_media_stream(websocket)` — bidirectional audio: Twilio μ-law ↔ PCM ↔ Gemini Live WS |

**Routes exposed by `calling/app.py`:**
```
GET/POST /voice          TwiML webhook (connect Twilio call to media stream)
WS       /media-stream   Bidirectional audio (Twilio ↔ Gemini)
GET      /api/users
POST     /api/users
PUT      /api/users/{id}
DELETE   /api/users/{id}
POST     /api/process-command   { "command": "Call Alice" }
GET      /api/logs
```

**Run:**
```bash
python -m calling.app   # port from PORT env, default 8000
# Requires a public URL (ngrok) set as BASE_URL for Twilio webhooks
```

**Env vars needed:**
```
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, BASE_URL
GEMINI_API_KEY (or GEMINI_ACCESS_TOKEN), GEMINI_LIVE_MODEL, GEMINI_VOICE
```

---

### `shared/` — Cross-cutting utilities

Used by `channels/` and `api/`. **Not used by `calling/`** (it is self-contained).

| File | Exports |
|---|---|
| `prompts.py` | `SYSTEM_PROMPT`, `COMPANY_CONTEXT` — Gloify assistant persona |
| `ai.py` | `make_openrouter_client()`, `make_gemini_client()` (sync `OpenAI`); `make_openrouter_async_client()`, `get_completion_async()` (async `AsyncOpenAI`); `get_completion()` (sync) |
| `conversation.py` | `ConversationStore(system_prompt, max_messages=20)` — per-user history with auto-trim. Methods: `get(uid)`, `add_user_message`, `add_assistant_message`, `clear(uid)` |

---

### `tests/` — Test suite

All external I/O (OpenAI, psycopg2) is mocked — no keys or DB needed.

| File | What it tests |
|---|---|
| `test_nl_to_sql.py` | `nl_to_sql()`: return types, markdown fence stripping, prompt content, temperature=0 |
| `test_query_executor.py` | `validate_read_only()`: allow SELECT/CTE, block write ops; `execute_query()`: rows, elapsed, connection cleanup, error propagation |
| `test_pipeline.py` | Full NL→SQL→rows flow with domain-specific SQL patterns (PSU bonds, FRB count, maturity dates, perpetuals) |

**Run:**
```bash
pytest          # uses pytest.ini → testpaths = tests
```

Mock patch targets:
- `nl_sql.nl_to_sql._get_client`
- `nl_sql.query_executor._get_connection`

---

## Entry points

| Command | What starts | Default port |
|---|---|---|
| `python start_dashboard.py` | Dashboard UI + `/api/query` | 8000 (`DASHBOARD_PORT`) |
| `python start_api.py` | Public API + Swagger at `/docs` | 8001 (`API_PORT`) |
| `python -m channels.whatsapp.webhook` | WhatsApp Flask bot | 5000 (`PORT`) |
| `python -m channels.telegram.bot` | Telegram polling bot | — |
| `python -m calling.app` | Voice agent (FastAPI + WS) | 8000 (`PORT`) |

---

## Environment variables (full list)

See `.env.example` for the canonical reference. Key groupings:

```
# AI
OPENAI_API_KEY          nl_sql/* (OpenAI direct)
OPENROUTER_API_KEY      channels/* (WhatsApp, Telegram via OpenRouter)
GEMINI_API_KEY          calling/* (Gemini Live voice)
LLM_MODEL               nl_sql (default: gpt-4o-mini)

# Database
DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD

# Twilio
TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_PHONE_NUMBER
BASE_URL                Public ngrok URL for Twilio webhooks (calling service)

# Telegram
TELEGRAM_BOT_TOKEN

# API auth
V1_API_KEY              Empty = dev mode (no auth)
V1_PLAN_TIER            free | basic | pro | enterprise

# Ports
DASHBOARD_PORT=8000     start_dashboard.py
API_PORT=8001           start_api.py
```

---

## Data flow

```
User types question
  └─► POST /api/query (start_dashboard.py)
        └─► nl_to_sql()       OpenAI → raw SQL
        └─► validate_read_only()
        └─► execute_query()   psycopg2 → rows
        └─► JSON response → app.js renders table

WhatsApp message arrives
  └─► POST /webhook (channels/whatsapp/webhook.py)
        └─► parse_incoming()
        └─► get_ai_reply()    OpenRouter → reply text
        └─► twiml_reply()     TwiML XML → Twilio sends WhatsApp reply

Telegram message arrives
  └─► handle_message() (channels/telegram/bot.py)
        └─► get_ai_reply()    OpenRouter async → reply text
        └─► send_message()    Telegram Bot API

Inbound/outbound call
  └─► /voice (calling/app.py)         TwiML → connect media stream
  └─► WS /media-stream
        ├─ receive_twilio()    μ-law audio → PCM 16k → Gemini Live WS
        └─ receive_gemini()    Gemini audio → PCM 8k → μ-law → Twilio
```

---

## Key conventions

- **Imports:** always use absolute package paths (`from nl_sql.config import settings`), never relative.
- **`calling/`** is fully self-contained — it does not import from `shared/`, `nl_sql/`, or `api/`.
- **`shared/`** has no dependency on any other local package.
- **`nl_sql/`** has no dependency on `shared/` or `channels/`.
- All channel utilities (`channels/*/utils.py`) are pure functions — pass `store` and `ai_client` in; no module-level singletons inside utils files.
- The dashboard frontend makes exactly one API call: `POST /api/query`.
- `nl_sql/db_schema.py::full_db_context_helper` is the only file that needs to be filled in before the NL-to-SQL pipeline works.
