from __future__ import annotations

import re

VERSION_RE = re.compile(r'^\d+(?:\.\d+)*$')


def normalize_version(value: str) -> str:
    cleaned = value.strip().strip(';').strip()
    return cleaned


def parse_from_versions(raw: str | list[str]) -> list[str]:
    if isinstance(raw, list):
        items = raw
    else:
        items = re.split(r'[,;]+', raw)
    return [normalize_version(item) for item in items if normalize_version(item)]
