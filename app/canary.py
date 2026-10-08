"""A tiny, isolated piece of behaviour for the pipeline canary.

Nothing in the application imports this. The canary (.github/canary.json) opens pull requests that
change it in known ways and checks what the agent pipeline does with them, so a defect in the pipeline
shows up on a module where it can do no harm instead of on a real change.
"""

CANARY_LIMIT = 10


def within_limit(value: int) -> bool:
    """True when `value` does not exceed the limit. The limit itself is allowed."""
    return value <= CANARY_LIMIT
