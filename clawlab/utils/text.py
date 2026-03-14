from __future__ import annotations

import re


def normalize_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def split_csvish(value: str) -> list[str]:
    parts = re.split(r"[\n,;]+", value)
    return [part.strip() for part in parts if part.strip()]
