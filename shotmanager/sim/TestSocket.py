#!/usr/bin/env python
"""
Connects to shotManager so you can send it messages. Fun times!
"""

import os
import socket
import struct
import sys
import threading
import logging
import time
sys.path.append(os.path.realpath('..'))
import app_packet

# create socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('10.1.48.157', 5507)
sock.connect(server_address)

# start listen thread
def listener(sock, verbose):
	currentPacket = ""
	currentPacketLength = 9999

	while True:
		data = sock.recv(1)

		currentPacket += data
		if len(currentPacket) == app_packet.SOLO_MESSAGE_HEADER_LENGTH:
			(currentPacketType, currentPacketLength) = struct.unpack('<II', currentPacket)
			#print "received packet type is ", currentPacketType, currentPacketLength

		if len(currentPacket) == app_packet.SOLO_MESSAGE_HEADER_LENGTH + currentPacketLength:
			value = currentPacket[app_packet.SOLO_MESSAGE_HEADER_LENGTH:]

			if currentPacketType == app_packet.SOLO_MESSAGE_GET_CURRENT_SHOT:
				(shot,) = struct.unpack('<i', value)
				print "[App]: Received SOLO_MESSAGE_GET_CURRENT_SHOT"
				if verbose:
					print "Shot ID: %d" % shot

			elif currentPacketType == app_packet.SOLO_MESSAGE_LOCATION:
				(lat, lon, alt) = struct.unpack('<ddf', value)
				print "[App]: Received SOLO_MESSAGE_LOCATION"
				if verbose:
					print "Location: %f, %f, %f" % (lat, lon, alt)

			elif currentPacketType == app_packet.SOLO_SPLINE_RECORD:
				print "[App]: Received SOLO_SPLINE_RECORD"

			elif currentPacketType == app_packet.SOLO_SPLINE_PLAY:
				print "[App]: Received SOLO_SPLINE_PLAY"

			elif currentPacketType == app_packet.SOLO_SPLINE_POINT:
				(index, lat, lon, alt, pitch, yaw, uPosition, status) = struct.unpack('<Iddffffh', value)
				print "[App]: Received SOLO_SPLINE_POINT"
				if verbose:
					print "Index: %d" % index
					print "Location: %f, %f, %f" % (lat, lon, alt)
					print "Pitch, Yaw: %f, %f" % (pitch, yaw)
					print "uPosition: %f" % uPosition
					print "Status: %d" % status

			elif currentPacketType == app_packet.SOLO_SPLINE_ATTACH:
				(index,) = struct.unpack('<I', value)
				print "[App]: Received SOLO_SPLINE_ATTACH"
				if verbose:
					print "Index: %d" % index

			elif currentPacketType == app_packet.SOLO_SPLINE_PLAYBACK_STATUS:
				(uPosition,uVelocity) = struct.unpack('<ff', value)
				print "[App]: Received SOLO_SPLINE_PLAYBACK_STATUS"
				if verbose:
					print "uPosition: %f" % uPosition
					print "uVelocity: %f" % uVelocity

			elif currentPacketType == app_packet.SOLO_SPLINE_PATH_STATUS:
				(minTime,maxTime) = struct.unpack('<ff', value)
				print "[App]: Received SOLO_SPLINE_PATH_STATUS"
				if verbose:
					print "minTime: %f" % minTime
					print "maxTime: %f" % maxTime

			elif currentPacketType == app_packet.GOPRO_V1_STATE:
				#(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,aa,bb,cc,dd,ee,ff,gg,hh,ii,jj,kk) = struct.unpack('<BBBBBBBBBBBBBBBBBBBBBBBBBBHHHHH', value)
				print "[App]: Received GOPRO_V1_STATE"
				if verbose:
					pass

			elif currentPacketType == app_packet.GOPRO_V2_STATE:
				#(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z,aa,bb,cc,dd,ee,ff,gg,hh,ii,jj,kk) = struct.unpack('<BBBBBBBBBBBBBBBBBBBBBBBBBBHHHHH', value)
				print "[App]: Received GOPRO_V2_STATE"
				if verbose:
					pass		

			# # Gopromanager handles these messages
			# elif self.currentPacketType in GoProManager.GOPROMESSAGES:
			#     self.goproManager.handlePacket( self.currentPacketType, value )
			else:
				print "[App]: Got an unknown packet type: %d" % (currentPacketType)

			# reset packet parsing
			currentPacket = ""

