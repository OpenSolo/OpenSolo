#!/usr/bin/env python

import os, sys, time, fnmatch
import serial.tools.list_ports
from pymavlink import mavutil
from pymavlink.mavutil import mavlink, mavserial, SerialPort
from pymavlink.dialects.v10 import ardupilotmega
from pymavlink.rotmat import Vector3
import setup_comutation, setup_mavlink
import serial

MAVLINK_SYSTEM_ID = 255
MAVLINK_COMPONENT_ID = mavlink.MAV_COMP_ID_GIMBAL
TARGET_SYSTEM_ID = 1
TARGET_COMPONENT_ID = mavlink.MAV_COMP_ID_GIMBAL

DATA_TRANSMISSION_HANDSHAKE_SIZE_MAGIC = 0x42AA5542

def getSerialPorts(preferred_list=['*USB Serial*','*FTDI*']):
    if os.name == 'nt':
        ports = list(serial.tools.list_ports.comports())
        ret = []
        for name, desc, hwid in ports:
            for preferred in preferred_list:
                if fnmatch.fnmatch(desc, preferred) or fnmatch.fnmatch(hwid, preferred):
                    ret.append(SerialPort(name, description=desc, hwid=hwid))
                    break
        return ret
    return mavutil.auto_detect_serial(preferred_list=preferred_list)

def open_comm(port=None, baudrate=230400):
    link = None
    try:
        if not port:
            serial_list = getSerialPorts(preferred_list=['*USB Serial*','*FTDI*'])
            if len(serial_list) >= 1:
                port = serial_list[0].device
            else:
                port = '0.0.0.0:14550'
        mavserial = mavutil.mavlink_connection(device=port, baud=baudrate)
        link = mavlink.MAVLink(mavserial, MAVLINK_SYSTEM_ID, MAVLINK_COMPONENT_ID)
        link.target_sysid = TARGET_SYSTEM_ID
        link.target_compid = TARGET_COMPONENT_ID
    except Exception:
        pass
    finally:
        return (port, link)

def wait_handshake(link, timeout=1, retries=1):
    '''wait for a handshake so we know the target system IDs'''
    for retries in range(retries):
        msg = link.file.recv_match(type='DATA_TRANSMISSION_HANDSHAKE', blocking=True, timeout=timeout)
        if msg and msg.get_srcComponent() == mavlink.MAV_COMP_ID_GIMBAL:
                return msg
    return None

def get_current_joint_angles(link):
    while(True):
        msg_gimbal = link.file.recv_match(type="GIMBAL_REPORT", blocking=True, timeout=2)
        if msg_gimbal == None:
            return None
        else:
            return Vector3([msg_gimbal.joint_roll, msg_gimbal.joint_el, msg_gimbal.joint_az])
        
def get_current_delta_angles(link):
    while(True):
        msg_gimbal = link.file.recv_match(type="GIMBAL_REPORT", blocking=True, timeout=2)
        if msg_gimbal == None:
            return None
        else:
            return Vector3([msg_gimbal.delta_angle_x, msg_gimbal.delta_angle_y, msg_gimbal.delta_angle_z])

def get_current_delta_velocity(link, timeout=1):
    if not isinstance(link.file, mavserial):
        print "accelerometer calibration requires a serial connection"
        sys.exit(1)    
    link.file.port.flushInput() # clear any messages in the buffer, so we get a current one
    while(True):
        msg_gimbal = link.file.recv_match(type="GIMBAL_REPORT", blocking=True, timeout=timeout)
        if msg_gimbal == None:
            return None
        else:
            return Vector3([msg_gimbal.delta_velocity_x, msg_gimbal.delta_velocity_y, msg_gimbal.delta_velocity_z])

def get_gimbal_report(link, timeout=2):
    msg_gimbal = link.file.recv_match(type="GIMBAL_REPORT", blocking=True, timeout=timeout)
    return msg_gimbal

def send_gimbal_control(link, rate):
    link.gimbal_control_send(link.target_sysid, link.target_compid,rate.x,rate.y,rate.z)
       
def reset_gimbal(link):
    link.file.mav.command_long_send(link.target_sysid, link.target_compid, 42501, 0, 0, 0, 0, 0, 0, 0, 0)
    result = link.file.recv_match(type="COMMAND_ACK", blocking=True, timeout=3)
    if result:
        # Sleep to allow the reset command to take
        time.sleep(2)
        # Wait for the gimbal to reset and begin comms again
        return setup_mavlink.get_any_gimbal_message(link, timeout=5)
    else:
        return False 

