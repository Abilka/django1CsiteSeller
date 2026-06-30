from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from landing.models import OneCConfiguration, OneCRelease, SiteSettings
from landing.services.update_calculator import (
    ReleaseInfo,
    UpdatePathError,
    build_update_chain,
    calculate_update_path,
)


class UpdateCalculatorServiceTests(TestCase):
    def setUp(self):
        self.configuration, _ = OneCConfiguration.objects.get_or_create(
            slug='rel_1c_ut11',
            defaults={'name': 'Управление торговлей, ред. 11'},
        )
        self.configuration.releases.all().delete()
        releases = [
            ('11.5.27.52', 0, ['11.5.22.186', '11.5.27.50'], '8.3.27.1859'),
            ('11.5.27.50', 1, ['11.5.22.186'], '8.3.27.1859'),
            ('11.5.22.186', 2, ['11.5.17.234'], '8.3.27.1559'),
            ('11.5.17.234', 3, ['11.5.12.270'], '8.3.27.1559'),
            ('11.5.12.270', 4, ['11.5.12.251'], '8.3.27.1559'),
            ('11.5.12.251', 5, [], ''),
        ]
        for version, sort_order, from_versions, platform in releases:
            OneCRelease.objects.create(
                configuration=self.configuration,
                version=version,
                from_versions=from_versions,
                min_platform=platform,
                sort_order=sort_order,
                its_url=f'https://its.1c.ru/db/updinfo/content/{1000 + sort_order}/hdoc',
            )

    def test_build_chain_from_old_release(self):
        result = calculate_update_path(self.configuration, '11.5.12.251')
        self.assertEqual(
            [step.version for step in result.chain],
            ['11.5.12.270', '11.5.17.234', '11.5.22.186', '11.5.27.52'],
        )
        self.assertTrue(all(step.url for step in result.chain))
        self.assertEqual(result.min_platform, '8.3.27.1859')
        self.assertFalse(result.is_up_to_date)
        self.assertEqual(result.steps_count, 4)

    def test_update_price_calculation(self):
        settings = SiteSettings.load()
        settings.hourly_rate = 2000
        settings.update_hours_per_release = 0.5
        settings.save()

        result = calculate_update_path(self.configuration, '11.5.12.251', site_settings=settings)
        self.assertEqual(result.estimated_hours, 2.0)
        self.assertEqual(result.estimated_price, 4000)

    def test_update_price_zero_when_up_to_date(self):
        result = calculate_update_path(self.configuration, '11.5.27.52')
        self.assertEqual(result.estimated_price, 0)
        self.assertEqual(result.estimated_hours, 0)

    def test_already_latest(self):
        result = calculate_update_path(self.configuration, '11.5.27.52')
        self.assertEqual(result.chain, [])
        self.assertTrue(result.is_up_to_date)

    def test_one_step_to_latest(self):
        result = calculate_update_path(self.configuration, '11.5.27.50')
        self.assertEqual([step.version for step in result.chain], ['11.5.27.52'])

    def test_no_path_raises(self):
        infos = [
            ReleaseInfo('2.0.0', {'1.0.0'}, ''),
            ReleaseInfo('1.0.0', set(), ''),
        ]
        with self.assertRaises(UpdatePathError):
            build_update_chain('rel_1c_ut11', infos, '9.9.9.9')


class UpdateCalculatorAPITests(APITestCase):
    def setUp(self):
        self.configuration, _ = OneCConfiguration.objects.get_or_create(
            slug='rel_1c_bp30',
            defaults={'name': 'Бухгалтерия предприятия 3.0', 'is_published': True},
        )
        self.configuration.releases.all().delete()
        OneCRelease.objects.create(
            configuration=self.configuration,
            version='3.0.60.34',
            from_versions=['3.0.58.41'],
            min_platform='8.3.27.1859',
            sort_order=0,
        )
        OneCRelease.objects.create(
            configuration=self.configuration,
            version='3.0.58.41',
            from_versions=[],
            min_platform='8.3.27.1559',
            sort_order=1,
        )

    def test_public_calculate(self):
        response = self.client.post('/api/v1/calculate/', {
            'configuration': 'rel_1c_bp30',
            'current_version': '3.0.58.41',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chain'], [{
            'version': '3.0.60.34',
            'url': '',
        }])
        self.assertEqual(response.data['steps_count'], 1)
        self.assertEqual(response.data['estimated_hours'], '0.50')
        self.assertIn('estimated_price', response.data)

    def test_versions_list(self):
        response = self.client.get('/api/v1/configurations/rel_1c_bp30/versions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['latest_version'], '3.0.60.34')
        self.assertIn('3.0.58.41', response.data['versions'])

    def test_release_crud_requires_auth(self):
        response = self.client.post('/api/v1/releases/', {
            'configuration': self.configuration.pk,
            'version': '3.0.61.1',
            'from_versions': ['3.0.60.34'],
            'sort_order': 0,
        }, format='json')
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_release_crud_with_token(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username='admin', password='secret')
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.post('/api/v1/releases/', {
            'configuration': self.configuration.pk,
            'version': '3.0.61.1',
            'from_versions': ['3.0.60.34'],
            'min_platform': '8.3.27.1859',
            'sort_order': 0,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(OneCRelease.objects.filter(version='3.0.61.1').exists())

        release_id = response.data['id']
        response = self.client.patch(f'/api/v1/releases/{release_id}/', {
            'min_platform': '8.3.27.1900',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['min_platform'], '8.3.27.1900')

        response = self.client.delete(f'/api/v1/releases/{release_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