print "Verbose? y/n"
verbose = raw_input(">")
if verbose == "y":
	verbose = True
else:
	verbose = False

w = threading.Thread(name='listener', target=listener,args=(sock,verbose))
w.setDaemon(True)
w.start()

print "Please enter desired shot."
print "0 = Selfie"
print "1 = Orbit"
print "2 = MP Cable Cam"
print "5 = Follow Me"
print "6 = Classic Cable Cam"
print "7 = Load a MP Cable"
shot = raw_input(">")
shot = int(shot)
step = 0

# main "app" loop
while True:
	if shot == 0:
		# send shot request to shotManager
		packet = struct.pack('<III', app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT, 4, shot)
		sock.sendall(packet)
	elif shot == 1:
		# send shot request to shotManager
		packet = struct.pack('<III', app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT, 4, shot)
		sock.sendall(packet)
	elif shot == 2:
		if step == 0:
			aCount = 0
			bCount = 0
			# send shot request to shotManager
			packet = struct.pack('<III', app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT, 4, shot)
			sock.sendall(packet)
			step += 1
		elif step == 1:
			print "Please press A or B button."
			button = raw_input(">")
			if button == "A":
				packet = struct.pack('<II', app_packet.SOLO_RECORD_POSITION, 0)
				sock.sendall(packet)
				aCount += 1
			elif button == "B":
				packet = struct.pack('<II', app_packet.SOLO_RECORD_POSITION, 0)
				sock.sendall(packet)
				packet = struct.pack('<II', app_packet.SOLO_SPLINE_PLAY, 0)
				sock.sendall(packet)
				packet = struct.pack('<III', app_packet.SOLO_SPLINE_ATTACH, 4, aCount)
				sock.sendall(packet)
				packet = struct.pack('<IIhf', app_packet.SOLO_SPLINE_PATH_SETTINGS, 6, 0, 20)
				sock.sendall(packet)
				step += 1
		elif step == 2:
				_ = raw_input("Hit enter to send SEEK.")
				packet = struct.pack('<IIf', app_packet.SOLO_SPLINE_SEEK, 4, 0.5)
				sock.sendall(packet)
				step += 1
	elif shot == 5:
		# send shot request to shotManager
		packet = struct.pack('<III', app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT, 4, shot)
		sock.sendall(packet)
	elif shot == 6:
		# send shot request to shotManager
		packet = struct.pack('<III', app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT, 4, shot)
		sock.sendall(packet)
	elif shot == 7:
		if step == 0:
			# send shot request to shotManager
			packet = struct.pack('<III', app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT, 4, 2)
			sock.sendall(packet)
			#print "[App]: Sent SOLO_MESSAGE_SET_CURRENT_SHOT"
			packet = struct.pack('<IIIddffffh', app_packet.SOLO_SPLINE_POINT, 38, 0, 37.330674, -122.028759, 15, 0, 90, 0, 0)
			sock.sendall(packet)
			#print "[App]: Sent SOLO_SPLINE_POINT"
			packet = struct.pack('<IIIddffffh', app_packet.SOLO_SPLINE_POINT, 38, 1, 37.331456, -122.027785, 15, 0, 45, 0, 0)
			sock.sendall(packet)
			#print "[App]: Sent SOLO_SPLINE_POINT"
			packet = struct.pack('<IIIddffffh', app_packet.SOLO_SPLINE_POINT, 38, 2, 37.332216, -122.027842, 15, 0, 0, 0, 0)
			sock.sendall(packet)
			#print "[App]: Sent SOLO_SPLINE_POINT"
			packet = struct.pack('<II', app_packet.SOLO_SPLINE_PLAY, 0)
			sock.sendall(packet)
			#print "[App]: Sent SOLO_SPLINE_PLAY"
			packet = struct.pack('<III', app_packet.SOLO_SPLINE_ATTACH, 4, 0)
			sock.sendall(packet)
			#print "[App]: Sent SOLO_SPLINE_ATTACH"
			step += 1
