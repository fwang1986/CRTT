Overview
============

Info:
    fileupdate.py is used to compare the local file and remote file, update the remote file if not exist or the result of md5sum is not same.
    This software use ssh tool connect to synchronize to remote.

Notice:
    (1) Before you use this project, make sure that pexpect is installed. The method of installing pexpect is as following:
       1. cd pexpect-3.3
       2. python setup.py build
       3. python setup.py install

Conf:
    The config/conf.ini file is used to configure the local, remote and log information.
    The attributions of config/conf.ini are configured as following:
       1. [local]
         path  ---  The local path you want to synchronize to remote.
       2. [remote]
         path  ---  The remote path you want to synchronize with local path.
         user  ---  remote username.
         ip    ---  remote ip.
         passwd ---  remote passwd of the user.
       3. [log]
         path  ---  log path
         name  ---  log name
