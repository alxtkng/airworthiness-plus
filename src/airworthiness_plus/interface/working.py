"""How a figure was worked out: the rule, what went into it and its source (REQ-139).

A figure that a person may rely on is shown with the means to check it
(hazard H-014). The maintenance programme has its own form of this in
``programme.due.ExplainedLimit``; this is the form for every other figure.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Working:
    """One figure and how it was worked out."""

    title: str
    figure: str
    rule: str
    inputs: tuple[tuple[str, str], ...]
    source: str
