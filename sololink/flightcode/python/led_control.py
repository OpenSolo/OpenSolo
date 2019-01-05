#!/usr/bin/python
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

import argparse
import sys
from SoloLED import SoloLED

class AppendAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not namespace.commands:
            namespace.commands = [];
        optionName = option_string.lstrip(parser.prefix_chars)
        valueList = getattr(namespace, self.dest)
        if not valueList:
            valueList = []
            setattr(namespace, self.dest, valueList)
        if not self.const:
            valueList.append((optionName , values))
        else:
            valueList.append((optionName , values))
        return

def toLED(led):
    return getattr(SoloLED, "LED_" + led.upper())

def toPattern(pattern):
    return getattr(SoloLED, "PATTERN_" + pattern.upper())

ledChoices = choices=["all", "front_left", "front_right", "back_left", "back_right"]
parser = argparse.ArgumentParser()
parser.add_argument("--reset", action=AppendAction, dest="commands", choices=ledChoices, help="Reset to default color and pattern.")
parser.add_argument("--pattern", action=AppendAction, dest="commands", choices=["sine", "solid", "siren", "strobe", "fadein", "fadeout"], help="Set LED flash pattern.")
parser.add_argument("--phase_offset", action=AppendAction, dest="commands", metavar="degrees",  type = int, help="Set phase offset in degrees (range 0-360).")
parser.add_argument("--period", action=AppendAction, dest="commands", metavar="milliseconds", type = int, help="Set period in milliseconds (range 0-4000).")
parser.add_argument("--repeat", action=AppendAction, dest="commands", metavar="count", type = int, help="Set repeat count (0-255).")
parser.add_argument("--color", action=AppendAction, dest="commands", nargs=3, metavar=("red", "green", "blue"), type=int, choices=range(0, 256), help="Set LED red, green, and blue brightness values. (range 0 - 255)")
parser.add_argument("--amplitude", action=AppendAction, dest="commands", nargs=3, metavar=("red", "green", "blue"), type=int, choices=range(0, 256), help="Set LED red, green, and blue amplitude values. (range 0 - 255)")
parser.add_argument("--applyto", action=AppendAction, dest="commands", choices=ledChoices, help="Apply settings to LED(s)")
parser.add_argument("--ip", metavar = "protocol:ipAddress:port", default="udpout:127.0.0.1:14560", help = "Protocol / IP address / Port number for connction")

parsedArgs = parser.parse_args()

color = [255, 255, 255]
pattern = SoloLED.PATTERN_SOLID
phaseOffset = None
repeat = None
period = None
amplitude = None

if parsedArgs.commands is None:
    parser.print_help()
    sys.exit()

soloLED = SoloLED(ip = parsedArgs.ip, wait_ready = False)

for command in parsedArgs.commands:
    commandName = command[0]
    commandArgs = command[1]
    if (commandName == "applyto"):
        if (phaseOffset is None and repeat is None and amplitude is None and period is None):
            soloLED.rgb(toLED(commandArgs), pattern, color[0], color[1], color[2])
        else:
            # default values that weren't already set
            if (amplitude is None):
                amplitude = [0, 0, 0];
            if (repeat is None):
                repeat = 0;
            if (phaseOffset is None):
                phaseOffset = 0;
            if (period is None):
                period = 2000;
            soloLED.rgbExtended(toLED(commandArgs), pattern, color[0], color[1], color[2], amplitude[0], amplitude[1], amplitude[2], period, phaseOffset) 
    elif (commandName == "pattern"):
        pattern = toPattern(commandArgs)
    elif (commandName == "color"):
        color = commandArgs
    elif (commandName == "amplitude"):
        amplitude = commandArgs
    elif (commandName == "phase_offset"):
        phaseOffset = commandArgs
    elif (commandName == "period"):
        period = commandArgs
    elif (commandName == "repeat"):
        repeat = commandArgs
    elif (commandName == "reset"):
        soloLED.reset(toLED(commandArgs))
    else:
        raise ValueError, "Unrecognized command name " + commandName

#sleep(10)

soloLED.close()
print "Done."
