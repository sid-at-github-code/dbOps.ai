# DBscooper.io

**Ask your database a question. In plain English. From wherever you already are.**

DBscooper.io turns any PostgreSQL database into a conversation. Point it at your
schema once, and your team — and your customers — can get real answers back
through a web dashboard, a chat widget, WhatsApp, Telegram, or a REST API,
without ever writing a line of SQL. Every answer is backed by a real,
validated, read-only query against your live data — never a guess, never a
hallucinated number.

---

## The core idea

Under the hood is one engine: a natural-language-to-SQL pipeline that reads a
question, understands your schema, writes a single safe `SELECT`, and hands
back real rows. Everything else — the dashboard, the chatbot, the WhatsApp
bot, the public API — is a different front door onto that same trustworthy
core.

Today it runs against a 68-table, 5-schema production-style database
(AdventureWorks: people, HR, production, purchasing, sales) — proof it scales
to genuinely complex, real-world schemas, not just a toy demo table.

---

## Every way to reach it

### Web Dashboard
A full analyst-grade query workspace, not just a search box:
- Natural-language query box with a one-keystroke run (`Ctrl + Enter`)
- Generated SQL shown in a syntax-highlighted panel, one click to copy
- Live timing breakdown (LLM think-time vs. database time) for full transparency
- Sortable, filterable results table with type-aware formatting (numbers, booleans, nulls all styled distinctly)
- One-click switch from **Table** view to **Chart** view — bar, line, or pie — auto-generated from the result set
- Export any result as **CSV**, **Excel**, or a **PNG** of the chart
- Adjustable row limit per query
- Dark, modern UI with zero build step (pure HTML/CSS/JS — deploy it anywhere)

### Conversational Web Chatbot
A second, friendlier front end over the same engine — this one talks like a
person, not a query tool:
- LLM decides *for itself* when a question needs real data and calls a
  `query_database` tool — small talk gets a normal reply, no wasted DB hits
  or API cost
- Replies in warm, human summaries ("Here's what I found...") while the raw
  table renders underneath for anyone who wants the detail
- Every tool-generated query is still validated read-only and hard-capped in
  row count before it ever touches the database

### WhatsApp
Meet customers on the channel they already have open all day:
- A branded conversational assistant persona (fully swappable — ships with a
  ready-made example persona and company context you customize per client)
- A data-query mode: ask a question in WhatsApp, get an **Excel file sent
  straight back to the chat** with your results
- Full conversation memory per sender, so follow-up questions just work

### Telegram
The same natural-language assistant, native to Telegram:
- `/start`, `/clear`, `/help` commands
- Per-chat conversation history with automatic trimming
- Fully async — built for high concurrent chat volume

### Public REST API
A ready-to-sell, ready-to-meter API surface, not a raw internal endpoint:
- Bearer-token authentication
- **Four built-in plan tiers** — free / basic / pro / enterprise — enforced
  per request, so packaging and monetization is a config change, not a
  rebuild
- Built-in rate limiting with standard `X-RateLimit-*` response headers
- Full interactive Swagger/OpenAPI docs generated automatically, with
  documented error codes for every failure mode (auth, rate limit, plan
  tier, bad query, server error)

---

## Why the engineers will like it too

- **One engine, five surfaces.** The dashboard, chatbot, WhatsApp bot,
  Telegram bot, and public API all share a single NL-to-SQL core — fix or
  improve it once, every channel gets better.
- **Defense in depth on every query.** Every generated statement passes
  through a dedicated read-only validator that hard-blocks `INSERT`,
  `UPDATE`, `DELETE`, and any DDL, before it's allowed anywhere near the
  database — regardless of which channel asked for it.
- **Modern, 100% async stack.** Every service — dashboard, API, WhatsApp,
  chatbot — is FastAPI end to end. No mixed sync frameworks, no WSGI shims.
- **One command, full platform.** `python run_all.py` boots the dashboard,
  public API, WhatsApp bot, and web chatbot together — each on its own port
  — in a single process, with pre-flight port checks, environment
  validation, and a clean one-Ctrl+C shutdown across all four services.
- **Bring your own schema.** The entire schema context lives in one file.
  Point it at a new database and every channel — dashboard, chatbot,
  WhatsApp, API — instantly understands the new domain.
- **Tested.** A pytest suite covers the NL-to-SQL pipeline, the query
  executor, and the read-only validator end to end, fully mocked — no live
  credentials required to run CI.
- **LLM-provider flexible.** Runs on OpenAI directly or transparently
  fails over to OpenRouter, so you're never locked to a single model
  vendor.

---

## Where we can take it next

Ideas that fall naturally out of the architecture already in place — the
channel layer is modular by design, so each of these is an extension, not a
rewrite:

- **Voice calling** — ask your database a question over a phone call.
  (Twilio + real-time voice AI groundwork is already sketched into the
  architecture; this is the next channel to bring online.)
- **Slack & Microsoft Teams connectors** — same pattern as WhatsApp/Telegram,
  for teams that live in workplace chat instead.
- **Scheduled, delivered reports** — "send me the top 10 accounts every
  Monday at 9am," delivered automatically to WhatsApp, Telegram, or email.
- **Natural-language alerts** — "tell me if inventory drops below 500
  units" — a standing query that pages you the moment it's true.
- **Multi-tenant, multi-database routing** — one deployment, many customer
  databases, each isolated behind its own schema context and API key.
- **Query result caching** — recognize repeated or near-duplicate questions
  and skip the LLM round-trip entirely, cutting cost and latency for common
  queries.
- **Row/column-level data masking** — automatically hide sensitive columns
  based on the requester's plan tier or role, enforced at the same layer
  that already blocks write queries.
- **Query history & audit dashboard** — who asked what, when, and what SQL
  ran — for teams that need a compliance trail.
- **Embeddable widget** — drop the dashboard's query box into any customer
  portal as an iframe, fully white-labeled.

---

## In one sentence

**DBscooper.io is the natural-language front end for your database — one
safe, validated query engine, reachable from a dashboard, a chatbot,
WhatsApp, Telegram, and a sellable public API, all from a single codebase.**
