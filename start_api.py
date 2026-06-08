"""
Public API server — exposes /v1/query with Bearer auth, rate limiting,
plan-tier enforcement, and full Swagger/ReDoc docs.

Run:
    python start_api.py
    uvicorn start_api:app --reload --port 8001
"""

import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from api.v1 import router as v1_router

load_dotenv()

app = FastAPI(
    title="fetcher.io API",
    description="Natural language → validated read-only PostgreSQL SELECT query.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Register BearerAuth scheme so Swagger UI shows the Authorize button
    schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "BearerAuth"
    ] = {"type": "http", "scheme": "bearer"}
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _custom_openapi


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8001))
    uvicorn.run("start_api:app", host="0.0.0.0", port=port, reload=True)
