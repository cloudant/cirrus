#!/usr/bin/env python
"""
Utils/helpers for fabric api
"""
from fabric.config import Config
from fabric.connection import Connection


class FabricHelper(Connection):
    """
    Simplified fabric Connection

    Example usage;

    with FabricHelper('pypi.cloudant.com', 'evansde77', '/Users/david/.ssh/id_rsa') as fh:
        fh.run('/bin/date')

    Will run the date command on pypi.cloudant.com as evansde77 using the key file
    specified
    """
    def __init__(self, hostname, username, ssh_key):
        config = Config(key_filename=ssh_key)
        super().__init__(hostname, user=username, config=config)

    def put(self, local, remote, use_sudo=False):
        """
        Adds sudo implementation that was removed in fabric2

        :param bool use_sudo: if True, file is first moved to user's home
            directory and then moved to the remote location
        """
        if use_sudo:
            super().put(local)
            self.sudo('mv {} {}'.format(local, remote))
        else:
            super().put(local, remote)