def reset_into_bootloader(link):
    return link.data_transmission_handshake_send(mavlink.MAVLINK_TYPE_UINT16_T, DATA_TRANSMISSION_HANDSHAKE_SIZE_MAGIC, 0, 0, 0, 0, 0)

def exit_bootloader(link):
    return link.data_transmission_handshake_send(mavlink.MAVLINK_TYPE_UINT16_T, 0, 0, 0, 0, 0, 0)

def send_bootloader_data(link, sequence_number, data):
    return link.encapsulated_data_send(sequence_number, data)

def getCalibrationProgress(link):
    while(True):
        msg_progress = link.file.recv_match(type="COMMAND_LONG", blocking=True, timeout=1)
        if msg_progress is None:
            return None
        if msg_progress.command == 42502:
            break

    axis = setup_comutation.axis_enum[int(msg_progress.param1) - 1]
    progress = int(msg_progress.param2)
    status = setup_comutation.status_enum[int(msg_progress.param3)]
    
    return [axis, progress, status]

def receive_home_offset_result(link):
    return link.file.recv_match(type="COMMAND_ACK", blocking=True, timeout=3)

def requestCalibration(link):
    return link.file.mav.command_long_send(link.target_sysid, link.target_compid, 42503, 0, 0, 0, 0, 0, 0, 0, 0)

def get_all(link, timeout=1):
    msg = link.file.recv_match(blocking=True, timeout=timeout)
    if msg != None:
        if msg.get_srcComponent() == mavlink.MAV_COMP_ID_GIMBAL:
            return msg
    return None

def get_any_message(link, timeout=1):
    return link.file.recv_match(blocking=True, timeout=timeout)

def get_gimbal_message(link, timeout=2):
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        msg = link.file.recv_match(blocking=True, timeout=1)
        if msg:
            if msg.get_srcComponent() == mavlink.MAV_COMP_ID_GIMBAL:
                # Ignore the two types of bootloader messages
                if msg.get_msgId() == mavlink.MAVLINK_MSG_ID_DATA_TRANSMISSION_HANDSHAKE:
                    return False
                if msg.get_msgId() == mavlink.MAVLINK_MSG_ID_HEARTBEAT:
                    continue
                else:
                    return True
    return False

def wait_for_gimbal_message(link, timeout=5):
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if get_gimbal_message(link, timeout=1):
            return True
    return None

def get_any_gimbal_message(link, timeout=2):
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        msg = link.file.recv_match(blocking=True, timeout=1)
        if msg:
            if (msg.get_srcComponent() == mavlink.MAV_COMP_ID_GIMBAL
                and msg.get_msgId() != mavlink.MAVLINK_MSG_ID_HEARTBEAT):
                return msg
    return None

def wait_for_any_gimbal_message(link, timeout=5):
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if get_any_gimbal_message(link, timeout=1):
            return True
    return None

def is_bootloader_message(msg):
    if (msg.get_srcComponent() == mavlink.MAV_COMP_ID_GIMBAL and
        msg.get_msgId() == mavlink.MAVLINK_MSG_ID_DATA_TRANSMISSION_HANDSHAKE):
        return True
    return False

if __name__ == '__main__':
    import argparse, setup_home, setup_param
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="Serial port or device used for MAVLink bootloading", default=None)
    parser.add_argument("--jointstest", help="Run a number of joint calibrations", action='store_true')
    parser.add_argument("--printjoints", help="Print out joint angles", action='store_true')
    parser.add_argument("--printall", help="Print out all mavlink messages", action='store_true')
    args = parser.parse_args()

    # Open the serial port
    port, link = open_comm(args.port)
    print("Connecting via port %s" % port)

    # Send a heartbeat first to wake up the interface
    link.heartbeat_send(0, 0, 0, 0, 0)

    if args.jointstest:
        print("Power On")
        setup_param.enable_torques_message(link, enabled=False)
        for i in range(5):
            print setup_home.calibrate_joints(link)

    elif args.printjoints:
        while True:
            msg = get_gimbal_report(link)
            print msg.joint_az, msg.joint_roll, msg.joint_el

    elif args.printall:
        while True:
            print get_any_message(link)

    else:
        while True:
            print time.time(), get_gimbal_message(link)
