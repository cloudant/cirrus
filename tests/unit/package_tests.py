#!/usr/bin/env python
"""tests for package commands """
from unittest import TestCase, mock, skip
import os
import json
import tempfile
import configparser

from cirrus.package import (
    create_files,
    setup_branches,
    commit_and_tag,
    build_parser,
    backup_file,
    init_package,
    build_project

)

from .harnesses import CirrusConfigurationHarness


class BuildParserTest(TestCase):
    """test for cli parser"""
    def test_build_parser(self):
        argslist = ['init']
        self.assertRaises(SystemExit, build_parser, argslist)

        argslist = ['init', '-p', 'throwaway', '-s', 'src']
        opts = build_parser(argslist)
        self.assertEqual(opts.source, 'src')
        self.assertEqual(opts.package, 'throwaway')
        self.assertEqual(opts.master, 'master')
        self.assertEqual(opts.develop, 'develop')


class GitFunctionTests(TestCase):
    """
    tests for git util functions
    """
    def setUp(self):
        """
        set up for tests
        """
        self.tempdir = tempfile.mkdtemp()
        self.repo = os.path.join(self.tempdir, 'throwaway')
        os.mkdir(self.repo)
        self.bak_file = os.path.join(self.repo, 'backmeup')
        with open(self.bak_file, 'w') as handle:
            handle.write("this file exists")

        self.patch_working_dir = mock.patch('cirrus.package.working_dir')
        self.mock_wd = self.patch_working_dir.start()

    def tearDown(self):
        self.patch_working_dir.stop()
        if os.path.exists(self.tempdir):
            os.system('rm -rf {}'.format(self.tempdir))

    def test_backup_file(self):
        """test backup_file"""
        backup_file(self.bak_file)
        files = os.listdir(self.repo)
        self.assertIn('backmeup', files)
        self.assertIn('backmeup.BAK', files)

    @mock.patch('cirrus.package.branch')
    @mock.patch('cirrus.package.push')
    @mock.patch('cirrus.package.get_active_branch')
    def test_setup_branches(self, mock_active, mock_push, mock_branch):
        """test setup_branches"""
        opts = mock.Mock()
        opts.no_remote = False
        opts.repo = self.repo
        mock_active.return_value = 'mock_develop'

        setup_branches(opts)
        self.assertEqual(mock_branch.call_count, 2)
        self.assertTrue(mock_push.called)
        self.assertTrue(mock_active.called)

        mock_push.reset_mock()
        opts.no_remote = True
        setup_branches(opts)
        self.assertTrue(not mock_push.called)

    @mock.patch('cirrus.package.commit_files_optional_push')
    @mock.patch('cirrus.package.get_tags')
    @mock.patch('cirrus.package.tag_release')
    @mock.patch('cirrus.package.branch')
    def test_commit_and_tag(self, mock_branch, mock_tag_rel, mock_tags, mock_commit):
        opts = mock.Mock()
        opts.no_remote = False
        opts.repo = self.repo
        opts.master = 'master'
        opts.version = '0.0.0'

        #tag doesnt exist
        mock_tags.return_value = ['0.0.1']
        commit_and_tag(opts, 'file1', 'file2')

        self.assertTrue(mock_commit.called)
        mock_commit.assert_has_calls([
            mock.call(
                self.repo,
                'git cirrus package init',
                True,
                'file1',
                'file2'
            )
        ])
        self.assertTrue(mock_tags.called)
        self.assertTrue(mock_tag_rel.called)
        self.assertTrue(mock_branch.called)

        # tag exists
        opts.version = '0.0.1'
        mock_tag_rel.reset_mock()
        commit_and_tag(opts, 'file1', 'file2')
        self.assertTrue(not mock_tag_rel.called)

