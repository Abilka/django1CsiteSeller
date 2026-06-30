from __future__ import annotations

from dataclasses import dataclass

from landing.models import OneCConfiguration, OneCRelease, SiteSettings
from landing.services.update_calculator import UpdatePathError, calculate_update_path, normalize_version
from landing.tools.version_utils import VersionFormatError, compare_versions, parse_version_parts

PLATFORM_VERSION_CUSTOM = '__custom__'


class PlatformCheckError(Exception):
    def __init__(self, message: str, code: str = 'error'):
        super().__init__(message)
        self.code = code


@dataclass
class PlatformCheckResult:
    configuration_slug: str
    configuration_name: str
    platform_version: str
    target_release: str
    required_platform: str
    is_compatible: bool
    platform_gap: int
    update_chain: list[str]
    update_steps_count: int
    estimated_update_hours: float
    estimated_update_price: int
    hourly_rate: int
    message: str


def get_known_platform_versions() -> list[str]:
    raw_versions = (
        OneCRelease.objects.filter(configuration__is_published=True)
        .exclude(min_platform='')
        .values_list('min_platform', flat=True)
    )
    unique_versions: dict[str, list[int]] = {}
    for raw in raw_versions:
        version = normalize_version(raw).strip(';').strip()
        if not version:
            continue
        try:
            unique_versions[version] = parse_version_parts(version)
        except VersionFormatError:
            continue
    return [
        version
        for version, _ in sorted(
            unique_versions.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def resolve_platform_version(platform_version: str, platform_version_custom: str = '') -> str:
    if platform_version == PLATFORM_VERSION_CUSTOM:
        return normalize_version(platform_version_custom)
    return normalize_version(platform_version)


def _resolve_release(
    configuration: OneCConfiguration,
    target_release: str | None,
) -> OneCRelease:
    if target_release:
        release = configuration.releases.filter(version=normalize_version(target_release)).first()
        if release is None:
            raise PlatformCheckError(
                f'Релиз «{target_release}» не найден для «{configuration.name}».',
                'release_not_found',
            )
        return release
    release = configuration.latest_release
    if release is None:
        raise PlatformCheckError('Для конфигурации нет релизов.', 'no_releases')
    return release


def check_platform_compatibility(
    configuration: OneCConfiguration,
    platform_version: str,
    target_release: str | None = None,
    current_release: str | None = None,
    site_settings: SiteSettings | None = None,
) -> PlatformCheckResult:
    platform = normalize_version(platform_version)
    if not platform:
        raise PlatformCheckError('Укажите версию платформы.', 'invalid_platform')

    try:
        compare_versions(platform, platform)
    except VersionFormatError as exc:
        raise PlatformCheckError(str(exc), 'invalid_platform') from exc

    release = _resolve_release(configuration, target_release)
    required = release.min_platform.strip().strip(';').strip()
    if not required:
        raise PlatformCheckError(
            f'Для релиза {release.version} не указана минимальная версия платформы.',
            'no_platform_data',
        )

    try:
        gap = compare_versions(platform, required)
    except VersionFormatError as exc:
        raise PlatformCheckError(str(exc), 'invalid_platform_data') from exc

    is_compatible = gap >= 0
    update_chain: list[str] = []
    update_steps = 0
    estimated_hours = 0.0
    estimated_price = 0
    settings = site_settings or SiteSettings.load()

    if current_release and not is_compatible:
        try:
            path = calculate_update_path(configuration, current_release, site_settings=settings)
            update_chain = path.chain
            update_steps = path.steps_count
            estimated_hours = float(path.estimated_hours)
            estimated_price = path.estimated_price
        except UpdatePathError:
            pass

    if is_compatible:
        message = (
            f'Платформа {platform} подходит для релиза {release.version} '
            f'(требуется не ниже {required}).'
        )
    else:
        message = (
            f'Платформа {platform} ниже требуемой {required} для релиза {release.version}. '
            'Обновите платформу 1С:Предприятие перед установкой конфигурации.'
        )

    return PlatformCheckResult(
        configuration_slug=configuration.slug,
        configuration_name=configuration.name,
        platform_version=platform,
        target_release=release.version,
        required_platform=required,
        is_compatible=is_compatible,
        platform_gap=gap,
        update_chain=update_chain,
        update_steps_count=update_steps,
        estimated_update_hours=estimated_hours,
        estimated_update_price=estimated_price,
        hourly_rate=settings.hourly_rate,
        message=message,
    )
