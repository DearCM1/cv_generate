"""
Step 3 of the tailor pipeline: enrich the user-supplied company profile
with hosted `web_search` and return a structured `CompanyContext`.

The model is given two tools in one call:

- `web_search` (Anthropic server tool) — runs server-side; the results
  come back inline within the same response, so no orchestration loop
  is required.
- `record_company_context` (client tool) — schema-bound exit
  that is extracted into a `CompanyContext` Pydantic model.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from .client import client, SONNET
from .prompts import COMPANY_RESEARCH_SYSTEM, COMPANY_RESEARCH_USER
from .schemas import CompanyContext


# =============================================================
# config
# =============================================================

TOOL_NAME = "record_company_context"
MAX_WEB_SEARCHES = 5

RESEARCH_MAX_TOKENS = 8192

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": MAX_WEB_SEARCHES,
}


# =============================================================
# functions
# =============================================================

def _tool_definition() -> dict:
    """
    Build the Anthropic client tool definition for the recording step,
    derived from the `CompanyContext` Pydantic schema so the model is
    forced to emit a structurally valid object.
    """
    return {
        "name": TOOL_NAME,
        "description": (
            "Record the enriched company context after research. Call "
            "this exactly once, as the final step of your turn."
        ),
        "input_schema": CompanyContext.model_json_schema(),
    }


def research_company(profile_text: str) -> CompanyContext:
    """
    Run a single agentic research turn against the user-supplied company
    profile. The model may issue up to `MAX_WEB_SEARCHES` web searches
    (server-side) and must finish by emitting the `record_company_context`
    tool call.
    """
    response = client().messages.create(
        model=SONNET,
        max_tokens=RESEARCH_MAX_TOKENS,
        system=COMPANY_RESEARCH_SYSTEM,
        tools=[WEB_SEARCH_TOOL, _tool_definition()],
        messages=[
            {
                "role": "user",
                "content": COMPANY_RESEARCH_USER.format(
                    profile_text=profile_text
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            return CompanyContext.model_validate(block.input)

    raise RuntimeError(
        f"Expected a `{TOOL_NAME}` tool call after research; got: "
        f"{[b.type for b in response.content]}"
    )
