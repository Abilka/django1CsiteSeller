from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from landing.models import MigrationPath, MigrationPathStep, OneCConfiguration, OneCRelease, PriceListItem, SiteSettings, TypicalTask
from landing.tools.migration_calc import estimate_migration
from landing.tools.platform_check import (
    PlatformCheckError,
    check_platform_compatibility,
    get_known_platform_versions,
    resolve_platform_version,
)
from landing.tools.query_formatter import format_query
from landing.tools.release_feed import get_release_feed
from landing.tools.task_estimator import estimate_tasks
from landing.tools.version_utils import compare_versions


class VersionUtilsTests(TestCase):
    def test_compare_versions(self):
        self.assertEqual(compare_versions('8.3.27.1859', '8.3.24.1467'), 1)
        self.assertEqual(compare_versions('8.3.24.1467', '8.3.27.1859'), -1)
        self.assertEqual(compare_versions('8.3.27', '8.3.27.0'), 0)


class PlatformCheckTests(TestCase):
    def setUp(self):
        self.configuration = OneCConfiguration.objects.create(
            slug='test_ut11',
            name='Тест УТ 11',
            is_published=True,
        )
        OneCRelease.objects.create(
            configuration=self.configuration,
            version='11.5.27.52',
            min_platform='8.3.27.1859',
            sort_order=0,
        )

    def test_compatible_platform(self):
        result = check_platform_compatibility(self.configuration, '8.3.27.2000')
        self.assertTrue(result.is_compatible)

    def test_incompatible_platform(self):
        result = check_platform_compatibility(self.configuration, '8.3.24.1467')
        self.assertFalse(result.is_compatible)

    def test_get_known_platform_versions(self):
        versions = get_known_platform_versions()
        self.assertIn('8.3.27.1859', versions)

    def test_resolve_platform_version_custom(self):
        self.assertEqual(
            resolve_platform_version('__custom__', '8.3.24.100'),
            '8.3.24.100',
        )

    def test_missing_platform_raises(self):
        with self.assertRaises(PlatformCheckError):
            check_platform_compatibility(self.configuration, '')


class ReleaseFeedTests(TestCase):
    def setUp(self):
        self.configuration = OneCConfiguration.objects.create(
            slug='test_feed',
            name='Тест',
            is_published=True,
        )
        OneCRelease.objects.create(
            configuration=self.configuration,
            version='1.0.1',
            release_date=date.today() - timedelta(days=5),
            min_platform='8.3.27.1859',
        )

    def test_get_release_feed(self):
        items = get_release_feed(days=30)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].version, '1.0.1')


class TaskEstimatorTests(TestCase):
    def setUp(self):
        settings = SiteSettings.load()
        settings.hourly_rate = 1000
        settings.save()
        self.task = TypicalTask.objects.create(
            title='Настройка отчёта',
            estimated_hours=Decimal('2'),
            duration='1 день',
        )
        self.price_item = PriceListItem.objects.create(
            category=PriceListItem.Category.DEVELOPMENT,
            name='Доработка печатной формы',
            hours_from=Decimal('2'),
            hours_to=Decimal('4'),
        )

    def test_estimate_tasks(self):
        result = estimate_tasks([self.task.pk], [self.price_item.pk])
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.total_hours, 5.0)
        self.assertEqual(result.total_price, 5000)


class QueryFormatterTests(TestCase):
    def test_format_query(self):
        source = 'выбрать ссылка из справочник.номенклатура'
        result = format_query(source)
        self.assertIn('ВЫБРАТЬ', result.formatted)
        self.assertIn('ИЗ', result.formatted)

    def test_unbalanced_parentheses_warning(self):
        result = format_query('ВЫБРАТЬ (1 ИЗ Справочник.Тест')
        self.assertTrue(result.warnings)


class MigrationCalcTests(TestCase):
    def setUp(self):
        settings = SiteSettings.load()
        settings.hourly_rate = 1500
        settings.save()
        self.path = MigrationPath.objects.create(
            slug='test-path',
            name='Тестовая миграция',
            source_name='A',
            target_name='B',
        )
        MigrationPathStep.objects.create(
            migration_path=self.path,
            title='Этап 1',
            estimated_hours=Decimal('10'),
            sort_order=0,
        )

    def test_estimate_migration(self):
        result = estimate_migration(self.path)
        self.assertEqual(result.total_hours, 10.0)
        self.assertEqual(result.total_price, 15000)


class ToolsPageTests(TestCase):
    def test_tools_index_page(self):
        response = self.client.get(reverse('landing:tools_index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Проверка платформы 1С')

    def test_platform_check_page(self):
        response = self.client.get(reverse('landing:platform_check'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Выберите версию')

    def test_release_feed_rss(self):
        response = self.client.get(reverse('landing:release_feed_rss'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/rss+xml', response['Content-Type'])

    def test_release_feed_rss_with_configuration_filter(self):
        response = self.client.get(
            reverse('landing:release_feed_rss'),
            {'configuration': 'test_feed'},
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('application/rss+xml', response['Content-Type'])
        self.assertIn('test_feed', content)


class ToolsApiTests(APITestCase):
    def setUp(self):
        self.configuration = OneCConfiguration.objects.create(
            slug='api_ut11',
            name='API УТ 11',
            is_published=True,
        )
        OneCRelease.objects.create(
            configuration=self.configuration,
            version='11.5.27.52',
            min_platform='8.3.27.1859',
            sort_order=0,
        )

    def test_platform_check_api(self):
        response = self.client.post('/api/v1/tools/platform-check/', {
            'configuration': 'api_ut11',
            'platform_version': '8.3.27.2000',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_compatible'])

    def test_query_formatter_api(self):
        response = self.client.post('/api/v1/tools/query-formatter/', {
            'query': 'ВЫБРАТЬ 1',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('formatted', response.data)

    def test_release_feed_api(self):
        response = self.client.get('/api/v1/tools/release-feed/', {'days': 90})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('items', response.data)
