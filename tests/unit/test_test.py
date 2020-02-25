'''
test command tests
'''
from unittest import TestCase, mock

from cirrus.test import nose_run
from cirrus.test import tox_run


class TestTest(TestCase):

    def test_tox_test(self):
        """test mox based test call"""
        with mock.patch('cirrus.test.run') as mock_local:
            mock_opts = mock.Mock()
            mock_opts.suite = 'default'
            mock_opts.options = '-o OPTION'
            mock_config = mock.Mock()
            mock_config.venv_name = mock.Mock()
            mock_config.venv_name.return_value = "VENV"

            tox_run(mock_config, mock_opts)
            self.assertTrue(mock_local.called)
            self.assertTrue(mock_config.venv_name.called)
            command = mock_local.call_args[0][0]
            self.assertEqual(command, '. ./VENV/bin/activate && tox -o OPTION')

    def test_nose_test(self):
        """test nose_test call"""
        with mock.patch('cirrus.test.run') as mock_local:
            mock_opts = mock.Mock()
            mock_opts.suite = 'default'
            mock_opts.options = '-o OPTION'
            mock_config = mock.Mock()
            mock_config.venv_name = mock.Mock()
            mock_config.venv_name.return_value = "VENV"
            mock_config.test_where = mock.Mock()
            mock_config.test_where.return_value = "WHERE"

            nose_run(mock_config, mock_opts)
            self.assertTrue(mock_local.called)
            self.assertTrue(mock_config.venv_name.called)
            self.assertTrue(mock_config.test_where.called)
            command = mock_local.call_args[0][0]
            self.assertEqual(command, '. ./VENV/bin/activate && nosetests -w WHERE -o OPTION')


if __name__ == "__main__":
    unittest.main()
