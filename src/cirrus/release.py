#!/usr/bin/env python
"""
Implement git cirrus release command
"""
import os
import sys
import datetime
import itertools
import shutil
from collections import OrderedDict
from invoke import run
import pluggage.registry

import argparse
from argparse import ArgumentParser
from cirrus.configuration import load_configuration
from cirrus.environment import repo_directory
from cirrus.git_tools import build_release_notes
from cirrus.git_tools import has_unstaged_changes
from cirrus.git_tools import branch, checkout_and_pull
from cirrus.git_tools import commit_files, remote_branch_exists
from cirrus.git_tools import get_active_commit_sha, get_active_branch
from cirrus.github_tools import GitHubContext
from cirrus.utils import update_file, update_version
from cirrus.logger import get_logger
from cirrus.plugins.jenkins import JenkinsClient

BUILD_CMD = 'python setup.py bdist_wheel'
BUILD_CMD_TAGGED = "python setup.py egg_info --tag-build '.{}' bdist_wheel"
LOGGER = get_logger()


def highlander(iterable):
    """check only single True value in iterable"""
    # There Can Be Only One!!!
    i = iter(iterable)
    return any(i) and not any(i)


def parse_version(version):
    """
    _parse_version_

    Parse semantic major.minor.micro version string

    :param version: X.Y.Z format version string

    :returns: dictionary containing major, minor, micro versions
    as integers

    """
    split = version.split('.', 2)
    return {
        'major': int(split[0]),
        'minor': int(split[1]),
        'micro': int(split[2]),
    }


def bump_version_field(version, field='major'):
    """
    parse the version and update the major, minor and micro
    version specified by field
    Return the updated version string
    """
    vers_params = parse_version(version)
    vers_params[field] += 1
    if field == 'major':
        vers_params['minor'] = 0
        vers_params['micro'] = 0
    elif field == 'minor':
        vers_params['micro'] = 0

    return "{major}.{minor}.{micro}".format(**vers_params)


def artifact_name(config, tag=None):
    """
    Builds the expected artifact name

    :param Configuration config: cirrus config
    :param str tag: python_tag portion of the name, omitted if None (default)

    :returns: path of the build artifact
    :rtype: str
    """
    if tag is None:
        artifact_name = (
            '{distribution}-{version}-{python_tag}'
            '-{abi_tag}-{platform_tag}.whl'
        ).format(
            distribution=config.package_name(),
            version=config.package_version(),
            python_tag=config.python_versions(),
            abi_tag='none',
            platform_tag='any'
        )
    else:
        artifact_name = (
            '{distribution}-{version}.{tag}-{python_tag}'
            '-{abi_tag}-{platform_tag}.whl'
        ).format(
                distribution=config.package_name(),
                version=config.package_version(),
                tag=tag,
                python_tag=config.python_versions(),
                abi_tag='none',
                platform_tag='any'
        )
    build_artifact = os.path.join(
        os.getcwd(),
        'dist',
        artifact_name
    )
    return build_artifact


parse_to_list = lambda s: [x.strip() for x in s.split(',') if x.strip()]


def release_branch_name(config):
    """
    build expected release branch name from current config

    """
    branch_name = "{0}{1}".format(
        config.gitflow_release_prefix(),
        config.package_version()
    )
    return branch_name


def convert_bool(value):
    """helper to make sure bools are bools"""
    if value in (True, False):
        return value
    if value is None:
        return False
    if str(value).lower() in ('true', '1'):
        return True
    return False


def get_plugin(plugin_name):
    """
    _get_plugin_

    Get the deploy plugin requested from the factory
    """
    factory = pluggage.registry.get_factory(
        'upload',
        load_modules=['cirrus.plugins.uploaders']
    )
    return factory(plugin_name)


