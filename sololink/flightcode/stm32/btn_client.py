#!/usr/bin/env python

import socket
import struct
import threading
from sololink import btn_msg

HOST = "10.1.1.1"
PORT = 5016

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print "connecting to", HOST, ":", PORT, "...",
s.connect((HOST, PORT))
print "OK"

def in_thread(s):
    while True:
        msg = btn_msg.recv(s)
        if msg is None:
            print "received \"None\""
            break
        elif len(msg) != 4:
            print "received funky message: ", str(msg)
        else:
            print "received:", msg[0], \
                  btn_msg.ButtonName[msg[1]], \
                  btn_msg.EventName[msg[2]], msg[3]
        if btn_msg.msg_buf_long != 0:
            print "btn_msg.msg_buf_long=%d!" % btn_msg.msg_buf_long
            btn_msg.msg_buf_long = 0
        if btn_msg.msg_buf_short != 0:
            print "btn_msg.msg_buf_short=%d!" % btn_msg.msg_buf_short
            btn_msg.msg_buf_short = 0

in_id = threading.Thread(target=in_thread, args=(s,))
in_id.daemon = True
in_id.start()

format = 1
while True:

    desc = raw_input()

    # allow changing which message goes out
    if desc == "1":
        format = 1
        continue;
    elif desc == "2":
        format = 2
        continue;

    if format == 1:
        button_id = btn_msg.ButtonA
        shot_id = 0
        btn_msg.sendArtooString(s, button_id, shot_id, desc + "\0")
    elif format == 2:
        btn_msg.sendShotString(s, desc + "\0")
