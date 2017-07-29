#!/bin/sh

date > /log/python_stderr.log
python /usr/bin/main.py udpout:127.0.0.1:14560 udpout:127.0.0.1:14550 >> /log/python_stderr.log 2>&1
