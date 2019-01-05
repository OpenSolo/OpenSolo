#!/usr/bin/env python

import datetime
import socket
import input_report_msg

HOST = "10.1.1.1"
PORT = 5021 # stm32.cpp

# messages to print per second
RATE = 1

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print "connecting to", HOST, ":", PORT, "...",
s.connect((HOST, PORT))
print "OK"

next_print_time = datetime.datetime.now()
print_interval = datetime.timedelta(seconds=1.0/RATE)

while True:

    msg = input_report_msg.recv(s)

    now = datetime.datetime.now()

    # msg is a tuple: (msg_id, timestamp, gimbal_y, gimbal_rate, battery)

    if msg is None:
        print "received \"None\""
        break
    elif len(msg) != 5:
        print "received funky message: ", str(msg)
    elif now > next_print_time:
        print "received:", str(msg)
        next_print_time += print_interval

    if input_report_msg.msg_buf_long != 0:
        print "input_report_msg.msg_buf_long=%d!" % input_report_msg.msg_buf_long
        input_report_msg.msg_buf_long = 0

    if input_report_msg.msg_buf_short != 0:
        print "input_report_msg.msg_buf_short=%d!" % input_report_msg.msg_buf_short
        input_report_msg.msg_buf_short = 0
