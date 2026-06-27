from __future__ import annotations

import re
from dataclasses import dataclass

from landing.models import OneCConfiguration, OneCRelease, SiteSettings


class UpdatePathError(Exception):
    def __init__(self, message: str, code: str = 'error'):
        super().__init__(message)
        self.code = code


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


@dataclass
class ReleaseInfo:
    version: str
    from_versions: set[str]
    min_platform: str


@dataclass
class UpdatePathResult:
    configuration_slug: str
    configuration_name: str
    current_version: str
    latest_version: str
    chain: list[str]
    min_platform: str
    is_up_to_date: bool
    steps_count: int
    hourly_rate: int
    hours_per_release: float
    estimated_hours: float
    estimated_price: int


def build_update_chain(
    releases: list[ReleaseInfo],
    current_version: str,
) -> tuple[list[str], str, str]:
    if not releases:
        raise UpdatePathError('Для конфигурации нет релизов.', 'no_releases')

    current = normalize_version(current_version)
    if not current:
        raise UpdatePathError('Укажите номер текущего релиза.', 'invalid_version')

    latest = releases[0].version
    if current == latest:
        return [], latest, releases[0].min_platform

    chain: list[str] = []
    cursor = current
    visited: set[str] = set()

    while cursor != latest:
        if cursor in visited:
            raise UpdatePathError(
                f'Обнаружен цикл при построении цепочки обновлений (версия {cursor}).',
                'cycle_detected',
            )
        visited.add(cursor)

        next_release = None
        for release in releases:
            if cursor in release.from_versions:
                next_release = release.version
                break

        if not next_release:
            raise UpdatePathError(
                f'Не найдено обновление для версии {cursor}. '
                'Проверьте данные релизов или обратитесь к специалисту.',
                'no_path',
            )

        chain.append(next_release)
        cursor = next_release

    return chain, latest, releases[0].min_platform


def get_release_infos(configuration: OneCConfiguration) -> list[ReleaseInfo]:
    queryset = OneCRelease.objects.filter(configuration=configuration).order_by(
        'sort_order',
        '-release_date',
        '-id',
    )
    return [
        ReleaseInfo(
            version=normalize_version(release.version),
            from_versions=set(parse_from_versions(release.from_versions)),
            min_platform=release.min_platform.strip().strip(';').strip(),
        )
        for release in queryset
    ]


def calculate_update_path(
    configuration: OneCConfiguration,
    current_version: str,
    site_settings: SiteSettings | None = None,
) -> UpdatePathResult:
    releases = get_release_infos(configuration)
    chain, latest, platform = build_update_chain(releases, current_version)
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
