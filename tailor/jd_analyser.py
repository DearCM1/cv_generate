"""
Step 2 of the tailor pipeline: turn raw job-description text into a
structured `JDSpec` (must-have skills, ATS keywords, tone signals, framing).
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from .client import DEFAULT_MAX_TOKENS, HAIKU, client
from .prompts import JD_ANALYSER_SYSTEM, JD_ANALYSER_USER
from .schemas import JDSpec


# =============================================================
# config
# =============================================================

TOOL_NAME = "record_jd_spec"


# =============================================================
# functions
# =============================================================

def _tool_definition() -> dict:
    """
    Build the Anthropic tool-use definition from the `JDSpec` Pydantic
    schema, so the model is forced to emit a structurally valid object.
    """
    return {
        "name": TOOL_NAME,
        "description": (
            "Record the structured job-description spec. The pipeline uses "
            "this to drive snippet retrieval and CV assembly."
        ),
        "input_schema": JDSpec.model_json_schema(),
    }


def analyze_jd(jd_text: str) -> JDSpec:
    """
    Call Claude with the JD text and force it to emit a `JDSpec` via a
    single tool call. Returns the validated Pydantic model.
    """
    response = client().messages.create(
        model=HAIKU,
        max_tokens=DEFAULT_MAX_TOKENS,
        system=JD_ANALYSER_SYSTEM,
        tools=[_tool_definition()],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": JD_ANALYSER_USER.format(jd_text=jd_text),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            return JDSpec.model_validate(block.input)

    raise RuntimeError(
        f"Expected a `{TOOL_NAME}` tool call in the model response; got: "
        f"{[b.type for b in response.content]}"
    )
