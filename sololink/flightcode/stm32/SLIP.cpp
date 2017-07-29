#include <iostream>
#include "SLIP.h"

using namespace std;

SLIP::SLIP(char *msg, int maxMsgLen)
    : _msg(msg), _msgPtr(msg), _maxLen(maxMsgLen), _msgLen(0), _escTriggered(false)
{
}

/****************************************************************
Class: SLIPEncoder

Description:  Encodes a byte stream into SLIP
****************************************************************/
SLIPEncoder::SLIPEncoder(char *msg, int maxMsgLen) : SLIP(msg, maxMsgLen){};

/****************************************************************
Method: encode(char *buf, int bufLen)

Description:  Encodes a buffer into SLIP, returns the length of
              the encoded message
****************************************************************/
int SLIPEncoder::encode(char *buf, int bufLen) // Encodes an array of bytes
{
    int ret = -1;
    int i;

    // Prepend with an end
    *_msgPtr++ = END;
    _msgLen++;

    for (i = 0; i < bufLen; ++i) {
        // Add the esc sequence if necessary
        if (buf[i] == ESC || buf[i] == END) {
            *_msgPtr++ = ESC;
            *_msgPtr++ = (buf[i] == ESC ? ESC_ESC : ESC_END);
            _msgLen += 2;
        }
        // Otherwise just copy bytes
        else {
            *_msgPtr++ = buf[i];
            ++_msgLen;
        }

        // Error checking
        if (_msgLen > _maxLen) {
            reset();
            return -1;
        }
    }

    // Add an END at the end...novel idea.
    *_msgPtr = END;
    ++_msgLen;

    ret = _msgLen;
    reset();

    return ret;
}

/****************************************************************
Class: SLIPDecoder

Description:  Accepts encoded SLIP bytes in and creates a decoded
              message.
****************************************************************/
SLIPDecoder::SLIPDecoder(char *msg, int maxMsgLen) : SLIP(msg, maxMsgLen){};

/****************************************************************
Method: addByte(char *b)

Description:  Adds bytes from an encoded SLIP message to an
              decoded SLIP message.  Returns a positive value when
              the entire message has been read, zero if not done.
              A negative number indicates an error.
****************************************************************/
int SLIPDecoder::addByte(char *b)
{
    int retVal = -1;

    // and END packet indicates the end of a message
    if (*b == END) {
        retVal = _msgLen;

        // Reset the _msgLen for the next message
        reset();

        return retVal;
    }

    // Error check
    if (_msgLen > _maxLen) {
        reset();
        return -1;
    }

    // Otherwise, append the byte to the message.

    // Check for ESC and END bytes
    if (_escTriggered) {
        // This should be an ESC_END or ESC_ESC
        if (*b != ESC_END && *b != ESC_ESC) {
            reset();
            return -1;
        } else {
            *_msgPtr++ = (*b == ESC_END ? END : ESC);
            ++_msgLen;
        }

        _escTriggered = false;
    } else {
        // Look for an escape sequence
        if (*b == ESC) {
            _escTriggered = true;
        } else {
            *_msgPtr++ = *b;
            ++_msgLen;
        }
    }

    return 0;
}
