"""Cache key construction for upstream provider responses.
Keys are hashed so that free-text queries and encoded request bodies stay within the
character and length rules every Django cache backend accepts.
"""

from __future__ import annotations

import hashlib


def cache_key(namespace: str, *parts: object) -> str:
    material = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:40]
    return f"{namespace}:{digest}"
