from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from blog.models import BlogPost
from landing.models import OneCConfiguration, OneCRelease


@override_settings(SITE_URL='https://example.com')
class BlogPostFeedTests(TestCase):
    def setUp(self):
        self.post = BlogPost.objects.create(
            title='Тестовая статья',
            slug='test-post',
            excerpt='Краткое описание статьи.',
            body='## Полный текст',
            is_published=True,
            published_at=timezone.now(),
        )

    def test_blog_rss_returns_xml(self):
        response = self.client.get(reverse('blog:rss'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/rss+xml', response['Content-Type'])
        content = response.content.decode()
        self.assertIn('Тестовая статья', content)
        self.assertIn('https://example.com/blog/test-post/', content)
        self.assertIn('Краткое описание статьи.', content)

    def test_unpublished_posts_are_excluded(self):
        self.post.is_published = False
        self.post.save(update_fields=['is_published'])

        response = self.client.get(reverse('blog:rss'))
        self.assertNotIn('Тестовая статья', response.content.decode())


@override_settings(SITE_URL='https://example.com')
class SiteUpdatesFeedTests(TestCase):
    def setUp(self):
        BlogPost.objects.create(
            title='Статья блога',
            slug='blog-item',
            body='Текст',
            is_published=True,
            published_at=timezone.now(),
        )
        configuration = OneCConfiguration.objects.create(
            slug='feed_ut11',
            name='УТ 11',
            is_published=True,
        )
        OneCRelease.objects.create(
            configuration=configuration,
            version='11.5.27.52',
            release_date=date.today() - timedelta(days=3),
            min_platform='8.3.27.1859',
            sort_order=0,
        )

    def test_site_feed_returns_xml(self):
        response = self.client.get(reverse('site_feed'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/rss+xml', response['Content-Type'])
        content = response.content.decode()
        self.assertIn('Статья блога', content)
        self.assertIn('УТ 11 — 11.5.27.52', content)