class CreateFilesTest(TestCase):
    """mocked create_files function tests"""
    def setUp(self):
        """
        set up for tests
        """
        self.tempdir = tempfile.mkdtemp()
        self.repo = os.path.join(self.tempdir, 'throwaway')
        src_dir = os.path.join(self.repo, 'src')
        pkg_dir = os.path.join(self.repo, 'src', 'unittests')
        os.mkdir(self.repo)
        os.mkdir(src_dir)
        os.mkdir(pkg_dir)
        init_file = os.path.join(pkg_dir, '__init__.py')
        with open(init_file, 'w') as handle:
            handle.write('# initfile\n')
            handle.write('__version__=\'0.0.0\'\n')

    def tearDown(self):
        if os.path.exists(self.tempdir):
            os.system('rm -rf {}'.format(self.tempdir))

    def test_create_files(self):
        """test create_files call and content of files"""
        opts = mock.Mock()
        opts.repo = self.repo
        opts.source = 'src'
        opts.version = '0.0.1'
        opts.version_file = None
        opts.templates = ['include steve/*']
        opts.history_file = 'HISTORY.md'
        opts.package = 'unittests'
        opts.create_version_file = False
        opts.desc = 'testing123'
        opts.org = 'IBM Cloudant'
        opts.develop = 'test-develop'

        create_files(opts)

        dir_list = os.listdir(self.repo)
        self.assertIn('cirrus.conf', dir_list)
        self.assertIn('HISTORY.md', dir_list)
        self.assertIn('MANIFEST.in', dir_list)
        self.assertIn('setup.py', dir_list)

        cirrus_conf = os.path.join(self.repo, 'cirrus.conf')
        config = configparser.RawConfigParser()
        config.read(cirrus_conf)
        self.assertEqual(config.get('package', 'name'), opts.package)
        self.assertEqual(config.get('package', 'version'), opts.version)

        history = os.path.join(self.repo, 'HISTORY.md')
        with open(history, 'r') as handle:
            self.assertIn('CIRRUS_HISTORY_SENTINEL', handle.read())

        manifest = os.path.join(self.repo, 'MANIFEST.in')
        with open(manifest, 'r') as handle:
            content = handle.read()
            self.assertIn('include requirements.txt', content)
            self.assertIn('include cirrus.conf', content)
            self.assertIn('include steve/*', content)

        version = os.path.join(self.repo, 'src', 'unittests', '__init__.py')
        with open(version, 'r') as handle:
            self.assertTrue(opts.version in handle.read())

    def test_create_files_with_version(self):
        """test create_files call and content of files"""
        opts = mock.Mock()
        opts.repo = self.repo
        opts.create_version_file = True
        opts.source = 'src'
        opts.version = '0.0.1'
        opts.version_file = None
        opts.templates = ['include steve/*']
        opts.history_file = 'HISTORY.md'
        opts.package = 'unittests'
        opts.desc = 'testing123'
        opts.org = 'IBM Cloudant'
        opts.develop = 'test-develop'

        version = os.path.join(self.repo, 'src', 'unittests', '__init__.py')
        os.system('rm -f {}'.format(version))
        create_files(opts)

        dir_list = os.listdir(self.repo)
        self.assertIn('cirrus.conf', dir_list)
        self.assertIn('HISTORY.md', dir_list)
        self.assertIn('MANIFEST.in', dir_list)
        self.assertIn('setup.py', dir_list)

        cirrus_conf = os.path.join(self.repo, 'cirrus.conf')
        config = configparser.RawConfigParser()
        config.read(cirrus_conf)
        self.assertEqual(config.get('package', 'name'), opts.package)
        self.assertEqual(config.get('package', 'version'), opts.version)

        history = os.path.join(self.repo, 'HISTORY.md')
        with open(history, 'r') as handle:
            self.assertIn('CIRRUS_HISTORY_SENTINEL', handle.read())

        manifest = os.path.join(self.repo, 'MANIFEST.in')
        with open(manifest, 'r') as handle:
            content = handle.read()
            self.assertIn('include requirements.txt', content)
            self.assertIn('include cirrus.conf', content)
            self.assertIn('include steve/*', content)

        version = os.path.join(self.repo, 'src', 'unittests', '__init__.py')
        with open(version, 'r') as handle:
            self.assertTrue(opts.version in handle.read())


@skip("Integ test not unit test")
class PackageInitCommandIntegTest(TestCase):
    """test case for package init command """

    def setUp(self):
        """
        set up for tests
        """
        self.tempdir = tempfile.mkdtemp()
        self.repo = os.path.join(self.tempdir, 'throwaway')
        src_dir = os.path.join(self.repo, 'src')
        pkg_dir = os.path.join(self.repo, 'src', 'throwaway')
        os.mkdir(self.repo)
        os.mkdir(src_dir)
        os.mkdir(pkg_dir)
        init_file = os.path.join(pkg_dir, '__init__.py')
        with open(init_file, 'w') as handle:
            handle.write('# initfile\n')
        cmd = (
            "cd {} && git init && "
            "git checkout -b master && "
            "git commit --allow-empty -m \"new repo\" "
        ).format(self.repo)
        os.system(cmd)

    def tearDown(self):
        if os.path.exists(self.tempdir):
            os.system('rm -rf {}'.format(self.tempdir))

    def test_init_command(self):
        """test the init command"""
        argslist = [
            'init', '-p', 'throwaway', '-r', self.repo,
            '--no-remote',
            '-s', 'src',
            '--templates', 'src/throwaway/templates/*'
        ]
        opts = build_parser(argslist)
        init_package(opts)
        conf = os.path.join(self.repo, 'cirrus.conf')
        self.assertTrue(os.path.exists(conf))

    @mock.patch('cirrus.editor_plugin.load_configuration')
    def test_project_sublime_command(self, mock_lc):
        """
        test the sublime project command plugin

        """
        mock_config = mock.Mock()
        mock_config.package_name = mock.Mock(return_value='unittests')
        mock_lc.return_value = mock_config

        argslist = [
            'project',
            '-t', 'Sublime',
            '-r', self.repo,
        ]
        opts = build_parser(argslist)
        build_project(opts)
        proj = os.path.join(self.repo, 'unittests.sublime-project')
        self.assertTrue(os.path.exists(proj))
        with open(proj, 'r') as handle:
            data = json.load(handle)
        self.assertIn('folders', data)
        self.assertTrue(data['folders'])
        self.assertIn('path', data['folders'][0])
        self.assertEqual(data['folders'][0]['path'], self.repo)

        build = data['build_systems'][0]
        self.assertIn('name', build)
        self.assertEqual(build['name'], "cirrus virtualenv")
        self.assertIn('env', build)
        self.assertIn('PYTHONPATH', build['env'])
        self.assertEqual(build['env']['PYTHONPATH'], self.repo)

if __name__ == '__main__':
    unittest.main()
