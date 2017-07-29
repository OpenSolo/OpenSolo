#include <iostream>
#include <iomanip>
#include "ButtonEventMessage.h"

using namespace std;

// Send a ButtonEventMessage to a stream in a friendly format.
ostream &operator<<(ostream &os, const struct ButtonEventMessage &msg)
{
    os << "timestamp=" << msg.timestamp;
    os << " id=" << msg.idName();
    os << " event=" << msg.eventName();
    os << " allButtons=" << setfill('0') << setw(4) << hex << msg.allButtons;
    return os;
}
