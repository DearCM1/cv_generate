"""
Shared parsing for Anthropic forced tool-call responses.

Each LLM stage in the tailor pipeline asks Anthropic for a single forced tool
call and then validates the tool input against a Pydantic schema. This module
keeps that response-shape checking in one place so stages fail consistently
when the model hits a token limit, omits the expected tool call, or returns
schema-invalid input.
"""
# =============================================================
# packages
# =============================================================

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError


# =============================================================
# types
# =============================================================

ModelT = TypeVar("ModelT", bound=BaseModel)


# =============================================================
# functions
# =============================================================

def parse_forced_tool_response(
    *,
    response: Any,
    model: type[ModelT],
    tool_name: str,
    stage: str,
    max_tokens: int,
    max_tokens_name: str,
) -> ModelT:
    """
    Extract the expected tool call from an Anthropic response and validate it.

    Args:
        response: Anthropic `messages.create` response object.
        model: Pydantic model class used to validate the tool input.
        tool_name: Name of the forced tool call expected from the model.
        stage: Human-readable pipeline stage name used in error messages.
        max_tokens: Token budget used for the API call.
        max_tokens_name: Config constant name to mention when token limits fail.

    Returns:
        A validated instance of `model`.

    Raises:
        RuntimeError: The response stopped at `max_tokens`, did not include the
            expected tool call, or included tool input that failed Pydantic
            validation.
    """
    stop_reason = getattr(response, "stop_reason", None)
    if stop_reason == "max_tokens":
        raise RuntimeError(
            f"{stage} hit token limit ({max_tokens}); tool call may be incomplete. "
            f"Consider raising {max_tokens_name}."
        )

    content = getattr(response, "content", [])
    for block in content:
        if (
            getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == tool_name
        ):
            raw_input = getattr(block, "input", None)
            try:
                return model.model_validate(raw_input)
            except ValidationError as e:
                raise RuntimeError(
                    f"{stage} returned `{tool_name}` with unexpected shape: {e}\n"
                    f"Raw input: {raw_input!r}"
                ) from e

    block_summary = [
        {
            "type": getattr(block, "type", None),
            "name": getattr(block, "name", None),
        }
        for block in content
    ]
    raise RuntimeError(
        f"{stage} did not return expected `{tool_name}` tool call; got: "
        f"{block_summary} (stop_reason={stop_reason!r})"
    )
