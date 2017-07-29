import os

def blink(on_ms, off_ms):
    os.system("echo timer > /sys/class/leds/user2/trigger")
    os.system("echo %d > /sys/class/leds/user2/delay_on" % (on_ms, ))
    os.system("echo %d > /sys/class/leds/user2/delay_off" % (off_ms, ))

def off():
    os.system("echo none > /sys/class/leds/user2/trigger")