def release_config(config, opts):
    """
    _release_config_

    Extract and validate the release config parameters
    from the cirrus config for the package
    """
    release_config_defaults = {
        'wait_on_ci': False,
        'wait_on_ci_develop': False,
        'wait_on_ci_master': False,
        'wait_on_ci_timeout': 600,
        'wait_on_ci_interval': 2,
        'push_retry_attempts': 1,
        'push_retry_cooloff': 0,
        'github_context_string': None,
        'update_github_context': False,
        'develop_github_context_string': None,
        'master_github_context_string': None,
        'update_develop_github_context': False,
        'update_master_github_context': False
    }

    release_config = {}
    if 'release' not in config:
        release_config = release_config_defaults
    else:
        for key, val in release_config_defaults.items():
            release_config[key] = config.get_param('release', key, val)

    release_config['wait_on_ci'] = convert_bool(release_config['wait_on_ci'])
    release_config['wait_on_ci_develop'] = convert_bool(
        release_config['wait_on_ci_develop']
    )
    release_config['wait_on_ci_master'] = convert_bool(
        release_config['wait_on_ci_master']
    )

    if opts.wait_on_ci:
        release_config['wait_on_ci'] = True
    if opts.github_context_string:
        release_config['update_github_context'] = True
        release_config['github_context_string'] = opts.github_context_string

    if opts.github_develop_context_string:
        release_config['update_develop_github_context'] = True
        release_config['github_develop_context_string'] = opts.github_develop_context_string
    if opts.github_master_context_string:
        release_config['update_master_github_context'] = True
        release_config['github_master_context_string'] = opts.github_master_context_string

    # validate argument types
    release_config['wait_on_ci_timeout'] = int(
        release_config['wait_on_ci_timeout']
    )
    release_config['wait_on_ci_interval'] = int(
        release_config['wait_on_ci_interval']
    )
    release_config['update_github_context'] = convert_bool(
        release_config['update_github_context']
    )
    release_config['push_retry_attempts'] = int(
        release_config['push_retry_attempts']
    )
    release_config['push_retry_cooloff'] = int(
        release_config['push_retry_cooloff']
    )

    if release_config['update_github_context']:
        # require context string
        if release_config['github_context_string'] is None:
            msg = "if using update_github_context you must provide a github_context_string"
            raise RuntimeError(msg)
        release_config['github_context_string'] = parse_to_list(
            release_config['github_context_string']
        )
    if release_config['update_develop_github_context']:
        # require context string                                                                                                                                                        if release_config['github_develop_context_string'] is None:
        if release_config['github_develop_context_string'] is None:
            msg = "if using update_develop_github_context you must provide a github_context_string"
            raise RuntimeError(msg)
        release_config['github_develop_context_string'] = parse_to_list(
            release_config['github_develop_context_string']
        )
    if release_config['update_master_github_context']:
        # require context string
        if release_config['github_master_context_string'] is None:
            msg = "if using update_master_github_context you must provide a github_master_context_string"
            raise RuntimeError(msg)
        release_config['github_master_context_string'] = parse_to_list(
            release_config['github_master_context_string']
        )
    return release_config


