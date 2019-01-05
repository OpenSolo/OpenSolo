#!/usr/bin/env python
"""
Test script to test sending RC input to shotManager
(Used for testing shotManager in SITL)
Also emulates the button server in stm32 running on Artoolink
This takes user input to change rc values (use the arrow keys)

Only meant for debugging purposes, so it's not production code
"""

#Imports
import sys
import os
import curses
import Queue
import select
import socket
import struct
import threading
import time
sys.path.append(os.path.realpath('..'))
import app_packet
sys.path.append(os.path.realpath('../../../net/usr/bin'))
from sololink import rc_pkt
sys.path.append(os.path.realpath('../../../flightcode/stm32'))
from sololink import btn_msg

#Globals
state = "starting" #state of artoo emulator
stringsUpdated = False
Amapping = "unset"
Bmapping = "unset"
shotName = "unset"

NUM_CHANNELS = 8
channelValues = [1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500]
PORT = 5016

outputLock = threading.Lock()

def main(stdscr):
    '''Main function that contains while loop, wrapped by curses'''

    #import globals
    global state
    global stringsUpdated
    global Amapping
    global Bmapping
    global shotName
    global clientQueue

    stringsUpdated = True
    activeChannel = 0
    stdscr.nodelay(1)
    stdscr.addstr(0,10,"Hit 'q' to quit")

    for i in range(NUM_CHANNELS):
        stdscr.addstr(i+2, 20, "Channel %d : %d" % (i+1, channelValues[i]))


    stdscr.addstr(activeChannel+2, 18, ">>")
    stdscr.addstr(12, 10, "Hit up/down to change active channel")
    stdscr.addstr(13, 10, "Hit left/right to change stick value")
    stdscr.addstr(14, 10, "Hit 'c' to release sticks")
    stdscr.refresh()

    #start RC thread
    rc = threading.Thread(name = "sendRC", target = sendRC, args = ())
    rc.daemon = True
    rc.start()

    #start artoo thread
    artooThread = threading.Thread(name = "ArtooButtonThread", target = ArtooButtonThread, args = ())
    artooThread.daemon = True
    artooThread.start()

    key = ''

    while key != ord('q'):
        key = stdscr.getch()
        stdscr.refresh()
        if key == curses.KEY_UP:
            stdscr.addstr(activeChannel+2, 18, "  Channel %d : %d"%(activeChannel + 1, channelValues[activeChannel]))
            activeChannel -= 1
            if activeChannel < 0:
                activeChannel = 0
            stdscr.addstr(activeChannel+2, 18, ">>")
        if key == curses.KEY_DOWN:
            stdscr.addstr(activeChannel+2, 18, "  Channel %d : %d"%(activeChannel + 1, channelValues[activeChannel]))
            activeChannel += 1
            if activeChannel >= NUM_CHANNELS:
                activeChannel = NUM_CHANNELS - 1
            stdscr.addstr(activeChannel+2, 18, ">>")
        if key == curses.KEY_RIGHT:
            channelValues[activeChannel] += 10
            if channelValues[activeChannel] > 2000:
            	channelValues[activeChannel] = 2000
            stdscr.addstr(activeChannel+2, 18, "  Channel %d : %d"%(activeChannel + 1, channelValues[activeChannel]))
        if key == curses.KEY_LEFT:
            channelValues[activeChannel] -= 10
            if channelValues[activeChannel] < 1000:
                channelValues[activeChannel] = 1000
            stdscr.addstr(activeChannel+2, 18, "  Channel %d : %d"%(activeChannel + 1, channelValues[activeChannel]))
        if key == ord('c'):
            for i in range(NUM_CHANNELS):
                channelValues[i] = 1500
                stdscr.addstr(i+2, 20, "Channel %d : %d" % (i+1, channelValues[i]))
        # hit the A button
        if key == ord('a'):
            #   (timestamp_us, button_id, button_event, pressed_mask)
            pkt = struct.pack("<QBBH", 0, btn_msg.ButtonA, btn_msg.Press, 0)
            sendPacket(pkt)
        if key == ord('b'):
            #   (timestamp_us, button_id, button_event, pressed_mask)
            pkt = struct.pack("<QBBH", 0, btn_msg.ButtonB, btn_msg.Press, 0)
            sendPacket(pkt)
        if key == ord('p'):
            #   (timestamp_us, button_id, button_event, pressed_mask)
            pkt = struct.pack("<QBBH", 0, btn_msg.ButtonLoiter, btn_msg.Press, 0)
            sendPacket(pkt)
        if key == ord('f'):
            #   (timestamp_us, button_id, button_event, pressed_mask)
            pkt = struct.pack("<QBBH", 0, btn_msg.ButtonFly, btn_msg.Press, 0)
            sendPacket(pkt)

        if stringsUpdated:
            stdscr.addstr(16, 10, 'Current shot: ' + shotName + '              ')
            stdscr.addstr(17, 10, "Hit 'a' to do " + Amapping + '              ')
            stdscr.addstr(18, 10, "Hit 'b' to do " + Bmapping + '              ')
            stdscr.addstr(19, 10, "Hit 'p' to hit pause button")
            stdscr.addstr(20, 10, "Hit 'f' to hit fly button")
            stdscr.addstr(21, 10, state + '              ')
            stdscr.refresh()

            stringsUpdated = False
        time.sleep(0.01)

