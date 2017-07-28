#!/usr/bin/env python

import mmap
import posix_ipc
import rc_pkt

# see rc_remap_sample.py for usage

# must match rc_ipc.c
shm_name = "/rc_shm"
sem_name = "/rc_sem"

# must match sizeof(struct rc_pkt)
shm_size = rc_pkt.LENGTH

shm = None
sem = None
shm_file = None


def attach():
    global shm
    global sem
    global shm_file
    # create/attach shared memory
    try:
        shm = posix_ipc.SharedMemory(shm_name, posix_ipc.O_CREAT, size=shm_size)
    except:
        print "rc_shm.attach: ERROR creating shared memory", shm_name
        return False
    shm_file = mmap.mmap(shm.fd, shm.size)
    shm.close_fd()
    # create/attach semaphore
    try:
        sem = posix_ipc.Semaphore(sem_name, posix_ipc.O_CREAT)
    except:
        print "rc_shm.attach: ERROR creating semaphore", sem_name
        return False
    return True


# pkt is a tuple (timestamp, sequence, channels[])
def put(pkt):
    if shm_file is None or sem is None:
        #print "rc_shm.put: must attach first"
        return False
    # convert from tuple to string
    p = rc_pkt.pack(pkt)
    if p is None:
        return False
    # write to shared memory
    sem.acquire()
    shm_file.seek(0)
    shm_file.write(p)
    sem.release()
    return True


# return pkt or None
# pkt is returned as a tuple (timestamp, sequence, channels[])
def get():
    if shm_file is None or sem is None:
        #print "rc_shm.get: must attach first"
        return False
    sem.acquire()
    shm_file.seek(0)
    s = shm_file.read(shm_size)
    sem.release()
    return rc_pkt.unpack(s)


def detach():
    global shm
    global sem
    global shm_file
    if shm_file:
        shm_file.close()
    shm_file = None
    shm = None
    sem = None
