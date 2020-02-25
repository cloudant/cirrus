'''
qc command tests
'''
from unittest import TestCase, mock

from cirrus.quality_control import run_pep8
from cirrus.quality_control import run_pyflakes
from cirrus.quality_control import run_pylint


class QualityControlTest(TestCase):

    def setUp(self):
        """setup mocks"""
        self.patch_config_load = mock.patch(
            'cirrus.quality_control.load_configuration')
        self.mock_config = self.patch_config_load.start()

    def tearDown(self):
        self.patch_config_load.stop()

    def test_run_pylint(self):
        with mock.patch('cirrus.quality_control.pylint_file') as mock_pylint:
            self.mock_config.return_value.quality_threshold.return_value = 0
            mock_pylint.return_value = (['hello.py', 'goodbye.py'], 0)
            run_pylint()
            self.assertTrue(mock_pylint.called)

    def test_run_pyflakes(self):
        with mock.patch(
            'cirrus.quality_control.pyflakes_file') as mock_pyflakes:

            run_pyflakes(False)
            self.assertTrue(mock_pyflakes.called)

    def test_run_pep8(self):
        with mock.patch('cirrus.quality_control.pep8_file') as mock_pep8:
            run_pep8(False)
            self.assertTrue(mock_pep8.called)
