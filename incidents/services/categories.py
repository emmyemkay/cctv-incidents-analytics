from __future__ import annotations

import re

UNCATEGORISED_LABEL = "Uncategorised"
_WHITESPACE_RE = re.compile(r"\s+")


def clean_category_label(value) -> str:
    """Trim a category label without merging or renaming source categories."""
    if value is None:
        return ""
    return str(value).strip()


def resolve_category(category, sub_category) -> str:
    """Apply the platform-wide Category -> Sub-Category -> Uncategorised rule."""
    return (
        clean_category_label(category)
        or clean_category_label(sub_category)
        or UNCATEGORISED_LABEL
    )


def category_colour_key(category) -> str:
    """Return the stable colour identity while preserving the visible source label.

    Case, harmless repeated whitespace and spacing immediately inside parentheses
    do not create different colours. No analytical categories are merged or renamed.
    """
    label = clean_category_label(category) or UNCATEGORISED_LABEL
    normalized = _WHITESPACE_RE.sub(" ", label)
    normalized = normalized.replace(" )", ")").replace("( ", "(")
    return normalized.upper() or UNCATEGORISED_LABEL.upper()


def _stable_hash(value: str) -> int:
    """Mirror the FNV-1a hash used by map-colors.js for deterministic colours."""
    result = 2166136261
    for character in value:
        result ^= ord(character)
        result = (result * 16777619) & 0xFFFFFFFF
    return result


def category_colour(category) -> str:
    """Return the deterministic CSS colour used on all map surfaces."""
    key = category_colour_key(category)
    if key == UNCATEGORISED_LABEL.upper():
        return "#94a3b8"
    hashed = _stable_hash(key)
    hue = hashed % 360
    saturation = 66 + ((hashed >> 8) % 20)
    lightness = 38 + ((hashed >> 16) % 14)
    return f"hsl({hue} {saturation}% {lightness}%)"
