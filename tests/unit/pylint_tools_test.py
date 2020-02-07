'''
pylint_tools tests
'''
from unittest import TestCase, mock

from pep8 import StyleGuide

from cirrus.pylint_tools import pep8_file
from cirrus.pylint_tools import pyflakes_file
from cirrus.pylint_tools import pylint_file


class PylintToolsTest(TestCase):

    def setUp(self):
        self.filenames = ['hello.py', 'goodbye.py']
        patch_run = mock.patch('cirrus.pylint_tools.run')
        self.mock_run = patch_run.start()
        patch_pep8 = mock.patch('cirrus.pylint_tools.pep8')
        self.mock_pep8 = patch_pep8.start()

    def tearDown(self):
        mock.patch.stopall()

    def test_pylint_file(self):
        results = pylint_file(self.filenames)
        self.mock_run.assert_called_with(
            'pylint {}'.format(' '.join(self.filenames)),
            hide=True,
            warn=True
        )
        self.assertEqual(results[0], self.filenames)

    def test_pyflakes_file(self):
        results = pyflakes_file(self.filenames)
        self.mock_run.assert_called_with(
            'pyflakes {}'.format(' '.join(self.filenames)),
            hide=True,
            warn=True
        )
        self.assertEqual(results[0], self.filenames)

    def test_pep8_file(self):
        mock_style_guide = mock.Mock(spec=StyleGuide)
        self.mock_pep8.StyleGuide.return_value = mock_style_guide

        results = pep8_file(self.filenames)
        mock_style_guide.check_files.assert_called_with(self.filenames)
        self.assertFalse(
            mock_style_guide.check_files.return_value.print_statistics.called
        )
        self.assertEqual(results[0], self.filenames)

    def test_pep8_file_verbose(self):
        mock_style_guide = mock.Mock(spec=StyleGuide)
        self.mock_pep8.StyleGuide.return_value = mock_style_guide

        results = pep8_file(self.filenames, verbose=True)
        mock_style_guide.check_files.assert_called_with(self.filenames)
        self.assertTrue(
            mock_style_guide.check_files.return_value.print_statistics.called
        )
        self.assertEqual(results[0], self.filenames)
