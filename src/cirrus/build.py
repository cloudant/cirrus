#!/usr/bin/env python
"""
_build_

Implements the cirrus build command.

This command:
 - creates a virtualenv in the package
 - pip installs requirements.txt for the package into the venv

"""
import os
import sys
from argparse import ArgumentParser

from cirrus.documentation_utils import build_docs
from cirrus.environment import cirrus_home
from cirrus.configuration import load_configuration, get_pypi_auth
from cirrus.pypirc import PypircFile
from cirrus.logger import get_logger
from invoke import run

LOGGER = get_logger()


def build_parser(argslist):
    """
    _build_parser_

    Set up command line parser for the build command

    : param list argslist: A list of command line arguments
    """
    parser = ArgumentParser(
        description='git cirrus build'
    )
    parser.add_argument('command', nargs='?')
    parser.add_argument(
        '-c',
        '--clean',
        action='store_true',
        help='remove existing virtual environment')

    parser.add_argument(
        '-d',
        '--docs',
        nargs='*',
        help=(
            'generate documentation with Sphinx '
            '(Makefile path must be set in cirrus.conf.'
        )
    )

    parser.add_argument(
        '-u',
        '--upgrade',
        action='store_true',
        default=False,
        help=(
            'Use --upgrade to update the dependencies '
            'in the package requirements'
        )
    )
    parser.add_argument(
        '--extra-requirements',
        nargs="+",
        type=str,
        dest='extras',
        help='extra requirements files to install'
    )
    parser.add_argument(
        '--no-setup-develop',
        dest='nosetupdevelop',
        default=False,
        action='store_true'
    )
    parser.add_argument(
        '--freeze',
        action='store_true',
        help='ignores sub-dependency pins, and then updates them'
    )
    opts = parser.parse_args(argslist)
    return opts


def execute_build(opts):
    """
    _execute_build_

    Execute the build in the current package context.

    - reads the config to check for custom build parameters
      - defaults to ./venv for virtualenv
      - defaults to ./requirements.txt for reqs
    - removes existing virtualenv if clean flag is set
    - builds the virtualenv
    - pip installs the requirements into it

    : param argparse.Namspace opts: A Namespace of build options
    """
    working_dir = os.getcwd()
    config = load_configuration()
    build_params = config.get('build', {})

    # we have custom build controls in the cirrus.conf
    reqs_name = build_params.get('requirements_file', 'requirements.txt')
    activate_cmd = '. ./{}/bin/activate'.format(config.venv_name())
    if opts.freeze:
        requirements = Requirements(
            reqs_name,
            'requirements-sub.txt',
            activate_cmd
        )
        requirements.parse_out_sub_dependencies()
    extra_reqs = build_params.get('extra_requirements', '')
    extra_reqs = [x.strip() for x in extra_reqs.split(',') if x.strip()]
    if opts.extras:
        extra_reqs.extend(opts.extras)
        extra_reqs = set(extra_reqs)  # dedupe

    venv_path = os.path.join(working_dir, config.venv_name())
    venv_bin_path = os.path.join(venv_path, 'bin', 'python')
    venv_command = os.path.join(
        cirrus_home(),
        'venv',
        'bin',
        'virtualenv')

    # remove existing virtual env if building clean
    if opts.clean and os.path.exists(venv_path):
        cmd = "rm -rf {0}".format(venv_path)
        LOGGER.info("Removing existing virtualenv: {0}".format(venv_path))
        run(cmd)

    if not os.path.exists(venv_bin_path):
        cmd = "{0} {1}".format(venv_command, venv_path)
        LOGGER.info("Bootstrapping virtualenv: {0}".format(venv_path))
        run(cmd)

    # custom pypi server
    pypi_server = config.pypi_url()
    pip_options = config.pip_options()
    pip_command_base = None
    if pypi_server is not None:

        pypirc = PypircFile()
        if pypi_server in pypirc.index_servers:
            pypi_url = pypirc.get_pypi_url(pypi_server)
        else:
            pypi_conf = get_pypi_auth()
            pypi_url = (
                "https://{pypi_username}:{pypi_token}@{pypi_server}/simple"
            ).format(
                pypi_token=pypi_conf['token'],
                pypi_username=pypi_conf['username'],
                pypi_server=pypi_server
            )

        pip_command_base = (
            '{0}/bin/pip install -i {1}'
        ).format(venv_path, pypi_url)

        if opts.upgrade:
            cmd = (
                '{0} --upgrade '
                '-r {1}'
            ).format(pip_command_base, reqs_name)
        else:
            cmd = (
                '{0} '
                '-r {1}'
            ).format(pip_command_base, reqs_name)

    else:
        pip_command_base = '{0}/bin/pip install'.format(venv_path)
        # no pypi server
        if opts.upgrade:
            cmd = '{0} --upgrade -r {1}'.format(pip_command_base, reqs_name)
        else:
            cmd = '{0} -r {1}'.format(pip_command_base, reqs_name)

    if pip_options:
        cmd += " {} ".format(pip_options)

    try:
        run(cmd)
    except OSError as ex:
        msg = (
            "Error running pip install command during build\n"
            "Error was {0}\n"
            "Running command: {1}\n"
            "Working Dir: {2}\n"
            "Virtualenv: {3}\n"
            "Requirements: {4}\n"
        ).format(ex, cmd, working_dir, venv_path, reqs_name)
        LOGGER.error(msg)
        sys.exit(1)

    if extra_reqs:
        if opts.upgrade:
            commands = [
                "{0} --upgrade -r {1}".format(pip_command_base, reqfile)
                for reqfile in extra_reqs
            ]
        else:
            commands = [
                "{0} -r {1}".format(pip_command_base, reqfile)
                for reqfile in extra_reqs
            ]

        for cmd in commands:
            LOGGER.info("Installing extra requirements... {}".format(cmd))
            try:
                run(cmd)
            except OSError as ex:
                msg = (
                    "Error running pip install command extra "
                    "requirements install: {}\n{}"
                ).format(reqfile, ex)
                LOGGER.error(msg)
                sys.exit(1)

    # setup for development
    if opts.nosetupdevelop:
        msg = "skipping python setup.py develop..."
        LOGGER.info(msg)
    else:
        LOGGER.info('running python setup.py develop...')
        run(
            '{} && python setup.py develop'.format(
                activate_cmd
            )
        )

    if opts.freeze:
        requirements.update_sub_dependencies()
        requirements.restore_sub_dependencies()


