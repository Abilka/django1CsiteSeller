from __future__ import annotations

from dataclasses import dataclass

from landing.models import OneCConfiguration, OneCRelease, SiteSettings
from landing.services.its_release_graph import build_chain_versions
from landing.services.version_utils import (
    normalize_version,
    parse_from_versions,
    pick_latest_version,
    version_parts,
)


class UpdatePathError(Exception):
    def __init__(self, message: str, code: str = 'error'):
        super().__init__(message)
        self.code = code


@dataclass
class ChainStep:
    version: str
    url: str

@dataclass
class ReleaseInfo:
    version: str
    from_versions: set[str]
    min_platform: str
    its_url: str = ''


@dataclass
class UpdatePathResult:
    configuration_slug: str
    configuration_name: str
    current_version: str
    latest_version: str
    chain: list[ChainStep]
    min_platform: str
    is_up_to_date: bool
    steps_count: int
    hourly_rate: int
    hours_per_release: float
    estimated_hours: float
    estimated_price: int


def build_update_chain(
    configuration_slug: str,
    releases: list[ReleaseInfo],
    current_version: str,
) -> tuple[list[ChainStep], str, str]:
    if not releases:
        raise UpdatePathError('Для конфигурации нет релизов.', 'no_releases')

    current = normalize_version(current_version)
    if not current:
        raise UpdatePathError('Укажите номер текущего релиза.', 'invalid_version')

    latest = pick_latest_version([release.version for release in releases])
    latest_release = next(release for release in releases if release.version == latest)

    if current == latest:
        return [], latest, latest_release.min_platform

    release_urls = {release.version: release.its_url for release in releases}
    versions_newest_first = sorted(
        [release.version for release in releases],
        key=version_parts,
        reverse=True,
    )

    try:
        chain_versions = build_chain_versions(
            configuration_slug,
            versions_newest_first,
            current,
            latest,
        )
    except ValueError as exc:
        raise UpdatePathError(str(exc), 'invalid_version') from exc

    if not chain_versions:
        return [], latest, latest_release.min_platform

    chain = [
        ChainStep(version=version, url=release_urls.get(version, ''))
        for version in chain_versions
    ]
    return chain, latest, latest_release.min_platform


def get_release_infos(configuration: OneCConfiguration) -> list[ReleaseInfo]:
    releases = list(OneCRelease.objects.filter(configuration=configuration))
    releases.sort(key=lambda release: version_parts(release.version), reverse=True)
    return [
        ReleaseInfo(
            version=normalize_version(release.version),
            from_versions=set(parse_from_versions(release.from_versions)),
            min_platform=release.min_platform.strip().strip(';').strip(),
            its_url=release.its_url,
        )
        for release in releases
    ]


def calculate_update_path(
    configuration: OneCConfiguration,
    current_version: str,
    site_settings: SiteSettings | None = None,
) -> UpdatePathResult:
    releases = get_release_infos(configuration)
    chain, latest, platform = build_update_chain(configuration.slug, releases, current_version)
    current = normalize_version(current_version)
    settings = site_settings or SiteSettings.load()
    pricing = settings.estimate_update_price(len(chain))

    return UpdatePathResult(
        configuration_slug=configuration.slug,
        configuration_name=configuration.name,
        current_version=current,
        latest_version=latest,
        chain=chain,
        min_platform=platform,
        is_up_to_date=not chain,
        steps_count=len(chain),
        hourly_rate=pricing['hourly_rate'],
        hours_per_release=float(pricing['hours_per_release']),
        estimated_hours=float(pricing['estimated_hours']),
        estimated_price=pricing['estimated_price'],
    )
