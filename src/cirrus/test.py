'''
_test_

Command to run available test suites in a package
'''
import sys

from invoke import run
from argparse import ArgumentParser

from cirrus.configuration import load_configuration


def build_parser(argslist):
    """
    _build_parser_

    Set up command line parser for the release command

    """
    parser = ArgumentParser(
        description='git cirrus test command'
    )
    parser.add_argument(
        '--suite',
        help=(
            'test suite configuration to use as defined in the '
            'test-<suite> section of cirrus.conf'
        ),
        default='default'
    )
    parser.add_argument(
        '--mode',
        choices=['nosetests', 'pytest', 'tox'],
        default='pytest',
        help='Choose test runner framework'
    )
    parser.add_argument(
        '--test-options',
        default='',
        dest='options',
        help='Optional args to pass to test runner'
    )

    opts = parser.parse_args(argslist)
    return opts


def nose_run(config, opts):
    """
    Locally activate vitrualenv and run tests via nose
    """
    where = config.test_where(opts.suite)
    run(
        '. ./{0}/bin/activate && nosetests -w {1} {2}'.format(
            config.venv_name(),
            where,
            opts.options
        ),
        warn=True
    )


def pytest_run(config, opts):
    """
    Locally activate virtualenv and run tests with pytest
    """
    testpath = config.test_where(opts.suite)
    command = (
        '. ./{}/bin/activate && pytest {} {}'.format(
            config.venv_name(),
            testpath,
            opts.options
        )
    )
    run(command, pty=True)  # pty preserves pytest colors


def tox_run(config, opts):
    """
    tox test

    activate venv and run tox test suite

    """
    run(
        '. ./{0}/bin/activate && tox {1}'.format(
            config.venv_name(),
            opts.options
        )
    )


def main():
    """
    _main_

    Execute test command
    """
    opts = build_parser(sys.argv[1:])
    config = load_configuration()
    testrunners = {
        'nosetests': nose_run,
        'pytest': pytest_run,
        'tox': tox_run
    }

    try:
        testrunner = testrunners[opts.mode]
    except KeyError as ex:
        # argpase will catch this first, but just in case...
        sys.exit("Invalid selection for --mode: {}".format(ex))

    testrunner(config, opts)
    sys.exit(0)


if __name__ == '__main__':
    main()
