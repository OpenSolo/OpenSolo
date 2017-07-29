#include "format_reader.h"

#include "la-log.h"

void Format_Reader::do_idle_callbacks()
{
    uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);
    if (next_100hz_time <= now_us) {
        for (int i = 0; i < next_message_handler; i++) {
            message_handler[i]->idle_100Hz();
        }
        next_100hz_time += 10000;
    }
    if (next_10hz_time <= now_us) {
        for (int i = 0; i < next_message_handler; i++) {
            message_handler[i]->idle_10Hz();
        }
        next_10hz_time += 100000;
    }
    if (next_1hz_time <= now_us) {
        for (int i = 0; i < next_message_handler; i++) {
            message_handler[i]->idle_1Hz();
        }
        next_1hz_time += 1000000;
    }
    if (next_tenthhz_time <= now_us) {
        for (int i = 0; i < next_message_handler; i++) {
            message_handler[i]->idle_tenthHz();
        }
        next_tenthhz_time += 10000000;
    }
}

bool Format_Reader::add_message_handler(Message_Handler *handler, const char *handler_name)
{
    if (MAX_MESSAGE_HANDLERS - next_message_handler < 2) {
        la_log(LOG_INFO, "Insufficient message handler slots (MAX=%d) (next=%d)?!",
               MAX_MESSAGE_HANDLERS, next_message_handler);
        return false;
    }

    if (!handler->configure(_config)) {
        la_log(LOG_INFO, "Failed to configure (%s)", handler_name);
        return false;
    }

    message_handler[next_message_handler++] = handler;
    return true;
}

void Format_Reader::clear_message_handlers()
{
    next_message_handler = 0;
}

void Format_Reader::sighup_handler()
{
    for (int i = 0; i < next_message_handler; i++) {
        message_handler[i]->sighup_received();
    }
}
