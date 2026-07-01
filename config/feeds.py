from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import markdown
from django.conf import settings
from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils import timezone

from blog.models import BlogPost
from blog.templatetags.blog_extras import MARKDOWN_EXTENSIONS
from config.feed_utils import absolute_url, image_mime_type
from landing.tools.release_feed import get_release_feed

SITE_FEED_LIMIT = 30


@dataclass
class SiteFeedItem:
    title: str
    link: str
    description: str
    pubdate: datetime
    enclosure_url: str = ''
    enclosure_mime_type: str = ''


def _release_pubdate(release_date) -> datetime:
    if release_date:
        return timezone.make_aware(datetime.combine(release_date, datetime.min.time()))
    return timezone.now()


def get_site_feed_items(limit: int = SITE_FEED_LIMIT) -> list[SiteFeedItem]:
    items: list[SiteFeedItem] = []

    for release in get_release_feed(days=90, limit=limit):
        parts = [f'Конфигурация: {release.configuration_name}', f'Релиз: {release.version}']
        if release.min_platform:
            parts.append(f'Мин. платформа: {release.min_platform}')
        items.append(
            SiteFeedItem(
                title=f'{release.configuration_name} — {release.version}',
                link=absolute_url(
                    reverse('landing:release_feed') + f'?configuration={release.configuration_slug}'
                ),
                description='. '.join(parts),
                pubdate=_release_pubdate(release.release_date),
            )
        )

    for post in BlogPost.published.all()[:limit]:
        if post.excerpt:
            description = f'<p>{post.excerpt}</p>'
        else:
            description = markdown.markdown(post.body, extensions=MARKDOWN_EXTENSIONS)
        enclosure_url = ''
        enclosure_mime_type = ''
        if post.cover_image:
            enclosure_url = absolute_url(post.cover_image.url)
            enclosure_mime_type = image_mime_type(post.cover_image.name)
        items.append(
            SiteFeedItem(
                title=post.title,
                link=absolute_url(post.get_absolute_url()),
                description=description,
                pubdate=post.published_at,
                enclosure_url=enclosure_url,
                enclosure_mime_type=enclosure_mime_type,
            )
        )

    items.sort(key=lambda item: item.pubdate, reverse=True)
    return items[:limit]


class SiteUpdatesFeed(Feed):
    title = f'Обновления — {settings.SITE_NAME}'
    link = '/'
    description = 'Новые статьи блога и релизы типовых конфигураций 1С.'

    def items(self):
        return get_site_feed_items()

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return item.link

    def item_pubdate(self, item):
        return item.pubdate

    def item_enclosure_url(self, item):
        return item.enclosure_url or None

    def item_enclosure_mime_type(self, item):
        return item.enclosure_mime_type or None
