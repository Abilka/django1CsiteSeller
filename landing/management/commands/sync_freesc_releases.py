from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from landing.models import OneCConfiguration, ReleaseSyncLog, SiteSettings
from landing.services.freesc_sync import (
    is_sync_due,
    sync_all_from_freesc,
    sync_releases_for_configuration,
)


class Command(BaseCommand):
    help = (
        'Синхронизация конфигураций и релизов 1С с freesc.ru '
        '(калькулятор и список релизов).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Синхронизировать все конфигурации из базы',
        )
        parser.add_argument(
            '--config',
            dest='config_slug',
            help='Slug одной конфигурации, например rel_1c_ut11',
        )
        parser.add_argument(
            '--sync-configs',
            action='store_true',
            help='Обновить список конфигураций со страницы калькулятора freesc.ru',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что изменится, без записи в базу',
        )
        parser.add_argument(
            '--prune',
            action='store_true',
            help='Удалить релизы, которых нет на freesc.ru',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Игнорировать интервал и выполнить синхронизацию сейчас',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self._run_dry_run(options)
            return

        if options['config_slug']:
            self._sync_single(options['config_slug'], options['prune'])
            return

        settings = SiteSettings.load()
        should_run = options['all'] or options['force'] or is_sync_due(settings)
        if not should_run:
            raise CommandError(
                'Синхронизация ещё не требуется. Используйте --force или --all. '
                f'Последняя: {settings.freesc_last_sync_at or "никогда"}. '
                f'Интервал: {settings.freesc_sync_interval_days} дн.'
            )

        sync_configs = options['sync_configs'] or options['all'] or options['force']
        report = sync_all_from_freesc(
            sync_configs=sync_configs,
            dry_run=False,
            prune=options['prune'],
        )
        self._print_report(report)

        log_status = ReleaseSyncLog.Status.SUCCESS if report.success else ReleaseSyncLog.Status.PARTIAL
        if report.error:
            log_status = ReleaseSyncLog.Status.ERROR

        ReleaseSyncLog.objects.create(
            status=log_status,
            triggered_by=ReleaseSyncLog.Trigger.FORCE if options['force'] else ReleaseSyncLog.Trigger.MANUAL,
            configurations_total=len(report.details),
            configurations_synced=report.configurations_synced,
            configurations_failed=report.configurations_failed,
            configs_created=report.configs_created,
            configs_updated=report.configs_updated,
            releases_created=report.releases_created,
            releases_updated=report.releases_updated,
            releases_deleted=report.releases_deleted,
            message=self._report_summary(report),
            error_message=report.error or self._failed_configs_message(report),
            finished_at=timezone.now(),
        )

        settings.freesc_last_sync_at = timezone.now()
        settings.save(update_fields=['freesc_last_sync_at'])

        if report.error:
            raise CommandError(report.error)

    def _run_dry_run(self, options):
        slugs = [options['config_slug']] if options.get('config_slug') else None
        report = sync_all_from_freesc(
            slugs=slugs,
            sync_configs=options.get('sync_configs') or options.get('all') or not slugs,
            dry_run=True,
            prune=options.get('prune', False),
        )
        self.stdout.write(self.style.WARNING('Режим dry-run — изменения не сохранены.'))
        self._print_report(report)

    def _sync_single(self, slug: str, prune: bool):
        configuration = OneCConfiguration.objects.filter(slug=slug).first()
        if configuration is None:
            raise CommandError(f'Конфигурация «{slug}» не найдена.')

        detail = sync_releases_for_configuration(configuration, prune=prune)
        if detail.error:
            raise CommandError(detail.error)

        self.stdout.write(self.style.SUCCESS(
            f'{configuration.name}: создано {detail.created}, '
            f'обновлено {detail.updated}, удалено {detail.deleted}, '
            f'всего на freesc.ru: {detail.total_fetched}.',
        ))

    def _print_report(self, report):
        if report.configs_created or report.configs_updated:
            self.stdout.write(
                f'Конфигурации freesc.ru: +{report.configs_created} / ~{report.configs_updated}',
            )
        for detail in report.details:
            if detail.error:
                self.stdout.write(self.style.ERROR(f'  [x] {detail.slug}: {detail.error}'))
            else:
                line = (
                    f'  [ok] {detail.name}: +{detail.created} ~{detail.updated} '
                    f'({detail.total_fetched} релизов)'
                )
                if detail.deleted:
                    line += f', удалено {detail.deleted}'
                self.stdout.write(line)
        self.stdout.write(self.style.SUCCESS(
            f'Итого: конфигураций {report.configurations_synced}/{len(report.details)}, '
            f'релизов +{report.releases_created} ~{report.releases_updated}'
            + (f' -{report.releases_deleted}' if report.releases_deleted else ''),
        ))

    def _report_summary(self, report) -> str:
        return (
            f'конфигураций {report.configurations_synced}/{len(report.details)}, '
            f'релизов +{report.releases_created} ~{report.releases_updated}'
        )

    def _failed_configs_message(self, report) -> str:
        failed = [f'{item.slug}: {item.error}' for item in report.details if item.error]
        return '; '.join(failed[:5])
