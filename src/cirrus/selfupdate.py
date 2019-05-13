#!/usr/bin/env python
"""
_selfupdate_

Util command for updating the cirrus install itself
Supports getting a spefified branch or tag, or defaults to
looking up the latest release and using that instead.

"""
import sys
import argparse
import arrow
import os
import inspect
import contextlib

from invoke import run

import cirrus
from cirrus.configuration import load_configuration
from cirrus.environment import cirrus_home, virtualenv_home
from cirrus.github_tools import get_releases
from cirrus.git_tools import update_to_branch, update_to_tag
from cirrus.logger import get_logger


LOGGER = get_logger()


@contextlib.contextmanager
def chdir(dirname=None):
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)


def build_parser(argslist):
    """
    _build_parser_

    Set up command line parser for the selfupdate command

    """
    parser = argparse.ArgumentParser(
        description=(
            'git cirrus selfupdate command, '
            'used to update cirrus itself'
            )
    )
    parser.add_argument('command', nargs='?')
    parser.add_argument(
        '--version',
        help='specify a tag to install',
        required=False,
        default='',

    )
    parser.add_argument(
        '--branch',
        help='specify a branch to use',
        required=False,
        default=None,
    )
    parser.add_argument(
        '--legacy-repo',
        help='Use the old, non pip update process',
        required=False,
        dest='legacy_repo',
        action='store_true',
        default=False,
    )

    opts = parser.parse_args(argslist)
    return opts


def find_cirrus_install():
    """
    _find_cirrus_install_

    Use inspect to find root path of install so we
    can cd there and run the cirrus updates in the right location

    The install process will check out the cirrus repo, the cirrus
    module will be in src/cirrus of that dir

    """
    cirrus_mod = os.path.dirname(inspect.getsourcefile(cirrus))
    src_dir = os.path.dirname(cirrus_mod)
    cirrus_dir = os.path.dirname(src_dir)
    return cirrus_dir


def setup_develop(config):
    """
    _setup_develop_

    run local python setup.py develop via fab

    """
    LOGGER.info("running setup.py develop...")
    run(
        'git cirrus build --upgrade'
    )

    run(
        ' . ./{0}/bin/activate && python setup.py develop'.format(
            config.venv_name()
        )
    )
    return


def pip_install(version):
    """pip install the version of cirrus requested"""
    if version:
        version = '=={}'.format(version)
    pip_req = 'cirrus-cli{}'.format(version)
    venv_name = os.path.basename(virtualenv_home())
    LOGGER.info("running pip upgrade...")
    run(
        ' . ./{0}/bin/activate && pip install --upgrade {1}'.format(
            venv_name, pip_req
        )
    )


def legacy_update(opts):
    """update repo installed cirrus"""
    install = find_cirrus_install()
    with chdir(install):
        config = load_configuration()

        if opts.branch and opts.version:
            msg = "Can specify branch -OR- version, not both"
            raise RuntimeError(msg)

        if opts.branch is not None:
            update_to_branch(opts.branch, config)
            setup_develop(config)
            return

        if opts.version is not None:
            tag = opts.version
        else:
            tag = latest_release(config)
            LOGGER.info("Retrieved latest tag: {0}".format(tag))
        update_to_tag(tag, config)
        setup_develop(config)


def pip_update(opts):
    """update pip installed cirrus"""
    install = cirrus_home()
    with chdir(install):
        pip_install(opts.version)


def main():
    """
    Parses command line opts and deduce wether to check out
    a branch or tag, default behaviour is to install latest release found by
    pip
    """
    opts = build_parser(sys.argv)
    if opts.legacy_repo:
        legacy_update(opts)
    else:
        pip_update(opts)
    return

if __name__ == '__main__':
    main()
