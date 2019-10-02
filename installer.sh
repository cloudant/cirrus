#!/bin/bash

#
# installer for cirrus
# Sets up working dir eg $HOME/.cirrus
# Clones latest stable tag of cirrus into it
# runs setup commands to build venv for cirrus
# installs git alias commands
# gets token for github access & updates .gitconfig

CIRRUS_INSTALL_DIR="${HOME}/.cirrus"
CIRRUS_DEFAULT_USER="${USER}"

# prerequisites are pip and virtualenv
pip --version 2>/dev/null
if [ $? -eq 127 ]; then
    echo "pip binary not found, cannot proceed"
    exit 127
fi

virtualenv --version 2>/dev/null
if [ $? -eq 127 ]; then
    echo "virtualenv binary not found, cannot proceed"
    exit 127
fi

read -p "Installation directory [${CIRRUS_INSTALL_DIR}]: " LOCATION
LOCATION=${LOCATION:-$CIRRUS_INSTALL_DIR}

echo "Installing cirrus in ${LOCATION}..."
mkdir -p ${LOCATION}

echo "Installing cirrus to LOCATION=${LOCATION}" > ${LOCATION}/install.log
cd ${LOCATION}

# bootstrap virtualenv
python -m venv venv
. venv/bin/activate

# Upgrade to the latest pip, otherwise the default 9.x version has trouble 
# with escaped @ characters in pip.conf
pip install -U pip -i https://pypi.python.org/simple

# This depends on a properly configured pip.conf file.
# See https://github.com/cloudant/service_engineering/wiki/Using-JFrog-Artifactory
pip install cirrus-cli${CIRRUS_INSTALL_VERSION} 1>> ${LOCATION}/install.log

export CIRRUS_HOME=${LOCATION}
export VIRTUALENV_HOME=${LOCATION}/venv
selfsetup
