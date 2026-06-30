from django.test import TestCase

from landing.services.its_parser import (
    build_its_version_url,
    parse_configuration_versions,
    parse_configurations,
    resolve_configuration_slug,
)

SAMPLE_INDEX_HTML = """
<ul>
    <li><a href="/db/updinfo/content/4/hdoc" target="_top">1С:Бухгалтерия 8</a></li>
    <li><a href="/db/updinfo/content/284/hdoc" target="_top">1С:Управление торговлей 11</a></li>
    <li><a href="/db/updinfoarch" target="_top">Архив</a></li>
</ul>
"""

SAMPLE_TRADE_INDEX_HTML = """
<ul>
    <li><a href="/db/updinfo/content/2749/hdoc" target="_top">Новое в версии 11.5.27.56</a></li>
    <li><a href="/db/updinfo/content/2739/hdoc" target="_top">Новое в версии 11.5.27.49</a></li>
</ul>
"""


class ItsParserTests(TestCase):
    def test_parse_configurations(self):
        configs = parse_configurations(SAMPLE_INDEX_HTML)
        self.assertEqual(len(configs), 2)
        self.assertEqual(configs[0].doc_id, 4)
        self.assertEqual(configs[0].slug, 'rel_1c_bp30')
        self.assertEqual(configs[1].slug, 'rel_1c_ut11')

    def test_parse_configuration_versions(self):
        versions = parse_configuration_versions(SAMPLE_TRADE_INDEX_HTML)
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].version, '11.5.27.56')
        self.assertEqual(versions[0].url, build_its_version_url(2749))

    def test_resolve_configuration_slug(self):
        self.assertEqual(resolve_configuration_slug(284, '1С:Управление торговлей 11'), 'rel_1c_ut11')
