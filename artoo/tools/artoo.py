#!/usr/bin/env python

# common defs for artoo

BAUD = 115200

# host protocol msg id's
MSGID_NOP                   = chr(0x0)
MSGID_DSM_CHANNELS          = chr(0x1)
MSGID_CALIBRATE             = chr(0x2)
MSGID_SYS_INFO              = chr(0x3)
MSGID_MAVLINK               = chr(0x4)
MSGID_SET_RAW_IO            = chr(0x5)
MSGID_RAW_IO_REPORT         = chr(0x6)
MSGID_PAIR_REQUEST          = chr(0x7)
MSGID_PAIR_CONFIRM          = chr(0x8)
MSGID_PAIR_RESULT           = chr(0x9)
MSGID_SHUTDOWN_REQUEST      = chr(0xa)
MSGID_PARAM_STORED_VALS     = chr(0xb)
MSGID_OUTPUT_TEST           = chr(0xc)
MSGID_BUTTON_EVENT          = chr(0xd)
MSGID_INPUT_REPORT          = chr(0xe)
MSGID_CONFIG_STICK_AXES     = chr(0xf)
MSGID_BUTTON_FUNCTION_CFG   = chr(0x10)
MSGID_SET_SHOT_INFO         = chr(0x11)
MSGID_UPDATER               = chr(0x12)
MSGID_LOCKOUT_STATE         = chr(0x13)
MSGID_SELF_TEST             = chr(0x14)
MSGID_SWEEP_TIME_CFG        = chr(0x15)
MSGID_GPIO_TEST             = chr(0x16)
MSGID_TEST_EVENT            = chr(0x17)
MSGID_SET_TELEM_UNITS       = chr(0x18)
MSGID_INVALID_STICK_INPUTS  = chr(0x19)
MSGID_SOLO_APP_CONNECTION   = chr(0x1a)

# button IDs
BtnPower        = 0
BtnFly          = 1
BtnRTL          = 2
BtnLoiter       = 3
BtnA            = 4
BtnB            = 5
BtnPreset1      = 6
BtnPreset2      = 7
BtnCameraClick  = 8

# button names
BtnName = ["Power", "Fly", "RTL", "Loiter", "A", "B",
              "Preset1", "Preset2", "CameraClick"]

# button events
BtnEvtPress         = 0
BtnEvtRelease       = 1
BtnEvtClickRelease  = 2
BtnEvtHold          = 3
BtnEvtLongHold      = 4
BtnEvtDoubleClick   = 5

# GPIO test
GPIO_TEST_LED_BACKLIGHT = 0
GPIO_TEST_CHG_ENABLE    = 1

# units
UNITS_USE_METRIC    = 1
UNITS_USE_IMPERIAL  = 0

class Artoo:

    def __init__(self, slip_dev):
        self.slip_dev = slip_dev

    def read(self):
        return self.slip_dev.read()

    def set_lockout_state(self, locked):
        lck = chr(1) if locked else chr(0)
        self.slip_dev.write([MSGID_LOCKOUT_STATE, lck])

    def request_sys_info(self):
        self.slip_dev.write([MSGID_SYS_INFO])

    def begin_self_test(self):
        self.slip_dev.write([MSGID_SELF_TEST, 0x74, 0x73, 0x65, 0x74, 0x66, 0x6c, 0x65, 0x73])

    def gpio_test(self, pin, state):
        self.slip_dev.write([MSGID_GPIO_TEST, pin, state])

    def set_telem_units(self, units):
        self.slip_dev.write([MSGID_SET_TELEM_UNITS, units])
    
    def output_test(self, bg_btnmask, fg_btnmask, freq, haptic_secs):
        self.slip_dev.write([MSGID_OUTPUT_TEST, bg_btnmask, fg_btnmask, freq & 0xff, (freq >> 8) & 0xff, haptic_secs])

