from django.core.management.base import BaseCommand, CommandError

from landing.models import OneCConfiguration
from landing.services.freesc_sync import sync_releases_for_configuration


class Command(BaseCommand):
    help = (
        'Импорт релизов одной конфигурации с freesc.ru '
        '(обёртка над sync_freesc_releases --config).'
    )

    def add_arguments(self, parser):
        parser.add_argument('configuration', help='slug конфигурации, например rel_1c_ut11')
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Удалить релизы, которых нет на freesc.ru',
        )

    def handle(self, *args, **options):
        slug = options['configuration']
        configuration = OneCConfiguration.objects.filter(slug=slug).first()
        if configuration is None:
            raise CommandError(f'Конфигурация «{slug}» не найдена.')

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
