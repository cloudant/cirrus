#!/usr/bin/env python
"""
release command tests

"""
import os
import unittest
import tempfile
import mock

from cirrus.release import (
    artifact_name,
    build_and_upload,
    build_release,
    new_release,
    upload_release
)
from cirrus.configuration import Configuration
from pluggage.errors import FactoryError

from harnesses import CirrusConfigurationHarness, write_cirrus_conf


class ReleaseNewCommandTest(unittest.TestCase):
    """
    Test Case for new_release function
    """
    def setUp(self):
        """set up test files"""
        self.dir = tempfile.mkdtemp()
        self.config = os.path.join(self.dir, 'cirrus.conf')
        write_cirrus_conf(self.config,
            **{
                'package': {'name': 'cirrus_unittest', 'version': '1.2.3'},
                'gitflow': {'develop_branch': 'develop', 'release_branch_prefix': 'release/'},
                }
            )
        self.harness = CirrusConfigurationHarness('cirrus.release.load_configuration', self.config)
        self.harness.setUp()
        self.patch_pull = mock.patch('cirrus.release.checkout_and_pull')
        self.patch_branch = mock.patch('cirrus.release.branch')
        self.patch_commit = mock.patch('cirrus.release.commit_files')
        self.mock_pull = self.patch_pull.start()
        self.mock_branch = self.patch_branch.start()
        self.mock_commit = self.patch_commit.start()

    def tearDown(self):
        self.patch_pull.stop()
        self.patch_branch.stop()
        self.patch_commit.stop()
        self.harness.tearDown()
        if os.path.exists(self.dir):
            os.system('rm -rf {0}'.format(self.dir))

    @mock.patch('cirrus.release.has_unstaged_changes')
    @mock.patch('cirrus.release.get_active_branch')
    @mock.patch('cirrus.release.get_active_commit_sha')
    def test_new_release(
        self,
        mock_get_sha,
        mock_get_branch,
        mock_unstaged
    ):
        """
        _test_new_release_

        """
        mock_get_branch.return_value = mock.Mock()
        mock_get_sha.return_value = 'abc123'
        mock_unstaged.return_value = False
        opts = mock.Mock()
        opts.micro = True
        opts.major = False
        opts.minor = False
        opts.release_candidate = False
        opts.bump = None

        # should create a new minor release, editing
        # the cirrus config in the test dir
        new_release(opts)

        # verify new version
        new_conf = Configuration(self.config)
        new_conf.load()
        self.assertEqual(new_conf.package_version(), '1.2.4')

        self.failUnless(self.mock_pull.called)
        self.assertEqual(self.mock_pull.call_args[0][1], 'develop')
        self.failUnless(self.mock_branch.called)
        self.assertEqual(self.mock_branch.call_args[0][1], 'release/1.2.4')
        self.failUnless(self.mock_commit.called)
        self.assertEqual(self.mock_commit.call_args[0][2], 'cirrus.conf')

    @mock.patch('cirrus.release.has_unstaged_changes')
    @mock.patch('cirrus.release.get_active_branch')
    @mock.patch('cirrus.release.get_active_commit_sha')
    def test_new_release_unstaged(
        self,
        mock_get_sha,
        mock_get_branch,
        mock_unstaged
    ):
        """
        test new release fails on unstaged changes

        """
        mock_get_branch.return_value = mock.Mock()
        mock_get_sha.return_value = 'abc123'
        mock_unstaged.return_value = True
        opts = mock.Mock()
        opts.micro = True
        opts.major = False
        opts.minor = False
        opts.release_candidate = False
        opts.bump = None
        self.assertRaises(RuntimeError, new_release, opts)