def sendRC():
    '''Sends RC to Sololink'''

    #import globals
    global channelValues
    rcSock = None

    #Main RC loop
    while True:
        if not rcSock:
            #print "trying to connect"
            if os.path.exists( "/tmp/shotManager_RCInputs_socket" ):
                rcSock = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
            try:
                rcSock.connect( "/tmp/shotManager_RCInputs_socket" )
            except:
                rcSock = None
        else:
            #print "connected, sending rc info"
            try:
                pkt = rc_pkt.pack((0, 0, [channelValues[2], channelValues[0],
                    channelValues[1], channelValues[3], channelValues[4],
                    channelValues[5], channelValues[6], channelValues[7]]))
                rcSock.send(pkt)
                #print "sending rc data"
            except socket.error:
                #print "failed to send"
                rcSock = None
        time.sleep(1.0 / 50.0)
    rcSock.close()

def sendPacket(pkt):
    '''Sends packet to client (Sololink)'''
    if clientQueue:
        global outputPacket
        outputLock.acquire()
        clientQueue.put(pkt)
        outputLock.release()


def ArtooButtonThread():
    '''this thread simulates the server running in the stm32 process in Artoolink'''

    #import globals
    global state
    global stringsUpdated
    global Amapping
    global Bmapping
    global shotName
    global clientQueue

    #establish server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(0)

    # Bind the socket to the port
    server_address = ('', PORT)

    stringsUpdated = True
    currentPacket = ""
    currentPacketLength = 9999
    currentPacketType = None

    #blocking connect loop
    while True:
        try:
            server.bind(server_address)
        except:
            time.sleep(1.0)
            pass
        else:
            break

    #update emulator state
    state = "bound"
    stringsUpdated = True

    server.listen(2)
    inputs = [server,]
    outputs = []

    #main emulator loop
    while True:
        #grab data on pipe
        rl, wl, el = select.select( inputs, outputs, [] )

        for s in rl:
            if s is server:
                client, address = server.accept()
                client.setblocking(0)
                inputs.append(client)
                outputs.append(client)
                clientQueue = Queue.Queue()
                state = "accepted"
                stringsUpdated = True
            else:
                data = s.recv( 1 )

                if data:
                    currentPacket += data

                    state = "got a packet"

                    # parse the packet
                    if len(currentPacket) == app_packet.SOLO_MESSAGE_HEADER_LENGTH:
                        (currentPacketType, currentPacketLength) = struct.unpack('<II', currentPacket)
                    if len(currentPacket) == app_packet.SOLO_MESSAGE_HEADER_LENGTH + currentPacketLength:
                        value = currentPacket[app_packet.SOLO_MESSAGE_HEADER_LENGTH:]
                        if currentPacketType == btn_msg.ARTOO_MSG_SET_BUTTON_STRING:
                            state = "Button String"
                            (button_id, event, shot, mask) = struct.unpack('<BBbb', value[:4])
                            artooString = value[4:]

                            if button_id == btn_msg.ButtonA:
                                # remove null terminator
                                Amapping = artooString[:-1]

                                if mask & btn_msg.ARTOO_BITMASK_ENABLED:
                                    Amapping += "(enabled)"
                                else:
                                    Amapping += "(disabled)"
                            elif button_id == btn_msg.ButtonB:
                                # remove null terminator
                                Bmapping = artooString[:-1]

                                if mask & btn_msg.ARTOO_BITMASK_ENABLED:
                                    Bmapping += "(enabled)"
                                else:
                                    Bmapping += "(disabled)"
                        elif currentPacketType == btn_msg.ARTOO_MSG_SET_SHOT_STRING:
                            # remove null terminator
                            shotName = value[:-1]

                        currentPacket = ""
                else:
                    inputs.remove(s)
                    outputs.remove(s)
                    s.close()
                    client = None
                    clientQueue = None
                stringsUpdated = True

        # now handle writes
        for s in wl:
            outputLock.acquire()
            try:
                if clientQueue:
                    msg = clientQueue.get_nowait()
            except Queue.Empty:
                pass   
            else:
                try:
                    s.send(msg)
                except Exception as e:
                    state = 'Shotmanager disconnected.'
                    shotName = 'unset'
                    Amapping = 'unset'
                    Bmapping = 'unset'

            outputLock.release()

#Calls main function inside a curses wrapper for graceful exit
if __name__ == '__main__':
	curses.wrapper(main)
