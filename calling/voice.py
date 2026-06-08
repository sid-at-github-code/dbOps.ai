"""
Bidirectional voice handler — Twilio Media Stream ↔ Gemini Live.
Handles the /media-stream WebSocket endpoint.
"""

import asyncio
import audioop
import base64
import json
import os

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from shared.prompts import SYSTEM_PROMPT

GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
GEMINI_ACCESS_TOKEN = os.getenv("GEMINI_ACCESS_TOKEN")
GEMINI_LIVE_MODEL  = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
GEMINI_VOICE       = os.getenv("GEMINI_VOICE", "Kore")
GEMINI_LIVE_WS_URL = os.getenv(
    "GEMINI_LIVE_WS_URL",
    "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent",
)

# Per-call conversation history (in-memory, keyed by call SID)
call_history: dict = {}


def _gemini_ws_url() -> str:
    base = GEMINI_LIVE_WS_URL.rstrip("/")
    if GEMINI_ACCESS_TOKEN:
        return f"{base}?access_token={GEMINI_ACCESS_TOKEN}"
    return f"{base}?key={GEMINI_API_KEY}"


async def handle_media_stream(websocket: WebSocket) -> None:
    """Main handler — call from the FastAPI @app.websocket route."""
    await websocket.accept()
    print("📞 Twilio Media Stream connected")

    stream_sid       = None
    call_sid         = None
    gemini_ws        = None
    input_audio_state  = None
    output_audio_state = None

    async def _send_audio(raw_ulaw: bytes) -> None:
        nonlocal stream_sid
        CHUNK = 640
        for i in range(0, len(raw_ulaw), CHUNK):
            chunk = raw_ulaw[i : i + CHUNK]
            try:
                await websocket.send_text(json.dumps({
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": base64.b64encode(chunk).decode()},
                }))
            except Exception:
                break

    async def _send_mark() -> None:
        if not stream_sid:
            return
        try:
            await websocket.send_text(json.dumps({
                "event": "mark",
                "streamSid": stream_sid,
                "mark": {"name": "playback_done"},
            }))
        except Exception:
            pass

    async def _connect_gemini() -> None:
        nonlocal gemini_ws
        if gemini_ws is not None:
            return
        gemini_ws = await websockets.connect(_gemini_ws_url())
        print(f"✅ Gemini Live connected | voice={GEMINI_VOICE}")

        await gemini_ws.send(json.dumps({
            "setup": {
                "model": f"models/{GEMINI_LIVE_MODEL}",
                "generation_config": {
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {"voice_name": GEMINI_VOICE}
                        }
                    },
                },
                "output_audio_transcription": {},
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            }
        }))
        # Opening greeting
        await gemini_ws.send(json.dumps({
            "realtimeInput": {
                "text": "Greet the caller briefly. Say: Hi, I am the Gloify assistant. How can I help you today?"
            }
        }))

    async def _play_gemini_audio(inline_data: dict) -> None:
        nonlocal output_audio_state
        b64 = inline_data.get("data")
        if not b64:
            return
        mime = inline_data.get("mimeType") or inline_data.get("mime_type") or ""
        sample_rate = 24000 if "24000" in mime else 16000
        try:
            pcm = base64.b64decode(b64)
            pcm_8k, output_audio_state = audioop.ratecv(pcm, 2, 1, sample_rate, 8000, output_audio_state)
            ulaw = audioop.lin2ulaw(pcm_8k, 2)
            await _send_audio(ulaw)
        except Exception as e:
            print(f"Audio playback error: {e}")

    async def _receive_twilio() -> None:
        nonlocal stream_sid, call_sid, input_audio_state
        try:
            while True:
                data = json.loads(await websocket.receive_text())

                if data["event"] == "start":
                    stream_sid = data["start"]["streamSid"]
                    call_sid   = data["start"]["callSid"]
                    print(f"▶️  Stream started | SID: {stream_sid}")
                    if call_sid not in call_history:
                        call_history[call_sid] = [{"role": "system", "content": SYSTEM_PROMPT}]
                    await _connect_gemini()

                elif data["event"] == "media":
                    ulaw = base64.b64decode(data["media"]["payload"])
                    try:
                        pcm_8k  = audioop.ulaw2lin(ulaw, 2)
                        pcm_16k, input_audio_state = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, input_audio_state)
                        encoded = base64.b64encode(pcm_16k).decode()
                    except Exception as e:
                        print(f"Audio conversion error: {e}")
                        continue

                    if gemini_ws:
                        try:
                            await gemini_ws.send(json.dumps({
                                "realtime_input": {
                                    "audio": {"data": encoded, "mime_type": "audio/pcm;rate=16000"}
                                }
                            }))
                        except Exception as e:
                            print(f"Gemini send error: {e}")

                elif data["event"] == "stop":
                    print("⏹️  Stream stopped")
                    break

        except WebSocketDisconnect:
            print("📴 Twilio disconnected")
        except Exception as e:
            print(f"Twilio receive error: {e}")

    async def _receive_gemini() -> None:
        nonlocal gemini_ws
        try:
            while True:
                if gemini_ws is None:
                    await asyncio.sleep(0.1)
                    continue

                msg = json.loads(await gemini_ws.recv())
                sc  = msg.get("serverContent", {})

                if "outputTranscription" in sc:
                    t = sc["outputTranscription"].get("text", "")
                    if t:
                        print(f"🤖 Gemini: {t}")

                if "modelTurn" in sc:
                    for part in sc["modelTurn"].get("parts", []):
                        if part.get("text"):
                            print(f"🤖 Text: {part['text']}")
                        if part.get("inlineData"):
                            await _play_gemini_audio(part["inlineData"])

                if sc.get("turnComplete"):
                    await _send_mark()

                if sc.get("interrupted") and stream_sid:
                    try:
                        await websocket.send_text(json.dumps({"event": "clear", "streamSid": stream_sid}))
                    except Exception:
                        pass

                if "inputTranscription" in sc:
                    print(f"🗣️  Caller: {sc['inputTranscription'].get('text', '')}")

        except websockets.exceptions.ConnectionClosed:
            print("Gemini websocket closed")
        except Exception as e:
            print(f"Gemini receive error: {e}")

    await asyncio.gather(
        asyncio.create_task(_receive_twilio()),
        asyncio.create_task(_receive_gemini()),
    )

    if gemini_ws:
        try:
            await gemini_ws.close()
        except Exception:
            pass

    print("🔌 Media stream session ended")
