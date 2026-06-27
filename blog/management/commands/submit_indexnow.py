from django.core.management.base import BaseCommand

from blog.models import BlogPost
from blog.services.indexnow import build_absolute_url, notify_indexnow
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

        if notify_indexnow(urls):
            self.stdout.write(self.style.SUCCESS(f'IndexNow: отправлено {len(urls)} URL'))
        else:
            self.stdout.write(self.style.ERROR('IndexNow: отправка не удалась (проверьте SITE_URL и логи)'))
