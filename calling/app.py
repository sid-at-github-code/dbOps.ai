"""
Calling service — FastAPI entry point.
Run: python -m calling.app
Or:  uvicorn calling.app:app --reload
"""

import os
from typing import List

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from calling.database import add_log, get_logs, get_users, get_user_by_name, save_users
from calling.models import CommandRequest, User, UserCreate, UserUpdate
from calling.orchestrator import process_command
from calling.voice import handle_media_stream
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

load_dotenv()

app = FastAPI(title="Gloify Calling Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Gloify Calling Service"}


# ── Users ─────────────────────────────────────────────────────────────────────

@app.get("/api/users", response_model=List[User])
async def list_users():
    return get_users()


@app.post("/api/users", response_model=User)
async def create_user(body: UserCreate):
    users = get_users()
    if any(u.username.lower() == body.username.lower() for u in users):
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(username=body.username, phone_number=body.phone_number)
    users.append(new_user)
    save_users(users)
    return new_user


@app.put("/api/users/{user_id}", response_model=User)
async def update_user(user_id: str, body: UserUpdate):
    users = get_users()
    for i, u in enumerate(users):
        if u.id == user_id:
            updated = u.model_copy(update=body.model_dump(exclude_unset=True))
            users[i] = updated
            save_users(users)
            return updated
    raise HTTPException(status_code=404, detail="User not found")


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    save_users([u for u in get_users() if u.id != user_id])
    return {"message": "User deleted"}


# ── Commands & Logs ───────────────────────────────────────────────────────────

@app.post("/api/process-command")
async def run_command(body: CommandRequest):
    return await process_command(body.command)


@app.get("/api/logs")
async def list_logs():
    return get_logs()


# ── Voice webhook ─────────────────────────────────────────────────────────────

@app.api_route("/voice", methods=["GET", "POST"])
async def voice_webhook(request: Request):
    """TwiML that connects Twilio to the bidirectional media stream."""
    host = os.getenv("BASE_URL", "").replace("https://", "").replace("http://", "")
    if not host:
        host = request.headers.get("host", "localhost:8000")

    response = VoiceResponse()
    response.say("Please wait while I connect you.", voice="Polly.Aditi")
    connect = Connect()
    stream  = Stream(url=f"wss://{host}/media-stream")
    stream.parameter(name="direction", value="both")
    connect.append(stream)
    response.append(connect)
    response.pause(length=60)

    return Response(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await handle_media_stream(websocket)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("calling.app:app", host=host, port=port, reload=True)
