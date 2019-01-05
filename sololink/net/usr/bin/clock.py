#!/usr/bin/env python

# Python interface into the posix clock functions
# clock_gettime(), clock_settime()
#
# Motivation is to get access to CLOCK_MONOTONIC, so flight code can not care
# about jumps in system time (in which case CLOCK_REALTIME and python's
# datetime jump).

import ctypes
import os

CLOCK_REALTIME              = 0
CLOCK_MONOTONIC             = 1
CLOCK_PROCESS_CPUTIME_ID    = 2
CLOCK_THREAD_CPUTIME_ID     = 3
CLOCK_MONOTONIC_RAW         = 4
CLOCK_REALTIME_COARSE       = 5
CLOCK_MONOTONIC_COARSE      = 6
CLOCK_BOOTTIME              = 7
CLOCK_REALTIME_ALARM        = 8
CLOCK_BOOTTIME_ALARM        = 9

class timespec(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_long),
        ("tv_nsec", ctypes.c_long)
    ]

librt = ctypes.CDLL('librt.so.1', use_errno=True)

clock_gettime = librt.clock_gettime
clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]

clock_settime = librt.clock_settime
clock_settime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]

def gettime(clock_id):
    t = timespec()
    if clock_gettime(clock_id, ctypes.pointer(t)) != 0:
        errno_ = ctypes.get_errno()
        raise OSError(errno_, os.strerror(errno_))
    return t

def gettime_us(clock_id):
    t = gettime(clock_id)
    return long(t.tv_sec * 1000000 + (t.tv_nsec + 500) / 1000)

def settime(clock_id, t):
    if clock_settime(clock_id, ctypes.pointer(t)) != 0:
        errno_ = ctypes.get_errno()
        raise OSError(errno_, os.strerror(errno_))

def settime_us(clock_id, us):
    t = timespec(us/1000000, (us%1000000) * 1000)
    if clock_settime(clock_id, ctypes.pointer(t)) != 0:
        errno_ = ctypes.get_errno()
        raise OSError(errno_, os.strerror(errno_))

def test(do_set):
    rt = gettime(CLOCK_REALTIME)
    print "REALTIME:  %10d.%09d" % (rt.tv_sec, rt.tv_nsec)
    mt = gettime(CLOCK_MONOTONIC)
    print "MONOTONIC: %10d.%09d" % (mt.tv_sec, mt.tv_nsec)
    if do_set:
        # WARNING: this sets the time to zero (1/1/1970)
        print "set time..."
        os.system("date --set=\"@0\"")
        rt = gettime(CLOCK_REALTIME)
        print "REALTIME:  %10d.%09d" % (rt.tv_sec, rt.tv_nsec)
        mt = gettime(CLOCK_MONOTONIC)
        print "MONOTONIC: %10d.%09d" % (mt.tv_sec, mt.tv_nsec)

if __name__ == "__main__":
    test(False) # True will set your system time to zero
