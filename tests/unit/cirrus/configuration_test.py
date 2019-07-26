#!/usr/bin/env python
"""
tests for configuration module
"""
import os
import unittest
import configparser
import tempfile
from unittest import mock

from cirrus.plugins.creds.default import Default
from cirrus.configuration import load_configuration


class ConfigurationTests(unittest.TestCase):
    """
    tests for cirrus.conf interface class

    """
    def setUp(self):
        """create a sample conf file"""
        self.dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.dir, 'cirrus.conf')
        self.gitconfig = os.path.join(self.dir, '.gitconfig')

        parser = configparser.RawConfigParser()
        parser.add_section('package')
        parser.add_section('gitflow')
        parser.add_section('pypi')
        parser.set(
            'pypi',
            'pypi_url',
            'na.artifactory.swg-devops.com/artifactory/api/pypi/wcp-sapi-pypi-virtual'
        )
        parser.set('package', 'name', 'cirrus_tests')
        parser.set('package', 'version', '1.2.3')
        parser.set('package', 'python_versions', '2, 3')
        parser.set('gitflow', 'develop_branch', 'develop')
        parser.set('gitflow', 'release_branch_prefix', 'release/')
        parser.set('gitflow', 'feature_branch_prefix', 'feature/')

        with open(self.test_file, 'w') as handle:
            parser.write(handle)

        gitconf = configparser.RawConfigParser()
        gitconf.add_section('cirrus')
        gitconf.set('cirrus', 'credential-plugin', 'default')

        with open(self.gitconfig, 'w') as handle:
            gitconf.write(handle)

        self.gitconf_str = "cirrus.credential-plugin=default"

        self.patcher = mock.patch('cirrus.plugins.creds.default.os')
        default_os = self.patcher.start()
        default_os.path = mock.Mock()
        default_os.path.join = mock.Mock()
        default_os.path.join.return_value = self.gitconfig

    def tearDown(self):
        """cleanup"""
        self.patcher.stop()
        if os.path.exists(self.dir):
            os.system('rm -rf {0}'.format(self.dir))

    @mock.patch('cirrus.gitconfig.shell_command')
    def test_reading(self, mock_shell):
        """test config load """
        #test read and accessors
        mock_shell.return_value = self.gitconf_str
        config = load_configuration(package_dir=self.dir, gitconfig_file=self.gitconfig)
        self.assertEqual(config.package_version(), '1.2.3')
        self.assertEqual(config.package_name(), 'cirrus_tests')
        self.assertEqual(config.python_versions(), 'py2.py3')

        self.assertEqual(config.gitflow_branch_name(), 'develop')
        self.assertEqual(config.gitflow_release_prefix(), 'release/')
        self.assertEqual(config.gitflow_feature_prefix(), 'feature/')

        self.assertEqual(config.release_notes(), (None, None))
        self.assertEqual(config.version_file(), (None, '__version__'))

        self.assertIsNotNone(config.credentials)
        self.assertTrue(isinstance(config.credentials, Default))

        # test updating version
        config.update_package_version('1.2.4')
        self.assertEqual(config.package_version(), '1.2.4')
        config2 = load_configuration(package_dir=self.dir)
        self.assertEqual(config2.package_version(), '1.2.4')

    @mock.patch('cirrus.gitconfig.shell_command')
    @mock.patch('cirrus.configuration.subprocess.Popen')
    def test_reading_missing(self, mock_pop, mock_shell):
        """test config load using repo dir"""
        mock_result = mock.Mock()
        mock_result.communicate = mock.Mock()
        mock_result.returncode = 0
        mock_result.communicate.return_value = (self.dir.encode(), None)
        mock_pop.return_value = mock_result
        mock_shell.return_value = self.gitconf_str
        config = load_configuration(package_dir="womp")

        self.assertTrue(mock_result.communicate.called)
        mock_pop.assert_has_calls([
            mock.call(['git', 'rev-parse', '--show-toplevel'], stdout=-1)
        ])
        self.assertEqual(config.package_version(), '1.2.3')
        self.assertEqual(config.package_name(), 'cirrus_tests')
        self.assertTrue(mock_shell.called)
        mock_shell.assert_has_calls([
            mock.call('git config --file {} -l'.format(self.gitconfig))
        ])

    def test_configuration_map(self):
        """test building config mapping"""
        config = load_configuration(package_dir=self.dir, gitconfig_file=self.gitconfig)
        mapping = config.configuration_map()
        self.assertIn('cirrus', mapping)
        self.assertIn('credentials', mapping['cirrus'])
        self.assertIn('configuration', mapping['cirrus'])
        self.assertIn('github_credentials', mapping['cirrus']['credentials'])
        self.assertEqual(
            mapping['cirrus']['credentials']['github_credentials'],
            {'github_user': None, 'github_token': None}
        )
        self.assertEqual(
            mapping['cirrus']['configuration']['package']['name'], 'cirrus_tests'
        )

    @mock.patch('cirrus.gitconfig.shell_command')
    def test_pypi_server(self, mock_shell):
        """
        Ensures the pypi url (server) can be obtained from the config
        """
        mock_shell.return_value = self.gitconf_str
        config = load_configuration(
            package_dir=self.dir,
            gitconfig_file=self.gitconfig
        )
        self.assertEqual(
            config.pypi_server(),
            'na.artifactory.swg-devops.com/artifactory/api/pypi/wcp-sapi-pypi-virtual'
        )

    @mock.patch('cirrus.gitconfig.shell_command')
    def test_pypi_url(self, mock_shell):
        """
        Ensures the full pypi url can be returned
        """
        mock_shell.return_value = self.gitconf_str
        config = load_configuration(
            package_dir=self.dir,
            gitconfig_file=self.gitconfig
        )
        config.credentials.pypi_credentials = mock.Mock()
        config.credentials.pypi_credentials.return_value = {
            'username': 'doge@dogehous.bark',
            'token': 'wowsuchtoken'
        }
        self.assertEqual(
            config.pypi_url(),
            'https://doge%40dogehous.bark:wowsuchtoken@na.artifactory.swg-devops.com/artifactory/api/pypi/wcp-sapi-pypi-virtual/simple'
        )


if __name__ == '__main__':
    unittest.main()
