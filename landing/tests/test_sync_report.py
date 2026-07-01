from django.test import TestCase

from landing.services.freesc_sync import ConfigurationSyncResult, FreescSyncReport, format_sync_report_message


class SyncReportMessageTests(TestCase):
    def test_format_sync_report_includes_latest_versions(self):
        report = FreescSyncReport(
            configurations_synced=1,
            releases_created=3,
            releases_updated=10,
            releases_deleted=2,
            details=[
                ConfigurationSyncResult(
                    slug='rel_1c_bp30',
                    name='Бухгалтерия предприятия 3.0',
                    created=1,
                    updated=5,
                    deleted=2,
                    total_fetched=654,
                    latest_version='3.0.199.13',
                ),
            ],
        )

        message = format_sync_report_message(report)

        self.assertIn('актуальный 3.0.199.13', message)
        self.assertIn('на freesc.ru: 654', message)
        self.assertIn('удалено 2', message.split('\n', 1)[0])
