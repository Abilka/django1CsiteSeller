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


def version_parts(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in normalize_version(version).split('.'))


def sort_versions_newest_first(versions: list[str]) -> list[str]:
    return sorted(versions, key=version_parts, reverse=True)


def pick_latest_version(versions: list[str]) -> str:
    if not versions:
        raise ValueError('Список версий пуст.')
    return max(versions, key=version_parts)
