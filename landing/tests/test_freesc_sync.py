from unittest.mock import patch

from django.test import TestCase

from landing.models import OneCConfiguration, OneCRelease
from landing.services.its_parser import ItsVersion
from landing.services.its_sync import sync_releases_for_configuration

SAMPLE_ITS_INDEX_HTML = """
<ul>
<li><a href="/db/updinfo/content/284/hdoc" target="_top">1С:Управление торговлей 11</a></li>
</ul>
"""

SAMPLE_BP_VERSIONS = [
    ItsVersion(
        doc_id=5001,
        version='3.0.200',
        url='https://its.1c.ru/db/updinfo/content/5001/hdoc',
    ),
    ItsVersion(
        doc_id=5000,
        version='3.0.199',
        url='https://its.1c.ru/db/updinfo/content/5000/hdoc',
    ),
]


class ReleaseSyncCommandTests(TestCase):
    def test_sync_dry_run_with_mock(self):
        from django.core.management import call_command

        with patch('landing.services.its_sync.fetch_updinfo_index', return_value=SAMPLE_ITS_INDEX_HTML), \
             patch('landing.services.its_sync.fetch_configuration_versions', return_value=[
                 ItsVersion(
                     doc_id=2749,
                     version='11.5.27.52',
                     url='https://its.1c.ru/db/updinfo/content/2749/hdoc',
                 ),
             ]):
            from landing.models import OneCConfiguration

            OneCConfiguration.objects.get_or_create(
                slug='rel_1c_ut11',
                defaults={'name': 'УТ 11', 'its_doc_id': 284},
            )
            call_command('sync_its_releases', '--all', '--dry-run')

    def test_bp30b_syncs_from_same_its_section(self):
        configuration, _ = OneCConfiguration.objects.get_or_create(
            slug='rel_1c_bp30b',
            defaults={
                'name': '1С:Бухгалтерия 8 (базовая)',
                'its_doc_id': 4,
                'is_published': True,
            },
        )
        configuration.its_doc_id = 4
        configuration.save(update_fields=['its_doc_id'])
        configuration.releases.all().delete()
        OneCRelease.objects.create(
            configuration=configuration,
            version='3.0.199.13',
            sort_order=0,
        )

        with patch('landing.services.its_sync.fetch_configuration_versions', return_value=SAMPLE_BP_VERSIONS):
            result = sync_releases_for_configuration(configuration, prune=True)

        configuration.refresh_from_db()
        self.assertEqual(result.latest_version, '3.0.200')
        self.assertEqual(configuration.latest_release.version, '3.0.200')
        self.assertFalse(configuration.releases.filter(version='3.0.199.13').exists())