class ReleaseBuildCommandTest(unittest.TestCase):
    """
    test case for cirrus release build command

    """
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.config = os.path.join(self.dir, 'cirrus.conf')
        write_cirrus_conf(self.config,
            **{
                'package': {'name': 'cirrus_unittest', 'version': '1.2.3'},
                'gitflow': {'develop_branch': 'develop', 'release_branch_prefix': 'release/'}
            }
            )
        self.harness = CirrusConfigurationHarness('cirrus.release.load_configuration', self.config)
        self.harness.setUp()

        self.patch_local =  mock.patch('cirrus.release.local')
        self.mock_local = self.patch_local.start()

    def tearDown(self):
        self.harness.tearDown()
        self.patch_local.stop()

    @mock.patch('cirrus.release.artifact_name')
    @mock.patch('cirrus.release.get_active_commit_sha')
    def test_build_command_raises(self, mock_git_sha, mock_artifact_name):
        """should raise when build artifact is not present"""
        opts = mock.Mock()
        mock_git_sha.return_value = 'abc12'
        mock_artifact_name.return_value = 'some/path/that/does/not/exist'

        self.assertRaises(RuntimeError, build_release, opts)

    def test_build_command(self):
        """test calling build, needs os.path.exists mocks since we arent actually building"""
        with mock.patch('cirrus.release.os') as mock_os:

            mock_os.path = mock.Mock()
            mock_os.path.exists = mock.Mock()
            mock_os.path.exists.return_value = True
            mock_os.path.join = mock.Mock()
            mock_os.path.join.return_value = 'build_artifact'

            opts = mock.Mock()
            opts.dev = None
            result = build_release(opts)
            self.assertEqual(result, 'build_artifact')
            self.failUnless(mock_os.path.exists.called)
            self.assertEqual(mock_os.path.exists.call_args[0][0], 'build_artifact')

            self.failUnless(self.mock_local.called)
            self.assertEqual(self.mock_local.call_args[0][0], 'python setup.py bdist_wheel')

    @mock.patch('cirrus.release.get_active_commit_sha')
    def test_build_command_with_tag(self, mock_git_sha):
        with mock.patch('cirrus.release.os') as mock_os:

            mock_os.path = mock.Mock()
            mock_os.path.exists = mock.Mock()
            mock_os.path.exists.return_value = True
            mock_os.path.join = mock.Mock()
            mock_os.path.join.return_value = 'build_artifact'
            opts = mock.Mock()
            opts.dev = True
            mock_git_sha.return_value = 'abc123'

            result = build_release(opts)
            self.assertEqual(result, 'build_artifact')
            self.failUnless(mock_os.path.exists.called)
            self.assertEqual(
                mock_os.path.exists.call_args[0][0],
                'build_artifact'
            )

            self.failUnless(self.mock_local.called)
            self.assertEqual(
                self.mock_local.call_args[0][0],
                "python setup.py egg_info --tag-build '.abc123' bdist_wheel"
            )


class ReleaseUploadTest(unittest.TestCase):
    """unittest coverage for upload command using plugins"""
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.config = os.path.join(self.dir, 'cirrus.conf')
        write_cirrus_conf(self.config,
            **{
                'package' :{'name': 'cirrus_unittest', 'version': '1.2.3'},
                'github': {'develop_branch': 'develop', 'release_branch_prefix': 'release/'},
                'pypi': {
                    'pypi_upload_path': '/opt/pypi',
                    'pypi_url': 'pypi.cloudant.com',
                    'pypi_username': 'steve',
                    'pypi_ssh_key': 'steves_creds'
                }
            }
            )
        self.harness = CirrusConfigurationHarness('cirrus.release.load_configuration', self.config)
        self.harness.setUp()
        self.artifact_name = artifact_name(self.harness.config)

    def tearDown(self):
        self.harness.tearDown()

    def test_missing_build_artifact(self):
        """test throws if build artifact not found"""
        opts = mock.Mock()
        opts.target = None
        self.assertRaises(RuntimeError, upload_release, opts)

    @mock.patch('cirrus.release.os.path.exists')
    @mock.patch('cirrus.release.get_plugin')
    def test_upload_plugin(self, mock_plugin, mock_exists):
        """test call with well behaved plugin"""
        plugin = mock.Mock()
        plugin.upload = mock.Mock()
        mock_exists.return_value = True
        mock_plugin.return_value = plugin
        opts = mock.Mock()
        opts.plugin = 'pypi'
        opts.test = False
        opts.target = None
        self.assertRaises(RuntimeError, upload_release, opts)
        self.failIf(plugin.upload.called)

    @mock.patch('cirrus.release.os.path.exists')
    @mock.patch('cirrus.release.get_plugin')
    def test_upload_plugin_test_mode(self, mock_plugin, mock_exists):
        plugin = mock.Mock()
        plugin.upload = mock.Mock()
        mock_exists.return_value = True
        mock_plugin.return_value = plugin
        opts = mock.Mock()
        opts.plugin = 'pypi'
        opts.test = True
        self.assertRaises(RuntimeError, upload_release, opts)

    @mock.patch('cirrus.release.os.path.exists')
    def test_upload_bad_plugin(self, mock_exists):
        """test with missing plugin"""
        mock_exists.return_value = True
        opts = mock.Mock()
        opts.plugin = 'womp'
        opts.test = True
        self.assertRaises(RuntimeError, upload_release, opts)


