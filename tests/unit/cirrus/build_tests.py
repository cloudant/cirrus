#!/usr/bin/env python
"""
build command test coverage
"""
import os
import tempfile
from unittest import TestCase, mock

from cirrus.build import Requirements, execute_build, build_parser


class BuildParserTests(TestCase):
    """test build_parser"""

    def test_build_parser(self):
        """test parser setup"""
        argv = ['build']
        opts = build_parser(argv)
        self.assertEqual(opts.clean, False)
        self.assertEqual(opts.command, 'build')
        self.assertEqual(opts.docs, None)
        self.assertEqual(opts.extras, None)
        self.assertEqual(opts.nosetupdevelop, False)
        self.assertEqual(opts.upgrade, False)

        argv = ['build', '--no-setup-develop']
        opts = build_parser(argv)
        self.assertTrue(opts.nosetupdevelop)

        argv = [
            'build',
            '--extra-requirements',
            'test-requirements.txt',
            'other-requirements.txt'
        ]
        opts = build_parser(argv)
        self.assertEqual(
            opts.extras,
            ['test-requirements.txt', 'other-requirements.txt']
        )


class BuildCommandTests(TestCase):
    """test coverage for build command code"""
    def setUp(self):
        """set up patchers and mocks"""
        self.conf_patcher = mock.patch('cirrus.build.load_configuration')
        self.local_patcher = mock.patch('cirrus.build.run')
        self.os_path_exists_patcher = mock.patch('cirrus.build.os.path.exists')
        self.os_cwd_patcher = mock.patch('cirrus.build.os.getcwd')
        self.pypi_auth_patcher = mock.patch('cirrus.build.get_pypi_auth')
        self.cirrus_home_patcher = mock.patch('cirrus.build.cirrus_home')
        self.pypirc_patcher = mock.patch('cirrus.build.PypircFile')

        self.build_params = {}
        self.pypi_url_value = None

        self.mock_pypirc_inst = mock.Mock()
        self.mock_pypirc_inst.index_servers = []

        self.mock_load_conf = self.conf_patcher.start()
        self.mock_conf = mock.Mock()
        self.mock_load_conf.return_value = self.mock_conf
        self.mock_conf.get = mock.Mock()
        self.mock_conf.get.return_value = self.build_params
        self.mock_conf.pypi_url = mock.Mock()
        self.mock_conf.pypi_url.return_value = self.pypi_url_value
        self.mock_conf.pip_options = mock.Mock(return_value=None)
        self.mock_conf.venv_name.return_value = 'venv'
        self.mock_local = self.local_patcher.start()
        self.mock_os_exists = self.os_path_exists_patcher.start()
        self.mock_os_exists.return_value = False
        self.mock_pypi_auth = self.pypi_auth_patcher.start()
        self.mock_os_cwd = self.os_cwd_patcher.start()
        self.mock_os_cwd.return_value = 'CWD'
        self.mock_cirrus_home = self.cirrus_home_patcher.start()
        self.mock_cirrus_home.return_value = 'CIRRUS_HOME'
        self.mock_pypirc = self.pypirc_patcher.start()
        self.mock_pypirc.return_value = self.mock_pypirc_inst

        self.mock_pypi_auth.return_value = {
            'username': 'PYPIUSERNAME',
            'ssh_username': 'SSHUSERNAME',
            'ssh_key': 'SSHKEY',
            'token': 'TOKEN'
        }

    def tearDown(self):
        self.conf_patcher.stop()
        self.local_patcher.stop()
        self.os_path_exists_patcher.stop()
        self.pypi_auth_patcher.stop()
        self.os_cwd_patcher.stop()
        self.cirrus_home_patcher.stop()
        self.pypirc_patcher.stop()

    def test_execute_build_default_pypi(self):
        """test execute_build with default pypi settings"""
        opts = mock.Mock()
        opts.clean = False
        opts.upgrade = False
        opts.extras = []
        opts.nosetupdevelop = False
        opts.freeze = False

        execute_build(opts)

        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install -r requirements.txt'),
            mock.call('. ./venv/bin/activate && python setup.py develop')
        ])

    def test_execute_build_pypirc(self):
        """test execute_build with pypirc provided settings"""
        opts = mock.Mock()
        opts.clean = False
        opts.upgrade = False
        opts.extras = []
        opts.nosetupdevelop = False
        opts.freeze = False

        self.mock_conf.pypi_url.return_value = "dev"
        self.mock_pypirc_inst.index_servers = ['dev']
        self.mock_pypirc_inst.get_pypi_url = mock.Mock(return_value="DEVPYPIURL")
        execute_build(opts)

        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install -i DEVPYPIURL -r requirements.txt'),
            mock.call('. ./venv/bin/activate && python setup.py develop')
        ])

    def test_execute_build_default_pypi_pip_options(self):
        """test execute_build with default pypi settings"""
        opts = mock.Mock()
        opts.clean = False
        opts.upgrade = False
        opts.extras = []
        opts.nosetupdevelop = False
        opts.freeze = False
        self.mock_conf.pip_options.return_value = "PIPOPTIONS"
        execute_build(opts)

        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install -r requirements.txt PIPOPTIONS '),
            mock.call('. ./venv/bin/activate && python setup.py develop')
        ])

    def test_execute_build_default_pypi_upgrade(self):
        """test execute_build with default pypi settings and upgrade"""
        opts = mock.Mock()
        opts.clean = False
        opts.upgrade = True
        opts.extras = []
        opts.nosetupdevelop = False
        opts.freeze = False

        execute_build(opts)

        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install --upgrade -r requirements.txt'),
            mock.call('. ./venv/bin/activate && python setup.py develop')
        ])

    def test_execute_build_with_extras(self):
        """test execute build with extra reqs"""
        opts = mock.Mock()
        opts.clean = False
        opts.upgrade = False
        opts.extras = ['test-requirements.txt']
        opts.nosetupdevelop = False
        opts.freeze = False
        execute_build(opts)
        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install -r requirements.txt'),
            mock.call('CWD/venv/bin/pip install -r test-requirements.txt'),
            mock.call('. ./venv/bin/activate && python setup.py develop')
        ])

    def test_execute_build_with_nosetupdevelop(self):
        """test nosetupdevelop option"""
        opts = mock.Mock()
        opts.clean = False
        opts.extras = []
        opts.upgrade = False
        opts.nosetupdevelop = True
        opts.freeze = False

        execute_build(opts)
        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install -r requirements.txt')
        ])

    def test_execute_build_with_pypi(self):
        """test execute build with pypi opts"""
        opts = mock.Mock()
        opts.clean = False
        opts.extras = []
        opts.upgrade = False
        opts.nosetupdevelop = False
        opts.freeze = False
        self.mock_conf.pypi_url.return_value = "PYPIURL"

        execute_build(opts)

        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install -i https://PYPIUSERNAME:TOKEN@PYPIURL/simple -r requirements.txt'),
            mock.call('. ./venv/bin/activate && python setup.py develop')

        ])

    def test_execute_build_with_pypi_upgrade(self):
        """test execute build with pypi opts and upgrade"""
        opts = mock.Mock()
        opts.clean = False
        opts.extras = []
        opts.nosetupdevelop = False
        opts.upgrade = True
        opts.freeze = False
        self.mock_conf.pypi_url.return_value = "PYPIURL"

        execute_build(opts)

        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install -i https://PYPIUSERNAME:TOKEN@PYPIURL/simple --upgrade -r requirements.txt'),
            mock.call('. ./venv/bin/activate && python setup.py develop')
        ])

    @mock.patch('cirrus.build.Requirements', spec=Requirements)
    def test_execute_build_freeze(self, mock_requirements):
        """test execute_build with default pypi settings"""
        opts = mock.Mock()
        opts.clean = False
        opts.upgrade = False
        opts.extras = []
        opts.nosetupdevelop = False
        opts.freeze = True
        m_requirements = mock_requirements.return_value

        execute_build(opts)

        self.mock_local.assert_has_calls([
            mock.call('CIRRUS_HOME/venv/bin/virtualenv CWD/venv'),
            mock.call('CWD/venv/bin/pip install -r requirements.txt'),
            mock.call('. ./venv/bin/activate && python setup.py develop')
        ])
        mock_requirements.assert_called_once_with(
            'requirements.txt',
            'requirements-sub.txt',
            '. ./venv/bin/activate'
        )
        self.assertTrue(m_requirements.parse_out_sub_dependencies.called)
        self.assertTrue(m_requirements.update_sub_dependencies.called)
        self.assertTrue(m_requirements.restore_sub_dependencies.called)


class RequirementsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requirements_file = tempfile.mkstemp(text=True)[1]
        with open(cls.requirements_file, 'w+') as f:
            f.write(
                '-r test-requirements-sub.txt\n'
                'Doge==0.0.0\n'
                'bar==0.0.0\n'
                'carburetor==16.1.0.e321a26\n'
                'foo==0.0.0\n'
            )
        cls.sub_requirements_file = tempfile.mkstemp(text=True)[1]
        with open(cls.sub_requirements_file, 'w+') as f:
            f.write(
            'baz==0.0.0\n'
            'oof==0.0.0\n'
        )
        cls.requirements = Requirements(
            cls.requirements_file,
            cls.sub_requirements_file,
            '. ./venv/bin/activate'
        )

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.requirements_file)
        os.remove(cls.sub_requirements_file)

    @mock.patch('cirrus.build.run')
    def test_requirements(self, mock_run):
        # Ensures the nested requirments file is removed
        self.requirements.parse_out_sub_dependencies()
        with open(self.requirements_file, 'r') as f:
            req_contents = f.read()
        self.assertEqual(
            'Doge==0.0.0\nbar==0.0.0\ncarburetor==16.1.0.e321a26\nfoo==0.0.0',
            req_contents
        )

        # Ensures sub dependencies get updated
        mock_run.side_effect = self.mock_pick_freeze
        self.requirements.update_sub_dependencies()

        with open(self.sub_requirements_file, 'r') as f:
            new_contents = f.read()
        self.assertEqual('baz==0.0.1\noof==0.1.0', new_contents)

        # Ensures the nested requirements file is restored
        self.requirements.restore_sub_dependencies()
        with open(self.requirements_file, 'r') as f:
            req_contents = f.read()
        sub_required_line = '-r {}\n'.format(self.sub_requirements_file)
        self.assertEqual(
            '{}'
            'Doge==0.0.0\n'
            'bar==0.0.0\n'
            'carburetor==16.1.0.e321a26\n'
            'foo==0.0.0'.format(sub_required_line),
            req_contents
        )

    def mock_pick_freeze(self, *args):
        os.remove(self.sub_requirements_file)
        with open(self.sub_requirements_file, 'w+') as f:
            f.write(
                '-e git+somegiturl'
                'Doge==0.0.0\n'
                'bar==0.0.0\n'
                'baz==0.0.1\n'
                'carburetor==16.1.0.e321a26\n'
                'foo==0.0.0\n'
                'oof==0.1.0'
            )
