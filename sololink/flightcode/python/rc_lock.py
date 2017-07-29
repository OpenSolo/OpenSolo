#!/usr/bin/env python

import errno
import os


# must match RcLock.cpp
ro_lockfile = "/mnt/rootfs.ro/etc/.rc_lock"
tmp_lockfile = "/tmp/.rc_lock"
tmp_unlockfile = "/tmp/.rc_unlock"


def locked():
    if os.path.isfile(tmp_unlockfile):
        return False
    elif os.path.isfile(tmp_lockfile) or \
         os.path.isfile(ro_lockfile):
        return True
    else:
        return False


def lock_version():
    with open(tmp_lockfile, 'a'): # "touch"
        os.utime(tmp_lockfile, None)


def unlock_version():
    try:
        os.unlink(tmp_lockfile)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise e


def unlock_override():
    with open(tmp_unlockfile, 'a'): # "touch"
        os.utime(tmp_unlockfile, None)