def main():
    """
    _main_

    Execute build command
    """
    opts = build_parser(sys.argv)
    execute_build(opts)

    if opts.docs is not None:
        build_docs(make_opts=opts.docs)


class Requirements:
    """
    Modify requirments files
    """
    def __init__(self, dep_filename, sub_dep_filename, activate_cmd):
        """
        :param str dep_filename: name of the requirements file containing
            direct dependencies
        :param str sub_dep_filename: name of the requirements file containing
            sub-dependencies
        :param str activate_cmd: shell command used to activate a virtualenv
        """
        self.direct_filename = dep_filename
        self.sub_filename = sub_dep_filename
        self.direct_dependencies = None
        self.sub_dependencies = None
        self.activate_cmd = activate_cmd

    def parse_out_sub_dependencies(self):
        """
        Modifies the direct requirements file to exclude sub-dependencies,
        noop if no sub-dependencies specified
        """
        with open(self.direct_filename, 'r') as requirements_file:
            direct = requirements_file.read().strip().split('\n')
            del direct[0]
        with open(self.direct_filename, 'w+') as new_req_file:
            direct = sorted(direct)
            new_req_file.write('\n'.join(direct))

        self.direct_dependencies = set(direct)

    def update_sub_dependencies(self):
        """
        Re-pins sub-dependencies after getting the latest acceptable versions
        """
        run('{} && pip freeze > {}'.format(
            self.activate_cmd, self.sub_filename
        ))
        with open(self.sub_filename, 'r') as sub_req_file:
            sub = sub_req_file.read().strip().split('\n')
            sub = [item for item in sub if not item.startswith('-e')]
            self.sub_dependencies = set(sub)
        new_sub_req = self.sub_dependencies - self.direct_dependencies
        with open(self.sub_filename, 'w+') as sub_req_file:
            new_sub_req = sorted(list(new_sub_req))
            sub_req_file.write('\n'.join(new_sub_req))

    def restore_sub_dependencies(self):
        """
        Modifies requirments file to include sub-dependencies
        """
        with open(self.direct_filename, 'r+') as requirements_file:
            contents = requirements_file.read()
            requirements_file.seek(0)
            requirements_file.write(
                '-r {}\n'.format(self.sub_filename) + contents
            )


if __name__ == '__main__':
    main()
