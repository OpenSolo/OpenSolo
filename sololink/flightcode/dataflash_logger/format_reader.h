#ifndef FORMAT_READER_H
#define FORMAT_READER_H

#include "INIReader.h"
#include "util.h"

#include "message_handler.h"

class Format_Reader
{
public:
    Format_Reader(INIReader *config) : _config(config)
    {
        uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);
        next_tenthhz_time = now_us;
        next_1hz_time = now_us;
        next_10hz_time = now_us;
        next_100hz_time = now_us;
    };

    void do_idle_callbacks();

    virtual bool add_message_handler(Message_Handler *handler, const char *handler_name);
    virtual void clear_message_handlers();

    virtual void sighup_handler();

    virtual uint32_t feed(const uint8_t *buf, const uint32_t len) = 0;

    virtual void end_of_log(){};

protected:
    INIReader *_config;

// FIXME: Scope
#define MAX_MESSAGE_HANDLERS 10
    uint8_t next_message_handler = 0;
    Message_Handler *message_handler[MAX_MESSAGE_HANDLERS];

private:
    bool sighup_received = false;

    uint64_t next_tenthhz_time;
    uint64_t next_1hz_time;
    uint64_t next_10hz_time;
    uint64_t next_100hz_time;
};

#endif
