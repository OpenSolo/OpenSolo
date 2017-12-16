'''
  Copyright (C) 2017  Hugh Eaves
 
  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
 
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
 
  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from dronekit import connect
from time import sleep

class SoloLED:
    # LED position values
    LED_BACK_LEFT = 0
    LED_BACK_RIGHT = 1
    LED_FRONT_RIGHT = 2
    LED_FRONT_LEFT = 3
    LED_ALL = 255
    
    # Macros for macro function
    MACRO_RESET = 0 # Removes LED color override
    MACRO_COLOUR_CYCLE = 1 # Party colors
    MACRO_BREATH = 2 # Adds a on/off cycle to any mode
    MACRO_STROBE = 3 # Turn LED's off
    MACRO_FADEIN = 4 # No-Op
    MACRO_FADEOUT = 5 # No-Op
    MACRO_RED = 6 # No-Op
    MACRO_GREEN = 7 # No-Op
    MACRO_BLUE = 8 # No-Op
    MACRO_YELLOW = 9 # All yellow
    MACRO_WHITE = 10 # All LED's white
    MACRO_AUTOMOBILE = 11 # White in front, red in back (Not defined in oreo-led source v1.5)
    MACRO_AVIATION = 12 # White / red / green (Not defined in oreo-led source v1.5)
    MACRO_NOT_A_MACRO_BUT_A_CUSTOM_COMMAND = 255 # indicates this is not a macro, but a custom command
    
    # Flash patterns for rgb function
    PATTERN_OFF = 0
    PATTERN_SINE = 1
    PATTERN_SOLID = 2
    PATTERN_SIREN = 3
    PATTERN_STROBE = 4
    PATTERN_FADEIN = 5
    PATTERN_FADEOUT = 6
    PATTERN_PARAMUPDATE = 7  # Not sure what this does.
    
    # Commands for custom function
    PARAM_BIAS_RED = 0
    PARAM_BIAS_GREEN = 1
    PARAM_BIAS_BLUE = 2
    PARAM_AMPLITUDE_RED = 3
    PARAM_AMPLITUDE_GREEN = 4
    PARAM_AMPLITUDE_BLUE = 5
    PARAM_PERIOD = 6
    PARAM_REPEAT = 7
    PARAM_PHASEOFFSET = 8
    PARAM_MACRO = 9
    PARAM_RESET = 10 # Not sure what this does (Not defined in oreo-led source v1.5)
    PARAM_APP_CHECKSUM = 11 # Not sure what this does (Not defined in oreo-led source v1.5)
    
    CUSTOM_BYTES_LENGTH = 24

    def __init__(self, ip = None, vehicle = None, wait_ready=True):
        print "Connecting to", ip
        if (ip == None):
            ip = "udpin:0.0.0.0:14550"
        if (vehicle == None):
            self.vehicle = connect(ip, wait_ready=wait_ready)
        else:
            self.vehicle = vehicle
        
    # Pad byteArray to required length for custom message (24 bytes)
    def padArray(self, byteArray):
        return byteArray + bytearray([0]) * (self.CUSTOM_BYTES_LENGTH - len(byteArray))    
    
    # Set LED macro
    def macro(self, led, macro):
        print "macro", led, macro
        self.sendMessage(led, macro)

    # Set LED pattern and color (RGB value)
    def rgb(self, led, pattern, red, green, blue):
        print "rgb", led, pattern, red, green, blue
        byteArray = bytearray(['R', 'G', 'B', '0', pattern, red, green, blue])
        self.sendMessage(led, self.MACRO_NOT_A_MACRO_BUT_A_CUSTOM_COMMAND, byteArray)

    # Set LED pattern, color (RGB value), and extended parameters
    def rgbExtended(self, led, pattern, red, green, blue, amplitudeRed, amplitudeGreen, amplitudeBlue, period, phaseOffset):
        print "rgbExtended", led, pattern, red, green, blue, amplitudeRed, amplitudeGreen, amplitudeBlue, period, phaseOffset
        byteArray = bytearray(['R', 'G', 'B', '1', pattern, red, green, blue, amplitudeRed, amplitudeGreen, amplitudeBlue,
                               period >> 8, period & 0xff, phaseOffset >> 8, phaseOffset & 0xff])
        self.sendMessage(led, self.MACRO_NOT_A_MACRO_BUT_A_CUSTOM_COMMAND, byteArray)
    
    # reset LED to default behavior
    def reset(self, led):
        print "reset", led
        self.macro(led, SoloLED.MACRO_RESET)


    def sendMessage(self, led, macro, byteArray = bytearray()):
        print "sendMessage", led, macro, ":".join(str(b) for b in byteArray)
        msg = self.vehicle.message_factory.led_control_encode(0, 0, led, macro, len(byteArray), self.padArray(byteArray))
        self.vehicle.send_mavlink(msg)
        # Can't find a functional flush() operation, so wait instead
        sleep(0.1)

    def close(self):
        # Doesn't appear to do anything unless sending waypoints
        self.vehicle.flush()
        # Can't find a functional flush() operation, so wait instead (hopefully that's enough)
        sleep(0.2)
        self.vehicle.close()
        # Cleanly shut down mavlink handler threads to avoid error on exit
        if self.vehicle._handler.mavlink_thread_in is not None:
            self.vehicle._handler.mavlink_thread_in.join()
            self.vehicle._handler.mavlink_thread_in = None        
        if self.vehicle._handler.mavlink_thread_out is not None:
            self.vehicle._handler.mavlink_thread_out.join()
            self.vehicle._handler.mavlink_thread_out = None
