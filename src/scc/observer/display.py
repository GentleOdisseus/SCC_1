"""Text formatting helpers for terminal observer views."""
from __future__ import annotations

import re
import textwrap
from typing import Any


def display_text(value: Any, width: int = 92) -> str:
    if not isinstance(value, str):
        return "[unavailable]"
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", " ", text)
    return textwrap.shorten(" ".join(text.split()), width=width, placeholder=" …") or "[empty]"
