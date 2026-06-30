from unittest.mock import patch

from django.test import TestCase

from landing.services.its_parser import ItsVersion

SAMPLE_ITS_INDEX_HTML = """
<ul>
<li><a href="/db/updinfo/content/284/hdoc" target="_top">1С:Управление торговлей 11</a></li>
</ul>
"""


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
