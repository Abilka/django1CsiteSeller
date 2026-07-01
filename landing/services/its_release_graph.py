from __future__ import annotations

from landing.services.version_utils import (
    normalize_version,
    parse_from_versions,
    version_parts,
)


def branch3(version: str) -> tuple[int, ...]:
    parts = version_parts(version)
    return parts[:3] if len(parts) >= 3 else parts


def is_ut11_major_line(version: str) -> bool:
    parts = version_parts(version)
    if len(parts) < 3:
        return True
    if parts[0] == 11 and parts[1] == 5:
        return parts[2] % 5 == 2
    return True


def is_major_line(configuration_slug: str, version: str) -> bool:
    if configuration_slug == 'rel_1c_ut11':
        return is_ut11_major_line(version)
    return True


def branch3_heads(versions_newest_first: list[str]) -> list[str]:
    heads: dict[tuple[int, ...], str] = {}
    for version in versions_newest_first:
        heads.setdefault(branch3(version), version)
    return sorted(heads.values(), key=version_parts, reverse=True)


def milestone_heads(configuration_slug: str, versions_newest_first: list[str]) -> list[str]:
    return [
        head
        for head in branch3_heads(versions_newest_first)
        if is_major_line(configuration_slug, head)
    ]


def build_chain_versions(
    configuration_slug: str,
    versions_newest_first: list[str],
    current_version: str,
    latest_version: str,
) -> list[str]:
    current = normalize_version(current_version)
    latest = normalize_version(latest_version)
    if current == latest:
        return []
    if current not in versions_newest_first:
        raise ValueError(f'Версия {current} отсутствует в списке релизов.')

    milestones = sorted(milestone_heads(configuration_slug, versions_newest_first), key=version_parts)
    cursor = version_parts(current)
    chain: list[str] = []

    same_branch = [
        version
        for version in versions_newest_first
        if branch3(version) == branch3(current) and version_parts(version) > cursor
    ]
    if same_branch:
        chain.append(min(same_branch, key=version_parts))
        cursor = version_parts(chain[-1])

    for milestone in milestones:
        if version_parts(milestone) > cursor:
            chain.append(milestone)

    if latest not in chain and version_parts(latest) > cursor:
        if not chain or version_parts(latest) >= version_parts(chain[-1]):
            chain.append(latest)

    deduped: list[str] = []
    for version in chain:
        if version not in deduped:
            deduped.append(version)
    return deduped


def derive_from_versions(
    configuration_slug: str,
    versions_newest_first: list[str],
) -> dict[str, list[str]]:
    if not versions_newest_first:
        return {}

    milestones = milestone_heads(configuration_slug, versions_newest_first)
    milestone_set = set(milestones)
    milestone_index = {version: index for index, version in enumerate(milestones)}
    result: dict[str, list[str]] = {}

    for index, version in enumerate(versions_newest_first):
        older = versions_newest_first[index + 1:]
        same_branch = [item for item in older if branch3(item) == branch3(version)][:5]

        if version in milestone_set:
            from_versions: list[str] = []
            milestone_pos = milestone_index[version]
            if milestone_pos + 1 < len(milestones):
                from_versions.append(milestones[milestone_pos + 1])
            from_versions.extend(same_branch)
        else:
            from_versions = same_branch

        cleaned = [normalize_version(item) for item in from_versions if normalize_version(item)]
        result[version] = list(dict.fromkeys(cleaned))

    return result


def derive_from_versions_for_release(
    configuration_slug: str,
    versions_newest_first: list[str],
    version: str,
) -> list[str]:
    mapping = derive_from_versions(configuration_slug, versions_newest_first)
    return parse_from_versions(mapping.get(normalize_version(version), []))
