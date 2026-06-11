"""
Shared Anthropic client + model defaults + cache-control helpers +
metered call wrapper.

Every stage in the tailor pipeline routes its Anthropic call through
`call_model` so that per-call timing, token usage, and dollar cost are
captured uniformly and returned alongside the raw response. The
orchestrator stitches the resulting `ModelMetrics` objects into the
master `Metrics` record written to each run's `metrics.json`.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import os
from dotenv import load_dotenv

from anthropic import Anthropic

from .schemas import CallTimeMetrics, ModelCost, ModelMetrics, TokenCost


# =============================================================
# config
# =============================================================

load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

DEFAULT_MAX_TOKENS = 4096


# Dollars per million tokens. Cache-write rates assume the default 5-minute
# ephemeral cache window (cv_generate's `cached_text_block` uses
# `{"type": "ephemeral"}`). Verify against current Anthropic pricing before
# the metrics first feed the public webpage.
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


# =============================================================
# functions
# =============================================================

@lru_cache(maxsize=1)
def client() -> Anthropic:
    return Anthropic(
        api_key=api_key
    )


def cached_text_block(text: str) -> dict:
    """
    Build a system block with `cache_control` set for prompt caching.
    """
    return {
        "type": "text",
        "text": text,
        "cache_control": {"type": "ephemeral"},
    }


def call_model(*, model: str, **kwargs) -> tuple[Any, ModelMetrics]:
    """
    Timed, metered wrapper around `client().messages.create`. Returns the
    raw Anthropic response alongside a `ModelMetrics` describing call
    runtime, token usage (including cache reads / writes), and computed
    dollar cost based on the per-model rates in `PRICING`.

    Keyword-only `model` selects both the API model and the pricing entry;
    all remaining kwargs are forwarded verbatim to `messages.create`.
    """
    start = datetime.now(timezone.utc)
    response = client().messages.create(model=model, **kwargs)
    finish = datetime.now(timezone.utc)

    usage = response.usage
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    tokens = TokenCost(
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        tokens_reasoning=0,
        tokens_cache_creation=cache_creation,
        tokens_cache_read=cache_read,
        tokens_total=(
            usage.input_tokens
            + usage.output_tokens
            + cache_creation
            + cache_read
        ),
    )

    rates = PRICING[model]
    dollars = (
        tokens.tokens_in * rates["input"]
        + tokens.tokens_out * rates["output"]
        + tokens.tokens_cache_creation * rates["cache_write_5m"]
        + tokens.tokens_cache_read * rates["cache_read"]
    ) / 1_000_000

    metrics = ModelMetrics(
        model=model,
        runtime=CallTimeMetrics(
            start=start,
            finish=finish,
            elapsed=finish - start,
        ),
        cost=ModelCost(dollars=dollars, tokens=tokens),
    )

    return response, metrics
