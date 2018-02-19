cirrus
======

python library build, test and devop like things assistant

[![Build Status](https://travis-ci.org/cloudant/cirrus.svg?branch=develop)](https://travis-ci.org/cloudant/cirrus)

Installation Prerequisites
==========================

* Cirrus requires either python/pip/virtualenv or conda and has been tested with python2.7, 3.5 and 3.6 as of Release 0.2.0.
   * Since python3 support and conda support are fairly new, please report any problems as Issues in this project.
* Git tools are heavily used, git is a requirement as cirrus is accessed via git command aliases.

Installation as a user:
=======================

```bash
# replace with your web_password credentials
export CIRRUS_PYPI_URL="https://user:password@pypi.cloudant.com"

curl -O https://raw.githubusercontent.com/cloudant/cirrus/develop/installer.sh
bash installer.sh
```

Installation for Development:
=============================

_Note_: This package uses GitFlow, any development work should be done off the develop branches and
pull requests made against develop, not master.

```bash
git clone https://github.com/cloudant/cirrus.git
cd cirrus
git cirrus build
```

Package Configuration Files:
============================

The per package controls used by cirrus live in a cirrus.conf file in the top level of the repo you use with cirrus.
This file, coupled with the cirrus setup.py template and command line tools dictate the behaviour of the cirrus commands within the package. Details for the cirrus config are in the [Cirrus Configuration Docs](https://github.com/cloudant/cirrus/wiki/CirrusConfiguration)


Cirrus Commands:
================

See the [Cirrus Commands Docs](https://github.com/cloudant/cirrus/wiki#command-reference)

* [git cirrus hello](https://github.com/cloudant/cirrus/wiki/HelloCommand) - Install check and version info
* [git cirrus build](https://github.com/cloudant/cirrus/wiki/BuildCommand) - Create a development environment
* [git cirrus test](https://github.com/cloudant/cirrus/wiki/TestCommand) - Run test suites
* [git cirrus release](https://github.com/cloudant/cirrus/wiki/ReleaseCommand) - Release code and push to pypi
* [git cirrus feature](https://github.com/cloudant/cirrus/wiki/FeatureCommand) - Work on new features
* [git cirrus docker-image](https://github.com/cloudant/cirrus/wiki/DockerImageCommand) - Build and release container images
* [git cirrus selfupdate](https://github.com/cloudant/cirrus/wiki/SelfupdateCommand) - Update cirrus
* [git cirrus qc](https://github.com/cloudant/cirrus/wiki/QCCommand) - Run quality control and code standard tests
* [git cirrus docs](https://github.com/cloudant/cirrus/wiki/DocsCommand) - Build sphinx package docs
* [git cirrus review](https://github.com/cloudant/cirrus/wiki/ReviewCommand) - Helper for GitHub Pull Requests


Troubleshooting
================

**macOS Sierra**: Try the steps below if `git cirrus build` fails during installation of uWSGI because of `ld: file not found: /usr/lib/system/libsystem_symptoms.dylib for architecture x86_64`. Details [here](https://github.com/unbit/uwsgi/issues/1364).
```
brew update
brew unlink libxml2
brew uninstall libxml2
brew install --with-python libxml2
brew link libxml2 --force
```


