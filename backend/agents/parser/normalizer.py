"""Normalization helpers for deterministic parsing."""

import re

WHITESPACE_RE = re.compile(r"[ \t]+")
BLANK_LINES_RE = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    normalized = "\n".join(line for line in lines if line)
    return BLANK_LINES_RE.sub("\n\n", normalized).strip()
