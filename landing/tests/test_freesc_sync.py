from unittest.mock import patch

from django.test import TestCase

from landing.models import OneCConfiguration
from landing.services.freesc_parser import parse_configurations, parse_release_table

SAMPLE_LIST_HTML = """
<table class="table1">
<tbody>
<tr><th>Номер</th><th>Дата</th><th>From</th><th>Platform</th></tr>
<tr>
<td>&nbsp;&nbsp;11.5.27.52</td>
<td>&nbsp;&nbsp;2026-06-17</td>
<td>&nbsp;&nbsp;11.5.22.186, 11.5.27.50</td>
<td>&nbsp;&nbsp;8.3.27.1859;</td>
</tr>
</tbody>
</table>
"""

SAMPLE_CALC_HTML = """
<select name="cur_conf">
<option value=''>-- Выберите --</option>
<option value= rel_1c_ut11>Управление торговлей, ред. 11</option>
</select>
"""


class ReleaseSyncCommandTests(TestCase):
    def test_sync_dry_run_with_mock(self):
        from django.core.management import call_command

        with patch('landing.services.freesc_sync.fetch_calc_update_page', return_value=SAMPLE_CALC_HTML), \
             patch('landing.services.freesc_sync.fetch_release_list_page', return_value=SAMPLE_LIST_HTML):
            OneCConfiguration.objects.get_or_create(
                slug='rel_1c_ut11',
                defaults={'name': 'УТ 11'},
            )
            call_command('sync_freesc_releases', '--all', '--dry-run')
