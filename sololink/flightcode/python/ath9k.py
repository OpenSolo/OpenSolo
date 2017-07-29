#!/usr/bin/env python

import re
import sys
import time
#sys.path.append("/usr/bin")
#import clock


# This takes ~20 msec
# (VO):  qnum: 3 qdepth:  0 ampdu-depth:  0 pending:   0 stopped: 0
r = re.compile(\
"\
\((.+)\):\
 +([a-z-]+): +([0-9]+)\
 +([a-z-]+): +([0-9]+)\
 +([a-z-]+): +([0-9]+)\
 +([a-z-]+): +([0-9]+)\
 +([a-z-]+): +([0-9]+)\
")


def get_queues():
    try:
        f = open("/sys/kernel/debug/ieee80211/phy0/ath9k/queues")
    except:
        return None
    s = f.read()
    f.close()
    s = s.splitlines()
    d = { }
    for line in s:
        m = r.match(line)
        v = { }
        v[m.group(2)] = int(m.group(3))
        v[m.group(4)] = int(m.group(5))
        v[m.group(6)] = int(m.group(7))
        v[m.group(8)] = int(m.group(9))
        v[m.group(10)] = int(m.group(11))
        d[m.group(1)] = v
    return d


graph = True

if __name__ == "__main__":
    last = { }
    count = 0
    while True:
        qs = get_queues()
        if graph:
            if count == 0:
                line = ['-'] * 128
                count = 9
            else:
                line = [' '] * 128
                count -= 1
            for c in range(7):
                line[c * 20] = '|'
            for q in qs:
                val = qs[q]['pending']
                if val > 127:
                    val = 127
                #print q, qs[q], str(qs[q]), str(qs[q])[1]
                line[val] = q[1]
            print "".join(line)
        else:
            for q in qs:
                # if too many packets pending twice in a row, print message
                if q in last and last[q] > 120 and qs[q]['pending'] > 120:
                    print q, last[q], qs[q]['pending']
                last[q] = qs[q]['pending']
        time.sleep(0.1)
