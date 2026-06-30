from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import BlogPost


class BaseSitemap(Sitemap):
    protocol = 'https'

    def get_domain(self, site=None):
        if settings.SITE_HOST:
            return settings.SITE_HOST
        return super().get_domain(site)


class StaticViewSitemap(BaseSitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return [
            'landing:index',
            'landing:tools_index',
            'landing:update_calculator',
            'landing:platform_check',
            'landing:release_feed',
            'landing:task_estimator',
            'landing:query_formatter',
            'landing:migration_calculator',
            'landing:release_version_help',
            'landing:user_agreement',
            'landing:privacy_policy',
            'blog:list',
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(BaseSitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return BlogPost.published.all()

    def lastmod(self, obj):
        return obj.updated_at
