"""
Shared Anthropic client + model defaults + cache-control helpers.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from functools import lru_cache

from anthropic import Anthropic


# =============================================================
# config
# =============================================================

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

DEFAULT_MAX_TOKENS = 4096


# =============================================================
# functions
# =============================================================

@lru_cache(maxsize=1)
def client() -> Anthropic:
    return Anthropic()


def cached_text_block(text: str) -> dict:
    """
    Build a system block with `cache_control` set for prompt caching.
    """
    return {
        "type": "text",
        "text": text,
        "cache_control": {"type": "ephemeral"},
    }
