from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction

from landing.models import OneCConfiguration, OneCRelease
from landing.services.its_parser import (
    ItsConfiguration,
    ItsFetchError,
    ItsVersion,
    fetch_configuration_versions,
    fetch_updinfo_index,
    parse_configurations,
    resolve_configuration_slug,
)
from landing.services.its_release_graph import derive_from_versions


@dataclass
class ConfigurationSyncResult:
    slug: str
    name: str
    created: int = 0
    updated: int = 0
    deleted: int = 0
    total_fetched: int = 0
    error: str = ''


@dataclass
class ItsSyncReport:
    configurations_synced: int = 0
    configurations_failed: int = 0
    releases_created: int = 0
    releases_updated: int = 0
    releases_deleted: int = 0
    configs_created: int = 0
    configs_updated: int = 0
    dry_run: bool = False
    details: list[ConfigurationSyncResult] = field(default_factory=list)
    error: str = ''

    @property
    def success(self) -> bool:
        return not self.error and self.configurations_failed == 0


def sync_configurations_from_its(dry_run: bool = False) -> tuple[int, int]:
    html = fetch_updinfo_index()
    remote_configs = parse_configurations(html)
    created = 0
    updated = 0

    for index, remote in enumerate(remote_configs):
        slug = remote.slug or resolve_configuration_slug(remote.doc_id, remote.name)
        if not slug:
            continue
        defaults = {
            'name': remote.name,
            'sort_order': index,
            'is_published': True,
            'its_doc_id': remote.doc_id,
        }
        if dry_run:
            exists = OneCConfiguration.objects.filter(slug=slug).exists()
            if exists:
                updated += 1
            else:
                created += 1
            continue

        _, is_created = OneCConfiguration.objects.update_or_create(
            slug=slug,
            defaults=defaults,
        )
        if is_created:
            created += 1
        else:
            updated += 1

    return created, updated


def sync_releases_for_configuration(
    configuration: OneCConfiguration,
    *,
    dry_run: bool = False,
    prune: bool = False,
    fetch_dates: bool = False,
) -> ConfigurationSyncResult:
    result = ConfigurationSyncResult(slug=configuration.slug, name=configuration.name)

    if not configuration.its_doc_id:
        result.error = 'У конфигурации не задан раздел ИТС (its_doc_id).'
        return result

    try:
        its_config = ItsConfiguration(
            doc_id=configuration.its_doc_id,
            name=configuration.name,
            content_path='',
            slug=configuration.slug,
        )
        versions = fetch_configuration_versions(its_config, fetch_dates=fetch_dates)
    except ItsFetchError as exc:
        result.error = str(exc)
        return result

    if not versions:
        result.error = 'Не удалось получить список релизов с ИТС.'
        return result

    version_numbers = [item.version for item in versions]
    from_versions_map = derive_from_versions(configuration.slug, version_numbers)
    result.total_fetched = len(versions)
    fetched_versions = set(version_numbers)

    if dry_run:
        for item in versions:
            if OneCRelease.objects.filter(configuration=configuration, version=item.version).exists():
                result.updated += 1
            else:
                result.created += 1
        if prune:
            result.deleted = configuration.releases.exclude(version__in=fetched_versions).count()
        return result

    with transaction.atomic():
        for index, item in enumerate(versions):
            _, is_created = OneCRelease.objects.update_or_create(
                configuration=configuration,
                version=item.version,
                defaults={
                    'release_date': item.release_date,
                    'from_versions': from_versions_map.get(item.version, []),
                    'min_platform': '',
                    'sort_order': index,
                    'its_doc_id': item.doc_id,
                    'its_url': item.url,
                },
            )
            if is_created:
                result.created += 1
            else:
                result.updated += 1

        if prune:
            deleted, _ = configuration.releases.exclude(version__in=fetched_versions).delete()
            result.deleted = deleted

    return result


def sync_all_from_its(
    *,
    slugs: list[str] | None = None,
    sync_configs: bool = True,
    dry_run: bool = False,
    prune: bool = False,
    fetch_dates: bool = False,
) -> ItsSyncReport:
    report = ItsSyncReport(dry_run=dry_run)

    try:
        if sync_configs:
            report.configs_created, report.configs_updated = sync_configurations_from_its(dry_run=dry_run)
    except ItsFetchError as exc:
        report.error = str(exc)
        return report

    queryset = OneCConfiguration.objects.filter(its_doc_id__isnull=False).order_by('sort_order', 'name')
    if slugs:
        queryset = queryset.filter(slug__in=slugs)

    configurations = list(queryset)
    if not configurations:
        report.error = 'Нет конфигураций с привязкой к ИТС для синхронизации.'
        return report

    for configuration in configurations:
        detail = sync_releases_for_configuration(
            configuration,
            dry_run=dry_run,
            prune=prune,
            fetch_dates=fetch_dates,
        )
        report.details.append(detail)
        report.releases_created += detail.created
        report.releases_updated += detail.updated
        report.releases_deleted += detail.deleted
        if detail.error:
            report.configurations_failed += 1
        else:
            report.configurations_synced += 1

    return report