def build_parser(argslist):
    """
    _build_parser_

    Set up command line parser for the release command

    """
    parser = ArgumentParser(
        description='git cirrus release command'
    )
    parser.add_argument('command', nargs='?')

    subparsers = parser.add_subparsers(dest='command')
    new_command = subparsers.add_parser('new')
    new_command.add_argument(
        '--micro',
        action='store_true',
        dest='micro'
    )
    new_command.add_argument(
        '--minor',
        action='store_true',
        dest='minor'
    )
    new_command.add_argument(
        '--major',
        action='store_true',
        dest='major'
    )
    new_command.add_argument(
        '--bump',
        nargs='+',
        help='package versions (pkg==0.0.0) to update in requirements.txt'
    )

    # borrow --micro/minor/major options from "new" command.
    subparsers.add_parser('trigger', parents=[new_command], add_help=False)
    subparsers.add_parser('build')

    merge_command = subparsers.add_parser('merge')
    merge_command.add_argument(
        '--wait-on-ci',
        action='store_true',
        dest='wait_on_ci',
        default=False,
        help='Wait for GH CI status to be success before uploading'
    )
    merge_command.add_argument(
        '--context-string',
        default=None,
        dest='github_context_string',
        help='Update the github context string provided when pushed'
    )

    merge_command.add_argument(
        '--develop-context-string',
        default=None,
        dest='github_develop_context_string',
        help='Update the github context string for develop branch provided when pushed'
    )
    merge_command.add_argument(
        '--master-context-string',
        default=None,
        dest='github_master_context_string',
        help='Update the github context string for master branch provided when pushed'
    )

    merge_command.add_argument(
        '--cleanup',
        action='store_true',
        dest='cleanup',
        help='Clean up release branch after merging'
    )
    merge_command.add_argument(
        '--skip-master',
        action='store_true',
        dest='skip_master',
        default=False,
        help='Skip the master merge and push'
    )
    merge_command.add_argument(
        '--skip-develop',
        action='store_true',
        dest='skip_develop',
        default=False,
        help='Skip the develop merge and push'
    )
    merge_command.add_argument(
        '--log-status',
        action='store_true',
        dest='log_status',
        default=False,
        help='log all status values for branches during command'
    )

    build_command = subparsers.add_parser('build')
    build_command.add_argument(
        '--dev',
        action='store_true',
        help='builds a git sha tagged pre-release'
    )

    build_and_upload_command = subparsers.add_parser('build_and_upload')
    build_and_upload_command.add_argument(
        '--dev',
        action='store_true',
        help='builds and upload a git sha tagged pre-release'
    )

    upload_command = subparsers.add_parser('upload')
    upload_command.add_argument(
        '--test',
        action='store_true',
        dest='test',
        help='test only, do not actually push or upload'
    )
    upload_command.add_argument(
        '--plugin',
        dest='plugin',
        required=True,
        help='Uploader plugin to use'
    )
    upload_command.add_argument(
        '--pypi-url',
        action='store',
        dest='pypi_url',
        help='upload to specified pypi url'
    )
    upload_command.add_argument(
        '--pypi-sudo',
        action='store_true',
        dest='pypi_sudo',
        help='use sudo to upload build artifact to pypi'
    )
    upload_command.add_argument(
        '--no-pypi-sudo',
        action='store_false',
        dest='pypi_sudo',
        help='do not use sudo to upload build artifact to pypi'
    )
    upload_command.add_argument(
        'target',
        nargs='?',
        type=str,
        default=None,
        help='Optional file path of the tarball to be uploaded'
    )
    upload_command.set_defaults(pypi_sudo=True)

    opts = parser.parse_args(argslist)
    return opts


def get_release_version(opts):
    fields = ['major', 'minor', 'micro']
    mask = [opts.major, opts.minor, opts.micro]
    field = [x for x in itertools.compress(fields, mask)][0]
    return field


