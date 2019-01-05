#ifndef _PACKETTYPES_H
#define _PACKETTYPES_H

/***********************************************************************
Serial packet IDs
Match constants in artoo/src/hostProtocol.h
***********************************************************************/
#define PKT_ID_NOP 0
#define PKT_ID_DSM_CHANNELS 1
#define PKT_ID_CALIBRATE 2
#define PKT_ID_SYS_INFO 3
#define PKT_ID_MAVLINK 4
#define PKT_ID_SET_RAW_IO 5
#define PKT_ID_RAW_IO_REPORT 6
#define PKT_ID_PAIR_REQUEST 7
#define PKT_ID_PAIR_CONFIRM 8
#define PKT_ID_PAIR_RESULT 9
#define PKT_ID_SHUTDOWN_REQUEST 10
#define PKT_ID_PARAM_STORED_VALS 11
#define PKT_ID_OUTPUT_TEST 12
#define PKT_ID_BUTTON_EVENT 13
#define PKT_ID_INPUT_REPORT 14
#define PKT_ID_CONFIG_STICK_AXES 15
#define PKT_ID_BUTTON_FUNCTION_CFG 16
#define PKT_ID_SET_SHOT_INFO 17
#define PKT_ID_UPDATER 18
#define PKT_ID_LOCKOUT_STATE 19
#define PKT_ID_SELF_TEST 20 // test fixture only
#define PKT_ID_CONFIG_SWEEP_TIME 21
#define PKT_ID_GPIO_TEST 22
#define PKT_ID_TEST_EVENT 23
#define PKT_ID_SET_TELEM_UNITS 24
#define PKT_ID_INVALID_STICK_INPUTS 25
#define PKT_ID_SOLO_APP_CONNECTION 26

#define PKT_ID_MAX 27

#endif //_PACKETTYPES_H
