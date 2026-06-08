"""
AI client factory.
Returns an OpenAI-compatible client pointed at any provider.
Both sync (OpenAI) and async (AsyncOpenAI) variants are provided.
"""

import os
from openai import AsyncOpenAI, OpenAI


# ── Sync clients (WhatsApp / calling) ─────────────────────────────────────────

def make_openrouter_client(api_key: str | None = None) -> OpenAI:
    """OpenRouter sync client — works with GPT-4o, Claude, Mistral, etc."""
    return OpenAI(
        api_key=api_key or os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )


def make_gemini_client(api_key: str | None = None) -> OpenAI:
    """Gemini via its OpenAI-compatible REST endpoint (sync)."""
    return OpenAI(
        api_key=api_key or os.environ["GEMINI_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def get_completion(
    client: OpenAI,
    messages: list[dict],
    model: str = "openai/gpt-4o-mini",
    temperature: float = 0.7,
) -> str:
    """Sync completion — raises RuntimeError on failure."""
    try:
        response = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise RuntimeError(f"AI completion failed: {exc}") from exc


# ── Async clients (Telegram) ──────────────────────────────────────────────────

def make_openrouter_async_client(api_key: str | None = None) -> AsyncOpenAI:
    """OpenRouter async client — for use inside async frameworks (Telegram bot)."""
    return AsyncOpenAI(
        api_key=api_key or os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )


async def get_completion_async(
    client: AsyncOpenAI,
    messages: list[dict],
    model: str = "openai/gpt-4o-mini",
    temperature: float = 0.7,
) -> str:
    """Async completion — raises RuntimeError on failure."""
    try:
        response = await client.chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        raise RuntimeError(f"AI completion failed: {exc}") from exc
