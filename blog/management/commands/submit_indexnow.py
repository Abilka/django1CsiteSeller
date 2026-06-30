from django.core.management.base import BaseCommand

from blog.models import BlogPost
from blog.services.indexnow import INDEXNOW_BATCH_SIZE, build_absolute_url, submit_urls_batched
from config.sitemaps import StaticViewSitemap


class Command(BaseCommand):
    help = 'Отправить URL сайта в IndexNow (статические страницы и статьи блога)'

    def handle(self, *args, **options):
        urls = []
        static_sitemap = StaticViewSitemap()
        for item in static_sitemap.items():
            urls.append(build_absolute_url(static_sitemap.location(item)))

        for post in BlogPost.published.all():
            urls.append(build_absolute_url(post.get_absolute_url()))

        if not urls:
            self.stdout.write(self.style.WARNING('Нет URL для отправки'))
            return

        result = submit_urls_batched(urls)
        if result['batches_failed']:
            self.stdout.write(self.style.ERROR(
                f'IndexNow: {result["batches_failed"]} из {result["batches_total"]} '
                f'пачек не удалось (по {INDEXNOW_BATCH_SIZE} URL)'
            ))
        elif result['batches_ok']:
            self.stdout.write(self.style.SUCCESS(
                f'IndexNow: отправлено {result["total"]} URL '
                f'({result["batches_total"]} пачек по {INDEXNOW_BATCH_SIZE})'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                'IndexNow: отправка не удалась (проверьте SITE_URL и логи)'
            ))
