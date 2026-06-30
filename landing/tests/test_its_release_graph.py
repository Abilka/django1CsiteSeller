from django.test import TestCase

from landing.services.its_release_graph import build_chain_versions, derive_from_versions


class ItsReleaseGraphTests(TestCase):
    def test_ut11_chain_from_old_release(self):
        versions = [
            '11.5.27.52',
            '11.5.22.186',
            '11.5.17.234',
            '11.5.12.270',
            '11.5.12.251',
        ]
        chain = build_chain_versions('rel_1c_ut11', versions, '11.5.12.251', '11.5.27.52')
        self.assertEqual(
            chain,
            ['11.5.12.270', '11.5.17.234', '11.5.22.186', '11.5.27.52'],
        )

    def test_ut11_one_step_to_latest(self):
        versions = ['11.5.27.52', '11.5.27.50', '11.5.22.186']
        chain = build_chain_versions('rel_1c_ut11', versions, '11.5.27.50', '11.5.27.52')
        self.assertEqual(chain, ['11.5.27.52'])

    def test_derive_from_versions_contains_previous_milestone(self):
        versions = ['11.5.27.52', '11.5.22.186', '11.5.17.234']
        mapping = derive_from_versions('rel_1c_ut11', versions)
        self.assertIn('11.5.22.186', mapping['11.5.27.52'])
