"""
Model identifiers and per-token pricing — the single source of truth for
which Claude models the pipeline uses and what they cost.

`client.py` re-exports these names, so existing `from .client import SONNET`
imports across the tailor stages keep working.
"""

# =============================================================
# model ids
# =============================================================

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"


# =============================================================
# pricing
# =============================================================

# Dollars per million tokens.
PRICING: dict[str, dict[str, float]] = {
    SONNET: {
        "input": 3.00,
        "output": 15.00,
        "cache_write_5m": 3.75,
        "cache_read": 0.30,
    },
    HAIKU: {
        "input": 1.00,
        "output": 5.00,
        "cache_write_5m": 1.25,
        "cache_read": 0.10,
    },
}