def new_release(opts):
    """
    _new_release_

    - Create a new release branch in the local repo
    - Edit the conf to bump the version
    - Edit the history file with release notes

    """
    LOGGER.info("Creating new release...")
    config = load_configuration()

    if not highlander([opts.major, opts.minor, opts.micro]):
        msg = "Can only specify one of --major, --minor or --micro"
        LOGGER.error(msg)
        raise RuntimeError(msg)

    current_version = config.package_version()

    # version bump:
    field = get_release_version(opts)
    new_version = bump_version_field(current_version, field)

    # release branch
    branch_name = "{0}{1}".format(
        config.gitflow_release_prefix(),
        new_version
    )
    LOGGER.info('release branch is {0}'.format(branch_name))

    # need to be on the latest develop
    repo_dir = repo_directory()
    # make sure the branch doesnt already exist on remote
    if remote_branch_exists(repo_dir, branch_name):
        msg = (
            "Error: branch {} already exists on the remote repo "
            "Please clean up that branch before proceeding"
            ).format(branch_name)
        LOGGER.error(msg)
        raise RuntimeError(msg)

    # make sure repo is clean
    if has_unstaged_changes(repo_dir):
        msg = (
            "Error: Unstaged changes are present on the branch "
            "Please commit them or clean up before proceeding"
        )
        LOGGER.error(msg)
        raise RuntimeError(msg)

    main_branch = config.gitflow_branch_name()
    checkout_and_pull(repo_dir, main_branch)

    # create release branch
    branch(repo_dir, branch_name, main_branch)

    # update cirrus conf
    config.update_package_version(new_version)
    changes = ['cirrus.conf']

    if opts.bump:
        for pkg in opts.bump:
            if '==' not in pkg:
                msg = 'Malformed version expression.  Please use "pkg==0.0.0"'
                LOGGER.error(msg)
                raise RuntimeError(msg)
        try:
            update_requirements('requirements.txt', opts.bump)
            changes.append('requirements.txt')
        except Exception as ex:
            # halt on any problem updating requirements
            LOGGER.exception('Failed to update requirements.txt -- {}'.format(ex))
            raise RuntimeError(ex)

    # update release notes file
    relnotes_file, relnotes_sentinel = config.release_notes()
    if (relnotes_file is not None) and (relnotes_sentinel is not None):
        LOGGER.info('Updating release notes in {0}'.format(relnotes_file))
        relnotes = "Release: {0} Created: {1}\n".format(
            new_version,
            datetime.datetime.utcnow().isoformat()
        )
        relnotes += build_release_notes(
            repo_dir,
            current_version,
            config.release_notes_format()
        )
        update_file(relnotes_file, relnotes_sentinel, relnotes)
        changes.append(relnotes_file)

    # update __version__ or equivalent
    version_file, version_attr = config.version_file()
    if version_file is not None:
        LOGGER.info('Updating {0} attribute in {1}'.format(version_file, version_attr))
        update_version(version_file, new_version, version_attr)
        changes.append(version_file)

    # update files changed
    msg = "cirrus release: new release created for {0}".format(branch_name)
    LOGGER.info('Committing files: {0}'.format(','.join(changes)))
    LOGGER.info(msg)
    commit_files(repo_dir, msg, *changes)
    return (new_version, field)


def trigger_release(opts):
    """
    _trigger_release_

    Alias for "git cirrus release new --micro/minor/major.
    - Run the "release new" command
    - Capture the new version string
    - Pass new version number to external build server

    Requires the following sections and values in cirrus.conf:

    [build-server]
    name = jenkins

    [jenkins]
    url = http://localhost:8080
    job = default
    """
    config = load_configuration()

    try:
        build_server = config['build-server']['name']
        build_server_config = config[build_server]
    except KeyError:
        msg = (
            '[build-server] section is incomplete or missing from cirrus.conf. '
            'Please see below for an example.\n'
            '\n [build-server]'
            '\n name = jenkins'
            '\n [jenkins]'
            '\n url = http://localhost:8080'
            '\n job = default'
            )
        raise RuntimeError(msg)

    new_version, release_level = new_release(opts)

    if build_server == 'jenkins':
        _trigger_jenkins_release(build_server_config,
                                 new_version,
                                 release_level)


def _trigger_jenkins_release(config, new_version, level):
    """
    _trigger_jenkins_release_

    Performs jenkins specific steps for launching a build job
    """
    client = JenkinsClient(config['url'])
    build_params = {
        'LEVEL': level,
        'VERSION': new_version,
    }

    response = client.start_job(config['job'], build_params)

    if response.status_code != 201:
        LOGGER.error(response.text)
        raise RuntimeError('Jenkins HTTP API returned code {}'.format(response.status_code))


def upload_release(opts):
    raise RuntimeError('Command no longer supported. Use build_and_upload')


