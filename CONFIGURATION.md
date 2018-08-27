# Description for cirrus.conf
## package
General package configuration

- `name`: name of the package
- `version`: current version (note that this is updated manually on release)
- `description`: package description
- `organization`: git org
- `version_file`: where to read version from (typically high level `__init__` module)
- `python_versions`: coma separated list of compatible python versions used to validate build artifacts

## gitflow
Config related to gitflow operations

- `develop_branch`: branch prefix used for the main development branch (typically `develop/`)
- `release_branch_prefix`: branch prefix used for release branches (typically `release/`
- `feature_branch_prefix`: branch prefix used for feature branches(typically `feature/`)

## pypi
pypi specific configuration

- `pypi_url`: url of the pypi server

## test-default
`git cirrus test` will run these by default. More suites can be defined and ran using the `--suite` option. Those should be defined as `test-SUITE` where `SUITE` can be any user defined name.

- `where`: name of the directory where the tests from this suite live

## quality
Configuration for quality control and linting checks

- `threshold`: pylint threshold

## doc
Configuration for generating and uploading documentation

- `sphinx_makefile_dir`: location of the Sphinx MAKE file
- `sphinx_doc_dir`: target location to store the generated documents
- `artifact_dir`: target location to store the bundled document artifacts
- `publisher`: build server used to upload documentation

## release
Release specific configuration. This section is primarily used for dealing with branch protection.

- `wait_on_ci`: wait for GH CI status to be success before uploading?
- `wait_on_ci_develop`: wait for GH CI status of the develop branch to be success before uploading?
- `wait_on_ci_master`: wait for GH CI status of the master branch to be success before uploading?
- `wait_on_ci_timeout`: total number of seconds to spend attempting status check
- `wait_on_ci_interval`: number of seconds to wait between status checks
- `github_context_string`: context of the status check
- `update_github_context`: if True, attempt to set the branch state to success
- `push_retry_attempts`: number of attempts to make when retrying a branch push
- `push_retry_cooloff`: number of seconds to wait between branch push attempts