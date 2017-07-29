#ifndef _SLIP_H
#define _SLIP_H

class SLIP
{
public:
    SLIP(char *msg, int maxMsgLen);

protected:
    char *_msg;    // Pointer to the message bufer
    char *_msgPtr; // The current read/write pointer
    int _maxLen;
    int _msgLen;
    bool _escTriggered;
    static const unsigned END = 0300;     // indicates end of packet
    static const unsigned ESC = 0333;     // indicates byte stuffing
    static const unsigned ESC_END = 0334; // ESC ESC_END means END data byte
    static const unsigned ESC_ESC = 0335; // ESC ESC_ESC means ESC data byte

    void reset(void)
    {
        _msgPtr = _msg;
        _msgLen = 0;
        _escTriggered = false;
    };
};

class SLIPDecoder : public SLIP
{
public:
    SLIPDecoder(char *msg, int maxMsgLen);
    int addByte(char *b); // Returns -1: error, 0:no message yet, >0:done, msg available
};

class SLIPEncoder : public SLIP
{
public:
    SLIPEncoder(char *msg, int maxMsgLen);
    int encode(char *buf, int bufLen); // Encodes an array of bytes, returns len
};

#endif //_SLIP_H
