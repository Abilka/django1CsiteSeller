from __future__ import annotations

import re

from landing.services.version_utils import normalize_version

VERSION_RE = re.compile(r'^\d+(?:\.\d+)*$')


class VersionFormatError(ValueError):
    pass


def parse_version_parts(version: str) -> list[int]:
    cleaned = normalize_version(version)
    if not cleaned or not VERSION_RE.match(cleaned):
        raise VersionFormatError(f'Некорректный формат версии: «{version}».')
    return [int(part) for part in cleaned.split('.')]


def compare_versions(left: str, right: str) -> int:
    """Return -1 if left < right, 0 if equal, 1 if left > right."""
    left_parts = parse_version_parts(left)
    right_parts = parse_version_parts(right)
    max_len = max(len(left_parts), len(right_parts))
    left_parts.extend([0] * (max_len - len(left_parts)))
    right_parts.extend([0] * (max_len - len(right_parts)))
    for left_part, right_part in zip(left_parts, right_parts, strict=True):
        if left_part < right_part:
            return -1
        if left_part > right_part:
            return 1
    return 0
