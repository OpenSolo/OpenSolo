#!/usr/bin/env python

"""
Utility for loading firmware into the 3DR Gimbal.

"""

import sys

from firmware_helper import append_checksum, load_firmware
import setup_mavlink
import setup_validate

bootloaderVersionHandler = None
progressHandler = None

MAVLINK_ENCAPSULATED_DATA_LENGTH = 253

DATA_TRANSMISSION_HANDSHAKE_EXITING_MAGIC_WIDTH = 0xFFFF

class Results:
    Success, NoResponse, Timeout, InBoot, Restarting = 'Success', 'NoResponse', 'Timeout', 'InBoot', 'Restarting'

def decode_bootloader_version(msg):
    """The first message handshake contains the bootloader version int the height field as a 16bit int"""
    version_major = (msg.height >> 8) & 0xff
    version_minor = msg.height & 0xff
    return [version_major, version_minor]

def start_bootloader(link):
    """Check if target is in booloader, if not reset into bootloader mode"""
    msg = setup_mavlink.get_any_gimbal_message(link)
    if msg and setup_mavlink.is_bootloader_message(msg):
        return Results.InBoot
    
    # Signal the target to reset into bootloader mode
    setup_mavlink.reset_into_bootloader(link)

    # Wait for the bootloader to send a handshake
    timeout_counter = 0
    while timeout_counter < 10:
        msg = setup_mavlink.wait_handshake(link)
        if msg is None:
            setup_mavlink.reset_into_bootloader(link)
            timeout_counter += 1
        else:
            return Results.Restarting
    return Results.NoResponse

def send_block(link, binary, msg):
    sequence_number = msg.width
    payload_length = msg.payload

    # Calculate the window of data to send
    start_idx = sequence_number * payload_length
    end_idx = (sequence_number + 1) * payload_length

    # Clamp the end index from overflowing
    if (end_idx > len(binary)):
        end_idx = len(binary)

    # Slice the binary image
    data = binary[start_idx:end_idx]

    # Pad the data to fit the mavlink message
    if len(data) < MAVLINK_ENCAPSULATED_DATA_LENGTH:
        data.extend([0] * (MAVLINK_ENCAPSULATED_DATA_LENGTH - len(data)))

    # Send the data with the corrosponding sequence number
    setup_mavlink.send_bootloader_data(link, sequence_number, data)
    return end_idx

def upload_data(link, binary):
    global progressHandler, bootloaderVersionHandler

    msg = setup_mavlink.wait_handshake(link)
    if msg == None:
        return Results.NoResponse

    # Emit the bootloader version
    if bootloaderVersionHandler:
        blver = decode_bootloader_version(msg)
        bootloaderVersionHandler(blver[0], blver[1])

    # Loop until we are finished
    end_idx = 0
    retries = 0
    # Note: MAX_RETRIES needs to be longer than the maximum possible flash
    # erase time (2 seconds * 6 Sectors = 12 Seconds)
    MAX_RETRIES = 15 # Seconds
    while end_idx < len(binary):
        msg = setup_mavlink.wait_handshake(link)
        if msg is None:
            if retries > MAX_RETRIES:
                return Results.NoResponse
            else:
                retries += 1
                continue
        retries = 0

        end_idx = send_block(link, binary, msg)
        
        uploaded_kb = round(end_idx / 1024.0, 2)
        total_kb = round(len(binary) / 1024.0, 2)
        percentage = int((100.0 * end_idx) / len(binary))
        if progressHandler:
            progressHandler(uploaded_kb, total_kb, percentage)

    return Results.Success
            
def finish_upload(link):
    """Send an "end of transmission" signal to the target, to cause a target reset""" 
    while True:
        setup_mavlink.exit_bootloader(link)
        msg = setup_mavlink.wait_handshake(link)
        if msg == None:
            return Results.Timeout
        if msg.width == DATA_TRANSMISSION_HANDSHAKE_EXITING_MAGIC_WIDTH:
            break

    if setup_mavlink.wait_for_gimbal_message(link, timeout=10):
        return Results.Success
    else:
        return Results.Timeout

def load_binary(binary, link,  bootloaderVersionCallback=None, progressCallback=None):
    global bootloaderVersionHandler, progressHandler

    if progressCallback:
        progressHandler = progressCallback

    if bootloaderVersionCallback:
        bootloaderVersionHandler = bootloaderVersionCallback

    result = upload_data(link, binary)
    if result != Results.Success:
        return result

    return finish_upload(link)
    