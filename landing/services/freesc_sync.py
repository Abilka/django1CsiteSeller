"""Синхронизация релизов. Историческое имя модуля сохранено для совместимости."""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from landing.models import OneCConfiguration, ReleaseSyncLog, SiteSettings
from landing.services.its_sync import (
    ConfigurationSyncResult,
    ItsSyncReport,
    sync_all_from_its,
    sync_configurations_from_its,
    sync_releases_for_configuration,
)

FreescSyncReport = ItsSyncReport


def sync_configurations_from_freesc(dry_run: bool = False) -> tuple[int, int]:
    return sync_configurations_from_its(dry_run=dry_run)


def sync_all_from_freesc(
    *,
    slugs: list[str] | None = None,
    sync_configs: bool = True,
    dry_run: bool = False,
    prune: bool = False,
) -> ItsSyncReport:
    return sync_all_from_its(
        slugs=slugs,
        sync_configs=sync_configs,
        dry_run=dry_run,
        prune=prune,
        fetch_dates=False,
    )


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
        report = sync_all_from_its(sync_configs=True, prune=True)
        log.configurations_total = len(report.details)
        log.configurations_synced = report.configurations_synced
        log.configurations_failed = report.configurations_failed
        log.configs_created = report.configs_created
        log.configs_updated = report.configs_updated
        log.releases_created = report.releases_created
        log.releases_updated = report.releases_updated
        log.releases_deleted = report.releases_deleted
        log.message = format_sync_report_message(report)

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


def format_sync_report_message(report: ItsSyncReport) -> str:
    parts = [
        f'Конфигураций: {report.configurations_synced}/{len(report.details)}',
        f'релизов +{report.releases_created} ~{report.releases_updated}',
    ]
    if report.releases_deleted:
        parts.append(f'удалено {report.releases_deleted}')
    if report.configs_created or report.configs_updated:
        parts.append(f'справочник конфигураций +{report.configs_created} ~{report.configs_updated}')

    lines = [', '.join(parts)]
    for detail in report.details:
        if detail.error:
            lines.append(f'✗ {detail.name}: {detail.error}')
            continue
        extra = f', удалено {detail.deleted}' if detail.deleted else ''
        latest = detail.latest_version or '—'
        lines.append(
            f'✓ {detail.name}: актуальный {latest}, '
            f'+{detail.created} ~{detail.updated}{extra} (на ИТС: {detail.total_fetched})',
        )

    skipped = OneCConfiguration.objects.filter(
        is_published=True,
        its_doc_id__isnull=True,
    ).count()
    if skipped:
        lines.append(
            f'⚠ {skipped} конфигураций в калькуляторе без привязки к ИТС — '
            'их релизы не обновляются (БП 2.0, УТ 10 и др.).',
        )
    return '\n'.join(lines)


def _format_report_message(report: ItsSyncReport) -> str:
    return format_sync_report_message(report).split('\n', 1)[0]


def _failed_configs_message(report: ItsSyncReport) -> str:
    failed = [f'{item.slug}: {item.error}' for item in report.details if item.error]
    return '; '.join(failed[:5])