def merge_release(opts):
    """
    _merge_release_

    Merge a release branch git flow style into master and develop
    branches (or those configured for this package) and tag
    master.

    """
    config = load_configuration()
    rel_conf = release_config(config, opts)
    repo_dir = os.getcwd()
    tag = config.package_version()
    master = config.gitflow_master_name()
    develop = config.gitflow_branch_name()

    with GitHubContext(repo_dir) as ghc:

        release_branch = ghc.active_branch_name
        expected_branch = release_branch_name(config)
        if release_branch != expected_branch:
            msg = (
                "Not on the expected release branch according "
                "to cirrus.conf\n Expected:{0} but on {1}"
            ).format(expected_branch, release_branch)
            LOGGER.error(msg)
            raise RuntimeError(msg)

        # merge release branch into master
        LOGGER.info("Tagging and pushing {0}".format(tag))
        if opts.skip_master:
            LOGGER.info('Skipping merging to {}'.format(master))
        if opts.skip_develop:
            LOGGER.info('Skipping merging to {}'.format(develop))

        if opts.log_status:
            ghc.log_branch_status(master)
        if not opts.skip_master:
            sha = ghc.repo.head.ref.commit.hexsha

            if rel_conf['wait_on_ci']:
                #
                # wait on release branch CI success
                #
                LOGGER.info("Waiting on CI build for {0}".format(release_branch))
                ghc.wait_on_gh_status(
                    sha,
                    timeout=rel_conf['wait_on_ci_timeout'],
                    interval=rel_conf['wait_on_ci_interval']
                )

            LOGGER.info("Merging {} into {}".format(release_branch, master))
            ghc.pull_branch(master)
            ghc.merge_branch(release_branch)
            sha = ghc.repo.head.ref.commit.hexsha


            if rel_conf['wait_on_ci_master']:
                #
                # wait on release branch CI success
                #
                LOGGER.info("Waiting on CI build for {0}".format(master))
                ghc.wait_on_gh_status(
                    sha,
                    timeout=rel_conf['wait_on_ci_timeout'],
                    interval=rel_conf['wait_on_ci_interval']
                )
            if rel_conf['update_github_context']:
                for ctx in rel_conf['github_context_string']:
                    LOGGER.info("Setting {} for {}".format(
                        ctx,
                        sha)
                    )
                    ghc.set_branch_state(
                        'success',
                        ctx,
                        branch=sha
                    )

            if rel_conf['update_master_github_context']:
                for ctx in rel_conf['github_master_context_string']:
                    LOGGER.info("Setting {} for {}".format(
                        ctx,
                        sha)
                    )
                    ghc.set_branch_state(
                        'success',
                        ctx,
                        branch=sha
                    )
            ghc.push_branch_with_retry(
                attempts=rel_conf['push_retry_attempts'],
                cooloff=rel_conf['push_retry_cooloff']
            )
            LOGGER.info("Tagging {} as {}".format(master, tag))
            ghc.tag_release(tag, master)

        LOGGER.info("Merging {} into {}".format(release_branch, develop))
        if opts.log_status:
            ghc.log_branch_status(develop)
        if not opts.skip_develop:
            ghc.pull_branch(develop)
            ghc.merge_branch(release_branch)
            sha = ghc.repo.head.ref.commit.hexsha

            if rel_conf['wait_on_ci_develop']:
                #
                # wait on release branch CI success
                #
                LOGGER.info("Waiting on CI build for {0}".format(develop))
                ghc.wait_on_gh_status(
                    sha,
                    timeout=rel_conf['wait_on_ci_timeout'],
                    interval=rel_conf['wait_on_ci_interval']
                )
            if rel_conf['update_github_context']:
                for ctx in rel_conf['github_context_string']:
                    LOGGER.info("Setting {} for {}".format(
                        ctx,
                        sha)
                    )
                    ghc.set_branch_state(
                        'success',
                        ctx,
                        branch=sha
                    )

            if rel_conf['update_develop_github_context']:
                for ctx in rel_conf['github_develop_context_string']:
                    LOGGER.info("Setting {} for {}".format(
                        ctx,
                        sha)
                    )
                    ghc.set_branch_state(
                        'success',
                        ctx,
                        branch=sha
                    )
            ghc.push_branch_with_retry(
                attempts=rel_conf['push_retry_attempts'],
                cooloff=rel_conf['push_retry_cooloff']
            )
        if opts.cleanup:
            ghc.delete_branch(release_branch)


