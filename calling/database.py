"""JSON file persistence for the calling service."""

import json
import os
from typing import Any, Dict, List, Optional

from calling.models import CommunicationLog, User

_BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(_BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
LOGS_FILE  = os.path.join(DATA_DIR, "logs.json")


def _ensure() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    for path in (USERS_FILE, LOGS_FILE):
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)


def get_users() -> List[User]:
    _ensure()
    with open(USERS_FILE) as f:
        return [User(**u) for u in json.load(f)]


def save_users(users: List[User]) -> None:
    _ensure()
    with open(USERS_FILE, "w") as f:
        json.dump([u.model_dump() for u in users], f, indent=4)


def get_user_by_name(username: str) -> Optional[User]:
    for user in get_users():
        if user.username.lower() == username.lower():
            return user
    return None


def add_log(log: CommunicationLog) -> None:
    _ensure()
    with open(LOGS_FILE) as f:
        logs = json.load(f)
    logs.append(log.model_dump(mode="json"))
    with open(LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=4)


def get_logs() -> List[Dict[str, Any]]:
    _ensure()
    with open(LOGS_FILE) as f:
        return json.load(f)
