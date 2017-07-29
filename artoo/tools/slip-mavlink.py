#!/usr/bin/env python
#
# script to bidirectionally bridge mavlink and the SLIP stream
# supported on artoo
#
# i mainly use this script to communicate with the SITL environment as follows:
#   * connect an FTDI cable (or similar) from the UART on Artoo to your dev machine
#   * run SITL in a VM, using `--out 192.168.1.158:14550` to pipe to your machine (adjust IP addr as necessary)
#   * fire up this script on your dev machine: `python slip-mavlink.py /dev/tty.usbserial-FTFA80EV`
#

import sys, os, socket, serial, select, struct, datetime, array
import slip, button, artoo
from pymavlink import mavutil


# enable for more verbose output
SHOW_THROUGHPUT = False

MAVPROXY_DEFAULT_PORT = 14550

ARTOO_DSM_ID        = chr(0x1)
ARTOO_MAVLINK_ID    = chr(0x4)  # artoo msg type specifying this is a mavlink packet
#ARTOO_SHOT_INFO_ID  = chr()
ARTOO_MAVLINK_SYSID = 0xff      # default sysid pixhawk looks for

DEFAULT_BAUD = 115200


FLIGHT_MODES = {
    0: "STABILIZE",
    1: "ACRO",
    2: "ALT HOLD",
    3: "AUTO",
    4: "GUIDED",
    5: "LOITER",
    6: "RTL",
    7: "CIRCLE",
    9: "LAND",
    10: "OF_LOITER",
    11: "DRIFT",
    13: "SPORT",
    14: "FLIP",
    15: "AUTOTUNE",
    16: "POS HOLD",
    17: "STOP",
}


def artooMavlinkPkt(mav, slip_pkt):
    if slip_pkt[0] == ARTOO_MAVLINK_ID:
        # extract and return the mavlink portion of this packet
        return "".join(slip_pkt[1:])

    if slip_pkt[0] == ARTOO_DSM_ID:
        # convert a raw DSM packet into an RC override mavlink packet
        # it's possible to send raw DSM packets directly into the ArduCopter simulation process,
        # but if SITL is running within a VM, it's extra work to expose that network connection,
        # so we just send via mavproxy since we already have a connection to it.

        pkt_length = len(slip_pkt[1:])
        if (pkt_length != 16):
            print ("[slip-mavlink] Received packet of length: {}".format(pkt_length))
            return None

        ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8 = struct.unpack("<HHHHHHHH", "".join(slip_pkt[1:]))
        # on solo, rc input is piped through the spektrum, which rearranges channel values
        # to match the order expected by ardupilot. see dsm_decode() in px4's dsm.c.
        ch1, ch2, ch3 = ch2, ch3, ch1

        return mavutil.mavlink.MAVLink_rc_channels_override_message(1, 1, ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8).pack(mav)


def send_shot_info(slipdev, shot):
    slipdev.write("".join([artoo.MSGID_SET_SHOT_INFO, shot, '\0']))


def fwd_shot_info(mav, slipdev, pkt):
    '''
    roughly simulate shot manager by sending down flight mode changes as shot info.
    we'll never send any actual 'shots', since we're just running against sitl,
    but it's better than nothing.
    '''
    try:
        m = mav.decode(array.array('B', pkt))
        if m.get_msgId() == mavutil.mavlink.MAVLINK_MSG_ID_HEARTBEAT:
            if m.custom_mode in FLIGHT_MODES:
                send_shot_info(slipdev, FLIGHT_MODES[m.custom_mode])
    except mavutil.mavlink.MAVError as me:
        print "MAVError:", me


def send_status_text(slipdev, severity, txt):
    '''
    helper to send a status text message to artoo, useful for testing
    alerts for vehicle failures.
    '''
    solo_mav = mavutil.mavlink.MAVLink(None, 0x1, 0x1)
    mav_pkt = mavutil.mavlink.MAVLink_statustext_message(severity, txt)
    slipdev.write("".join([ARTOO_MAVLINK_ID, mav_pkt.pack(solo_mav)]))


def handleCommand(slipdev, cmd):
    '''
    spot to handle arbitrary input from user.
    can be helpful to test scenarios that require serial input, but must
    also have serial connected to SITL.
    '''

    if cmd == "um":
        artoo.Artoo(slipdev).set_telem_units(artoo.UNITS_USE_METRIC)
    elif cmd == "ui":
        artoo.Artoo(slipdev).set_telem_units(artoo.UNITS_USE_IMPERIAL)


    print "cmd:", cmd

def mainloop(ser, addr, port):
    print "listening on %s:%d, sending to %s" %(addr, port, ser)

    serialport = serial.Serial(ser, DEFAULT_BAUD)
    slipdev = slip.SlipDevice(serialport)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x00)
    sock.bind((addr, port))

    mav = mavutil.mavlink.MAVLink(None, ARTOO_MAVLINK_SYSID, mavutil.mavlink.MAV_TYPE_GCS)

    peer_addr = None

    inputs = [sock, serialport, sys.stdin]

    rx_bytes = 0
    tx_bytes = 0
    ts = datetime.datetime.now()

    # wait for input on either the UDP socket or the serial port, and forward it
    while True:
        readable, writable, exceptional = select.select(inputs, [], inputs)

        if sock in readable:
            udp_pkt, peer_addr = sock.recvfrom(1024)
            if udp_pkt:
                rx_bytes += slipdev.write("".join([ARTOO_MAVLINK_ID, udp_pkt]))
                fwd_shot_info(mav, slipdev, udp_pkt)


        if serialport in readable:
            mav_pkt = artooMavlinkPkt(mav, slipdev.read())
            if mav_pkt and peer_addr:
                tx_bytes += len(mav_pkt)
                sock.sendto(mav_pkt, peer_addr)

        if sys.stdin in readable:
            cmd = sys.stdin.readline().strip()
            handleCommand(slipdev, cmd)

        dt = datetime.datetime.now() - ts
        if SHOW_THROUGHPUT and dt.seconds > 5:
            sys.stdout.write(("throughput (bytes/sec) - tx: %d, rx: %d\r") % (tx_bytes/5, rx_bytes/5))
            sys.stdout.flush()
            ts = datetime.datetime.now()
            rx_bytes = 0
            tx_bytes = 0


if len(sys.argv) < 2:
    print "usage: slip-mavlink.py /dev/ttyMyDev (addr:port)"
    sys.exit(1)

serial_path = sys.argv[1]
if len(sys.argv) >= 3:
    addr, port = sys.argv[2].split(":")
    if port == "":
        port = MAVPROXY_DEFAULT_PORT
else:
    addr, port = '', MAVPROXY_DEFAULT_PORT
    # this assumes we want to listen to something coming from our own address,
    # ie, a SITL instance running in a VM vai NAT
    myaddr = socket.gethostbyname(socket.gethostname())
    if myaddr is not '127.0.0.1':
        addr = myaddr

mainloop(serial_path, addr, int(port))
