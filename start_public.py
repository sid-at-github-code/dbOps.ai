"""
Public backend for client-side-frontend/ — a standalone static HTML/CSS/JS
frontend (dashboard + chatbot) meant to be hosted separately (e.g. Netlify)
and talk to this server cross-origin (e.g. deployed on Vercel).

Exposes the same /api/query and /chat routes as start_dashboard.py /
start_chatbot.py, but with no static-file mount and CORS restricted to an
explicit origin allowlist instead of "*". This does not change or replace
the existing SSR entry points — start_dashboard.py and start_chatbot.py are
untouched and keep working exactly as before.

Run:
    python start_public.py
    uvicorn start_public:app --reload --port 8003

Env:
    PUBLIC_PORT       Port to listen on (default 8003)
    ALLOWED_ORIGINS   Comma-separated list of allowed origins, e.g.
                       "https://my-frontend.netlify.app,http://localhost:5500"
                       Defaults to "*" (dev mode — any origin allowed).
"""

import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.query import router as query_router

load_dotenv()

app = FastAPI(title="Fetcher.io Public API", docs_url=None, redoc_url=None)

_origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()
_allow_origins = ["*"] if _origins_env == "*" else [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(query_router, prefix="/api")
app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PUBLIC_PORT", 8003))
    uvicorn.run("start_public:app", host="0.0.0.0", port=port, reload=True)
