import socket
import time
import struct
from threading import Thread
from sololink import rc_pkt

rc_sock = None
rc_attached = False

rc_actual = [1500, 1500, 900, 1500, 0, 0, 0, 0]
rc_override = [1500, 1500, 900, 1500, 0, 0, 0, 0]

def attach():
    global rc_attached
    rc_attached = True

def detach():
    global rc_attached
    rc_attached = False

def put(arg):
    global rc_override
    (timestamp, sequence, chan) = arg
    rc_override = [chan[2], chan[1], chan[0], chan[3], chan[4], chan[5], chan[6], chan[7]]
    return True

def pixrc_start():
    global rc_sock
    global rc_actual

    if not rc_sock:
        rc_sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        rc_sock.setblocking(0)

        rc_actual = [1500, 1500, 900, 1500, 0, 0, 0, 0]

    def listener():
        global rc_sock, rc_actual
        sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        sock.bind(('0.0.0.0', 13341))

        while True:
            try:
                data = sock.recv( 1000 )
                if data == None or len(data) != rc_pkt.LENGTH:
                    continue

                (timestamp, sequence, chan) = rc_pkt.unpack(data)
                rc_actual = [chan[2], chan[1], chan[0], chan[3], chan[4], chan[5], chan[6], chan[7]]
            except Exception as e:
                print(e)
                if rc_sock == None:
                    return

    t_l = Thread(target=listener)
    t_l.daemon = True
    t_l.start()

    def sender():
        global rc_sock, rc_override, rc_attached
        while True:
            time.sleep(.020)
            pkt = struct.pack('<HHHHHHHH', *(rc_override if rc_attached else rc_actual))
            try:
                # print('--->', rc_attached, rc_override if rc_attached else rc_actual)
                rc_sock.sendto(pkt, ('127.0.0.1', 5501))
            except Exception as e:
                print(e)
                if rc_sock == None:
                    return

    t_s = Thread(target=sender)
    t_s.daemon = True
    t_s.start()

def pixrc_stop():
    global rc_sock
    if rc_sock:
        rc_sock.close()
    rc_sock = None
