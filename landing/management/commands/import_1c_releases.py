from django.core.management.base import BaseCommand, CommandError

from landing.models import OneCConfiguration
from landing.services.freesc_parser import parse_release_table
from landing.services.freesc_sync import sync_releases_for_configuration


class Command(BaseCommand):
    help = (
        'Импорт релизов одной конфигурации с freesc.ru '
        '(обёртка над sync_freesc_releases --config).'
    )

    def add_arguments(self, parser):
        parser.add_argument('configuration', help='slug конфигурации, например rel_1c_ut11')
        parser.add_argument(
            '--file',
            dest='file_path',
            help='Путь к сохранённому HTML (для отладки парсера)',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Удалить релизы, которых нет в загруженной таблице',
        )

    def handle(self, *args, **options):
        slug = options['configuration']
        configuration = OneCConfiguration.objects.filter(slug=slug).first()
        if configuration is None:
            raise CommandError(f'Конфигурация «{slug}» не найдена.')

        if options.get('file_path'):
            with open(options['file_path'], encoding='utf-8') as file:
                html = file.read()
            rows = parse_release_table(html)
            if not rows:
                raise CommandError('Не удалось распознать таблицу релизов.')
            if options['replace']:
                fetched = {row.version for row in rows}
                configuration.releases.exclude(version__in=fetched).delete()
            created = updated = 0
            for row in rows:
                _, is_created = configuration.releases.update_or_create(
                    version=row.version,
                    defaults={
                        'release_date': row.release_date,
                        'from_versions': row.from_versions,
                        'min_platform': row.min_platform,
                        'sort_order': row.sort_order,
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1
            self.stdout.write(self.style.SUCCESS(
                f'Импорт из файла: создано {created}, обновлено {updated}.',
            ))
            return

        detail = sync_releases_for_configuration(
            configuration,
            prune=options['replace'],
        )
        if detail.error:
            raise CommandError(detail.error)
        self.stdout.write(self.style.SUCCESS(
            f'Импорт завершён: создано {detail.created}, обновлено {detail.updated}, '
            f'удалено {detail.deleted}.',
        ))
