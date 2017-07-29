#!/usr/bin/env python

import sys, csv

BUCKETS = 32

def do_it(f, prefix):
    with open(f, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        readings = [float(r[2]) for r in reader if r[0].startswith(prefix)]

        interval = len(readings) / BUCKETS
        lut = [readings[i * interval] for i in range(BUCKETS)]

        for v in lut:
            print "    MillivoltsToAdc(%d)," % int(v * 1000)

if len(sys.argv) < 3:
    print "usage: curve-buddy.py curve-data.csv prefix"
    sys.exit(1)

do_it(sys.argv[1], sys.argv[2])
