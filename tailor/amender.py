"""
Step 7 of the tailor pipeline: apply the `ReviewReport` to the profile
and return the revised `Profile` JSON.

No iteration: a single amendment pass is the contract for v1. If the
reviewer flags issues again on a future run, that is a problem for the
next iteration of the pipeline, not for this stage.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

import json

from .client import SONNET, cached_text_block, client
from .prompts import AMENDER_SYSTEM, AMENDER_USER
from .schemas import Profile, ReviewReport


# =============================================================
# config
# =============================================================

TOOL_NAME = "record_amended_profile"
AMENDER_MAX_TOKENS = 8192


# =============================================================
# functions
# =============================================================

def _tool_definition() -> dict:
    """
    Build the Anthropic client tool definition for the recording step.
    The output schema is `Profile` — identical to the assembler — so the
    amender's result is drop-in compatible with the renderer.
    """
    return {
        "name": TOOL_NAME,
        "description": (
            "Record the revised CV profile JSON after applying the "
            "review report. Preserve all unaffected fields verbatim."
        ),
        "input_schema": Profile.model_json_schema(),
    }


def amend(profile: Profile, report: ReviewReport) -> Profile:
    """
    Apply the review report to the profile in a single Sonnet call.
    Schema is enforced via the forced tool call and re-validated by
    Pydantic on the way out.
    """
    response = client().messages.create(
        model=SONNET,
        max_tokens=AMENDER_MAX_TOKENS,
        system=[
            {"type": "text", "text": AMENDER_SYSTEM},
            cached_text_block(
                "Profile schema (must match exactly):\n"
                + json.dumps(Profile.model_json_schema(), indent=2)
            ),
        ],
        tools=[_tool_definition()],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": AMENDER_USER.format(
                    report=report.model_dump_json(indent=2),
                    profile=profile.model_dump_json(indent=2),
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            return Profile.model_validate(block.input)

    raise RuntimeError(
        f"Expected a `{TOOL_NAME}` tool call from the amender; got: "
        f"{[b.type for b in response.content]}"
    )
