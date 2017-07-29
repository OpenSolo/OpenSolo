'''
    Helper functions to work with firmware files
'''
import base64
import zlib
import json


def bytearray_to_wordarray(data):
    '''Converts an 8-bit byte array into a 16-bit word array'''
    wordarray = list()

    for i in range(len(data) / 2):
        # Calculate 16 bit word from two bytes
        msb = data[(i * 2) + 0]
        lsb = data[(i * 2) + 1]
        word = (msb << 8) | lsb
        wordarray.append(word)

    return wordarray

def add_checksum(checksum, word):
    '''Simple XOR checksum'''
    checksum ^= word
    return checksum

def append_checksum(binary):
    '''Calculate and append the XOR checksum to the bytearray'''
    checksum = 0xFFFF
    wordarray = bytearray_to_wordarray(binary)

    # Compute the checksum
    for i in range(len(wordarray)):
        checksum ^= wordarray[i]

    # Add the checksum to the end of the wordarray
    wordarray.extend([checksum & 0xFFFF, (checksum & 0xFFFF) >> 16, 0x0000])

    # Convert the wordarray back into a bytearray
    barray = list()
    for i in range(len(wordarray)):
        lsb = wordarray[i] & 0xFF
        msb = (wordarray[i] >> 8) & 0xFF
        barray.append(lsb)
        barray.append(msb)

    return barray, checksum

def load_firmware(filename):
    '''Load the image from the JSON firmware file into a byte array'''
    with open(filename, "r") as f:
        desc = json.load(f)
        desc['binary'] = bytearray(zlib.decompress(base64.b64decode(desc['image'])))
        return desc
    
    
def load_binary(filename):
    '''Load binary image file into a byte array'''
    with open(filename, "rb") as f:
        return bytearray(f.read())
