#ifndef BOARD_H
#define BOARD_H

// board hw revision options
#define BOARD_BB02      1
#define BOARD_BB03      2
#define BOARD_DVT       3

// select default board to build for
#ifndef BOARD
#define BOARD BOARD_DVT
#endif


#if BOARD == BOARD_BB02
#include "board_bb02.h"
#elif BOARD == BOARD_BB03
#include "board_bb03.h"
#elif BOARD == BOARD_DVT
#include "board_dvt.h"
#else
#error BOARD not configured
#endif

#endif // BOARD_H
