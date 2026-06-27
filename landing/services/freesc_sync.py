from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from landing.models import OneCConfiguration, OneCRelease, ReleaseSyncLog, SiteSettings
from landing.services.freesc_parser import (
    FreescFetchError,
    fetch_calc_update_page,
    fetch_release_list_page,
    parse_configurations,
    parse_release_table,
)


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
class FreescSyncReport:
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


def sync_configurations_from_freesc(dry_run: bool = False) -> tuple[int, int]:
    html = fetch_calc_update_page()
    remote_configs = parse_configurations(html)
    created = 0
    updated = 0

    for index, remote in enumerate(remote_configs):
        defaults = {
            'name': remote.name,
            'sort_order': index,
            'is_published': True,
        }
        if dry_run:
            exists = OneCConfiguration.objects.filter(slug=remote.slug).exists()
            if exists:
                updated += 1
            else:
                created += 1
            continue

        _, is_created = OneCConfiguration.objects.update_or_create(
            slug=remote.slug,
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
) -> ConfigurationSyncResult:
    result = ConfigurationSyncResult(slug=configuration.slug, name=configuration.name)
    try:
        html = fetch_release_list_page(configuration.slug)
        rows = parse_release_table(html)
    except FreescFetchError as exc:
        result.error = str(exc)
        return result

    if not rows:
        result.error = 'Не удалось распознать таблицу релизов.'
        return result

    result.total_fetched = len(rows)
    fetched_versions = {row.version for row in rows}

    if dry_run:
        for row in rows:
            if OneCRelease.objects.filter(configuration=configuration, version=row.version).exists():
                result.updated += 1
            else:
                result.created += 1
        if prune:
            result.deleted = configuration.releases.exclude(version__in=fetched_versions).count()
        return result

    with transaction.atomic():
        for row in rows:
            release, is_created = OneCRelease.objects.update_or_create(
                configuration=configuration,
                version=row.version,
                defaults={
                    'release_date': row.release_date,
                    'from_versions': row.from_versions,
                    'min_platform': row.min_platform,
                    'sort_order': row.sort_order,
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


def sync_all_from_freesc(
    *,
    slugs: list[str] | None = None,
    sync_configs: bool = True,
    dry_run: bool = False,
    prune: bool = False,
) -> FreescSyncReport:
    report = FreescSyncReport(dry_run=dry_run)

    try:
        if sync_configs:
            report.configs_created, report.configs_updated = sync_configurations_from_freesc(dry_run=dry_run)
    except FreescFetchError as exc:
        report.error = str(exc)
        return report

    queryset = OneCConfiguration.objects.all().order_by('sort_order', 'name')
    if slugs:
        queryset = queryset.filter(slug__in=slugs)

    configurations = list(queryset)
    if not configurations:
        report.error = 'Нет конфигураций для синхронизации.'
        return report

    for configuration in configurations:
        detail = sync_releases_for_configuration(
            configuration,
            dry_run=dry_run,
            prune=prune,
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


def is_sync_due(settings: SiteSettings | None = None) -> bool:
    settings = settings or SiteSettings.load()
    if not settings.freesc_auto_sync_enabled:
        return False
    if settings.freesc_last_sync_at is None:
        return True
    interval = timedelta(days=settings.freesc_sync_interval_days)
    return timezone.now() - settings.freesc_last_sync_at >= interval


def run_scheduled_sync(*, force: bool = False) -> ReleaseSyncLog | None:
    settings = SiteSettings.load()
    if not force and not is_sync_due(settings):
        return None

    log = ReleaseSyncLog.objects.create(
        status=ReleaseSyncLog.Status.RUNNING,
        triggered_by=ReleaseSyncLog.Trigger.FORCE if force else ReleaseSyncLog.Trigger.SCHEDULER,
    )

    try:
        report = sync_all_from_freesc(sync_configs=True, prune=False)
        log.configurations_total = len(report.details)
        log.configurations_synced = report.configurations_synced
        log.configurations_failed = report.configurations_failed
        log.configs_created = report.configs_created
        log.configs_updated = report.configs_updated
        log.releases_created = report.releases_created
        log.releases_updated = report.releases_updated
        log.releases_deleted = report.releases_deleted
        log.message = _format_report_message(report)

        if report.error:
            log.status = ReleaseSyncLog.Status.ERROR
            log.error_message = report.error
        elif report.configurations_failed:
            log.status = ReleaseSyncLog.Status.PARTIAL
            log.error_message = _failed_configs_message(report)
        else:
            log.status = ReleaseSyncLog.Status.SUCCESS

        if not report.dry_run and log.status in {
            ReleaseSyncLog.Status.SUCCESS,
            ReleaseSyncLog.Status.PARTIAL,
        }:
            settings.freesc_last_sync_at = timezone.now()
            settings.save(update_fields=['freesc_last_sync_at'])

    except Exception as exc:
        log.status = ReleaseSyncLog.Status.ERROR
        log.error_message = str(exc)
        log.message = 'Синхронизация прервана из-за ошибки.'
        log.finished_at = timezone.now()
        log.save()
        raise

    log.finished_at = timezone.now()
    log.save()
    return log


def _format_report_message(report: FreescSyncReport) -> str:
    parts = [
        f'Конфигураций: {report.configurations_synced}/{len(report.details)}',
        f'релизов +{report.releases_created} ~{report.releases_updated}',
    ]
    if report.configs_created or report.configs_updated:
        parts.append(f'справочник конфигураций +{report.configs_created} ~{report.configs_updated}')
    return ', '.join(parts)


def _failed_configs_message(report: FreescSyncReport) -> str:
    failed = [f'{item.slug}: {item.error}' for item in report.details if item.error]
    return '; '.join(failed[:5])
