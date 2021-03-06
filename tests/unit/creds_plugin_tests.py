#!/usr/bin/env python
"""
creds_plugin tests
"""
import unittest

from cirrus.creds_plugin import CredsPlugin


class CredsPluginTest(unittest.TestCase):
    """
    test coverage for creds plugin object
    """
    def test_creds_plugin(self):
        """test base class methods"""
        plugin = CredsPlugin()
        methods = [x[0] for x in plugin.credential_methods()]
        mapping = plugin.credential_map()
        self.assertTrue(all(m in mapping for m in methods))

        gh_defaults = plugin.github_credentials()
        self.assertIn('github_user', gh_defaults)
        self.assertIn('github_token', gh_defaults)
        self.assertEqual(gh_defaults['github_user'], None)
        self.assertEqual(gh_defaults['github_token'], None)


if __name__ == '__main__':
    unittest.main()
