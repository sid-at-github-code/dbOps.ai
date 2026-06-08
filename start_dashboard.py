"""
Dashboard server — serves the frontend UI and the /api/query endpoint.

Run:
    python start_dashboard.py
    uvicorn start_dashboard:app --reload --port 8000
"""

import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.query import router as query_router

load_dotenv()

app = FastAPI(title="Fetcher.io Dashboard", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes MUST be registered before the static mount so they take priority
app.include_router(query_router, prefix="/api")

# Catch-all: serves index.html + static assets (style.css, app.js)
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 8000))
    uvicorn.run("start_dashboard:app", host="0.0.0.0", port=port, reload=True)
