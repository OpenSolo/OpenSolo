#ifndef DATAFLASH_MESSAGE_HANDLER_H
#define DATAFLASH_MESSAGE_HANDLER_H

#include <stdio.h>

/*
 * dataflash_message_handler
 *
 * A base class for objects which process dataflash messages and
 * possibly send responses
 *
 */

#include <stdint.h>

#include "INIReader.h"

#include "message_handler.h"

class DataFlash_Message_Handler : public Message_Handler
{
public:
    virtual void handle_format_message_received(const char *name, const struct log_Format &format,
                                                const char *msg) = 0;
    virtual void handle_message_received(const struct log_Format &format, const uint8_t *msg) = 0;

protected:
private:
};

#endif
