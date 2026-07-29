"""
run_all.py — launches the dashboard, public API, WhatsApp webhook, and web
chatbot together, each on its own port, in a single process.

Run:
    python run_all.py

Starts:
    dashboard   -> http://localhost:8000   (DASHBOARD_PORT)
    public API  -> http://localhost:8001   (API_PORT)   docs at /docs
    whatsapp    -> http://localhost:5000   (PORT)
    chatbot     -> http://localhost:8002   (CHATBOT_PORT)

Stop: Ctrl+C (shuts down all four cleanly).
"""

import asyncio
import contextlib
import os
import signal
import socket
import sys

import uvicorn
from dotenv import load_dotenv

load_dotenv()

# Import the already-built app objects instead of shelling out to the
# standalone scripts — avoids uvicorn's --reload subprocess spawning and
# keeps everything in one process that a single Ctrl+C can stop.
from start_dashboard import app as dashboard_app
from start_api import app as api_app
from channels.whatsapp.webhook import app as whatsapp_app
from start_chatbot import app as chatbot_app

DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 8000))
API_PORT = int(os.getenv("API_PORT", 8001))
WHATSAPP_PORT = int(os.getenv("PORT", 5000))
CHATBOT_PORT = int(os.getenv("CHATBOT_PORT", 8002))

SERVICES = {
    "dashboard": (dashboard_app, DASHBOARD_PORT),
    "api": (api_app, API_PORT),
    "whatsapp": (whatsapp_app, WHATSAPP_PORT),
    "chatbot": (chatbot_app, CHATBOT_PORT),
}


def _check_env() -> None:
    # nl_sql falls back OPENROUTER_API_KEY -> OPENAI_API_KEY, so only warn if BOTH missing.
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
        print("[run_all] WARNING: neither OPENAI_API_KEY nor OPENROUTER_API_KEY is set — "
              "/api/query and /v1/query will fail when the LLM is called.")
    if not os.getenv("SUPABASE_URI") and not os.getenv("DB_HOST"):
        print("[run_all] WARNING: no DB connection info set (SUPABASE_URI / DB_HOST) — "
              "queries will fail at the database step.")
    for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"):
        if not os.getenv(key):
            print(f"[run_all] WARNING: {key} not set — WhatsApp send-side features will fail "
                  f"(the webhook itself will still run).")


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def _check_ports() -> None:
    busy = [(name, port) for name, (_, port) in SERVICES.items() if not _port_free(port)]
    if not busy:
        return
    print("[run_all] ERROR: port(s) already in use — is another run_all.py "
          "(or start_dashboard.py/start_api.py) still running from an earlier attempt?")
    for name, port in busy:
        print(f"    {name}: port {port} is busy")
    print("[run_all] find and stop the owning process, e.g. on Windows:")
    print("    powershell -Command \"Get-NetTCPConnection -LocalPort <port> | Select-Object OwningProcess\"")
    print("    powershell -Command \"Stop-Process -Id <pid> -Force\"")
    sys.exit(1)


async def _serve(server: uvicorn.Server, name: str) -> None:
    try:
        await server.serve()
    except SystemExit as exc:
        # uvicorn calls sys.exit(1) on startup failure (e.g. port taken in a
        # race after our preflight check). Convert to a normal exception so
        # asyncio.gather(return_exceptions=True) can collect it cleanly
        # instead of leaving an "exception was never retrieved" warning.
        raise RuntimeError(f"{name} server failed to start") from exc


@contextlib.contextmanager
def _no_signal_capture():
    # uvicorn.Server.serve() installs its own SIGINT/SIGTERM handlers via
    # signal.signal() on every call. With multiple servers in one process,
    # each new one silently steals the previous one's handler, so earlier
    # servers never learn Ctrl+C happened and gather() hangs forever.
    # We disable each server's own capture and install a single shared
    # handler in main_async() instead.
    yield


async def main_async() -> None:
    _check_ports()
    _check_env()

    servers = {
        name: uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info"))
        for name, (app, port) in SERVICES.items()
    }
    for server in servers.values():
        server.capture_signals = _no_signal_capture

    def _handle_stop(sig, frame) -> None:
        print("\n[run_all] shutting down...")
        for server in servers.values():
            server.should_exit = True

    signal.signal(signal.SIGINT, _handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_stop)

    for name, (_, port) in SERVICES.items():
        print(f"[run_all] {name:<9} -> http://localhost:{port}")
    print("[run_all] all services launched. Press Ctrl+C to stop.\n")

    results = await asyncio.gather(
        *(_serve(server, name) for name, server in servers.items()),
        return_exceptions=True,
    )

    errors = [r for r in results if isinstance(r, BaseException)]
    if errors:
        for err in errors:
            print(f"[run_all] {err}")
        sys.exit(1)

    print("[run_all] all services stopped.")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
