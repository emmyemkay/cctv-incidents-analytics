from __future__ import annotations

import re

COMMAND_CENTER_LABEL = "Command Center"
COMMAND_CENTER_ALIASES = {
    "COMMAND CENTER",
    "COMMAND CENTRE",
    "CONTROL ROOM",
    "HEADQUARTERS",
}


def normalize_operational_area(value) -> str:
    """Return a consistent area/station label for analytics and filtering."""
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.upper() in COMMAND_CENTER_ALIASES:
        return COMMAND_CENTER_LABEL
    return text