def build_release(opts):
    """
    Runs "python setup.py bdist_wheel" to create the release artifact
    """
    cmd = BUILD_CMD
    tag = None
    if opts.dev:
        tag = get_active_commit_sha('.')
        cmd = BUILD_CMD_TAGGED.format(tag)

    LOGGER.info("Building release...")
    config = load_configuration()
    run(cmd)
    build_artifact = artifact_name(config, tag=tag)
    if not os.path.exists(build_artifact):
        msg = "Expected build artifact: {0} Not Found".format(build_artifact)
        LOGGER.error(msg)
        raise RuntimeError(msg)
    LOGGER.info("Release artifact created: {0}".format(build_artifact))
    return build_artifact


def build_and_upload(opts):
    """
    Runs 'python setup.py egg_info bdist_wheel upload -r local'
    to build and upload. If 'dev' opts is provided, the setup.py command will
    be ran with a '--tag-build' option which appends the current git sha to the
    end of the release number (MAJOR.MINOR.MICRO.SHA).
    """
    # delete any existing build directory if it exists
    if os.path.isdir('build'):
        shutil.rmtree('build')

    if opts.dev:
        active_sha = get_active_commit_sha('.')
        tag_option = '--tag-build ".{}"'.format(active_sha)
    else:
        # check that the active branch is a release branch, fail out with
        # message if not
        if not get_active_branch('.').name.startswith('release'):
            msg = (
                'Must be on a release branch to make a release. If you '
                'intended to make a prerelease, re-run this command with the '
                '--dev option'
            )
            raise RuntimeError(msg)
        tag_option = ''
    LOGGER.info("Building and uploading release...")
    config = load_configuration()
    working_dir = os.getcwd()
    venv_py_path = os.path.join(
        working_dir,
        config.venv_name(),
        'bin',
        'python'
    )
    cmd = '{} setup.py egg_info {} bdist_wheel upload -r local'.format(
        venv_py_path,
        tag_option
    )
    result = run(cmd, hide='stdout', echo=True)
    try:
        submit_msg = result.stdout.split('\n')[-3]
        print(submit_msg)
    except Exception:
        print('Unable to print submit message')
    if opts.dev:
        release_version = '.'.join((config.package_version(), active_sha))
        run(
            'git tag {} && git push --tags'.format(release_version)
        )
    LOGGER.info("...Build and upload complete")


def update_requirements(path, versions):
    """
    _update_requirements_

    Update requirements.txt with the provided versions list, where each item in
    such a list looks exactly like a version specifier in a requirements.txt
    file.  Items without '==' are ignored.

    Example:
    ['foo==0.0.9', 'bar==1.2']
    """
    LOGGER.info('Updating {}'.format(path))

    with open(path, 'r+') as fh:
        # original requirements.txt in its pristine order
        reqs = OrderedDict(tuple(pkg.split('=='))
                           for pkg in fh.readlines() if '==' in pkg)

        for pkg in versions:
            new_pkg, new_version = pkg.split('==')
            reqs[new_pkg] = '{}\n'.format(new_version)
            LOGGER.info('{}=={}'.format(new_pkg, new_version))

        # overwrite original requirements.txt with updated version
        fh.seek(0)
        fh.writelines(['{}=={}'.format(pkg, version)
                      for pkg, version in reqs.items()])
        fh.truncate()


def main():
    opts = build_parser(sys.argv)
    if opts.command == 'new':
        new_release(opts)

    if opts.command == 'trigger':
        trigger_release(opts)

    if opts.command == 'merge':
        merge_release(opts)

    if opts.command == 'upload':
        upload_release(opts)

    if opts.command == 'build':
        build_release(opts)

    if opts.command == 'build_and_upload':
        build_and_upload(opts)

if __name__ == '__main__':

    main()