class ReleaseBuildAndUploadTest(unittest.TestCase):
    def setUp(self):
        self.patch_get_active_sha = mock.patch(
            'cirrus.release.get_active_commit_sha'
        )
        self.mock_get_active_sha = self.patch_get_active_sha.start()
        self.patch_local = mock.patch('cirrus.release.local')
        self.mock_local = self.patch_local.start()

    def tearDown(self):
        self.patch_get_active_sha.stop()
        self.patch_local.stop()

    @mock.patch('cirrus.release.get_active_branch')
    def test_build_and_upload(self, mock_get_active_branch):
        """
        Ensures the build_and_upload command can be ran
        """
        opts = mock.Mock()
        opts.dev = False
        mock_head = mock.Mock()
        mock_head.name = 'release/0.0.0'
        mock_get_active_branch.return_value = mock_head
        build_and_upload(opts)
        self.assertFalse(self.mock_get_active_sha.called)
        self.mock_local.assert_called_with(
            'python setup.py egg_info  bdist_wheel upload -r local',
            capture=True
        )

    @mock.patch('cirrus.release.get_active_branch')
    def test_build_and_upload_not_on_release_branch(
        self,
        mock_get_active_branch
    ):
        """
        Ensures the build_and_upload command fails out when ran from a non
        release branch without the --dev option
        """
        opts = mock.Mock()
        opts.dev = False
        mock_head = mock.Mock()
        mock_head.name = 'develop'
        mock_get_active_branch.return_value = mock_head
        self.assertRaises(RuntimeError, build_and_upload, opts)
        self.assertFalse(self.mock_get_active_sha.called)
        self.assertFalse(self.mock_local.called)

    def test_build_and_upload_dev(self):
        """
        Ensures the build_and_upload command can be ran with the 'dev' option
        for creating pre-releases (git sha tagged builds)
        """
        self.mock_get_active_sha.return_value = 'deadbee'
        opts = mock.Mock()
        opts.dev = True
        build_and_upload(opts)
        self.assertTrue(self.mock_get_active_sha.called)
        self.mock_local.assert_called_with(
            'python setup.py egg_info --tag-build ".deadbee" bdist_wheel upload -r local',
            capture=True
        )


class ArtifactNameTests(unittest.TestCase):
    """
    Tests for artifact_name
    """
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        config = os.path.join(self.dir, 'cirrus.conf')
        write_cirrus_conf(
            config,
            **{
                'package': {
                    'name': 'cirrus_unittest',
                    'version': '1.2.3',
                    'python_versions': '2'
                },
                'github': {
                    'develop_branch': 'develop',
                    'release_branch_prefix': 'release/'
                },
                'pypi': {
                    'pypi_upload_path': '/opt/pypi',
                    'pypi_url': 'pypi.cloudant.com',
                    'pypi_username': 'steve',
                    'pypi_ssh_key': 'steves_creds'
                }
            }
        )
        self.harness = CirrusConfigurationHarness(
            'cirrus.release.load_configuration',
            config
        )
        self.harness.setUp()

    def tearDown(self):
        self.harness.tearDown()

    def test_artifact_name(self):
        """
        Ensures artifact_name returns as expected when no tag is provided
        """
        self.assertIn(
            'dist/cirrus_unittest-1.2.3-py2-none-any.whl',
            artifact_name(self.harness.config)
        )

    def test_tagged_artifact_name(self):
        """
        Ensures artifact_name returns as expected when a tag is provided
        """
        self.assertIn(
            'dist/cirrus_unittest-1.2.3.somesortoftag-py2-none-any.whl',
            artifact_name(self.harness.config, tag='somesortoftag')
        )


if __name__ == '__main__':
    unittest.main()
