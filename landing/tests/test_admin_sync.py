from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from landing.models import ReleaseSyncLog, SiteSettings


class SiteSettingsSyncAdminTests(TestCase):
    def setUp(self):
        SiteSettings.load()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='secret',
        )
        self.client = Client()
        self.client.force_login(self.admin)

    @patch('landing.services.freesc_sync.run_scheduled_sync')
    def test_sync_freesc_releases_view_success(self, run_sync):
        log = ReleaseSyncLog.objects.create(
            status=ReleaseSyncLog.Status.SUCCESS,
            triggered_by=ReleaseSyncLog.Trigger.MANUAL,
            message='конфигураций 3/3, релизов +2 ~5',
        )
        log.finished_at = log.started_at
        log.save(update_fields=['finished_at'])
        run_sync.return_value = log

        url = reverse('admin:landing_sitesettings_sync_freesc_releases')
        response = self.client.get(url, follow=True)

        self.assertEqual(response.status_code, 200)
        run_sync.assert_called_once_with(force=True)
        self.assertContains(response, 'Синхронизация завершена')

    @patch('landing.services.freesc_sync.run_scheduled_sync')
    def test_sync_freesc_releases_view_error(self, run_sync):
        run_sync.side_effect = RuntimeError('network down')

        url = reverse('admin:landing_sitesettings_sync_freesc_releases')
        response = self.client.get(url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Синхронизация прервана')
