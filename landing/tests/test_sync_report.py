from django.test import TestCase

from landing.services.freesc_sync import format_sync_report_message
from landing.services.its_sync import ConfigurationSyncResult, ItsSyncReport


class SyncReportMessageTests(TestCase):
    def test_format_sync_report_includes_latest_versions(self):
        report = ItsSyncReport(
            configurations_synced=2,
            releases_created=3,
            releases_updated=10,
            releases_deleted=5,
            details=[
                ConfigurationSyncResult(
                    slug='rel_1c_bp30',
                    name='Бухгалтерия 3.0',
                    created=1,
                    updated=5,
                    deleted=2,
                    total_fetched=167,
                    latest_version='3.0.200',
                ),
                ConfigurationSyncResult(
                    slug='rel_1c_ut11',
                    name='УТ 11',
                    created=2,
                    updated=5,
                    deleted=3,
                    total_fetched=196,
                    latest_version='11.5.27.56',
                ),
            ],
        )

        message = format_sync_report_message(report)

        self.assertIn('актуальный 3.0.200', message)
        self.assertIn('актуальный 11.5.27.56', message)
        self.assertIn('удалено 5', message.split('\n', 1)[0])
