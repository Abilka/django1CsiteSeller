from django.test import TestCase

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
<option value= rel_1c_bp30>Бухгалтерия предприятия 3.0</option>
</select>
"""


class FreescParserTests(TestCase):
    def test_parse_release_table(self):
        rows = parse_release_table(SAMPLE_LIST_HTML)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].version, '11.5.27.52')
        self.assertEqual(rows[0].from_versions, ['11.5.22.186', '11.5.27.50'])
        self.assertEqual(rows[0].min_platform, '8.3.27.1859')

    def test_parse_configurations(self):
        configs = parse_configurations(SAMPLE_CALC_HTML)
        self.assertEqual(len(configs), 2)
        self.assertEqual(configs[0].slug, 'rel_1c_ut11')
