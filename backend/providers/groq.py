"""Optional Groq adapter that turns an already-decided plan into a short driver briefing.
The recommendation is computed deterministically before this runs, so the model only
narrates it; callers fall back to a generated sentence whenever no key is configured.
"""

from __future__ import annotations

from django.conf import settings

from core.errors import ProviderError
from core.http import post_json

PROVIDER = "groq"

SYSTEM_PROMPT = (
    "You write terse pre-trip briefings for commercial truck drivers. "
    "You are given a routing decision that a deterministic risk engine has already made. "
    "Never contradict, re-rank or second-guess that decision, and never invent weather values. "
    "Write three to four plain sentences covering why the recommended route won, the worst "
    "conditions expected and roughly where they occur, and one concrete operational note such "
    "as a departure delay or a stretch to watch. "
    "No bullet points, no headings, no markdown and no emojis."
)


def generate_briefing(context: str) -> str | None:
    if not settings.GROQ_API_KEY:
        return None

    payload = {
        "model": settings.GROQ_MODEL,
        "temperature": 0.2,
        "max_completion_tokens": 900,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    }

    try:
        response = post_json(
            PROVIDER,
            settings.GROQ_URL,
            payload=payload,
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            timeout=25.0,
        )
        message = response["choices"][0]["message"]["content"]
    except (ProviderError, KeyError, IndexError, TypeError):
        return None

    return (message or "").strip() or None
