"""
In-memory conversation history store.
Keyed by any string ID (phone number, chat_id, session ID, etc.).
"""

from typing import Any


class ConversationStore:
    """
    Manages per-user message history for multi-turn AI conversations.

    Usage:
        store = ConversationStore(system_prompt="You are...")
        store.add_user_message(user_id, "Hello")
        store.add_assistant_message(user_id, "Hi there!")
        messages = store.get(user_id)   # list ready for OpenAI chat.completions
    """

    def __init__(self, system_prompt: str = "", max_messages: int = 20) -> None:
        self._system_prompt = system_prompt
        self._max_messages = max_messages
        self._histories: dict[str, list[dict[str, Any]]] = {}

    def get(self, user_id: str) -> list[dict[str, Any]]:
        """Return full message list for user_id (creates it with system prompt if new)."""
        if user_id not in self._histories:
            self._histories[user_id] = []
            if self._system_prompt:
                self._histories[user_id].append(
                    {"role": "system", "content": self._system_prompt}
                )
        return self._histories[user_id]

    def add_user_message(self, user_id: str, content: str) -> None:
        self.get(user_id).append({"role": "user", "content": content})
        self._trim(user_id)

    def add_assistant_message(self, user_id: str, content: str) -> None:
        self.get(user_id).append({"role": "assistant", "content": content})
        self._trim(user_id)

    def clear(self, user_id: str) -> None:
        """Reset history for a user (keeps system prompt)."""
        self._histories.pop(user_id, None)

    def _trim(self, user_id: str) -> None:
        """Keep system prompt + last max_messages entries to avoid token overflow."""
        history = self._histories[user_id]
        has_system = history and history[0]["role"] == "system"
        max_total = self._max_messages + (1 if has_system else 0)
        if len(history) > max_total:
            system = [history[0]] if has_system else []
            self._histories[user_id] = system + history[-self._max_messages :]
